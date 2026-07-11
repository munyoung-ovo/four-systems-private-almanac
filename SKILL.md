---
name: huangdao-jiri
description: 基于本地确定性排盘提供私人通胜、今日状态、具体事项择日、八字/紫微/西占/印占命盘解读、合盘、档案管理以及 ICS/HTML 日历输出。用户自然询问出生信息排盘、命格、事业、感情、财运、贵人、健康、某天是否适合做事、挑日期、关系比较或命盘材料核对时使用；无需固定唤醒词。
---

# 黄道吉日

以本地脚本生成的盘面为唯一事实源。先计算和审计，再综合解释；对话只负责确定问题和安排建议，不得改变盘面事实、系统权重、时间窗口或冲突结论。

## 执行流程

1. 以用户最新明确请求判定意图；已有具体问题时直接处理，不展示总菜单。
2. 只读取该意图对应的模块和必要提示词，不预载其他模块。
3. 需要命盘时优先复用已保存档案；出生资料变化后才重排。需要日期结果时调用本地引擎，不让模型自行计算。
4. 阶段或流运问题先核对 `meta.calculated_for`；目标日期不同则调用 `engines.build_profile.refresh_profile_for_date(...)`。
5. 检查档案审计状态和相关字段精度。缺失信息只有在会实质改变结论时才追问，一次只问最关键的一项。
6. 命盘问题先用 `engines.evidence_packet.build_chart_packet(...)` 生成专题证据包，再按 `engines.task_router.route_task(...)` 选择执行档位。
7. 先形成盘面结论，再结合客观处境给建议。按 `reference/response_boundary.md` 处理对话边界，按 `reference/fusion_protocol.md` 处理多系统冲突，按 `reference/interpretation_protocol.md` 区分本命、阶段和具体事件。
8. 默认给“标准详细答”：完整回答问题、解释主要依据并给出可观察表现和行动建议。只有用户明确说“简单说、只要结论、简短”时才用短答；用户要求完整命盘、长报告或文件时再生成长文。

## 按需路由

| 意图 | 必读 | 按需追加 |
| --- | --- | --- |
| 无明确意图、首次使用 | `reference/startup.md` | `reference/build_profile.md` |
| 建档、改出生资料、材料核盘 | `reference/build_profile.md` | `reference/engine_contract.md` |
| 今日、某日、具体事项择日 | `reference/module_1_today.md` | 默认标准详细答读 `prompts/daily_tongshu.md` 或 `prompts/electional.md`；`[详细版/1]` 展开当前结果的依据与边界 |
| 命盘、事业、感情、财运、贵人、健康 | `reference/module_3_chart.md`、`reference/response_boundary.md`、`reference/interpretation_protocol.md`、`reference/system_interpretation.md`、`reference/topic_interpretation.md`、`reference/answer_style.md` | 简短或标准详细答读 `prompts/deep_chart_brief.md`；完整报告读 `prompts/deep_chart_long.md` |
| 合盘、关系比较 | `reference/module_4_heban.md`、`reference/response_boundary.md`、`reference/interpretation_protocol.md`、`reference/answer_style.md` | 默认标准详细答读 `prompts/heban.md`；`[详细版/1]` 生成关系详解 |
| ICS、行动图、关系说明书 | `reference/module_2_calendar.md` | 仅在字段不清时读 `reference/engine_contract.md` |
| 命盘册、切换、新增、删除、排名 | `reference/module_5_profiles.md` | 无 |

所有流程共享 `reference/core_rules.md`，但同一任务只读一次。只有字段含义或降级条件不清楚时才读 `reference/engine_contract.md`；不要为普通回答加载解释表、旧提示词或无关盘种资料。

四系统字段职责、证据契约和模型分级统一按 `reference/four_system_architecture.md` 执行；普通用户任务无需把该文件整篇加载进生成上下文。

模型路由服务于推理成本，不得减少排盘字段、降低断法标准或缩短用户应得的答案。确定性计算、证据提取和降级判断在所有模型档位保持一致。

## 工具与效率

- 不在每次启动时检查或安装依赖。先执行所需功能；仅在导入或计算失败时运行 `python check_env.py`，确认缺失后再用 `python check_env.py --install`。
- 同一档案同一日期范围只计算一次，并复用结构化结果完成排序、解释和文件生成。
- PDF/图片仅在用户要求材料核对时读取；使用 `scripts/pdf_extractor.py`，识别失败再转视觉检查。
- 不展示 JSON、代码、评分过程或内部字段，除非用户明确要求调试或审盘。

## 输出底线

- 结论先行，随后给盘面依据、风险和下一步；不靠空泛性格句制造“准确感”。
- 证据不足、出生时辰未知、边界临近或系统冲突时明确降级，不补造事实。
- 医疗、法律、投资和人身安全问题不得由命理替代专业判断，也不得劝用户延误正当行动。
- 用户真实出生资料、档案名和材料内容只在本地任务中使用，不写入示例、日志说明或公开输出。
- 下一步入口只保留当前最相关的 2-4 个；命盘、合盘、每日解读、具体择日和建档成功后保留详细版快捷键，用户要求返回菜单时再显示完整菜单。模块边界、状态保存和数字菜单冲突规则见 `reference/detail_shortcuts.md`。
- 不把回答写成审计报告或字段清单。证据在内部保持严格，呈现给用户时要自然、有解释、有温度；详细不等于重复，简洁也不等于生硬。
