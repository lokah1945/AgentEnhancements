"""Tests for the memory hooks (unified-integration/memory/hooks/).

Regression coverage:
- F-01: bash hooks must be thin wrappers delegating to the Python hook;
  no SQL may be interpolated in bash (CONTRACT R101).
- F-10: hook CLI argument mapping (save <key> <value> <type>).
"""
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, REPO_DIR, run

AGENTS = ["claude-code", "codex", "opencode", "cursor", "gemini-cli", "windsurf", "copilot", "kiro"]
HOOKS = UI_DIR / "memory" / "hooks"


class HookPolicyTests(unittest.TestCase):
    def test_every_agent_has_python_hook(self):
        for agent in AGENTS:
            self.assertTrue((HOOKS / f"{agent}-memory-hook.py").exists(),
                            f"missing python hook for {agent}")

    def test_bash_hooks_contain_no_sql(self):
        """R101: parameterized queries only - no sqlite3 in bash hooks."""
        for sh in sorted(HOOKS.glob("*.sh")):
            content = sh.read_text()
            self.assertNotIn("sqlite3", content,
                             f"{sh.name} contains SQL in bash (R101 violation)")
            self.assertIn("memory-hook.py", content,
                          f"{sh.name} is not a delegating wrapper")

    def test_python_hooks_use_parameterized_queries(self):
        for py in sorted(HOOKS.glob("*.py")):
            content = py.read_text()
            self.assertIn("conn.execute(", content)
            # no f-string or % formatting feeding execute()
            self.assertNotIn("execute(f\"", content)
            self.assertNotIn("execute(\"%", content)


class HookCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _hook(self, agent):
        return str(HOOKS / f"{agent}-memory-hook.py")

    def test_save_load_roundtrip(self):
        rc, out, err = run(
            [sys.executable, self._hook("claude-code"), "save", "k1", "v1", "session_context", "proj"],
            env={"AGENT_MEMORY_ROOT": self.tmp.name},
        )
        self.assertEqual(rc, 0, err)
        rc, out, err = run(
            [sys.executable, self._hook("claude-code"), "load", "k1", "session_context", "proj"],
            env={"AGENT_MEMORY_ROOT": self.tmp.name},
        )
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.strip(), "v1")

    def test_save_with_sql_payload_is_stored_verbatim(self):
        """A quote-bearing payload must be stored as data, never executed."""
        payload = "x', 'injected_type', 'k', 'pwned') -- "
        rc, _, err = run(
            [sys.executable, self._hook("codex"), "save", "k2", payload, "session_context", "proj"],
            env={"AGENT_MEMORY_ROOT": self.tmp.name},
        )
        self.assertEqual(rc, 0, err)
        rc, out, err = run(
            [sys.executable, self._hook("codex"), "load", "k2", "session_context", "proj"],
            env={"AGENT_MEMORY_ROOT": self.tmp.name},
        )
        self.assertEqual(out.rstrip("\n"), payload)

    def test_load_missing_exits_nonzero(self):
        rc, out, err = run(
            [sys.executable, self._hook("kiro"), "load", "nope"],
            env={"AGENT_MEMORY_ROOT": self.tmp.name},
        )
        self.assertEqual(rc, 1)

    def test_bash_wrapper_delegates_to_python(self):
        rc, out, err = run(
            ["bash", str(HOOKS / "kiro-memory-hook.sh"), "save", "k3", "v3", "session_context", "proj"],
            env={"AGENT_MEMORY_ROOT": self.tmp.name},
        )
        self.assertEqual(rc, 0, err)
        rc, out, err = run(
            ["bash", str(HOOKS / "kiro-memory-hook.sh"), "load", "k3", "session_context", "proj"],
            env={"AGENT_MEMORY_ROOT": self.tmp.name},
        )
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.strip(), "v3")

    def test_cleanup_command(self):
        rc, out, err = run(
            [sys.executable, self._hook("windsurf"), "cleanup"],
            env={"AGENT_MEMORY_ROOT": self.tmp.name},
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("Cleaned up", out)


if __name__ == "__main__":
    unittest.main()
