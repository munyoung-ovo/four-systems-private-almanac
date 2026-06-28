
import json
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

def _find_aspects(positions: dict[str, float]) -> list[dict]:
    planets = list(positions.items())
    result = []
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1, lon1 = planets[i]
            p2, lon2 = planets[j]
            diff = abs(lon1 - lon2) % 360
            if diff > 180:
                diff = 360 - diff
            for angle, orb, name in ASPECTS:
                if abs(diff - angle) <= orb:
                    exact_orb = round(abs(diff - angle), 2)
                    result.append({
                        "planet1": p1,
                        "planet2": p2,
                        "aspect":  name,
                        "angle":   round(diff, 2),
                        "orb":     exact_orb,
                        "orb_limit": orb,
                        "strength": round(max(0, 1 - exact_orb / orb), 3),
                    })
                    break
    return result

def _aspect_to_angle(diff: float) -> tuple[str, float, float] | None:
    for angle, orb, name in ASPECTS:
        exact_orb = abs(diff - angle)
        if exact_orb <= orb:
            return name, angle, exact_orb
    return None

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
    natal_aspects = _find_aspects(valid_pos)

    result = {
        "sun":       planet_positions.get("太阳", {}).get("sign"),
        "moon":      planet_positions.get("月亮", {}).get("sign"),
        "ascendant": asc_sign,
        "ascendant_longitude": round(asc_lon, 4) if asc_lon is not None else None,
        "mc":        mc_sign if time_precision == "exact" else None,
        "mc_longitude": round(mc_lon, 4) if time_precision == "exact" and mc_lon is not None else None,
        "planets":   planet_positions,
        "natal_aspects": natal_aspects,
        "house_cusps":   house_cusps,
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
            hits.append({
                "transit_planet": transit_name,
                "natal_point": natal_name,
                "aspect": aspect,
                "angle": round(diff, 2),
                "orb": round(orb, 2),
                "strength": round(max(0, 1 - orb / 8), 3),
                "transit_retrograde": res[3] < 0,
            })
    hits.sort(key=lambda x: (-x["strength"], x["orb"]))
    return hits

