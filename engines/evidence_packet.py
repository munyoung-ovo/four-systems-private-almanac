from __future__ import annotations

from engines.audit import audit_profile


TOPIC_ALIASES = {
    "感情": "love", "love": "love",
    "事业": "career", "career": "career",
    "财运": "wealth", "wealth": "wealth",
    "健康": "health", "health": "health",
    "贵人": "support", "support": "support",
}

VEDIC_HOUSES = {
    "love": (7,), "career": (10,), "wealth": (2, 11),
    "health": (6, 8), "support": (9, 11),
}

WESTERN_PLANETS = {
    "love": ("月亮", "金星", "火星"),
    "career": ("太阳", "水星", "木星", "土星"),
    "wealth": ("金星", "木星", "土星"),
    "health": ("月亮", "火星", "土星"),
    "support": ("木星", "水星", "金星"),
}


def _meta(chart: dict) -> dict:
    calculation = chart.get("calculation_profile") or {}
    return {
        "available": bool(chart) and not bool(chart.get("error")),
        "degraded": bool(chart.get("degraded")),
        "confidence": float(calculation.get("confidence_score", 0.5)),
        "precision": calculation.get("time_precision", "unknown"),
        "warnings": list(calculation.get("warnings") or []),
    }


def _bazi_packet(chart: dict) -> dict:
    facts = {
        "pillars": chart.get("pillars"),
        "day_master": chart.get("day_master"),
        "strength": chart.get("day_master_strength"),
        "strength_confidence": chart.get("strength_confidence"),
        "pattern": chart.get("ge_ju"),
        "special_pattern": chart.get("special_pattern"),
        "current_dayun": (chart.get("luck") or {}).get("current_dayun"),
        "current_liunian": (chart.get("luck") or {}).get("current_liunian"),
    }
    if (not chart.get("special_pattern")
            and float(chart.get("strength_confidence") or 0) >= 0.65
            and (chart.get("pillars") or {}).get("hour")):
        facts["yong_shen"] = chart.get("yong_shen")
        facts["ji_shen"] = chart.get("ji_shen")
    return {**_meta(chart), "scope": "natal-year", "facts": facts}


def _ziwei_packet(chart: dict, topic: str) -> dict:
    basis = chart.get("ziwei_basis") or {}
    facts = {
        "soul_palace": chart.get("soul_palace"),
        "body_palace": chart.get("body_palace"),
        "topic_palaces": (basis.get("topic_index") or {}).get(topic, []),
        "flow_summary": (chart.get("horoscope_layers") or {}).get("summary"),
    }
    return {**_meta(chart), "scope": "natal-year-month", "facts": facts}


def _vedic_packet(chart: dict, topic: str) -> dict:
    sav = (chart.get("ashtakavarga") or {}).get("sav_by_house") or {}
    selected = {str(h): sav.get(h) or sav.get(str(h)) for h in VEDIC_HOUSES.get(topic, ())}
    facts = {
        "moon_nakshatra": chart.get("moon_nakshatra"),
        "moon_pada": chart.get("moon_pada"),
        "lagna": chart.get("lagna"),
        "current_mahadasha": (chart.get("vimshottari") or {}).get("current_mahadasha"),
        "current_antardasha": (chart.get("vimshottari") or {}).get("current_antardasha"),
        "target_date": (chart.get("vimshottari") or {}).get("target_date"),
        "topic_sav_houses": selected,
    }
    return {**_meta(chart), "scope": "natal-period-day", "facts": facts}


def _western_packet(chart: dict, topic: str, target_date: str | None) -> dict:
    basis = chart.get("western_basis") or {}
    wanted = set(WESTERN_PLANETS.get(topic, ()))
    planets = basis.get("planets") or {}
    facts = {
        "sun": chart.get("sun"),
        "moon": chart.get("moon"),
        "ascendant": chart.get("ascendant") if basis.get("houses_available") else None,
        "houses_available": bool(basis.get("houses_available")),
        "topic_planets": {name: data for name, data in planets.items() if name in wanted},
        "topic_aspects": [
            item for item in (chart.get("natal_aspects") or [])
            if item.get("planet1") in wanted or item.get("planet2") in wanted
        ],
        "target_date": target_date,
    }
    if target_date:
        try:
            from engines.western import transit_hits

            timezone = (chart.get("calculation_profile") or {}).get("timezone", 8)
            facts["transit_hits"] = transit_hits(chart, target_date, tz=float(timezone or 8))[:8]
        except Exception:
            facts["transit_hits"] = []
    return {**_meta(chart), "scope": "natal-day-week", "facts": facts}


def build_chart_packet(profile: dict, topic: str, target_date: str | None = None) -> dict:
    """Build a compact, chart-only packet suitable for lower-cost models."""
    normalized = TOPIC_ALIASES.get(str(topic).strip(), str(topic).strip().lower() or "general")
    audit = audit_profile(profile)
    target_date = target_date or (profile.get("meta") or {}).get("calculated_for")
    from engines.chart_signals import build_topic_signals

    topic_signals = build_topic_signals(profile, normalized, target_date)
    return {
        "topic": normalized,
        "calculated_for": (profile.get("meta") or {}).get("calculated_for"),
        "audit": {
            "status": audit["status"],
            "issues": audit.get("issues", []),
        },
        "systems": {
            "bazi": _bazi_packet(profile.get("bazi") or {}),
            "ziwei": _ziwei_packet(profile.get("ziwei") or {}, normalized),
            "vedic": _vedic_packet(profile.get("vedic") or {}, normalized),
            "western": _western_packet(profile.get("western") or {}, normalized, target_date),
        },
        "topic_signals": topic_signals["signals"],
        "synthesis": topic_signals["synthesis"],
        "context_policy": "chart_only",
    }
