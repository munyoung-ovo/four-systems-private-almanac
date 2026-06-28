import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".skill_deps"))

from engines.build_profile import build_profile


def _profile(name: str, birth: str, gender: str = "女"):
    return build_profile(
        name,
        birth,
        gender,
        birth_place_name="测试城市",
        time_precision="exact",
        save=False,
    )


def test_action_map_has_new_product_structure():
    from engines.render import render_treasure_map

    html = render_treasure_map(_profile("_test_action", "1995-03-12T08:30:00"), "2026-06")

    assert "{{" not in html
    assert "运势行动图" in html
    assert "本阶段策略" in html
    assert "推进窗口" in html
    assert "避坑窗口" in html
    assert "月度藏宝图" not in html


def test_relationship_map_shows_selected_names_by_default():
    from engines.render import render_relationship_map

    a = _profile("真实姓名甲", "1995-03-12T08:30:00")
    b = _profile("真实姓名乙", "1996-08-20T20:10:00", "男")

    html = render_relationship_map(a, b)

    assert "{{" not in html
    assert "关系说明书" in html
    assert "真实姓名甲 × 真实姓名乙" in html
    assert "未来30天" in html


def test_relationship_map_can_show_alias_without_real_names():
    from engines.render import render_relationship_map

    a = _profile("真实姓名甲", "1995-03-12T08:30:00")
    b = _profile("真实姓名乙", "1996-08-20T20:10:00", "男")

    html = render_relationship_map(a, b, alias_a="我", alias_b="对方", show_names=False)

    assert "我 × 对方" in html
    assert "真实姓名甲" not in html
    assert "真实姓名乙" not in html
