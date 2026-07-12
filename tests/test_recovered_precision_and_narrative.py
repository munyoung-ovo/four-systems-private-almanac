from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_recovered_details_preserve_chart_authority_and_natural_delivery():
    daily = _read("prompts/daily_tongshu.md")
    calendar = _read("reference/module_2_calendar.md")
    chart = _read("reference/module_3_chart.md")
    relationship = _read("prompts/heban.md")
    long_report = _read("prompts/deep_chart_long.md")

    assert "short_sign" in daily
    assert "render_tongshu_day(..., short_sign=short_sign)" in daily
    assert "短签只作标题浓缩，不能参与分数、档位、宜忌或日期排序" in calendar
    assert "它只是兴趣和沟通上下文" in chart
    assert "绝不进入命盘证据、改写盘面结论、改变系统权重" in chart
    assert "先在开头第一段自然点出这段共同窗口" in relationship
    assert "没有可靠日期时，不虚构时间线" in relationship
    assert "一条连贯叙事" in long_report
