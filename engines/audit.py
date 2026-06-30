from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "profiles"


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [], {}, "unknown")


def _collect_boundary_warnings(profile: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    bazi = profile.get("bazi") or {}
    for item in bazi.get("boundary_warnings") or []:
        if item and item not in warnings:
            warnings.append(str(item))

    time_adjustment = bazi.get("time_adjustment") or {}
    effective_time = time_adjustment.get("effective_time")
    if effective_time:
        warnings.append(f"true_solar_effective_time={effective_time}")
    return warnings


def _system_health(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bazi = profile.get("bazi") or {}
    ziwei = profile.get("ziwei") or {}
    vedic = profile.get("vedic") or {}
    western = profile.get("western") or {}

    return {
        "bazi": {
            "ok": bool((bazi.get("pillars") or {}).get("day")),
            "degraded": bool(bazi.get("degraded")),
            "key": (bazi.get("pillars") or {}),
        },
        "ziwei": {
            "ok": bool(ziwei.get("soul_palace") or ziwei.get("palace_by_name")),
            "degraded": bool(ziwei.get("degraded")),
            "key": {
                "soul_palace": ziwei.get("soul_palace"),
                "five_elements_class": ziwei.get("five_elements_class"),
            },
        },
        "vedic": {
            "ok": bool(vedic.get("moon_nakshatra")),
            "degraded": bool(vedic.get("degraded")),
            "key": {
                "moon_nakshatra": vedic.get("moon_nakshatra"),
                "moon_pada": vedic.get("moon_pada"),
                "ascendant": vedic.get("ascendant"),
            },
        },
        "western": {
            "ok": bool(western.get("sun") and western.get("moon")),
            "degraded": bool(western.get("degraded")),
            "key": {
                "sun": western.get("sun"),
                "moon": western.get("moon"),
                "ascendant": western.get("ascendant"),
                "mc": western.get("mc"),
            },
        },
    }


_SIGN_ALIASES = {
    "aries": "白羊",
    "taurus": "金牛",
    "gemini": "双子",
    "cancer": "巨蟹",
    "leo": "狮子",
    "virgo": "处女",
    "libra": "天秤",
    "scorpio": "天蝎",
    "sagittarius": "射手",
    "capricorn": "摩羯",
    "aquarius": "水瓶",
    "pisces": "双鱼",
}


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = _SIGN_ALIASES.get(text, text)
    for mark in (" ", "\t", "\n", "\r", ":", "：", ",", "，", ";", "；", "、"):
        text = text.replace(mark, "")
    return text


def _first_value(*values: Any) -> Any:
    for value in values:
        if _nonempty(value):
            return value
    return None


def _bazi_pillars_text(profile: dict[str, Any]) -> str:
    pillars = (profile.get("bazi") or {}).get("pillars") or {}
    return "".join(str(pillars.get(key) or "") for key in ("year", "month", "day", "hour"))


def compare_material_to_profile(profile: dict[str, Any], material_result: dict[str, Any]) -> dict[str, Any]:
    status = material_result.get("status")
    if status in ("needs_ocr", "needs_ai_vision", "unreadable", "error"):
        return {
            "file": material_result.get("file"),
            "status": status,
            "reason": material_result.get("reason"),
            "message": material_result.get("message"),
            "matches": [],
            "conflicts": [],
        }

    labels = material_result.get("chart_labels") or {}
    checks = [
        ("western_sun", labels.get("western_sun"), (profile.get("western") or {}).get("sun")),
        ("western_moon", labels.get("western_moon"), (profile.get("western") or {}).get("moon")),
        ("western_ascendant", labels.get("western_ascendant"), (profile.get("western") or {}).get("ascendant")),
        ("vedic_moon_nakshatra", labels.get("vedic_moon_nakshatra"), (profile.get("vedic") or {}).get("moon_nakshatra")),
        (
            "ziwei_ming_gong",
            labels.get("ziwei_ming_gong"),
            " ".join(
                str(item)
                for item in [
                    ((profile.get("ziwei") or {}).get("soul_palace") or {}).get("name"),
                    " ".join(((profile.get("ziwei") or {}).get("soul_palace") or {}).get("major_stars") or []),
                ]
                if _nonempty(item)
            ),
        ),
        ("bazi_pillars", labels.get("bazi_pillars"), _bazi_pillars_text(profile)),
    ]

    matches: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    skipped: list[str] = []
    for field, material_value, local_value in checks:
        if not _nonempty(material_value):
            skipped.append(field)
            continue
        if not _nonempty(local_value):
            conflicts.append({"field": field, "material": material_value, "local": None, "reason": "LOCAL_MISSING"})
            continue
        material_norm = _norm(material_value)
        local_norm = _norm(local_value)
        if material_norm == local_norm or material_norm in local_norm or local_norm in material_norm:
            matches.append({"field": field, "material": material_value, "local": local_value})
        else:
            conflicts.append({"field": field, "material": material_value, "local": local_value})

    if conflicts:
        result_status = "conflict"
    elif matches:
        result_status = "match"
    else:
        result_status = "no_comparable_labels"

    return {
        "file": material_result.get("file"),
        "status": result_status,
        "matches": matches,
        "conflicts": conflicts,
        "skipped": skipped,
        "source_status": status,
    }


def compare_materials_to_profile(profile: dict[str, Any], material_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [compare_material_to_profile(profile, item) for item in material_results]


def audit_profile(profile: dict[str, Any], material_checks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    meta = profile.get("meta") or {}
    place = meta.get("birth_place") or {}
    health = _system_health(profile)
    issues: list[dict[str, str]] = []
    notes: list[str] = []

    if not _nonempty(meta.get("solar_birth")):
        issues.append({"level": "high", "code": "missing_birth_time", "message": "缺少出生时间。"})
    if meta.get("time_precision") in ("unknown", "day"):
        issues.append({"level": "high", "code": "unknown_birth_time", "message": "出生时间精度不足，时辰、上升和宫位不可强断。"})
    elif meta.get("time_precision") in ("hour", "approximate"):
        issues.append({"level": "caution", "code": "approximate_birth_time", "message": "出生时间不是分钟级，贴近边界的判断要保守。"})

    if not _nonempty(place.get("lat")) or not _nonempty(place.get("lon")):
        issues.append({"level": "caution", "code": "missing_coordinates", "message": "出生地经纬度不完整，西占/印占宫位与真太阳时需要复核。"})
    if not _nonempty(place.get("tz")):
        issues.append({"level": "caution", "code": "missing_timezone", "message": "时区不完整，月亮、上升、月宿和四柱边界需要复核。"})

    for system, item in health.items():
        if not item["ok"]:
            issues.append({"level": "high", "code": f"{system}_missing", "message": f"{system} 关键排盘字段缺失。"})
        elif item["degraded"]:
            issues.append({"level": "caution", "code": f"{system}_degraded", "message": f"{system} 处于降级状态。"})

    boundary_warnings = _collect_boundary_warnings(profile)
    if boundary_warnings:
        issues.append({"level": "caution", "code": "boundary_or_true_solar", "message": "存在真太阳时或边界提醒，相关判断需保守。"})

    material_checks = material_checks or []
    if any(item.get("status") == "ok" and "chart_labels" in item for item in material_checks):
        material_checks = compare_materials_to_profile(profile, material_checks)
    conflicts = [item for item in material_checks if item.get("status") == "conflict"]
    matches = [item for item in material_checks if item.get("status") == "match"]
    pending = [item for item in material_checks if item.get("status") in ("needs_ocr", "needs_ai_vision", "unreadable", "no_comparable_labels")]
    if conflicts:
        issues.append({"level": "high", "code": "material_conflict", "message": "用户材料与本地排盘存在冲突，需要先确认。"})
    if matches:
        notes.append(f"材料交叉验证一致项 {len(matches)} 个。")
    if pending:
        issues.append({"level": "caution", "code": "material_pending", "message": "部分图片或扫描件需要 OCR/AI 视觉辅助读取。"})

    high = any(item["level"] == "high" for item in issues)
    caution = any(item["level"] == "caution" for item in issues)
    status = "high_risk" if high else "caution" if caution else "stable"

    return {
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile_name": meta.get("name"),
        "checks": {
            "birth_info_complete": not any(item["code"].startswith("missing_") for item in issues),
            "system_health": health,
            "boundary_warnings": boundary_warnings,
            "material_checks": material_checks,
        },
        "issues": issues,
        "notes": notes,
        "user_summary": _summary(status, issues),
    }


def _summary(status: str, issues: list[dict[str, str]]) -> str:
    if status == "stable":
        return "我已经帮你核过盘，这次出生信息和四套系统都可以稳定使用。"
    if status == "caution":
        return "我已经帮你核过盘，有少量边界或材料待确认，解读会保守处理。"
    first = issues[0]["message"] if issues else "出生信息或材料存在高风险。"
    return f"这次排盘需要先确认：{first}"


def save_audit(profile: dict[str, Any], material_checks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    audit = audit_profile(profile, material_checks=material_checks)
    name = (profile.get("meta") or {}).get("name")
    if name:
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        path = PROFILES_DIR / f"{name}.audit.json"
        path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit


def load_audit(name: str) -> dict[str, Any] | None:
    path = PROFILES_DIR / f"{name}.audit.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Audit a saved astrology profile.")
    parser.add_argument("name", help="Profile name without .json")
    args = parser.parse_args()

    profile_path = PROFILES_DIR / f"{args.name}.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    audit = save_audit(profile)
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
