import sys
import json

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TIERS = {"命定时刻", "大吉", "吉", "平", "忌", "凶"}
STANCES = {"favor", "neutral", "avoid"}
FLAG_KEYS = {"冲日主", "冲流年太岁", "贵人到", "驿马动", "桃花到", "用神得力"}
WUXING = {"木", "火", "土", "金", "水"}

def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)

def detect_kind(obj: dict) -> str:
    if not isinstance(obj, dict):
        return "unknown"
    if "votes" in obj and "resonance_strength" in obj:
        return "resonance"
    if "overall" in obj and "evidence" in obj and "weight_policy" in obj:
        return "fusion"
    if "personal_yi" in obj or "tier" in obj:
        return "personalize"
    if "bazi" in obj and "meta" in obj:
        return "profile"
    return "unknown"

def validate_personalize(r: dict) -> dict:
    errors, warnings = [], []
    for k in ("date", "score", "personal_yi", "personal_ji", "flags", "tier"):
        if k not in r:
            errors.append(f"缺顶层字段 `{k}`。")
    if "score" in r:
        if not _num(r["score"]) or not (0 <= r["score"] <= 100):
            errors.append(f"`score` 必须是 0-100 的数字，实得 {r['score']!r}。")
    if r.get("tier") not in TIERS and "tier" in r:
        errors.append(f"`tier` 必须 ∈ {sorted(TIERS)}，实得 {r['tier']!r}。")
    if "flags" in r:
        missing = FLAG_KEYS - set(r["flags"] or {})
        if missing:
            errors.append(f"`flags` 缺固定键：{sorted(missing)}。")
    if "confidence" in r and (not _num(r["confidence"]) or not (0 <= r["confidence"] <= 1)):
        errors.append(f"`confidence` 必须在 0-1 之间，实得 {r['confidence']!r}。")
    for fld in ("personal_yi", "personal_ji"):
        for i, it in enumerate(r.get(fld, []) or []):
            if not isinstance(it, dict) or "item" not in it or "strength" not in it:
                errors.append(f"`{fld}[{i}]` 须含 item/strength，实得 {it!r}。")
            elif not (1 <= it.get("strength", 0) <= 5):
                warnings.append(f"`{fld}[{i}].strength` 建议 1-5，实得 {it.get('strength')!r}。")
    if "confidence" not in r:
        warnings.append("建议附 `confidence` 元字段（置信度自评更可信）。")
    if r.get("degraded") and not r.get("degrade_reason"):
        warnings.append("`degraded=true` 但缺 `degrade_reason`，建议补一句诚实说明。")
    return _wrap(errors, warnings)

def validate_resonance(r: dict) -> dict:
    errors, warnings = [], []
    for k in ("date", "act", "votes", "resonance_strength", "is_destined_moment"):
        if k not in r:
            errors.append(f"缺顶层字段 `{k}`。")
    rs = r.get("resonance_strength")
    if rs is not None and (not _num(rs) or not (0 <= rs <= 4)):
        errors.append(f"`resonance_strength` 必须 0-4，实得 {rs!r}。")
    votes = r.get("votes", {})
    for sysname in ("bazi", "ziwei", "vedic", "western"):
        if sysname not in votes:
            errors.append(f"`votes` 缺系统 `{sysname}`。")
            continue
        st = votes[sysname].get("stance")
        if st not in STANCES:
            errors.append(f"`votes.{sysname}.stance` 必须 ∈ {sorted(STANCES)}，实得 {st!r}。")
    if isinstance(votes, dict) and rs is not None:
        favor = sum(1 for v in votes.values() if isinstance(v, dict) and v.get("stance") == "favor")
        if favor != rs:
            errors.append(f"`resonance_strength`({rs}) ≠ favor 计数({favor})，违反收敛计数法。")
        if r.get("is_destined_moment") and rs != 4:
            errors.append(f"`is_destined_moment=true` 但 strength≠4（实得{rs}），命定时刻须 4/4。")
    if votes and not all("precision" in v for v in votes.values() if isinstance(v, dict)):
        warnings.append("部分 vote 缺 `precision`，冲突仲裁时无法判断该听谁。")
    return _wrap(errors, warnings)

def validate_fusion(r: dict) -> dict:
    errors, warnings = [], []
    required = ("date", "act", "topic", "overall", "score", "weight_policy",
                "system_order", "evidence", "confidence", "one_liner")
    for k in required:
        if k not in r:
            errors.append(f"缺顶层字段 `{k}`。")

    score = r.get("score")
    if score is not None and (not _num(score) or not (-1 <= score <= 1)):
        errors.append(f"`score` 必须在 -1 到 1 之间，实得 {score!r}。")
    confidence = r.get("confidence")
    if confidence is not None and (not _num(confidence) or not (0 <= confidence <= 1)):
        errors.append(f"`confidence` 必须在 0-1 之间，实得 {confidence!r}。")

    evidence = r.get("evidence") or []
    if len(evidence) != 4:
        errors.append(f"`evidence` 必须包含四个系统，实得 {len(evidence)}。")
    systems = {item.get("system") for item in evidence if isinstance(item, dict)}
    expected = {"bazi", "ziwei", "vedic", "western"}
    if systems != expected:
        errors.append(f"`evidence` 系统集合不完整，实得 {sorted(s for s in systems if s)}。")
    for i, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f"`evidence[{i}]` 必须是对象。")
            continue
        if item.get("signal") not in STANCES:
            errors.append(f"`evidence[{i}].signal` 无效：{item.get('signal')!r}。")
        if not _num(item.get("weight")) or item.get("weight", 0) <= 0:
            errors.append(f"`evidence[{i}].weight` 必须为正数。")
        for field in ("strength", "confidence"):
            if not _num(item.get(field)) or not (0 <= item.get(field, -1) <= 1):
                errors.append(f"`evidence[{i}].{field}` 必须在 0-1 之间。")
        if not _num(item.get("effective_weight")) or item.get("effective_weight", -1) < 0:
            errors.append(f"`evidence[{i}].effective_weight` 必须是非负数。")

    if r.get("weight_policy") not in {"act_default", "user_order_x_act", "user_weights"}:
        errors.append(f"未知 `weight_policy`：{r.get('weight_policy')!r}。")
    if r.get("conflict") and not r["conflict"].get("type"):
        warnings.append("存在 `conflict` 但缺冲突类型。")
    return _wrap(errors, warnings)

def validate_profile(p: dict) -> dict:
    errors, warnings = [], []
    if "meta" not in p:
        errors.append("缺 `meta`。")
    elif not p["meta"].get("name"):
        errors.append("`meta.name` 为空。")
    bazi = p.get("bazi")
    if not bazi:
        errors.append("缺 `bazi`。")
    else:
        if not bazi.get("day_master"):
            errors.append("`bazi.day_master` 为空。")
        if not bazi.get("pillars"):
            errors.append("`bazi.pillars` 为空。")
        if not bazi.get("yong_shen"):
            errors.append("`bazi.yong_shen` 不可为空（契约约束）。")
        elif set(bazi["yong_shen"]) - WUXING:
            errors.append(f"`bazi.yong_shen` 含非五行值：{set(bazi['yong_shen']) - WUXING}。")
    if p.get("vedic", {}).get("ayanamsa") not in (None, "Lahiri"):
        errors.append(f"`vedic.ayanamsa` 必须 Lahiri，实得 {p['vedic'].get('ayanamsa')!r}。")
    if not p.get("bazi", {}).get("ge_ju"):
        warnings.append("`bazi.ge_ju` 缺失（旧档案？深度解读将无格局一句）。")
    return _wrap(errors, warnings)

def _wrap(errors, warnings):
    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

_VALIDATORS = {
    "personalize": validate_personalize,
    "resonance": validate_resonance,
    "fusion": validate_fusion,
    "profile": validate_profile,
}

def validate(obj: dict, kind: str = "") -> dict:
    kind = kind or detect_kind(obj)
    fn = _VALIDATORS.get(kind)
    if not fn:
        return {"valid": False,
                "errors": [f"无法识别输出类型（kind={kind}）；请显式指定 profile/personalize/resonance。"],
                "warnings": []}
    out = fn(obj)
    out["kind"] = kind
    return out

def main():
    args = [a for a in sys.argv[1:]]
    kind = ""
    path = ""
    for a in args:
        if a in _VALIDATORS:
            kind = a
        else:
            path = a
    try:
        raw = open(path, encoding="utf-8").read() if path else sys.stdin.read()
        obj = json.loads(raw)
    except Exception as e:
        print(json.dumps({"valid": False, "errors": [f"读取/解析 JSON 失败：{e}"], "warnings": []},
                         ensure_ascii=False, indent=2))
        sys.exit(1)

    res = validate(obj, kind)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res["valid"] else 1)

if __name__ == "__main__":
    main()
