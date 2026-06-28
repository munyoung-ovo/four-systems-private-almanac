
import json
from iztro_py import astro as _astro
from typing import Literal
from models.profile import CalculationProfile, CalendarType, EvidenceLevel, TimePrecision

def _hour_to_time_index(hour: int, minute: int = 0) -> int:
    total = hour * 60 + minute
    if total < 60:    return 0
    if total >= 1380: return 12
    return (total - 60) // 120 + 1

TIME_PRECISION = Literal["exact", "hour", "unknown"]

def _safe_translate(obj, method: str, fallback: str = "") -> str:
    fn = getattr(obj, method, None)
    if callable(fn):
        try:
            return fn() or fallback
        except Exception:
            return fallback
    return fallback

def build(solar_dt: str, gender: str,
          time_precision: TIME_PRECISION = "exact",
          target_date: str | None = None) -> dict:
    from datetime import datetime
    from datetime import date
    dt = datetime.fromisoformat(solar_dt)
    if target_date is None:
        target_date = date.today().isoformat()

    time_index = 0 if time_precision == "unknown" else _hour_to_time_index(dt.hour, dt.minute)

    chart = _astro.by_solar(
        f"{dt.year}-{dt.month}-{dt.day}",
        time_index,
        gender,
    )
    chart.set_language("zh-CN")

    soul_palace  = chart.get_soul_palace()
    body_palace  = chart.get_body_palace()

    def palace_dict(p) -> dict | None:
        if p is None:
            return None
        return {
            "name":           _safe_translate(p, "translate_name"),
            "heavenly_stem":  _safe_translate(p, "translate_heavenly_stem"),
            "earthly_branch": _safe_translate(p, "translate_earthly_branch"),
            "major_stars":    [_safe_translate(s, "translate_name") for s in p.major_stars],
            "minor_stars":    [_safe_translate(s, "translate_name") for s in p.minor_stars],
        }

    palaces = []
    palace_by_name = {}
    for p in chart.palaces:
        item = {
            "index":          p.index,
            "name":           _safe_translate(p, "translate_name"),
            "heavenly_stem":  _safe_translate(p, "translate_heavenly_stem"),
            "earthly_branch": _safe_translate(p, "translate_earthly_branch"),
            "major_stars":    [_safe_translate(s, "translate_name") for s in p.major_stars],
            "minor_stars":    [_safe_translate(s, "translate_name") for s in p.minor_stars],
        }
        palaces.append(item)
        if item["name"]:
            palace_by_name[item["name"]] = item

    result = {
        "soul_palace":       palace_dict(soul_palace),
        "body_palace":       palace_dict(body_palace),
        "five_elements_class": chart.five_elements_class or "",
        "palaces":           palaces,
        "palace_by_name":    palace_by_name,
        "horoscope_layers":  horoscope_layers(solar_dt, gender, target_date, time_precision),
        "calculation_profile": CalculationProfile(
            calendar_type=CalendarType.SOLAR,
            is_true_solar_time=False,
            time_precision=(
                TimePrecision.MINUTE if time_precision == "exact"
                else TimePrecision.HOUR if time_precision == "hour"
                else TimePrecision.UNKNOWN
            ),
            confidence_score=0.88 if time_precision == "exact" else 0.68 if time_precision == "hour" else 0.3,
            evidence_level=EvidenceLevel.HIGH if time_precision == "exact" else EvidenceLevel.MEDIUM if time_precision == "hour" else EvidenceLevel.LOW,
            warnings=[] if time_precision != "unknown" else ["出生时间未知，命宫、身宫与流限判断降级"],
        ).to_dict(),
        "degraded":          time_precision == "unknown",
    }
    return result

def horoscope(solar_dt: str, gender: str,
              target_date: str,
              time_precision: TIME_PRECISION = "exact") -> dict:
    from datetime import datetime
    dt = datetime.fromisoformat(solar_dt)
    time_index = 0 if time_precision == "unknown" else _hour_to_time_index(dt.hour, dt.minute)

    chart = _astro.by_solar(
        f"{dt.year}-{dt.month}-{dt.day}",
        time_index,
        gender,
    )
    chart.set_language("zh-CN")
    h = chart.horoscope(target_date)
    try:
        return h.model_dump() if hasattr(h, "model_dump") else dict(h)
    except Exception:
        return {}

_PALACE_ROLE_ZH = {
    "soulPalace": "命宫", "siblingsPalace": "兄弟", "spousePalace": "夫妻",
    "childrenPalace": "子女", "wealthPalace": "财帛", "healthPalace": "疾厄",
    "surfacePalace": "迁移", "friendsPalace": "交友", "careerPalace": "官禄",
    "propertyPalace": "田宅", "spiritPalace": "福德", "parentsPalace": "父母",
}
_MUTAGEN_TYPES = ["禄", "权", "科", "忌"]

def _horoscope_state(chart, item, degraded: bool) -> dict:
    palace_names = list(item.palace_names)

    star_key_map: dict[str, tuple] = {}
    flow_roles = []
    flow_soul_idx = palace_names.index("soulPalace") if "soulPalace" in palace_names else -1
    for p in chart.palaces:
        role_key = palace_names[p.index] if p.index < len(palace_names) else ""
        role_zh = _PALACE_ROLE_ZH.get(role_key, role_key)
        flow_roles.append({
            "index": p.index,
            "natal_palace": _safe_translate(p, "translate_name"),
            "flow_role": role_zh,
            "earthly_branch": _safe_translate(p, "translate_earthly_branch"),
        })
        for s in list(p.major_stars) + list(p.minor_stars):
            raw = getattr(s, "name", None)
            if raw:
                star_key_map[raw] = (_safe_translate(s, "translate_name", raw), role_zh,
                                     _safe_translate(p, "translate_name"))

    transforms = []
    for i, star_key in enumerate(list(item.mutagen or [])[:4]):
        zh, flow_role, natal_palace = star_key_map.get(star_key, (star_key, "", ""))
        transforms.append({
            "type": _MUTAGEN_TYPES[i],
            "star": zh,
            "flow_palace": flow_role,
            "natal_palace": natal_palace,
        })

    flow_soul_stars = []
    flow_soul_palace = None
    if 0 <= flow_soul_idx < len(chart.palaces):
        p = chart.palaces[flow_soul_idx]
        flow_soul_palace = {
            "index": p.index,
            "name": _safe_translate(p, "translate_name"),
            "earthly_branch": _safe_translate(p, "translate_earthly_branch"),
        }
        flow_soul_stars = [_safe_translate(s, "translate_name") for s in p.major_stars]

    return {
        "degraded": degraded,
        "name": getattr(item, "name", ""),
        "index": getattr(item, "index", None),
        "heavenly_stem": str(getattr(item, "heavenly_stem", "")),
        "earthly_branch": str(getattr(item, "earthly_branch", "")),
        "flow_soul_palace": flow_soul_palace,
        "flow_soul_stars": flow_soul_stars,
        "flow_roles": flow_roles,
        "transforms": transforms,
    }

def horoscope_layers(solar_dt: str, gender: str, target_date: str,
                     time_precision: TIME_PRECISION = "exact") -> dict:
    from datetime import datetime
    dt = datetime.fromisoformat(solar_dt)
    degraded = time_precision == "unknown"
    time_index = 0 if degraded else _hour_to_time_index(dt.hour, dt.minute)

    try:
        chart = _astro.by_solar(f"{dt.year}-{dt.month}-{dt.day}", time_index, gender)
        chart.set_language("zh-CN")
        h = chart.horoscope(target_date)
    except Exception as e:
        empty = {"degraded": True, "error": str(e), "flow_soul_stars": [], "transforms": []}
        return {"degraded": True, "error": str(e),
                "decadal": empty, "yearly": empty, "monthly": empty, "daily": empty}

    return {
        "degraded": degraded,
        "decadal": _horoscope_state(chart, h.decadal, degraded),
        "yearly": _horoscope_state(chart, h.yearly, degraded),
        "monthly": _horoscope_state(chart, h.monthly, degraded),
        "daily": _horoscope_state(chart, h.daily, degraded),
    }

def year_horoscope_state(solar_dt: str, gender: str, target_date: str,
                         time_precision: TIME_PRECISION = "exact") -> dict:
    layers = horoscope_layers(solar_dt, gender, target_date, time_precision)
    yearly = layers.get("yearly", {})
    return {
        "degraded": yearly.get("degraded", layers.get("degraded", True)),
        "year_soul_stars": yearly.get("flow_soul_stars", []),
        "transforms": [
            {"type": t["type"], "star": t["star"], "palace": t.get("flow_palace", "")}
            for t in yearly.get("transforms", [])
        ],
    }

