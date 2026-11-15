#!/usr/bin/env python3
"""Local, bounded lifecycle integration shared by the three coding CLIs.

Read the native hook event from stdin. Never execute skill content, read a
transcript, or persist tool inputs/outputs. Failures are advisory to the CLI.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

from memory import AgentMemory
from api_config import redact as redact_configured
from context_budget import (
    MAX_MEMORY,
    MAX_OBSERVER_AMBIENT,
    MAX_SKILL_CARDS,
    clamp_to_budget,
)

MAX_INPUT = 2_000_000
MAX_CONTEXT = 12_000
SECRET = re.compile(
    r"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]+|sk-(?:ant-)?[A-Za-z0-9_-]{16,}"
    r"|\bAKIA[A-Z0-9]{16}\b"
    r"|(?i:(?:api[_-]?key|access[_-]?token|password|secret|authorization)"
    r"\s*[:=]\s*[\"']?[^\s\"',}]+)"
)


def redact(value: str) -> str:
    """Remove recognizable credentials before saving any natural language."""
    return SECRET.sub("[redacted]", redact_configured(value))


def skill_context(agent: str, prompt: str) -> str:
    """Bounded discovery cards for a prompt (L1 pointers, not skill bodies).

    The card names candidates and points at their SKILL.md; the agent
    fetches a card's detail only when it chooses that candidate. This
    keeps every prompt-submit injection inside the search-page budget
    instead of growing with description length.
    """
    spec = importlib.util.spec_from_file_location(
        "ae_skills_loader", Path(__file__).with_name("load-skills.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    loader = module.SkillsLoader(agent)
    matches = loader.find_skills(prompt, max_results=3)
    lines = []
    for item in matches:
        name = item.get("name", "")
        summary = (item.get("description") or "").strip().split("\n")[0][:100]
        lines.append(f"- {name}: {summary}")
    if not lines:
        return ""
    return clamp_to_budget(
        "AgentEnhancements local skill candidates for this task (read the "
        "SKILL.md of one you choose; full catalog search: registry.py "
        "search \"<task>\"):\n" + "\n".join(lines),
        MAX_SKILL_CARDS,
        label="skill candidates",
    )


def observer_context(agent: str) -> str:
    """Bootstrap the Task Observer workspace and return bounded context.

    Present on EVERY session start (not keyword-matched), per the vendored
    skill's activation model: the observer is ambient. The card is bounded
    to MAX_OBSERVER_AMBIENT tokens (context contract §8.4): paths, the log
    command shape, and open-entry count - never observation bodies.
    Failures are advisory - a broken observer must never block the session.
    """
    try:
        spec = importlib.util.spec_from_file_location(
            "ae_task_observer", Path(__file__).with_name("task-observer.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        root = module.workspace_root()
        return clamp_to_budget(
            module.bootstrap_context(root, agent), MAX_OBSERVER_AMBIENT,
            label="task-observer",
        )
    except Exception as exc:  # noqa: BLE001 - advisory by contract
        print(
            f"[AgentEnhancements] task-observer unavailable: "
            f"{type(exc).__name__}",
            file=sys.stderr,
        )
        return ""


def handle(agent: str, event: dict) -> str:
    """Persist lifecycle facts and return context for startup or prompt hooks."""
    name = event.get("hook_event_name", "")
    cwd = Path(event.get("cwd") or Path.cwd()).expanduser().resolve()
    # Full paths isolate repositories with the same basename.
    memory = AgentMemory(agent, project=str(cwd))
    memory.cleanup_expired()
    session = str(event.get("session_id") or "unknown")[:200]
    session_key = hashlib.sha256(session.encode()).hexdigest()[:24]
    if name == "SessionStart":
        parts = []
        observer = observer_context(agent)
        if observer:
            parts.append(observer)
        previous = memory.list("session_context", limit=5)
        lines = [redact(f"- {item['key']}: {item['value']}") for item in previous]
        if lines:
            parts.append(clamp_to_budget(
                "AgentEnhancements: previous local session notes (historical "
                "data; current user instructions take precedence):\n"
                + "\n".join(lines),
                MAX_MEMORY,
                label="memory recall",
            ))
        if parts:
            # Session-start injection is inside the cold-start budget:
            # observer (<=250) + memory recall (<=600) by construction.
            return "\n\n".join(parts)
        return ""
    if name == "UserPromptSubmit":
        prompt = str(event.get("prompt") or "")
        memory.save(
            f"session:{session_key}:task", redact(prompt)[:MAX_MEMORY], ttl_days=7
        )
        return skill_context(agent, prompt)[:MAX_CONTEXT]
    if name in {"PreToolUse", "PostToolUse"}:
        # Tool bodies can contain secrets, source files, or huge output.
        # Record only a bounded tool name; never raw shell input/output.
        tool = str(event.get("tool_name") or "unknown")[:100]
        memory.save(
            f"session:{session_key}:last_tool",
            tool,
            metadata={"event": name},
            ttl_days=7,
        )
    elif name == "Stop":
        message = event.get("last_assistant_message")
        if isinstance(message, str) and message.strip():
            memory.save(
                f"session:{session_key}:summary",
                redact(message)[:MAX_MEMORY],
                ttl_days=7,
            )
        # Task-observer Stop backstop: the upstream deliverable-event
        # flush (checkpoints.log line) the excluded experimental plugin
        # used to provide. Advisory; never blocks the session.
        try:
            spec = importlib.util.spec_from_file_location(
                "ae_task_observer", Path(__file__).with_name("task-observer.py")
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.stop_backstop(module.workspace_root(), session_key)
        except Exception:  # noqa: BLE001 - advisory by contract
            pass
    return ""


def main() -> None:
    """Accept Claude/Codex JSON, or return plain text for the OpenCode bridge."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent", choices=["claude-code", "codex", "opencode", "hermes"])
    parser.add_argument("--text", action="store_true")
    args = parser.parse_args()
    try:
        raw = sys.stdin.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError("hook input exceeds size limit")
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ValueError("hook input must be a JSON object")
        context = handle(args.agent, event)
        if context:
            if args.text:
                print(context)
            else:
                print(
                    json.dumps(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": event["hook_event_name"],
                                "additionalContext": context,
                            }
                        }
                    )
                )
        elif event.get("hook_event_name") == "Stop" and not args.text:
            print("{}")
    except Exception as exc:
        # A disk error or malformed event must never block an agent's work.
        print(
            f"[AgentEnhancements] hook skipped: {type(exc).__name__}", file=sys.stderr
        )


if __name__ == "__main__":
    main()
