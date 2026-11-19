"""Bridge Hermes lifecycle events without reading or storing its transcript."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

UI = Path(__file__).resolve().parent.parent


def runtime(name: str, session_id: str, **extra: str) -> str:
    """Only explicit bounded event fields cross into the shared runtime."""
    state = Path(os.environ.get('AGENT_ENHANCEMENTS_STATE_DIR', UI.parent / '.agentenhancements'))
    python = state / 'runtime/venv/bin/python'
    event = {"hook_event_name": name, "session_id": session_id,
             "cwd": os.getcwd(), **extra}
    try:
        result = subprocess.run(
            [str(python) if python.is_file() else sys.executable,
             str(UI / "scripts/runtime.py"), "hermes", "--text"],
            input=json.dumps(event), capture_output=True, text=True, timeout=8,
        )
        return result.stdout[:12000] if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""  # Local integration failures never interrupt the host.


def register(ctx) -> None:
    """Register the public Hermes plugin hooks; never modify host approvals."""
    def before(session_id: str, user_message: str, is_first_turn: bool = False, **_):
        startup = runtime("SessionStart", session_id) if is_first_turn else ""
        candidates = runtime("UserPromptSubmit", session_id, prompt=user_message)
        text = "\n\n".join(part for part in (startup, candidates) if part)
        return {"context": text} if text else None

    def after(session_id: str, assistant_response: str, **_) -> None:
        runtime("Stop", session_id, last_assistant_message=assistant_response)

    def tool(tool_name: str, session_id: str | None = None, **_) -> None:
        if session_id:
            runtime("PostToolUse", session_id, tool_name=tool_name)

    ctx.register_hook("pre_llm_call", before)
    ctx.register_hook("post_llm_call", after)
    ctx.register_hook("post_tool_call", tool)
