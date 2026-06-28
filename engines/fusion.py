from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from engines.daily import build as daily_build
from engines.personalize import build as personalize_build
from engines.resonance import analyze_date


Signal = Literal["favor", "neutral", "avoid"]
SYSTEM_KEYS = ("bazi", "ziwei", "vedic", "western")
SYSTEM_CHOICE_MAP = {
    "1": "bazi",
    "2": "ziwei",
    "3": "western",
    "4": "vedic",
}
RANK_MULTIPLIERS = (1.0, 0.75, 0.5, 0.25)


SYSTEM_ROLES = {
    "bazi": {
        "role": "本命底层与日课",
        "time_scale": "本命/日",
        "default_weight": 0.35,
    },
    "ziwei": {
        "role": "人生宫位与年度背景",
        "time_scale": "年/月",
        "default_weight": 0.15,
    },
    "vedic": {
        "role": "择时与月宿",
        "time_scale": "日/时",
        "default_weight": 0.30,
    },
    "western": {
        "role": "外部事件触发",
        "time_scale": "天/周",
        "default_weight": 0.20,
    },
}

ACT_PROFILE = {
    "签约": {
        "topic": "合作/文书",
        "weights": {"bazi": 0.30, "ziwei": 0.10, "vedic": 0.25, "western": 0.35},
        "best_prepare": ["谈条件", "补资料", "改合同", "内部确认"],
        "best_commit": ["签字", "付款", "公开承诺"],
        "risks": ["合同反复", "信息遗漏", "话说太满"],
    },
    "开业": {
        "topic": "事业/财务",
        "weights": {"bazi": 0.35, "ziwei": 0.20, "vedic": 0.30, "western": 0.15},
        "best_prepare": ["试营业", "内部演练", "整理物料", "邀约贵人"],
        "best_commit": ["正式发布", "开张收款", "大额投入"],
        "risks": ["节奏过急", "资源没到位", "外部阻力"],
    },
    "嫁娶": {
        "topic": "感情/关系",
        "weights": {"bazi": 0.25, "ziwei": 0.25, "vedic": 0.30, "western": 0.20},
        "best_prepare": ["沟通安排", "确认双方家人意见", "定仪式细节"],
        "best_commit": ["领证", "订婚", "公开关系"],
        "risks": ["情绪误判", "期待不一致", "临时变卦"],
    },
    "出行": {
        "topic": "出行/迁移",
        "weights": {"bazi": 0.30, "ziwei": 0.20, "vedic": 0.35, "western": 0.15},
        "best_prepare": ["订路线", "收拾行李", "确认交通", "轻装出门"],
        "best_commit": ["远行启程", "搬迁", "跨城会面"],
        "risks": ["行程变动", "时间拖延", "体力透支"],
    },
    "投资": {
        "topic": "财务/风险",
        "weights": {"bazi": 0.35, "ziwei": 0.20, "vedic": 0.25, "western": 0.20},
        "best_prepare": ["复盘账目", "查资料", "小额试探", "设止损"],
        "best_commit": ["大额投入", "借贷", "长期绑定"],
        "risks": ["判断过热", "现金流紧", "被短期消息带偏"],
    },
}

DEFAULT_ACT = {
    "topic": "通用行动",
    "weights": {k: v["default_weight"] for k, v in SYSTEM_ROLES.items()},
    "best_prepare": ["整理计划", "确认信息", "小步推进"],
    "best_commit": ["正式定局", "公开承诺", "大额投入"],
    "risks": ["节奏不稳", "外部变动", "自己先泄气"],
}

SIGNAL_SCORE = {"favor": 1.0, "neutral": 0.0, "avoid": -1.0}


@dataclass(frozen=True)
class Evidence:
    system: str
    signal: Signal
    role: str
    time_scale: str
    weight: float
    reason: str

    def as_dict(self) -> dict:
        return {
            "system": self.system,
            "signal": self.signal,
            "role": self.role,
            "time_scale": self.time_scale,
            "weight": self.weight,
            "reason": self.reason,
        }


def _act_profile(act: str) -> dict:
    return ACT_PROFILE.get(act, DEFAULT_ACT)


def _personalize_signal(personal: dict) -> Signal:
    tier = personal.get("tier")
    flags = personal.get("flags", {})
    if tier in ("忌", "凶") or flags.get("冲日主") or flags.get("冲流年太岁"):
        return "avoid"
    if tier in ("大吉", "命定时刻") or flags.get("用神得力") or flags.get("贵人到"):
        return "favor"
    return "neutral"


def _bazi_reason(personal: dict) -> str:
    flags = [k for k, v in (personal.get("flags") or {}).items() if v]
    if flags:
        return f"{personal.get('tier', '平')}，" + "、".join(flags[:3])
    return f"{personal.get('tier', '平')}，综合分 {personal.get('score')}"


def _normalize_order(system_order: list[str] | tuple[str, ...] | None) -> list[str]:
    if not system_order:
        return []
    out = []
    for item in system_order:
        key = str(item).strip().lower()
        if key in SYSTEM_KEYS and key not in out:
            out.append(key)
    out.extend(k for k in SYSTEM_KEYS if k not in out)
    return out


def parse_order_choice(choice: str) -> dict:
    raw = str(choice or "").strip().lower().replace(" ", "")
    if raw in ("", "a"):
        return {"mode": "default", "system_order": []}
    if raw.startswith("b"):
        digits = [ch for ch in raw[1:] if ch in SYSTEM_CHOICE_MAP]
        order = []
        for digit in digits:
            system = SYSTEM_CHOICE_MAP[digit]
            if system not in order:
                order.append(system)
        if order:
            order.extend(k for k in SYSTEM_KEYS if k not in order)
            return {"mode": "custom", "system_order": order}
    return {"mode": "invalid", "system_order": []}


def _rank_weights(system_order: list[str] | tuple[str, ...] | None) -> dict[str, float]:
    order = _normalize_order(system_order)
    if not order:
        return {}
    return {system: RANK_MULTIPLIERS[i] for i, system in enumerate(order)}


def _resolve_weights(
    act: str,
    *,
    system_order: list[str] | tuple[str, ...] | None = None,
    system_weights: dict[str, float] | None = None,
) -> tuple[dict[str, float], str, list[str]]:
    act_weights = dict(_act_profile(act)["weights"])
    clean_order = _normalize_order(system_order)

    if system_weights:
        explicit = {
            k: float(v) for k, v in system_weights.items()
            if k in SYSTEM_KEYS and isinstance(v, (int, float)) and v > 0
        }
        if explicit:
            weights = {k: explicit.get(k, act_weights.get(k, SYSTEM_ROLES[k]["default_weight"]))
                       for k in SYSTEM_KEYS}
            ordered = sorted(SYSTEM_KEYS, key=lambda k: -weights[k])
            return weights, "user_weights", list(ordered)

    rank = _rank_weights(clean_order)
    if rank:
        weights = {k: round(act_weights.get(k, SYSTEM_ROLES[k]["default_weight"]) * rank[k], 4)
                   for k in SYSTEM_KEYS}
        return weights, "user_order_x_act", clean_order

    ordered = sorted(SYSTEM_KEYS, key=lambda k: -act_weights.get(k, 0))
    return act_weights, "act_default", list(ordered)


def _evidence_from_votes(
    resonance: dict,
    personal: dict,
    act: str,
    weights: dict[str, float],
) -> list[Evidence]:
    profile = _act_profile(act)
    evidence = []
    votes = resonance.get("votes", {})

    for system, role_info in SYSTEM_ROLES.items():
        vote = votes.get(system, {})
        signal = vote.get("stance", "neutral")
        if signal not in SIGNAL_SCORE:
            signal = "neutral"
        reason = vote.get("basis", "无明显信号")
        if system == "bazi":
            signal = _personalize_signal(personal)
            reason = _bazi_reason(personal)
        evidence.append(Evidence(
            system=system,
            signal=signal,  # type: ignore[arg-type]
            role=role_info["role"],
            time_scale=role_info["time_scale"],
            weight=weights.get(system, role_info["default_weight"]),
            reason=reason,
        ))
    return evidence


def _weighted_score(evidence: list[Evidence]) -> float:
    total_w = sum(e.weight for e in evidence) or 1.0
    raw = sum(SIGNAL_SCORE[e.signal] * e.weight for e in evidence)
    return round(raw / total_w, 3)


def _convergence(evidence: list[Evidence]) -> dict:
    counts = {s: sum(1 for e in evidence if e.signal == s) for s in SIGNAL_SCORE}
    dominant = max(counts, key=counts.get)
    return {
        "dominant": dominant,
        "favor": counts["favor"],
        "neutral": counts["neutral"],
        "avoid": counts["avoid"],
    }


def _conflict_type(evidence: list[Evidence]) -> dict | None:
    favors = [e for e in evidence if e.signal == "favor"]
    avoids = [e for e in evidence if e.signal == "avoid"]
    if not favors or not avoids:
        return None

    avoid_systems = [e.system for e in avoids]
    favor_systems = [e.system for e in favors]
    time_scales = {e.time_scale for e in favors + avoids}

    if len(time_scales) > 1:
        ctype = "timeframe"
        note = "不同系统说的是不同时间尺度：大方向能动，不代表今天适合定局。"
    elif len({e.role for e in favors + avoids}) > 1:
        ctype = "domain"
        note = "不同系统抓到的是不同生活领域：一边有推进力，另一边提示具体风险。"
    else:
        ctype = "genuine_tension"
        note = "同一层面出现真实拉扯，建议缩小动作、延后定局。"

    return {
        "type": ctype,
        "favor_systems": favor_systems,
        "avoid_systems": avoid_systems,
        "note": note,
    }


def _overall(score: float, convergence: dict, conflict: dict | None) -> str:
    if convergence["avoid"] >= 2 and score < 0:
        return "delay"
    if convergence["favor"] >= 3 and not conflict:
        return "commit"
    if convergence["favor"] >= 2 and convergence["avoid"] == 0:
        return "proceed"
    if convergence["favor"] >= 1 and convergence["avoid"] >= 1:
        return "prepare_not_commit"
    if score > 0.15:
        return "proceed_with_care"
    if score < -0.15:
        return "review_not_push"
    return "observe"


def _state(overall: str, topic: str) -> str:
    return {
        "commit": f"{topic}信号顺，可以定下来",
        "proceed": f"{topic}有推进力，适合往前走",
        "proceed_with_care": f"{topic}能推进，但要留余地",
        "prepare_not_commit": f"{topic}有动力，但定局信号不稳",
        "review_not_push": f"{topic}适合复盘，不适合硬推",
        "delay": f"{topic}今天阻力偏重，适合延后",
        "observe": f"{topic}信号中性，先看反馈",
    }[overall]


def _actions(overall: str, act_profile: dict) -> tuple[list[str], list[str]]:
    prepare = act_profile["best_prepare"]
    commit = act_profile["best_commit"]
    if overall in ("commit", "proceed"):
        return commit[:3], []
    if overall in ("prepare_not_commit", "proceed_with_care", "observe"):
        return prepare[:3], commit[:3]
    return ["复盘", "补资料", "等反馈"], commit[:3]


def _one_liner(overall: str, act_profile: dict) -> str:
    topic = act_profile["topic"]
    prepare = "、".join(act_profile["best_prepare"][:2])
    commit = "、".join(act_profile["best_commit"][:2])
    return {
        "commit": f"今天{topic}可以定下来。",
        "proceed": f"今天适合推进{topic}。",
        "proceed_with_care": f"今天能推进，但别把话说死。",
        "prepare_not_commit": f"今天适合{prepare}，不适合{commit}。",
        "review_not_push": f"今天适合复盘，不适合硬推。",
        "delay": f"今天先别定局，等信号顺一点再说。",
        "observe": f"今天先观察反馈，小步走就好。",
    }[overall]


def fuse_date(profile: dict, act: str, date_str: str) -> dict:
    """Fuse four-system date signals into one actionable language layer."""
    day = daily_build(date_str)
    personal = personalize_build(profile, day)
    resonance = analyze_date(profile, act, date_str)
    act_profile = _act_profile(act)
    meta = profile.get("meta", {})
    context = profile.get("context", {})
    system_order = (
        meta.get("fusion_system_order")
        or context.get("fusion_system_order")
    )
    system_weights = (
        meta.get("fusion_system_weights")
        or context.get("fusion_system_weights")
    )
    weights, weight_policy, resolved_order = _resolve_weights(
        act, system_order=system_order, system_weights=system_weights)
    evidence = _evidence_from_votes(resonance, personal, act, weights)
    score = _weighted_score(evidence)
    convergence = _convergence(evidence)
    conflict = _conflict_type(evidence)
    overall = _overall(score, convergence, conflict)
    best_actions, avoid_actions = _actions(overall, act_profile)

    return {
        "date": date_str,
        "act": act,
        "topic": act_profile["topic"],
        "overall": overall,
        "score": score,
        "weight_policy": weight_policy,
        "system_order": resolved_order,
        "confidence": round(min(0.95, max(0.35, abs(score) * 0.45 + 0.45)), 2),
        "convergence": convergence,
        "conflict": conflict,
        "state": _state(overall, act_profile["topic"]),
        "best_actions": best_actions,
        "avoid_actions": avoid_actions,
        "risks": act_profile["risks"][:],
        "timing": _one_liner(overall, act_profile),
        "one_liner": _one_liner(overall, act_profile),
        "evidence": [e.as_dict() for e in evidence],
        "raw": {
            "personalize": personal,
            "resonance": resonance,
        },
    }


def fuse_date_with_order(
    profile: dict,
    act: str,
    date_str: str,
    system_order: list[str] | tuple[str, ...],
) -> dict:
    """Fuse date signals with a one-off user-chosen system importance order."""
    profile_with_order = dict(profile)
    meta = dict(profile_with_order.get("meta", {}))
    meta["fusion_system_order"] = list(system_order)
    profile_with_order["meta"] = meta
    return fuse_date(profile_with_order, act, date_str)


def fuse_date_with_choice(profile: dict, act: str, date_str: str, choice: str) -> dict:
    parsed = parse_order_choice(choice)
    if parsed["mode"] == "custom":
        return fuse_date_with_order(profile, act, date_str, parsed["system_order"])
    return fuse_date(profile, act, date_str)
