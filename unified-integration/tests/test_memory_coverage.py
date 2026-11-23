"""Behavioral coverage for unified-integration/scripts/memory.py.

Complements test_memory.py, test_security_regressions.py and
test_setup_regressions.py: this file drives AgentMemory semantics (scoping,
upsert, TTL, listing, redaction fallback) and the CLI entry point in-process,
so every branch is exercised without relying on subprocess coverage.
All state lives in a per-test temp directory; no network is used.
"""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module

MEMORY_PY = UI_DIR / "scripts" / "memory.py"


class _MemoryCase(unittest.TestCase):
    """Fresh module + private memory root + isolated credentials file."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.mem_root = self.root / "memory"
        # Point the shared redactor at an empty, isolated config so the
        # developer's real credentials file is never read.
        self.api_file = self.root / "api.json"
        self.api_file.write_text(json.dumps(
            {"version": 1, "api_keys": {}, "connections": {}, "mcp": {}}))
        env = {
            "AGENT_MEMORY_ROOT": str(self.mem_root),
            "AGENT_ENHANCEMENTS_API_FILE": str(self.api_file),
            "HOME": str(self.root / "home"),
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.mod = load_module("memory_coverage_%d" % id(self), MEMORY_PY)
        self.addCleanup(sys.modules.pop, "memory_coverage_%d" % id(self), None)

    def store(self, agent="codex", project="proj-a"):
        return self.mod.AgentMemory(agent, project=project)

    def rows(self, sql, params=()):
        with sqlite3.connect(self.mod.DB_PATH) as conn:
            return conn.execute(sql, params).fetchall()


class ModuleConfigurationTests(_MemoryCase):
    def test_paths_follow_memory_root_override(self):
        self.assertEqual(self.mod.MEMORY_ROOT, self.mem_root)
        self.assertEqual(self.mod.DB_PATH, self.mem_root / "memory.db")

    def test_init_creates_private_schema_idempotently(self):
        self.store()
        self.store()  # second init must not fail on existing schema
        self.assertEqual(self.mem_root.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.mod.DB_PATH.stat().st_mode & 0o777, 0o600)
        names = {r[0] for r in self.rows(
            "SELECT name FROM sqlite_master WHERE type IN ('table','index')")}
        self.assertIn("memories", names)
        self.assertTrue({"idx_agent_project", "idx_type", "idx_expires"} <= names)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires POSIX FIFOs")
    def test_non_regular_database_path_is_rejected(self):
        self.mem_root.mkdir(mode=0o700)
        os.mkfifo(self.mod.DB_PATH, 0o600)
        with self.assertRaisesRegex(OSError, "must be a regular file"):
            self.store()
        # The FIFO is left alone, not replaced by a database.
        self.assertFalse(self.mod.DB_PATH.is_file())

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_symlinked_database_path_is_refused(self):
        self.mem_root.mkdir(mode=0o700)
        victim = self.root / "victim.db"
        victim.write_text("do not touch")
        victim.chmod(0o644)
        self.mod.DB_PATH.symlink_to(victim)
        with self.assertRaises(OSError):
            self.store()
        self.assertEqual(victim.read_text(), "do not touch")
        self.assertEqual(victim.stat().st_mode & 0o777, 0o644)

    def test_default_project_is_resolved_cwd(self):
        work = self.root / "work"
        work.mkdir()
        old = os.getcwd()
        os.chdir(work)
        self.addCleanup(os.chdir, old)
        mem = self.mod.AgentMemory("codex")
        self.assertEqual(mem.project, str(work.resolve()))


class SaveLoadSemanticsTests(_MemoryCase):
    def test_save_same_key_replaces_value_without_duplicates(self):
        mem = self.store()
        mem.save("k", "first")
        mem.save("k", "second")
        self.assertEqual(mem.load("k"), "second")
        count = self.rows("SELECT COUNT(*) FROM memories WHERE key='k'")[0][0]
        self.assertEqual(count, 1)

    def test_memories_are_scoped_by_agent_project_and_type(self):
        a = self.store("codex", "proj-a")
        b = self.store("claude", "proj-a")
        c = self.store("codex", "proj-b")
        a.save("k", "codex-a")
        b.save("k", "claude-a")
        c.save("k", "codex-b")
        a.save("k", "typed", "user_preferences")
        self.assertEqual(a.load("k"), "codex-a")
        self.assertEqual(b.load("k"), "claude-a")
        self.assertEqual(c.load("k"), "codex-b")
        self.assertEqual(a.load("k", "user_preferences"), "typed")
        self.assertIsNone(b.load("k", "user_preferences"))
        # Deleting in one scope leaves the others intact.
        self.assertTrue(a.delete("k"))
        self.assertEqual(b.load("k"), "claude-a")
        self.assertEqual(a.load("k", "user_preferences"), "typed")

    def test_delete_respects_memory_type(self):
        mem = self.store()
        mem.save("k", "v", "project_context")
        self.assertFalse(mem.delete("k"))  # default type: nothing there
        self.assertTrue(mem.delete("k", "project_context"))
        self.assertIsNone(mem.load("k", "project_context"))

    def test_positive_ttl_is_stored_in_sqlite_comparable_format(self):
        mem = self.store()
        mem.save("k", "v", ttl_days=3)
        (expires,) = self.rows("SELECT expires_at FROM memories WHERE key='k'")[0]
        # "YYYY-MM-DD HH:MM:SS" (space separator) so comparisons against
        # datetime('now') are lexically correct.
        self.assertRegex(expires, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
        in_future = self.rows("SELECT ? > datetime('now', '+2 days')", (expires,))[0][0]
        self.assertEqual(in_future, 1)
        self.assertEqual(mem.load("k"), "v")

    def test_out_of_range_ttl_raises_value_error_and_keeps_record(self):
        mem = self.store()
        mem.save("k", "kept")
        for ttl in (3_000_000, 99_999_999_999, -99_999_999_999):
            with self.subTest(ttl=ttl), self.assertRaises(ValueError):
                mem.save("k", "replaced", ttl_days=ttl)
        self.assertEqual(mem.load("k"), "kept")

    def test_no_ttl_means_no_expiry(self):
        mem = self.store()
        mem.save("k", "v")
        self.assertEqual(self.rows("SELECT expires_at FROM memories")[0][0], None)
        self.assertEqual(mem.cleanup_expired(), 0)
        self.assertEqual(mem.load("k"), "v")

    def test_metadata_round_trips_through_list(self):
        mem = self.store()
        mem.save("k", "v", metadata={"source": "test", "n": 3})
        mem.save("plain", "v")
        by_key = {m["key"]: m for m in mem.list()}
        self.assertEqual(by_key["k"]["metadata"], {"source": "test", "n": 3})
        self.assertEqual(by_key["plain"]["metadata"], {})
        self.assertEqual(self.rows(
            "SELECT metadata FROM memories WHERE key='plain'")[0][0], None)

    def test_unicode_and_large_values_round_trip_exactly_on_load(self):
        mem = self.store()
        value = "café ☃ " * 400
        mem.save("big", value)
        self.assertEqual(mem.load("big"), value)


class ListAndCleanupTests(_MemoryCase):
    def test_list_entry_shape(self):
        mem = self.store()
        mem.save("k", "v", "user_preferences")
        (item,) = mem.list()
        self.assertEqual(set(item), {"type", "key", "value", "metadata", "updated"})
        self.assertEqual(item["type"], "user_preferences")
        self.assertEqual(item["value"], "v")
        self.assertRegex(item["updated"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_list_respects_limit_with_and_without_type(self):
        mem = self.store()
        for i in range(5):
            mem.save(f"k{i}", "v")
            mem.save(f"t{i}", "v", "project_context")
        self.assertEqual(len(mem.list(limit=3)), 3)
        self.assertEqual(len(mem.list()), 10)
        typed = mem.list("project_context", limit=2)
        self.assertEqual(len(typed), 2)
        self.assertTrue(all(m["type"] == "project_context" for m in typed))

    def test_list_excludes_other_scopes_and_expired_rows(self):
        mem = self.store()
        self.store("other-agent").save("foreign", "v")
        self.store(project="other-proj").save("foreign2", "v")
        mem.save("live", "v", ttl_days=1)
        mem.save("dead", "v", ttl_days=-1)
        mem.save("dead-typed", "v", "project_context", ttl_days=-1)
        self.assertEqual([m["key"] for m in mem.list()], ["live"])
        self.assertEqual(mem.list("project_context"), [])

    def test_list_truncates_long_values_but_load_does_not(self):
        mem = self.store()
        limit = self.mod.LIST_VALUE_LIMIT
        exact = "a" * limit
        long = "b" * (limit + 50)
        mem.save("exact", exact)
        mem.save("long", long)
        by_key = {m["key"]: m["value"] for m in mem.list()}
        self.assertEqual(by_key["exact"], exact)  # at the limit: untouched
        self.assertEqual(by_key["long"], "b" * limit + "...")
        self.assertEqual(mem.load("long"), long)

    def test_cleanup_removes_only_expired_rows_across_all_scopes(self):
        a = self.store("codex")
        b = self.store("claude", "proj-z")
        a.save("old", "v", ttl_days=-2)
        b.save("old", "v", ttl_days=-2)
        a.save("fresh", "v", ttl_days=2)
        a.save("forever", "v")
        self.assertEqual(a.cleanup_expired(), 2)
        self.assertEqual(a.cleanup_expired(), 0)
        keys = sorted(r[0] for r in self.rows("SELECT key FROM memories"))
        self.assertEqual(keys, ["forever", "fresh"])


class RedactorTests(_MemoryCase):
    def test_redactor_falls_back_to_identity_when_api_config_unavailable(self):
        # sys.modules[name] = None makes the lazy import raise ImportError.
        with mock.patch.dict(sys.modules, {"api_config": None}):
            redact = self.mod._redactor()
            self.assertEqual(redact("token sk-live-abc"), "token sk-live-abc")

    def test_redactor_falls_back_when_config_read_fails(self):
        broken = mock.Mock()
        broken.read_config.side_effect = RuntimeError("corrupt config")
        with mock.patch.dict(sys.modules, {"api_config": broken}):
            redact = self.mod._redactor()
            self.assertEqual(redact("unchanged"), "unchanged")
        broken.redact.assert_not_called()

    def test_list_still_works_without_redactor(self):
        mem = self.store()
        mem.save("k", "plain value")
        with mock.patch.dict(sys.modules, {"api_config": None}):
            self.assertEqual(mem.list()[0]["value"], "plain value")

    def test_list_applies_configured_redaction(self):
        secret = "Zq7Lm2Xr9Pw4Ty6Hb3Nc8Vd1Kf5Gs0Jh2Qa7We4R"
        self.api_file.write_text(json.dumps({
            "version": 1, "api_keys": {"FIXTURE_KEY": secret},
            "connections": {}, "mcp": {}}))
        mem = self.store()
        mem.save("k", f"before {secret} after")
        listed = mem.list()[0]["value"]
        self.assertNotIn(secret, listed)
        self.assertIn("before", listed)
        # Raw storage and load are not redacted (redaction is display-only).
        self.assertEqual(mem.load("k"), f"before {secret} after")

    def test_secret_straddling_truncation_point_is_not_leaked(self):
        secret = "Zq7Lm2Xr9Pw4Ty6Hb3Nc8Vd1Kf5Gs0Jh2Qa7We4R"
        self.api_file.write_text(json.dumps({
            "version": 1, "api_keys": {"FIXTURE_KEY": secret},
            "connections": {}, "mcp": {}}))
        mem = self.store()
        # Place the secret so the LIST_VALUE_LIMIT cut lands inside it.
        pad = "x" * (self.mod.LIST_VALUE_LIMIT - len(secret) // 2)
        mem.save("k", pad + secret + "y" * 100)
        listed = mem.list()[0]["value"]
        self.assertTrue(listed.endswith("..."))
        self.assertNotIn(secret[: len(secret) // 2], listed)


class IntArgTests(_MemoryCase):
    def test_parses_integers_including_negative(self):
        self.assertEqual(self.mod._int_arg("7", "usage"), 7)
        self.assertEqual(self.mod._int_arg("-1", "usage"), -1)

    def test_invalid_integer_prints_usage_and_exits_1(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as ctx:
            self.mod._int_arg("soon", "USAGE TEXT")
        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(out.getvalue(), "USAGE TEXT\n")

    def test_bounds_are_inclusive_and_out_of_range_exits_1(self):
        self.assertEqual(self.mod._int_arg("1", "usage", lo=1, hi=5), 1)
        self.assertEqual(self.mod._int_arg("5", "usage", lo=1, hi=5), 5)
        for raw in ("0", "6", "-1", "9" * 40):
            with self.subTest(raw=raw):
                out = io.StringIO()
                with contextlib.redirect_stdout(out), \
                        self.assertRaises(SystemExit) as ctx:
                    self.mod._int_arg(raw, "BOUNDED", lo=1, hi=5)
                self.assertEqual(ctx.exception.code, 1)
                self.assertEqual(out.getvalue(), "BOUNDED\n")


class CliMainTests(_MemoryCase):
    """Drive main() in-process with a patched argv and a temp cwd."""

    def setUp(self):
        super().setUp()
        self.work = self.root / "work"
        self.work.mkdir()
        old = os.getcwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, old)

    def cli(self, *args):
        out = io.StringIO()
        code = 0
        with mock.patch.object(sys, "argv", ["memory.py", *args]), \
                contextlib.redirect_stdout(out):
            try:
                self.mod.main()
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue()

    def test_no_arguments_prints_full_usage(self):
        code, out = self.cli("codex")
        self.assertEqual(code, 1)
        self.assertIn("Usage: memory.py <agent> <command>", out)
        for cmd in ("save", "load", "list", "delete", "cleanup"):
            self.assertIn(cmd, out)

    def test_unknown_command(self):
        self.assertEqual(self.cli("codex", "frobnicate"),
                         (1, "Unknown command: frobnicate\n"))

    def test_save_then_load_uses_cwd_as_project(self):
        self.assertEqual(self.cli("codex", "save", "k", "hello"),
                         (0, "Saved: k (session_context)\n"))
        self.assertEqual(self.cli("codex", "load", "k"), (0, "hello\n"))
        direct = self.mod.AgentMemory("codex", project=str(self.work.resolve()))
        self.assertEqual(direct.load("k"), "hello")
        # Another agent in the same project does not see it.
        self.assertEqual(self.cli("claude", "load", "k"),
                         (1, "Memory not found: k\n"))

    def test_save_with_type_and_ttl(self):
        self.assertEqual(self.cli("codex", "save", "k", "v", "user_preferences", "5"),
                         (0, "Saved: k (user_preferences)\n"))
        self.assertEqual(self.cli("codex", "load", "k", "user_preferences"), (0, "v\n"))
        self.assertEqual(self.cli("codex", "load", "k")[0], 1)  # wrong type
        (expires,) = self.rows("SELECT expires_at FROM memories WHERE key='k'")[0]
        self.assertIsNotNone(expires)

    def test_save_usage_errors(self):
        code, out = self.cli("codex", "save", "k")
        self.assertEqual(code, 1)
        self.assertIn("save <key> <value>", out)
        code, out = self.cli("codex", "save", "k", "v", "session_context", "x")
        self.assertEqual(code, 1)
        self.assertIn("[ttl_days]", out)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM memories")[0][0], 0)

    def test_load_without_key_prints_usage(self):
        self.assertEqual(self.cli("codex", "load"),
                         (1, "Usage: memory.py <agent> load <key> [type]\n"))

    def test_delete_without_key_prints_usage(self):
        self.assertEqual(self.cli("codex", "delete"),
                         (1, "Usage: memory.py <agent> delete <key> [type]\n"))

    def test_delete_with_type(self):
        self.cli("codex", "save", "k", "v", "project_context")
        self.assertEqual(self.cli("codex", "delete", "k"), (0, "Not found: k\n"))
        self.assertEqual(self.cli("codex", "delete", "k", "project_context"),
                         (0, "Deleted: k\n"))

    def test_list_default_and_filtered_output(self):
        self.cli("codex", "save", "a", "1")
        self.cli("codex", "save", "b", "2", "project_context")
        code, out = self.cli("codex", "list")
        self.assertEqual(code, 0)
        lines = sorted(out.splitlines())
        self.assertEqual(len(lines), 2)
        self.assertRegex(lines[0], r"^\[project_context\] b: 2 \(updated: .+\)$")
        self.assertRegex(lines[1], r"^\[session_context\] a: 1 \(updated: .+\)$")
        code, out = self.cli("codex", "list", "project_context", "1")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertIn("] b: 2", out)

    def test_list_bad_limit(self):
        code, out = self.cli("codex", "list", "session_context", "lots")
        self.assertEqual(code, 1)
        self.assertIn("list [type] [limit]", out)

    def test_list_limit_must_be_positive_and_bounded(self):
        for raw in ("0", "-1", str(self.mod.LIST_LIMIT_MAX + 1)):
            with self.subTest(limit=raw):
                code, out = self.cli("codex", "list", "session_context", raw)
                self.assertEqual(code, 1)
                self.assertIn("list [type] [limit]", out)
        self.cli("codex", "save", "a", "1")
        code, out = self.cli("codex", "list", "session_context",
                             str(self.mod.LIST_LIMIT_MAX))
        self.assertEqual(code, 0)
        self.assertIn("] a: 1", out)

    def test_save_rejects_non_positive_or_huge_ttl_and_keeps_record(self):
        self.cli("codex", "save", "k", "kept")
        for raw in ("0", "-1", str(self.mod.TTL_DAYS_MAX + 1), "3000000",
                    "99999999999"):
            with self.subTest(ttl=raw):
                code, out = self.cli("codex", "save", "k", "lost",
                                     "session_context", raw)
                self.assertEqual(code, 1)
                self.assertIn("[ttl_days]", out)
                self.assertNotIn("Saved", out)
        self.assertEqual(self.cli("codex", "load", "k"), (0, "kept\n"))
        self.assertEqual(
            self.cli("codex", "save", "k", "v", "session_context",
                     str(self.mod.TTL_DAYS_MAX))[0], 0)

    def test_list_empty_prints_nothing(self):
        self.assertEqual(self.cli("codex", "list"), (0, ""))

    def test_cleanup_reports_count(self):
        # The CLI refuses non-positive TTLs; plant the expired row via the API.
        self.mod.AgentMemory("codex", project=str(self.work.resolve())).save(
            "gone", "v", ttl_days=-1)
        self.cli("codex", "save", "kept", "v")
        self.assertEqual(self.cli("codex", "cleanup"),
                         (0, "Cleaned up 1 expired memories\n"))
        self.assertEqual(self.cli("codex", "load", "kept"), (0, "v\n"))

    def test_running_as_script_invokes_main(self):
        import runpy
        out = io.StringIO()
        argv = [str(MEMORY_PY), "codex", "save", "k", "via-script"]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
            runpy.run_path(str(MEMORY_PY), run_name="__main__")
        self.assertEqual(out.getvalue(), "Saved: k (session_context)\n")
        self.assertEqual(self.cli("codex", "load", "k"), (0, "via-script\n"))


if __name__ == "__main__":
    unittest.main()
