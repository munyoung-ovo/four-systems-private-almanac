from __future__ import annotations

from typing import Literal


ModelTier = Literal["deterministic", "low_cost", "standard", "reasoning"]

DETERMINISTIC_INTENTS = {"build_profile", "profile_manage", "calendar_export"}
LOW_COST_INTENTS = {"menu", "file_handoff", "profile_summary"}
STANDARD_INTENTS = {"daily", "chart_brief", "electional", "relationship_brief"}
REASONING_INTENTS = {"chart_long", "full_portrait", "relationship_long"}


def route_task(
    intent: str,
    *,
    audit_status: str = "stable",
    has_conflict: bool = False,
    material_conflict: bool = False,
    long_form: bool = False,
    high_stakes: bool = False,
    missing_required: bool = False,
) -> dict:
    """Return a provider-neutral execution tier for the orchestrator."""
    reasons: list[str] = []

    if missing_required:
        return {
            "tier": "low_cost",
            "action": "clarify",
            "context_budget": "small",
            "reasons": ["missing_required_input"],
        }

    if intent in DETERMINISTIC_INTENTS and not long_form:
        tier: ModelTier = "deterministic"
        reasons.append("script_owned_output")
    elif intent in LOW_COST_INTENTS:
        tier = "low_cost"
        reasons.append("bounded_summary")
    elif intent in REASONING_INTENTS or long_form:
        tier = "reasoning"
        reasons.append("long_or_cross_domain_synthesis")
    else:
        tier = "standard"
        reasons.append("structured_interpretation")

    if has_conflict:
        tier = "reasoning"
        reasons.append("cross_system_conflict")
    if audit_status == "high_risk" or material_conflict:
        tier = "reasoning"
        reasons.append("input_integrity_risk")
    elif audit_status == "caution" and tier == "low_cost":
        tier = "standard"
        reasons.append("precision_caution")
    if high_stakes:
        tier = "reasoning"
        reasons.append("high_stakes_boundary")

    budget = {
        "deterministic": "none",
        "low_cost": "small",
        "standard": "medium",
        "reasoning": "large",
    }[tier]
    return {
        "tier": tier,
        "action": "execute",
        "context_budget": budget,
        "reasons": reasons,
    }
