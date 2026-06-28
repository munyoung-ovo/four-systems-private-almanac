
import os
import sys
import uuid
from datetime import date, timedelta, datetime, timezone

MONTH_CAP         = None
TOTAL_CAP         = None
DEFAULT_DAYS      = 30
PREVIEW_DAYS      = DEFAULT_DAYS
PREVIEW_CAP       = 4

_DESTINED_ACTS = ("签约", "开业", "出行")
_GOOD_TIERS = {"大吉"}
_BAD_TIERS = {"忌", "凶"}
_EMPTY_ITEMS = {"", "无"}
_CALENDAR_NOISY_JI = {"诸事不宜"}
_FALLBACK_YI = ("整理", "祈福", "出行", "签约", "清洁")
_FALLBACK_JI = ("搬家", "装修", "付款", "投资", "签约")
_MODERN_SUMMARY_WORDS = {
    "祭祀": "祭拜",
    "祈福": "祈福",
    "求嗣": "求子",
    "纳采": "订婚",
    "订盟": "订婚",
    "嫁娶": "结婚",
    "冠笄": "成人礼",
    "开光": "开光",
    "出行": "出门",
    "移徙": "搬家",
    "入宅": "搬家",
    "安床": "安床",
    "开市": "开业",
    "开业": "开业",
    "签约": "签约",
    "纳财": "收款",
    "交易": "交易",
    "立券": "签约",
    "付款": "付款",
    "投资": "投资",
    "动土": "修饰",
    "破土": "修饰",
    "装修": "装修",
    "修造": "装修",
    "安葬": "安葬",
    "求医": "看病",
    "治病": "看病",
    "理发": "理发",
    "沐浴": "洗护",
    "扫舍": "清洁",
    "塞穴": "堵漏",
    "畋猎": "狩猎",
    "破屋": "拆旧",
    "坏垣": "拆墙",
    "作灶": "开灶",
    "出火": "动火",
    "斋醮": "祈仪",
    "普渡": "祭拜",
    "合寿木": "木作",
}

_MODERN_DESCRIPTION_WORDS = {
    **_MODERN_SUMMARY_WORDS,
    "整理": "整理",
}

def _calendar_items(items: list[dict], limit: int, *, is_ji: bool = False) -> list[str]:
    blocked = _EMPTY_ITEMS | (_CALENDAR_NOISY_JI if is_ji else set())
    out: list[str] = []
    for item in items:
        word = str(item.get("item", "")).strip()
        if word in blocked:
            continue
        if word not in out:
            out.append(word)
        if len(out) >= limit:
            break
    return out

def _best_items(event: dict, track: str, limit: int) -> list[str]:
    is_ji = track == "ji"
    key = "personal_ji" if is_ji else "personal_yi"
    items = _calendar_items(event.get(key, []), limit, is_ji=is_ji)
    if items:
        return items

    base = _FALLBACK_JI if is_ji else _FALLBACK_YI
    score = int(event.get("score", 50))
    if is_ji:
        if event.get("flags", {}).get("冲日主") or event.get("flags", {}).get("冲流年太岁"):
            base = ("付款", "投资", "签约", "搬家", "装修")
        elif score >= 63:
            base = ("冲动决定", "大额付款", "争执", "装修", "搬家")
    else:
        if score >= 63:
            base = ("签约", "出行", "开业", "祈福", "整理")
        elif score < 38:
            base = ("整理", "清洁", "复盘", "休息", "祈福")
    return list(base[:limit])

def _raw_calendar_items(items: list[dict], limit: int) -> list[str]:
    out: list[str] = []
    for item in items:
        word = str(item.get("item", "")).strip()
        if word in _EMPTY_ITEMS:
            continue
        if word not in out:
            out.append(word)
        if len(out) >= limit:
            break
    return out

def _modern_word(word: str) -> str:
    return _MODERN_SUMMARY_WORDS.get(word, word)

def _modernize_unique(words: list[str], mapping: dict[str, str]) -> list[str]:
    out: list[str] = []
    for word in words:
        modern = mapping.get(word, word)
        if modern not in out:
            out.append(modern)
    return out

def _summary_text(event: dict, track: str) -> str:
    is_ji = track == "ji"
    items = _best_items(event, track, 2)
    prefix = "忌" if is_ji else "宜"
    words = _modernize_unique(items, _MODERN_SUMMARY_WORDS)
    if not words:
        return "看日子"
    one = f"{prefix}{words[0]}"
    if len(words) > 1:
        two = f"{prefix}{words[0]}.{words[1]}"
        if len(two) <= 6:
            return two
    return one[:6]

def _description_text(event: dict, track: str) -> str:
    if track == "ji":
        ji_items = _modernize_unique(_best_items(event, "ji", 5), _MODERN_DESCRIPTION_WORDS)[:3]
        return f"【今日忌】{'、'.join(ji_items)}"
    yi_items = _modernize_unique(_best_items(event, "yi", 5), _MODERN_DESCRIPTION_WORDS)[:3]
    return f"【今日宜】{'、'.join(yi_items)}"

def _vevent(event: dict, track: str) -> str:
    d          = event["date"]
    date_stamp = d.replace("-", "")
    end_stamp  = (date.fromisoformat(d) + timedelta(days=1)).strftime("%Y%m%d")
    uid        = str(uuid.uuid4())
    now        = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    summary = _summary_text(event, track)
    desc    = _description_text(event, track)

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART;VALUE=DATE:{date_stamp}",
        f"DTEND;VALUE=DATE:{end_stamp}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{desc}",
        "TRANSP:TRANSPARENT",
    ]

    lines.append("END:VEVENT")
    return "\n".join(lines)

def _vevents_for_day(event: dict) -> list[str]:
    return [_vevent(event, "yi"), _vevent(event, "ji")]

def _is_destined_moment(profile: dict, day_data: dict) -> bool:
    from engines.resonance import _vote_bazi, _vote_ziwei, _vote_vedic, _vote_western
    for act in _DESTINED_ACTS:
        votes = [
            _vote_bazi(profile, day_data, act),
            _vote_ziwei(profile, day_data, act),
            _vote_vedic(profile, day_data, act),
            _vote_western(profile, day_data, act),
        ]
        if sum(1 for v in votes if v["stance"] == "favor") == 4:
            return True
    return False

def _event_priority(event: dict) -> int:
    if event.get("is_destined"):
        return 200
    score = int(event.get("score", 50))
    flags = event.get("flags", {})
    risk_bonus = 0
    if flags.get("冲日主"):
        risk_bonus += 18
    if flags.get("冲流年太岁"):
        risk_bonus += 18
    if event.get("event_kind") == "avoid":
        return 100 - score + risk_bonus
    return score + risk_bonus

def _mark_calendar_event(profile: dict, day_data: dict, pers: dict) -> dict:
    tier = pers.get("tier")
    if tier in _GOOD_TIERS:
        is_destined = _is_destined_moment(profile, day_data)
        return {
            **pers,
            "event_kind": "good",
            "is_destined": is_destined,
            "tier": "命定时刻" if is_destined else "大吉",
        }
    if tier in _BAD_TIERS:
        return {
            **pers,
            "event_kind": "avoid",
            "is_destined": False,
            "tier": "避凶提醒",
        }
    return {
        **pers,
        "event_kind": "daily",
        "is_destined": False,
        "tier": tier or "平",
    }

def collect_events(
    profile: dict,
    days_ahead: int = DEFAULT_DAYS,
    start_date: date | None = None,
    total_cap: int | None = TOTAL_CAP,
    month_cap: int | None = MONTH_CAP,
) -> list[dict]:
    from engines.daily import build as daily_build
    from engines.personalize import build as p_build

    if start_date is None:
        start_date = date.today()

    events: list[dict] = []
    month_counts: dict[tuple[str, str], int] = {}
    errors = 0

    for offset in range(days_ahead):
        d         = start_date + timedelta(days=offset)
        date_str  = d.isoformat()
        month_key = date_str[:7]

        try:
            day_data = daily_build(date_str)
            pers     = p_build(profile, day_data)
        except Exception as e:
            errors += 1
            continue

        event = _mark_calendar_event(profile, day_data, pers)

        kind = event["event_kind"]
        month_keyed = (month_key, kind)
        if month_cap is not None and month_counts.get(month_keyed, 0) >= month_cap:
            continue

        event["priority"] = _event_priority(event)
        events.append(event)
        month_counts[month_keyed] = month_counts.get(month_keyed, 0) + 1

        if total_cap is not None and len(events) >= total_cap:
            break

    if errors > 0:
        print(f"[ics_builder] 警告：{errors} 天计算失败已跳过", file=sys.stderr)

    return events

def preview_days(
    profile: dict,
    days_ahead: int = PREVIEW_DAYS,
    limit: int = PREVIEW_CAP,
    start_date: date | None = None,
) -> list[dict]:
    events = collect_events(
        profile,
        days_ahead=days_ahead,
        start_date=start_date,
        total_cap=None,
        month_cap=None,
    )
    if limit is None or len(events) <= limit:
        return events

    good = [e for e in events if e.get("event_kind") == "good"]
    avoid = [e for e in events if e.get("event_kind") == "avoid"]
    selected: list[dict] = []

    if good:
        selected.append(max(good, key=_event_priority))
    if avoid:
        selected.append(max(avoid, key=_event_priority))

    selected_ids = {e["date"] for e in selected}
    for event in sorted(events, key=_event_priority, reverse=True):
        if event["date"] in selected_ids:
            continue
        selected.append(event)
        selected_ids.add(event["date"])
        if len(selected) >= limit:
            break

    return sorted(selected, key=lambda e: e["date"])

def preview_lines(events: list[dict]) -> list[str]:
    lines: list[str] = []
    for event in events:
        yi_items = _best_items(event, "yi", 2)
        ji_items = _best_items(event, "ji", 2)
        parts = [event["date"], event["tier"]]
        if yi_items:
            parts.append("宜" + "、".join(yi_items))
        if ji_items:
            parts.append("忌" + "、".join(ji_items))
        lines.append("  ".join(parts))
    return lines

def build_ics(
    profile: dict,
    days_ahead: int = DEFAULT_DAYS,
    start_date: date | None = None,
    events: list[dict] | None = None,
) -> str:
    if start_date is None:
        start_date = date.today()

    if events is None:
        events = collect_events(profile, days_ahead, start_date)

    cal_name = f"{profile['meta']['name']}·私人通勝"
    now      = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    header = "\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//HuangdaoJiri//ZH",
        f"X-WR-CALNAME:{cal_name}",
        "X-WR-TIMEZONE:Asia/Shanghai",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ])

    vevents = [vevent for e in events for vevent in _vevents_for_day(e)]

    return "\n".join([header] + vevents + ["END:VCALENDAR"])

def save_ics(
    profile: dict,
    out_dir: str = ".",
    days_ahead: int = DEFAULT_DAYS,
    events: list[dict] | None = None,
) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    name     = profile["meta"]["name"]
    filename = f"{name}·私人通勝.ics"
    path     = os.path.join(out_dir, filename)

    existed  = os.path.exists(path)
    old_mtime = os.path.getmtime(path) if existed else None

    content = build_ics(profile, days_ahead, events=events)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return {"path": path, "existed": existed, "old_mtime": old_mtime}

def find_next_destined_moment(profile: dict, days_ahead: int = 180) -> dict | None:
    from engines.resonance import analyze_date

    today         = date.today()
    acts_to_check = ["签约", "开业", "出行"]

    for offset in range(1, days_ahead + 1):
        d_str = (today + timedelta(days=offset)).isoformat()
        for act in acts_to_check:
            try:
                r = analyze_date(profile, act, d_str)
                if r.get("is_destined_moment"):
                    return {
                        "date":      d_str,
                        "act":       act,
                        "days_away": offset,
                        "summary":   f"距命定时刻还有 {offset} 天（{d_str}·{act}·四系统共振）",
                    }
            except Exception:
                continue
    return None

