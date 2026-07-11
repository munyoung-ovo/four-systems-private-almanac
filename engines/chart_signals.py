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
            source_fields: list[str], components: list[dict] | None = None) -> dict:
    return {
        "system": system,
        "topic": topic,
        "direction": direction,
        "strength": round(max(0.0, min(1.0, strength)), 3),
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "scope": scope,
        "basis": basis,
        "source_fields": source_fields,
        "components": components or [],
    }


def _direction_from_score(score: float, threshold: float = 0.2) -> str:
    if score >= threshold:
        return "support"
    if score <= -threshold:
        return "pressure"
    return "mixed"


def _component(label: str, direction: str, weight: float, detail: str) -> dict:
    return {"label": label, "direction": direction, "weight": weight, "detail": detail}


def _combine_components(components: list[dict]) -> tuple[str, float, float]:
    signed = {"support": 1.0, "pressure": -1.0, "mixed": 0.0}
    total = sum(abs(float(c["weight"])) for c in components) or 1.0
    score = sum(signed.get(c["direction"], 0.0) * float(c["weight"]) for c in components) / total
    direction = _direction_from_score(score)
    strength = min(0.9, 0.35 + abs(score) * 0.55)
    return direction, round(score, 3), round(strength, 3)


def _bazi_signals(profile: dict, topic: str) -> list[dict]:
    chart = profile.get("bazi") or {}
    if not chart:
        return []
    luck = chart.get("luck") or {}
    current = luck.get("current_dayun") or {}
    liunian = luck.get("current_liunian") or {}
    dayun_gods = {current.get("gan_shi_shen"), current.get("zhi_shi_shen")} - {None, ""}
    year_gods = {liunian.get("gan_shi_shen")} - {None, ""}
    rules = BAZI_GODS.get(topic)
    if topic == "love":
        spouse = {"正财", "偏财"} if (profile.get("meta") or {}).get("gender") == "男" else {"正官", "七杀"}
        rules = {"support": spouse, "pressure": {"比肩", "劫财", "伤官"}}
    if not rules or not (dayun_gods or year_gods):
        return []

    components = []
    for label, gods, weight in (("大运", dayun_gods, 0.65), ("流年", year_gods, 0.35)):
        support = sorted(gods & rules["support"])
        pressure = sorted(gods & rules["pressure"])
        direction = "mixed" if support and pressure else "support" if support else "pressure" if pressure else "mixed"
        matched = support + pressure or sorted(gods)
        if matched:
            components.append(_component(label, direction, weight, f"{label}十神为{'、'.join(matched)}"))
    direction, _, strength = _combine_components(components)
    reliability = float(chart.get("strength_confidence") or 0.5)
    if chart.get("special_pattern"):
        reliability = min(reliability, 0.45)
        direction = "mixed"
        strength = min(strength, 0.4)
    basis = "；".join(c["detail"] for c in components)
    return [_signal(
        "bazi", topic, direction,
        basis,
        strength=strength,
        confidence=min(_confidence(chart), reliability, 0.72),
        scope="period-year",
        source_fields=["bazi.luck.current_dayun", "bazi.luck.current_liunian", "bazi.strength_confidence", "bazi.special_pattern"],
        components=components,
    )]


def _ziwei_signals(profile: dict, topic: str) -> list[dict]:
    chart = profile.get("ziwei") or {}
    palaces = ((chart.get("ziwei_basis") or {}).get("topic_index") or {}).get(topic, [])
    if not palaces:
        return []
    qualities = [(p.get("strength") or {}).get("quality") for p in palaces]
    supported = qualities.count("supported")
    pressured = qualities.count("pressured")
    names = [p.get("normalized_name") or p.get("name") for p in palaces if p.get("name")]
    magnitude = max(supported, pressured) / max(1, len(palaces))
    natal_direction = "mixed" if supported and pressured else "support" if supported else "pressure" if pressured else "mixed"
    components = [_component("本命宫位", natal_direction, 0.45, f"专题宫位为{'、'.join(names)}，结构{DIRECTION_LABELS[natal_direction]}")]

    relevant_names = set(names)
    summaries = (chart.get("horoscope_layers") or {}).get("summary") or {}
    for layer_name, layer_weight, label in (("yearly", 0.35, "流年"), ("monthly", 0.20, "流月")):
        transforms = (summaries.get(layer_name) or {}).get("transform_by_type") or {}
        def _in_topic(transform: dict) -> bool:
            palace = str(transform.get("flow_palace") or "")
            normalized = palace if palace.endswith("宫") else f"{palace}宫"
            return normalized in relevant_names

        support_types = [t for t in ("禄", "权", "科") if _in_topic(transforms.get(t) or {})]
        pressure_types = [t for t in ("忌",) if _in_topic(transforms.get(t) or {})]
        if support_types or pressure_types:
            layer_direction = "mixed" if support_types and pressure_types else "support" if support_types else "pressure"
            marks = support_types + pressure_types
            components.append(_component(label, layer_direction, layer_weight, f"{label}{'、'.join(marks)}进入相关宫位"))

    direction, _, strength = _combine_components(components)
    return [_signal(
        "ziwei", topic, direction,
        "；".join(c["detail"] for c in components),
        strength=max(strength, min(0.7, 0.35 + magnitude * 0.3)),
        confidence=_confidence(chart, 0.82),
        scope="natal-year-month",
        source_fields=[f"ziwei.ziwei_basis.topic_index.{topic}", "ziwei.horoscope_layers.summary.yearly", "ziwei.horoscope_layers.summary.monthly"],
        components=components,
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
    detail = "、".join(f"第{house}宫{value:g}点" for house, value in values)
    sav_direction = "support" if average >= 30 else "pressure" if average <= 25 else "mixed"
    components = [_component("相关宫位", sav_direction, 0.45, f"相关宫位八分图为{detail}")]

    basis = chart.get("jyotish_basis") or {}
    planets = basis.get("planets") or {}
    dignity = basis.get("dignity") or {}
    combustion = basis.get("combustion") or {}
    dasha = chart.get("vimshottari") or {}
    for label, planet, weight in (
        ("大运", dasha.get("current_mahadasha") or dasha.get("mahadasha"), 0.35),
        ("分运", (dasha.get("current_antardasha") or {}).get("planet"), 0.20),
    ):
        pdata = planets.get(planet) or {}
        if not planet or not pdata:
            continue
        house = pdata.get("house")
        level = (dignity.get(planet) or {}).get("level")
        if house in houses_by_topic.get(topic, ()):
            d = "support"
        elif level == "debilitated" or planet in combustion:
            d = "pressure"
        elif level in {"exalted", "own_sign"}:
            d = "support"
        else:
            d = "mixed"
        notes = [f"{label}主星{planet}落第{house}宫"]
        if level and level != "neutral":
            notes.append(level)
        if planet in combustion:
            notes.append("燃烧")
        components.append(_component(label, d, weight, "，".join(notes)))

    direction, _, strength = _combine_components(components)
    return [_signal(
        "vedic", topic, direction,
        "；".join(c["detail"] for c in components),
        strength=strength,
        confidence=_confidence(chart, 0.82),
        scope="natal-period",
        source_fields=["vedic.ashtakavarga.sav_by_house", "vedic.vimshottari", "vedic.jyotish_basis.planets", "vedic.jyotish_basis.dignity", "vedic.jyotish_basis.combustion"],
        components=components,
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
    components = []
    for hit in hits[:3]:
        direction = WESTERN_ASPECTS.get(hit.get("aspect"), "mixed")
        phase = "逼近" if hit.get("phase") == "applying" else "分离"
        weight = float(hit.get("strength", 0.5)) * (1.0 if hit.get("phase") == "applying" else 0.75)
        components.append(_component(
            "行运相位", direction, weight,
            f"{hit.get('transit_planet')}与本命{hit.get('natal_point')}形成{hit.get('aspect')}，相位{phase}",
        ))
    direction, _, strength = _combine_components(components)
    confidence = _confidence(chart, 0.82)
    if components and all("分离" in c["detail"] for c in components):
        confidence *= 0.85
    return [_signal(
        "western", topic, direction,
        "；".join(c["detail"] for c in components),
        strength=strength,
        confidence=confidence,
        scope="day-week",
        source_fields=["western.transit_hits"],
        components=components,
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
