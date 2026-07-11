# 命盘解读兼容入口

此文件只负责旧入口路由，不承载完整提示词。

- 快照、约 200 字专题和具体问题：使用 `prompts/deep_chart_brief.md`。
- 命盘模块中的 `[详细版/1]`、用户回复 `1`、`详细版`、`展开`、`深度解读`、专题长文和完整命盘：使用 `prompts/deep_chart_long.md`。其他模块的 `[详细版/1]` 必须按其自身提示词展开，不得路由到命盘长文。
- 解读前遵守 `reference/response_boundary.md`，多系统综合遵守 `reference/fusion_protocol.md`。
- 盘面字段不清或处于降级状态时，按 `reference/engine_contract.md` 核对，不自行推算。

不要同时加载新旧长提示，也不要从本文件生成正文。
