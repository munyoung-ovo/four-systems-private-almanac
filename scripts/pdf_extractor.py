from __future__ import annotations

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


def _json_print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


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
        match = re.search(r"(\d{1,2})\s*(?:h|时|点)\s*(\d{1,2})?", lowered)
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
            r"(?:Name|姓名)\s*[:：]\s*([^\n,，;；]{1,64})",
            r"(?:Native|Nativ[e]?|Chart name)\s*[:：]\s*([^\n,，;；]{1,64})",
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
                r"(?:Time of Birth|Birth Time|TOB|出生时间|时间)\s*[:：]\s*([^\n]{2,40})",
                r"(\d{1,2}[:：]\d{2}(?:[:：]\d{2})?\s*(?:AM|PM|am|pm)?)",
            ],
            text,
        )
    )
    place = _first(
        [
            r"(?:Place of Birth|Birth Place|POB|出生地|地点)\s*[:：]\s*([^\n]{1,80})",
            r"(?:City|城市)\s*[:：]\s*([^\n]{1,80})",
        ],
        text,
    )
    latitude = _float(
        _first([r"(?:Latitude|Lat\.?|纬度)\s*[:：]?\s*([-+]?\d+(?:\.\d+)?)"], text)
    )
    longitude = _float(
        _first([r"(?:Longitude|Long\.?|Lon\.?|经度)\s*[:：]?\s*([-+]?\d+(?:\.\d+)?)"], text)
    )
    timezone = _first(
        [
            r"(?:Time Zone|Timezone|TZ|时区)\s*[:：]?\s*(UTC\s*[-+]?\d+(?:\.\d+)?|GMT\s*[-+]?\d+(?:\.\d+)?|[-+]?\d+(?:\.\d+)?)"
        ],
        text,
    )
    solar_birth = None
    if birth_date and birth_time and re.match(r"^\d{4}-\d{2}-\d{2}$", birth_date):
        solar_birth = f"{birth_date}T{birth_time}"

    fields: dict[str, Any] = {
        "name": name,
        "gender": {"Male": "男", "M": "男", "Female": "女", "F": "女"}.get(str(gender), gender),
        "birth_date": birth_date,
        "birth_time": birth_time,
        "solar_birth": solar_birth,
        "birth_place_name": place,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
    }
    return {key: value for key, value in fields.items() if value not in (None, "", {}, [])}


def _confidence(fields: dict[str, Any]) -> float:
    score = 0.0
    weights = {
        "solar_birth": 0.45,
        "birth_place_name": 0.2,
        "latitude": 0.15,
        "longitude": 0.15,
        "timezone": 0.05,
    }
    for key, weight in weights.items():
        if fields.get(key):
            score += weight
    return round(min(score, 1.0), 2)


def main() -> None:
    PdfReader = _load_pypdf()
    if PdfReader is None:
        _json_print(
            {
                "status": "error",
                "reason": "DEPENDENCY_INSTALL_FAILED",
                "message": "无法静默安装或导入 pypdf",
            }
        )
        return

    pdfs = sorted(path for path in MATERIALS_DIR.glob("*.pdf") if path.is_file())
    if not pdfs:
        _json_print(
            {
                "status": "error",
                "reason": "NO_PDF_FOUND",
                "message": "materials 目录下没有 PDF 文件",
            }
        )
        return

    results: list[dict[str, Any]] = []
    for path in pdfs:
        try:
            text, pages = _read_pdf_text(path, PdfReader)
        except Exception:
            results.append(
                {
                    "file": path.name,
                    "status": "error",
                    "reason": "CORRUPT_OR_UNREADABLE",
                    "message": "PDF 文件损坏或无法读取",
                }
            )
            continue

        if len(text.strip()) < 20:
            results.append(
                {
                    "file": path.name,
                    "status": "error",
                    "reason": "UNREADABLE_OR_SCANNED",
                    "message": "无法识别文本",
                    "pages": pages,
                }
            )
            continue

        fields = _extract_fields(text)
        if not fields:
            results.append(
                {
                    "file": path.name,
                    "status": "error",
                    "reason": "NO_RELEVANT_FIELDS",
                    "message": "未提取到可用于排盘的结构化字段",
                    "pages": pages,
                }
            )
            continue

        results.append(
            {
                "file": path.name,
                "status": "ok",
                "pages": pages,
                "confidence": _confidence(fields),
                "calculation_profile_fields": fields,
            }
        )

    ok_count = sum(1 for item in results if item.get("status") == "ok")
    _json_print({"status": "ok" if ok_count else "error", "pdf_count": len(pdfs), "results": results})


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _json_print(
            {
                "status": "error",
                "reason": "UNEXPECTED_FAILURE",
                "message": "PDF 提取器执行失败",
            }
        )
