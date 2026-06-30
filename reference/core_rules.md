# Core Rules

## Calculation

- All BaZi, Ziwei, Western, Vedic, daily, electional, calendar, and relationship facts must come from local scripts.
- If data or dependencies are missing, degrade or ask for missing information; never fill chart facts from imagination.
- Every saved build/rebuild must create or refresh `profiles/[name].audit.json` with `engines.audit.save_audit(profile)`.
- Before long detailed readings, read `profiles/[name].audit.json`; regenerate it if missing.

## Audit Status

- `stable`: proceed normally.
- `caution`: keep related claims conservative.
- `high_risk`: ask for birth data or material confirmation before strong conclusions or long-form detail.

## Materials

- PDF/image materials are evidence only. They never override locally calculated chart facts.
- Use `scripts/pdf_extractor.py` for PDF and image files.
- If OCR is unavailable or weak, use AI visual inspection to extract birth fields or chart labels, then cross-check.
- If material labels conflict with local results, ask the user to confirm birth time, place, timezone, calendar type, or whether the material belongs to the same person.

## Routing And Files

- If the user has a concrete intent, route directly; do not force the main menu.
- Show system-order/sorting controls only when the user asks about priority, order, weighting, or custom preference.
- Keep next-step route buttons in chat only; never write them into `outputs/*.md`.
- Store recent chart topic state with `engines.ui_state.set_chart_topic(...)`; `[详细版/1]` resolves from `profiles/_ui_state.json`.
