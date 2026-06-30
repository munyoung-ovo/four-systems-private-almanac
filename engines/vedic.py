
import json
import swisseph as swe
from datetime import date, datetime, timezone
from typing import Literal
from models.profile import CalculationProfile, CalendarType, EvidenceLevel, TimePrecision

TIME_PRECISION = Literal["exact", "hour", "unknown"]

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishtha", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
]

NAK_SPAN = 360 / 27

VIMSHOTTARI_ORDER = [
    ("Ketu",    7), ("Venus",  20), ("Sun",     6), ("Moon",   10),
    ("Mars",    7), ("Rahu",  18), ("Jupiter", 16), ("Saturn", 19),
    ("Mercury", 17),
]
NAK_TO_DASHA = [
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
]
NAK_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
]
SIGNS_EN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORDS = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
    4: "Sun", 5: "Mercury", 6: "Venus", 7: "Mars",
    8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter",
}
VIMSHOTTARI_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
PLANET_SWE = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
    "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS, "Saturn": swe.SATURN,
}
EXALTATION = {"Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
              "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
              "Saturn": "Libra"}
DEBILITATION = {"Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
                "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
                "Saturn": "Aries"}
OWN_SIGNS = {"Sun": {"Leo"}, "Moon": {"Cancer"}, "Mars": {"Aries", "Scorpio"},
             "Mercury": {"Gemini", "Virgo"}, "Jupiter": {"Sagittarius", "Pisces"},
             "Venus": {"Taurus", "Libra"}, "Saturn": {"Capricorn", "Aquarius"}}
HOUSE_DOMAINS = {
    1: "自我", 2: "财富", 3: "兄弟沟通", 4: "家庭居所",
    5: "创造子女", 6: "疾病劳务", 7: "伴侣合作", 8: "变故深层",
    9: "信念远行", 10: "事业名望", 11: "收入社群", 12: "损耗隐退",
}

def _jd_from_solar(solar_dt: str, time_precision: TIME_PRECISION,
                   tz: float = 8) -> float:
    dt = datetime.fromisoformat(solar_dt)
    if time_precision == "unknown":
        dt = dt.replace(hour=0, minute=0, second=0)
    utc_hour = (dt.hour + dt.minute / 60) - tz
    return swe.julday(dt.year, dt.month, dt.day, utc_hour)

def _nakshatra_from_lon(lon_sid: float) -> dict:
    idx = int(lon_sid / NAK_SPAN) % 27
    degree_in = lon_sid % NAK_SPAN
    pada = int(degree_in / (NAK_SPAN / 4)) + 1
    return {
        "name":     NAKSHATRA_NAMES[idx],
        "index":    idx,
        "pada":     pada,
        "lord":     NAK_LORDS[idx],
        "longitude": round(lon_sid, 4),
    }

def _sign_idx(lon: float) -> int:
    return int(lon / 30) % 12

def _degree_in_sign(lon: float) -> float:
    return round(lon % 30, 4)

def _house_from_lagna(sign_idx: int, lagna_idx: int) -> int:
    return ((sign_idx - lagna_idx) % 12) + 1

def _format_degree(degree: float) -> str:
    deg = int(degree)
    minute = int(round((degree - deg) * 60))
    if minute == 60:
        deg += 1
        minute = 0
    return f"{deg}°{minute:02d}'"

def _calc_lagna(jd: float, lat: float, lon: float) -> dict:
    try:
        cusps, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
        asc_lon = ascmc[0] % 360
    except Exception:
        cusps, ascmc = swe.houses(jd, lat, lon, b"P")
        asc_lon = (ascmc[0] - swe.get_ayanamsa_ut(jd)) % 360
    idx = _sign_idx(asc_lon)
    degree = _degree_in_sign(asc_lon)
    return {
        "longitude": round(asc_lon, 4),
        "sign": SIGNS_EN[idx],
        "sign_zh": _RASI_CN[idx],
        "sign_idx": idx,
        "degree": degree,
        "deg_str": _format_degree(degree),
        "house": 1,
        "nakshatra": _nakshatra_from_lon(asc_lon),
    }

def _calc_planets(jd: float, lagna_idx: int) -> dict:
    planets = {}
    for name, pid in PLANET_SWE.items():
        res, _ = swe.calc_ut(jd, pid, swe.FLG_SIDEREAL | swe.FLG_SPEED)
        lon = res[0] % 360
        idx = _sign_idx(lon)
        degree = _degree_in_sign(lon)
        planets[name] = {
            "longitude": round(lon, 4),
            "sign": SIGNS_EN[idx],
            "sign_zh": _RASI_CN[idx],
            "sign_idx": idx,
            "degree": degree,
            "deg_str": _format_degree(degree),
            "house": _house_from_lagna(idx, lagna_idx),
            "retrograde": bool(res[3] < 0),
            "speed": round(res[3], 6),
            "nakshatra": _nakshatra_from_lon(lon),
        }

    rahu, _ = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SIDEREAL | swe.FLG_SPEED)
    rahu_lon = rahu[0] % 360
    for name, lon, speed in (("Rahu", rahu_lon, rahu[3]), ("Ketu", (rahu_lon + 180) % 360, -rahu[3])):
        idx = _sign_idx(lon)
        degree = _degree_in_sign(lon)
        planets[name] = {
            "longitude": round(lon, 4),
            "sign": SIGNS_EN[idx],
            "sign_zh": _RASI_CN[idx],
            "sign_idx": idx,
            "degree": degree,
            "deg_str": _format_degree(degree),
            "house": _house_from_lagna(idx, lagna_idx),
            "retrograde": True,
            "speed": round(speed, 6),
            "nakshatra": _nakshatra_from_lon(lon),
        }
    return planets

def _navamsa_idx(lon: float) -> int:
    sign_idx = _sign_idx(lon)
    part = int((lon % 30) / (30 / 9))
    start_by_element = [0, 9, 6, 3]
    return (start_by_element[sign_idx % 4] + part) % 12

def _dashamsa_idx(lon: float) -> int:
    sign_idx = _sign_idx(lon)
    part = int((lon % 30) / 3)
    return (sign_idx + part + (0 if sign_idx % 2 == 0 else 8)) % 12

def _chaturthamsha_idx(lon: float) -> int:
    sign_idx = _sign_idx(lon)
    part = int((lon % 30) / (30 / 4))
    return (sign_idx + part * 3) % 12

def _panchamsha_idx(lon: float) -> int:
    part = int((lon % 30) / 6)
    sign_idx = _sign_idx(lon)
    odd = [0, 10, 8, 2, 6]
    even = [1, 5, 11, 9, 7]
    return (odd if sign_idx % 2 == 0 else even)[min(part, 4)]

def _divisional_charts(lagna: dict, planets: dict) -> dict:
    points = {"Lagna": lagna, **planets}
    formulas = {
        "D9": _navamsa_idx,
        "D10": _dashamsa_idx,
        "D4": _chaturthamsha_idx,
        "D5": _panchamsha_idx,
    }
    charts = {}
    for chart_name, fn in formulas.items():
        chart = {}
        lagna_idx = fn(lagna["longitude"])
        for name, data in points.items():
            idx = fn(data["longitude"])
            chart[name] = {
                "sign": SIGNS_EN[idx],
                "sign_zh": _RASI_CN[idx],
                "sign_idx": idx,
                "house": _house_from_lagna(idx, lagna_idx),
            }
        charts[chart_name] = chart
    return charts

def _house_lords(lagna_idx: int, planets: dict) -> dict:
    out = {}
    for house in range(1, 13):
        sign_idx = (lagna_idx + house - 1) % 12
        lord = SIGN_LORDS[sign_idx]
        out[house] = {
            "sign": SIGNS_EN[sign_idx],
            "sign_zh": _RASI_CN[sign_idx],
            "domain": HOUSE_DOMAINS[house],
            "lord": lord,
            "lord_house": planets.get(lord, {}).get("house"),
        }
    return out

def _dignity(planets: dict) -> dict:
    out = {}
    for name in VIMSHOTTARI_PLANETS:
        sign = planets[name]["sign"]
        if EXALTATION.get(name) == sign:
            level = "exalted"
        elif DEBILITATION.get(name) == sign:
            level = "debilitated"
        elif sign in OWN_SIGNS.get(name, set()):
            level = "own_sign"
        else:
            level = "neutral"
        out[name] = {"sign": sign, "sign_zh": planets[name]["sign_zh"], "level": level}
    return out

def _chara_karakas(planets: dict) -> dict:
    labels = ["AK", "AmK", "BK", "MK", "PK", "GK", "DK"]
    ranked = sorted(
        [(name, planets[name]["degree"]) for name in VIMSHOTTARI_PLANETS],
        key=lambda x: x[1],
        reverse=True,
    )
    seven = [{"karaka": labels[i], "planet": p, "degree": round(deg, 4)}
             for i, (p, deg) in enumerate(ranked)]
    return {"seven_karaka": seven, "darakaraka": seven[-1]["planet"]}

def _aspects(planets: dict) -> list[dict]:
    names = list(planets)
    items = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            diff = abs(planets[a]["longitude"] - planets[b]["longitude"]) % 360
            if diff > 180:
                diff = 360 - diff
            kind = None
            if diff <= 8:
                kind = "conjunction"
            elif abs(diff - 180) <= 8:
                kind = "opposition"
            elif abs(diff - 120) <= 6:
                kind = "trine"
            if kind:
                items.append({"p1": a, "p2": b, "type": kind, "angle": round(diff, 2)})
    return sorted(items, key=lambda x: x["angle"])[:12]

def _moon_phase(planets: dict) -> dict:
    diff = (planets["Moon"]["longitude"] - planets["Sun"]["longitude"]) % 360
    return {"waxing": diff < 180, "sun_moon_diff": round(diff, 2)}

def _combustion(planets: dict) -> dict:
    limits = {
        "Moon": 12.0, "Mars": 17.0, "Mercury": 14.0,
        "Jupiter": 11.0, "Venus": 10.0, "Saturn": 15.0,
    }
    sun_lon = planets["Sun"]["longitude"]
    out = {}
    for name, limit in limits.items():
        diff = abs(planets[name]["longitude"] - sun_lon) % 360
        if diff > 180:
            diff = 360 - diff
        if diff <= limit:
            out[name] = {"distance": round(diff, 2), "limit": limit}
    return out

def _vimshottari(jd_birth: float, moon_lon_sid: float,
                 target_date: str | None = None) -> dict:
    nak_idx  = int(moon_lon_sid / NAK_SPAN) % 27
    dasha_planet = NAK_TO_DASHA[nak_idx]

    deg_in_nak   = moon_lon_sid % NAK_SPAN
    elapsed_frac = deg_in_nak / NAK_SPAN

    order_names = [p for p, _ in VIMSHOTTARI_ORDER]
    start_idx   = order_names.index(dasha_planet)

    total_years  = VIMSHOTTARI_ORDER[start_idx][1]
    elapsed_years = elapsed_frac * total_years
    remaining    = total_years - elapsed_years

    start_jd = jd_birth - elapsed_years * 365.2425
    timeline = []
    cursor = start_jd
    for i in range(len(VIMSHOTTARI_ORDER)):
        idx = (start_idx + i) % len(VIMSHOTTARI_ORDER)
        planet, years = VIMSHOTTARI_ORDER[idx]
        end = cursor + years * 365.2425
        timeline.append({
            "planet": planet,
            "start_jd": round(cursor, 2),
            "end_jd": round(end, 2),
            "start_date": _jd_to_date(cursor),
            "end_date": _jd_to_date(end),
            "duration_years": years,
            "antardasha": _antardasha(idx, cursor, years),
        })
        cursor = end

    if target_date is None:
        target_date = date.today().isoformat()
    y, m, d = (int(x) for x in target_date.split("-"))
    target_jd = swe.julday(y, m, d, 12.0)
    current = None
    current_idx = start_idx
    for i, item in enumerate(timeline):
        if item["start_jd"] <= target_jd < item["end_jd"]:
            current = item
            current_idx = (start_idx + i) % len(VIMSHOTTARI_ORDER)
            break
    if current is None:
        current = timeline[-1] if target_jd >= timeline[-1]["end_jd"] else timeline[0]
        current_idx = order_names.index(current["planet"])

    current_antardasha = None
    for item in current.get("antardasha", []):
        sy, sm, sd = (int(x) for x in item["start_date"].split("-"))
        ey, em, ed = (int(x) for x in item["end_date"].split("-"))
        start_ad = swe.julday(sy, sm, sd, 12.0)
        end_ad = swe.julday(ey, em, ed, 12.0)
        if start_ad <= target_jd < end_ad:
            current_antardasha = item
            break

    remaining_years = max(0.0, (current["end_jd"] - target_jd) / 365.2425)
    next_idx = (current_idx + 1) % len(VIMSHOTTARI_ORDER)

    return {
        "birth_mahadasha":           dasha_planet,
        "birth_mahadasha_remaining_years": round(remaining, 2),
        "mahadasha":                 current["planet"],
        "current_mahadasha":         current["planet"],
        "current_antardasha":        current_antardasha,
        "mahadasha_remaining_years": round(remaining_years, 2),
        "next_mahadasha":            VIMSHOTTARI_ORDER[next_idx][0],
        "timeline":                  timeline,
        "target_date":               target_date,
        "precision": {
            "level": "medium",
            "method": "moon_nakshatra_proportional",
            "uses_birth_moon_longitude": True,
            "has_all_antardasha": True,
        },
        "note": "Vimshottari 按出生月宿起算并定位到 target_date；需结合分盘与行运",
    }

def _jd_to_date(jd: float) -> str:
    y, m, d, _ = swe.revjul(jd)
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

def _antardasha(maha_idx: int, start_jd: float, maha_years: float) -> list[dict]:
    items = []
    cursor = start_jd
    for i in range(len(VIMSHOTTARI_ORDER)):
        idx = (maha_idx + i) % len(VIMSHOTTARI_ORDER)
        planet, years = VIMSHOTTARI_ORDER[idx]
        duration_years = maha_years * years / 120
        end = cursor + duration_years * 365.2425
        items.append({
            "planet": planet,
            "start_jd": round(cursor, 2),
            "end_jd": round(end, 2),
            "start_date": _jd_to_date(cursor),
            "end_date": _jd_to_date(end),
            "duration_years": round(duration_years, 3),
        })
        cursor = end
    return items

_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
_CONTRIB = _PLANETS + ["Lagna"]
_SWE_ID = {"Sun": 0, "Moon": 1, "Mercury": 2, "Venus": 3, "Mars": 4, "Jupiter": 5, "Saturn": 6}
_RASI_CN = ["白羊", "金牛", "双子", "巨蟹", "狮子", "处女",
            "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼"]
AV_TABLE = {
    "Sun": {"Sun": [1,2,4,7,8,9,10,11], "Moon": [3,6,10,11], "Mars": [1,2,4,7,8,9,10,11],
            "Mercury": [3,5,6,9,10,11,12], "Jupiter": [5,6,9,11], "Venus": [6,7,12],
            "Saturn": [1,2,4,7,8,9,10,11], "Lagna": [3,4,6,10,11,12]},
    "Moon": {"Sun": [3,6,7,8,10,11], "Moon": [1,3,6,7,10,11], "Mars": [2,3,5,6,9,10,11],
             "Mercury": [1,3,4,5,7,8,10,11], "Jupiter": [1,4,7,8,10,11,12],
             "Venus": [3,4,5,7,9,10,11], "Saturn": [3,5,6,11], "Lagna": [3,6,10,11]},
    "Mars": {"Sun": [3,5,6,10,11], "Moon": [3,6,11], "Mars": [1,2,4,7,8,10,11],
             "Mercury": [3,5,6,11], "Jupiter": [6,10,11,12], "Venus": [6,8,11,12],
             "Saturn": [1,4,7,8,9,10,11], "Lagna": [1,3,6,10,11]},
    "Mercury": {"Sun": [5,6,9,11,12], "Moon": [2,4,6,8,10,11], "Mars": [1,2,4,7,8,9,10,11],
                "Mercury": [1,3,5,6,9,10,11,12], "Jupiter": [6,8,11,12],
                "Venus": [1,2,3,4,5,8,9,11], "Saturn": [1,2,4,7,8,9,10,11],
                "Lagna": [1,2,4,6,8,10,11]},
    "Jupiter": {"Sun": [1,2,3,4,7,8,9,10,11], "Moon": [2,5,7,9,11], "Mars": [1,2,4,7,8,10,11],
                "Mercury": [1,2,4,5,6,9,10,11], "Jupiter": [1,2,3,4,7,8,10,11],
                "Venus": [2,5,6,9,10,11], "Saturn": [3,5,6,12],
                "Lagna": [1,2,4,5,6,7,9,10,11]},
    "Venus": {"Sun": [8,11,12], "Moon": [1,2,3,4,5,8,9,11,12], "Mars": [3,5,6,9,11,12],
              "Mercury": [3,5,6,9,11], "Jupiter": [5,8,9,10,11],
              "Venus": [1,2,3,4,5,8,9,10,11], "Saturn": [3,4,5,8,9,10,11],
              "Lagna": [1,2,3,4,5,8,9,11]},
    "Saturn": {"Sun": [1,2,4,7,8,10,11], "Moon": [3,6,11], "Mars": [3,5,6,10,11,12],
               "Mercury": [6,8,9,10,11,12], "Jupiter": [5,6,11,12], "Venus": [6,11,12],
               "Saturn": [3,5,6,11], "Lagna": [1,3,4,6,10,11]},
}

def _ashtakavarga(jd: float, asc_lon: float) -> dict:
    signs = {p: int(swe.calc_ut(jd, _SWE_ID[p], swe.FLG_SIDEREAL)[0][0] / 30) % 12
             for p in _PLANETS}
    signs["Lagna"] = int(asc_lon / 30) % 12

    bav = {p: [0] * 12 for p in _PLANETS}
    for p in _PLANETS:
        for c in _CONTRIB:
            s_c = signs[c]
            for h in AV_TABLE[p][c]:
                bav[p][(s_c + h - 1) % 12] += 1

    sav = [sum(bav[p][i] for p in _PLANETS) for i in range(12)]
    lagna_idx = int(asc_lon / 30) % 12
    sav_by_house = {
        h: {
            "sign": SIGNS_EN[(lagna_idx + h - 1) % 12],
            "sign_zh": _RASI_CN[(lagna_idx + h - 1) % 12],
            "value": sav[(lagna_idx + h - 1) % 12],
        }
        for h in range(1, 13)
    }
    bav_by_sign = {
        p: {SIGNS_EN[i]: bav[p][i] for i in range(12)}
        for p in _PLANETS
    }
    return {
        "sav": {_RASI_CN[i]: sav[i] for i in range(12)},
        "sav_en": {SIGNS_EN[i]: sav[i] for i in range(12)},
        "sav_by_house": sav_by_house,
        "bav": bav_by_sign,
        "bav_totals": {p: sum(bav[p]) for p in _PLANETS},
        "sav_total": sum(sav),
        "lagna_sign": _RASI_CN[signs["Lagna"]],
        "validation": {
            "sav_total_is_337": sum(sav) == 337,
            "bav_row_totals": {p: sum(bav[p]) for p in _PLANETS},
        },
        "note": "Ashtakavarga(Lahiri)：某座 SAV 越高，行星过境该座越有力，用于流年/择日加权",
    }

def _strength_metrics(planets: dict | None) -> dict:
    if not planets:
        return {"available": False, "level": "unavailable", "metrics": {}}
    return {
        "available": False,
        "level": "not_configured",
        "metrics": {},
        "reason": "本地强度精算模块未配置；当前只输出尊贵度、逆行、燃烧等可确定字段",
    }

def build(solar_dt: str, gender: str,
          time_precision: TIME_PRECISION = "exact",
          lat: float = 31.23, lon: float = 121.47,
          tz: float = 8,
          target_date: str | None = None) -> dict:
    jd = _jd_from_solar(solar_dt, time_precision, tz)

    swe.set_sid_mode(swe.SIDM_LAHIRI)

    moon_sid, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
    moon_lon    = moon_sid[0]
    moon_nak    = _nakshatra_from_lon(moon_lon)

    vimshottari = _vimshottari(jd, moon_lon, target_date)

    ashtakavarga = None
    lagna = None
    planets = None
    jyotish_basis = None
    asc_nak = None
    if time_precision == "exact":
        try:
            if abs(lat) >= 66.5:
                raise ValueError("polar latitude: lagna and houses degraded")
            lagna = _calc_lagna(jd, lat, lon)
            planets = _calc_planets(jd, lagna["sign_idx"])
            asc_nak = lagna["nakshatra"]
            ashtakavarga = _ashtakavarga(jd, lagna["longitude"])
            divisional = _divisional_charts(lagna, planets)
            jyotish_basis = {
                "ayanamsa_value": round(swe.get_ayanamsa_ut(jd), 6),
                "node_mode": "mean",
                "lagna": lagna,
                "planets": planets,
                "house_lords": _house_lords(lagna["sign_idx"], planets),
                "divisional_charts": divisional,
                "vargottama": {
                    name: data["sign_idx"] == divisional["D9"].get(name, {}).get("sign_idx")
                    for name, data in planets.items()
                },
                "dignity": _dignity(planets),
                "strength_metrics": _strength_metrics(planets),
                "combustion": _combustion(planets),
                "karakas": _chara_karakas(planets),
                "aspects": _aspects(planets),
                "moon_phase": _moon_phase(planets),
                "validation": {
                    "planet_count": len(planets),
                    "rahu_ketu_opposition": (
                        round((planets["Ketu"]["longitude"] - planets["Rahu"]["longitude"]) % 360, 4) == 180
                    ),
                    "sav_total": ashtakavarga.get("sav_total") if ashtakavarga else None,
                },
            }
        except Exception:
            lagna = None
            planets = None
            asc_nak = None
            ashtakavarga = None
            jyotish_basis = None

    result = {
        "moon_nakshatra":  moon_nak["name"],
        "moon_pada":       moon_nak["pada"],
        "moon_longitude_sidereal": moon_lon,
        "ascendant_nak":   asc_nak["name"] if asc_nak else None,
        "lagna":           lagna,
        "planets":         planets,
        "jyotish_basis":   jyotish_basis,
        "vimshottari":     vimshottari,
        "ashtakavarga":    ashtakavarga,
        "ayanamsa":        "Lahiri",
        "calculation_profile": CalculationProfile(
            calendar_type=CalendarType.SOLAR,
            is_true_solar_time=False,
            time_precision=(
                TimePrecision.MINUTE if time_precision == "exact"
                else TimePrecision.HOUR if time_precision == "hour"
                else TimePrecision.UNKNOWN
            ),
            longitude=lon,
            latitude=lat,
            timezone=tz,
            confidence_score=0.9 if time_precision == "exact" else 0.72 if time_precision == "hour" else 0.38,
            evidence_level=EvidenceLevel.HIGH if time_precision == "exact" else EvidenceLevel.MEDIUM if time_precision == "hour" else EvidenceLevel.LOW,
            warnings=[] if time_precision == "exact" else ["出生时间非分钟级，Lagna、分盘与Ashtakavarga判断降级"],
        ).to_dict(),
        "degraded":        time_precision == "unknown",
    }
    return result

