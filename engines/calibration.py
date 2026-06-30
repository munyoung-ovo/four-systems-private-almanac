from __future__ import annotations


def system_confidence_factor(profile: dict, system: str, topic: str = "") -> float:
    calibration = profile.get("calibration") or profile.get("feedback_calibration") or {}
    adjustments = calibration.get("system_adjustments", [])
    factor = 1.0
    for item in adjustments:
        if item.get("system") != system:
            continue
        item_topic = str(item.get("topic", ""))
        if item_topic and topic and item_topic != topic:
            continue
        try:
            factor += float(item.get("confidence_adjustment", 0))
        except (TypeError, ValueError):
            continue
    return round(max(0.2, min(1.4, factor)), 3)


def apply_vote_calibration(vote: dict, profile: dict, topic: str = "") -> dict:
    system = vote.get("system", "")
    factor = system_confidence_factor(profile, system, topic)
    if factor == 1.0:
        return vote
    out = dict(vote)
    out["confidence"] = round(max(0.0, min(1.0, out.get("confidence", 0.7) * factor)), 3)
    notes = list(out.get("calibration_notes", []))
    notes.append(f"用户反馈校准×{factor}")
    out["calibration_notes"] = notes
    return out

