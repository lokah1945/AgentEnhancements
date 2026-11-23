#!/usr/bin/env python3
"""Regression tests: the Hermes and OpenCode per-session caches evict LRU.

Audit 2026-11-23: both caches evicted by creation order, so a long-lived
host dropped a still-active session. Hermes then wrote that session's
PostToolUse record to the profile-wide scope (shared by every sender of the
profile); OpenCode re-ran SessionStart and lost the session's flush state.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

UI_DIR = Path(__file__).resolve().parents[1]


def load_hermes(name: str):
    """Load a fresh copy of the Hermes plugin module."""
    spec = importlib.util.spec_from_file_location(name, UI_DIR / "hermes-plugin/__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HermesScopeCacheTests(unittest.TestCase):
    """The Hermes sender-scope cache keeps active sessions and never widens."""

    def setUp(self) -> None:
        self.module = load_hermes("ae_hermes_cache_regression")
        self.callbacks: dict = {}
        callbacks = self.callbacks

        class Context:
            profile_name = "p"

            def register_hook(self, name, callback):
                callbacks[name] = callback

        self.module.register(Context())

    def test_recently_used_session_survives_eviction(self) -> None:
        with patch.object(self.module, "runtime", return_value="") as runtime:
            for index in range(1000):
                self.callbacks["pre_llm_call"](f"s-{index}", "hi", False,
                                               platform="telegram", sender_id=str(index))
            # s-0 is active again, then one more session arrives.
            self.callbacks["pre_llm_call"]("s-0", "again", False, platform="telegram", sender_id="0")
            self.callbacks["pre_llm_call"]("s-new", "hi", False, platform="telegram", sender_id="new")
            runtime.reset_mock()
            self.callbacks["post_tool_call"]("terminal", "s-0")
            runtime.assert_called_once_with("PostToolUse", "s-0", tool_name="terminal",
                                            memory_scope="hermes-profile:p|telegram:0")
            # The least recently used session (s-1) is the one evicted.
            runtime.reset_mock()
            self.callbacks["post_tool_call"]("terminal", "s-1")
            runtime.assert_not_called()

    def test_unknown_session_never_falls_back_to_profile_scope(self) -> None:
        with patch.object(self.module, "runtime", return_value="") as runtime:
            self.callbacks["post_tool_call"]("terminal", "never-seen")
            self.callbacks["post_llm_call"]("never-seen", assistant_response="private")
            runtime.assert_not_called()
            # With the platform known, the fallback is per-session, not shared.
            self.callbacks["post_llm_call"]("never-seen", assistant_response="private",
                                            platform="telegram")
            runtime.assert_called_once()
            self.assertEqual(runtime.call_args.kwargs["memory_scope"],
                             "hermes-profile:p|telegram:session:never-seen")


OPENCODE_DRIVER = r"""
import { readFile } from "node:fs/promises"
const [plugin, log] = process.argv.slice(2)
const { default: definition } = await import(plugin)
const hooks = new Map()
await definition.setup({
  location: { directory: process.cwd() },
  mcp: { list: async () => [{ name: "agent-enhancements", status: { status: "connected" } }] },
  tool: { reload: async () => {} },
  session: { hook: async (name, callback) => { hooks.set(name, callback); return { dispose: async () => {} } },
    context: async () => [] },
})
const prompt = (id) => hooks.get("prompt")({ sessionID: id, prompt: { text: "hi" } })
for (let index = 0; index < 100; index++) await prompt("s-" + index)
await prompt("s-0")      // s-0 is active again
await prompt("s-new")    // forces one eviction
await prompt("s-0")      // must not be treated as a new session
await prompt("s-1")      // the least recently used one was evicted
const starts = {}
for (const line of (await readFile(log, "utf8")).split("\n").filter(Boolean)) {
  const event = JSON.parse(line)
  if (event.hook_event_name === "SessionStart") starts[event.session_id] = (starts[event.session_id] || 0) + 1
}
console.log(JSON.stringify(starts))
"""

FAKE_PYTHON = """#!/bin/sh
cat >> "$AE_TEST_EVENT_LOG"
echo >> "$AE_TEST_EVENT_LOG"
if [ "$3" = "--bridge" ]; then echo '{"context":"","fallback":""}'; fi
"""


@unittest.skipUnless(shutil.which("node"), "node is required for the OpenCode plugin")
class OpenCodeNotesCacheTests(unittest.TestCase):
    """The OpenCode notes Map keeps active sessions (LRU order)."""

    def test_active_session_is_not_restarted_after_eviction(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ae-opencode-lru-") as directory:
            root = Path(directory)
            fake = root / "state/runtime/venv/bin/python"
            fake.parent.mkdir(parents=True)
            fake.write_text(FAKE_PYTHON)
            fake.chmod(0o755)
            log = root / "events.log"
            log.write_text("")
            driver = root / "driver.mjs"
            driver.write_text(OPENCODE_DRIVER)
            env = {**os.environ, "AGENT_ENHANCEMENTS_STATE_DIR": str(root / "state"),
                   "AE_TEST_EVENT_LOG": str(log), "HOME": str(root)}
            result = subprocess.run(
                ["node", str(driver), (UI_DIR / "opencode-plugin/index.js").as_uri(), str(log)],
                cwd=root, env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            starts = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertEqual(starts.get("s-0"), 1)
            self.assertEqual(starts.get("s-1"), 2)


if __name__ == "__main__":
    unittest.main()
