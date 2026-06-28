
import os
import html
from datetime import date, timedelta

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

_TIER_CLASS = {
    "命定时刻": "t-destined",
    "大吉":     "t-daji",
    "吉":       "t-ji",
    "平":       "t-ping",
    "忌":       "t-bad",
    "凶":       "t-xiong",
}

def _load_template(name: str) -> str:
    path = os.path.join(TEMPLATES_DIR, name)
    with open(path, encoding="utf-8") as f:
        return f.read()

def _fill(template: str, slots: dict, raw_keys: set = frozenset()) -> str:
    for k, v in slots.items():
        sval = str(v) if k in raw_keys else html.escape(str(v))
        template = template.replace("{{" + k + "}}", sval)
    return template

def _item_names(items: list[dict], limit: int = 3) -> list[str]:
    out = []
    for item in items[:limit]:
        word = str(item.get("item", "")).strip()
        if word and word != "无" and word not in out:
            out.append(word)
    return out

def _join_items(items: list[str], fallback: str = "整理节奏") -> str:
    return "、".join(items) if items else fallback

def _western_summary(profile: dict) -> str:
    western = profile.get("western", {}) or {}
    def sign_of(value):
        if isinstance(value, dict):
            return value.get("sign", "未标明")
        return value or "未标明"
    sun = sign_of(western.get("sun"))
    moon = sign_of(western.get("moon"))
    asc = sign_of(western.get("ascendant"))
    parts = [
        f"太阳{sun}",
        f"月亮{moon}",
        f"上升{asc}",
    ]
    return " / ".join(parts)

def _vedic_summary(profile: dict) -> str:
    vedic = profile.get("vedic", {}) or {}
    vim = vedic.get("vimshottari", {}) if isinstance(vedic.get("vimshottari"), dict) else {}
    maha = vim.get("mahadasha") or vim.get("current_mahadasha") or "未标明"
    nak = vedic.get("moon_nakshatra") or "未标明"
    pada = vedic.get("moon_pada") or "未标明"
    return f"月宿{nak} Pada {pada} / 大运{maha}"

def _ziwei_summary(profile: dict) -> str:
    ziwei = profile.get("ziwei", {}) or {}
    soul = ziwei.get("soul_palace", {}) if isinstance(ziwei.get("soul_palace"), dict) else {}
    body = ziwei.get("body_palace", {}) if isinstance(ziwei.get("body_palace"), dict) else {}
    soul_name = soul.get("name") or soul.get("branch") or "未标明"
    body_name = body.get("name") or body.get("branch") or "未标明"
    stars = soul.get("major_stars") or []
    star_text = "、".join(stars[:2]) if stars else "主星未标明"
    return f"命宫{soul_name} / 身宫{body_name} / {star_text}"

def _bazi_summary(profile: dict) -> str:
    bazi = profile.get("bazi", {}) or {}
    yong = "、".join(bazi.get("yong_shen") or []) or "未标明"
    ji = "、".join(bazi.get("ji_shen") or []) or "未标明"
    return f"{bazi.get('day_master', '未标明')}日主 / {bazi.get('ge_ju', '未标明')} / 用{yong} 忌{ji}"

def _build_system_tiles(profile: dict) -> str:
    rows = [
        ("八字", _bazi_summary(profile)),
        ("紫微", _ziwei_summary(profile)),
        ("印占", _vedic_summary(profile)),
        ("西占", _western_summary(profile)),
    ]
    return "\n".join(
        f'<div class="system-tile"><span>{html.escape(title)}</span><b>{html.escape(text)}</b></div>'
        for title, text in rows
    )

def _action_label(pers: dict) -> str:
    tier = pers.get("tier")
    if tier in ("大吉", "命定时刻"):
        return "推进窗口"
    if tier in ("忌", "凶"):
        return "避坑窗口"
    if pers.get("score", 50) >= 52:
        return "顺势整理"
    return "低速观察"

def _strategy_line(days: list[dict]) -> str:
    good = sum(1 for d in days if d["kind"] == "good")
    avoid = sum(1 for d in days if d["kind"] == "avoid")
    if good >= avoid + 2:
        return "这段时间适合把想法推到台前，先做出一个看得见的成果。"
    if avoid >= good + 2:
        return "这段时间不急着定局，先收口、补资料、降低承诺成本。"
    return "这段时间一边有机会，一边也有摩擦；适合小步推进，不适合一次押满。"

def _profile_reading_line(profile: dict) -> str:
    bazi = profile.get("bazi", {}) or {}
    western = profile.get("western", {}) or {}
    vedic = profile.get("vedic", {}) or {}
    ziwei = profile.get("ziwei", {}) or {}
    day_master = bazi.get("day_master", "这张盘")
    ge_ju = bazi.get("ge_ju", "本命结构")
    strength = bazi.get("day_master_strength", "")
    sun = western.get("sun")
    moon = western.get("moon")
    if isinstance(sun, dict):
        sun = sun.get("sign")
    if isinstance(moon, dict):
        moon = moon.get("sign")
    nak = vedic.get("moon_nakshatra")
    vim = vedic.get("vimshottari", {}) if isinstance(vedic.get("vimshottari"), dict) else {}
    maha = vim.get("mahadasha")
    body = ziwei.get("body_palace", {}) if isinstance(ziwei.get("body_palace"), dict) else {}
    body_name = body.get("name")

    sentence = f"这张盘以{day_master}日主为底，{ge_ju}"
    if strength:
        sentence += f"、日主{strength}"
    if sun or moon:
        sentence += f"；西占的{('太阳' + sun) if sun else ''}{('、月亮' + moon) if moon else ''}让情绪和直觉更容易参与判断"
    if nak or maha:
        sentence += f"；印占的{nak or '月宿'}与{maha or '当前'}大运，把阶段主题推向学习、信念和方向感"
    if body_name:
        sentence += f"；紫微身宫落在{body_name}，说明行动最后还是要落回现实安全感。"
    else:
        sentence += "。"
    return sentence

def _window_reading(days: list[dict], scores: dict[str, int]) -> str:
    good = sum(1 for d in days if d["kind"] == "good")
    avoid = sum(1 for d in days if d["kind"] == "avoid")
    if scores["risk"] >= 60 or avoid > good:
        return "未来30天不是不能动，而是不要在情绪最满的时候把话说死、把决定做绝。先把关键承诺、见面、材料和边界排清楚，真正要冲的事留给推进窗口。"
    if scores["momentum"] >= 70:
        return "未来30天有一股可以借的顺风，适合把想了很久的事推到台前：递材料、见关键人、公开表达、启动计划，都可以集中放在推进窗口里。"
    return "未来30天更像整理期。不是没有机会，而是机会需要先被筛选：哪些值得继续，哪些只是消耗，先分清楚，再把动作放大。"

def _action_scores(days: list[dict]) -> dict[str, int]:
    if not days:
        return {"momentum": 50, "stability": 50, "risk": 50, "focus": 50}
    avg = sum(d["score"] for d in days) / len(days)
    avoid = sum(1 for d in days if d["kind"] == "avoid")
    good = sum(1 for d in days if d["kind"] == "good")
    destined = sum(1 for d in days if d["is_destined"])
    return {
        "momentum": max(35, min(96, int(avg + good * 2))),
        "stability": max(35, min(96, int(72 - avoid * 4 + good))),
        "risk": max(20, min(88, int(avoid * 12 + (60 - avg) * 0.6))),
        "focus": max(35, min(96, int(62 + destined * 10 + good * 2))),
    }

def _build_action_metric_rows(scores: dict[str, int]) -> str:
    labels = [
        ("推进势能", "momentum"),
        ("稳定程度", "stability"),
        ("风险噪音", "risk"),
        ("聚焦指数", "focus"),
    ]
    return "\n".join(
        f"""
<div class="metric-row">
  <span class="metric-name">{html.escape(label)}</span>
  <span class="metric-bar"><i style="width:{scores[key]}%"></i></span>
  <span class="metric-score">{scores[key]}</span>
</div>"""
        for label, key in labels
    )

def _build_calendar_rows(days: list[dict]) -> str:
    rows = []
    for d in days[:10]:
        action = _join_items(d["yi"] if d["kind"] != "avoid" else d["ji"], "整理节奏")
        rows.append(f"""
<div class="calendar-row">
  <span>{html.escape(d["date"][5:])}</span>
  <b>{html.escape(d["tier"])}</b>
  <em>{html.escape(action)}</em>
  <i>{int(d["score"])}</i>
</div>""")
    return "\n".join(rows) or '<div class="mini-empty">暂无可展示窗口</div>'

def _action_advice(scores: dict[str, int]) -> str:
    if scores["risk"] >= 60:
        return "这30天不适合把所有事情一次推满。先处理关键承诺、合同、见面和沟通边界，重要决定留出复盘时间。"
    if scores["momentum"] >= 70:
        return "这30天适合主动推进：公开表达、递交材料、见关键人、启动新计划都可以集中安排在推进窗口。"
    return "这30天更适合稳步整理，把手上的事做顺，把关系和资源重新排队，等势能更清晰时再放大动作。"

def render_treasure_map(profile: dict, month_str: str | None = None) -> str:
    from engines.daily import build as daily_build
    from engines.personalize import build as p_build
    from engines.ics_builder import _is_destined_moment

    if month_str:
        start = date.fromisoformat(month_str + "-01")
    else:
        start = date.today()
    days_ahead = 30
    end = start + timedelta(days=days_ahead - 1)

    days = []
    for offset in range(days_ahead):
        d = start + timedelta(days=offset)
        d_str = d.isoformat()
        try:
            day_data = daily_build(d_str)
            pers = p_build(profile, day_data)
            tier = pers["tier"]
            is_destined = _is_destined_moment(profile, day_data)
            kind = "good" if tier == "大吉" else ("avoid" if tier in ("忌", "凶") else "neutral")
            yi = _item_names(pers.get("personal_yi", []), 3)
            ji = _item_names(pers.get("personal_ji", []), 3)
            days.append({
                "date": d_str,
                "day": d.day,
                "weekday": "一二三四五六日"[d.weekday()],
                "ganzhi": day_data["ganzhi"]["day"],
                "score": pers["score"],
                "tier": "命定时刻" if is_destined else tier,
                "label": _action_label(pers),
                "yi": yi,
                "ji": ji,
                "kind": "good" if is_destined else kind,
                "is_destined": is_destined,
            })
        except Exception:
            continue

    ranked = sorted(days, key=lambda x: (x["is_destined"], x["kind"] == "good", x["score"]), reverse=True)
    good_windows = [d for d in ranked if d["kind"] == "good"][:3]
    avoid_windows = sorted([d for d in days if d["kind"] == "avoid"], key=lambda x: x["score"])[:2]
    if len(good_windows) < 3:
        good_windows += [d for d in ranked if d not in good_windows and d["kind"] == "neutral"][:3 - len(good_windows)]
    if len(avoid_windows) < 2:
        avoid_windows += sorted([d for d in days if d not in avoid_windows], key=lambda x: x["score"])[:2 - len(avoid_windows)]

    key_windows = good_windows + avoid_windows
    cards_html = _build_action_cards(good_windows, "good") + _build_action_cards(avoid_windows, "avoid")
    scores = _action_scores(days)
    avg_score = int(sum(d["score"] for d in days) / len(days)) if days else 50

    user_name = profile["meta"]["name"]
    day_master = profile["bazi"]["day_master"]
    yong_shen  = "·".join(profile["bazi"].get("yong_shen", []))

    template = _load_template("treasure_map.html")
    return _fill(template, {
        "USER_NAME":   user_name,
        "RANGE":       f"{start.isoformat()} - {end.isoformat()}",
        "DAY_MASTER":  day_master,
        "YONG_SHEN":   yong_shen,
        "OVERALL_SCORE": avg_score,
        "GOOD_COUNT":  len(good_windows),
        "AVOID_COUNT": len(avoid_windows),
        "STRATEGY":    _window_reading(days, scores),
        "BEST_ACTIONS": _join_items(_item_names([{"item": item} for d in good_windows for item in d["yi"]], 4)),
        "AVOID_ACTIONS": _join_items(_item_names([{"item": item} for d in avoid_windows for item in d["ji"]], 4), "大额承诺"),
        "SYSTEM_TILES": _build_system_tiles(profile),
        "METRIC_ROWS": _build_action_metric_rows(scores),
        "CALENDAR_ROWS": _build_calendar_rows(sorted(key_windows, key=lambda x: x["date"])),
        "ACTION_ADVICE": _profile_reading_line(profile),
        "CARDS":       cards_html,
        "GENERATED_AT": date.today().isoformat(),
    }, raw_keys={"CARDS", "SYSTEM_TILES", "METRIC_ROWS", "CALENDAR_ROWS"})

def _build_action_cards(days: list[dict], group: str) -> str:
    if not days:
        return ""

    parts = []
    for d in days:
        badge = "机会" if group == "good" else "避坑"
        badge_cls = "destined" if group == "good" else "avoid"
        title = _join_items(d["yi"] if group == "good" else d["ji"], "整理节奏")
        subtitle = "适合：" + _join_items(d["yi"], "小步推进") if group == "good" else "避开：" + _join_items(d["ji"], "冲动决定")
        esc = lambda x: html.escape(str(x))
        parts.append(f"""
<div class="day-card {badge_cls}">
  <div class="day-header">
    <span class="day-num">{int(d['day'])}</span>
    <span class="day-week">周{esc(d['weekday'])}</span>
    <span class="destined-badge">{esc(badge)}</span>
  </div>
  <div class="ganzhi">{esc(d['ganzhi'])}</div>
  <div class="short-sign">{esc(d['label'])}｜{esc(title)}</div>
  <div class="yi-items">{esc(subtitle)}</div>
  <div class="nakshatra">{esc(d['date'])}</div>
  <div class="score-bar">
    <div class="score-fill" style="width:{int(d['score'])}%"></div>
  </div>
</div>""")
    return "\n".join(parts)

def _profile_role(profile: dict) -> str:
    dm = profile.get("bazi", {}).get("day_master", "")
    if dm in ("甲", "丙", "戊", "庚", "壬"):
        return "推动者"
    return "稳定器"

def _relation_keywords(profile_a: dict, profile_b: dict) -> tuple[str, str, str]:
    a_wx = (profile_a.get("bazi", {}).get("yong_shen") or [""])[0]
    b_wx = (profile_b.get("bazi", {}).get("yong_shen") or [""])[0]
    if a_wx and a_wx == b_wx:
        return "同频互补", "这段关系最强的地方，是两个人很容易在某些底层需求上对上号；但也因为太像，固执起来谁都不愿意先退。", "共同目标要说清楚。不要只确认情绪，要把时间表、边界和下一步讲出来。"
    if {a_wx, b_wx} & {"水", "木"}:
        return "慢热生长", "这段关系不是靠一瞬间定生死的类型。它需要空间、节奏和反复确认，越催越容易乱，越稳定越容易长出信任。", "少用试探，多用明确的小约定。关系能不能走下去，很多时候看节奏能不能被照顾。"
    return "强吸引高摩擦", "这段关系容易互相点燃：靠近时很有能量，节奏不齐时也容易互相消耗。吸引是真的，摩擦也不是假的。", "重要决定先缓一天。等情绪退潮以后，再谈需求、方案和边界。"

def _relation_points(keyword: str, label_a: str, label_b: str) -> tuple[str, str]:
    if keyword == "同频互补":
        return (
            f"{label_a}和{label_b}容易很快听懂对方在意什么，适合一起定计划、做长期安排。真正的加分点不是谁迁就谁，而是把同一个方向拆成可执行的小步骤。",
            "最怕两个人都觉得“我已经懂你了”，于是跳过沟通。默契一旦被当成默认同意，就很容易从亲近变成较劲。",
        )
    if keyword == "慢热生长":
        return (
            "这段关系的优势在于耐心和滋养感。稳定陪伴、共同学习、规律见面，比突然的浓烈表达更能加分。",
            "最怕用忽冷忽热测试对方，也怕把沉默误读成拒绝。边界、回复频率和期待要提前说清楚，不要让猜测替你们做决定。",
        )
    return (
        "吸引力来自彼此能激活对方的行动面，适合一起做有目标感的事：旅行、项目、运动、公开表达。能量被用在创造上，关系就会亮起来。",
        "高摩擦关系最怕在情绪最高点做结论。重要话题留到第二天，把指责改成具体请求，把试探改成直接确认。",
    )

def _first_item(values: list | tuple | None, fallback: str = "未标明") -> str:
    return str(values[0]) if values else fallback

def _compatibility_scores(profile_a: dict, profile_b: dict, keyword: str) -> dict[str, int]:
    bazi_a = profile_a.get("bazi", {})
    bazi_b = profile_b.get("bazi", {})
    same_need = bool(set(bazi_a.get("yong_shen") or []) & set(bazi_b.get("yong_shen") or []))
    same_avoid = bool(set(bazi_a.get("ji_shen") or []) & set(bazi_b.get("ji_shen") or []))
    strength_a = bazi_a.get("strength_score") or 50
    strength_b = bazi_b.get("strength_score") or 50
    balance_gap = abs(float(strength_a) - float(strength_b))
    base = {"同频互补": 78, "慢热生长": 72}.get(keyword, 66)
    resonance = base + (8 if same_need else 0) - (4 if same_avoid else 0)
    communication = 74 if keyword != "强吸引高摩擦" else 62
    intimacy = 70 + (6 if keyword == "慢热生长" else 0)
    conflict = 82 - int(min(balance_gap, 25) * 0.7) - (10 if keyword == "强吸引高摩擦" else 0)
    long_term = 73 + (7 if same_need else 0) - (5 if keyword == "强吸引高摩擦" else 0)
    scores = {
        "overall": round((resonance + communication + intimacy + conflict + long_term) / 5),
        "resonance": resonance,
        "communication": communication,
        "intimacy": intimacy,
        "conflict": conflict,
        "long_term": long_term,
    }
    return {k: max(35, min(96, int(v))) for k, v in scores.items()}

def _build_metric_rows(scores: dict[str, int]) -> str:
    labels = [
        ("共振感", "resonance"),
        ("沟通顺滑度", "communication"),
        ("亲密稳定度", "intimacy"),
        ("冲突消化力", "conflict"),
        ("长期经营度", "long_term"),
    ]
    parts = []
    for label, key in labels:
        value = scores[key]
        parts.append(f"""
<div class="metric-row">
  <span class="metric-name">{html.escape(label)}</span>
  <span class="metric-bar"><i style="width:{value}%"></i></span>
  <span class="metric-score">{value}</span>
</div>""")
    return "\n".join(parts)

def _build_profile_compare(profile_a: dict, profile_b: dict, label_a: str, label_b: str) -> str:
    a = profile_a.get("bazi", {})
    b = profile_b.get("bazi", {})
    rows = [
        ("日主", a.get("day_master", "未标明"), b.get("day_master", "未标明")),
        ("格局", a.get("ge_ju", "未标明"), b.get("ge_ju", "未标明")),
        ("能量强弱", a.get("day_master_strength", "未标明"), b.get("day_master_strength", "未标明")),
        ("需要补的能量", "、".join(a.get("yong_shen") or []) or "未标明", "、".join(b.get("yong_shen") or []) or "未标明"),
        ("容易过量的能量", "、".join(a.get("ji_shen") or []) or "未标明", "、".join(b.get("ji_shen") or []) or "未标明"),
    ]
    body = []
    for title, va, vb in rows:
        body.append(f"""
<div class="compare-row">
  <span>{html.escape(title)}</span>
  <b>{html.escape(str(va))}</b>
  <b>{html.escape(str(vb))}</b>
</div>""")
    return f"""
<div class="compare-head">
  <span></span><strong>{html.escape(label_a)}</strong><strong>{html.escape(label_b)}</strong>
</div>
{''.join(body)}"""

def _build_relation_system_compare(profile_a: dict, profile_b: dict) -> str:
    rows = [
        ("八字", _bazi_summary(profile_a), _bazi_summary(profile_b), "看两个人的能量需求、互补方式和冲突触发点。"),
        ("紫微", _ziwei_summary(profile_a), _ziwei_summary(profile_b), "看关系里的角色感、人生重心和安全感来源。"),
        ("印占", _vedic_summary(profile_a), _vedic_summary(profile_b), "看情绪本能、关系节奏和阶段性大运背景。"),
        ("西占", _western_summary(profile_a), _western_summary(profile_b), "看表达方式、亲密需求和外在互动风格。"),
    ]
    parts = []
    for title, a, b, use_for in rows:
        parts.append(f"""
<div class="system-compare-row">
  <span>{html.escape(title)}</span>
  <b>{html.escape(a)}</b>
  <b>{html.escape(b)}</b>
  <em>{html.escape(use_for)}</em>
</div>""")
    return "\n".join(parts)

def _relation_playbook(keyword: str) -> tuple[str, str, str, str]:
    if keyword == "同频互补":
        return (
            "适合共同制定目标、复盘进展、一起做需要耐心的长期计划。",
            "容易把默契当成默认同意，真实需求反而没有被说出口。",
            "每周留一次低压力对齐：最近累在哪里、想被怎样支持、下周最重要的一件事。",
            "争执时先停在事实层，不急着判断谁更成熟、谁更懂关系。",
        )
    if keyword == "慢热生长":
        return (
            "适合用稳定陪伴累积安全感，越规律越容易亲密。",
            "容易因为害怕打扰而过度退让，最后变成冷处理。",
            "把见面、回复、独处空间讲清楚，让关系有可预期的节奏。",
            "情绪低时别用消失测试对方，直接说需要一点时间会更稳。",
        )
    return (
        "适合一起做有行动感的事，把吸引力放到真实生活和共同项目里。",
        "容易在高情绪里互相点燃，把小问题讲成原则问题。",
        "重要议题延迟24小时再定结论，先确认需求，再谈方案。",
        "别用胜负感处理亲密关系，赢了争论也可能输掉连接。",
    )

def _evidence_line(profile_a: dict, profile_b: dict, keyword: str) -> str:
    return (
        f"这不是只看一套盘。八字先看两个人的能量需求和冲突触发点，紫微补角色感和人生重心，"
        f"印占看情绪本能与大运节奏，西占看表达方式和亲密需求。四组信息收束以后，这段关系更像“{keyword}”。"
    )

def render_relationship_map(
    profile_a: dict,
    profile_b: dict,
    days_ahead: int = 30,
    alias_a: str | None = None,
    alias_b: str | None = None,
    show_names: bool = True,
) -> str:
    from engines.daily import build as daily_build
    from engines.personalize import build as p_build

    start = date.today()
    end = start + timedelta(days=days_ahead - 1)
    keyword, texture, advice = _relation_keywords(profile_a, profile_b)
    role_a = _profile_role(profile_a)
    role_b = _profile_role(profile_b)

    close_days = []
    talk_days = []
    caution_days = []
    for offset in range(days_ahead):
        d = start + timedelta(days=offset)
        day = daily_build(d.isoformat())
        pa = p_build(profile_a, day)
        pb = p_build(profile_b, day)
        avg = (pa["score"] + pb["score"]) / 2
        if pa["tier"] in ("大吉", "吉") and pb["tier"] in ("大吉", "吉"):
            close_days.append((d, avg, pa, pb))
        elif pa["tier"] in ("忌", "凶") or pb["tier"] in ("忌", "凶"):
            caution_days.append((d, avg, pa, pb))
        elif avg >= 52:
            talk_days.append((d, avg, pa, pb))

    close_days = sorted(close_days, key=lambda x: -x[1])[:2]
    talk_days = sorted(talk_days, key=lambda x: -x[1])[:2]
    caution_days = sorted(caution_days, key=lambda x: x[1])[:2]

    template = _load_template("relationship_map.html")
    if show_names:
        label_a = alias_a or profile_a.get("meta", {}).get("name", "对象A")
        label_b = alias_b or profile_b.get("meta", {}).get("name", "对象B")
        pair_label = f"{label_a} × {label_b}"
        privacy_note = "显示所选两人"
    else:
        label_a = alias_a or "对象A"
        label_b = alias_b or "对象B"
        pair_label = f"{label_a} × {label_b}"
        privacy_note = "匿名显示"
    gain_point, risk_point = _relation_points(keyword, label_a, label_b)
    scores = _compatibility_scores(profile_a, profile_b, keyword)
    play_best, play_trap, play_ritual, play_repair = _relation_playbook(keyword)
    return _fill(template, {
        "PAIR_LABEL": pair_label,
        "RANGE": f"{start.isoformat()} - {end.isoformat()}",
        "KEYWORD": keyword,
        "OVERALL_SCORE": scores["overall"],
        "TEXTURE": texture,
        "ADVICE": advice,
        "GAIN_POINT": gain_point,
        "RISK_POINT": risk_point,
        "METRIC_ROWS": _build_metric_rows(scores),
        "PROFILE_COMPARE": _build_profile_compare(profile_a, profile_b, label_a, label_b),
        "SYSTEM_COMPARE": _build_relation_system_compare(profile_a, profile_b),
        "BEST_SCENE": play_best,
        "TRAP_SCENE": play_trap,
        "RITUAL": play_ritual,
        "REPAIR": play_repair,
        "EVIDENCE_LINE": _evidence_line(profile_a, profile_b, keyword),
        "ROLE_A": f"{label_a}：{role_a}",
        "ROLE_B": f"{label_b}：{role_b}",
        "CLOSE_DAYS": _build_relation_days(close_days, "适合靠近"),
        "TALK_DAYS": _build_relation_days(talk_days, "适合沟通"),
        "CAUTION_DAYS": _build_relation_days(caution_days, "先别摊牌"),
        "PRIVACY_NOTE": privacy_note,
        "GENERATED_AT": date.today().isoformat(),
    }, raw_keys={"CLOSE_DAYS", "TALK_DAYS", "CAUTION_DAYS", "METRIC_ROWS", "PROFILE_COMPARE", "SYSTEM_COMPARE"})

def _build_relation_days(rows: list[tuple], label: str) -> str:
    if not rows:
        return '<div class="mini-empty">这类窗口不明显</div>'
    parts = []
    for d, avg, pa, pb in rows:
        parts.append(f"""
<div class="mini-day">
  <span class="mini-date">{d.month}/{d.day}</span>
  <span class="mini-label">{html.escape(label)}</span>
  <span class="mini-score">{int(avg)}</span>
</div>""")
    return "\n".join(parts)

def render_tongshu_day(profile: dict, date_str: str,
                       short_sign: str = "",
                       llm_text: str = "") -> str:
    from engines.daily import build as daily_build
    from engines.personalize import build as p_build

    day_data = daily_build(date_str)
    pers = p_build(profile, day_data)

    ganzhi = day_data["ganzhi"]
    yi_items = "　".join(f"宜{x['item']}" for x in pers["personal_yi"][:4])
    ji_items = "　".join(f"忌{x['item']}" for x in pers["personal_ji"][:3])

    sign = short_sign or pers.get("short_sign") or f"「{pers['tier']}」"
    interp = llm_text or "（待解读）"

    conf = pers.get("confidence")
    conf_str = f"{conf:.2f}" if isinstance(conf, (int, float)) else "—"
    score = max(0, min(100, int(pers["score"])))

    template = _load_template("tongshu_day.html")
    return _fill(template, {
        "USER_NAME":   profile["meta"]["name"],
        "DATE":        date_str,
        "YEAR_GZ":     ganzhi["year"],
        "MONTH_GZ":    ganzhi["month"],
        "DAY_GZ":      ganzhi["day"],
        "ZHI_XING":    day_data["zhi_xing"],
        "NAKSHATRA":   day_data["panchanga"]["nakshatra"],
        "TIER":        pers["tier"],
        "TIER_CLASS":  _TIER_CLASS.get(pers["tier"], "t-ping"),
        "SCORE":       score,
        "CONFIDENCE":  conf_str,
        "SHORT_SIGN":  sign,
        "YI_ITEMS":    yi_items,
        "JI_ITEMS":    ji_items,
        "INTERP":      interp,
        "GENERATED_AT": date.today().isoformat(),
    })

def save_render(html: str, filename: str, out_dir: str = "outputs") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
