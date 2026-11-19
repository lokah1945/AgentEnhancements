"""Shared helpers for the unified-integration test suite."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = UI_DIR.parent


def load_module(name, path, env=None):
    """Import a module from a file path, optionally with env vars set at
    import time (restored afterwards). Returns a FRESH module each call.

    The module is registered in sys.modules while it executes: the
    dataclass machinery (and `from __future__ import annotations`)
    resolves the owning module's namespace through sys.modules, so an
    unregistered exec breaks any module that defines a dataclass."""
    saved = {}
    if env:
        for k, v in env.items():
            saved[k] = os.environ.get(k)
            os.environ[k] = v
    try:
        spec = importlib.util.spec_from_file_location(name, str(path))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        try:
            spec.loader.exec_module(mod)
        except BaseException:
            sys.modules.pop(name, None)
            raise
        return mod
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def run(cmd, env=None, cwd=None, input_text=None):
    """Run a subprocess, returning (returncode, stdout, stderr)."""
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=merged_env,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr
