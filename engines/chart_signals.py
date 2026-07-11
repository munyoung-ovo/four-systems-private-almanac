from __future__ import annotations


TOPIC_ALIASES = {
    "感情": "love", "love": "love",
    "事业": "career", "career": "career",
    "财运": "wealth", "wealth": "wealth",
    "健康": "health", "health": "health",
    "贵人": "support", "support": "support",
}

TOPIC_WEIGHTS = {
    "love": {"bazi": 0.25, "ziwei": 0.30, "vedic": 0.20, "western": 0.25},
    "career": {"bazi": 0.30, "ziwei": 0.30, "vedic": 0.20, "western": 0.20},
    "wealth": {"bazi": 0.30, "ziwei": 0.25, "vedic": 0.25, "western": 0.20},
    "health": {"bazi": 0.25, "ziwei": 0.25, "vedic": 0.25, "western": 0.25},
    "support": {"bazi": 0.20, "ziwei": 0.30, "vedic": 0.20, "western": 0.30},
}

BAZI_GODS = {
    "career": {
        "support": {"正官", "正印", "偏印", "食神"},
        "pressure": {"七杀", "劫财"},
    },
    "wealth": {
        "support": {"正财", "偏财", "食神", "伤官"},
        "pressure": {"比肩", "劫财"},
    },
    "health": {
        "support": {"正印", "偏印", "食神"},
        "pressure": {"七杀", "伤官"},
    },
    "support": {
        "support": {"正印", "偏印", "正官"},
        "pressure": {"劫财", "七杀"},
    },
}

WESTERN_ASPECTS = {
    "三分相": "support", "三合": "support", "六合相": "support",
    "六合": "support", "六分相": "support", "四分相": "pressure",
    "四分": "pressure", "刑相": "pressure", "对分相": "pressure",
    "对分": "pressure", "冲相": "pressure", "合相": "mixed",
}

WESTERN_TOPIC_POINTS = {
    "love": {"月亮", "金星", "火星"},
    "career": {"太阳", "天顶"},
    "wealth": {"金星"},
    "health": {"月亮", "火星"},
    "support": {"太阳", "上升"},
}

DIRECTION_LABELS = {
    "support": "有支撑",
    "pressure": "承压",
    "mixed": "支撑与压力并存",
}


def _confidence(chart: dict, cap: float = 1.0) -> float:
    value = float((chart.get("calculation_profile") or {}).get("confidence_score", 0.5))
    return round(max(0.0, min(cap, value)), 3)


def _signal(system: str, topic: str, direction: str, basis: str, *,
            strength: float, confidence: float, scope: str,
            source_fields: list[str]) -> dict:
    return {
        "system": system,
        "topic": topic,
        "direction": direction,
        "strength": round(max(0.0, min(1.0, strength)), 3),
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "scope": scope,
        "basis": basis,
        "source_fields": source_fields,
    }


def _bazi_signals(profile: dict, topic: str) -> list[dict]:
    chart = profile.get("bazi") or {}
    if not chart:
        return []
    current = (chart.get("luck") or {}).get("current_dayun") or {}
    gods = {current.get("gan_shi_shen"), current.get("zhi_shi_shen")} - {None, ""}
    rules = BAZI_GODS.get(topic)
    if topic == "love":
        spouse = {"正财", "偏财"} if (profile.get("meta") or {}).get("gender") == "男" else {"正官", "七杀"}
        rules = {"support": spouse, "pressure": {"比肩", "劫财", "伤官"}}
    if not rules or not gods:
        return []

    support = sorted(gods & rules["support"])
    pressure = sorted(gods & rules["pressure"])
    direction = "mixed" if support and pressure else "support" if support else "pressure" if pressure else "mixed"
    matched = support + pressure or sorted(gods)
    reliability = float(chart.get("strength_confidence") or 0.5)
    if chart.get("special_pattern"):
        reliability = min(reliability, 0.45)
        direction = "mixed"
    return [_signal(
        "bazi", topic, direction,
        f"当前大运十神主题为{'、'.join(matched)}",
        strength=0.62 if direction != "mixed" else 0.4,
        confidence=min(_confidence(chart), reliability, 0.72),
        scope="period-year",
        source_fields=["bazi.luck.current_dayun", "bazi.strength_confidence", "bazi.special_pattern"],
    )]


def _ziwei_signals(profile: dict, topic: str) -> list[dict]:
    chart = profile.get("ziwei") or {}
    palaces = ((chart.get("ziwei_basis") or {}).get("topic_index") or {}).get(topic, [])
    if not palaces:
        return []
    qualities = [(p.get("strength") or {}).get("quality") for p in palaces]
    supported = qualities.count("supported")
    pressured = qualities.count("pressured")
    direction = "mixed" if supported and pressured else "support" if supported else "pressure" if pressured else "mixed"
    names = [p.get("normalized_name") or p.get("name") for p in palaces if p.get("name")]
    magnitude = max(supported, pressured) / max(1, len(palaces))
    return [_signal(
        "ziwei", topic, direction,
        f"专题宫位为{'、'.join(names)}，宫位结构{DIRECTION_LABELS[direction]}",
        strength=max(0.35, min(0.8, magnitude)),
        confidence=_confidence(chart, 0.82),
        scope="natal-year-month",
        source_fields=[f"ziwei.ziwei_basis.topic_index.{topic}"],
    )]


def _vedic_signals(profile: dict, topic: str) -> list[dict]:
    chart = profile.get("vedic") or {}
    houses_by_topic = {
        "love": (7,), "career": (10,), "wealth": (2, 11),
        "health": (6, 8), "support": (9, 11),
    }
    sav = (chart.get("ashtakavarga") or {}).get("sav_by_house") or {}
    values = []
    for house in houses_by_topic.get(topic, ()):
        item = sav.get(house) or sav.get(str(house)) or {}
        if isinstance(item.get("value"), (int, float)):
            values.append((house, float(item["value"])))
    if not values:
        return []
    average = sum(value for _, value in values) / len(values)
    direction = "support" if average >= 30 else "pressure" if average <= 25 else "mixed"
    strength = min(0.85, 0.35 + abs(average - 27.5) / 12)
    detail = "、".join(f"第{house}宫{value:g}点" for house, value in values)
    return [_signal(
        "vedic", topic, direction,
        f"相关宫位八分图为{detail}",
        strength=strength,
        confidence=_confidence(chart, 0.82),
        scope="natal-period",
        source_fields=["vedic.ashtakavarga.sav_by_house", "vedic.vimshottari.target_date"],
    )]


def _western_signals(profile: dict, topic: str, target_date: str | None) -> list[dict]:
    chart = profile.get("western") or {}
    if not chart or not target_date:
        return []
    try:
        from engines.western import transit_hits

        timezone = (chart.get("calculation_profile") or {}).get("timezone", 8)
        hits = transit_hits(chart, target_date, tz=float(timezone or 8))
    except Exception:
        return []
    relevant_points = WESTERN_TOPIC_POINTS.get(topic, set())
    hits = [hit for hit in hits if hit.get("natal_point") in relevant_points]
    if not hits:
        return []
    hit = hits[0]
    direction = WESTERN_ASPECTS.get(hit.get("aspect"), "mixed")
    phase = "逼近" if hit.get("phase") == "applying" else "分离"
    confidence = _confidence(chart, 0.82)
    if hit.get("phase") == "separating":
        confidence *= 0.85
    return [_signal(
        "western", topic, direction,
        f"{hit.get('transit_planet')}与本命{hit.get('natal_point')}形成{hit.get('aspect')}，相位{phase}",
        strength=float(hit.get("strength", 0.5)),
        confidence=confidence,
        scope="day-week",
        source_fields=["western.transit_hits"],
    )]


def _synthesize(signals: list[dict], topic: str) -> dict:
    weights = TOPIC_WEIGHTS.get(topic, {s: 0.25 for s in ("bazi", "ziwei", "vedic", "western")})
    score_map = {"support": 1.0, "pressure": -1.0}
    usable = [s for s in signals if s["direction"] in score_map]
    if not usable:
        return {
            "direction": "insufficient",
            "score": 0.0,
            "confidence": 0.0,
            "conflict": False,
            "support_systems": [],
            "pressure_systems": [],
            "grade": "insufficient",
            "system_count": 0,
        }
    effective = [
        weights.get(s["system"], 0.25) * s["strength"] * s["confidence"]
        for s in usable
    ]
    total = sum(effective) or 1.0
    score = sum(score_map[s["direction"]] * w for s, w in zip(usable, effective)) / total
    support = [s["system"] for s in usable if s["direction"] == "support"]
    pressure = [s["system"] for s in usable if s["direction"] == "pressure"]
    direction = "support" if score >= 0.2 else "pressure" if score <= -0.2 else "mixed"
    confidence = sum(s["confidence"] * w for s, w in zip(usable, effective)) / total
    if support and pressure:
        confidence *= 0.85
    system_count = len({s["system"] for s in usable})
    if system_count >= 2 and confidence >= 0.75 and not (support and pressure):
        grade = "strong"
    elif system_count >= 2:
        grade = "moderate"
    else:
        grade = "limited"
    return {
        "direction": direction,
        "score": round(score, 3),
        "confidence": round(confidence, 3),
        "conflict": bool(support and pressure),
        "support_systems": support,
        "pressure_systems": pressure,
        "grade": grade,
        "system_count": system_count,
    }


def build_topic_signals(profile: dict, topic: str, target_date: str | None = None) -> dict:
    normalized = TOPIC_ALIASES.get(str(topic).strip(), str(topic).strip().lower())
    target_date = target_date or (profile.get("meta") or {}).get("calculated_for")
    signals = [
        *_bazi_signals(profile, normalized),
        *_ziwei_signals(profile, normalized),
        *_vedic_signals(profile, normalized),
        *_western_signals(profile, normalized, target_date),
    ]
    return {
        "topic": normalized,
        "target_date": target_date,
        "signals": signals,
        "synthesis": _synthesize(signals, normalized),
    }
