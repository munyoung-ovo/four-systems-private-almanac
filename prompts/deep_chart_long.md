# Deep Chart Long Prompt

Use only for `[详细版/1]`, “展开详细”, “完整命盘”, or explicit long-form topic detail. Short topic answers should use `prompts/deep_chart_brief.md`.

## Input

```json
{{profile_json}}
```

## Before Writing

- Resolve the detail topic from `profiles/_ui_state.json`; do not rely only on chat memory.
- Read or regenerate `profiles/[name].audit.json`.
- `stable`: write normally. `caution`: soften related claims. `high_risk`: ask for confirmation before writing strong long-form conclusions.
- Write the full result to `outputs/*.md`; chat gets only a 3-5 sentence summary and file path.
- Never write chat route buttons into the Markdown file.

## Length

- Topic detailed version: at least 1200 Chinese characters.
- Love/career/wealth: recommended 1800-3000 Chinese characters.
- Full four-system portrait: recommended 1800-3000 Chinese characters.

## Structure

Use 4-6 natural sections. Each section should cover:

- what this means in plain language
- why the chart supports it
- what the user can do

Keep the ratio near 70% plain-language interpretation, 20% chart evidence, 10% technical notes. Translate every technical term immediately.

## Topic Minimums

- Love: intimacy pattern, suitable people, relationship risk, communication style, next-year rhythm, practical advice.
- Career: work environment, ability monetization, track choice, current phase, cooperation/job change/side project risk, practical advice.
- Wealth: where money comes from, how to keep it, cooperation/investment risk, resource strategy, spending/cash-flow advice.
- Helpful people: type, channels, recognition cues, relationship maintenance, current window, people to avoid.
- Health: rhythm, stress pattern, five-element bias, sleep/movement/food direction, current care focus. Do not predict diseases.

## Full Portrait

For complete chart portrait, integrate BaZi, Ziwei, Western, and Vedic into one person. Do not paste four separate system reports. If systems conflict, explain whether the conflict is about timing, domain, layer, or signal strength.
