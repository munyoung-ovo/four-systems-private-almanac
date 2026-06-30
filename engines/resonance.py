
import json, os
from typing import Literal, Optional
from engines.calibration import apply_vote_calibration
from engines.daily import build as daily_build
from engines.personalize import _compute_flags, _precision_state, _yong_shen_reliable

Stance = Literal["favor", "neutral", "avoid"]

NAK_FAVOR = {
    "Rohini", "Hasta", "Pushya", "Uttara Phalguni",
    "Uttara Ashadha", "Uttara Bhadrapada", "Revati",
}
NAK_AVOID = {
    "Bharani", "Krittika", "Ardra", "Ashlesha",
    "Jyeshtha", "Mula",
}
YOGA_FAVOR = {"Saubhagya", "Shobhana", "Sukarman", "Dhriti", "Dhruva", "Siddhi", "Shiva", "Siddha", "Shubha", "Brahma", "Indra"}
YOGA_AVOID = {"Atiganda", "Shoola", "Ganda", "Vyaghata", "Vajra", "Vyatipata", "Parigha", "Vaidhriti"}
KARANA_AVOID = {"Vishti", "Shakuni", "Chatushpada", "Naga"}

MERCURY_RETROGRADE = [
    ("2026-02-26", "2026-03-20"),
    ("2026-06-30", "2026-07-23"),
    ("2026-10-24", "2026-11-13"),
]
_MERC_RETRO_CACHE: dict[str, bool] = {}

ACT_NAK_FAVOR: dict[str, set] = {
    "签约":  {"Rohini", "Uttara Phalguni", "Hasta"},
    "开业":  {"Rohini", "Uttara Ashadha", "Pushya"},
    "嫁娶":  {"Rohini", "Uttara Phalguni", "Uttara Bhadrapada"},
    "出行":  {"Hasta", "Revati", "Punarvasu"},
    "投资":  {"Pushya", "Uttara Ashadha", "Rohini"},
    "搬家":  {"Pushya", "Uttara Bhadrapada", "Rohini"},
    "求医":  {"Hasta", "Ashwini", "Pushya"},
    "祈福":  {"Pushya", "Rohini", "Revati"},
    "动土":  {"Uttara Ashadha", "Hasta"},
    "借贷":  set(),
}

SYSTEM_PRECISION = {
    "bazi":    "日级",
    "ziwei":   "年-月级",
    "vedic":   "日-时级",
    "western": "天级",
}

SYSTEM_SCOPE = {
    "bazi": "day",
    "ziwei": "year-month",
    "vedic": "day-hour",
    "western": "day-week",
}

def _vote(system: str, stance: Stance, basis: str, *,
          strength: float = 0.5, confidence: float = 0.7,
          scope: str | None = None, domain: list[str] | None = None,
          note: str | None = None) -> dict:
    out = {
        "stance": stance,
        "basis": basis,
        "system": system,
        "strength": round(max(0.0, min(1.0, strength)), 3),
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "scope": scope or SYSTEM_SCOPE.get(system, ""),
        "domain": domain or [],
    }
    if note:
        out["note"] = note
    return out

_CONFLICT_FRAME = {
    "timeframe": {
        "why_both": "大运是年-月级背景色，八字/Nakshatra 是日级节点——大势向好与某一天不佳并不矛盾。",
        "note":     "听日级（精度更高）：大方向可做，避开这一天的具体节点即可。",
    },
    "granularity": {
        "why_both": "粗粒度系统看整月框架，Nakshatra 看当日时辰——框架支持，只是当日某段时辰偏凶。",
        "note":     "大框架可动，用细粒度找吉时：当日月宿转换后（多在午后）再行动。",
    },
    "domain": {
        "why_both": "各系统擅长的维度不同，给的是不同属性的判断，并非对同一件事正面对立。",
        "note":     "按 act 最相关的系统权重排序：婚恋听 Nakshatra/金星，财务听八字/土星。",
    },
    "opposite": {
        "why_both": "两系统在同一维度对同一事给出相反信号——这通常意味着此事的能量对你格外强烈，而非单纯的吉或凶。",
        "note":     "信号真矛盾、本条置信度低：建议保守（延期或缩小规模），并以你的实际生活反馈为准。",
    },
}

def _mercury_retrograde_swe(date_str: str) -> Optional[bool]:
    try:
        import swisseph as swe
        from datetime import date as _date
        y, m, d = (int(x) for x in date_str.split("-"))
        jd = swe.julday(y, m, d, 12.0)
        res = swe.calc_ut(jd, swe.MERCURY, swe.FLG_SWIEPH | swe.FLG_SPEED)
        lon_speed = res[0][3]
        return lon_speed < 0
    except Exception:
        return None

def _is_mercury_retrograde(date_str: str) -> bool:
    if date_str in _MERC_RETRO_CACHE:
        return _MERC_RETRO_CACHE[date_str]
    val = _mercury_retrograde_swe(date_str)
    if val is None:
        val = any(start <= date_str <= end for start, end in MERCURY_RETROGRADE)
    _MERC_RETRO_CACHE[date_str] = val
    return val

def _vote_bazi(profile: dict, day: dict, act: str) -> dict:
    ganzhi = day["ganzhi"]
    day_gan = ganzhi["day"][0]
    day_zhi = ganzhi["day"][1]
    precision, hour_known = _precision_state(profile)
    bazi = profile.get("bazi", {})
    use_yong_shen = _yong_shen_reliable(bazi, hour_known)
    flags   = _compute_flags(day_gan, day_zhi, profile, use_yong_shen)
    shensha = day.get("shensha", [])
    confidence = 0.82 if precision == "exact" else 0.62 if precision == "hour" else 0.35
    if not use_yong_shen:
        confidence = min(confidence, 0.55)

    if flags["冲日主"] or flags["冲流年太岁"]:
        stance = "avoid"
        basis  = "日支冲日主或太岁"
        strength = 0.8
    elif any(s in ["三煞","岁煞","月煞","五黄"] for s in shensha):
        stance = "avoid"
        basis  = "三煞/岁煞到位"
        strength = 0.65
    elif flags["贵人到"] and flags["用神得力"]:
        stance = "favor"
        basis  = "天乙贵人到位、用神得令"
        strength = 0.85
    elif flags["用神得力"] or flags["贵人到"]:
        stance = "favor"
        basis  = "用神得力" if flags["用神得力"] else "贵人到位"
        strength = 0.65
    else:
        stance = "neutral"
        strength = 0.25
        basis  = "无明显吉凶神煞"
        if not use_yong_shen:
            basis += "；普通喜用神不稳，本票不采用用神得力"

    if act in ("出行", "旅行") and flags["驿马动"]:
        stance = "favor"
        basis  += "；驿马动利出行"
    if act in ("嫁娶",) and flags["桃花到"]:
        stance = "favor"
        basis  += "；桃花到位"
    if act in ("签约", "开业") and day["zhi_xing"] in ("成", "开"):
        if stance != "avoid":
            stance = "favor"
            basis  += f"；建除'{day['zhi_xing']}'利启动"
            strength = max(strength, 0.6)
    if act in ("动土",) and day["zhi_xing"] == "建":
        stance = "avoid"
        basis  = "建日忌动土"
        strength = 0.75

    return _vote("bazi", stance, basis, strength=strength,
                 confidence=confidence, domain=[act])

_ACT_ZIWEI_PALACE = {
    "签约": ["财帛", "官禄"], "投资": ["财帛", "官禄"], "开业": ["财帛", "官禄"],
    "纳财": ["财帛"], "借贷": ["财帛"], "诉讼": ["官禄"],
    "嫁娶": ["夫妻"], "纳采": ["夫妻"], "订盟": ["夫妻"],
    "出行": ["迁移"], "旅行": ["迁移"], "搬家": ["迁移"], "移徙": ["迁移"],
    "求医": ["疾厄"],
}
_ZIWEI_STATE_CACHE: dict[tuple, dict] = {}

def _ziwei_year_state(profile: dict, date_str: str) -> dict:
    meta = profile.get("meta", {})
    solar_birth = meta.get("solar_birth")
    gender      = meta.get("gender", "女")
    precision   = meta.get("time_precision", "exact")
    if not solar_birth:
        return {"degraded": True, "year_soul_stars": [], "transforms": []}
    key = (solar_birth, gender, precision, date_str[:4])
    if key not in _ZIWEI_STATE_CACHE:
        from engines.ziwei import year_horoscope_state
        try:
            _ZIWEI_STATE_CACHE[key] = year_horoscope_state(
                solar_birth, gender, date_str, precision)
        except Exception as e:
            _ZIWEI_STATE_CACHE[key] = {"degraded": True, "error": str(e),
                                       "year_soul_stars": [], "transforms": []}
    return _ZIWEI_STATE_CACHE[key]

def _vote_ziwei(profile: dict, day: dict, act: str) -> dict:
    state = _ziwei_year_state(profile, day["date"])

    if state.get("degraded"):
        return _vote("ziwei", "neutral",
                     "时辰未知，紫微流年宫位不可信，仅作背景信息",
                     strength=0.1, confidence=0.25, domain=[act],
                     note="紫微流年为年级背景，非日级判断")

    transforms = state.get("transforms", [])
    relevant = set(_ACT_ZIWEI_PALACE.get(act, []))

    benefic = [t for t in transforms if t["type"] in ("禄", "权", "科") and t["palace"] in relevant]
    ji      = [t for t in transforms if t["type"] == "忌" and t["palace"] in relevant]

    def _fmt(items):
        return "、".join(f"{t['star']}化{t['type']}入流年{t['palace']}" for t in items)

    soul = "·".join(state.get("year_soul_stars", [])) or "无主星"
    if not relevant:
        stance, basis, strength = "neutral", f"流年命宫坐{soul}（年级背景）；此事无对应流年宫，紫微不表态", 0.15
    elif ji and not benefic:
        stance, basis, strength = "avoid", f"流年{_fmt(ji)}，该宫宜守不宜进", 0.55
    elif benefic and not ji:
        stance, basis, strength = "favor", f"流年{_fmt(benefic)}，利{act}", 0.55
    elif benefic and ji:
        stance, basis, strength = "neutral", f"流年{_fmt(benefic)}，但{_fmt(ji)}，吉凶交叠", 0.35
    else:
        stance, basis, strength = "neutral", f"流年命宫坐{soul}（年级背景）；四化未落{'/'.join(relevant)}，紫微不表态", 0.2

    return _vote("ziwei", stance, basis, strength=strength,
                 confidence=0.58, domain=[act],
                 note="紫微流年为年级背景，非日级判断")

def _vote_vedic(profile: dict, day: dict, act: str) -> dict:
    panchanga = day.get("panchanga", {})
    nakshatra = panchanga.get("nakshatra", "")
    is_waxing = panchanga.get("is_waxing", True)
    yoga = panchanga.get("yoga", "")
    karana = panchanga.get("karana", "")

    act_fav = ACT_NAK_FAVOR.get(act, set())

    if nakshatra in NAK_AVOID:
        stance = "avoid"
        basis  = f"{nakshatra} 为凶宿，忌一切重要启动"
        strength = 0.75
    elif nakshatra in NAK_FAVOR or nakshatra in act_fav:
        stance = "favor"
        basis  = f"{nakshatra} 吉宿"
        strength = 0.7
        if nakshatra in act_fav:
            basis += f"，尤适合{act}"
            strength = 0.85
        if is_waxing:
            basis += "；月相上弦，能量上升"
    else:
        stance = "neutral"
        basis  = f"{nakshatra} 中性宿"
        strength = 0.25
        if not is_waxing:
            basis += "；月相下弦，适合收尾而非启动"

    if karana in KARANA_AVOID:
        stance = "avoid" if stance != "favor" else "neutral"
        basis += f"；{karana} Karana 不利正式启动"
        strength = max(strength, 0.65)
    elif yoga in YOGA_FAVOR and stance != "avoid":
        stance = "favor"
        basis += f"；{yoga} Yoga 加分"
        strength = max(strength, 0.65)
    elif yoga in YOGA_AVOID and stance == "neutral":
        stance = "avoid"
        basis += f"；{yoga} Yoga 偏阻"
        strength = max(strength, 0.55)

    return _vote("vedic", stance, basis, strength=strength,
                 confidence=0.75, domain=[act])

def _vote_western(profile: dict, day: dict, act: str) -> dict:
    western = profile.get("western", {})
    basis_data = western.get("western_basis") or {}
    precision = profile.get("meta", {}).get("time_precision", "unknown")
    confidence = 0.78 if precision == "exact" else 0.62 if precision == "hour" else 0.45

    void_moon = basis_data.get("void_moon") or {}
    if void_moon.get("is_void") and act in ("签约", "合同", "嫁娶", "出行", "旅行", "开业"):
        return _vote("western", "avoid",
                     f"月亮空亡，{act}类事项易缺少后续承接",
                     strength=0.6, confidence=min(confidence, 0.66), domain=[act])

    if act in ("签约", "合同") and _is_mercury_retrograde(day["date"]):
        return _vote("western", "avoid",
                     "水星逆行期间，签约/合同类事项易生反复",
                     strength=0.85, confidence=confidence, domain=[act])

    try:
        from engines.western import transit_hits
        hits = transit_hits(western, day["date"])
    except Exception:
        hits = []

    act_planets = {
        "签约": {"水星", "土星", "木星"},
        "合同": {"水星", "土星", "木星"},
        "开业": {"太阳", "木星", "土星", "火星"},
        "投资": {"金星", "木星", "土星"},
        "嫁娶": {"金星", "月亮", "木星"},
        "出行": {"月亮", "水星", "火星"},
        "旅行": {"月亮", "水星", "火星"},
    }.get(act, {"太阳", "月亮", "水星", "金星", "火星", "木星", "土星"})
    hard = {"四分", "对分"}
    soft = {"六合", "三合"}

    scored = []
    for h in hits:
        planet = h.get("transit_planet")
        if planet not in act_planets:
            continue
        aspect = h.get("aspect")
        strength = float(h.get("strength", 0))
        if h.get("phase") == "applying":
            strength = min(1.0, strength + 0.08)
        elif h.get("phase") == "separating":
            strength = max(0.0, strength - 0.08)
        if aspect in soft:
            scored.append((strength, "favor", h))
        elif aspect in hard:
            scored.append((strength, "avoid", h))
        elif aspect == "合相":
            if planet in {"木星", "金星"}:
                scored.append((strength, "favor", h))
            elif planet in {"土星", "火星"}:
                scored.append((strength, "avoid", h))

    if not scored:
        return _vote("western", "neutral", "行运无明显相关相位",
                     strength=0.15, confidence=confidence, domain=[act])

    scored.sort(key=lambda x: -x[0])
    strength, stance, hit = scored[0]
    basis = (f"{hit['transit_planet']}行运{hit['aspect']}本命{hit['natal_point']}"
             f"（容许度{hit['orb']}°）")
    if hit.get("phase") == "applying":
        basis += "；相位正在逼近"
    elif hit.get("phase") == "separating":
        basis += "；相位已经分离"
    if hit.get("transit_retrograde"):
        confidence = min(confidence, 0.68)
        basis += "；行星逆行，结果易反复"
    return _vote("western", stance, basis, strength=strength,
                 confidence=confidence, domain=[act])

def _classify_conflict(votes: list[dict]) -> dict | None:
    stances = [v["stance"] for v in votes]
    if "avoid" not in stances:
        return None

    favors = sum(1 for s in stances if s == "favor")
    avoids = sum(1 for s in stances if s == "avoid")
    if avoids == 0:
        return None

    avoid_systems = [v.get("system", "?") for v in votes if v["stance"] == "avoid"]

    if "ziwei" in avoid_systems and favors >= 2:
        ctype = "timeframe"
    elif avoids >= 2 and favors >= 2:
        ctype = "opposite"
    elif "vedic" in avoid_systems and favors >= 2:
        ctype = "granularity"
    else:
        ctype = "domain"

    frame = _CONFLICT_FRAME[ctype]
    return {
        "type":          ctype,
        "note":          frame["note"],
        "why_both":      frame["why_both"],
        "avoid_systems": avoid_systems,
    }

def analyze_date(profile: dict, act: str, date_str: str) -> dict:
    day   = daily_build(date_str)
    votes_raw = [
        apply_vote_calibration(_vote_bazi(profile, day, act), profile, act),
        apply_vote_calibration(_vote_ziwei(profile, day, act), profile, act),
        apply_vote_calibration(_vote_vedic(profile, day, act), profile, act),
        apply_vote_calibration(_vote_western(profile, day, act), profile, act),
    ]

    votes = {
        "bazi":    votes_raw[0],
        "ziwei":   votes_raw[1],
        "vedic":   votes_raw[2],
        "western": votes_raw[3],
    }

    aligned_favor     = sum(1 for v in votes_raw if v["stance"] == "favor")
    conflict          = _classify_conflict(votes_raw)
    is_destined       = aligned_favor == 4
    weighted_raw = 0.0
    weight_total = 0.0
    stance_score = {"favor": 1.0, "neutral": 0.0, "avoid": -1.0}
    for v in votes_raw:
        weight = float(v.get("strength", 0.5)) * float(v.get("confidence", 0.7))
        weighted_raw += stance_score[v["stance"]] * weight
        weight_total += weight
    weighted_score = round(weighted_raw / weight_total, 3) if weight_total else 0.0

    return {
        "date":              date_str,
        "act":               act,
        "votes":             {k: {"stance": v["stance"], "basis": v["basis"],
                                   "precision": SYSTEM_PRECISION.get(k, ""),
                                   "scope": v.get("scope", SYSTEM_SCOPE.get(k, "")),
                                   "strength": v.get("strength", 0.5),
                                   "confidence": v.get("confidence", 0.7),
                                   "domain": v.get("domain", [])}
                              for k, v in votes.items()},
        "aligned_favor":     aligned_favor,
        "resonance_strength": aligned_favor,
        "weighted_score":    weighted_score,
        "conflict":          conflict,
        "is_destined_moment": is_destined,
    }

def find_best_dates(
    profile: dict,
    act: str,
    candidate_dates: list[str],
) -> list[dict]:
    results = []
    for d in candidate_dates:
        try:
            r = analyze_date(profile, act, d)
            results.append(r)
        except Exception as e:
            results.append({"date": d, "act": act, "error": str(e)})

    results.sort(key=lambda x: x.get("resonance_strength", -1), reverse=True)
    return results

