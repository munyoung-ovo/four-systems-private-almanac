import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_audit_marks_stable_profile():
    from engines.audit import audit_profile

    profile = {
        "meta": {
            "name": "audit_sample",
            "solar_birth": "1997-11-14T14:30:00",
            "birth_place": {"lat": 38.9259, "lon": 100.4498, "tz": 8},
            "time_precision": "exact",
        },
        "bazi": {"pillars": {"day": "庚申"}, "degraded": False},
        "ziwei": {"soul_palace": {"name": "命宫"}, "degraded": False},
        "vedic": {"moon_nakshatra": "Bharani", "degraded": False},
        "western": {"sun": "天蝎", "moon": "金牛", "degraded": False},
    }

    audit = audit_profile(profile)

    assert audit["status"] == "stable"
    assert audit["checks"]["system_health"]["vedic"]["ok"] is True


def test_audit_blocks_unknown_birth_time():
    from engines.audit import audit_profile

    profile = {
        "meta": {
            "name": "audit_unknown",
            "solar_birth": "1997-11-14T00:00:00",
            "birth_place": {"lat": 38.9259, "lon": 100.4498, "tz": 8},
            "time_precision": "unknown",
        },
        "bazi": {"pillars": {"day": "庚申"}, "degraded": True},
        "ziwei": {"soul_palace": {"name": "命宫"}, "degraded": True},
        "vedic": {"moon_nakshatra": "Bharani", "degraded": True},
        "western": {"sun": "天蝎", "moon": "金牛", "degraded": True},
    }

    audit = audit_profile(profile)

    assert audit["status"] == "high_risk"
    assert any(item["code"] == "unknown_birth_time" for item in audit["issues"])


def test_ui_state_round_trip(tmp_path, monkeypatch):
    from engines import ui_state

    state_path = tmp_path / "_ui_state.json"
    monkeypatch.setattr(ui_state, "STATE_PATH", state_path)
    monkeypatch.setattr(ui_state, "PROFILES_DIR", tmp_path)

    ui_state.set_chart_topic("事业", profile_name="大仙")

    assert ui_state.resolve_detail_topic() == "事业"
    assert ui_state.load_state()["active_profile"] == "大仙"


def test_material_text_extracts_birth_fields_and_labels():
    from scripts.pdf_extractor import _extract_chart_labels, _extract_fields

    text = """
    Name: Daxian
    Gender: Female
    Date of Birth: 1997-11-14
    Time of Birth: 14:30
    Place of Birth: Zhangye, Gansu
    Latitude: 38.9259
    Longitude: 100.4498
    Time Zone: UTC+8
    Sun: Scorpio
    Moon: Taurus
    Ascendant: Aquarius
    Nakshatra: Bharani
    """

    fields = _extract_fields(text)
    labels = _extract_chart_labels(text)

    assert fields["solar_birth"] == "1997-11-14T14:30:00"
    assert fields["gender"] == "女"
    assert fields["latitude"] == 38.9259
    assert labels["western_ascendant"] == "Aquarius"
    assert labels["vedic_moon_nakshatra"] == "Bharani"


def test_material_compare_match_and_conflict():
    from engines.audit import compare_material_to_profile

    profile = {
        "bazi": {"pillars": {"year": "丁丑", "month": "辛亥", "day": "庚申", "hour": "癸未"}},
        "ziwei": {"soul_palace": {"name": "命宫", "major_stars": ["太阴"]}},
        "vedic": {"moon_nakshatra": "Bharani"},
        "western": {"sun": "天蝎", "moon": "金牛", "ascendant": "水瓶"},
    }
    material = {
        "file": "chart.png",
        "status": "ok",
        "chart_labels": {
            "western_sun": "Scorpio",
            "western_moon": "Taurus",
            "western_ascendant": "Aquarius",
            "vedic_moon_nakshatra": "Bharani",
            "ziwei_ming_gong": "太阴",
            "bazi_pillars": "丁丑 辛亥 庚申 癸未",
        },
    }

    matched = compare_material_to_profile(profile, material)
    assert matched["status"] == "match"
    assert len(matched["matches"]) == 6

    material["chart_labels"]["western_ascendant"] = "Leo"
    conflicted = compare_material_to_profile(profile, material)
    assert conflicted["status"] == "conflict"
    assert conflicted["conflicts"][0]["field"] == "western_ascendant"
