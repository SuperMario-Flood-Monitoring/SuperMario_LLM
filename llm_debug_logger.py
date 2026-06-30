import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def is_enabled() -> bool:
    value = os.getenv("LLM_DEBUG_LOG_ENABLED", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _base_dir() -> Path:
    return Path(os.getenv("LLM_DEBUG_LOG_DIR", "llm-debug"))


def _make_debug_id(analysis_input: dict[str, Any]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    scenario_id = str(analysis_input.get("scenarioId") or "unknown")
    run_id = str((analysis_input.get("swmmSimulation") or {}).get("runId") or "no-run")
    suffix = uuid.uuid4().hex[:8]
    safe_scenario = "".join(ch if ch.isascii() and ch.isalnum() else "_" for ch in scenario_id)
    safe_run_id = "".join(
        ch if ch.isascii() and (ch.isalnum() or ch in {"-", "_"}) else "_"
        for ch in run_id
    )
    return f"{timestamp}_{safe_scenario}_{safe_run_id}_{suffix}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save_llm_input(
    *,
    system_prompt: str,
    human_message: str,
    analysis_input: dict[str, Any],
) -> str | None:
    if not is_enabled():
        return None

    debug_id = _make_debug_id(analysis_input)
    payload = {
        "debugId": debug_id,
        "loggedAt": datetime.now(timezone.utc).isoformat(),
        "analysisInput": analysis_input,
        "invokeMessages": [
            {"role": "system", "content": system_prompt},
            {"role": "human", "content": human_message},
        ],
    }
    _write_json(_base_dir() / "inputs" / f"{debug_id}.json", payload)
    return debug_id


def save_llm_answer(*, debug_id: str | None, answer: str) -> None:
    if not is_enabled():
        return

    resolved_debug_id = debug_id or f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}_answer"
    _write_text(_base_dir() / "answers" / f"{resolved_debug_id}.txt", answer)
