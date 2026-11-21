#!/usr/bin/env python3
"""Merge enhancements into the configuration actually read by each CLI.

Run with the isolated interpreter prepared by setup-mcp.sh. Provider choices,
credentials, tool approvals, user hooks and user MCP servers are preserved.
Only project-owned integration entries are managed; agent auth stays native.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import tomlkit

from api_config import BUILTINS, initialize
from native_config import managed_integration_path, read_json, write, write_json
from native_hermes import host_selection_path, install_hermes

EXTRA_COMMANDS = {"hermes": "hermes"}
NATIVE_AGENTS = ("claude-code", "codex", "opencode", "hermes")

UI = Path(__file__).resolve().parent.parent
ROOT = UI.parent
EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
)


def runtime_python() -> str:
    """Keep venv command paths stable across python/python3 entry points."""
    from project_paths import runtime_root
    local = runtime_root() / 'venv/bin/python3'
    if local.is_file():
        return str(local)
    canonical = Path(sys.prefix) / "bin/python3"
    if sys.prefix != sys.base_prefix and canonical.is_file():
        return str(canonical)
    return sys.executable


def own_hook(handler: dict) -> bool:
    """Recognize only hooks previously installed by AgentEnhancements."""
    command = str(handler.get("command", ""))
    return "unified-integration/" in command and any(
        x in command for x in ["scripts/runtime.py", "-memory-hook.py"]
    )


def merge_hooks(doc: dict, agent: str, install: bool = True) -> None:
    """Refresh our handlers in place, preserving other events and groups.

    AE's handler keeps its group and handler position, and a new group is
    appended only for an event that has none: Codex keys hook trust by
    event, group and handler index, so re-appending AE at the end shifted
    a user's later hook and silently untrusted it (final audit 2026-11-20).
    With install=False only previously installed AE handlers are removed
    (hosts whose config drops command hooks, e.g. OpenCode 2).
    """
    hooks = doc.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("hooks must be an object")
    handler = None
    if install:
        from project_paths import environment
        variables = environment()
        for name in ('AGENT_ENHANCEMENTS_API_FILE',):
            if os.environ.get(name):
                variables[name] = os.environ[name]
        command = shlex.join(['env', *[key+'='+value for key, value in variables.items()],
                              runtime_python(), str(UI / "scripts/runtime.py"), agent])
        handler = {"type": "command", "command": command, "timeout": 10}
    for event, groups in list(hooks.items()):
        retained = []
        placed = False
        for group in groups:
            handlers = []
            for item in group.get("hooks", []):
                if not own_hook(item):
                    handlers.append(item)
                elif handler is not None and event in EVENTS and not placed:
                    handlers.append(dict(handler))
                    placed = True
            if handlers:
                retained.append({**group, "hooks": handlers})
        hooks[event] = retained
        if not install and not retained:
            del hooks[event]
    if not install:
        if not hooks:
            del doc["hooks"]
        return
    for event in EVENTS:
        groups = hooks.setdefault(event, [])
        if not any(item == handler for group in groups for item in group.get("hooks", [])):
            groups.append({"hooks": [dict(handler)]})


def mcp_block() -> dict:
    """Expose one stable gateway; it gates and reloads credentials internally."""
    initialize()
    template = json.loads((UI / "mcp-servers/mcp.json.example").read_text())[
        "mcpServers"
    ]
    from project_paths import environment
    template['agent-enhancements'].setdefault('env', {}).update(environment())
    for name in (
        "AGENT_ENHANCEMENTS_API_FILE",
        "AGENT_MEMORY_ROOT",
        "AE_FFMPEG_ALLOWED_ROOTS",
    ):
        if os.environ.get(name):
            template["agent-enhancements"].setdefault("env", {})[name] = os.environ[
                name
            ]
    return {
        name: {
            **cfg,
            "command": runtime_python(),
            "args": [
                arg.replace("PLACEHOLDER_REPO_ROOT", str(ROOT)) for arg in cfg["args"]
            ],
        }
        for name, cfg in template.items()
    }


# Variables AE itself used to write into the gateway entry and no longer
# reads (preflight settings moved into ui.api.json). Refresh removes them so
# a moved checkout does not keep a dangling path; user variables stay.
RETIRED_GATEWAY_ENV = frozenset({"AGENT_ENHANCEMENTS_MODEL_FILE"})


def merge_servers(existing: dict, block: dict) -> None:
    """Refresh managed servers; keep name collisions belonging to the user."""
    # Retire only our previous direct entries. Leaving those active would
    # bypass the gateway's visibility and credential checks.
    for name in BUILTINS:
        old = existing.get(name)
        if isinstance(old, dict):
            command = old.get("args", old.get("command", []))
            if isinstance(command, list) and any(
                managed_integration_path(arg, "mcp-servers", name, "server.py")
                for arg in command
            ):
                del existing[name]
    for name, cfg in block.items():
        old = existing.get(name)
        if old is not None and old != cfg:
            old_args = old.get("args", old.get("command", []))
            if not isinstance(old_args, list) or not any(
                managed_integration_path(arg, "mcp-servers", "gateway.py")
                for arg in old_args
            ):
                print(f"[native] preserving user server: {name}", file=sys.stderr)
                continue
        # The managed command may change after an update; per-tool approvals,
        # timeouts and user environment entries are still the user's settings.
        merged = {**(old or {}), **cfg}
        for field in ("disabled", "codemode"):
            if old and field in old:
                merged[field] = old[field]
        for field in ("env", "environment"):
            if field in cfg and old and isinstance(old.get(field), dict):
                merged[field] = {
                    key: value for key, value in {**old[field], **cfg[field]}.items()
                    if key not in RETIRED_GATEWAY_ENV
                }
        existing[name] = merged


def install(agent: str, *, mcp_only: bool = False, profiles: list[str] | None = None) -> None:
    """Install one existing supported agent using its native configuration."""
    home = Path.home()
    block = mcp_block()
    if agent == "claude-code":
        config_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude"))
        if not mcp_only:
            path = config_dir / "settings.json"
            doc = read_json(path)
            merge_hooks(doc, agent)
            write_json(path, doc)
        # User-scope MCP is in ~/.claude.json, not ~/.claude/mcp.json.
        path = (
            config_dir / ".claude.json"
            if os.environ.get("CLAUDE_CONFIG_DIR")
            else home / ".claude.json"
        )
        doc = read_json(path)
        merge_servers(doc.setdefault("mcpServers", {}), block)
        write_json(path, doc)
    elif agent == "codex":
        config_dir = Path(os.environ.get("CODEX_HOME", home / ".codex"))
        path = config_dir / "config.toml"
        doc = tomlkit.parse(path.read_text()) if path.exists() else tomlkit.document()
        merge_servers(doc.setdefault("mcp_servers", {}), block)
        write(path, tomlkit.dumps(doc))
        if not mcp_only:
            path = config_dir / "hooks.json"
            hooks = read_json(path)
            merge_hooks(hooks, agent)
            write_json(path, hooks)
    elif agent == "opencode":
        # Never replace a working V1 config with a V2-only document.
        executable = shutil.which("opencode")
        if executable:
            version = subprocess.run([executable, "--version"], capture_output=True,
                                     text=True, timeout=10)
            if version.returncode or not version.stdout.strip().removeprefix("opencode v").startswith("2."):
                raise ValueError("OpenCode 2 is required; upgrade the CLI before installing its adapter")
        config_dir = (
            Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "opencode"
        )
        # Edit the existing JSONC file if present: a sibling JSON file can
        # otherwise be shadowed by a user's higher-precedence JSONC config.
        path = config_dir / "opencode.jsonc"
        if not path.exists():
            path = config_dir / "opencode.json"
        original_text = path.read_text(encoding="utf-8") if path.exists() else ""
        doc = read_json(path)
        doc.setdefault("$schema", "https://opencode.ai/config.json")
        converted = {
            name: {
                "type": "local",
                "command": [cfg["command"], *cfg["args"]],
                "disabled": False,
                "codemode": False,
                **({"environment": cfg["env"]} if cfg.get("env") else {}),
            }
            for name, cfg in block.items()
        }
        mcp = doc.setdefault("mcp", {})
        # OpenCode 2 ignores V1's flat mcp.<name> entries. Migrate valid
        # legacy servers (including personal ones) without changing their
        # commands, credentials or existing disabled state.
        servers = mcp.setdefault("servers", {})
        for name, legacy in list(mcp.items()):
            if (
                name == "servers"
                or not isinstance(legacy, dict)
                or "type" not in legacy
            ):
                continue
            normalized = dict(legacy)
            if "enabled" in normalized:
                enabled = normalized.pop("enabled")
                normalized.setdefault("disabled", not enabled)
            if "env" in normalized:
                env = normalized.pop("env")
                normalized.setdefault("environment", env)
            servers.setdefault(name, normalized)
            del mcp[name]
        merge_servers(servers, converted)
        if not mcp_only:
            # Use the curated set natively, plus prompt-time routing for the
            # full index, avoiding thousands of skill descriptions per call.
            old = doc.get("skills", [])
            if isinstance(old, list):
                doc["skills"] = [p for p in old if not managed_integration_path(p, "skills", "by-category")]
            instructions = doc.setdefault("instructions", [])
            doc["instructions"] = [p for p in instructions if not managed_integration_path(
                p, "prompts", "opencode-system-prompt.txt")]
            instruction = str(config_dir / "AGENTS.md")
            if instruction not in doc["instructions"]:
                doc["instructions"].append(instruction)
            plugin = str(UI / "opencode-plugin")
            plugins = [p for p in doc.get("plugins", []) if not managed_integration_path(p, "opencode-plugin")]
            doc["plugins"] = [*plugins, plugin]
            # OpenCode 2 drops Claude-style command hooks from its config; the
            # plugin above is the lifecycle channel. Remove handlers that
            # earlier AE versions wrote, keep the user's own.
            merge_hooks(doc, agent, install=False)
        write_json(path, doc)
        # Audit AE-15: JSON serialization drops user comments from JSONC
        # files. The untouched original is preserved in the 0600 backup;
        # say so instead of letting the change pass silently.
        if path.suffix == ".jsonc" and (
            "//" in original_text or "/*" in original_text
        ):
            print(
                f"[native] opencode: note - comments in {path.name} were "
                "dropped by the JSON rewrite; the original file was backed "
                "up next to it (mode 0600)",
                file=sys.stderr,
            )
    elif agent in EXTRA_COMMANDS:
        install_hermes(block, merge_servers, mcp_only=mcp_only, profiles=profiles)
    else:
        raise ValueError(f"unsupported agent: {agent}")
    print(
        f"[native] {agent}: configured"
        + (" MCP" if mcp_only else " hooks/plugin + MCP")
    )


def main() -> None:
    """Native installation entry point; errors fail setup instead of claiming success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent", choices=["claude-code", "codex", "opencode", *EXTRA_COMMANDS, "all"], default="all"
    )
    parser.add_argument("--mcp-only", action="store_true")
    parser.add_argument("--profile", action="append", help="select a Hermes profile (repeatable; saved locally)")
    parser.add_argument("--select-agents", help="persist an explicit comma-separated native-agent selection")
    parser.add_argument("--print-selection", action="store_true", help="print the saved selection without installing")
    args = parser.parse_args()
    selection = read_json(host_selection_path())
    selected = selection.get("agents")
    if args.select_agents is not None:
        selected = list(dict.fromkeys(args.select_agents.split(",")))
    if selected is not None and (not isinstance(selected, list) or not selected
                                or any(agent not in NATIVE_AGENTS for agent in selected)):
        parser.error("selection must contain supported native agent names")
    if args.print_selection:
        print(",".join(selected or []))
        return
    agents = (
        ["claude-code", "codex", "opencode", *[
            agent for agent, command in EXTRA_COMMANDS.items() if shutil.which(command)
        ]] if args.agent == "all" else [args.agent]
    )
    for agent in agents:
        if args.agent == "all" and selected is not None and agent not in selected:
            continue
        install(agent, mcp_only=args.mcp_only, profiles=args.profile if agent == "hermes" else None)
    if args.select_agents is not None:
        selection = read_json(host_selection_path())
        selection["agents"] = selected
        write_json(host_selection_path(), selection)


if __name__ == "__main__":
    main()
