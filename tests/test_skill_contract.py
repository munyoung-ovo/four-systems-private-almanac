from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_skill_has_compact_progressive_routing():
    skill = _read("SKILL.md")
    assert len(skill.splitlines()) < 100
    assert "按需路由" in skill
    assert "不在每次启动时检查或安装依赖" in skill
    assert "reference/response_boundary.md" in skill
    assert "engines.task_router.route_task" in skill
    assert "engines.evidence_packet.build_chart_packet" in skill
    assert "reference/interpretation_protocol.md" in skill
    assert "reference/system_interpretation.md" in skill
    assert "reference/topic_interpretation.md" in skill


def test_legacy_chart_prompt_is_router_only():
    prompt = _read("prompts/deep_chart.md")
    assert len(prompt.splitlines()) < 30
    assert "不要同时加载新旧长提示" in prompt


def test_all_generation_prompts_lock_facts_to_structured_input():
    prompts = [
        _read("prompts/deep_chart_brief.md"),
        _read("prompts/deep_chart_long.md"),
        _read("prompts/daily_tongshu.md"),
        _read("prompts/electional.md"),
        _read("prompts/heban.md"),
    ]
    for prompt in prompts:
        assert "```json" in prompt
        assert any(term in prompt for term in ("唯一事实来源", "输入事实仅来自", "不得成为证明", "不能替代合盘证据"))


def test_agent_metadata_is_readable_chinese():
    metadata = _read("agents/openai.yaml")
    assert 'display_name: "黄道吉日"' in metadata
    assert "$huangdao-jiri" in metadata


def test_four_system_architecture_defines_all_layers():
    architecture = _read("reference/four_system_architecture.md")
    for name in ("八字", "紫微", "印占", "西占", "四系统融合", "模型路由"):
        assert f"## {name}" in architecture
    assert "effective_weight" in architecture


def test_interpretation_protocol_requires_falsifiable_boundaries():
    protocol = _read("reference/interpretation_protocol.md")
    for term in ("本命", "阶段", "事件/日期", "反证", "不符合时的校正顺序"):
        assert term in protocol


def test_topic_protocol_preserves_detailed_domain_reasoning():
    protocol = _read("reference/topic_interpretation.md")
    for heading in ("整体命盘与核验", "感情", "事业", "财运", "贵人", "健康与状态", "具体事件"):
        assert f"## {heading}" in protocol
    for safeguard in ("反馈不能反向生成盘面事实", "不能仅根据一个五行", "不自动等于盈利", "不编造方位"):
        assert safeguard in protocol


def test_model_cost_does_not_reduce_answer_or_chart_quality():
    skill = _read("SKILL.md")
    assert "模型路由服务于推理成本" in skill
    assert "不得减少排盘字段、降低断法标准或缩短用户应得的答案" in skill
