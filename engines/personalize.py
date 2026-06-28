
import json
from typing import Optional

GENERATES = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
CONTROLS  = {"木":"土","火":"金","土":"水","金":"木","水":"火"}
GENERATED_BY = {v:k for k,v in GENERATES.items()}
CONTROLLED_BY = {v:k for k,v in CONTROLS.items()}

GAN_WUXING = {
    "甲":"木","乙":"木","丙":"火","丁":"火","戊":"土",
    "己":"土","庚":"金","辛":"金","壬":"水","癸":"水",
}
ZHI_WUXING = {
    "子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火",
    "午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水",
}
YANG_GAN = {"甲","丙","戊","庚","壬"}

ZHI_HIDDEN = {
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
_QI_NAME = {2.0: "本气", 0.8: "中气", 0.5: "余气"}

ZHI_HE6 = {
    ("子","丑"):("土",10), ("寅","亥"):("木",8), ("卯","戌"):("火",8),
    ("辰","酉"):("金",8), ("巳","申"):("水",8), ("午","未"):("土",6),
}
ZHI_CHONG6 = {
    frozenset(["子","午"]), frozenset(["丑","未"]), frozenset(["寅","申"]),
    frozenset(["卯","酉"]), frozenset(["辰","戌"]), frozenset(["巳","亥"]),
}
ZHI_XING = {
    frozenset(["寅","巳","申"]), frozenset(["丑","戌","未"]),
    frozenset(["子","卯"]),
}
ZHI_HAI = {
    frozenset(["子","未"]), frozenset(["丑","午"]), frozenset(["寅","巳"]),
    frozenset(["卯","辰"]), frozenset(["申","亥"]), frozenset(["酉","戌"]),
}
ZHI_SANHE = [
    frozenset(["申","子","辰"]), frozenset(["亥","卯","未"]),
    frozenset(["寅","午","戌"]), frozenset(["巳","酉","丑"]),
]

TIANYI_MAP = {
    "甲":["丑","未"],"戊":["丑","未"],
    "乙":["子","申"],"己":["子","申"],
    "丙":["亥","酉"],"丁":["亥","酉"],
    "庚":["丑","未"],"辛":["寅","午"],
    "壬":["卯","巳"],"癸":["卯","巳"],
}
YIMA_MAP = {
    "申":"寅","子":"寅","辰":"寅",
    "亥":"巳","卯":"巳","未":"巳",
    "寅":"申","午":"申","戌":"申",
    "巳":"亥","酉":"亥","丑":"亥",
}
TAOHUA_MAP = {
    "申":"酉","子":"酉","辰":"酉",
    "亥":"子","卯":"子","未":"子",
    "寅":"卯","午":"卯","戌":"卯",
    "巳":"午","酉":"午","丑":"午",
}

SHENSHA_SCORE = {
    "天德合": 7, "月德合": 7, "天德": 9, "月德": 9, "天赦": 8, "天愿": 6,
    "天恩": 5, "天医": 5, "母仓": 4, "时德": 4, "天喜": 4, "三合": 5,
    "六合": 4, "福生": 4, "阳德": 3, "阴德": 3, "金匮": 4, "宝光": 4,
    "玉堂": 4, "司命": 3, "青龙": 5, "明堂": 4, "除神": 2, "益后": 3,
    "续世": 3, "鸣吠": 2, "要安": 2, "解神": 3,
    "岁破": -12, "月破": -10, "大耗": -8, "小耗": -4, "四废": -8,
    "四绝": -6, "四离": -6, "三煞": -10, "岁煞": -8, "月煞": -7,
    "灾煞": -7, "劫煞": -6, "天刑": -5, "朱雀": -4, "白虎": -6,
    "天牢": -4, "玄武": -4, "勾陈": -3, "月厌": -5, "大煞": -6,
    "游祸": -4, "天吏": -4, "死神": -5, "死气": -3, "月害": -3,
    "重日": -3, "复日": -3, "八专": -2, "触水龙": -2, "归忌": -3,
    "血支": -3, "血忌": -3, "五虚": -3, "土符": -2, "往亡": -4,
}
_SHENSHA_GUIREN = ("天德", "月德", "天赦", "天恩", "天医", "天喜")
_SHENSHA_CLAMP = 18

YI_WUXING_HINT = {
    "祭祀":"水", "祈福":"火", "出行":"木", "嫁娶":"土",
    "签约":"金", "开业":"火", "动土":"土", "装修":"金",
    "投资":"金", "借贷":"水", "诉讼":"金", "求医":"水",
    "旅行":"木", "搬家":"木", "纳财":"金", "开仓":"金",
}
_YIMA_WORDS  = {"出行", "旅行", "搬家", "移徙"}
_TAOHUA_WORDS = {"嫁娶", "纳采", "订盟"}

FLAG_KEYS = ["冲日主", "冲流年太岁", "贵人到", "驿马动", "桃花到", "用神得力"]

_TIER_BOUNDS = (38, 52, 63)

def _wuxing(gan_or_zhi: str) -> str:
    return GAN_WUXING.get(gan_or_zhi) or ZHI_WUXING.get(gan_or_zhi, "")

def _sheng_ke_score(dm_wx: str, target_wx: str) -> int:
    if dm_wx == target_wx:      return 1
    if GENERATES[dm_wx] == target_wx: return 2
    if GENERATED_BY[dm_wx] == target_wx: return 0
    if CONTROLS[dm_wx] == target_wx: return -2
    if CONTROLLED_BY.get(dm_wx) == target_wx: return -1
    return 0

def _sk_word(dm_wx: str, target_wx: str) -> str:
    if dm_wx == target_wx:                return "同气比助"
    if GENERATES[dm_wx] == target_wx:     return "日主生之·泄秀"
    if GENERATED_BY[dm_wx] == target_wx:  return "生身·印星"
    if CONTROLS[dm_wx] == target_wx:      return "日主克之·财星"
    if CONTROLLED_BY.get(dm_wx) == target_wx: return "克身·官杀"
    return "无涉"

def _zhi_relation(zhi_a: str, zhi_b: str) -> tuple[str, int]:
    pair = frozenset([zhi_a, zhi_b])
    ordered = tuple(sorted([zhi_a, zhi_b]))
    if ordered in ZHI_HE6:
        _, score = ZHI_HE6[ordered]
        return "六合", score
    if pair in ZHI_CHONG6:
        return "六冲", -15
    for group in ZHI_XING:
        if zhi_a in group and zhi_b in group and zhi_a != zhi_b:
            return "相刑", -8
    if pair in ZHI_HAI:
        return "六害", -5
    for group in ZHI_SANHE:
        if zhi_a in group and zhi_b in group and zhi_a != zhi_b:
            return "半三合", 4
    return "无", 0

def _natal_zhis(pillars: dict) -> list[str]:
    zs = [
        str(pillars.get("year", ""))[1:2],
        str(pillars.get("month", ""))[1:2],
        str(pillars.get("day", ""))[1:2],
    ]
    if pillars.get("hour"):
        zs.append(str(pillars["hour"])[1:2])
    return [z for z in zs if z]

def _precision_state(profile: dict) -> tuple[str, bool]:
    meta = profile.get("meta", {})
    precision = meta.get("time_precision")
    if precision not in ("exact", "hour", "unknown"):
        precision = "unknown" if profile.get("degraded") else "exact"
    hour_known = bool(profile.get("bazi", {}).get("pillars", {}).get("hour"))
    if precision == "unknown":
        hour_known = False
    return precision, hour_known

class _ScoreSheet:
    def __init__(self):
        self.breakdown: list[dict] = []

    def add(self, label: str, delta: float, detail: str):
        delta = round(delta, 1)
        if delta == 0 and not label.startswith("基础"):
            return
        self.breakdown.append({"label": label, "delta": delta, "detail": detail})

    def total(self) -> float:
        return sum(b["delta"] for b in self.breakdown)

def _compute_flags(day_gan: str, day_zhi: str, profile: dict) -> dict:
    bazi    = profile["bazi"]
    dm_gan  = bazi["day_master"]
    pillars = bazi["pillars"]

    natal_zhis = _natal_zhis(pillars)
    tai_sui_branch = bazi.get("tai_sui_branch", "")

    flags = {k: False for k in FLAG_KEYS}

    dm_wx     = _wuxing(dm_gan)
    day_wx    = _wuxing(day_gan)
    dayzhi_wx = _wuxing(day_zhi)

    if CONTROLS.get(day_wx) == dm_wx:
        flags["冲日主"] = True

    if frozenset([day_zhi, tai_sui_branch]) in ZHI_CHONG6:
        flags["冲流年太岁"] = True

    if day_zhi in TIANYI_MAP.get(dm_gan, []):
        flags["贵人到"] = True

    for nz in natal_zhis:
        if YIMA_MAP.get(nz) == day_zhi:
            flags["驿马动"] = True

    for nz in natal_zhis:
        if TAOHUA_MAP.get(nz) == day_zhi:
            flags["桃花到"] = True

    yong = set(bazi.get("yong_shen", []))
    if day_wx in yong or dayzhi_wx in yong:
        flags["用神得力"] = True

    return flags

def _score_dimensions(sheet: _ScoreSheet, day_gan: str, day_zhi: str,
                      profile: dict, flags: dict, hour_known: bool) -> None:
    bazi    = profile["bazi"]
    dm_gan  = bazi["day_master"]
    dm_wx   = _wuxing(dm_gan)
    pillars = bazi["pillars"]

    day_wx = _wuxing(day_gan)

    sheet.add("基础分", 50, "传统老黄历中性起评 50")

    sk = _sheng_ke_score(dm_wx, day_wx)
    sheet.add("日干生克", sk * 5,
              f"日干{day_gan}({day_wx}) 对日主{dm_gan}({dm_wx})：{_sk_word(dm_wx, day_wx)}")

    hidden = ZHI_HIDDEN.get(day_zhi, [])
    hidden_total = 0.0
    parts = []
    for gan, w in hidden:
        gwx = _wuxing(gan)
        contrib = _sheng_ke_score(dm_wx, gwx) * w * 0.8
        hidden_total += contrib
        parts.append(f"{_QI_NAME.get(w,'?')}{gan}({gwx},{_sk_word(dm_wx, gwx)})")
    if hidden:
        sheet.add("日支藏干", hidden_total, f"日支{day_zhi}藏 " + "、".join(parts))

    rel_total = 0
    rel_parts = []
    for nz in _natal_zhis(pillars):
        rel, pts = _zhi_relation(day_zhi, nz)
        if pts != 0:
            rel_total += pts
            rel_parts.append(f"与{nz}{rel}({pts:+d})")
    if rel_parts:
        sheet.add("地支关系", rel_total, "日支" + "、".join(rel_parts))

    yong = set(bazi.get("yong_shen", []))
    ji   = set(bazi.get("ji_shen", []))
    sc_conf   = bazi.get("strength_confidence", 1.0)
    sc_factor = round(min(1.0, 0.55 + 0.5 * sc_conf), 2)
    w_factor  = (1.0 if hour_known else 0.6) * sc_factor
    _notes = ([] if hour_known else ["生时未知·降权"]) + \
             ([f"旺衰置信{sc_conf:.2f}·降权"] if sc_factor < 0.95 else [])
    note = f"（{'·'.join(_notes)}）" if _notes else ""

    if day_wx in yong:
        sheet.add("用神·日干", 10 * w_factor, f"日干五行{day_wx}属用神{note}")
    if day_wx in ji:
        sheet.add("忌神·日干", -10 * w_factor, f"日干五行{day_wx}属忌神{note}")
    for gan, w in hidden:
        gwx = _wuxing(gan)
        unit = 6 * (w / 2.0)
        if gwx in yong:
            sheet.add("用神·藏干", unit * w_factor,
                      f"日支藏{_QI_NAME.get(w,'?')}{gan}({gwx})属用神{note}")
        if gwx in ji:
            sheet.add("忌神·藏干", -unit * w_factor,
                      f"日支藏{_QI_NAME.get(w,'?')}{gan}({gwx})属忌神{note}")

    if flags["贵人到"]:
        sheet.add("天乙贵人", 6, "日支临天乙贵人位")
    if flags["驿马动"]:
        sheet.add("驿马动", 3, "日支引动本命驿马，主走动/进取")
    if flags["桃花到"]:
        sheet.add("桃花到", 2, "日支临本命桃花，主人缘/情感")
    if flags["冲日主"]:
        sheet.add("冲日主", -12, "当日五行回克日主，身心易受扰")
    if flags["冲流年太岁"]:
        sheet.add("冲流年太岁", -10, "日支冲流年太岁，岁运略有摩擦")

    tiaohou = set(bazi.get("tiaohou_yong_shen", []))
    if tiaohou:
        if day_wx in tiaohou:
            sheet.add("调候·日干", 4, f"日干{day_wx}合季节调候所喜，寒暖得宜")
        for gan, w in hidden:
            gwx = _wuxing(gan)
            if gwx in tiaohou:
                sheet.add("调候·藏干", round(3 * (w / 2.0), 1),
                          f"日支藏{_QI_NAME.get(w,'?')}{gan}({gwx})合季节调候")

def _score_shensha(sheet: _ScoreSheet, shensha: list, flags: dict) -> None:
    if not shensha:
        return
    total = 0
    matched = []
    for s in shensha:
        s = str(s)
        for key, val in SHENSHA_SCORE.items():
            if key in s:
                total += val
                matched.append(f"{key}({val:+d})")
                if val > 0 and any(g in s for g in _SHENSHA_GUIREN):
                    flags["贵人到"] = True
                break
    if total == 0:
        return
    clamped = max(-_SHENSHA_CLAMP, min(_SHENSHA_CLAMP, total))
    detail = "当日神煞：" + "、".join(matched[:8])
    if clamped != total:
        detail += f"（原{total:+d}→封顶{clamped:+d}）"
    sheet.add("神煞等级", clamped, detail)

def _confidence(score: int, precision: str, hour_known: bool,
                strength_conf: float = 1.0) -> tuple[float, bool, Optional[str]]:
    base = {"exact": 0.92, "hour": 0.88, "unknown": 0.6}.get(precision, 0.75)
    margin = min(abs(score - b) for b in _TIER_BOUNDS)
    near_boundary = margin <= 3
    if near_boundary:
        base -= 0.08
    if strength_conf < 0.6:
        base -= 0.06
    conf = round(max(0.3, min(0.99, base)), 2)

    reason = None
    if not hour_known:
        reason = "生时未知，时柱缺失：已剥离/降权时辰敏感维度（用神×0.6），结论置信度下调，仅供参考"
    elif strength_conf < 0.6:
        reason = f"日主旺衰接近中和（旺衰置信{strength_conf:.2f}），用神方向不稳，吉凶判断仅供参考"
    elif near_boundary:
        reason = f"综合分 {score} 贴近分档边界，吉凶倾向不稳，建议结合当日实际"
    return conf, near_boundary, reason

def _reweight_yiji(base_yi: list, base_ji: list,
                   flags: dict, profile: dict,
                   score: int, degraded: bool) -> tuple[list, list]:
    bazi  = profile["bazi"]
    yong  = set(bazi.get("yong_shen", []))
    ji_sh = set(bazi.get("ji_shen", []))
    tiaohou = set(bazi.get("tiaohou_yong_shen", []))
    cap   = 4 if degraded else 5

    def item_score(word: str) -> int:
        hint_wx = YI_WUXING_HINT.get(word, "")
        s = 3
        if hint_wx in yong:     s += 1
        if hint_wx in tiaohou:  s += 1
        if hint_wx in ji_sh:    s -= 2
        if flags["贵人到"]:      s += 1
        if flags["用神得力"]:    s += 1
        if word in _YIMA_WORDS  and flags["驿马动"]:  s += 1
        if word in _TAOHUA_WORDS and flags["桃花到"]: s += 1
        if flags["冲日主"]:      s -= 2
        if flags["冲流年太岁"]:  s -= 1
        return max(1, min(cap, s))

    def yi_reason(word: str) -> str:
        parts = []
        hint_wx = YI_WUXING_HINT.get(word, "")
        if hint_wx in yong:
            parts.append(f"{hint_wx}属用神")
        if hint_wx in tiaohou:
            parts.append(f"{hint_wx}合季节调候")
        if flags["贵人到"]:
            parts.append("天乙贵人到位")
        if flags["用神得力"]:
            parts.append("当日用神得令")
        if word in _YIMA_WORDS and flags["驿马动"]:
            parts.append("驿马引动利走动")
        if word in _TAOHUA_WORDS and flags["桃花到"]:
            parts.append("桃花临门利姻缘")
        out = "；".join(parts) if parts else "传统吉日"
        if degraded:
            out += "（生时未知·低置信）"
        return out

    def ji_reason(word: str) -> str:
        parts = []
        hint_wx = YI_WUXING_HINT.get(word, "")
        if hint_wx in ji_sh:
            parts.append(f"{hint_wx}属忌神")
        if flags["冲日主"]:
            parts.append("日干克日主")
        if flags["冲流年太岁"]:
            parts.append("冲太岁")
        out = "；".join(parts) if parts else "传统忌日"
        if degraded:
            out += "（生时未知·低置信）"
        return out

    personal_yi = []
    demoted_to_ji = []

    for w in base_yi:
        s = item_score(w)
        hint_wx = YI_WUXING_HINT.get(w, "")
        if hint_wx in ji_sh and s <= 1:
            r = f"传统宜，但{hint_wx}属忌神，降级为忌"
            if degraded:
                r += "（生时未知·低置信）"
            demoted_to_ji.append({"item": w, "strength": 2, "reason": r})
        else:
            personal_yi.append({"item": w, "strength": s, "reason": yi_reason(w)})

    personal_ji = list(demoted_to_ji)
    for w in base_ji:
        s = item_score(w)
        personal_ji.append({"item": w, "strength": s, "reason": ji_reason(w)})

    personal_yi.sort(key=lambda x: -x["strength"])
    personal_ji.sort(key=lambda x: -x["strength"])

    return personal_yi, personal_ji

def _tier(score: int, flags: dict, confidence: float, degraded: bool) -> str:
    if flags.get("冲流年太岁") or flags.get("冲日主"):
        return "忌" if score < 40 else "平"
    any_bonus = flags.get("用神得力") or flags.get("贵人到") or flags.get("驿马动")
    da_ji_bar = 66 if degraded else 63
    if score >= da_ji_bar and any_bonus and confidence >= 0.55:
        return "大吉"
    if score >= 52:
        return "吉"
    if score >= 38:
        return "平"
    return "忌"

def _degraded_neutral(day: dict, reason: str) -> dict:
    base_yi = day.get("base_yi", []) or []
    base_ji = day.get("base_ji", []) or []
    return {
        "date":         day.get("date"),
        "score":        50,
        "personal_yi":  [{"item": w, "strength": 3,
                          "reason": "命盘数据不足，采用传统宜（中性）"} for w in base_yi],
        "personal_ji":  [{"item": w, "strength": 3,
                          "reason": "命盘数据不足，采用传统忌（中性）"} for w in base_ji],
        "flags":        {k: False for k in FLAG_KEYS},
        "tier":         "平",
        "short_sign":   None,
        "confidence":   0.3,
        "degraded":     True,
        "degrade_reason": reason,
        "near_boundary": False,
        "score_breakdown": [{"label": "基础分", "delta": 50, "detail": reason}],
    }

def build(profile: dict, day: dict) -> dict:
    bazi = profile.get("bazi")
    if not bazi or not bazi.get("day_master") or not bazi.get("pillars"):
        return _degraded_neutral(day, "缺失八字命盘核心数据（day_master/pillars）")

    ganzhi  = day["ganzhi"]
    day_str = ganzhi["day"]
    if not day_str or len(day_str) < 2:
        return _degraded_neutral(day, "当日干支数据异常")
    day_gan, day_zhi = day_str[0], day_str[1]

    precision, hour_known = _precision_state(profile)
    degraded = not hour_known

    flags = _compute_flags(day_gan, day_zhi, profile)

    sheet = _ScoreSheet()
    _score_dimensions(sheet, day_gan, day_zhi, profile, flags, hour_known)
    _score_shensha(sheet, day.get("shensha", []), flags)

    score = int(round(max(0, min(100, sheet.total()))))

    confidence, near_boundary, degrade_reason = _confidence(
        score, precision, hour_known, bazi.get("strength_confidence", 1.0))

    special_pattern = bazi.get("special_pattern")
    if special_pattern:
        confidence = min(confidence, 0.45)
        near_boundary = True
        degrade_reason = (f"{special_pattern}；普通用神方向可能不适用，"
                          f"吉凶判断仅供参考，建议人工复核")

    p_yi, p_ji = _reweight_yiji(
        day.get("base_yi", []),
        day.get("base_ji", []),
        flags, profile, score, degraded,
    )

    tier = _tier(score, flags, confidence, degraded)

    return {
        "date":         day["date"],
        "score":        score,
        "personal_yi":  p_yi,
        "personal_ji":  p_ji,
        "flags":        flags,
        "tier":         tier,
        "short_sign":   None,
        "confidence":     confidence,
        "degraded":       degraded,
        "degrade_reason": degrade_reason,
        "near_boundary":  near_boundary,
        "special_pattern": special_pattern,
        "score_breakdown": sheet.breakdown,
    }

