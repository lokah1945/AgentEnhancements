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
    # The gateway keeps one process cwd for every chat; Hermes exposes the
    # working directory it gives tools as TERMINAL_CWD.
    event = {"hook_event_name": name, "session_id": session_id,
             "cwd": os.environ.get("TERMINAL_CWD") or os.getcwd(), **extra}
    try:
        result = subprocess.run(
            [str(python) if python.is_file() else sys.executable,
             str(UI / "scripts/runtime.py"), "hermes", "--text"],
            input=json.dumps(event), capture_output=True, text=True, timeout=8,
        )
        return result.stdout[:12000] if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""  # Local integration failures never interrupt the host.


def memory_scope(ctx, session_id: str, platform: str = "", sender_id: str = "") -> str:
    """Isolate AE notes per Hermes profile and, on messaging platforms, per
    sender (per session when the sender is unknown). Without it every chat
    user and profile of one gateway shared notes (final audit 2026-11-20)."""
    try:
        profile = str(getattr(ctx, "profile_name", "") or "default")
    except Exception:  # noqa: BLE001 - profile lookup is host state
        profile = "default"
    scope = f"hermes-profile:{profile}"
    if platform and platform != "cli":
        scope += f"|{platform}:{sender_id or 'session:' + session_id}"
    return scope[:200]


def register(ctx) -> None:
    """Register the public Hermes plugin hooks; never modify host approvals."""
    scopes: dict[str, str] = {}

    def scoped(session_id: str, platform: str = "") -> str:
        """Reuse the turn's pre_llm_call scope (post hooks carry no sender_id).

        An unknown session with no platform returns "": the profile-wide
        fallback would publish a messaging sender's records to every user
        of the profile, so the caller skips the event instead."""
        scope = scopes.get(session_id)
        if scope:
            return scope
        return memory_scope(ctx, session_id, platform) if platform else ""

    def before(session_id: str, user_message: str, is_first_turn: bool = False,
               platform: str = "", sender_id: str = "", **_):
        # Re-insert so dict order is recency order: eviction then drops the
        # least recently used session, never an active one.
        scopes.pop(session_id, None)
        scope = scopes[session_id] = memory_scope(ctx, session_id, platform, sender_id)
        if len(scopes) > 1000:
            scopes.pop(next(iter(scopes)))
        startup = runtime("SessionStart", session_id, memory_scope=scope) if is_first_turn else ""
        candidates = runtime("UserPromptSubmit", session_id, prompt=user_message, memory_scope=scope)
        text = "\n\n".join(part for part in (startup, candidates) if part)
        return {"context": text} if text else None

    def after(session_id: str, assistant_response: str, platform: str = "", **_) -> None:
        scope = scoped(session_id, platform)
        if scope:
            runtime("Stop", session_id, last_assistant_message=assistant_response,
                    memory_scope=scope)

    def tool(tool_name: str, session_id: str | None = None, **_) -> None:
        scope = scoped(session_id) if session_id else ""
        if scope:
            runtime("PostToolUse", session_id, tool_name=tool_name, memory_scope=scope)

    ctx.register_hook("pre_llm_call", before)
    ctx.register_hook("post_llm_call", after)
    ctx.register_hook("post_tool_call", tool)
