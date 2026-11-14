"""Coordinate native MCP discovery with the coding CLI's prompt hook.

Markers contain process IDs only, never tool data or credentials. Other hosts
retain their own native MCP lifecycle; OpenCode uses its public readiness API.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
import tempfile
import time


def marker_root() -> Path:
    """Private per-user process coordination directory."""
    return (
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        / "agentenhancements/mcp-ready"
    )


def mark_ready() -> Path:
    """Called once tools/list has been served to the native parent client."""
    directory = marker_root()
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    path = directory / f"{os.getppid()}-{os.getpid()}.ready"
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".ready-")
    with os.fdopen(descriptor, "w") as stream:
        stream.write(str(os.getpid()))
    os.replace(temporary, path)
    return path


def client_parent(agent: str) -> int | None:
    """Identify the CLI through shell-hook ancestry on the installed Linux host."""
    parent = os.getppid()
    for _ in range(3):
        try:
            process = Path("/proc") / str(parent)
            name = (process / "comm").read_text().strip().lower()
            expected = "claude" if agent == "claude-code" else "codex"
            if expected in name:
                return parent
            stat = (process / "stat").read_text().rsplit(")", 1)[1].split()
            parent = int(stat[1])
            if parent <= 1:
                break
        except (OSError, ValueError, IndexError):
            break
    return None


def wait_for_mcp(agent: str, timeout: float = 10) -> None:
    """Let the first prompt capture already-listed tools; never require a command."""
    parent = client_parent(agent)
    if parent is None:
        return
    # Personal removal/disablement must not add a wait to every prompt.
    try:
        if agent == "claude-code":
            override = os.environ.get("CLAUDE_CONFIG_DIR")
            path = (
                Path(override) / ".claude.json"
                if override
                else Path.home() / ".claude.json"
            )
            entry = (
                json.loads(path.read_text())
                .get("mcpServers", {})
                .get("agent-enhancements", {})
            )
        else:
            import tomllib

            path = (
                Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
                / "config.toml"
            )
            entry = (
                tomllib.loads(path.read_text())
                .get("mcp_servers", {})
                .get("agent-enhancements", {})
            )
        if not entry.get("enabled", True) or entry.get("disabled", False):
            return
        if "mcp-servers/gateway.py" not in json.dumps(entry.get("args", [])):
            return
    except (OSError, ValueError, TypeError, ImportError):
        return
    directory = marker_root()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for marker in directory.glob(f"{parent}-*.ready"):
            try:
                child = int(marker.read_text())
                os.kill(child, 0)
                # Allow the parent's pending tools/list promise to settle.
                time.sleep(0.1)
                return
            except (OSError, ValueError):
                continue
        time.sleep(0.1)
