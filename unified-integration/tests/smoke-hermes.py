#!/usr/bin/env python3
"""Run real Hermes profiles against a localhost model, with isolated state."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

import yaml

UI = Path(__file__).resolve().parent.parent


def main() -> int:
    """Verify native MCP discovery and automatic task/summary hooks."""
    if not shutil.which("hermes"):
        print("Hermes CLI is not installed", file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("ae_model_fixture", UI / "tests/smoke-native-clis.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    server = ThreadingHTTPServer(("127.0.0.1", 0), fixture.Mock)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix="ae-hermes-smoke-") as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            project = root / "project"
            project.mkdir()
            api = root / "ui.api.json"
            api.write_text((UI / "config/ui.api.example.json").read_text())
            env = {**os.environ, "HOME": str(home),
                   "HERMES_HOME": str(home / ".hermes"),
                   "XDG_DATA_HOME": str(home / ".local/share"),
                   "AGENT_MEMORY_ROOT": str(root / "memory"),
                   "AGENT_ENHANCEMENTS_API_FILE": str(api),
                   "HTTP_PROXY": "http://127.0.0.1:1", "HTTPS_PROXY": "http://127.0.0.1:1",
                   "ALL_PROXY": "http://127.0.0.1:1", "NO_PROXY": "127.0.0.1,localhost",
                   "no_proxy": "127.0.0.1,localhost"}
            for name in ("ilma", "master-chief"):
                folder = home / ".hermes/profiles" / name
                folder.mkdir(parents=True)
                config = {"model": {"default": "fixture", "provider": "custom",
                          "base_url": f"http://127.0.0.1:{server.server_port}/v1"},
                          "agent": {"max_turns": 2}, "display": {"interface": "cli"}}
                (folder / "config.yaml").write_text(yaml.safe_dump(config))
            subprocess.run([sys.executable, str(UI / "scripts/native-integration.py"),
                            "--agent", "hermes", "--profile", "ilma", "--profile", "master-chief"],
                           env=env, check=True, capture_output=True, timeout=20)
            for name in ("ilma", "master-chief"):
                result = subprocess.run(
                    ["hermes", "-p", name, "chat", "-q", "security audit fixture; respond briefly",
                     "--quiet", "--max-turns", "2"], env=env, cwd=project,
                    capture_output=True, text=True, timeout=65)
                passed = result.returncode == 0 and "AGENT_ENHANCEMENTS_FIXTURE_OK" in result.stdout
                print(f"hermes/{name}: exit={result.returncode} fixture={passed}", flush=True)
                if not passed:
                    # Only isolated fixture diagnostics, never production auth.
                    print(result.stderr[-3000:], file=sys.stderr)
                    print(result.stdout[-1500:], file=sys.stderr)
                    return 1
            db = root / "memory/memory.db"
            with sqlite3.connect(db) as conn:
                summaries = conn.execute(
                    "SELECT count(*) FROM memories WHERE agent=? AND key LIKE ? AND value LIKE ?",
                    ("hermes", "%:summary", "%AGENT_ENHANCEMENTS_FIXTURE_OK%"),
                ).fetchone()[0]
                tasks = conn.execute("SELECT count(*) FROM memories WHERE agent=? AND key LIKE ?",
                                     ("hermes", "%:task")).fetchone()[0]
            names = set().union(*fixture.tools_seen.values()) if fixture.tools_seen else set()
            discovered = any("embeddings_embed" in name for name in names)
            print(json.dumps({"summaries": summaries, "tasks": tasks,
                              "native_mcp_discovered": discovered}))
            return 0 if summaries == 2 and tasks == 2 and discovered else 1
    finally:
        server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
