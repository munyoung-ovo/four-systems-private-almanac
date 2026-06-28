# Examples

This folder contains safe, fictional or sanitized examples for public demos.

Do not commit real birth charts, PDF files, generated readings, or personal
profiles. Put private files in `materials/`, `profiles/`, and `outputs/`;
those folders are ignored by git except for their `.gitkeep` files.

## Files

- `sample_profile_input.json` — a fictional profile input shape.
- `deep_chart_preview_t_val.md` — a short four-system deep-chart preview.
- `action_map_t_val_2026-06.html` — an example 30-day action map.
- `relationship_map_20260629_012844.html` — an example relationship brief.

## Example Input

```text
姓名：林小满
性别：女
出生：1998-04-12 09:30
地点：广东广州天河区
关系备注：我
```

## Example Flow

```text
① 今日算命
② 生成日历
③ 深度命盘解读
④ 合盘
⑤ 命盘册
```

## Privacy Note

The skill should use birth time and birthplace as the only source for chart
calculation. Uploaded PDFs may help identify birth information, but their
planet positions or timing tables should not replace local calculation.

Before publishing your own fork, check that example files do not contain real
names, exact birth data, private relationship notes, or generated readings from
real people.
