"""Regressions for setup.sh and the shared memory/compression utilities.

Covers: redaction before truncation in memory recall, the memory.py CLI
contract, the non-regular memory database guard, compress.py byte safety,
merge_agents_md marker validation, the OpenCode 2 precheck, portable sed
use, the Python version floor and the universal prompt's host claims.
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module

SCRIPTS = UI_DIR / "scripts"
SETUP = UI_DIR / "setup.sh"
BASH = shutil.which("bash") or "/bin/bash"


def shell_function(name: str) -> str:
    """Extract one top-level bash function definition from setup.sh."""
    match = re.search(r"^" + re.escape(name) + r"\(\) \{\n.*?^\}\n",
                      SETUP.read_text(), re.DOTALL | re.MULTILINE)
    if match is None:
        raise AssertionError(f"{name} not found in setup.sh")
    return match.group(0)


class IsolatedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = dict(os.environ)
        self.env.update({
            "HOME": str(self.root / "home"),
            "AGENT_MEMORY_ROOT": str(self.root / "memory"),
            "AGENT_ENHANCEMENTS_API_FILE": str(self.root / "ui.api.json"),
            "TASK_OBSERVER_WORKSPACE": str(self.root / "observer"),
            "XDG_CONFIG_HOME": str(self.root / "xdg"),
        })
        (self.root / "home").mkdir()

    def run_cmd(self, cmd, input_bytes=None, cwd=None, env=None):
        return subprocess.run(cmd, input=input_bytes, capture_output=True,
                              env=env or self.env, cwd=cwd or str(self.root),
                              timeout=60)


class MemoryRecallRedactionTests(IsolatedTest):
    # Deliberately shaped so SECRET_PATTERN does not recognize it: only the
    # configured-key redaction can remove it, and only when it is whole.
    KEY = "Zq7Lm2Xr9Pw4Ty6Hb3Nc8Vd1Kf5Gs0Jh2Qa7We4R"

    def setUp(self):
        super().setUp()
        Path(self.env["AGENT_ENHANCEMENTS_API_FILE"]).write_text(json.dumps({
            "version": 1, "api_keys": {"FIXTURE_KEY": self.KEY},
            "connections": {}, "mcp": {},
        }))
        self.value = "x" * 180 + self.KEY + " trailing note"

    def assert_no_key_prefix(self, text):
        for size in range(8, len(self.KEY) + 1):
            self.assertNotIn(self.KEY[:size], text)

    def test_list_redacts_before_truncating(self):
        with mock.patch.dict(os.environ, self.env):
            memory = load_module("setup_family_memory_redact", SCRIPTS / "memory.py")
            store = memory.AgentMemory("claude-code", project="fixture")
            store.save("note", self.value)
            items = store.list("session_context")
        self.assertEqual(len(items), 1)
        self.assertIn("[redacted]", items[0]["value"])
        self.assert_no_key_prefix(items[0]["value"])

    def test_session_start_recall_never_leaks_a_key_prefix(self):
        project = self.root / "project"
        project.mkdir()
        code = (
            "import json, sys\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "from memory import AgentMemory\n"
            "import runtime\n"
            f"AgentMemory('claude', project={str(project.resolve())!r})"
            f".save('note', {self.value!r})\n"
            "print(runtime.handle('claude', {'hook_event_name': 'SessionStart',"
            f" 'session_id': 's1', 'cwd': {str(project)!r}}}))\n"
        )
        proc = self.run_cmd([sys.executable, "-c", code])
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = proc.stdout.decode()
        self.assertIn("previous local session notes", out)
        self.assert_no_key_prefix(out)


class MemoryCliTests(IsolatedTest):
    def cli(self, *args):
        proc = self.run_cmd([sys.executable, str(SCRIPTS / "memory.py"), *args])
        return proc.returncode, proc.stdout.decode(), proc.stderr.decode()

    def test_save_load_roundtrip_including_empty_value(self):
        self.assertEqual(self.cli("claude-code", "save", "k", "hello")[0], 0)
        self.assertEqual(self.cli("claude-code", "load", "k")[:2], (0, "hello\n"))
        rc, out, _ = self.cli("claude-code", "save", "empty", "")
        self.assertEqual((rc, out), (0, "Saved: empty (session_context)\n"))
        self.assertEqual(self.cli("claude-code", "load", "empty")[:2], (0, "\n"))

    def test_list_output_format(self):
        self.cli("claude-code", "save", "k1", "v1", "user_preferences")
        rc, out, _ = self.cli("claude-code", "list", "user_preferences", "5")
        self.assertEqual(rc, 0)
        self.assertRegex(out, r"^\[user_preferences\] k1: v1 \(updated: .+\)\n$")

    def test_delete_present_and_missing(self):
        self.cli("claude-code", "save", "k", "v")
        self.assertEqual(self.cli("claude-code", "delete", "k")[:2], (0, "Deleted: k\n"))
        self.assertEqual(self.cli("claude-code", "delete", "k")[:2], (0, "Not found: k\n"))

    def test_non_positive_ttl_is_rejected_and_keeps_existing_record(self):
        """ttl 0 used to overwrite a live row with an expired one while
        reporting success; the hooks treated 0 as "never expire"."""
        self.cli("claude-code", "save", "k", "live")
        for ttl in ("0", "-1"):
            with self.subTest(ttl=ttl):
                rc, out, err = self.cli("claude-code", "save", "k", "gone",
                                        "session_context", ttl)
                self.assertEqual(rc, 1)
                self.assertNotIn("Saved", out)
                self.assertNotIn("Traceback", err)
        self.assertEqual(self.cli("claude-code", "load", "k")[:2], (0, "live\n"))
        rc, out, _ = self.cli("claude-code", "cleanup")
        self.assertEqual((rc, out), (0, "Cleaned up 0 expired memories\n"))

    def test_invalid_arguments_exit_without_traceback(self):
        cases = [
            ("claude-code",),
            ("claude-code", "bogus"),
            ("claude-code", "save", "k"),
            ("claude-code", "save", "k", "v", "session_context", "soon"),
            ("claude-code", "list", "session_context", "many"),
            ("claude-code", "save", "k", "v", "session_context", "3000000"),
            ("claude-code", "save", "k", "v", "session_context", "99999999999"),
            ("claude-code", "list", "session_context", "-1"),
            ("claude-code", "list", "session_context", "0"),
        ]
        for args in cases:
            with self.subTest(args=args):
                rc, out, err = self.cli(*args)
                self.assertEqual(rc, 1)
                self.assertNotIn("Traceback", err)
                self.assertTrue(out.strip())


class MemoryDatabaseGuardTests(IsolatedTest):
    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX file types required")
    def test_memory_database_rejects_non_regular_file(self):
        directory = Path(self.env["AGENT_MEMORY_ROOT"])
        directory.mkdir()
        os.mkfifo(directory / "memory.db")
        with mock.patch.dict(os.environ, self.env):
            memory = load_module("setup_family_memory_fifo", SCRIPTS / "memory.py")
            with self.assertRaisesRegex(OSError, "regular file"):
                memory.AgentMemory("codex", project="fixture")
        self.assertTrue(stat.S_ISFIFO((directory / "memory.db").lstat().st_mode))


class MemoryHookCliTests(IsolatedTest):
    """The per-agent hooks write the same table as memory.py and must agree
    with it on what a TTL means and which arguments are valid."""

    def hook(self, *args):
        script = UI_DIR / "memory" / "hooks" / "codex-memory-hook.py"
        proc = self.run_cmd([sys.executable, str(script), *args])
        return proc.returncode, proc.stdout.decode(), proc.stderr.decode()

    def memory_cli(self, *args):
        proc = self.run_cmd([sys.executable, str(SCRIPTS / "memory.py"), *args])
        return proc.returncode, proc.stdout.decode(), proc.stderr.decode()

    def test_invalid_ttl_and_limit_exit_without_traceback(self):
        project = str(self.root.resolve())
        self.assertEqual(self.hook("save", "k", "live", "session_context", project)[0], 0)
        cases = [
            ("save", "k", "gone", "session_context", project, "0"),
            ("save", "k", "gone", "session_context", project, "-1"),
            ("save", "k", "gone", "session_context", project, "soon"),
            ("save", "k", "gone", "session_context", project, "3000000"),
            ("save", "k", "gone", "session_context", project, "99999999999"),
            ("list", "session_context", project, "-1"),
            ("list", "session_context", project, "0"),
            ("list", "session_context", project, "many"),
        ]
        for args in cases:
            with self.subTest(args=args):
                rc, out, err = self.hook(*args)
                self.assertEqual(rc, 1)
                self.assertNotIn("Traceback", err)
                self.assertNotIn("Saved", out)
                self.assertTrue(out.strip())
        self.assertEqual(self.hook("load", "k", "session_context", project)[:2],
                         (0, "live\n"))

    def test_hook_and_memory_cli_agree_on_ttl(self):
        project = str(self.root.resolve())
        for ttl in ("0", "-1", "36501"):
            with self.subTest(ttl=ttl):
                hook_rc = self.hook("save", "h", "v", "session_context", project, ttl)[0]
                cli_rc = self.memory_cli("codex", "save", "m", "v", "session_context", ttl)[0]
                self.assertEqual((hook_rc, cli_rc), (1, 1))
        self.assertEqual(self.hook("save", "h", "v", "session_context", project, "2")[0], 0)
        self.assertEqual(self.memory_cli("codex", "save", "m", "v", "session_context", "2")[0], 0)
        self.assertEqual(self.hook("load", "m", "session_context", project)[:2], (0, "v\n"))
        self.assertEqual(self.memory_cli("codex", "load", "h")[:2], (0, "v\n"))

    def test_hook_save_function_rejects_overflowing_ttl(self):
        with mock.patch.dict(os.environ, self.env):
            hook = load_module("setup_family_hook_ttl",
                               UI_DIR / "memory" / "hooks" / "codex-memory-hook.py")
            hook.init_db()
            with self.assertRaises(ValueError):
                hook.save_memory("k", "v", project="p", ttl_days=99_999_999_999)
            hook.save_memory("expired", "v", project="p", ttl_days=0)
            self.assertIsNone(hook.load_memory("expired", project="p"))


class LauncherStateEnvironmentTests(IsolatedTest):
    """launch-agent.sh must not exec the agent when the AE state
    environment cannot be prepared: eval "$(failing)" returns 0."""

    def setUp(self):
        super().setUp()
        self.unified = self.root / "ae" / "unified-integration"
        (self.unified / "scripts").mkdir(parents=True)
        (self.unified / "config").mkdir()
        shutil.copy2(UI_DIR / "launch-agent.sh", self.unified / "launch-agent.sh")
        shutil.copy2(SCRIPTS / "project_paths.py", self.unified / "scripts" / "project_paths.py")
        (self.unified / "config" / "detected-agents.sh").write_text("AGENTS=(claude-code)\n")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.marker = self.root / "agent-ran"
        stub = self.bin / "claude"
        stub.write_text(f"#!/bin/sh\ntouch {str(self.marker)!r}\n")
        stub.chmod(0o755)
        self.env.pop("AGENT_ENHANCEMENTS_UNIFIED_DIR", None)
        self.env.pop("AGENT_ENHANCEMENTS_BASE_DIR", None)
        self.env["PATH"] = str(self.bin) + os.pathsep + self.env.get("PATH", "")

    def launch(self, state_dir):
        self.env["AGENT_ENHANCEMENTS_STATE_DIR"] = state_dir
        proc = self.run_cmd([BASH, str(self.unified / "launch-agent.sh"), "claude-code"])
        return proc.returncode, proc.stderr.decode()

    def test_relative_state_dir_refuses_to_launch(self):
        rc, err = self.launch("relative/x")
        self.assertNotEqual(rc, 0)
        self.assertIn("AE state environment unavailable", err)
        self.assertFalse(self.marker.exists())

    def test_symlinked_state_dir_refuses_to_launch(self):
        real = self.root / "real-state"
        real.mkdir()
        link = self.root / "linked-state"
        link.symlink_to(real, target_is_directory=True)
        rc, err = self.launch(str(link))
        self.assertNotEqual(rc, 0)
        self.assertIn("AE state environment unavailable", err)
        self.assertFalse(self.marker.exists())

    def test_valid_state_dir_still_launches(self):
        rc, err = self.launch(str(self.root / "state"))
        self.assertEqual(rc, 0, err)
        self.assertTrue(self.marker.exists())


class CompressByteSafetyTests(IsolatedTest):
    def setUp(self):
        super().setUp()
        # Point the repo-built fallback binary somewhere empty so the Python
        # fallback runs unless a test supplies HEADROOM_BIN.
        self.env["AGENT_ENHANCEMENTS_BASE_DIR"] = str(self.root / "no-headroom")
        self.env["HEADROOM_BIN"] = str(self.root / "missing-headroom")

    def compress(self, payload, mode):
        return self.run_cmd(
            ["bash", str(UI_DIR / "compression" / "compress.sh"), "-", mode],
            input_bytes=payload,
        )

    def test_invalid_utf8_input_does_not_crash(self):
        proc = self.compress(b"abc\xff\xfe def\n", "auto")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"def", proc.stdout)
        self.assertNotIn(b"Traceback", proc.stderr)

    def test_fallback_output_is_byte_exact(self):
        for payload in (b"", b"a\n\nb", b"line1\n\n\nline2\n"):
            with self.subTest(payload=payload):
                proc = self.compress(payload, "code")
                self.assertEqual(proc.returncode, 0, proc.stderr.decode())
                self.assertEqual(proc.stdout, payload)

    def test_headroom_trailing_newline_is_not_duplicated(self):
        stub = self.root / "headroom-stub"
        # Behaves like the headroom CLI: echoes input, terminated by println!.
        stub.write_text("#!/bin/sh\ncat\nprintf '\\n'\n")
        stub.chmod(0o755)
        self.env["HEADROOM_BIN"] = str(stub)
        for payload in (b"", b"line1\n\n\nline2\n"):
            with self.subTest(payload=payload):
                proc = self.compress(payload, "code")
                self.assertEqual(proc.returncode, 0, proc.stderr.decode())
                self.assertEqual(proc.stdout, payload)


class MergeAgentsMdTests(IsolatedTest):
    BEGIN = "<!-- agent-enhancements:begin -->"
    END = "<!-- agent-enhancements:end -->"

    def merge(self, existing):
        target = self.root / "CLAUDE.md"
        if existing is None:
            target.unlink(missing_ok=True)
        else:
            target.write_text(existing)
        section = self.root / "section.md"
        section.write_text("AE SECTION\n")
        script = (
            "set -euo pipefail\n"
            "log_warn() { echo \"[WARN] $1\" >&2; }\n"
            + shell_function("merge_agents_md")
            + 'merge_agents_md "$1" "$2"\necho done\n'
        )
        proc = self.run_cmd(["bash", "-c", script, "merge", str(target), str(section)])
        return proc, target

    def test_unbalanced_or_ambiguous_markers_leave_file_unchanged(self):
        cases = {
            "orphan begin": f"intro\n{self.BEGIN}\nMY PERSONAL RULES\nkeep me\n",
            "orphan end": f"intro\n{self.END}\nkeep me\n",
            "reversed": f"{self.END}\nkeep me\n{self.BEGIN}\n",
            "duplicate": f"{self.BEGIN}\na\n{self.END}\nkeep\n{self.BEGIN}\nb\n{self.END}\n",
        }
        for label, existing in cases.items():
            with self.subTest(case=label):
                proc, target = self.merge(existing)
                self.assertEqual(proc.returncode, 0, proc.stderr.decode())
                self.assertIn(b"done", proc.stdout)
                self.assertIn(b"unbalanced agent-enhancements markers", proc.stderr)
                self.assertEqual(target.read_text(), existing)
                self.assertEqual(list(self.root.glob("CLAUDE.md.backup.*")), [])

    def test_well_formed_markers_still_merge(self):
        proc, target = self.merge(f"intro\n{self.BEGIN}\nold\n{self.END}\noutro\n")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(target.read_text(),
                         f"intro\n{self.BEGIN}\nAE SECTION\n{self.END}\noutro\n")
        proc, target = self.merge("mine\n")
        self.assertEqual(target.read_text(), f"mine\n\n{self.BEGIN}\nAE SECTION\n{self.END}\n")
        proc, target = self.merge(None)
        self.assertEqual(target.read_text(), f"{self.BEGIN}\nAE SECTION\n{self.END}\n")

    def test_symlinked_target_stays_a_symlink(self):
        dotfiles = self.root / "dotfiles"
        dotfiles.mkdir()
        real = dotfiles / "CLAUDE.md"
        real.write_text("mine\n")
        link = self.root / "CLAUDE.md"
        link.unlink(missing_ok=True)
        link.symlink_to(real)
        section = self.root / "section.md"
        section.write_text("AE SECTION\n")
        script = (
            "set -euo pipefail\n"
            "log_warn() { echo \"[WARN] $1\" >&2; }\n"
            + shell_function("merge_agents_md")
            + 'merge_agents_md "$1" "$2"\n'
        )
        proc = self.run_cmd(["bash", "-c", script, "merge", str(link), str(section)])
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), str(real))
        self.assertEqual(real.read_text(),
                         f"mine\n\n{self.BEGIN}\nAE SECTION\n{self.END}\n")
        # The backup sits next to the real file, not beside the link.
        self.assertEqual(len(list(dotfiles.glob("CLAUDE.md.backup.*"))), 1)
        self.assertEqual(list(self.root.glob("CLAUDE.md.backup.*")), [])
        self.assertEqual(list(dotfiles.glob(".instructions.*")), [])


class OpenCodePrecheckTests(IsolatedTest):
    def run_create(self, version_output):
        bin_dir = self.root / "bin"
        bin_dir.mkdir(exist_ok=True)
        if version_output is not None:
            stub = bin_dir / "opencode"
            stub.write_text(f"#!/bin/sh\necho '{version_output}'\n")
            stub.chmod(0o755)
        # Only the utilities the function needs, so an opencode installed in
        # a system directory cannot leak into the fixture.
        tools = self.root / "tools"
        tools.mkdir(exist_ok=True)
        for tool in ("mkdir", "mktemp", "rm"):
            link = tools / tool
            if not link.exists():
                link.symlink_to(shutil.which(tool))
        env = dict(self.env)
        env["PATH"] = f"{bin_dir}:{tools}"
        env["PYTHON_FOR_TEST"] = sys.executable
        script = (
            "set -euo pipefail\n"
            'python3() { "$PYTHON_FOR_TEST" "$@"; }\n'
            "log_warn() { echo \"[WARN] $1\" >&2; }\n"
            "render_native_library_instructions() { echo section; }\n"
            "merge_agents_md() { echo \"merge $1\"; }\n"
            + shell_function("opencode_cli_supported")
            + shell_function("create_opencode_config").replace(
                'python3 "$UNIFIED_DIR/scripts/native-integration.py" --agent opencode',
                'echo native-opencode')
            + "create_opencode_config\necho after\n"
        )
        proc = self.run_cmd([BASH, "-c", script], env=env)
        return proc, Path(env["XDG_CONFIG_HOME"]) / "opencode"

    def test_opencode_1_is_skipped_before_any_change(self):
        proc, config_dir = self.run_create("1.17.14")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"OpenCode 2 is required", proc.stderr)
        self.assertNotIn(b"merge", proc.stdout)
        self.assertNotIn(b"native-opencode", proc.stdout)
        self.assertIn(b"after", proc.stdout)
        self.assertFalse(config_dir.exists())

    def test_opencode_2_and_absent_cli_are_configured(self):
        for version in ("opencode v2.3.0", "2.2.5", None):
            with self.subTest(version=version):
                for item in (self.root / "bin").glob("*"):
                    item.unlink()
                proc, _ = self.run_create(version)
                self.assertEqual(proc.returncode, 0, proc.stderr.decode())
                self.assertIn(b"merge", proc.stdout)
                self.assertIn(b"native-opencode", proc.stdout)


class SetupPortabilityTests(unittest.TestCase):
    def test_no_gnu_only_in_place_sed(self):
        self.assertNotRegex(SETUP.read_text(), r"\bsed -i\b")


class RuntimePythonFloorTests(unittest.TestCase):
    def test_old_interpreter_is_refused_before_preparing(self):
        module = load_module("setup_family_runtime_dependencies",
                             SCRIPTS / "runtime_dependencies.py")
        with mock.patch.object(sys, "argv", ["runtime_dependencies.py"]), \
                mock.patch.object(sys, "version_info", (3, 9, 6, "final", 0)), \
                mock.patch.object(module, "prepare") as prepare, \
                mock.patch("sys.stderr") as stderr:
            self.assertEqual(module.main(), 1)
        prepare.assert_not_called()
        written = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("Python >= 3.11 is required", written)


class UniversalPromptTests(unittest.TestCase):
    def test_host_parity_claims_match_readme(self):
        prompt = (UI_DIR / "prompts" / "universal-system-prompt.txt").read_text()
        self.assertNotIn("Compatible with:", prompt)
        self.assertNotIn("Works with:", prompt)
        self.assertIn("Native lifecycle integration: Claude Code, Codex, OpenCode 2", prompt)
        self.assertIn("Hermes", prompt)
        self.assertIn("Reference configs only: Cursor, Gemini CLI, Copilot, Windsurf, Kiro",
                      prompt)


if __name__ == "__main__":
    unittest.main()
