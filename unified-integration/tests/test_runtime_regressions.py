"""Regression tests for unified-integration/scripts/runtime.py.

- AE_MAX_SKILL_CARDS: a malformed or non-positive value falls back to the
  default card count instead of raising (which used to drop every
  prompt-time card behind a "hook skipped: ValueError" line).
- main() input guards: oversized stdin and non-object JSON are skipped
  advisorily, print nothing on stdout and record no memory.
- OpenCode --bridge envelope: a Mode 2 preflight package carries the
  legacy Mode 0 render as its fallback, not a copy of the package.
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, REPO_DIR, load_module, run

# Base class and TLS fixture only; importing the module object (not its
# TestCase subclasses) keeps those tests from being collected twice here.
import test_adaptive_preflight as preflight_tests

SCRIPTS = UI_DIR / "scripts"
RUNTIME = SCRIPTS / "runtime.py"
PROMPT = preflight_tests.PROMPT


class IsolatedRuntimeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.env = {
            "AGENT_ENHANCEMENTS_STATE_DIR": str(root / "ae-state"),
            "AGENT_ENHANCEMENTS_API_FILE": str(root / "ui.api.json"),
            "AGENT_MEMORY_ROOT": str(root / "memory"),
            "HOME": str(root / "home"),
            "XDG_CONFIG_HOME": str(root / "home" / ".config"),
        }
        self.event = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "runtime-regression",
            "cwd": str(REPO_DIR),
            "prompt": PROMPT,
        }

    def hook(self, stdin, extra=None, *flags):
        env = dict(self.env)
        env.update(extra or {})
        return run([sys.executable, str(RUNTIME), "codex", *flags],
                   env=env, input_text=stdin)

    def memory_rows(self):
        database = Path(self.env["AGENT_MEMORY_ROOT"]) / "memory.db"
        if not database.exists():
            return []
        with sqlite3.connect(database) as conn:
            return conn.execute(
                "SELECT key FROM memories WHERE key LIKE 'session:%'"
            ).fetchall()


class SkillCardLimitTests(IsolatedRuntimeCase):
    def setUp(self):
        super().setUp()
        self.runtime = load_module("runtime_card_limit_test", RUNTIME)

    def limit(self, value):
        with patch.dict(os.environ, {"AE_MAX_SKILL_CARDS": value}):
            return self.runtime.skill_card_limit()

    def test_limit_parsing(self):
        with patch.dict(os.environ):
            os.environ.pop("AE_MAX_SKILL_CARDS", None)
            self.assertEqual(self.runtime.skill_card_limit(), 8)
        self.assertEqual(self.limit("3"), 3)
        self.assertEqual(self.limit(" 12 "), 12)
        for bad in ("abc", "", "2.5", "0", "-1"):
            self.assertEqual(self.limit(bad), 8, bad)
        self.assertEqual(self.limit("100000"), self.runtime.MAX_SKILL_CARDS_LIMIT)

    def test_invalid_env_still_renders_default_cards(self):
        payload = json.dumps(self.event)
        rc, default_out, err = self.hook(payload, None, "--text")
        self.assertEqual(rc, 0, err)
        self.assertIn("skill candidates", default_out)
        for bad in ("abc", "0", "-1"):
            rc, out, err = self.hook(payload, {"AE_MAX_SKILL_CARDS": bad}, "--text")
            self.assertEqual(rc, 0, err)
            self.assertNotIn("hook skipped", err, bad)
            self.assertEqual(out, default_out, bad)


class HookInputGuardTests(IsolatedRuntimeCase):
    def test_oversized_and_non_object_input_is_skipped(self):
        oversized = ('{"hook_event_name":"UserPromptSubmit","prompt":"'
                     + "a" * 2_000_001 + '"}')
        for stdin in (oversized, "[]", '"str"'):
            rc, out, err = self.hook(stdin)
            label = stdin[:20]
            self.assertEqual(rc, 0, label)
            self.assertEqual(out, "", label)
            self.assertIn("hook skipped: ValueError", err, label)
            self.assertEqual(self.memory_rows(), [], label)


class BridgeFallbackTests(preflight_tests.PreflightTestCase):
    def setUp(self):
        super().setUp()
        self.fixture = None
        self.runtime = load_module("runtime_bridge_test", RUNTIME)
        self.event = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "bridge-session",
            "cwd": str(REPO_DIR),
            "prompt": PROMPT,
        }

    def tearDown(self):
        if self.fixture:
            self.fixture.stop()
        super().tearDown()

    def test_bridge_envelope_carries_legacy_fallback(self):
        self.fixture = preflight_tests.SelectorFixture([
            preflight_tests.SelectorFixture.selection("selected", items=[
                {"id": "skill:postgresql-optimization", "reason": "planner"}])])
        self.write_model({"mode": 2,
                          "endpoint": self.fixture.endpoint,
                          "sdk": "openai",
                          "model": "fixture/selector"})
        env = dict(self.env)
        env.update({"SSL_CERT_FILE": str(self.fixture.ca),
                    "AE_PREFLIGHT_DEADLINE_MS": "8000"})
        rc, out, err = run([sys.executable, str(RUNTIME), "opencode", "--bridge"],
                           env=env, input_text=json.dumps(self.event))
        self.assertEqual(rc, 0, err)
        envelope = json.loads(out)
        self.assertTrue(
            envelope["context"].startswith("AgentEnhancements preflight"))
        self.assertIn("skill:postgresql-optimization", envelope["context"])
        legacy = self.runtime.skill_context("opencode", PROMPT)
        self.assertTrue(legacy)
        self.assertEqual(envelope["fallback"], legacy)
        self.assertNotEqual(envelope["fallback"], envelope["context"])
        self.assertEqual(len(self.fixture.requests), 1)
        tasks = [r for r in self.memory_rows() if r[0].endswith(":task")]
        self.assertEqual(len(tasks), 1)


if __name__ == "__main__":
    unittest.main()
