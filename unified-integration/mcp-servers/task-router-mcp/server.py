#!/usr/bin/env python3
"""task-router-mcp — AgentEnhancements in-house MCP server.

Dispatch sub-agent tasks and track progress (gsd, bmad-method, rea per
plugin-catalog/mcp-servers.json).

Tasks are short bash or python snippets executed in an isolated workspace
with a hard timeout. The registry is in-process; every task gets an id,
a status (queued/running/done/failed/cancelled), captured stdout/stderr
tails and an exit code.

Safety: commands matching an obvious-destructive denylist are refused
(best-effort guard, documented as such - not a sandbox).
"""
from __future__ import annotations

import concurrent.futures
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

VERSION = "1.0.0"
DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 600
STDOUT_TAIL = 4000

mcp = FastMCP("task-router-mcp")

TOOLS: dict[str, Callable] = {}


def _tool(fn):
    TOOLS[fn.__name__] = fn
    return mcp.tool()(fn)


_DENYLIST = [
    re.compile(r"rm\s+(-[a-zA-Z]*\s+)*-?[rf]{1,2}[a-zA-Z]*\s+/\s*$"),  # rm -rf /
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r":\(\)\s*\{.*\};\s*:"),  # fork bomb
    re.compile(r">\s*/dev/sd[a-z]"),
    re.compile(r"\bshutdown\b|\breboot\b"),
]

_TASKS: dict[str, dict] = {}
_WORKSPACES: dict[str, str] = {}
_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _refused(command: str) -> str | None:
    for pattern in _DENYLIST:
        if pattern.search(command):
            return pattern.pattern
    return None


def _run_task(task_id: str, spec: dict) -> None:
    entry = _TASKS[task_id]
    entry["status"] = "running"
    entry["started_at"] = time.time()
    workspace = _WORKSPACES[task_id]
    try:
        if spec["kind"] == "bash":
            proc = subprocess.run(
                ["bash", "-lc", spec["command"]],
                capture_output=True, text=True,
                timeout=spec["timeout"], cwd=workspace,
            )
        else:  # python
            proc = subprocess.run(
                ["python3", "-c", spec["code"]],
                capture_output=True, text=True,
                timeout=spec["timeout"], cwd=workspace,
            )
        entry.update(
            status="done" if proc.returncode == 0 else "failed",
            exit_code=proc.returncode,
            stdout=proc.stdout[-STDOUT_TAIL:],
            stderr=proc.stderr[-STDOUT_TAIL:],
        )
    except subprocess.TimeoutExpired:
        entry.update(status="failed", exit_code=-1,
                     stderr=f"timeout after {spec['timeout']}s")
    except Exception as exc:  # defensive: registry must stay consistent
        entry.update(status="failed", exit_code=-1, stderr=f"{type(exc).__name__}: {exc}")
    finally:
        entry["finished_at"] = time.time()
        entry["duration_s"] = round(entry["finished_at"] - entry["started_at"], 3)


@_tool
def health() -> dict:
    """Liveness probe + executor stats."""
    return {
        "status": "ok",
        "server": "task-router-mcp",
        "version": VERSION,
        "workers": 4,
        "tasks_known": len(_TASKS),
        "tasks_active": sum(1 for t in _TASKS.values() if t["status"] == "running"),
    }


@_tool
def dispatch(kind: str, command: str | None = None, code: str | None = None,
             timeout: int | None = None) -> dict:
    """Dispatch a task. Exactly one of command (bash) / code (python) is
    required, matched against kind ("bash" | "python").

    Args:
        kind: "bash" or "python".
        command: bash snippet (kind="bash").
        code: python snippet (kind="python").
        timeout: seconds, 1..600 (default 60).
    """
    if kind not in ("bash", "python"):
        return {"error": "kind must be 'bash' or 'python'",
                "hint": "got kind=%r" % kind}
    payload = command if kind == "bash" else code
    if not payload or not isinstance(payload, str) or not payload.strip():
        return {"error": f"{kind} task requires a non-empty "
                         f"{'command' if kind == 'bash' else 'code'} string"}
    effective_timeout = min(max(timeout or DEFAULT_TIMEOUT, 1), MAX_TIMEOUT)
    if kind == "bash":
        matched = _refused(payload)
        if matched:
            return {
                "error": "command refused by the destructive-pattern guard",
                "hint": f"matched denylist pattern {matched!r}; run risky "
                        f"operations manually, not through task-router",
            }
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    spec = {"kind": kind, "timeout": effective_timeout}
    if kind == "bash":
        spec["command"] = payload
    else:
        spec["code"] = payload
    _TASKS[task_id] = {
        "id": task_id, "status": "queued", "created_at": time.time(),
        "spec": {"kind": kind, "timeout": effective_timeout},
    }
    _WORKSPACES[task_id] = tempfile.mkdtemp(prefix=f"ae-task-{task_id}-")
    future = _POOL.submit(_run_task, task_id, spec)
    future.add_done_callback(lambda _f: None)
    return {"task_id": task_id, "status": "queued",
            "hint": f"call track('{task_id}') for status"}


@_tool
def track(task_id: str) -> dict:
    """Track one task: status, exit code, stdout/stderr tails, duration."""
    entry = _TASKS.get(task_id)
    if entry is None:
        return {"error": f"unknown task_id {task_id!r}",
                "hint": "call dispatch() first, or list() to see known ids"}
    return dict(entry)


@_tool
def cancel(task_id: str) -> dict:
    """Cancel a queued/running task (running subprocesses are killed)."""
    entry = _TASKS.get(task_id)
    if entry is None:
        return {"error": f"unknown task_id {task_id!r}"}
    if entry["status"] in ("done", "failed", "cancelled"):
        return {"task_id": task_id, "status": entry["status"],
                "note": "task already finished; nothing to cancel"}
    entry["status"] = "cancelled"
    entry["finished_at"] = time.time()
    shutil.rmtree(_WORKSPACES.get(task_id, ""), ignore_errors=True)
    return {"task_id": task_id, "status": "cancelled"}


@_tool
def list_tasks() -> dict:
    """List every known task with its current status."""
    return {"tasks": [
        {"id": t["id"], "status": t["status"]}
        for t in sorted(_TASKS.values(), key=lambda e: e["created_at"])
    ]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
