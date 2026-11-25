"""Memory API and CLI tests against isolated SQLite databases."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module, run


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
        self.mem.save("k2", "v2", "project_context", metadata={"source": "fixture"})
        items = self.mem.list()
        self.assertEqual(len(items), 2)
        only_project = self.mem.list("project_context")
        self.assertEqual(len(only_project), 1)
        self.assertEqual(only_project[0]["key"], "k2")
        self.assertEqual(only_project[0]["metadata"], {"source": "fixture"})

    def test_cleanup_expired_removes_ttl_memories(self):
        self.mem.save("shortlived", "v", ttl_days=-1)
        # ttl_days=-1 -> expiry timestamp is in the past
        removed = self.mem.cleanup_expired()
        self.assertGreaterEqual(removed, 1)
        self.assertIsNone(self.mem.load("shortlived"))


class MemoryCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.memory_root = self.root / "memory"

    def run_cli(self, *args, expected_status=0, cwd=None):
        status, stdout, stderr = run(
            [sys.executable, str(UI_DIR / "scripts" / "memory.py"), *args],
            env={"AGENT_MEMORY_ROOT": str(self.memory_root)},
            cwd=cwd or self.root,
        )
        self.assertEqual(status, expected_status, f"{args!r}\n{stdout}{stderr}")
        return stdout, stderr

    def test_save_and_load_default_type(self):
        self.run_cli("claude-code", "save", "decision", "reuse existing fixtures")
        stdout, _ = self.run_cli("claude-code", "load", "decision")
        self.assertEqual(stdout.strip(), "reuse existing fixtures")

    def test_load_is_scoped_to_agent_and_working_directory(self):
        self.run_cli("claude-code", "save", "decision", "reuse existing fixtures")
        other_project = self.root / "other checkout"
        other_project.mkdir()
        for agent, project in (("claude-code", other_project), ("codex", self.root)):
            with self.subTest(agent=agent, project=project):
                stdout, _ = self.run_cli(
                    agent, "load", "decision", cwd=project, expected_status=1,
                )
                self.assertIn("Memory not found: decision", stdout)

    def test_list_enforces_type_filter_and_limit(self):
        long_value = "x" * 210
        self.run_cli("claude-code", "save", "session-note", "draft")
        self.run_cli("claude-code", "save", "design", long_value, "project_context")
        self.run_cli("claude-code", "save", "review", "approved", "project_context")

        stdout, _ = self.run_cli("claude-code", "list")
        self.assertIn("[session_context] session-note: draft", stdout)
        self.assertIn(f"[project_context] design: {'x' * 200}... (updated:", stdout)

        stdout, _ = self.run_cli("claude-code", "list", "project_context")
        filtered = stdout.splitlines()
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(line.startswith("[project_context] ") for line in filtered))

        stdout, _ = self.run_cli("claude-code", "list", "project_context", "1")
        limited = stdout.splitlines()
        self.assertEqual(len(limited), 1)
        self.assertIn(limited[0], filtered)

    def test_delete_removes_only_the_requested_type(self):
        self.run_cli("claude-code", "save", "note", "session value")
        self.run_cli("claude-code", "save", "note", "project value", "project_context")
        stdout, _ = self.run_cli("claude-code", "delete", "note", "project_context")
        self.assertIn("Deleted: note", stdout)

        self.run_cli("claude-code", "load", "note", "project_context", expected_status=1)
        stdout, _ = self.run_cli("claude-code", "load", "note")
        self.assertEqual(stdout.strip(), "session value")

        stdout, _ = self.run_cli("claude-code", "delete", "note", "project_context")
        self.assertIn("Not found: note", stdout)

    def test_cleanup_removes_expired_memories_and_keeps_active_ones(self):
        self.run_cli("claude-code", "save", "expired", "stale", "project_context", "-1")
        self.run_cli("claude-code", "save", "active", "current", "project_context", "1")
        self.run_cli("claude-code", "load", "expired", "project_context", expected_status=1)

        stdout, _ = self.run_cli("claude-code", "cleanup")
        self.assertIn("Cleaned up 1 expired memories", stdout)
        stdout, _ = self.run_cli("claude-code", "load", "active", "project_context")
        self.assertEqual(stdout.strip(), "current")
        stdout, _ = self.run_cli("claude-code", "cleanup")
        self.assertIn("Cleaned up 0 expired memories", stdout)

    def test_missing_arguments_report_usage(self):
        cases = (
            (("claude-code",), "<agent> <command>"),
            (("claude-code", "save", "note"), "save <key> <value>"),
            (("claude-code", "load"), "load <key>"),
            (("claude-code", "delete"), "delete <key>"),
        )
        for args, usage in cases:
            with self.subTest(args=args):
                stdout, _ = self.run_cli(*args, expected_status=1)
                self.assertIn(usage, stdout)

    def test_unknown_command_reports_error(self):
        stdout, _ = self.run_cli("claude-code", "unknown-command", expected_status=1)
        self.assertIn("Unknown command: unknown-command", stdout)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux permits opening a FIFO read/write")
    def test_cli_rejects_fifo_as_database(self):
        self.memory_root.mkdir()
        database = self.memory_root / "memory.db"
        os.mkfifo(database)

        _, stderr = self.run_cli("claude-code", "list", expected_status=1)
        self.assertIn("memory database must be a regular file", stderr)
        self.assertTrue(database.is_fifo())


if __name__ == "__main__":
    unittest.main()
