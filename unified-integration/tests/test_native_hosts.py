"""Behavioral regressions for portable installation and real CLI fixtures."""

import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from helpers import UI_DIR, load_module


class NativeHostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ae host's ")
        self.home = Path(self.tmp.name)
        self.env = {**os.environ, "HOME": str(self.home),
                    "XDG_CONFIG_HOME": str(self.home / ".config"),
                    "XDG_DATA_HOME": str(self.home / ".local/share"),
                    "HERMES_HOME": str(self.home / ".hermes"),
                    "AGENT_ENHANCEMENTS_API_FILE": str(self.home / "api.json")}

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, agent, *args):
        result = subprocess.run(
            [sys.executable, str(UI_DIR / "scripts/native-integration.py"),
             "--agent", agent, *args], env=self.env, capture_output=True,
            text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_hermes_selection_preserves_siblings_and_repairs_missing_default(self):
        import yaml
        root = self.home / ".hermes"
        for name in ("ilma", "master-chief", "untouched"):
            path = root / "profiles" / name
            path.mkdir(parents=True)
            (path / "config.yaml").write_text('model:\n  provider: owner\n  default: personal\n')
            (path / "SOUL.md").write_text("Personal identity.\n")
        (root / "active_profile").write_text("missing\n")
        sibling = root / "profiles/untouched/config.yaml"
        original = sibling.read_bytes()
        self.install("hermes", "--profile", "ilma", "--profile", "master-chief")
        self.install("hermes")  # selection survives the next ordinary setup
        self.assertEqual(sibling.read_bytes(), original)
        self.assertFalse((root / "config.yaml").exists())
        self.assertEqual((root / "active_profile").read_text().strip(), "ilma")
        for name in ("ilma", "master-chief"):
            doc = yaml.safe_load((root / "profiles" / name / "config.yaml").read_text())
            self.assertEqual(doc["model"]["provider"], "owner")
            self.assertIn("agent-enhancements", doc["mcp_servers"])
            self.assertIn("agent-enhancements", doc["plugins"]["enabled"])
            self.assertTrue((root / "profiles" / name / "plugins/agent-enhancements/__init__.py").is_file())
            note = (root / "profiles" / name / "SOUL.md").read_text()
            self.assertTrue(note.startswith("Personal identity.\n"))
            self.assertEqual(note.count("<!-- agent-enhancements:begin -->"), 1)

    def test_opencode_v1_refused_before_changing_user_config(self):
        binary = self.home / "bin/opencode"
        binary.parent.mkdir()
        binary.write_text('#!/bin/sh\nprintf "1.17.14\\n"\n')
        binary.chmod(0o700)
        path = self.home / ".config/opencode/opencode.jsonc"
        path.parent.mkdir(parents=True)
        original = '{"model":"owner/model"}\n'
        path.write_text(original)
        result = subprocess.run([sys.executable, str(UI_DIR / "scripts/native-integration.py"),
                                 "--agent", "opencode"], env={**self.env,
                                 "PATH": str(binary.parent) + os.pathsep + os.environ["PATH"]},
                                capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OpenCode 2 is required", result.stderr)
        self.assertEqual(path.read_text(), original)

    def test_hermes_mcp_only_does_not_install_lifecycle_plugins(self):
        self.install("hermes", "--mcp-only")
        self.assertFalse((self.home / ".hermes/plugins").exists())

    def test_codex_gateway_update_preserves_per_tool_approvals_and_environment(self):
        import tomlkit
        path = self.home / ".codex/config.toml"
        path.parent.mkdir()
        path.write_text('[mcp_servers.agent-enhancements]\ncommand="old-python"\n'
            f'args=[{json.dumps(str(UI_DIR / "mcp-servers/gateway.py"))}]\n'
            'tool_timeout_sec=91\n[mcp_servers.agent-enhancements.tools.ae_health]\napproval_mode="prompt"\n'
            '[mcp_servers.agent-enhancements.env]\nCUSTOM="preserved"\n')
        self.install("codex")
        server = tomlkit.parse(path.read_text())["mcp_servers"]["agent-enhancements"]
        self.assertNotEqual(server["command"], "old-python")
        self.assertEqual(server["tools"]["ae_health"]["approval_mode"], "prompt")
        self.assertEqual(server["tool_timeout_sec"], 91)
        self.assertEqual(server["env"]["CUSTOM"], "preserved")

    def test_python_aliases_do_not_rewrite_hooks_or_require_new_trust(self):
        alternative = Path(sys.prefix) / "bin/python3"
        if sys.prefix == sys.base_prefix or not alternative.is_file():
            self.skipTest("run with the prepared integration venv")
        self.install("codex")
        folder = self.home / ".codex"
        paths = [folder / "config.toml", folder / "hooks.json"]
        original = {path: path.read_bytes() for path in paths}
        backups = set(folder.glob("*.backup.*"))
        result = subprocess.run([str(alternative), str(UI_DIR / "scripts/native-integration.py"),
                                 "--agent", "codex"], env=self.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({path: path.read_bytes() for path in paths}, original)
        self.assertEqual(set(folder.glob("*.backup.*")), backups)


class DoctorTests(unittest.TestCase):
    def test_failed_targets_are_retained_in_the_release_summary(self):
        with patch.object(sys, "path", [str(UI_DIR / "scripts"), *sys.path]):
            module = load_module("ae_doctor_test", UI_DIR / "scripts/doctor.py")
        report = module.summarize([
            {"agent": "codex", "passed": True},
            {"agent": "hermes/first", "passed": True},
            {"agent": "hermes/restarted", "passed": False},
        ])
        self.assertEqual((report["targets"], report["passed"], report["failed"]), (3, 2, 1))
        self.assertEqual(report["results"][-1]["agent"], "hermes/restarted")

    def test_malformed_gateway_entry_is_reported_as_a_failed_target(self):
        with patch.object(sys, "path", [str(UI_DIR / "scripts"), *sys.path]):
            module = load_module("ae_doctor_malformed_test", UI_DIR / "scripts/doctor.py")
        for config in ([], "invalid", 1, None):
            with self.subTest(config=config):
                row = asyncio.run(module.probe("codex", Path("config.toml"), config))
                self.assertFalse(row["passed"])
                self.assertIn("must be an object", row["diagnosis"])


class HermesPluginTests(unittest.TestCase):
    def test_callbacks_forward_only_bounded_lifecycle_fields(self):
        module = load_module("ae_hermes_plugin", UI_DIR / "hermes-plugin/__init__.py")
        callbacks = {}

        class Context:
            def register_hook(self, name, callback):
                callbacks[name] = callback

        module.register(Context())
        with patch.object(module, "runtime", return_value="local context") as runtime:
            result = callbacks["pre_llm_call"]("session", "task", True,
                conversation_history=[{"secret": "must not forward"}])
            self.assertIn("local context", result["context"])
            self.assertEqual(runtime.call_count, 2)
            for call in runtime.call_args_list:
                self.assertNotIn("conversation_history", call.kwargs)
        with patch.object(module, "runtime") as runtime:
            callbacks["post_tool_call"]("terminal", "session", result="private output", params={"secret": "private"})
            runtime.assert_called_once_with("PostToolUse", "session", tool_name="terminal")


class LibraryMapTests(unittest.TestCase):
    def test_estimate_and_timestamp_changes_do_not_rewrite_an_unchanged_map(self):
        module = load_module("ae_map_test", UI_DIR / "scripts/build-library-map.py")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "map.json"
            args = ["build-library-map.py", "--quiet", "--json-out", str(output)]
            with patch.object(sys, "argv", args), patch.object(module, "approx_tokens", return_value=400):
                with contextlib.redirect_stdout(io.StringIO()) as captured:
                    self.assertEqual(module.main(), 0)
                self.assertEqual(captured.getvalue(), "")
            original, stamp = output.read_bytes(), output.stat().st_mtime_ns
            with patch.object(sys, "argv", args), patch.object(module, "approx_tokens", return_value=500):
                self.assertEqual(module.main(), 0)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(output.stat().st_mtime_ns, stamp)
            with patch.object(sys, "argv", args), patch.object(module, "approx_tokens", return_value=1001):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(module.main(), 1)
            self.assertEqual(output.read_bytes(), original)


class SmokeEnvelopeTests(unittest.TestCase):
    def test_health_credentials_decode_across_client_envelopes(self):
        module = load_module("ae_smoke_test", UI_DIR / "tests/smoke-native-clis.py")
        for state in (False, True):
            report = {"embeddings-mcp": {"backends": {"openai": state}}}
            variants = [report, {"status": "ok", "backends": report},
                        {"structuredContent": {"backends": report}},
                        {"content": [{"type": "text", "text": json.dumps(report)}]}]
            for payload in variants:
                with self.subTest(state=state, payload=payload):
                    self.assertIs(module.openai_health(payload), state)
        self.assertIsNone(module.openai_health({"error": "no health data"}))


if __name__ == "__main__":
    unittest.main()
