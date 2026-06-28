
import json
import swisseph as swe
from lunar_python import Solar
from typing import Optional

JIANZHU_NAMES = ["建","除","满","平","定","执","破","危","成","收","开","闭"]

NAKSHATRA_NAMES = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha",
    "Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati",
]
NAK_SPAN = 360 / 27
YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
    "Sukarman", "Dhriti", "Shoola", "Ganda", "Vriddhi", "Dhruva",
    "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyana",
    "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla",
    "Brahma", "Indra", "Vaidhriti",
]
KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti",
]

PLANETS_TRANSIT = [
    (swe.SUN,     "太阳"),
    (swe.MOON,    "月亮"),
    (swe.MERCURY, "水星"),
    (swe.VENUS,   "金星"),
    (swe.MARS,    "火星"),
    (swe.JUPITER, "木星"),
    (swe.SATURN,  "土星"),
]

SIGNS_ZH = [
    "白羊","金牛","双子","巨蟹","狮子","处女",
    "天秤","天蝎","射手","摩羯","水瓶","双鱼",
]

ZHI_ORDER = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

def _zhi_index(zhi: str) -> int:
    return ZHI_ORDER.index(zhi)

def _jianzhu(month_zhi: str, day_zhi: str) -> str:
    m_idx = _zhi_index(month_zhi)
    d_idx = _zhi_index(day_zhi)
    offset = (d_idx - m_idx) % 12
    return JIANZHU_NAMES[offset]

def _panchanga(date_str: str) -> dict:
    y, m, d = map(int, date_str.split("-"))
    jd = swe.julday(y, m, d, 6.0)

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    moon_sid, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
    moon_lon = moon_sid[0]
    nak_index = int(moon_lon / NAK_SPAN) % 27

    sun_trop, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SPEED)
    moon_trop, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SPEED)
    diff = (moon_trop[0] - sun_trop[0]) % 360
    tithi_num = int(diff / 12) + 1
    is_waxing = tithi_num <= 15
    yoga_index = int(((sun_trop[0] + moon_trop[0]) % 360) / NAK_SPAN) % 27

    karana_half = int(diff / 6) + 1
    if karana_half == 1:
        karana = "Kimstughna"
    elif karana_half >= 58:
        karana = ["Shakuni", "Chatushpada", "Naga"][min(karana_half - 58, 2)]
    else:
        karana = KARANA_NAMES[(karana_half - 2) % 7]

    return {
        "nakshatra":  NAKSHATRA_NAMES[nak_index],
        "tithi":      tithi_num,
        "is_waxing":  is_waxing,
        "yoga":       YOGA_NAMES[yoga_index],
        "karana":     karana,
    }

def _daily_transits(date_str: str) -> list[dict]:
    y, m, d = map(int, date_str.split("-"))
    jd = swe.julday(y, m, d, 6.0)
    transits = []
    for planet_id, name in PLANETS_TRANSIT:
        try:
            res, _ = swe.calc_ut(jd, planet_id, swe.FLG_SPEED)
            lon = res[0]
            sign = SIGNS_ZH[int(lon / 30) % 12]
            transits.append({"planet": name, "sign": sign, "longitude": round(lon, 2)})
        except Exception:
            pass
    return transits

def build(date_str: str) -> dict:
    y, m, d = map(int, date_str.split("-"))
    solar  = Solar.fromYmdHms(y, m, d, 12, 0, 0)
    lunar  = solar.getLunar()
    ec     = lunar.getEightChar()

    year_zhi  = str(ec.getYear())[1]
    month_zhi = str(ec.getMonth())[1]
    day_zhi   = str(ec.getDay())[1]

    ji_shen   = lunar.getDayJiShen()   if hasattr(lunar, "getDayJiShen")   else []
    xiong_sha = lunar.getDayXiongSha() if hasattr(lunar, "getDayXiongSha") else []
    shensha = ji_shen + xiong_sha

    result = {
        "date": date_str,
        "ganzhi": {
            "year":  str(ec.getYear()),
            "month": str(ec.getMonth()),
            "day":   str(ec.getDay()),
        },
        "base_yi":  lunar.getDayYi(),
        "base_ji":  lunar.getDayJi(),
        "shensha":  shensha,
        "zhi_xing": _jianzhu(month_zhi, day_zhi),
        "panchanga": _panchanga(date_str),
        "transits":  _daily_transits(date_str),
    }
    return result

