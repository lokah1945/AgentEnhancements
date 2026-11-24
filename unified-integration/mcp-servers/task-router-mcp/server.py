#!/usr/bin/env python3
"""task-router-mcp — AgentEnhancements in-house MCP server.

Dispatch sub-agent tasks and track progress (gsd, bmad-method, rea per
plugin-catalog/mcp-servers.json).

Tasks are short bash or python snippets executed in an isolated workspace
with a hard timeout. The registry is in-process; every task gets an id,
a status (queued/running/done/failed/cancelled), captured stdout/stderr
tails and an exit code.

Safety: commands matching an obvious-destructive denylist are refused
(best-effort guard, documented as such - not a sandbox). The same guard
applies to python payloads. The gateway keeps this server hidden until the
user opts in via ui.api.json (see docs/SAFETY.md).
"""
from __future__ import annotations

import concurrent.futures
import os
import re
import shutil
import signal
import sys
import threading
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

VERSION = "1.0.0"
DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 600
STDOUT_TAIL = 4000
# Finished task entries kept for track()/list_tasks(); older ones are pruned
# so a long-lived server does not grow its registry without limit.
MAX_FINISHED_TASKS = 500

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
# Python payloads can express the same accidents without a shell: apply the
# shared denylist to the code text (also catches os.system/subprocess shells
# embedding a denylisted command) plus python-specific root-wipe spellings.
_DENYLIST_PYTHON = _DENYLIST + [
    re.compile(r"shutil\.rmtree\(\s*['\"](/|/(?:boot|etc|usr|var|home|root))"),
    re.compile(r"os\.(?:removedirs|unlink)\(\s*['\"]/"),
    # shell-outs embedding a root wipe: os.system("rm -rf /"), subprocess("rm -rf /")
    re.compile(r"rm\s+(-[a-zA-Z]*\s+)*-?[rf]{1,2}[a-zA-Z]*\s+/['\"]"),
]

_TASKS: dict[str, dict] = {}
_WORKSPACES: dict[str, str] = {}
_PROCESSES: dict[str, subprocess.Popen] = {}
_LOCK = threading.RLock()
_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def _refused(command: str, python: bool = False) -> str | None:
    patterns = _DENYLIST_PYTHON if python else _DENYLIST
    for pattern in patterns:
        if pattern.search(command):
            return pattern.pattern
    return None


def _terminate(proc: subprocess.Popen, session_id: int | None = None) -> None:
    """Stop the task's session, including all child processes and background jobs.

    Uses start_new_session=True so the shell is the session leader. Killing by
    session ID terminates the entire session on Linux.
    """
    try:
        if os.name == "posix":
            # Use provided session_id or try to get it from the process.
            # The session ID equals the PID of the session leader (the shell).
            sid = session_id
            if sid is None:
                try:
                    sid = os.getsid(proc.pid)
                except (ProcessLookupError, AttributeError):
                    sid = proc.pid
            # Kill all processes in the session using negative session ID.
            try:
                os.kill(-sid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            # Fallback: also kill the process group in case session kill missed something.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
    except PermissionError:
        # The group/session is already gone or belongs to someone else.
        pass


def _run_task(task_id: str, spec: dict) -> None:
    entry = _TASKS[task_id]
    output = {"stdout": b"", "stderr": b""}
    readers = []
    proc = None

    def drain(stream, key: str) -> None:
        # Drain continually and retain a bounded tail. capture_output=True
        # previously buffered the entire output in RAM before truncating it.
        try:
            # read1 returns whatever is available, so output already produced
            # is kept even if a lingering pipe holder outlives the join below.
            while chunk := stream.read1(4096):
                output[key] = (output[key] + chunk)[-STDOUT_TAIL:]
        finally:
            stream.close()

    try:
        with _LOCK:
            # A queued cancellation must never start executing later.
            if entry["status"] == "cancelled":
                return
            entry.update(status="running", started_at=time.time())
            # Use +m to disable job control (monitor mode) so background processes
            # stay in the same process group as the shell and are killed by _terminate.
            argv = (["bash", "+m", "-c", spec["command"]] if spec["kind"] == "bash"
                    else [sys.executable, "-c", spec["code"]])
            proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    cwd=_WORKSPACES[task_id], start_new_session=(os.name == "posix"))
            # Capture session ID immediately (equals shell PID when start_new_session=True)
            session_id = proc.pid if os.name == "posix" else None
            _PROCESSES[task_id] = proc
        for stream, key in [(proc.stdout, "stdout"), (proc.stderr, "stderr")]:
            reader = threading.Thread(target=drain, args=(stream, key), daemon=True)
            reader.start()
            readers.append(reader)
        timed_out = False
        try:
            proc.wait(timeout=spec["timeout"])
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate(proc, session_id)
            proc.wait()
        if os.name == "posix":
            # The task owns its session (start_new_session): kill background
            # children it left behind so they neither outlive the task nor
            # hold the output pipes open and delay completion.
            _terminate(proc, session_id)
        for reader in readers:
            reader.join(timeout=2)
        with _LOCK:
            entry.update(exit_code=proc.returncode,
                         stdout=output["stdout"].decode("utf-8", errors="replace"),
                         stderr=output["stderr"].decode("utf-8", errors="replace"))
            if timed_out:
                entry.update(exit_code=-1, stderr=f"timeout after {spec['timeout']}s")
            if entry["status"] != "cancelled":
                entry["status"] = "done" if proc.returncode == 0 and not timed_out else "failed"
    except Exception as exc:
        if proc is not None:
            _terminate(proc)
        with _LOCK:
            if entry["status"] != "cancelled":
                entry.update(status="failed", exit_code=-1, stderr=f"{type(exc).__name__}: {exc}")
    finally:
        with _LOCK:
            _PROCESSES.pop(task_id, None)
            entry["finished_at"] = time.time()
            entry["duration_s"] = round(entry["finished_at"] - entry.get("started_at", entry["created_at"]), 3)
            workspace = _WORKSPACES.pop(task_id, "")
        # Every finished task (done, failed or cancelled) releases its workspace.
        if workspace:
            shutil.rmtree(workspace, ignore_errors=True)


def _prune_finished_tasks() -> None:
    """Drop the oldest finished entries beyond MAX_FINISHED_TASKS (hold _LOCK)."""
    finished = [t for t in _TASKS.values()
                if t["status"] in ("done", "failed", "cancelled") and "finished_at" in t
                and t["id"] not in _WORKSPACES]
    excess = len(finished) - MAX_FINISHED_TASKS
    if excess > 0:
        for task in sorted(finished, key=lambda e: e["created_at"])[:excess]:
            _TASKS.pop(task["id"], None)


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
    matched = _refused(payload, python=(kind == "python"))
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
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
    from project_paths import prepare
    workspaces = prepare() / 'cache/tasks'
    workspaces.mkdir(mode=0o700, exist_ok=True)
    workspace = tempfile.mkdtemp(prefix=f"ae-task-{task_id}-", dir=workspaces)
    with _LOCK:
        _prune_finished_tasks()
        _TASKS[task_id] = {
            "id": task_id, "status": "queued", "created_at": time.time(),
            "spec": {"kind": kind, "timeout": effective_timeout},
        }
        _WORKSPACES[task_id] = workspace
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
    with _LOCK:
        entry = _TASKS.get(task_id)
        if entry is None:
            return {"error": f"unknown task_id {task_id!r}"}
        if entry["status"] in ("done", "failed", "cancelled"):
            return {"task_id": task_id, "status": entry["status"],
                    "note": "task already finished; nothing to cancel"}
        entry["status"] = "cancelled"
        entry["finished_at"] = time.time()
        proc = _PROCESSES.get(task_id)
    if proc is not None:
        _terminate(proc)
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
