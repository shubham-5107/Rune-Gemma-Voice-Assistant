"""JSONL interaction logger (logs/agent_log.jsonl, relative to project root)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "logs" / "agent_log.jsonl"


def log_interaction(
    query: str,
    model_output: str,
    validation: str,
    tool: str | None,
    result: str | None = None,
    error: str | None = None,
) -> None:
    """Append one interaction record; never raises so logging can't break the agent."""
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "raw_query": query,
        "model_output": model_output,
        "validation_status": validation,
        "tool_executed": tool,
        "result": result,
        "error": error,
    }
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as err:
        print(f"[log error] {err}")
