
import swisseph as swe
from typing import Literal
from models.profile import CalculationProfile, CalendarType, EvidenceLevel, TimePrecision

TIME_PRECISION = Literal["exact", "hour", "unknown"]

PLANETS = [
    (swe.SUN,     "太阳"),
    (swe.MOON,    "月亮"),
    (swe.MERCURY, "水星"),
    (swe.VENUS,   "金星"),
    (swe.MARS,    "火星"),
    (swe.JUPITER, "木星"),
    (swe.SATURN,  "土星"),
    (swe.URANUS,  "天王星"),
    (swe.NEPTUNE, "海王星"),
    (swe.PLUTO,   "冥王星"),
]

SIGNS_ZH = [
    "白羊", "金牛", "双子", "巨蟹", "狮子", "处女",
    "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼",
]

ASPECTS = [
    (0,   8, "合相"),
    (60,  6, "六合"),
    (90,  8, "四分"),
    (120, 8, "三合"),
    (150, 3, "梅花"),
    (180, 8, "对分"),
]

TRADITIONAL_PLANETS = {"太阳", "月亮", "水星", "金星", "火星", "木星", "土星"}

SIGN_RULERS = {
    "白羊": "火星", "金牛": "金星", "双子": "水星", "巨蟹": "月亮",
    "狮子": "太阳", "处女": "水星", "天秤": "金星", "天蝎": "火星",
    "射手": "木星", "摩羯": "土星", "水瓶": "土星", "双鱼": "木星",
}

EXALTATION = {
    "太阳": "白羊", "月亮": "金牛", "水星": "处女", "金星": "双鱼",
    "火星": "摩羯", "木星": "巨蟹", "土星": "天秤",
}

HOUSE_TOPICS = {
    1: "自我/身体", 2: "财务/资源", 3: "沟通/短途", 4: "家庭/根基",
    5: "恋爱/创作", 6: "工作/健康", 7: "关系/合作", 8: "共享资源/风险",
    9: "远行/学习", 10: "事业/名望", 11: "社群/收益", 12: "隐秘/消耗",
}

def _jd_utc(solar_dt: str, time_precision: TIME_PRECISION,
            tz: float = 8) -> float:
    from datetime import datetime
    dt = datetime.fromisoformat(solar_dt)
    if time_precision == "unknown":
        dt = dt.replace(hour=0, minute=0, second=0)
    utc_hour = (dt.hour + dt.minute / 60) - tz
    return swe.julday(dt.year, dt.month, dt.day, utc_hour)

def _sign(lon: float) -> str:
    return SIGNS_ZH[int(lon / 30) % 12]

def _degree_in_sign(lon: float) -> float:
    return round(lon % 30, 2)

def _zodiac_delta(a: float, b: float) -> float:
    return (a - b) % 360

def _aspect_diff(lon1: float, lon2: float) -> float:
    diff = abs(lon1 - lon2) % 360
    return 360 - diff if diff > 180 else diff

def _house_of(lon: float, cusps: list[float] | None) -> int | None:
    if not cusps or len(cusps) != 12:
        return None
    lon = lon % 360
    for idx in range(12):
        start = cusps[idx] % 360
        end = cusps[(idx + 1) % 12] % 360
        if start <= end:
            inside = start <= lon < end
        else:
            inside = lon >= start or lon < end
        if inside:
            return idx + 1
    return None

def _opposite_sign(sign: str) -> str | None:
    if sign not in SIGNS_ZH:
        return None
    return SIGNS_ZH[(SIGNS_ZH.index(sign) + 6) % 12]

def _dignity(planet: str, sign: str) -> dict:
    tags = []
    ruler = SIGN_RULERS.get(sign)
    exalted = EXALTATION.get(planet)
    if ruler == planet:
        tags.append("入庙")
    if exalted == sign:
        tags.append("擢升")
    if _opposite_sign(exalted) == sign:
        tags.append("失势")
    ruled_signs = [s for s, r in SIGN_RULERS.items() if r == planet]
    if any(_opposite_sign(s) == sign for s in ruled_signs):
        tags.append("落陷")
    score = 0
    if "入庙" in tags:
        score += 2
    if "擢升" in tags:
        score += 2
    if "失势" in tags:
        score -= 2
    if "落陷" in tags:
        score -= 2
    return {"ruler": ruler, "tags": tags, "score": score}

def _moon_phase(sun_lon: float | None, moon_lon: float | None) -> dict | None:
    if sun_lon is None or moon_lon is None:
        return None
    elongation = _zodiac_delta(moon_lon, sun_lon)
    phases = [
        (0, "新月"), (45, "眉月"), (90, "上弦"), (135, "盈凸"),
        (180, "满月"), (225, "亏凸"), (270, "下弦"), (315, "残月"),
    ]
    nearest = min(phases, key=lambda p: min(abs(elongation - p[0]), 360 - abs(elongation - p[0])))
    return {
        "elongation": round(elongation, 2),
        "phase": nearest[1],
        "waxing": 0 < elongation < 180,
    }

def _library_layer() -> dict:
    try:
        import flatlib  # type: ignore
        version = getattr(flatlib, "__version__", "") or getattr(flatlib, "VERSION", "")
        return {"available": True, "package": "flatlib", "version": str(version or "installed")}
    except Exception:
        return {
            "available": False,
            "package": "flatlib",
            "reason": "optional_dependency_not_available",
        }

def _find_aspects(positions: dict[str, float], speeds: dict[str, float] | None = None) -> list[dict]:
    planets = list(positions.items())
    result = []
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1, lon1 = planets[i]
            p2, lon2 = planets[j]
            diff = _aspect_diff(lon1, lon2)
            for angle, orb, name in ASPECTS:
                if abs(diff - angle) <= orb:
                    exact_orb = round(abs(diff - angle), 2)
                    phase = None
                    if speeds and speeds.get(p1) is not None and speeds.get(p2) is not None:
                        future = _aspect_diff(lon1 + speeds[p1] * 0.25, lon2 + speeds[p2] * 0.25)
                        phase = "applying" if abs(future - angle) < abs(diff - angle) else "separating"
                    result.append({
                        "planet1": p1,
                        "planet2": p2,
                        "aspect":  name,
                        "angle":   round(diff, 2),
                        "orb":     exact_orb,
                        "orb_limit": orb,
                        "strength": round(max(0, 1 - exact_orb / orb), 3),
                        "phase": phase,
                    })
                    break
    return result

def _aspect_to_angle(diff: float) -> tuple[str, float, float] | None:
    for angle, orb, name in ASPECTS:
        exact_orb = abs(diff - angle)
        if exact_orb <= orb:
            return name, angle, exact_orb
    return None

def _void_moon_status(positions: dict[str, float], speeds: dict[str, float]) -> dict:
    moon_lon = positions.get("月亮")
    moon_speed = speeds.get("月亮")
    if moon_lon is None or not moon_speed or moon_speed <= 0:
        return {"available": False, "reason": "moon_position_unavailable"}

    sign_end = (int(moon_lon / 30) + 1) * 30
    remaining = (sign_end - moon_lon) % 360
    if remaining == 0:
        remaining = 30
    days_left = remaining / moon_speed
    candidates = []
    for name, lon in positions.items():
        if name == "月亮" or name not in TRADITIONAL_PLANETS or lon is None:
            continue
        rel_speed = moon_speed - (speeds.get(name) or 0)
        if rel_speed <= 0:
            continue
        start = _zodiac_delta(moon_lon, lon)
        for angle, _, aspect_name in ASPECTS:
            if angle == 150:
                continue
            target = angle
            distance = (target - start) % 360
            days = distance / rel_speed
            if 0 < days <= days_left:
                candidates.append({
                    "planet": name,
                    "aspect": aspect_name,
                    "days_until_exact": round(days, 3),
                })
    candidates.sort(key=lambda x: x["days_until_exact"])
    return {
        "available": True,
        "is_void": len(candidates) == 0,
        "moon_sign": _sign(moon_lon),
        "degrees_until_sign_change": round(remaining, 2),
        "next_applying_aspect": candidates[0] if candidates else None,
    }

def _western_basis(planet_positions: dict, positions: dict[str, float],
                   speeds: dict[str, float], house_cusps: list[float] | None,
                   time_precision: TIME_PRECISION, house_system: str) -> dict:
    planets = {}
    for name, data in planet_positions.items():
        house = _house_of(data["longitude"], house_cusps)
        dignity = _dignity(name, data["sign"]) if name in TRADITIONAL_PLANETS else {
            "ruler": SIGN_RULERS.get(data["sign"]),
            "tags": [],
            "score": 0,
        }
        planets[name] = {
            **data,
            "house": house,
            "house_topic": HOUSE_TOPICS.get(house),
            "dignity": dignity,
        }

    sun_house = planets.get("太阳", {}).get("house")
    moon = _moon_phase(positions.get("太阳"), positions.get("月亮"))
    return {
        "available": True,
        "precision": "minute" if time_precision == "exact" else "hour" if time_precision == "hour" else "date",
        "zodiac": "tropical",
        "house_system": house_system,
        "houses_available": bool(house_cusps and time_precision == "exact"),
        "library_layer": _library_layer(),
        "planets": planets,
        "sect": {
            "available": sun_house is not None,
            "type": "day" if sun_house in (7, 8, 9, 10, 11, 12) else "night" if sun_house else None,
            "sun_house": sun_house,
        },
        "moon_phase": moon,
        "void_moon": _void_moon_status(positions, speeds),
        "validation": {
            "asc_mc_requires_exact_time": time_precision == "exact",
            "house_cusps_count": len(house_cusps or []),
            "planet_count": len(planets),
        },
    }

def build(solar_dt: str, gender: str,
          lat: float = 31.23, lon_geo: float = 121.47,
          time_precision: TIME_PRECISION = "exact",
          tz: float = 8) -> dict:
    jd = _jd_utc(solar_dt, time_precision, tz)

    positions = {}
    speeds = {}
    for planet_id, name in PLANETS:
        try:
            result, _ = swe.calc_ut(jd, planet_id, swe.FLG_SPEED)
            positions[name] = result[0]
            speeds[name] = result[3]
        except Exception:
            positions[name] = None
            speeds[name] = None

    house_system = "Placidus"
    asc_lon = mc_lon = asc_sign = mc_sign = house_cusps = None
    if time_precision == "exact":
        try:
            cusps, ascmc = swe.houses(jd, lat, lon_geo, b'P')
            asc_lon  = ascmc[0]
            mc_lon   = ascmc[1]
            asc_sign = _sign(asc_lon)
            mc_sign  = _sign(mc_lon)
            house_cusps = [round(c, 2) for c in cusps]
        except Exception:
            asc_lon = mc_lon = asc_sign = mc_sign = house_cusps = None

    planet_positions = {}
    for name, lon in positions.items():
        if lon is not None:
            planet_positions[name] = {
                "longitude": round(lon, 4),
                "sign":      _sign(lon),
                "degree":    _degree_in_sign(lon),
                "speed":     round(speeds[name], 6) if speeds.get(name) is not None else None,
                "retrograde": bool(speeds.get(name) is not None and speeds[name] < 0),
            }

    valid_pos = {k: v for k, v in positions.items() if v is not None}
    valid_speeds = {k: v for k, v in speeds.items() if v is not None}
    natal_aspects = _find_aspects(valid_pos, valid_speeds)
    western_basis = _western_basis(
        planet_positions, valid_pos, valid_speeds, house_cusps,
        time_precision, house_system,
    )

    result = {
        "sun":       planet_positions.get("太阳", {}).get("sign"),
        "moon":      planet_positions.get("月亮", {}).get("sign"),
        "ascendant": asc_sign,
        "ascendant_longitude": round(asc_lon, 4) if asc_lon is not None else None,
        "mc":        mc_sign if time_precision == "exact" else None,
        "mc_longitude": round(mc_lon, 4) if time_precision == "exact" and mc_lon is not None else None,
        "planets":   planet_positions,
        "western_basis": western_basis,
        "natal_aspects": natal_aspects,
        "house_cusps":   house_cusps,
        "house_system":  house_system,
        "calculation_profile": CalculationProfile(
            calendar_type=CalendarType.SOLAR,
            is_true_solar_time=False,
            time_precision=(
                TimePrecision.MINUTE if time_precision == "exact"
                else TimePrecision.HOUR if time_precision == "hour"
                else TimePrecision.UNKNOWN
            ),
            longitude=lon_geo,
            latitude=lat,
            timezone=tz,
            confidence_score=0.9 if time_precision == "exact" else 0.72 if time_precision == "hour" else 0.4,
            evidence_level=EvidenceLevel.HIGH if time_precision == "exact" else EvidenceLevel.MEDIUM if time_precision == "hour" else EvidenceLevel.LOW,
            warnings=[] if time_precision == "exact" else ["出生时间非分钟级，上升、天顶与宫位判断降级"],
        ).to_dict(),
        "degraded":  time_precision == "unknown",
    }
    return result

def transit_hits(western_chart: dict, date_str: str, tz: float = 8) -> list[dict]:
    jd = _jd_utc(f"{date_str}T12:00:00", "exact", tz)
    natal_points = {
        name: data["longitude"]
        for name, data in (western_chart.get("planets") or {}).items()
        if data.get("longitude") is not None
    }
    if western_chart.get("ascendant_longitude") is not None:
        natal_points["上升"] = western_chart["ascendant_longitude"]
    if western_chart.get("mc_longitude") is not None:
        natal_points["天顶"] = western_chart["mc_longitude"]

    focus = {"太阳", "月亮", "金星", "火星", "上升", "天顶"}
    natal_points = {k: v for k, v in natal_points.items() if k in focus}

    hits = []
    for planet_id, transit_name in PLANETS:
        res, _ = swe.calc_ut(jd, planet_id, swe.FLG_SPEED)
        transit_lon = res[0]
        for natal_name, natal_lon in natal_points.items():
            diff = abs(transit_lon - natal_lon) % 360
            if diff > 180:
                diff = 360 - diff
            hit = _aspect_to_angle(diff)
            if not hit:
                continue
            aspect, angle, orb = hit
            future_diff = _aspect_diff(transit_lon + res[3] * 0.25, natal_lon)
            phase = "applying" if abs(future_diff - angle) < abs(diff - angle) else "separating"
            hits.append({
                "transit_planet": transit_name,
                "natal_point": natal_name,
                "aspect": aspect,
                "angle": round(diff, 2),
                "orb": round(orb, 2),
                "strength": round(max(0, 1 - orb / 8), 3),
                "phase": phase,
                "transit_retrograde": res[3] < 0,
            })
    hits.sort(key=lambda x: (-x["strength"], x["orb"]))
    return hits

