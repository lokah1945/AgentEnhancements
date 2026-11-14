#!/usr/bin/env python3
"""Merge enhancements into the configuration actually read by each CLI.

Run with the isolated interpreter prepared by setup-mcp.sh. No credentials,
provider choices, tool approvals, user hooks, or user MCP servers are replaced.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile

import json5
import tomlkit

UI = Path(__file__).resolve().parent.parent
ROOT = UI.parent
EVENTS = ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop")


def write(path: Path, content: str) -> None:
    """Back up changes and replace atomically with private file permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text() == content:
            return
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        backup = path.with_name(path.name + ".backup." + stamp)
        shutil.copy2(path, backup)
        backup.chmod(0o600)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: Path) -> dict:
    """Read JSON or JSONC, rejecting malformed/non-object user configuration."""
    doc = json5.loads(path.read_text()) if path.exists() else {}
    if not isinstance(doc, dict):
        raise ValueError(f"configuration must be an object: {path}")
    return doc


def write_json(path: Path, doc: dict) -> None:
    """Serialize configuration; the original, including JSONC comments, is backed up."""
    write(path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def own_hook(handler: dict) -> bool:
    """Recognize only hooks previously installed by AgentEnhancements."""
    command = str(handler.get("command", ""))
    return "unified-integration/" in command and any(
        x in command for x in ["scripts/runtime.py", "-memory-hook.py"]
    )


def merge_hooks(doc: dict, agent: str) -> None:
    """Replace our handlers, preserving other events and matcher groups."""
    hooks = doc.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("hooks must be an object")
    for event, groups in list(hooks.items()):
        retained = []
        for group in groups:
            handlers = [h for h in group.get("hooks", []) if not own_hook(h)]
            if handlers:
                retained.append({**group, "hooks": handlers})
        hooks[event] = retained
    command = shlex.join([sys.executable, str(UI / "scripts/runtime.py"), agent])
    if os.environ.get("AGENT_MEMORY_ROOT"):
        command = (
            "env "
            + shlex.quote("AGENT_MEMORY_ROOT=" + os.environ["AGENT_MEMORY_ROOT"])
            + " "
            + command
        )
    for event in EVENTS:
        hooks.setdefault(event, []).append(
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": command,
                        "timeout": 10,
                    }
                ]
            }
        )


def mcp_block() -> dict:
    """Render the canonical MCP template with the isolated Python interpreter."""
    template = json.loads((UI / "mcp-servers/mcp.json.example").read_text())
    return {
        name: {
            **cfg,
            "command": sys.executable,
            "args": [
                arg.replace("PLACEHOLDER_REPO_ROOT", str(ROOT)) for arg in cfg["args"]
            ],
        }
        for name, cfg in template["mcpServers"].items()
    }


def merge_servers(existing: dict, block: dict) -> None:
    """Refresh managed servers; keep name collisions belonging to the user."""
    for name, cfg in block.items():
        old = existing.get(name)
        if old is not None and old != cfg:
            old_args = json.dumps(old.get("args", old.get("command", [])))
            if f"mcp-servers/{name}/server.py" not in old_args:
                print(f"[native] preserving user server: {name}", file=sys.stderr)
                continue
        existing[name] = cfg


def install(agent: str, *, mcp_only: bool = False) -> None:
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
        path = Path(str(config_dir) + ".json")
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
        config_dir = (
            Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "opencode"
        )
        # Edit the existing JSONC file if present: a sibling JSON file can
        # otherwise be shadowed by a user's higher-precedence JSONC config.
        path = config_dir / "opencode.jsonc"
        if not path.exists():
            path = config_dir / "opencode.json"
        doc = read_json(path)
        doc.setdefault("$schema", "https://opencode.ai/config.json")
        converted = {
            name: {
                "type": "local",
                "command": [cfg["command"], *cfg["args"]],
                "enabled": True,
            }
            for name, cfg in block.items()
        }
        merge_servers(doc.setdefault("mcp", {}), converted)
        if not mcp_only:
            # Use the curated set natively, plus prompt-time routing for the
            # full index, avoiding thousands of skill descriptions per call.
            old = doc.get("skills", [])
            managed = str(UI / "skills/by-category")
            if isinstance(old, list):
                doc["skills"] = [p for p in old if p != managed]
            instructions = doc.setdefault("instructions", [])
            prompt = str(UI / "prompts/opencode-system-prompt.txt")
            doc["instructions"] = [p for p in instructions if p != prompt]
            instruction = str(config_dir / "AGENTS.md")
            if instruction not in doc["instructions"]:
                doc["instructions"].append(instruction)
            plugin = str(UI / "opencode-plugin")
            plugins = doc.setdefault("plugins", [])
            if plugin not in plugins:
                plugins.append(plugin)
        write_json(path, doc)
    print(
        f"[native] {agent}: configured"
        + (" MCP" if mcp_only else " hooks/plugin + MCP")
    )


def main() -> None:
    """Native installation entry point; errors fail setup instead of claiming success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent", choices=["claude-code", "codex", "opencode", "all"], default="all"
    )
    parser.add_argument("--mcp-only", action="store_true")
    args = parser.parse_args()
    agents = (
        ["claude-code", "codex", "opencode"] if args.agent == "all" else [args.agent]
    )
    for agent in agents:
        install(agent, mcp_only=args.mcp_only)


if __name__ == "__main__":
    main()
