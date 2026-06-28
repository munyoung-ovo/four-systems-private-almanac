
import json
import swisseph as swe
from datetime import datetime, timezone
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
        "longitude": round(lon_sid, 4),
    }

def _vimshottari(jd_birth: float, moon_lon_sid: float) -> dict:
    nak_idx  = int(moon_lon_sid / NAK_SPAN) % 27
    dasha_planet = NAK_TO_DASHA[nak_idx]

    deg_in_nak   = moon_lon_sid % NAK_SPAN
    elapsed_frac = deg_in_nak / NAK_SPAN

    order_names = [p for p, _ in VIMSHOTTARI_ORDER]
    start_idx   = order_names.index(dasha_planet)

    total_years  = VIMSHOTTARI_ORDER[start_idx][1]
    elapsed_years = elapsed_frac * total_years
    remaining    = total_years - elapsed_years

    next_idx = (start_idx + 1) % len(VIMSHOTTARI_ORDER)
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

    return {
        "mahadasha":                 dasha_planet,
        "mahadasha_remaining_years": round(remaining, 2),
        "next_mahadasha":            VIMSHOTTARI_ORDER[next_idx][0],
        "timeline":                  timeline,
        "note": "Vimshottari 简算，仅供参考；精算需完整年表",
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
    return {
        "sav": {_RASI_CN[i]: sav[i] for i in range(12)},
        "bav_totals": {p: sum(bav[p]) for p in _PLANETS},
        "sav_total": sum(sav),
        "lagna_sign": _RASI_CN[signs["Lagna"]],
        "note": "Ashtakavarga(Lahiri)：某座 SAV 越高，行星过境该座越有力，用于流年/择日加权",
    }

def build(solar_dt: str, gender: str,
          time_precision: TIME_PRECISION = "exact",
          lat: float = 31.23, lon: float = 121.47,
          tz: float = 8) -> dict:
    jd = _jd_from_solar(solar_dt, time_precision, tz)

    swe.set_sid_mode(swe.SIDM_LAHIRI)

    moon_sid, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
    moon_lon    = moon_sid[0]
    moon_nak    = _nakshatra_from_lon(moon_lon)

    vimshottari = _vimshottari(jd, moon_lon)

    ashtakavarga = None
    asc_nak = None
    if time_precision == "exact":
        try:
            cusps, ascmc = swe.houses(jd, lat, lon, b'P')
            asc_lon  = ascmc[0]
            asc_sid  = (asc_lon - swe.get_ayanamsa_ut(jd)) % 360
            asc_nak  = _nakshatra_from_lon(asc_sid)
            ashtakavarga = _ashtakavarga(jd, asc_sid)
        except Exception:
            asc_nak = None
            ashtakavarga = None

    result = {
        "moon_nakshatra":  moon_nak["name"],
        "moon_pada":       moon_nak["pada"],
        "moon_longitude_sidereal": moon_lon,
        "ascendant_nak":   asc_nak["name"] if asc_nak else None,
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

