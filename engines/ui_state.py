from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "profiles"
STATE_PATH = PROFILES_DIR / "_ui_state.json"


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(**updates: Any) -> dict[str, Any]:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    state.update({key: value for key, value in updates.items() if value is not None})
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def set_chart_topic(topic: str, profile_name: str | None = None, module: str = "chart") -> dict[str, Any]:
    return save_state(active_profile=profile_name, last_module=module, last_topic=topic)


def resolve_detail_topic(default: str = "命盘总览") -> str:
    state = load_state()
    return state.get("last_topic") or default
