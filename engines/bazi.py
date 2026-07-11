
from lunar_python import Solar
from lunar_python.util import LunarUtil
import json
import math
from typing import Literal
from models.profile import CalculationProfile, CalendarType, EvidenceLevel, TimePrecision

TIME_PRECISION = Literal["exact", "hour", "unknown"]

_ZHI_HIDE_GAN = {
    "子": ["癸"], "丑": ["己","癸","辛"], "寅": ["甲","丙","戊"],
    "卯": ["乙"], "辰": ["戊","乙","癸"], "巳": ["丙","庚","戊"],
    "午": ["丁","己"], "未": ["己","丁","乙"], "申": ["庚","壬","戊"],
    "酉": ["辛"], "戌": ["戊","辛","丁"], "亥": ["壬","甲"],
}

_GAN_WUXING = {
    "甲":"木","乙":"木","丙":"火","丁":"火","戊":"土",
    "己":"土","庚":"金","辛":"金","壬":"水","癸":"水",
}
_ZHI_WUXING = {
    "子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火",
    "午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水",
}

_SHISHEN_TABLE = {
    ("木","木"): {"同":"比肩","异":"劫财"},
    ("木","火"): {"同":"食神","异":"伤官"},
    ("木","土"): {"同":"偏财","异":"正财"},
    ("木","金"): {"同":"七杀","异":"正官"},
    ("木","水"): {"同":"偏印","异":"正印"},
    ("火","火"): {"同":"比肩","异":"劫财"},
    ("火","土"): {"同":"食神","异":"伤官"},
    ("火","金"): {"同":"偏财","异":"正财"},
    ("火","水"): {"同":"七杀","异":"正官"},
    ("火","木"): {"同":"偏印","异":"正印"},
    ("土","土"): {"同":"比肩","异":"劫财"},
    ("土","金"): {"同":"食神","异":"伤官"},
    ("土","水"): {"同":"偏财","异":"正财"},
    ("土","木"): {"同":"七杀","异":"正官"},
    ("土","火"): {"同":"偏印","异":"正印"},
    ("金","金"): {"同":"比肩","异":"劫财"},
    ("金","水"): {"同":"食神","异":"伤官"},
    ("金","木"): {"同":"偏财","异":"正财"},
    ("金","火"): {"同":"七杀","异":"正官"},
    ("金","土"): {"同":"偏印","异":"正印"},
    ("水","水"): {"同":"比肩","异":"劫财"},
    ("水","木"): {"同":"食神","异":"伤官"},
    ("水","火"): {"同":"偏财","异":"正财"},
    ("水","土"): {"同":"七杀","异":"正官"},
    ("水","金"): {"同":"偏印","异":"正印"},
}

_YANG_GAN = {"甲","丙","戊","庚","壬"}

_ZHI_HIDE_WEIGHTED = {
    "子": [("癸", 2.0)],
    "丑": [("己", 2.0), ("癸", 0.8), ("辛", 0.5)],
    "寅": [("甲", 2.0), ("丙", 0.8), ("戊", 0.5)],
    "卯": [("乙", 2.0)],
    "辰": [("戊", 2.0), ("乙", 0.8), ("癸", 0.5)],
    "巳": [("丙", 2.0), ("庚", 0.8), ("戊", 0.5)],
    "午": [("丁", 2.0), ("己", 0.8)],
    "未": [("己", 2.0), ("丁", 0.8), ("乙", 0.5)],
    "申": [("庚", 2.0), ("壬", 0.8), ("戊", 0.5)],
    "酉": [("辛", 2.0)],
    "戌": [("戊", 2.0), ("辛", 0.8), ("丁", 0.5)],
    "亥": [("壬", 2.0), ("甲", 0.8)],
}

_CHANGSHENG_START = {
    "甲": "亥", "丙": "寅", "戊": "寅", "庚": "巳", "壬": "申",
    "乙": "午", "丁": "酉", "己": "酉", "辛": "子", "癸": "卯",
}
_ZHI_ORDER = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
_CHANGSHENG_STAGES = ["长生","沐浴","冠带","临官","帝旺","衰","病","死","墓","绝","胎","养"]
_STAGE_SCORE = {
    "长生": 2.0, "沐浴": -1.0, "冠带": 1.0, "临官": 3.0, "帝旺": 3.0, "衰": -1.0,
    "病": -2.0, "死": -3.0, "墓": -2.0, "绝": -3.0, "胎": -1.0, "养": 1.0,
}

_MONTH_GOD_BASE = {
    "比肩": 5.0, "劫财": 4.0, "正印": 3.0, "偏印": 3.0,
    "食神": -2.0, "伤官": -3.0, "正财": -4.0, "偏财": -3.0,
    "正官": -3.0, "七杀": -4.0,
}
_GE_JU_NAME = {
    "比肩": "建禄格", "劫财": "月劫格", "正印": "正印格", "偏印": "偏印格",
    "食神": "食神格", "伤官": "伤官格", "正财": "正财格", "偏财": "偏财格",
    "正官": "正官格", "七杀": "七杀格",
}
_TIAOHOU_BY_MONTH = {
    "亥": ["火"], "子": ["火"], "丑": ["火"], "寅": ["火"],
    "巳": ["水"], "午": ["水"], "未": ["水"],
    "申": ["水"], "酉": ["水"], "戌": ["水"],
    "卯": [], "辰": [],
}
_SUPPORT_GODS = {"比肩", "劫财", "正印", "偏印"}

def _equation_of_time_minutes(dt) -> float:
    day_of_year = dt.timetuple().tm_yday
    b = 2 * math.pi * (day_of_year - 81) / 364
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

def _true_solar_datetime(dt, lon: float, tz: float):
    from datetime import timedelta
    longitude_minutes = (lon - tz * 15) * 4
    eot_minutes = _equation_of_time_minutes(dt)
    total_minutes = longitude_minutes + eot_minutes
    return dt + timedelta(minutes=total_minutes), {
        "enabled": True,
        "input_time": dt.isoformat(timespec="minutes"),
        "effective_time": (dt + timedelta(minutes=total_minutes)).isoformat(timespec="minutes"),
        "longitude_correction_minutes": round(longitude_minutes, 2),
        "equation_of_time_minutes": round(eot_minutes, 2),
        "total_correction_minutes": round(total_minutes, 2),
    }

def _boundary_warnings(dt) -> list[dict]:
    minute_of_day = dt.hour * 60 + dt.minute
    hour_boundaries = [60, 180, 300, 420, 540, 660, 780, 900, 1020, 1140, 1260, 1380]
    warnings = []
    nearest = min(hour_boundaries, key=lambda b: abs(minute_of_day - b))
    dist = abs(minute_of_day - nearest)
    if dist <= 20:
        warnings.append({
            "type": "hour_boundary",
            "minutes_from_boundary": dist,
            "note": "接近时辰交界，时柱可能因记录误差或真太阳时校正而改变",
        })
    day_boundary_dist = min(abs(minute_of_day - 1380), minute_of_day + 60)
    if day_boundary_dist <= 30:
        warnings.append({
            "type": "day_boundary",
            "minutes_from_boundary": day_boundary_dist,
            "note": "接近 23:00 换日边界，日柱流派与出生时间误差需复核",
        })
    return warnings

def _build_luck(ec, gender: str, day_gan: str, current_year: int) -> dict:
    gender_code = 1 if gender == "男" else 0
    try:
        yun = ec.getYun(gender_code)
    except Exception as e:
        return {"degraded": True, "error": str(e), "dayun": [], "current_dayun": None}

    dayun = []
    current_dayun = None
    current_liunian = None
    for d in yun.getDaYun()[1:11]:
        gz = d.getGanZhi()
        if not gz:
            continue
        gan, zhi = gz[0], gz[1]
        liunian = []
        for ln in d.getLiuNian():
            lgz = ln.getGanZhi()
            item = {
                "year": ln.getYear(),
                "age": ln.getAge(),
                "gan_zhi": lgz,
                "gan_shi_shen": _shishen(day_gan, lgz[0]) if lgz else "",
                "zhi": lgz[1] if lgz else "",
            }
            liunian.append(item)
            if ln.getYear() == current_year:
                current_liunian = item
        item = {
            "gan_zhi": gz,
            "gan_shi_shen": _shishen(day_gan, gan),
            "zhi_shi_shen": _shishen(day_gan, _ZHI_HIDE_WEIGHTED[zhi][0][0]) if zhi in _ZHI_HIDE_WEIGHTED else "",
            "start_age": d.getStartAge(),
            "end_age": d.getEndAge(),
            "start_year": d.getStartYear(),
            "end_year": d.getEndYear(),
            "liunian": liunian,
        }
        dayun.append(item)
        if d.getStartYear() <= current_year <= d.getEndYear():
            current_dayun = item

    start_solar = yun.getStartSolar()
    return {
        "degraded": False,
        "direction": "forward" if yun.isForward() else "backward",
        "start": {
            "years": yun.getStartYear(),
            "months": yun.getStartMonth(),
            "days": yun.getStartDay(),
            "hours": yun.getStartHour(),
            "solar": start_solar.toYmdHms() if start_solar else "",
        },
        "dayun": dayun,
        "current_dayun": current_dayun,
        "current_liunian": current_liunian,
    }

def _changsheng_stage(day_gan: str, zhi: str) -> str:
    start = _CHANGSHENG_START.get(day_gan)
    if not start or zhi not in _ZHI_ORDER:
        return ""
    si, zi = _ZHI_ORDER.index(start), _ZHI_ORDER.index(zhi)
    idx = (zi - si) % 12 if day_gan in _YANG_GAN else (si - zi) % 12
    return _CHANGSHENG_STAGES[idx]

def _shishen(day_master_gan: str, other_gan: str) -> str:
    dm_wx = _GAN_WUXING[day_master_gan]
    ot_wx = _GAN_WUXING[other_gan]
    is_same_polarity = (day_master_gan in _YANG_GAN) == (other_gan in _YANG_GAN)
    key = (dm_wx, ot_wx)
    entry = _SHISHEN_TABLE.get(key)
    if not entry:
        return "未知"
    return entry["同"] if is_same_polarity else entry["异"]

def _pillar_to_parts(pillar_str: str):
    s = str(pillar_str)
    return s[0], s[1]

def _assess_strength(ec, gender: str,
                     time_precision: TIME_PRECISION = "exact") -> dict:
    day_gan,  day_zhi   = _pillar_to_parts(ec.getDay())
    year_gan, year_zhi  = _pillar_to_parts(ec.getYear())
    month_gan, month_zhi = _pillar_to_parts(ec.getMonth())
    time_gan, time_zhi  = _pillar_to_parts(ec.getTime())
    dm_wx = _GAN_WUXING[day_gan]
    hour_known = time_precision != "unknown"

    generates = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
    controls  = {"木":"土","火":"金","土":"水","金":"木","水":"火"}
    generated_by  = {v: k for k, v in generates.items()}
    controlled_by = {v: k for k, v in controls.items()}

    support_wx = {dm_wx, generated_by[dm_wx]}
    drain_wx   = {generates[dm_wx], controls[dm_wx], controlled_by[dm_wx]}

    score = 0.0
    breakdown: list[str] = []

    month_hidden = _ZHI_HIDE_WEIGHTED.get(month_zhi) or [(month_gan, 2.0)]
    month_god = _shishen(day_gan, month_hidden[0][0])
    base = _MONTH_GOD_BASE.get(month_god, 0.0)
    score += base
    breakdown.append(f"得令·月令{month_zhi}({month_god}) {base:+.1f}")

    stage = _changsheng_stage(day_gan, month_zhi)
    if stage:
        stage_pts = _STAGE_SCORE.get(stage, 0.0)
        score += stage_pts
        breakdown.append(f"长生·日主在{month_zhi}为{stage} {stage_pts:+.1f}")

    root_branches = [("年支", year_zhi), ("日支", day_zhi)]
    if hour_known:
        root_branches.append(("时支", time_zhi))
    for label, zhi in root_branches:
        for gan, w in _ZHI_HIDE_WEIGHTED.get(zhi, []):
            gwx = _GAN_WUXING[gan]
            if gwx in support_wx:
                pts = round(w, 2)
                score += pts
                breakdown.append(f"得地·{label}{zhi}藏{gan}({gwx})帮身 {pts:+.2f}")
            elif gwx in drain_wx:
                pts = round(-w * 0.7, 2)
                score += pts
                breakdown.append(f"得地·{label}{zhi}藏{gan}({gwx})耗身 {pts:+.2f}")

    stem_slots = [("年干", year_gan), ("月干", month_gan)]
    if hour_known:
        stem_slots.append(("时干", time_gan))
    for label, gan in stem_slots:
        god = _shishen(day_gan, gan)
        if god in _SUPPORT_GODS:
            score += 1.5
            breakdown.append(f"得势·{label}{gan}({god})帮身 +1.5")
        else:
            score += -1.0
            breakdown.append(f"得势·{label}{gan}({god})耗身 -1.0")

    score = round(score, 2)

    STRONG_BAR, WEAK_BAR = 4.0, -2.0
    if score >= STRONG_BAR:
        strength, dist = "偏强", score - STRONG_BAR
    elif score <= WEAK_BAR:
        strength, dist = "偏弱", WEAK_BAR - score
    else:
        strength, dist = "中和", min(score - WEAK_BAR, STRONG_BAR - score)

    confidence = round(min(0.95, max(0.35, 0.45 + 0.09 * dist)), 2)
    if not hour_known:
        confidence = round(min(confidence, 0.70) * 0.9, 2)
    near_boundary = dist < 1.2

    branches = [year_zhi, day_zhi] + ([time_zhi] if hour_known else [])
    all_branches = [month_zhi] + branches
    stems = [year_gan, month_gan] + ([time_gan] if hour_known else [])
    def _benqi_wx(zhi: str) -> str:
        hid = _ZHI_HIDE_WEIGHTED.get(zhi)
        return _GAN_WUXING[hid[0][0]] if hid else ""
    benqi_wxs = [_benqi_wx(z) for z in all_branches]
    stem_wxs  = [_GAN_WUXING[g] for g in stems]
    yin_wx = generated_by[dm_wx]
    has_bijie = (dm_wx in benqi_wxs) or (dm_wx in stem_wxs)
    has_yin   = (yin_wx in benqi_wxs) or (yin_wx in stem_wxs)
    month_base = _MONTH_GOD_BASE.get(month_god, 0.0)

    special_pattern = None
    if month_base < 0 and not has_bijie and not has_yin and score <= WEAK_BAR - 4:
        special_pattern = "疑似从弱格（日主无根、满盘财官食伤，用神或当从势而非帮身）"
    elif month_base > 0 and score >= STRONG_BAR + 6:
        drain_present = any(w in drain_wx for w in benqi_wxs + stem_wxs)
        if not drain_present:
            special_pattern = "疑似从强/专旺格（日主极旺、无财官制泄，用神或当顺旺而非耗身）"

    if special_pattern:
        confidence = min(confidence, 0.3)
        near_boundary = True
        breakdown.append(f"⚠️ {special_pattern}：普通旺衰用神可能判反，建议人工复核")

    if strength == "偏弱":
        yong = sorted(w for w in support_wx if w)
        ji   = sorted(w for w in drain_wx if w)
    else:
        yong = sorted(w for w in drain_wx if w)
        ji   = sorted(w for w in support_wx if w)
    if not yong:
        yong = [generated_by[dm_wx]]

    return {
        "strength":      strength,
        "score":         score,
        "confidence":    confidence,
        "near_boundary": near_boundary,
        "breakdown":     breakdown,
        "yong_shen":     yong,
        "ji_shen":       ji,
        "special_pattern": special_pattern,
        "tiaohou_yong_shen": _TIAOHOU_BY_MONTH.get(month_zhi, []),
        "ge_ju":             _GE_JU_NAME.get(month_god, "普通格"),
    }

def build(solar_dt: str, gender: str,
          time_precision: TIME_PRECISION = "exact",
          lon: float = 121.47,
          tz: float = 8,
          use_true_solar: bool = True,
          current_year: int | None = None) -> dict:
    from datetime import datetime
    dt = datetime.fromisoformat(solar_dt)
    if current_year is None:
        current_year = datetime.now().year
    input_dt = dt

    time_adjustment = {
        "enabled": False,
        "input_time": input_dt.isoformat(timespec="minutes"),
        "effective_time": input_dt.isoformat(timespec="minutes"),
        "longitude_correction_minutes": 0.0,
        "equation_of_time_minutes": 0.0,
        "total_correction_minutes": 0.0,
    }
    if use_true_solar and time_precision != "unknown":
        dt, time_adjustment = _true_solar_datetime(dt, lon, tz)

    if time_precision == "unknown":
        hour, minute = 0, 0
    else:
        hour, minute = dt.hour, dt.minute

    solar  = Solar.fromYmdHms(dt.year, dt.month, dt.day, hour, minute, 0)
    lunar  = solar.getLunar()
    ec     = lunar.getEightChar()

    day_gan, day_zhi = _pillar_to_parts(ec.getDay())
    sa        = _assess_strength(ec, gender, time_precision)
    strength  = sa["strength"]
    yong_shen = sa["yong_shen"]
    ji_shen   = sa["ji_shen"]

    year_gan  = str(ec.getYear())[0]
    month_gan = str(ec.getMonth())[0]
    time_gan  = str(ec.getTime())[0] if time_precision != "unknown" else None

    ten_gods = {
        "year":  _shishen(day_gan, year_gan),
        "month": _shishen(day_gan, month_gan),
        "time":  _shishen(day_gan, time_gan) if time_gan else None,
    }

    natal_year_branch = str(ec.getYear())[1]
    luck = _build_luck(ec, gender, day_gan, current_year)
    tai_sui_branch = (luck.get("current_liunian") or {}).get("zhi")

    result = {
        "pillars": {
            "year":  str(ec.getYear()),
            "month": str(ec.getMonth()),
            "day":   str(ec.getDay()),
            "hour":  str(ec.getTime()) if time_precision != "unknown" else None,
        },
        "day_master":          day_gan,
        "day_master_strength": strength,
        "strength_score":       sa["score"],
        "strength_confidence":  sa["confidence"],
        "strength_near_boundary": sa["near_boundary"],
        "strength_breakdown":   sa["breakdown"],
        "special_pattern":      sa["special_pattern"],
        "yong_shen":  yong_shen,
        "ji_shen":    ji_shen,
        "tiaohou_yong_shen": sa["tiaohou_yong_shen"],
        "ge_ju":             sa["ge_ju"],
        "ten_gods":   ten_gods,
        "natal_year_branch": natal_year_branch,
        "tai_sui_branch": tai_sui_branch,
        "nayin": {
            "year":  str(ec.getYearNaYin()),
            "month": str(ec.getMonthNaYin()),
            "day":   str(ec.getDayNaYin()),
            "hour":  str(ec.getTimeNaYin()) if time_precision != "unknown" else None,
        },
        "luck": luck,
        "time_adjustment": time_adjustment,
        "boundary_warnings": _boundary_warnings(dt) if time_precision != "unknown" else [],
        "calculation_profile": CalculationProfile(
            calendar_type=CalendarType.SOLAR,
            is_true_solar_time=use_true_solar,
            time_precision=(
                TimePrecision.MINUTE if time_precision == "exact"
                else TimePrecision.HOUR if time_precision == "hour"
                else TimePrecision.UNKNOWN
            ),
            longitude=lon,
            timezone=tz,
            confidence_score=0.9 if time_precision == "exact" else 0.7 if time_precision == "hour" else 0.35,
            evidence_level=EvidenceLevel.HIGH if time_precision == "exact" else EvidenceLevel.MEDIUM if time_precision == "hour" else EvidenceLevel.LOW,
            warnings=_boundary_warnings(dt) if time_precision != "unknown" else ["出生时间未知，时柱与用神判断降级"],
        ).to_dict(),
        "degraded": time_precision == "unknown",
    }
    return result

