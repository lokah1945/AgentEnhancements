"""Tests for unified-integration/scripts/memory.py (AgentMemory).

Covers save/load/list/delete/cleanup round-trips against a temp SQLite DB.
"""
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module


class AgentMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mod = load_module(
            "memory_test",
            UI_DIR / "scripts" / "memory.py",
            env={"AGENT_MEMORY_ROOT": self.tmp.name},
        )
        self.mem = self.mod.AgentMemory("claude-code", project="testproj")

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        self.mem.save("key1", "value1", "session_context")
        self.assertEqual(self.mem.load("key1", "session_context"), "value1")

    def test_load_missing_returns_none(self):
        self.assertIsNone(self.mem.load("missing", "session_context"))

    def test_save_with_quotes_is_safe(self):
        """Values containing single quotes must round-trip intact
        (regression for the SQL string interpolation in old bash hooks)."""
        tricky = "value with 'single quote' and \"double\" and ; -- SQL-ish"
        self.mem.save("tricky", tricky)
        self.assertEqual(self.mem.load("tricky"), tricky)

    def test_delete(self):
        self.mem.save("k", "v")
        self.assertTrue(self.mem.delete("k"))
        self.assertIsNone(self.mem.load("k"))
        self.assertFalse(self.mem.delete("k"))

    def test_list(self):
        self.mem.save("k1", "v1")
        self.mem.save("k2", "v2", "project_context")
        items = self.mem.list()
        self.assertEqual(len(items), 2)
        only_project = self.mem.list("project_context")
        self.assertEqual(len(only_project), 1)
        self.assertEqual(only_project[0]["key"], "k2")

    def test_cleanup_expired_removes_ttl_memories(self):
        self.mem.save("shortlived", "v", ttl_days=-1)
        # ttl_days=-1 -> expiry timestamp is in the past
        removed = self.mem.cleanup_expired()
        self.assertGreaterEqual(removed, 1)
        self.assertIsNone(self.mem.load("shortlived"))

    def test_cli_load_missing_exits_nonzero(self):
        """CLI contract: loading a missing memory exits 1."""
        import os
        import subprocess
        env = dict(os.environ)
        env["AGENT_MEMORY_ROOT"] = self.tmp.name
        proc = subprocess.run(
            [sys.executable, str(UI_DIR / "scripts" / "memory.py"), "claude-code", "load", "nope"],
            capture_output=True, text=True, env=env, timeout=60,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Memory not found", proc.stdout)


if __name__ == "__main__":
    unittest.main()
