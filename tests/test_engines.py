
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".skill_deps"))

import pytest
from engines.bazi import build as bazi_build
from engines.ziwei import build as ziwei_build
from engines.vedic import build as vedic_build
from engines.western import build as western_build
from engines.daily import build as daily_build
from engines.personalize import build as p_build
from engines.build_profile import build_profile

CASE_001 = {
    "solar_dt": "1995-03-12T08:30:00",
    "gender": "女",
    "expected_bazi": {
        "year": "乙亥", "month": "己卯", "day": "壬寅", "time": "甲辰"
    },
    "expected_nakshatra": "Punarvasu",
    "expected_sun_sign": "双鱼",
}

class TestBazi:
    def test_case001_four_pillars(self):
        r = bazi_build(CASE_001["solar_dt"], CASE_001["gender"])
        p = r["pillars"]
        exp = CASE_001["expected_bazi"]
        assert p["year"]  == exp["year"],  f"year: {p['year']}"
        assert p["month"] == exp["month"], f"month: {p['month']}"
        assert p["day"]   == exp["day"],   f"day: {p['day']}"
        assert p["hour"]  == exp["time"],  f"time: {p['hour']}"

    def test_noon_boundary(self):
        r1 = bazi_build("1990-06-15T10:59:00", "男", use_true_solar=False)
        r2 = bazi_build("1990-06-15T11:01:00", "男", use_true_solar=False)
        assert r1["pillars"]["hour"] == "癸巳", r1["pillars"]["hour"]
        assert r2["pillars"]["hour"] == "甲午", r2["pillars"]["hour"]
        assert r1["pillars"]["day"]  == r2["pillars"]["day"]

    def test_leap_month(self):
        from lunar_python import Solar
        l = Solar.fromYmdHms(2012, 6, 1, 10, 0, 0).getLunar()
        assert l.getMonth() == -4
        assert l.getDay()   == 12
        r = bazi_build("2012-06-01T10:00:00", "女")
        assert r["pillars"]["year"] == "壬辰"
        assert r["pillars"]["day"]  == "癸巳"

    def test_unknown_time_precision(self):
        r = bazi_build("1995-03-12T00:00:00", "女", time_precision="unknown")
        assert r["pillars"]["hour"] is None
        assert r["degraded"] is True

    def test_true_solar_metadata_present(self):
        r = bazi_build("1995-03-12T08:30:00", "女")
        assert r["time_adjustment"]["enabled"] is True
        assert "effective_time" in r["time_adjustment"]
        assert "boundary_warnings" in r

    def test_true_solar_can_shift_hour_pillar(self):
        clock = bazi_build("1995-03-12T08:30:00", "女", use_true_solar=False)
        far_west = bazi_build("1995-03-12T08:30:00", "女", lon=75, tz=8)
        assert clock["pillars"]["hour"] != far_west["pillars"]["hour"]
        assert far_west["time_adjustment"]["total_correction_minutes"] < -150

    def test_build_profile_threads_lon_tz_to_bazi(self):
        p = build_profile("_test_true_solar", "1995-03-12T08:30:00", "女",
                          lon=75, tz=8, time_precision="exact", save=False)
        assert p["bazi"]["time_adjustment"]["total_correction_minutes"] < -150

    def test_luck_pillars_present(self):
        r = bazi_build(CASE_001["solar_dt"], CASE_001["gender"], current_year=2026)
        luck = r["luck"]
        assert luck["degraded"] is False
        assert luck["direction"] in ("forward", "backward")
        assert len(luck["dayun"]) == 9 or len(luck["dayun"]) == 10
        assert luck["current_dayun"]["gan_zhi"] == "壬午"
        assert luck["current_liunian"]["year"] == 2026

    def test_day_master_present(self):
        r = bazi_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert r["day_master"] in "甲乙丙丁戊己庚辛壬癸"

    def test_yong_shen_nonempty(self):
        r = bazi_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert len(r["yong_shen"]) > 0

class TestZiwei:
    def test_twelve_palaces(self):
        r = ziwei_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert len(r["palaces"]) == 12
        assert len(r["palace_by_name"]) == 12
        assert "命宫" in r["palace_by_name"]

    def test_soul_palace_exists(self):
        r = ziwei_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert r["soul_palace"] is not None
        assert len(r["soul_palace"]["name"]) > 0

    def test_horoscope_layers_present(self):
        r = ziwei_build(CASE_001["solar_dt"], CASE_001["gender"], target_date="2026-06-25")
        layers = r["horoscope_layers"]
        for key in ("decadal", "yearly", "monthly", "daily"):
            assert key in layers
            assert layers[key]["flow_soul_palace"]
            assert len(layers[key]["transforms"]) == 4
        assert layers["yearly"]["transforms"][0]["star"] == "天同"

    def test_five_elements_class(self):
        r = ziwei_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert r["five_elements_class"] != ""

    def test_ziwei_basis_has_enriched_palaces(self):
        r = ziwei_build(CASE_001["solar_dt"], CASE_001["gender"], target_date="2026-06-25")
        basis = r["ziwei_basis"]
        assert basis["available"] is True
        assert basis["validation"]["palace_count"] == 12
        assert len(basis["palaces"]) == 12
        first = basis["palaces"][0]
        assert "strength" in first
        assert "opposite_index" in first
        assert "triad_indices" in first and len(first["triad_indices"]) == 3
        assert "career" in basis["topic_index"]
        assert basis["topic_index"]["career"]

    def test_ziwei_basis_empty_palace_borrows_opposite(self):
        r = ziwei_build(CASE_001["solar_dt"], CASE_001["gender"], target_date="2026-06-25")
        empty = next(p for p in r["ziwei_basis"]["palaces"] if not p["major_stars"])
        opposite = r["ziwei_basis"]["palaces"][empty["opposite_index"]]
        assert empty["borrowed_major_stars"] == opposite["major_stars"]

    def test_horoscope_layers_have_summary_indexes(self):
        r = ziwei_build(CASE_001["solar_dt"], CASE_001["gender"], target_date="2026-06-25")
        summary = r["horoscope_layers"]["summary"]["yearly"]
        assert summary["transform_by_type"]["禄"]["star"] == "天同"
        assert "福德" in summary["transform_by_palace"]
        assert summary["active_palaces"]

    def test_time_index_conversion(self):
        from engines.ziwei import _hour_to_time_index
        assert _hour_to_time_index(8, 30)  == 4
        assert _hour_to_time_index(14, 0)  == 7
        assert _hour_to_time_index(0, 30)  == 0
        assert _hour_to_time_index(23, 30) == 12

class TestVedic:
    def test_nakshatra_lahiri(self):
        r = vedic_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert r["moon_nakshatra"] == CASE_001["expected_nakshatra"], \
            f"Got {r['moon_nakshatra']}"

    def test_ayanamsa_label(self):
        r = vedic_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert r["ayanamsa"] == "Lahiri"

    def test_vimshottari_present(self):
        r = vedic_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert "mahadasha" in r["vimshottari"]
        assert "birth_mahadasha" in r["vimshottari"]
        assert "current_mahadasha" in r["vimshottari"]
        assert len(r["vimshottari"]["timeline"]) == 9
        assert r["vimshottari"]["timeline"][0]["planet"] == r["vimshottari"]["birth_mahadasha"]
        assert r["vimshottari"]["timeline"][0]["start_date"]
        assert len(r["vimshottari"]["timeline"][0]["antardasha"]) == 9

    def test_vimshottari_current_uses_target_date(self):
        birth = vedic_build(CASE_001["solar_dt"], CASE_001["gender"],
                            target_date="1995-03-12")
        current = vedic_build(CASE_001["solar_dt"], CASE_001["gender"],
                              target_date="2026-06-30")
        assert birth["vimshottari"]["mahadasha"] == birth["vimshottari"]["birth_mahadasha"]
        assert current["vimshottari"]["target_date"] == "2026-06-30"
        assert current["vimshottari"]["current_antardasha"]

    def test_degraded_no_ascendant(self):
        r = vedic_build("1995-03-12T00:00:00", "女", "unknown")
        assert r["degraded"] is True

    def test_ashtakavarga_golden_337(self):
        r = vedic_build(CASE_001["solar_dt"], CASE_001["gender"], "exact")
        av = r["ashtakavarga"]
        assert av is not None
        assert av["sav_total"] == 337, av["sav_total"]
        assert av["bav_totals"] == {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54,
                                    "Jupiter": 56, "Venus": 52, "Saturn": 39}
        assert sum(av["sav"].values()) == 337
        assert av["validation"]["sav_total_is_337"] is True
        assert len(av["bav"]) == 7
        assert len(av["bav"]["Sun"]) == 12
        assert len(av["sav_by_house"]) == 12

    def test_ashtakavarga_none_when_degraded(self):
        r = vedic_build("1995-03-12T00:00:00", "女", "unknown")
        assert r["ashtakavarga"] is None

    def test_jyotish_basis_has_d1_foundation(self):
        r = vedic_build(CASE_001["solar_dt"], CASE_001["gender"], "exact")
        basis = r["jyotish_basis"]
        assert basis is not None
        assert basis["lagna"]["house"] == 1
        assert len(basis["planets"]) == 9
        assert basis["planets"]["Rahu"]["retrograde"] is True
        assert basis["planets"]["Ketu"]["retrograde"] is True
        assert basis["validation"]["rahu_ketu_opposition"] is True
        assert basis["validation"]["planet_count"] == 9
        assert set(basis["house_lords"]) == set(range(1, 13))

    def test_jyotish_basis_has_divisional_and_interpretive_fields(self):
        r = vedic_build(CASE_001["solar_dt"], CASE_001["gender"], "exact")
        basis = r["jyotish_basis"]
        for key in ("D9", "D10", "D4", "D5"):
            assert key in basis["divisional_charts"]
            assert "Lagna" in basis["divisional_charts"][key]
        assert basis["karakas"]["darakaraka"]
        assert "Moon" in basis["dignity"]
        assert "waxing" in basis["moon_phase"]

    def test_vimshottari_precision_metadata_and_ad_jd(self):
        r = vedic_build(CASE_001["solar_dt"], CASE_001["gender"],
                        target_date="2026-06-30")
        vim = r["vimshottari"]
        assert vim["precision"]["has_all_antardasha"] is True
        assert vim["precision"]["uses_birth_moon_longitude"] is True
        first_ad = vim["timeline"][0]["antardasha"][0]
        assert first_ad["start_jd"] < first_ad["end_jd"]

    def test_strength_metrics_are_explicitly_degraded(self):
        r = vedic_build(CASE_001["solar_dt"], CASE_001["gender"], "exact")
        metrics = r["jyotish_basis"]["strength_metrics"]
        assert metrics["available"] is False
        assert metrics["level"] == "not_configured"
        assert "combustion" in r["jyotish_basis"]

class TestWestern:
    def test_sun_sign(self):
        r = western_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert r["sun"] == CASE_001["expected_sun_sign"], f"Got {r['sun']}"

    def test_aspects_exist(self):
        r = western_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert len(r["natal_aspects"]) > 0
        assert "strength" in r["natal_aspects"][0]
        assert 0 <= r["natal_aspects"][0]["strength"] <= 1

    def test_planets_include_retrograde_state(self):
        r = western_build(CASE_001["solar_dt"], CASE_001["gender"])
        mercury = r["planets"]["水星"]
        assert "speed" in mercury
        assert "retrograde" in mercury

    def test_transit_hits_structure(self):
        from engines.western import transit_hits
        r = western_build(CASE_001["solar_dt"], CASE_001["gender"])
        hits = transit_hits(r, "2026-07-01")
        assert isinstance(hits, list)
        if hits:
            for field in ["transit_planet", "natal_point", "aspect", "strength"]:
                assert field in hits[0]

    def test_tropical_no_sidereal(self):
        vedic_build(CASE_001["solar_dt"], CASE_001["gender"])
        r = western_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert r["sun"] == "双鱼"

    def test_western_basis_has_traditional_layers(self):
        r = western_build(CASE_001["solar_dt"], CASE_001["gender"])
        basis = r["western_basis"]
        assert basis["zodiac"] == "tropical"
        assert basis["house_system"] == "Placidus"
        assert basis["moon_phase"]["phase"]
        assert basis["void_moon"]["available"] is True
        assert "dignity" in basis["planets"]["太阳"]
        assert basis["planets"]["太阳"]["house"] is not None

    def test_aspects_include_applying_or_separating(self):
        r = western_build(CASE_001["solar_dt"], CASE_001["gender"])
        assert any(a.get("phase") in ("applying", "separating") for a in r["natal_aspects"])

class TestPersonalize:
    def test_different_users_different_output(self):
        p1 = build_profile("_test_用户甲", "1995-03-12T08:30:00", "女", time_precision="exact")
        p2 = build_profile("_test_用户乙", "1980-07-15T14:00:00", "男", time_precision="exact")
        day = daily_build("2026-06-23")
        r1 = p_build(p1, day)
        r2 = p_build(p2, day)
        assert r1["score"] != r2["score"] or r1["tier"] != r2["tier"], \
            "个人化失效：两人结果完全相同"

    def test_output_has_required_fields(self):
        p = build_profile("_test_用户丙", "1995-03-12T08:30:00", "女", time_precision="exact")
        day = daily_build("2026-06-23")
        r = p_build(p, day)
        for field in ["date", "score", "personal_yi", "personal_ji", "flags", "tier"]:
            assert field in r, f"Missing field: {field}"

    def test_score_in_range(self):
        p = build_profile("_test_用户丁", "1995-03-12T08:30:00", "女", time_precision="exact")
        day = daily_build("2026-06-23")
        r = p_build(p, day)
        assert 0 <= r["score"] <= 100

    def test_tier_valid(self):
        p = build_profile("_test_用户戊", "1995-03-12T08:30:00", "女", time_precision="exact")
        day = daily_build("2026-06-23")
        r = p_build(p, day)
        assert r["tier"] in ("大吉", "吉", "平", "忌", "凶", "命定时刻")

class TestDailyPanchanga:
    def test_panchanga_has_yoga_and_karana(self):
        day = daily_build("2026-06-23")
        assert day["panchanga"]["yoga"]
        assert day["panchanga"]["karana"]
        assert 1 <= day["panchanga"]["tithi"] <= 30

class TestResonance:
    def _get_profile(self):
        return build_profile("_test_resonance", "1995-03-12T08:30:00", "女",
                             time_precision="exact")

    def test_analyze_date_returns_required_fields(self):
        from engines.resonance import analyze_date
        p = self._get_profile()
        r = analyze_date(p, "签约", "2026-07-01")
        for field in ["date", "act", "votes", "aligned_favor",
                      "resonance_strength", "conflict", "is_destined_moment"]:
            assert field in r, f"Missing field: {field}"

    def test_votes_has_four_systems(self):
        from engines.resonance import analyze_date
        p = self._get_profile()
        r = analyze_date(p, "签约", "2026-07-01")
        for sys_name in ("bazi", "ziwei", "vedic", "western"):
            assert sys_name in r["votes"]
            assert r["votes"][sys_name]["stance"] in ("favor", "neutral", "avoid")

    def test_strength_equals_favor_count(self):
        from engines.resonance import analyze_date
        p = self._get_profile()
        r = analyze_date(p, "签约", "2026-07-01")
        expected = sum(1 for v in r["votes"].values() if v["stance"] == "favor")
        assert r["resonance_strength"] == expected

    def test_destined_only_on_four_favor(self):
        from engines.resonance import analyze_date
        p = self._get_profile()
        r = analyze_date(p, "签约", "2026-07-01")
        if r["is_destined_moment"]:
            assert r["resonance_strength"] == 4
        else:
            assert r["resonance_strength"] < 4

    def test_find_best_dates_sorted(self):
        from engines.resonance import find_best_dates
        p = self._get_profile()
        candidates = ["2026-07-01", "2026-07-05", "2026-07-10", "2026-07-15"]
        results = find_best_dates(p, "嫁娶", candidates)
        strengths = [r["resonance_strength"] for r in results]
        assert strengths == sorted(strengths, reverse=True)

    def test_mercury_retrograde_avoid_contract(self):
        from engines.resonance import analyze_date, _is_mercury_retrograde
        assert _is_mercury_retrograde("2026-07-01")
        assert not _is_mercury_retrograde("2026-06-01")
        p = self._get_profile()
        r = analyze_date(p, "签约", "2026-07-01")
        assert r["votes"]["western"]["stance"] == "avoid"

    def test_votes_include_reliability_fields(self):
        from engines.resonance import analyze_date
        p = self._get_profile()
        r = analyze_date(p, "嫁娶", "2026-07-01")
        assert "weighted_score" in r
        for v in r["votes"].values():
            assert "strength" in v and 0 <= v["strength"] <= 1
            assert "confidence" in v and 0 <= v["confidence"] <= 1
            assert "scope" in v

    def test_feedback_calibration_changes_confidence(self):
        from engines.resonance import analyze_date
        p = self._get_profile()
        p["calibration"] = {
            "system_adjustments": [
                {"system": "western", "topic": "嫁娶", "confidence_adjustment": -0.3}
            ]
        }
        r = analyze_date(p, "嫁娶", "2026-07-01")
        assert r["votes"]["western"]["confidence"] < 0.78

class TestFusion:
    def _get_profile(self):
        return build_profile("_test_fusion", "1995-03-12T08:30:00", "女",
                             time_precision="exact", save=False)

    def test_fuse_date_returns_unified_language(self):
        from engines.fusion import fuse_date
        r = fuse_date(self._get_profile(), "签约", "2026-07-01")
        for field in ["topic", "overall", "state", "best_actions",
                      "avoid_actions", "risks", "one_liner", "evidence"]:
            assert field in r, f"Missing field: {field}"
        assert r["topic"] == "合作/文书"
        assert len(r["evidence"]) == 4
        assert all(e["signal"] in ("favor", "neutral", "avoid") for e in r["evidence"])

    def test_contract_retrograde_becomes_action_advice(self):
        from engines.fusion import fuse_date
        r = fuse_date(self._get_profile(), "签约", "2026-07-01")
        assert "签字" in r["avoid_actions"] or "付款" in r["avoid_actions"]
        assert "合同反复" in r["risks"]
        assert "四系统" not in r["one_liner"]

    def test_conflict_is_visible_when_signals_disagree(self):
        from engines.fusion import fuse_date
        r = fuse_date(self._get_profile(), "签约", "2026-07-01")
        signals = {e["signal"] for e in r["evidence"]}
        if "favor" in signals and "avoid" in signals:
            assert r["conflict"] is not None
            assert r["conflict"]["type"] in ("timeframe", "domain", "genuine_tension")

    def test_default_weight_policy_is_act_default(self):
        from engines.fusion import fuse_date
        r = fuse_date(self._get_profile(), "签约", "2026-07-01")
        assert r["weight_policy"] == "act_default"
        assert r["system_order"][0] == "western"

    def test_user_order_changes_effective_weights(self):
        from engines.fusion import fuse_date_with_order
        r = fuse_date_with_order(
            self._get_profile(), "签约", "2026-07-01",
            ["vedic", "bazi", "ziwei", "western"],
        )
        weights = {e["system"]: e["weight"] for e in r["evidence"]}
        assert r["weight_policy"] == "user_order_x_act"
        assert r["system_order"] == ["vedic", "bazi", "ziwei", "western"]
        assert weights["vedic"] > weights["western"]
        assert weights["bazi"] > weights["ziwei"]

    def test_profile_meta_can_store_user_order(self):
        from engines.fusion import fuse_date
        p = self._get_profile()
        p["meta"]["fusion_system_order"] = ["bazi", "ziwei", "vedic", "western"]
        r = fuse_date(p, "签约", "2026-07-01")
        assert r["weight_policy"] == "user_order_x_act"
        assert r["system_order"] == ["bazi", "ziwei", "vedic", "western"]

    def test_parse_order_choice_short_code(self):
        from engines.fusion import parse_order_choice
        r = parse_order_choice("b4213")
        assert r["mode"] == "custom"
        assert r["system_order"] == ["vedic", "ziwei", "bazi", "western"]

    def test_parse_order_choice_default(self):
        from engines.fusion import parse_order_choice
        assert parse_order_choice("a") == {"mode": "default", "system_order": []}

    def test_fuse_date_with_choice_uses_short_code(self):
        from engines.fusion import fuse_date_with_choice
        r = fuse_date_with_choice(self._get_profile(), "签约", "2026-07-01", "b4213")
        assert r["weight_policy"] == "user_order_x_act"
        assert r["system_order"] == ["vedic", "ziwei", "bazi", "western"]

class TestRender:
    def _profile(self):
        return build_profile("_test_render", "1995-03-12T08:30:00", "女",
                             time_precision="exact")

    def test_treasure_map_no_unfilled_slots(self):
        from engines.render import render_treasure_map
        p = self._profile()
        html = render_treasure_map(p, "2026-06")
        assert "{{" not in html, "Unfilled slot found in treasure_map"

    def test_treasure_map_has_structure(self):
        from engines.render import render_treasure_map
        p = self._profile()
        html = render_treasure_map(p, "2026-06")
        assert "运势行动图" in html
        assert "推进窗口" in html
        assert "day-card" in html or "no-good" in html

    def test_tongshu_day_no_unfilled_slots(self):
        from engines.render import render_tongshu_day
        p = self._profile()
        html = render_tongshu_day(p, "2026-06-28",
                                  short_sign="「测试短签」")
        assert "{{" not in html, "Unfilled slot found in tongshu_day"

    def test_tongshu_day_has_short_sign(self):
        from engines.render import render_tongshu_day
        p = self._profile()
        html = render_tongshu_day(p, "2026-06-28",
                                  short_sign="「测试短签」")
        assert "测试短签" in html

    def test_tongshu_day_disclaimer_present(self):
        from engines.render import render_tongshu_day
        p = self._profile()
        html = render_tongshu_day(p, "2026-06-28")
        assert "文化娱乐参考" in html

class TestInputSchema:
    def test_valid_input_passes(self):
        from engines.build_profile import validate_build_input
        errs = validate_build_input(name="张三", gender="女",
                                    solar_birth="1995-03-12T08:30:00",
                                    lat=31.23, lon=121.47, time_precision="exact")
        assert errs == [], errs

    def test_bad_gender_rejected(self):
        from engines.build_profile import validate_build_input
        assert validate_build_input(name="x", gender="male",
                                    solar_birth="1995-03-12T08:30:00")

    def test_bad_precision_rejected(self):
        from engines.build_profile import validate_build_input
        assert validate_build_input(name="x", gender="女",
                                    solar_birth="1995-03-12T08:30:00",
                                    time_precision="精确")

    def test_lat_out_of_range_rejected(self):
        from engines.build_profile import validate_build_input
        assert validate_build_input(name="x", gender="女",
                                    solar_birth="1995-03-12T08:30:00", lat=200)

    def test_build_profile_raises_on_bad_input(self):
        from engines.build_profile import build_profile
        with pytest.raises(ValueError):
            build_profile("_t_bad", "1995-03-12T08:30:00", "男的", time_precision="exact")

class TestZiweiRealHoroscope:
    def test_year_state_has_four_transforms(self):
        from engines.ziwei import year_horoscope_state
        st = year_horoscope_state("1995-03-12T08:30:00", "女", "2026-06-25", "exact")
        types = [t["type"] for t in st["transforms"]]
        assert types == ["禄", "权", "科", "忌"]
        for t in st["transforms"]:
            assert t["star"] and t["palace"]

    def test_year_state_matches_known_2026(self):
        from engines.ziwei import year_horoscope_state
        st = year_horoscope_state("1995-03-12T08:30:00", "女", "2026-06-25", "exact")
        by_type = {t["type"]: t["star"] for t in st["transforms"]}
        assert by_type == {"禄": "天同", "权": "天机", "科": "文昌", "忌": "廉贞"}

    def test_vote_ziwei_is_real_not_vedic_proxy(self):
        from engines.resonance import _vote_ziwei
        from engines.daily import build as daily_build
        p = build_profile("_test_zw_real", "1995-03-12T08:30:00", "女",
                          time_precision="exact")
        v = _vote_ziwei(p, daily_build("2026-06-25"), "签约")
        assert "化" in v["basis"] and "流年" in v["basis"]
        assert "大运" not in v["basis"]

    def test_vote_ziwei_only_acts_on_relevant_palace(self):
        from engines.resonance import _vote_ziwei
        from engines.daily import build as daily_build
        p = build_profile("_test_zw_rel", "1995-03-12T08:30:00", "女",
                          time_precision="exact")
        day = daily_build("2026-06-25")
        v_travel = _vote_ziwei(p, day, "出行")
        v_sign   = _vote_ziwei(p, day, "签约")
        assert v_travel["stance"] == "favor" and "迁移" in v_travel["basis"]
        assert v_sign["stance"] == "neutral"

    def test_vote_ziwei_degraded_neutral(self):
        from engines.resonance import _vote_ziwei
        from engines.daily import build as daily_build
        p = build_profile("_test_zw_deg", "1995-03-12T08:30:00", "女",
                          time_precision="unknown")
        v = _vote_ziwei(p, daily_build("2026-06-25"), "签约")
        assert v["stance"] == "neutral"
        assert "时辰未知" in v["basis"]

class TestSpecialPattern:
    def test_normal_chart_not_flagged(self):
        r = bazi_build("1995-03-12T08:30:00", "女", "exact")
        assert r["special_pattern"] is None

    def test_cong_weak_detected(self):
        r = bazi_build("1984-02-26T21:00:00", "男", "exact", use_true_solar=False)
        assert r["special_pattern"] is not None
        assert "从弱" in r["special_pattern"]
        assert r["strength_confidence"] <= 0.3

    def test_detection_is_rare(self):
        from datetime import date, timedelta
        n = hit = 0
        d = date(1985, 1, 1)
        while d <= date(1995, 1, 1):
            for hh in (6, 18):
                n += 1
                if bazi_build(f"{d.isoformat()}T{hh:02d}:00:00", "男", "exact")["special_pattern"]:
                    hit += 1
            d += timedelta(days=53)
        assert hit / n < 0.10, f"特殊格局触发率过高({hit}/{n})，疑似误报"

    def test_special_pattern_caps_personalize_confidence(self):
        p = build_profile("_test_cong", "1984-02-26T21:00:00", "男",
                          time_precision="exact", use_true_solar=False)
        r = p_build(p, daily_build("2026-06-25"))
        assert r["special_pattern"] is not None
        assert r["confidence"] <= 0.45
        assert "人工复核" in r["degrade_reason"]

    def test_special_pattern_disables_yong_shen_scoring(self):
        p = build_profile("_test_cong_yong", "1984-02-26T21:00:00", "男",
                          time_precision="exact", use_true_solar=False)
        r = p_build(p, daily_build("2026-06-26"))
        assert r["special_pattern"] is not None
        assert r["flags"]["用神得力"] is False
        assert not any("用神" in b["label"] or "忌神" in b["label"]
                       for b in r["score_breakdown"])
        reasons = [x["reason"] for x in r["personal_yi"] + r["personal_ji"]]
        assert not any("用神" in reason or "忌神" in reason for reason in reasons)

class TestEdgeCaseRegressions:

    def test_tz_honored_in_vedic(self):
        nyc8  = vedic_build("1990-01-01T08:00:00", "男", "exact",
                            lat=40.71, lon=-74.0, tz=8)
        nyc5  = vedic_build("1990-01-01T08:00:00", "男", "exact",
                            lat=40.71, lon=-74.0, tz=-5)
        assert nyc8["moon_nakshatra"] != nyc5["moon_nakshatra"], \
            "tz 未参与计算，疑似又被硬编码"

    def test_tz_honored_in_western(self):
        w8 = western_build("1990-01-01T23:30:00", "男", lat=40.71, lon_geo=-74.0,
                           time_precision="exact", tz=8)
        w5 = western_build("1990-01-01T23:30:00", "男", lat=40.71, lon_geo=-74.0,
                           time_precision="exact", tz=-5)
        assert w8["ascendant"] != w5["ascendant"] or w8["moon"] != w5["moon"]

    def test_tz_threaded_through_build_profile(self):
        p_default = build_profile("_test_tz_a", "1990-01-01T08:00:00", "男",
                                  lat=40.71, lon=-74.0, tz=8, save=False)
        p_nyc     = build_profile("_test_tz_b", "1990-01-01T08:00:00", "男",
                                  lat=40.71, lon=-74.0, tz=-5, save=False)
        assert p_default["vedic"]["moon_nakshatra"] != p_nyc["vedic"]["moon_nakshatra"]

    def test_polar_latitude_no_crash_vedic(self):
        r = vedic_build("1990-12-21T12:00:00", "男", "exact", lat=78.0, lon=15.0, tz=1)
        assert r["ascendant_nak"] is None
        assert r["ashtakavarga"] is None
        assert r["moon_nakshatra"]

    def test_polar_latitude_no_crash_western(self):
        r = western_build("1990-12-21T12:00:00", "男", lat=78.0, lon_geo=15.0,
                          time_precision="exact", tz=1)
        assert r["ascendant"] is None and r["mc"] is None
        assert r["sun"]

    def test_polar_latitude_build_profile_survives(self):
        p = build_profile("_test_polar", "1990-12-21T12:00:00", "男",
                          lat=78.0, lon=15.0, tz=1, birth_place_name="Svalbard",
                          time_precision="exact", save=False)
        assert p["western"]["ascendant"] is None
        assert p["bazi"]["day_master"] in "甲乙丙丁戊己庚辛壬癸"
        assert p["ziwei"]["soul_palace"] is not None

    def test_treasure_map_destined_uses_resonance_not_dead_flag(self):
        from engines.render import render_treasure_map
        from engines.ics_builder import _is_destined_moment
        from engines.daily import build as _daily
        from datetime import date as _date, timedelta as _td
        p = build_profile("_test_treasure", "1995-03-12T08:30:00", "女",
                          time_precision="exact", save=False)
        month = "2026-06"
        html = render_treasure_map(p, month)
        y, m = 2026, 6
        first = _date(y, m, 1)
        last  = _date(y, m + 1, 1) - _td(days=1)
        expected = 0
        for off in range((last - first).days + 1):
            d = first + _td(days=off)
            dd = _daily(d.isoformat())
            if p_build(p, dd)["tier"] == "大吉" and _is_destined_moment(p, dd):
                expected += 1
        assert "运势行动图" in html

    def test_personalize_never_emits_destined_tier(self):
        from engines.personalize import FLAG_KEYS
        assert "命定时刻" not in FLAG_KEYS

    def test_invalid_calendar_date_friendly_error(self):
        from engines.build_profile import build_profile as _bp
        with pytest.raises(ValueError) as ei:
            _bp("_test_baddate", "2025-02-30T08:00:00", "男",
                time_precision="exact", save=False)
        assert "合法日期" in str(ei.value)

    def test_render_escapes_user_name(self):
        from engines.render import render_tongshu_day
        p = build_profile("_test_xss", "1995-03-12T08:30:00", "女",
                          time_precision="exact", save=False)
        p["meta"]["name"] = "<b>x</b>"
        html = render_tongshu_day(p, "2026-06-25")
        assert "<b>x</b>" not in html
        assert "&lt;b&gt;" in html

def teardown_module(module):
    import glob
    for f in glob.glob("profiles/_test_*.json"):
        os.remove(f)
