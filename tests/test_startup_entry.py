from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_skill_metadata_explicitly_covers_common_activation_phrases():
    skill = _read("SKILL.md")
    metadata = _read("agents/openai.yaml")

    for phrase in ("载入 skill", "载入这个 skill", "载入黄道吉日", "使用黄道吉日", "打开黄道吉日"):
        assert phrase in skill
    assert "载入黄道吉日" in metadata


def test_startup_handles_activation_prefixes_and_direct_questions():
    startup = _read("reference/startup.md")

    assert "启动语与具体问题出现在同一句" in startup
    assert "直接处理后面的具体问题，不显示菜单" in startup
    assert "不得回复“无法载入”" in startup
    assert "按含义路由到对应模块" in startup
    assert "不要假装 skill 没有启动" in startup
