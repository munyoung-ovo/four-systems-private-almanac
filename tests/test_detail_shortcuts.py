from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_detailed_shortcut_covers_interpretive_modules_without_cross_routing():
    core = _read("reference/core_rules.md")
    today = _read("reference/module_1_today.md")
    relationship = _read("reference/module_4_heban.md")
    shortcuts = _read("reference/detail_shortcuts.md")
    daily = _read("prompts/daily_tongshu.md")
    electional = _read("prompts/electional.md")
    heban = _read("prompts/heban.md")
    router = _read("engines/task_router.py")

    assert "每日解读和具体择日" in core
    assert "不占用 `1`" in core
    assert "整体状态和择日结果默认包含 `[详细版/1]`" in today
    assert "不补造未计算的时辰、方位或仪式" in today
    assert "不误路由到个人命盘" in relationship
    assert "只有当前回答明确展示 `[详细版/1]`" in shortcuts
    assert "250-450" in daily
    assert "默认保留 `[详细版/1]`" in daily
    assert "标准详细答结尾默认保留 `[详细版/1]`" in electional
    assert "第一个入口固定为 [详细版/1]" in heban
    assert 'STANDARD_INTENTS = {"daily", "chart_brief", "electional", "relationship_brief"}' in router
