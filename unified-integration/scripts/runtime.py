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
DEFAULT_SKILL_CARDS = 8
MAX_SKILL_CARDS_LIMIT = 50


def redact(value: str) -> str:
    """Remove recognizable credentials before saving any natural language."""
    return redact_configured(value)


def skill_card_limit() -> int:
    """AE_MAX_SKILL_CARDS as a bounded positive int.

    A malformed or non-positive value falls back to the default instead of
    raising: an exception here would silently drop every prompt-time card.
    The rendered cards stay inside the MAX_SKILL_CARDS token budget anyway;
    the upper bound only caps ranking work.
    """
    try:
        value = int(os.environ.get("AE_MAX_SKILL_CARDS", DEFAULT_SKILL_CARDS))
    except (TypeError, ValueError):
        return DEFAULT_SKILL_CARDS
    if value < 1:
        return DEFAULT_SKILL_CARDS
    return min(value, MAX_SKILL_CARDS_LIMIT)


def skill_context(agent: str, prompt: str) -> str:
    """Bounded discovery cards for a prompt (L1 pointers, not skill bodies).

    The card names candidates and points at their SKILL.md; the agent
    fetches a card's detail only when it chooses that candidate. This
    keeps every prompt-submit injection inside the search-page budget
    instead of growing with description length.

    max_results is configurable via AE_MAX_SKILL_CARDS env var (default 8).
    The agent decides which skills to actually read/use from the suggestions.

    This is the Mode 0 render of the adaptive preflight (CONTRACT 8.5):
    missing model.json, mode 0, and every preflight failure path must
    produce exactly this payload.
    """
    spec = importlib.util.spec_from_file_location(
        "ae_skills_loader", Path(__file__).with_name("load-skills.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    loader = module.SkillsLoader(agent)
    max_results = skill_card_limit()
    matches = loader.find_skills(prompt, max_results=max_results)
    lines = []
    for item in matches:
        name = item.get("name", "")
        summary = (item.get("description") or "").strip().split("\n")[0][:100]
        # Upstream risk labels stay visible on the card itself, so offensive
        # methodology is never offered as an ordinary step (final audit).
        risk = (" [risk: offensive - needs explicit authorization]"
                if item.get("risk") == "offensive" else "")
        lines.append(f"- {name}: {summary}{risk}")
    if not lines:
        return ""
    return clamp_to_budget(
        "AgentEnhancements local skill candidates for this task (read the "
        "SKILL.md of one you choose; full catalog search: registry.py "
        "search \"<task>\"):\n" + "\n".join(lines),
        MAX_SKILL_CARDS,
        label="skill candidates",
    )


def prompt_context(agent: str, prompt: str, event: dict) -> str:
    """UserPromptSubmit context: adaptive preflight Modes 0/1/2.

    Mode 0 (missing or invalid model.json) never imports the preflight
    module, never reads credentials and never opens a socket: the
    legacy discovery cards are rendered directly, byte-identical to
    the pre-feature runtime (CONTRACT 8.5 parity gate). Modes 1 and 2
    load the shared handler; every failure falls back to this render.
    """
    try:
        from adaptive_preflight import (
            MODE_DISABLED,
            load_model_config,
            preflight_context,
        )
    except Exception:  # noqa: BLE001 - advisory by contract
        return skill_context(agent, prompt)
    config = load_model_config()
    if config.mode == MODE_DISABLED and not config.diagnosis:
        return skill_context(agent, prompt)
    return preflight_context(
        agent, prompt, event, fallback=skill_context
    ).context


def native_skill_targets() -> list[Path]:
    """Directories that Agent Skills harnesses auto-discover.

    Mirrors ``link-skills.sh``: AGENT_SKILLS_NATIVE_TARGETS overrides the four
    default host directories. Host-specific env overrides (CLAUDE_CONFIG_DIR,
    CODEX_HOME, XDG_CONFIG_HOME) are handled by the host adapters that set the
    override variable; this function never guesses them.
    """
    raw = os.environ.get("AGENT_SKILLS_NATIVE_TARGETS")
    if raw:
        return [Path(p).expanduser() for p in raw.split(":") if p.strip()]
    home = Path(os.environ.get("HOME") or Path.home()).expanduser()
    return [
        home / ".claude" / "skills",
        home / ".agents" / "skills",
        home / ".codex" / "skills",
        home / ".config" / "opencode" / "skills",
    ]


def observer_linked_in_host() -> bool | None:
    """True when a registry-owned task-observer symlink exists in a host.

    Returns None only when no native target directory is present. That case is
    NOT proof of a native skill: the catalog marks task-observer as a default
    source even before ``link-skills.sh`` has created any link, so suppressing
    the card from the catalog alone would silently remove observer context on a
    fresh or partial install.
    """
    targets = native_skill_targets()
    if not targets:
        return None
    skills_dir = Path(
        os.environ.get("AGENT_SKILLS_DIR")
        or Path(__file__).resolve().parents[1] / "skills"
    ).expanduser().resolve()
    managed = str(skills_dir) + os.sep
    saw_target = False
    for target in targets:
        if not target.is_dir():
            continue
        saw_target = True
        link = target / "task-observer"
        if not link.is_symlink():
            continue
        try:
            current = os.readlink(link)
        except OSError:
            continue
        if Path(current).name != "task-observer":
            continue
        if (current.startswith(managed)
                or "/unified-integration/skills/by-category/" in current):
            return True
    return False if saw_target else None


def observer_context(agent: str) -> str:
    """Bootstrap the Task Observer workspace and return bounded context.

    Present on EVERY session start (not keyword-matched), per the vendored
    skill's activation model: the observer is ambient. The card is bounded
    to MAX_OBSERVER_AMBIENT tokens (context contract §8.4): paths, the log
    command shape, and open-entry count - never observation bodies.
    Failures are advisory - a broken observer must never block the session.

    NOTE: Bootstrap always runs (Stop's backstop needs the workspace), but the
    context card is suppressed when task-observer is actually linked into a
    host skill directory. A catalog `source` is not proof of a link: it is set
    before ``link-skills.sh`` runs. When no target directory can be inspected,
    the card is kept (conservative, never silently drops observer context).
    """
    try:
        natively_linked = observer_linked_in_host()
    except (OSError, RuntimeError, ValueError):
        natively_linked = False
    if natively_linked is None:
        natively_linked = False

    try:
        spec = importlib.util.spec_from_file_location(
            "ae_task_observer", Path(__file__).with_name("task-observer.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        root = module.workspace_root()
        # Bootstrap is required even when the native skill supplies context:
        # the Stop backstop writes its checkpoint into this workspace.
        context = module.bootstrap_context(root, agent)
        if natively_linked:
            return ""
        return clamp_to_budget(
            context, MAX_OBSERVER_AMBIENT, label="task-observer",
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
    # Full paths isolate repositories with the same basename. An adapter
    # serving several identities from one cwd (a Hermes messaging gateway or
    # profile) adds an opaque memory_scope so their notes never mix.
    scope = str(event.get("memory_scope") or "")[:200]
    memory = AgentMemory(agent, project=f"{cwd}#{scope}" if scope else str(cwd))
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
        # Memory effects run exactly once per prompt, before and
        # independently of any preflight mode (CONTRACT 8.5).
        memory.save(
            f"session:{session_key}:task", redact(prompt)[:MAX_MEMORY], ttl_days=7
        )
        return prompt_context(agent, prompt, event)[:MAX_CONTEXT]
    if name in {"PreToolUse", "PostToolUse"}:
        # Tool bodies can contain secrets, source files, or huge output.
        # Record only a bounded tool name; never raw shell input/output.
        tool = str(event.get("tool_name") or "unknown")[:100]
        memory.save(
            f"session:{session_key}:last_tool",
            tool,
            memory_type="session_context",
            metadata={"event": name},
            ttl_days=7,
        )
    elif name == "Stop":
        message = event.get("last_assistant_message")
        if isinstance(message, str) and message.strip():
            memory.save(
                f"session:{session_key}:summary",
                redact(message)[:MAX_MEMORY],
                memory_type="session_context",
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
    parser.add_argument("--bridge", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        from project_paths import environment
        os.environ.update(environment())
        raw = sys.stdin.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError("hook input exceeds size limit")
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ValueError("hook input must be a JSON object")
        context = handle(args.agent, event)
        if args.bridge:
            # Private OpenCode adapter envelope. Prepare a legacy render for
            # host-side snapshot invalidation without another lifecycle event
            # or memory effect. Existing --text/native JSON outputs are intact.
            fallback = context
            if (event.get("hook_event_name") == "UserPromptSubmit"
                    and context.startswith("AgentEnhancements preflight")):
                fallback = skill_context(args.agent, str(event.get("prompt") or ""))
            print(json.dumps({"context": context, "fallback": fallback}))
        elif context:
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
