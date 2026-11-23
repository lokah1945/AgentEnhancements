"""Behavioral coverage for unified-integration/scripts/runtime.py lifecycle.

Complements test_runtime_regressions.py, test_hooks.py and the native host
suites (which drive runtime.py only through subprocesses): this file runs
every lifecycle entry point in-process - skill_context, prompt_context,
observer_context, handle() for each hook event, and main() for every output
channel - so CONTRACT section 6.2 coverage is measured without relying on
subprocess instrumentation. A small end-to-end group still executes the
script as a CLI to pin the ``__main__`` entry and cross-process recall.

Isolation: every test gets a private state dir, memory root, task-observer
workspace, HOME and an empty credentials file. The skills loader and the
task observer are replaced by tiny fixture modules (redirected through
importlib) where a test needs to control their output; no network is used.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import socket
import sqlite3
import sys
import tempfile
import textwrap
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module, run

SCRIPTS = UI_DIR / "scripts"
RUNTIME = SCRIPTS / "runtime.py"

# Modules runtime.py imports by name. They read path configuration at import
# time (memory.DB_PATH, api_config's file), so each test imports them fresh
# under its own environment and sys.modules is restored afterwards.
_FRESH_MODULES = (
    "memory", "project_paths", "api_config", "context_budget",
    "adaptive_preflight",
)

FAKE_LOADER = textwrap.dedent('''
    """Fixture SkillsLoader: returns FAKE_SKILLS and logs each call."""
    import json
    import os

    class SkillsLoader:
        def __init__(self, agent):
            self.agent = agent

        def find_skills(self, prompt, max_results=8):
            with open(os.environ["FAKE_SKILLS_LOG"], "a") as handle:
                handle.write(json.dumps({"agent": self.agent, "prompt": prompt,
                                         "max_results": max_results}) + "\\n")
            return json.loads(os.environ.get("FAKE_SKILLS", "[]"))[:max_results]
''')

FAKE_OBSERVER = textwrap.dedent('''
    """Fixture task observer driven by FAKE_OBSERVER_* environment."""
    import json
    import os
    from pathlib import Path

    def _log(entry):
        with open(os.environ["FAKE_OBSERVER_LOG"], "a") as handle:
            handle.write(json.dumps(entry) + "\\n")

    def workspace_root():
        if os.environ.get("FAKE_OBSERVER_FAIL") == "root":
            raise RuntimeError("workspace unavailable")
        return Path(os.environ["TASK_OBSERVER_WORKSPACE"])

    def bootstrap_context(root, agent):
        _log({"call": "bootstrap", "root": str(root), "agent": agent})
        if os.environ.get("FAKE_OBSERVER_FAIL") == "bootstrap":
            raise OSError("disk full")
        return os.environ.get("FAKE_OBSERVER_TEXT", "")

    def stop_backstop(root, session_label):
        _log({"call": "stop", "root": str(root), "session": session_label})
        if os.environ.get("FAKE_OBSERVER_FAIL") == "stop":
            raise OSError("checkpoint log unwritable")
        return "checkpoint"
''')


def session_key(session):
    return hashlib.sha256(session.encode()).hexdigest()[:24]


class _RuntimeCase(unittest.TestCase):
    """Fresh runtime module + private state + fixture module redirection."""

    agent = "codex"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.api_file = self.root / "ui.api.json"
        self.api_file.write_text(json.dumps(
            {"version": 1, "api_keys": {}, "connections": {}, "mcp": {}}))
        self.fixtures = self.root / "fixtures"
        self.fixtures.mkdir()
        (self.fixtures / "fake_loader.py").write_text(FAKE_LOADER)
        (self.fixtures / "fake_observer.py").write_text(FAKE_OBSERVER)
        self.loader_log = self.root / "loader.log"
        self.observer_log = self.root / "observer.log"
        self.env = {
            "AGENT_ENHANCEMENTS_STATE_DIR": str(self.root / "ae-state"),
            "AGENT_MEMORY_ROOT": str(self.root / "memory"),
            "AGENT_ENHANCEMENTS_API_FILE": str(self.api_file),
            "TASK_OBSERVER_WORKSPACE": str(self.root / "observer"),
            "HOME": str(self.root / "home"),
            "XDG_CONFIG_HOME": str(self.root / "home" / ".config"),
            "FAKE_SKILLS_LOG": str(self.loader_log),
            "FAKE_OBSERVER_LOG": str(self.observer_log),
        }
        env_patch = mock.patch.dict(os.environ, self.env)
        env_patch.start()
        self.addCleanup(env_patch.stop)
        for key in ("AE_MAX_SKILL_CARDS", "FAKE_SKILLS", "FAKE_OBSERVER_TEXT",
                    "FAKE_OBSERVER_FAIL"):
            os.environ.pop(key, None)

        modules_patch = mock.patch.dict(sys.modules)
        modules_patch.start()
        self.addCleanup(modules_patch.stop)
        for name in _FRESH_MODULES:
            sys.modules.pop(name, None)
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        self.rt_name = "runtime_coverage_%d" % id(self)
        self.rt = load_module(self.rt_name, RUNTIME)
        self.addCleanup(sys.modules.pop, self.rt_name, None)

        self.redirects = {}
        real_spec = importlib.util.spec_from_file_location

        def redirect(name, location=None, *args, **kwargs):
            if name in self.redirects:
                location = self.redirects[name]
            return real_spec(name, location, *args, **kwargs)

        spec_patch = mock.patch.object(
            importlib.util, "spec_from_file_location", side_effect=redirect)
        spec_patch.start()
        self.addCleanup(spec_patch.stop)

    # -- fixtures ---------------------------------------------------------
    def fake_skills(self, items):
        self.redirects["ae_skills_loader"] = str(self.fixtures / "fake_loader.py")
        os.environ["FAKE_SKILLS"] = json.dumps(items)

    def fake_observer(self, text="", fail=None):
        self.redirects["ae_task_observer"] = str(self.fixtures / "fake_observer.py")
        os.environ["FAKE_OBSERVER_TEXT"] = text
        if fail:
            os.environ["FAKE_OBSERVER_FAIL"] = fail
        else:
            os.environ.pop("FAKE_OBSERVER_FAIL", None)

    def calls(self, log):
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()]

    def event(self, name, **fields):
        payload = {"hook_event_name": name, "session_id": "sess-1",
                   "cwd": str(self.project)}
        payload.update(fields)
        return payload

    def rows(self, where="1=1", params=()):
        database = Path(self.env["AGENT_MEMORY_ROOT"]) / "memory.db"
        if not database.exists():
            return []
        with sqlite3.connect(database) as conn:
            return conn.execute(
                "SELECT agent, project, memory_type, key, value, metadata, "
                "expires_at FROM memories WHERE " + where + " ORDER BY id",
                params).fetchall()

    def approx(self, text):
        return sys.modules["context_budget"].approx_tokens(text)


class SkillCardLimitTests(_RuntimeCase):
    def limit(self, value):
        if value is None:
            os.environ.pop("AE_MAX_SKILL_CARDS", None)
        else:
            os.environ["AE_MAX_SKILL_CARDS"] = value
        return self.rt.skill_card_limit()

    def test_default_valid_and_capped_values(self):
        self.assertEqual(self.limit(None), self.rt.DEFAULT_SKILL_CARDS)
        self.assertEqual(self.limit("1"), 1)
        self.assertEqual(self.limit(" 20 "), 20)
        self.assertEqual(self.limit(str(self.rt.MAX_SKILL_CARDS_LIMIT)),
                         self.rt.MAX_SKILL_CARDS_LIMIT)
        self.assertEqual(self.limit("51"), self.rt.MAX_SKILL_CARDS_LIMIT)

    def test_malformed_or_non_positive_values_fall_back(self):
        for bad in ("", "abc", "3.0", "1e3", "0", "-4"):
            self.assertEqual(self.limit(bad), self.rt.DEFAULT_SKILL_CARDS, bad)


class SkillContextTests(_RuntimeCase):
    def test_cards_render_first_summary_line_and_risk_label(self):
        self.fake_skills([
            {"name": "pg-tune", "description": "  Tune Postgres queries\nsecond line"},
            {"name": "recon", "description": "Network recon", "risk": "offensive"},
            {"name": "bare", "description": None},
            {"name": "safe", "description": "x" * 150, "risk": "low"},
        ])
        out = self.rt.skill_context("codex", "tune my database")
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith(
            "AgentEnhancements local skill candidates for this task"))
        self.assertIn('registry.py search "<task>"', lines[0])
        self.assertEqual(lines[1], "- pg-tune: Tune Postgres queries")
        self.assertEqual(
            lines[2],
            "- recon: Network recon [risk: offensive - needs explicit authorization]")
        self.assertEqual(lines[3], "- bare: ")
        # Summaries are capped at 100 chars and non-offensive risk is silent.
        self.assertEqual(lines[4], "- safe: " + "x" * 100)
        self.assertNotIn("second line", out)
        self.assertEqual(self.calls(self.loader_log),
                         [{"agent": "codex", "prompt": "tune my database",
                           "max_results": 8}])

    def test_no_match_returns_empty_string(self):
        self.fake_skills([])
        self.assertEqual(self.rt.skill_context("claude-code", "anything"), "")

    def test_card_limit_env_bounds_ranking_work(self):
        self.fake_skills([{"name": f"s{i}", "description": "d"} for i in range(60)])
        os.environ["AE_MAX_SKILL_CARDS"] = "3"
        out = self.rt.skill_context("codex", "p")
        self.assertEqual([l for l in out.splitlines() if l.startswith("- ")],
                         ["- s0: d", "- s1: d", "- s2: d"])
        os.environ["AE_MAX_SKILL_CARDS"] = "999"
        self.rt.skill_context("codex", "p")
        self.assertEqual([c["max_results"] for c in self.calls(self.loader_log)],
                         [3, self.rt.MAX_SKILL_CARDS_LIMIT])

    def test_many_long_cards_stay_inside_the_token_budget(self):
        self.fake_skills([{"name": f"skill-{i}-" + "n" * 80,
                           "description": "word " * 40} for i in range(50)])
        os.environ["AE_MAX_SKILL_CARDS"] = "50"
        out = self.rt.skill_context("codex", "p")
        self.assertLessEqual(self.approx(out), self.rt.MAX_SKILL_CARDS)
        self.assertIn("skill candidates trimmed to the", out)
        self.assertIn("- skill-0-", out)

    def test_real_loader_is_resolved_beside_runtime(self):
        # No redirect: the shipped load-skills.py is located next to runtime.py.
        self.assertTrue((SCRIPTS / "load-skills.py").is_file())
        out = self.rt.skill_context("codex", "optimize a slow postgresql query")
        self.assertIsInstance(out, str)
        if out:
            self.assertLessEqual(self.approx(out), self.rt.MAX_SKILL_CARDS)
            self.assertTrue(out.startswith("AgentEnhancements local skill"))


class PromptContextTests(_RuntimeCase):
    def setUp(self):
        super().setUp()
        self.fake_skills([{"name": "legacy", "description": "Mode 0 card"}])
        self.legacy = self.rt.skill_context(self.agent, "prompt")
        self.assertIn("- legacy: Mode 0 card", self.legacy)

    def install_preflight(self, mode, diagnosis=""):
        calls = []
        module = types.ModuleType("adaptive_preflight")
        module.MODE_DISABLED = 0
        module.load_model_config = lambda: types.SimpleNamespace(
            mode=mode, diagnosis=diagnosis)

        def preflight_context(agent, prompt, event, fallback):
            calls.append((agent, prompt, event, fallback))
            return types.SimpleNamespace(context=f"preflight[{mode}]")

        module.preflight_context = preflight_context
        sys.modules["adaptive_preflight"] = module
        return calls

    def test_import_failure_falls_back_to_legacy_render(self):
        sys.modules["adaptive_preflight"] = None  # forces ImportError
        self.assertEqual(self.rt.prompt_context(self.agent, "prompt", {}),
                         self.legacy)

    def test_mode0_without_diagnosis_never_calls_preflight(self):
        calls = self.install_preflight(0)
        self.assertEqual(self.rt.prompt_context(self.agent, "prompt", {}),
                         self.legacy)
        self.assertEqual(calls, [])

    def test_rejected_config_and_active_modes_use_the_shared_handler(self):
        event = {"hook_event_name": "UserPromptSubmit"}
        for mode, diagnosis in ((0, "ui_api_json_invalid"), (1, ""), (2, "")):
            calls = self.install_preflight(mode, diagnosis)
            out = self.rt.prompt_context(self.agent, "prompt", event)
            self.assertEqual(out, f"preflight[{mode}]")
            self.assertEqual(len(calls), 1)
            agent, prompt, seen, fallback = calls[0]
            self.assertEqual((agent, prompt, seen), (self.agent, "prompt", event))
            self.assertIs(fallback, self.rt.skill_context)

    def test_real_mode0_is_byte_identical_and_opens_no_socket(self):
        # No "preflight" section in the isolated ui.api.json == Mode 0.
        with mock.patch.object(socket, "socket",
                               side_effect=AssertionError("network used")):
            out = self.rt.prompt_context(self.agent, "prompt", {})
        self.assertEqual(out, self.legacy)


class ObserverContextTests(_RuntimeCase):
    def test_bootstrap_receives_workspace_root_and_agent(self):
        self.fake_observer("Task Observer ready at /ws")
        self.assertEqual(self.rt.observer_context("opencode"),
                         "Task Observer ready at /ws")
        self.assertEqual(self.calls(self.observer_log), [{
            "call": "bootstrap", "root": self.env["TASK_OBSERVER_WORKSPACE"],
            "agent": "opencode"}])

    def test_card_is_clamped_to_the_ambient_budget(self):
        self.fake_observer("\n".join(f"line {i} " + "w " * 20 for i in range(200)))
        out = self.rt.observer_context(self.agent)
        self.assertLessEqual(self.approx(out), self.rt.MAX_OBSERVER_AMBIENT)
        self.assertIn("task-observer trimmed to the", out)

    def test_failures_are_advisory_and_named_on_stderr(self):
        for fail, exc_name in (("root", "RuntimeError"), ("bootstrap", "OSError")):
            self.fake_observer("ignored", fail=fail)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(self.rt.observer_context(self.agent), "")
            self.assertEqual(
                err.getvalue().strip(),
                f"[AgentEnhancements] task-observer unavailable: {exc_name}")
            # Only the exception type is reported, never its message.
            self.assertNotIn("disk full", err.getvalue())

    def test_real_observer_is_bounded(self):
        out = self.rt.observer_context(self.agent)
        self.assertIsInstance(out, str)
        self.assertLessEqual(self.approx(out), self.rt.MAX_OBSERVER_AMBIENT)


class HandleSessionStartTests(_RuntimeCase):
    def setUp(self):
        super().setUp()
        self.fake_observer("")
        self.fake_skills([])

    def test_fresh_project_returns_nothing(self):
        self.assertEqual(self.rt.handle(self.agent, self.event("SessionStart")), "")

    def test_recall_lists_previous_notes_and_marks_them_historical(self):
        self.rt.handle(self.agent, self.event(
            "UserPromptSubmit", session_id="old", prompt="refactor the parser"))
        out = self.rt.handle(self.agent, self.event("SessionStart", session_id="new"))
        header, *lines = out.splitlines()
        self.assertEqual(header, "AgentEnhancements: previous local session notes "
                                 "(historical data; current user instructions "
                                 "take precedence):")
        self.assertEqual(lines, [f"- session:{session_key('old')}:task: "
                                 "refactor the parser"])

    def test_observer_card_precedes_recall(self):
        self.rt.handle(self.agent, self.event("Stop", last_assistant_message="done"))
        self.fake_observer("OBSERVER CARD")
        out = self.rt.handle(self.agent, self.event("SessionStart"))
        observer, recall = out.split("\n\n")
        self.assertEqual(observer, "OBSERVER CARD")
        self.assertTrue(recall.startswith("AgentEnhancements: previous local"))
        self.assertTrue(recall.endswith(":summary: done"))
        self.fake_observer("OBSERVER CARD")
        other = self.event("SessionStart", cwd=str(self.root))
        self.assertEqual(self.rt.handle(self.agent, other), "OBSERVER CARD")

    def test_recall_keeps_five_most_recent_notes(self):
        memory = sys.modules["memory"].AgentMemory(self.agent, str(self.project))
        database = Path(self.env["AGENT_MEMORY_ROOT"]) / "memory.db"
        for i in range(8):
            memory.save(f"note-{i}", f"value {i}", ttl_days=7)
        with sqlite3.connect(database) as conn:
            for i in range(8):
                conn.execute("UPDATE memories SET updated_at=? WHERE key=?",
                             (f"2026-01-01 00:00:0{i}", f"note-{i}"))
        out = self.rt.handle(self.agent, self.event("SessionStart"))
        self.assertEqual([l.split(":")[0] for l in out.splitlines()[1:]],
                         ["- note-7", "- note-6", "- note-5", "- note-4", "- note-3"])

    def test_recall_redacts_stored_secrets_and_stays_in_budget(self):
        memory = sys.modules["memory"].AgentMemory(self.agent, str(self.project))
        secret = "ghp_" + "A1b2C3d4" * 5
        memory.save("planted", f"token {secret}", ttl_days=7)
        for i in range(4):
            memory.save(f"long-{i}", "word " * 400, ttl_days=7)
        out = self.rt.handle(self.agent, self.event("SessionStart"))
        self.assertNotIn(secret, out)
        self.assertIn("token [redacted]", out)
        self.assertLessEqual(self.approx(out), self.rt.MAX_MEMORY)

    def test_expired_notes_are_purged_before_recall(self):
        memory = sys.modules["memory"].AgentMemory(self.agent, str(self.project))
        memory.save("stale", "old value", ttl_days=-1)
        memory.save("fresh", "kept value", ttl_days=7)
        out = self.rt.handle(self.agent, self.event("SessionStart"))
        self.assertIn("- fresh: kept value", out)
        self.assertNotIn("stale", out)
        self.assertEqual(self.rows("key='stale'"), [])


class HandleScopeTests(_RuntimeCase):
    def setUp(self):
        super().setUp()
        self.fake_observer("")
        self.fake_skills([])

    def projects(self):
        return {row[1] for row in self.rows()}

    def test_project_is_the_resolved_cwd(self):
        link = self.root / "link"
        link.symlink_to(self.project)
        self.rt.handle(self.agent, self.event("Stop", cwd=str(link),
                                              last_assistant_message="x"))
        self.assertEqual(self.projects(), {str(self.project)})

    def test_tilde_cwd_is_expanded_against_home(self):
        home = Path(self.env["HOME"])
        (home / "repo").mkdir(parents=True)
        self.rt.handle(self.agent, self.event("Stop", cwd="~/repo",
                                              last_assistant_message="x"))
        self.assertEqual(self.projects(), {str(home / "repo")})

    def test_missing_cwd_uses_process_cwd(self):
        with mock.patch.object(Path, "cwd", return_value=self.project):
            self.rt.handle(self.agent, {"hook_event_name": "Stop",
                                        "last_assistant_message": "x"})
        self.assertEqual(self.projects(), {str(self.project)})

    def test_memory_scope_isolates_identities_sharing_a_cwd(self):
        scope = "gateway-" + "z" * 300
        self.rt.handle(self.agent, self.event(
            "UserPromptSubmit", prompt="scoped note", memory_scope=scope))
        self.assertEqual(self.projects(), {f"{self.project}#{scope[:200]}"})
        self.assertEqual(self.rt.handle(self.agent, self.event("SessionStart")), "")
        recall = self.rt.handle(self.agent, self.event(
            "SessionStart", memory_scope=scope))
        self.assertIn("scoped note", recall)

    def test_agents_do_not_share_notes(self):
        self.rt.handle("claude-code", self.event("UserPromptSubmit", prompt="mine"))
        self.assertEqual(self.rt.handle("codex", self.event("SessionStart")), "")


class HandlePromptTests(_RuntimeCase):
    def setUp(self):
        super().setUp()
        self.fake_observer("")
        self.fake_skills([{"name": "card", "description": "matched"}])

    def test_prompt_is_saved_redacted_with_ttl_and_cards_returned(self):
        secret = "sk-ant-" + "Q" * 30
        out = self.rt.handle(self.agent, self.event(
            "UserPromptSubmit", prompt=f"deploy with {secret}"))
        self.assertIn("- card: matched", out)
        (row,) = self.rows()
        agent, project, mtype, key, value, metadata, expires = row
        self.assertEqual((agent, project, mtype), (self.agent, str(self.project),
                                                   "session_context"))
        self.assertEqual(key, f"session:{session_key('sess-1')}:task")
        self.assertEqual(value, "deploy with [redacted]")
        self.assertIsNone(metadata)
        self.assertIsNotNone(expires)
        # The loader still sees the raw prompt; only persistence is redacted.
        self.assertEqual(self.calls(self.loader_log)[0]["prompt"],
                         f"deploy with {secret}")

    def test_saved_prompt_is_truncated_and_upserted_per_session(self):
        self.rt.handle(self.agent, self.event("UserPromptSubmit", prompt="first"))
        self.rt.handle(self.agent, self.event("UserPromptSubmit",
                                              prompt="y" * 5000))
        (row,) = self.rows()
        self.assertEqual(row[4], "y" * self.rt.MAX_MEMORY)

    def test_missing_prompt_and_session_are_tolerated(self):
        self.fake_skills([])
        out = self.rt.handle(self.agent, {"hook_event_name": "UserPromptSubmit",
                                          "cwd": str(self.project), "prompt": None})
        self.assertEqual(out, "")
        (row,) = self.rows()
        self.assertEqual(row[3], f"session:{session_key('unknown')}:task")
        self.assertEqual(row[4], "")

    def test_session_id_is_truncated_before_hashing(self):
        base = "s" * 200
        self.rt.handle(self.agent, self.event("UserPromptSubmit", session_id=base + "A",
                                              prompt="one"))
        self.rt.handle(self.agent, self.event("UserPromptSubmit", session_id=base + "B",
                                              prompt="two"))
        (row,) = self.rows()
        self.assertEqual(row[3], f"session:{session_key(base)}:task")
        self.assertEqual(row[4], "two")

    def test_returned_context_is_capped(self):
        with mock.patch.object(self.rt, "prompt_context",
                               return_value="c" * (self.rt.MAX_CONTEXT + 500)) as pc:
            out = self.rt.handle(self.agent, self.event("UserPromptSubmit",
                                                        prompt="p"))
        self.assertEqual(len(out), self.rt.MAX_CONTEXT)
        pc.assert_called_once()
        self.assertEqual(pc.call_args.args[:2], (self.agent, "p"))


class HandleToolAndStopTests(_RuntimeCase):
    def setUp(self):
        super().setUp()
        self.fake_observer("")
        self.fake_skills([])

    def test_tool_events_record_only_a_bounded_tool_name(self):
        secret = "ghp_" + "S" * 36
        for name in ("PreToolUse", "PostToolUse"):
            out = self.rt.handle(self.agent, self.event(
                name, tool_name="Bash" + "x" * 200,
                tool_input={"command": f"echo {secret}"},
                tool_response={"stdout": "private source"}))
            self.assertEqual(out, "")
            (row,) = self.rows()
            self.assertEqual(row[3], f"session:{session_key('sess-1')}:last_tool")
            self.assertEqual(row[4], ("Bash" + "x" * 200)[:100])
            self.assertEqual(json.loads(row[5]), {"event": name})
            self.assertIsNotNone(row[6])
        database = Path(self.env["AGENT_MEMORY_ROOT"]) / "memory.db"
        raw = database.read_bytes()
        self.assertNotIn(secret.encode(), raw)
        self.assertNotIn(b"private source", raw)

    def test_tool_event_without_name_records_unknown(self):
        self.rt.handle(self.agent, self.event("PostToolUse"))
        self.assertEqual(self.rows()[0][4], "unknown")

    def test_stop_saves_redacted_summary_and_runs_backstop(self):
        secret = "AKIA" + "ABCDEFGHIJKLMNOP"
        out = self.rt.handle(self.agent, self.event(
            "Stop", last_assistant_message=f"used {secret} " + "z" * 2000))
        self.assertEqual(out, "")
        (row,) = self.rows()
        self.assertEqual(row[3], f"session:{session_key('sess-1')}:summary")
        self.assertTrue(row[4].startswith("used [redacted] "))
        self.assertEqual(len(row[4]), self.rt.MAX_MEMORY)
        self.assertEqual(self.calls(self.observer_log), [{
            "call": "stop", "root": self.env["TASK_OBSERVER_WORKSPACE"],
            "session": session_key("sess-1")}])

    def test_stop_without_usable_message_saves_nothing_but_still_checkpoints(self):
        for message in (None, "", "   \n", 42, ["list"]):
            self.rt.handle(self.agent, self.event(
                "Stop", last_assistant_message=message))
        self.assertEqual(self.rows(), [])
        self.assertEqual(len(self.calls(self.observer_log)), 5)

    def test_backstop_failure_is_swallowed(self):
        for fail in ("stop", "root"):
            self.fake_observer(fail=fail)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(self.rt.handle(self.agent, self.event(
                    "Stop", last_assistant_message="ok")), "")
            self.assertEqual(err.getvalue(), "")
        self.assertEqual(len(self.rows()), 1)

    def test_real_backstop_writes_into_the_isolated_workspace(self):
        self.redirects.pop("ae_task_observer", None)
        self.rt.handle(self.agent, self.event("Stop", last_assistant_message="ok"))
        workspace = Path(self.env["TASK_OBSERVER_WORKSPACE"])
        for path in workspace.rglob("*") if workspace.exists() else ():
            self.assertTrue(path.resolve().is_relative_to(self.root))

    def test_unknown_event_only_runs_ttl_cleanup(self):
        memory = sys.modules["memory"].AgentMemory("other-agent", "elsewhere")
        memory.save("stale", "v", ttl_days=-1)
        memory.save("live", "v", ttl_days=1)
        for name in ("Notification", "", None):
            self.assertEqual(self.rt.handle(self.agent, self.event(name)), "")
        self.assertEqual([r[3] for r in self.rows()], ["live"])
        self.assertEqual(self.calls(self.observer_log), [])


class MainTests(_RuntimeCase):
    def setUp(self):
        super().setUp()
        self.fake_observer("")
        self.fake_skills([{"name": "card", "description": "matched"}])

    def main(self, stdin, *argv, agent=None):
        out, err = io.StringIO(), io.StringIO()
        argv = ["runtime.py", agent or self.agent, *argv]
        with mock.patch.dict(os.environ), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(sys, "stdin", io.StringIO(stdin)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.rt.main()
        return out.getvalue(), err.getvalue()

    def test_native_json_envelope_for_prompt_context(self):
        out, err = self.main(json.dumps(self.event("UserPromptSubmit", prompt="p")))
        self.assertEqual(err, "")
        payload = json.loads(out)
        self.assertEqual(list(payload), ["hookSpecificOutput"])
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"],
                         "UserPromptSubmit")
        self.assertIn("- card: matched",
                      payload["hookSpecificOutput"]["additionalContext"])

    def test_text_mode_prints_plain_context(self):
        out, _ = self.main(json.dumps(self.event("UserPromptSubmit", prompt="p")),
                           "--text")
        self.assertTrue(out.startswith("AgentEnhancements local skill candidates"))
        self.assertTrue(out.endswith("- card: matched\n"))

    def test_session_start_envelope_names_the_event(self):
        self.fake_observer("OBS")
        out, _ = self.main(json.dumps(self.event("SessionStart")))
        self.assertEqual(json.loads(out), {"hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": "OBS"}})

    def test_empty_context_is_silent_except_native_stop_ack(self):
        tool = json.dumps(self.event("PreToolUse", tool_name="Read"))
        self.assertEqual(self.main(tool), ("", ""))
        self.assertEqual(self.main(tool, "--text"), ("", ""))
        stop = json.dumps(self.event("Stop"))
        self.assertEqual(self.main(stop), ("{}\n", ""))
        self.assertEqual(self.main(stop, "--text"), ("", ""))
        self.fake_skills([])
        prompt = json.dumps(self.event("UserPromptSubmit", prompt="p"))
        self.assertEqual(self.main(prompt), ("", ""))

    def test_bridge_envelope_reuses_context_when_not_a_preflight_package(self):
        prompt = json.dumps(self.event("UserPromptSubmit", prompt="p"))
        out, _ = self.main(prompt, "--bridge", "--text", agent="opencode")
        envelope = json.loads(out)
        self.assertEqual(set(envelope), {"context", "fallback"})
        self.assertIn("- card: matched", envelope["context"])
        self.assertEqual(envelope["fallback"], envelope["context"])
        self.assertEqual(len(self.calls(self.loader_log)), 1)
        out, _ = self.main(json.dumps(self.event("Stop")), "--bridge",
                           agent="opencode")
        self.assertEqual(json.loads(out), {"context": "", "fallback": ""})

    def test_bridge_preflight_package_carries_legacy_fallback(self):
        package = "AgentEnhancements preflight (mode 2): selected"
        with mock.patch.object(self.rt, "handle", return_value=package) as handle, \
                mock.patch.object(self.rt, "skill_context",
                                  return_value="LEGACY") as legacy:
            out, _ = self.main(json.dumps(self.event(
                "UserPromptSubmit", prompt="the prompt")), "--bridge",
                agent="opencode")
            # Same package text on a non-prompt event is passed through.
            out2, _ = self.main(json.dumps(self.event("SessionStart")),
                                "--bridge", agent="opencode")
        self.assertEqual(json.loads(out), {"context": package, "fallback": "LEGACY"})
        self.assertEqual(json.loads(out2), {"context": package, "fallback": package})
        legacy.assert_called_once_with("opencode", "the prompt")
        self.assertEqual(handle.call_count, 2)

    def test_project_environment_is_applied_before_handling(self):
        seen = {}

        def capture(agent, event):
            seen.update(agent=agent, event=event, env=dict(os.environ))
            return ""

        with mock.patch.object(self.rt, "handle", side_effect=capture):
            self.main(json.dumps(self.event("Notification")), agent="hermes")
        state = Path(self.env["AGENT_ENHANCEMENTS_STATE_DIR"])
        self.assertEqual(seen["agent"], "hermes")
        self.assertEqual(seen["event"]["hook_event_name"], "Notification")
        self.assertEqual(seen["env"]["XDG_CACHE_HOME"], str(state / "cache"))
        self.assertEqual(seen["env"]["TMPDIR"], str(state / "cache" / "tmp"))
        self.assertEqual(seen["env"]["AGENT_MEMORY_ROOT"],
                         self.env["AGENT_MEMORY_ROOT"])
        self.assertEqual(state.stat().st_mode & 0o777, 0o700)

    def test_input_exactly_at_the_limit_is_accepted(self):
        body = json.dumps(self.event("PreToolUse", tool_name="Edit"))
        padded = body + " " * (self.rt.MAX_INPUT - len(body))
        self.assertEqual(len(padded), self.rt.MAX_INPUT)
        self.assertEqual(self.main(padded), ("", ""))
        self.assertEqual(self.rows()[0][4], "Edit")

    def test_bad_input_is_skipped_with_type_only_diagnostic(self):
        cases = {
            " " * (self.rt.MAX_INPUT + 1): "ValueError",
            "[1, 2]": "ValueError",
            "null": "ValueError",
            "{not json": "JSONDecodeError",
            "": "JSONDecodeError",
        }
        for stdin, exc_name in cases.items():
            out, err = self.main(stdin)
            self.assertEqual(out, "", exc_name)
            self.assertEqual(err, f"[AgentEnhancements] hook skipped: {exc_name}\n")
        self.assertEqual(self.rows(), [])

    def test_handler_errors_never_escape(self):
        with mock.patch.object(self.rt, "handle",
                               side_effect=sqlite3.OperationalError("locked /x")):
            out, err = self.main(json.dumps(self.event("Stop")))
        self.assertEqual(out, "")
        self.assertEqual(err, "[AgentEnhancements] hook skipped: OperationalError\n")
        self.assertNotIn("locked", err)

    def test_non_string_cwd_is_skipped_not_raised(self):
        out, err = self.main(json.dumps(self.event("Stop", cwd=123)))
        self.assertEqual(out, "")
        self.assertIn("hook skipped: TypeError", err)

    def test_unknown_agent_is_rejected_by_argparse(self):
        with self.assertRaises(SystemExit) as raised:
            self.main("{}", agent="vim")
        self.assertEqual(raised.exception.code, 2)


class CommandLineTests(unittest.TestCase):
    """Run runtime.py as the hosts do: a fresh interpreter per event."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name).resolve()
        (root / "project").mkdir()
        api = root / "ui.api.json"
        api.write_text(json.dumps(
            {"version": 1, "api_keys": {}, "connections": {}, "mcp": {}}))
        self.cwd = str(root / "project")
        self.memory_db = root / "memory" / "memory.db"
        self.env = {
            "AGENT_ENHANCEMENTS_STATE_DIR": str(root / "ae-state"),
            "AGENT_MEMORY_ROOT": str(root / "memory"),
            "AGENT_ENHANCEMENTS_API_FILE": str(api),
            "TASK_OBSERVER_WORKSPACE": str(root / "observer"),
            "HOME": str(root / "home"),
            "XDG_CONFIG_HOME": str(root / "home" / ".config"),
        }

    def hook(self, event, *flags):
        payload = {"session_id": "cli", "cwd": self.cwd}
        payload.update(event)
        return run([sys.executable, str(RUNTIME), "claude-code", *flags],
                   env=self.env, input_text=json.dumps(payload))

    def test_stop_then_session_start_recalls_across_processes(self):
        rc, out, err = self.hook({"hook_event_name": "Stop",
                                  "last_assistant_message": "shipped the fix"})
        self.assertEqual((rc, out), (0, "{}\n"), err)
        self.assertNotIn("hook skipped", err)
        rc, out, err = self.hook({"hook_event_name": "SessionStart",
                                  "session_id": "next"}, "--text")
        self.assertEqual(rc, 0, err)
        self.assertIn(f"- session:{session_key('cli')}:summary: shipped the fix",
                      out)
        self.assertTrue(self.memory_db.is_file())
        self.assertEqual(self.memory_db.stat().st_mode & 0o777, 0o600)

    def test_invalid_agent_exits_with_usage_error(self):
        rc, out, err = run([sys.executable, str(RUNTIME), "vim"],
                           env=self.env, input_text="{}")
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertIn("invalid choice", err)


if __name__ == "__main__":
    unittest.main()
