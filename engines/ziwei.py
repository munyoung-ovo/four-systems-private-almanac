
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

MAIN_STARS = {
    "紫微", "天机", "太阳", "武曲", "天同", "廉贞", "天府", "太阴",
    "贪狼", "巨门", "天相", "天梁", "七杀", "破军",
}
AUSPICIOUS_STARS = {"左辅", "右弼", "文昌", "文曲", "天魁", "天钺", "禄存", "天马"}
PRESSURE_STARS = {"擎羊", "陀罗", "火星", "铃星", "地空", "地劫"}
TOPIC_PALACES = {
    "love": ["夫妻宫", "福德宫", "迁移宫"],
    "career": ["官禄宫", "财帛宫", "迁移宫"],
    "wealth": ["财帛宫", "田宅宫", "官禄宫"],
    "health": ["疾厄宫", "福德宫"],
    "support": ["父母宫", "交友宫", "兄弟宫"],
}

def _safe_translate(obj, method: str, fallback: str = "") -> str:
    fn = getattr(obj, method, None)
    if callable(fn):
        try:
            return fn() or fallback
        except Exception:
            return fallback
    return fallback

def _normalize_palace_name(name: str) -> str:
    name = str(name or "")
    return name if name.endswith("宫") else f"{name}宫"

def _palace_strength(major_stars: list[str], minor_stars: list[str]) -> dict:
    auspicious = [s for s in minor_stars if s in AUSPICIOUS_STARS]
    pressure = [s for s in minor_stars if s in PRESSURE_STARS]
    score = len(major_stars) * 2 + len(auspicious) - len(pressure)
    if not major_stars:
        quality = "empty"
    elif score >= 4:
        quality = "supported"
    elif score <= 0:
        quality = "pressured"
    else:
        quality = "balanced"
    return {
        "score": score,
        "quality": quality,
        "auspicious_stars": auspicious,
        "pressure_stars": pressure,
    }

def _support_indices(index: int) -> dict:
    return {
        "self": index,
        "opposite": (index + 6) % 12,
        "triad": sorted({index, (index + 4) % 12, (index + 8) % 12}),
        "triad_opposite": sorted({index, (index + 4) % 12, (index + 8) % 12, (index + 6) % 12}),
    }

def _build_ziwei_basis(palaces: list[dict], soul_palace: dict | None,
                       body_palace: dict | None, degraded: bool) -> dict:
    by_index = {p["index"]: p for p in palaces}
    enriched = []
    for p in palaces:
        idx = p["index"]
        support = _support_indices(idx)
        opposite = by_index.get(support["opposite"], {})
        strength = _palace_strength(p.get("major_stars", []), p.get("minor_stars", []))
        borrowed = []
        if not p.get("major_stars"):
            borrowed = opposite.get("major_stars", [])
        enriched.append({
            **p,
            "normalized_name": _normalize_palace_name(p.get("name", "")),
            "opposite_index": support["opposite"],
            "opposite_palace": opposite.get("name", ""),
            "triad_indices": support["triad"],
            "triad_opposite_indices": support["triad_opposite"],
            "borrowed_major_stars": borrowed,
            "strength": strength,
        })

    by_name = {_normalize_palace_name(p["name"]): p for p in enriched if p.get("name")}
    topic_index = {
        topic: [by_name[name] for name in names if name in by_name]
        for topic, names in TOPIC_PALACES.items()
    }
    return {
        "available": not degraded,
        "precision": "minute" if not degraded else "degraded",
        "palaces": enriched,
        "palace_by_name": by_name,
        "topic_index": topic_index,
        "soul_palace": soul_palace,
        "body_palace": body_palace,
        "validation": {
            "palace_count": len(palaces),
            "has_soul_palace": bool(soul_palace),
            "has_body_palace": bool(body_palace),
            "all_palaces_named": all(bool(p.get("name")) for p in palaces),
        },
    }

def _summarize_layer(layer: dict) -> dict:
    transform_by_palace: dict[str, list[dict]] = {}
    transform_by_type: dict[str, dict] = {}
    for t in layer.get("transforms", []):
        palace = t.get("flow_palace", "")
        transform_by_palace.setdefault(palace, []).append(t)
        transform_by_type[t.get("type", "")] = t
    return {
        "name": layer.get("name", ""),
        "degraded": layer.get("degraded", False),
        "flow_soul_palace": layer.get("flow_soul_palace"),
        "flow_soul_stars": layer.get("flow_soul_stars", []),
        "transform_by_palace": transform_by_palace,
        "transform_by_type": transform_by_type,
        "active_palaces": sorted(k for k in transform_by_palace if k),
    }

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
        "ziwei_basis":       _build_ziwei_basis(
            palaces, palace_dict(soul_palace), palace_dict(body_palace),
            time_precision == "unknown",
        ),
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

    layers = {
        "degraded": degraded,
        "decadal": _horoscope_state(chart, h.decadal, degraded),
        "yearly": _horoscope_state(chart, h.yearly, degraded),
        "monthly": _horoscope_state(chart, h.monthly, degraded),
        "daily": _horoscope_state(chart, h.daily, degraded),
    }
    layers["summary"] = {
        key: _summarize_layer(layers[key])
        for key in ("decadal", "yearly", "monthly", "daily")
    }
    return layers

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

