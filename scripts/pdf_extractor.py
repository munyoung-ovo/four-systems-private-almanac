from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MATERIALS_DIR = ROOT / "materials"
MAX_TEXT_CHARS = 240_000
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PDF_SUFFIXES = {".pdf"}

LOCAL_DEPS = ROOT / ".skill_deps"
if LOCAL_DEPS.is_dir():
    sys.path.insert(0, str(LOCAL_DEPS))
sys.path.insert(0, str(ROOT))


def _json_print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _optional_import(module: str):
    try:
        return __import__(module)
    except Exception:
        return None


def _load_pypdf():
    try:
        from pypdf import PdfReader  # type: ignore

        return PdfReader
    except ImportError:
        try:
            with open(os.devnull, "wb") as devnull:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "pypdf", "--quiet"],
                    stdout=devnull,
                    stderr=devnull,
                )
            from pypdf import PdfReader  # type: ignore

            return PdfReader
        except Exception:
            return None


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _read_pdf_text(path: Path, PdfReader) -> tuple[str, int]:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        reader = PdfReader(str(path))
        pages = len(reader.pages)
        chunks: list[str] = []
        total = 0
        for page in reader.pages:
            chunk = page.extract_text() or ""
            if chunk:
                chunks.append(chunk)
                total += len(chunk)
            if total >= MAX_TEXT_CHARS:
                break
    return _clean_text("\n".join(chunks)), pages


def _read_image_text(path: Path) -> tuple[str, str]:
    pytesseract = _optional_import("pytesseract")
    try:
        from PIL import Image  # type: ignore
    except Exception:
        Image = None
    if pytesseract is None or Image is None:
        return "", "needs_ai_vision"
    try:
        image = Image.open(str(path))
        text = pytesseract.image_to_string(image, lang="chi_sim+eng")  # type: ignore[attr-defined]
        return _clean_text(text), "ocr"
    except Exception:
        return "", "needs_ai_vision"


def _first(patterns: list[str], text: str, flags: int = re.IGNORECASE) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            for value in match.groups():
                if value is not None:
                    return re.sub(r"\s+", " ", value).strip(" :：,，;；")
    return None


def _float(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{4})[-/.年 ]+(\d{1,2})[-/.月 ]+(\d{1,2})", value)
    if not match:
        match = re.search(r"(\d{1,2})[-/. ]+(\d{1,2})[-/. ]+(\d{4})", value)
        if not match:
            return value.strip()
        month, day, year = match.groups()
    else:
        year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _normalize_time(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.lower()
    match = re.search(r"(\d{1,2})[:：](\d{2})(?:[:：](\d{2}))?", lowered)
    if not match:
        match = re.search(r"(\d{1,2})\s*(?:h|时|點|点)\s*(\d{1,2})?", lowered)
        if not match:
            return value.strip()
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    second = int(match.group(3) or 0) if len(match.groups()) >= 3 and match.group(3) else 0
    if "pm" in lowered and hour < 12:
        hour += 12
    if "am" in lowered and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        return value.strip()
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def _extract_fields(text: str) -> dict[str, Any]:
    name = _first(
        [
            r"(?:Name|姓名|名字|命主|Native|Chart name)\s*[:：]\s*([^\n,，]{1,64})",
        ],
        text,
    )
    gender = _first([r"(?:Gender|Sex|性别)\s*[:：]\s*(Male|Female|男|女|M|F)"], text)
    birth_date = _normalize_date(
        _first(
            [
                r"(?:Date of Birth|Birth Date|DOB|出生日期|出生)\s*[:：]\s*([^\n]{4,40})",
                r"(\d{4}[-/.年 ]+\d{1,2}[-/.月 ]+\d{1,2})",
            ],
            text,
        )
    )
    birth_time = _normalize_time(
        _first(
            [
                r"(?:Time of Birth|Birth Time|TOB|出生时间|時間|时间)\s*[:：]\s*([^\n]{2,40})",
                r"(\d{1,2}[:：]\d{2}(?:[:：]\d{2})?\s*(?:AM|PM|am|pm)?)",
            ],
            text,
        )
    )
    place = _first(
        [
            r"(?:Place of Birth|Birth Place|POB|出生地|出生地点)\s*[:：]\s*([^\n]{1,80})",
            r"(?:City|城市)\s*[:：]\s*([^\n]{1,80})",
        ],
        text,
    )
    latitude = _float(_first([r"(?:Latitude|Lat\.?|纬度)\s*[:：]?\s*([-+]?\d+(?:\.\d+)?)"], text))
    longitude = _float(_first([r"(?:Longitude|Long\.?|Lon\.?|经度)\s*[:：]?\s*([-+]?\d+(?:\.\d+)?)"], text))
    timezone = _first(
        [
            r"(?:Time Zone|Timezone|TZ|时区)\s*[:：]?\s*(UTC\s*[-+]?\d+(?:\.\d+)?|GMT\s*[-+]?\d+(?:\.\d+)?|[-+]?\d+(?:\.\d+)?)"
        ],
        text,
    )

    fields: dict[str, Any] = {
        "name": name,
        "gender": {"Male": "男", "M": "男", "Female": "女", "F": "女"}.get(str(gender), gender),
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_place_name": place,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
    }
    if birth_date and birth_time and re.match(r"^\d{4}-\d{2}-\d{2}$", birth_date):
        fields["solar_birth"] = f"{birth_date}T{birth_time}"
    return {key: value for key, value in fields.items() if value not in (None, "", {}, [])}


def _extract_chart_labels(text: str) -> dict[str, Any]:
    labels = {
        "western_sun": _first([r"(?:Sun|太阳)\s*(?:Sign)?\s*[:：]\s*([A-Za-z\u4e00-\u9fff]{1,24})"], text),
        "western_moon": _first([r"(?:Moon|月亮)\s*(?:Sign)?\s*[:：]\s*([A-Za-z\u4e00-\u9fff]{1,24})"], text),
        "western_ascendant": _first([r"(?:Ascendant|ASC|上升)\s*[:：]\s*([A-Za-z\u4e00-\u9fff]{1,24})"], text),
        "vedic_moon_nakshatra": _first([r"(?:Nakshatra|月宿)\s*[:：]\s*([A-Za-z\u4e00-\u9fff]{1,32})"], text),
        "ziwei_ming_gong": _first([r"(?:命宫|命宮)\s*[:：]?\s*([A-Za-z\u4e00-\u9fff、,，]{1,40})"], text),
        "bazi_pillars": _first([r"(?:四柱|八字)\s*[:：]\s*([甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥\s]{8,32})"], text),
    }
    return {key: value for key, value in labels.items() if value}


def _confidence(fields: dict[str, Any], labels: dict[str, Any]) -> float:
    score = 0.0
    weights = {
        "solar_birth": 0.38,
        "birth_place_name": 0.16,
        "latitude": 0.12,
        "longitude": 0.12,
        "timezone": 0.05,
    }
    for key, weight in weights.items():
        if fields.get(key):
            score += weight
    score += min(0.17, len(labels) * 0.04)
    return round(min(score, 1.0), 2)


def _result_from_text(path: Path, text: str, source_type: str, method: str, pages: int | None = None) -> dict[str, Any]:
    fields = _extract_fields(text)
    labels = _extract_chart_labels(text)
    if not fields and not labels:
        return {
            "file": path.name,
            "status": "error",
            "reason": "NO_RELEVANT_FIELDS",
            "message": "没有提取到可用于排盘或复审的结构化字段。",
            "source_type": source_type,
            "method": method,
            **({"pages": pages} if pages is not None else {}),
        }
    return {
        "file": path.name,
        "status": "ok",
        "source_type": source_type,
        "method": method,
        "confidence": _confidence(fields, labels),
        "calculation_profile_fields": fields,
        "chart_labels": labels,
        **({"pages": pages} if pages is not None else {}),
    }


def extract_file(path: Path, PdfReader=None) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in PDF_SUFFIXES:
        if PdfReader is None:
            return {"file": path.name, "status": "error", "reason": "PYPDF_UNAVAILABLE", "message": "无法读取 PDF。"}
        try:
            text, pages = _read_pdf_text(path, PdfReader)
        except Exception:
            return {"file": path.name, "status": "error", "reason": "CORRUPT_OR_UNREADABLE", "message": "PDF 损坏或无法读取。"}
        if len(text.strip()) < 20:
            return {
                "file": path.name,
                "status": "needs_ocr",
                "reason": "SCANNED_OR_EMPTY_PDF",
                "message": "这个 PDF 可能是扫描件，需要 OCR 或 AI 视觉读取。",
                "source_type": "pdf",
                "pages": pages,
            }
        return _result_from_text(path, text, "pdf", "pdf_text", pages=pages)

    if suffix in IMAGE_SUFFIXES:
        text, method = _read_image_text(path)
        if method == "needs_ai_vision" or len(text.strip()) < 10:
            return {
                "file": path.name,
                "status": "needs_ai_vision",
                "reason": "OCR_UNAVAILABLE_OR_LOW_TEXT",
                "message": "图片需要 OCR 或 AI 视觉读取；请把图交给当前 AI 直接看，提取出生信息和盘面标签后再复审。",
                "source_type": "image",
                "method": method,
            }
        return _result_from_text(path, text, "image", method)

    return {"file": path.name, "status": "skipped", "reason": "UNSUPPORTED_TYPE", "message": "暂不支持这个文件类型。"}


def _material_files(selected: list[str] | None) -> list[Path]:
    if selected:
        return [MATERIALS_DIR / item for item in selected]
    suffixes = PDF_SUFFIXES | IMAGE_SUFFIXES
    return sorted(path for path in MATERIALS_DIR.iterdir() if path.is_file() and path.suffix.lower() in suffixes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract birth fields and chart labels from materials.")
    parser.add_argument("files", nargs="*", help="Optional file names inside materials/.")
    args = parser.parse_args()

    files = _material_files(args.files)
    if not files:
        _json_print({"status": "error", "reason": "NO_MATERIAL_FOUND", "message": "materials 目录下没有 PDF/JPG/PNG 等可读取文件。"})
        return

    PdfReader = _load_pypdf()
    results = [extract_file(path, PdfReader=PdfReader) for path in files]
    ok_count = sum(1 for item in results if item.get("status") == "ok")
    pending_count = sum(1 for item in results if item.get("status") in ("needs_ocr", "needs_ai_vision"))
    _json_print(
        {
            "status": "ok" if ok_count else "needs_attention" if pending_count else "error",
            "material_count": len(files),
            "ok_count": ok_count,
            "pending_count": pending_count,
            "results": results,
        }
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _json_print({"status": "error", "reason": "UNEXPECTED_FAILURE", "message": str(exc)})
