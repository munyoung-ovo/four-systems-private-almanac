from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_recovered_interaction_paths_cover_first_run_chart_and_relationships():
    startup = _read("reference/startup.md")
    chart = _read("reference/module_3_chart.md")
    relationship = _read("reference/module_4_heban.md")
    today = _read("reference/module_1_today.md")
    style = _read("reference/answer_style.md")

    assert "用这个资料建档/核盘" in startup
    assert "下周哪天面试好" in startup
    assert "[详细版/1] [感情/2] [事业/3] [具体的事/4]" in chart
    assert "默认作为 A，只让用户选 B" in relationship
    assert "情侣、家人、亲子、合伙人或朋友" in relationship
    assert "[详细版/1] [看具体事/2] [挑日期/3]" in today
    for term in ("建档", "今日与择日", "命盘", "合盘", "日历与命盘册"):
        assert term in style
