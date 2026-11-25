"""Tests for the memory hooks (unified-integration/memory/hooks/).

Regression coverage:
- F-01: bash hooks must be thin wrappers delegating to the Python hook;
  no SQL may be interpolated in bash (CONTRACT R101).
- F-10: hook CLI argument mapping (save <key> <value> <type>).
"""
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module, run

AGENTS = [
    "claude-code", "codex", "opencode", "cursor", "gemini-cli",
    "windsurf", "copilot", "kiro", "hermes",
]
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
        temp = tempfile.TemporaryDirectory(prefix="ae memory hook's ")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.memory = self.root / "memory"
        self.database = self.memory / "memory.db"
        home = self.root / "home"
        home.mkdir()
        self.env = {
            "HOME": str(home),
            "AGENT_ENHANCEMENTS_STATE_DIR": str(self.root / "ae-state"),
            "AGENT_MEMORY_ROOT": str(self.memory),
        }

    def hook(self, agent, *arguments, status=0):
        rc, out, err = run(
            ["bash", str(HOOKS / f"{agent}-memory-hook.sh"), *arguments],
            env=self.env, cwd=self.root,
        )
        self.assertEqual(rc, status, out + err)
        return out, err

    def test_wrappers_isolate_the_same_default_key_by_agent(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                self.hook(agent, "save", "review", f"{agent}'s draft")

        for agent in AGENTS:
            with self.subTest(agent=agent):
                self.assertEqual(self.hook(agent, "load", "review"), (f"{agent}'s draft\n", ""))
                out, _ = self.hook(agent, "list")
                self.assertIn(f"[session_context] review: {agent}'s draft", out)
                self.assertEqual(len(out.splitlines()), 1)
                self.hook(agent, "delete", "review")
                out, err = self.hook(agent, "load", "review", status=1)
                self.assertEqual(out, "")
                self.assertIn("Memory not found: review", err)
                self.assertEqual(self.hook(agent, "list"), ("", ""))

        self.assertEqual(stat.S_IMODE(self.memory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.database.stat().st_mode), 0o600)

    def test_save_with_sql_payload_is_stored_verbatim(self):
        """A quote-bearing payload must be stored as data, never executed."""
        payload = "x', 'injected_type', 'k', 'pwned') -- "
        self.hook("codex", "save", "key", payload, "session_context", "proj")
        self.assertEqual(
            self.hook("codex", "load", "key", "session_context", "proj"),
            (payload + "\n", ""),
        )

    def test_explicit_project_and_type_scope_list_and_delete(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                self.hook(agent, "save", "report", "x" * 210, "fact", "proj")
                self.hook(agent, "save", "report", "different type", "note", "proj")
                self.hook(agent, "save", "report", "different project", "fact", "other")

                out, _ = self.hook(agent, "list", "fact", "proj", "1")
                self.assertIn(f"[fact] report: {'x' * 200}... (updated:", out)
                self.assertEqual(len(out.splitlines()), 1)
                self.assertEqual(self.hook(agent, "list", "fact", "proj", "0"), ("", ""))

                self.hook(agent, "delete", "report", "fact", "proj")
                self.hook(agent, "delete", "report", "fact", "proj", status=1)
                self.assertEqual(
                    self.hook(agent, "load", "report", "note", "proj"),
                    ("different type\n", ""),
                )
                self.assertEqual(
                    self.hook(agent, "load", "report", "fact", "other"),
                    ("different project\n", ""),
                )

    def test_cleanup_removes_expired_memory_and_retains_live_memory(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                self.hook(agent, "save", "old", "expired value", "note", "proj", "-1")
                self.hook(agent, "save", "new", "live value", "note", "proj", "7")
                self.hook(agent, "load", "old", "note", "proj", status=1)
                out, _ = self.hook(agent, "list", "note", "proj")
                self.assertIn("[note] new: live value", out)
                self.assertNotIn("expired value", out)
                self.assertEqual(
                    self.hook(agent, "cleanup"), ("Cleaned up 1 expired memories\n", ""),
                )
                self.assertEqual(
                    self.hook(agent, "load", "new", "note", "proj"), ("live value\n", ""),
                )

    def test_bad_arguments_exit_with_usage(self):
        cases = (
            ((), "Usage:"),
            (("save", "key-without-value"), "save <key> <value>"),
            (("load",), "load <key>"),
            (("delete",), "delete <key>"),
            (("unknown-command",), "Unknown command: unknown-command"),
        )
        for agent in AGENTS:
            for arguments, expected in cases:
                with self.subTest(agent=agent, arguments=arguments):
                    out, err = self.hook(agent, *arguments, status=1)
                    self.assertIn(expected, out)
                    self.assertEqual(err, "")

    def test_symlinked_database_leaves_target_untouched(self):
        target = self.root / "unrelated-file"
        target.write_bytes(b"unrelated data\n")
        target.chmod(0o644)
        self.memory.mkdir()
        self.database.symlink_to(target)
        for agent in AGENTS:
            with self.subTest(agent=agent):
                _, err = self.hook(agent, "save", "key", "value", status=1)
                self.assertIn("Refusing symlinked memory database", err)
                self.assertTrue(self.database.is_symlink())
                self.assertEqual(target.read_bytes(), b"unrelated data\n")
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires POSIX named pipes")
    def test_nonregular_database_is_rejected_before_sqlite_opens_it(self):
        self.memory.mkdir()
        os.mkfifo(self.database, 0o644)
        for agent in AGENTS:
            with self.subTest(agent=agent):
                _, err = self.hook(agent, "save", "key", "value", status=1)
                self.assertIn("Memory database must be a regular file", err)
                self.assertTrue(stat.S_ISFIFO(self.database.stat().st_mode))

    def test_imported_hook_roundtrips_structured_metadata(self):
        for agent in AGENTS:
            with self.subTest(agent=agent), patch.object(sys, "path", sys.path.copy()), \
                    patch.dict(sys.modules):
                hook = load_module(
                    "legacy_memory_hook_test", HOOKS / f"{agent}-memory-hook.py", self.env,
                )
                hook.init_db()
                hook.save_memory("checkpoint", "saved", project="proj", metadata={"steps": [1, 2]})
                entry, = hook.list_memories("session_context", "proj")
                self.assertEqual(entry["key"], "checkpoint")
                self.assertEqual(entry["value"], "saved")
                self.assertEqual(entry["metadata"], {"steps": [1, 2]})


if __name__ == "__main__":
    unittest.main()
