from datetime import date

from engines.build_profile import build_profile, refresh_profile_for_date
from engines.evidence_packet import build_chart_packet
from engines.chart_signals import _synthesize, build_topic_signals
from engines.task_router import route_task


def _profile():
    return build_profile(
        "_test_architecture", "1995-03-12T08:30:00", "女",
        time_precision="exact", save=False,
    )


def test_profile_records_temporal_target():
    profile = _profile()
    assert profile["meta"]["calculated_for"] == date.today().isoformat()


def test_refresh_profile_updates_all_temporal_targets_without_mutation():
    profile = _profile()
    refreshed = refresh_profile_for_date(profile, "2030-08-15")

    assert profile["meta"]["calculated_for"] == date.today().isoformat()
    assert refreshed["meta"]["calculated_for"] == "2030-08-15"
    assert refreshed["vedic"]["vimshottari"]["target_date"] == "2030-08-15"
    current_year = refreshed["bazi"]["luck"]["current_liunian"]
    assert current_year is None or current_year["year"] == 2030


def test_chart_packet_is_compact_and_context_free():
    profile = _profile()
    profile["context"] = {"concerns": ["这段话不能进入盘面证据"]}
    packet = build_chart_packet(profile, "事业")

    assert packet["topic"] == "career"
    assert packet["context_policy"] == "chart_only"
    assert set(packet["systems"]) == {"bazi", "ziwei", "vedic", "western"}
    assert "context" not in packet
    assert "这段话不能进入盘面证据" not in str(packet)
    assert "topic_signals" in packet
    assert "synthesis" in packet
    assert packet["synthesis"]["grade"] in {"strong", "moderate", "limited", "insufficient"}
    for signal in packet["topic_signals"]:
        for key in ("system", "direction", "strength", "confidence", "scope", "basis", "source_fields", "components"):
            assert key in signal
        assert signal["source_fields"]
    western_facts = packet["systems"]["western"]["facts"]
    assert western_facts["target_date"] == profile["meta"]["calculated_for"]
    assert "transit_hits" in western_facts


def test_tai_sui_branch_tracks_target_year_not_birth_year():
    refreshed = refresh_profile_for_date(_profile(), "2030-08-15")
    bazi = refreshed["bazi"]
    current = bazi["luck"]["current_liunian"]
    assert bazi["natal_year_branch"] == "亥"
    assert current is None or bazi["tai_sui_branch"] == current["zhi"]


def test_task_router_uses_low_cost_for_bounded_work():
    assert route_task("daily")["tier"] == "low_cost"
    assert route_task("calendar_export")["tier"] == "deterministic"
    assert route_task("chart_brief")["tier"] == "standard"


def test_task_router_escalates_only_for_real_complexity():
    assert route_task("chart_brief", has_conflict=True)["tier"] == "reasoning"
    assert route_task("chart_long", long_form=True)["tier"] == "reasoning"
    clarification = route_task("chart_brief", missing_required=True)
    assert clarification["tier"] == "low_cost"
    assert clarification["action"] == "clarify"


def test_topic_synthesis_preserves_opposing_evidence():
    signals = [
        {"system": "bazi", "direction": "support", "strength": 0.8, "confidence": 0.8},
        {"system": "ziwei", "direction": "pressure", "strength": 0.8, "confidence": 0.8},
        {"system": "vedic", "direction": "mixed", "strength": 0.9, "confidence": 0.9},
    ]
    result = _synthesize(signals, "career")
    assert result["conflict"] is True
    assert result["support_systems"] == ["bazi"]
    assert result["pressure_systems"] == ["ziwei"]
    assert result["grade"] == "moderate"


def test_topic_synthesis_does_not_invent_direction_from_mixed_only():
    signals = [
        {"system": "bazi", "direction": "mixed", "strength": 0.9, "confidence": 0.9},
    ]
    assert _synthesize(signals, "career")["direction"] == "insufficient"


def test_single_system_direction_is_limited_not_strong():
    signals = [
        {"system": "western", "direction": "support", "strength": 0.9, "confidence": 0.9},
    ]
    result = _synthesize(signals, "wealth")
    assert result["direction"] == "support"
    assert result["grade"] == "limited"
    assert result["system_count"] == 1


def test_each_system_uses_layered_topic_evidence():
    result = build_topic_signals(_profile(), "事业")
    by_system = {signal["system"]: signal for signal in result["signals"]}

    assert set(by_system) == {"bazi", "ziwei", "vedic", "western"}
    assert {c["label"] for c in by_system["bazi"]["components"]} >= {"大运", "流年"}
    assert any(c["label"] in {"流年", "流月"} for c in by_system["ziwei"]["components"])
    assert {c["label"] for c in by_system["vedic"]["components"]} >= {"相关宫位", "大运", "分运"}
    assert len(by_system["western"]["components"]) >= 2


def test_special_bazi_pattern_cannot_emit_strong_direction():
    profile = _profile()
    profile["bazi"]["special_pattern"] = "待复核特殊格局"
    profile["bazi"]["strength_confidence"] = 0.9
    signal = next(s for s in build_topic_signals(profile, "事业")["signals"] if s["system"] == "bazi")

    assert signal["direction"] == "mixed"
    assert signal["confidence"] <= 0.45
    assert signal["strength"] <= 0.4
