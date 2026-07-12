from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_first_run_without_a_profile_enters_the_profile_form():
    startup = _read("reference/startup.md")
    skill = _read("SKILL.md")

    assert "没有档案则直接进入首次资料填写引导" in startup
    assert "不能只在菜单里写“尚未建档”" in startup
    assert "不要先要求选“命盘解读”或再问一次要不要建档" in startup
    assert "出生日期：YYYY-MM-DD" in startup
    assert "用户明确说“先看功能”“先浏览菜单”时" in startup
    assert "当前没有档案时，直接进入资料填写引导" in skill
