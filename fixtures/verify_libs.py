
import json

print("=" * 50)
print("1. lunar_python — 八字 + 宜忌")
print("=" * 50)
try:
    from lunar_python import Solar
    solar = Solar.fromYmdHms(1995, 3, 12, 8, 30, 0)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()

    result_bazi = {
        "year_pillar":  str(ec.getYear()),
        "month_pillar": str(ec.getMonth()),
        "day_pillar":   str(ec.getDay()),
        "time_pillar":  str(ec.getTime()),
        "day_yi": lunar.getDayYi(),
        "day_ji": lunar.getDayJi(),
    }
    print(json.dumps(result_bazi, ensure_ascii=False, indent=2))
    print("lunar_python OK\n")
except Exception as e:
    print(f"lunar_python ERROR: {e}\n")

print("=" * 50)
print("2. iztro_py — 紫微排盘")
print("=" * 50)
try:
    from iztro_py import astro

    chart = astro.by_solar("1995-3-12", 8, "女")

    palaces_sample = []
    for p in chart.palaces[:3]:
        major = []
        for s in p.major_stars:
            major.append(getattr(s, "name", str(s)))
        palaces_sample.append({
            "name": p.name,
            "heavenly_stem": p.heavenly_stem,
            "earthly_branch": p.earthly_branch,
            "major_stars": major,
        })

    result_ziwei = {
        "soul_palace_branch": chart.earthly_branch_of_soul_palace,
        "body_palace_branch": chart.earthly_branch_of_body_palace,
        "five_elements_class": chart.five_elements_class,
        "palaces_count": len(chart.palaces),
        "sample_palaces": palaces_sample,
    }
    print(json.dumps(result_ziwei, ensure_ascii=False, indent=2))
    print("iztro_py OK\n")
except Exception as e:
    print(f"iztro_py ERROR: {e}\n")

print("=" * 50)
print("3. pyswisseph — Nakshatra(Lahiri) + 西占太阳")
print("=" * 50)
try:
    import swisseph as swe
    from datetime import datetime, timezone

    jd = swe.julday(1995, 3, 12, 0.5)

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    moon_sid, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)
    moon_lon = moon_sid[0]
    nak_index = int(moon_lon / (360 / 27))
    nakshatra_names = [
        "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
        "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
        "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
        "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha",
        "Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
    ]

    sun_trop, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SPEED)
    sun_lon = sun_trop[0]
    signs = ["白羊","金牛","双子","巨蟹","狮子","处女",
             "天秤","天蝎","射手","摩羯","水瓶","双鱼"]
    sun_sign = signs[int(sun_lon / 30)]

    result_vedic = {
        "moon_longitude_sidereal_lahiri": round(moon_lon, 4),
        "nakshatra": nakshatra_names[nak_index],
        "nakshatra_index": nak_index,
        "sun_longitude_tropical": round(sun_lon, 4),
        "sun_sign_tropical": sun_sign,
    }
    print(json.dumps(result_vedic, ensure_ascii=False, indent=2))
    print("pyswisseph OK\n")
except Exception as e:
    print(f"pyswisseph ERROR: {e}\n")

print("=" * 50)
print("Phase 0 验证完毕")
print("=" * 50)
