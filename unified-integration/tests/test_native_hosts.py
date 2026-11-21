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
                    "AGENT_ENHANCEMENTS_STATE_DIR": str(self.home / 'ae-state'),
                    "XDG_CONFIG_HOME": str(self.home / ".config"),
                    "XDG_DATA_HOME": str(self.home / ".local/share"),
                    "HERMES_HOME": str(self.home / ".hermes"),
                    "AGENT_MEMORY_ROOT": str(self.home / "memory"),
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
        # Native Hermes terminals export the current profile as HERMES_HOME.
        self.env["HERMES_HOME"] = str(root / "profiles/ilma")
        (root / "active_profile").write_text("missing\n")
        self.install("hermes")  # saved selection survives setup inside a profile
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

    def test_checkout_move_refreshes_codex_gateway_and_retires_old_direct_server(self):
        import tomlkit
        self.env.pop('TASK_OBSERVER_WORKSPACE', None)
        old = self.home / 'removed checkout/unified-integration'
        path = self.home / '.codex/config.toml'
        path.parent.mkdir()
        path.write_text(tomlkit.dumps({'mcp_servers': {
            'agent-enhancements': {'command': 'old-python',
                'args': [str(old / 'mcp-servers/gateway.py')],
                'tool_timeout_sec': 91, 'env': {'CUSTOM': 'preserved',
                    'AGENT_ENHANCEMENTS_MODEL_FILE': str(old / 'model.json'),
                    'TASK_OBSERVER_WORKSPACE': str(old / 'observer')}},
            'embeddings-mcp': {'command': 'old-python',
                'args': [str(old / 'mcp-servers/embeddings-mcp/server.py')]},
            'personal': {'command': 'personal-command'},
        }}))
        self.install('codex')
        servers = tomlkit.parse(path.read_text())['mcp_servers']
        self.assertEqual(list(servers['agent-enhancements']['args']),
                         [str(UI_DIR / 'mcp-servers/gateway.py')])
        self.assertEqual(servers['agent-enhancements']['tool_timeout_sec'], 91)
        self.assertEqual(servers['agent-enhancements']['env']['CUSTOM'], 'preserved')
        # Preflight settings live in ui.api.json; the retired path is removed.
        self.assertNotIn('AGENT_ENHANCEMENTS_MODEL_FILE', servers['agent-enhancements']['env'])
        self.assertEqual(servers['agent-enhancements']['env']['TASK_OBSERVER_WORKSPACE'],
                         str(Path(self.env['AGENT_MEMORY_ROOT']) / 'task-observer'))
        self.assertNotIn('embeddings-mcp', servers)
        self.assertEqual(servers['personal']['command'], 'personal-command')

    def test_checkout_move_replaces_opencode_plugin_and_instruction_paths(self):
        old = self.home / 'removed checkout/unified-integration'
        path = self.home / '.config/opencode/opencode.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            'plugins': [str(old / 'opencode-plugin'), 'personal-plugin'],
            'instructions': [str(old / 'prompts/opencode-system-prompt.txt'), 'personal.md'],
            'skills': [str(old / 'skills/by-category'), 'personal-skills'],
        }))
        self.install('opencode')
        doc = json.loads(path.read_text())
        self.assertEqual(doc['plugins'], ['personal-plugin', str(UI_DIR / 'opencode-plugin')])
        self.assertEqual(doc['skills'], ['personal-skills'])
        self.assertNotIn(str(old), json.dumps(doc))
        self.assertIn('personal.md', doc['instructions'])

    def test_checkout_move_refreshes_hermes_plugin_but_preserves_foreign_link(self):
        target = self.home / '.hermes/plugins/agent-enhancements'
        target.parent.mkdir(parents=True)
        target.symlink_to(self.home / 'removed checkout/unified-integration/hermes-plugin',
                          target_is_directory=True)
        self.install('hermes')
        self.assertEqual(target.resolve(), (UI_DIR / 'hermes-plugin').resolve())
        target.unlink()
        foreign = self.home / 'personal-plugin'
        foreign.mkdir()
        target.symlink_to(foreign, target_is_directory=True)
        self.install('hermes')
        self.assertEqual(target.resolve(), foreign.resolve())

    def test_checkout_move_refreshes_native_skill_link_without_overwriting_foreign_link(self):
        registry = self.home / 'current/unified-integration/skills'
        bundle = registry / 'by-category/general/probe'
        bundle.mkdir(parents=True)
        (bundle / 'SKILL.md').write_text('Fixture instructions')
        (registry / 'all-skills.json').write_text(json.dumps({'skills': [
            {'name': 'probe', 'category': 'general', 'source': 'Superpowers'}]}))
        target = self.home / 'native/skills'
        target.mkdir(parents=True)
        link = target / 'probe'
        link.symlink_to(self.home / 'removed/unified-integration/skills/by-category/general/probe',
                        target_is_directory=True)
        env = dict(self.env, AGENT_SKILLS_DIR=str(registry), AGENT_SKILLS_NATIVE_TARGETS=str(target))
        command = ['bash', str(UI_DIR / 'scripts/link-skills.sh'), '--quiet']
        first = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(link.resolve(), bundle.resolve())
        link.unlink()
        foreign = self.home / 'personal-skill'
        foreign.mkdir()
        link.symlink_to(foreign, target_is_directory=True)
        second = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(link.resolve(), foreign.resolve())

    def test_opencode_preserves_disabled_gateway_and_codemode(self):
        path = self.home / ".config/opencode/opencode.jsonc"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"mcp": {"servers": {"agent-enhancements": {
            "command": [sys.executable, str(UI_DIR / "mcp-servers/gateway.py")],
            "disabled": True, "codemode": True,
        }}}}))
        self.install("opencode")
        server = json.loads(path.read_text())["mcp"]["servers"]["agent-enhancements"]
        self.assertTrue(server["disabled"])
        self.assertTrue(server["codemode"])

    def test_doctor_accepts_the_unprofiled_hermes_home(self):
        binary = self.home / "bin/hermes"
        binary.parent.mkdir()
        binary.write_text('#!/bin/sh\n[ "$#" = 1 ] && [ "$1" = "--version" ] || exit 2\nprintf "Hermes fixture\\n"\n')
        binary.chmod(0o700)
        self.env["PATH"] = str(binary.parent) + os.pathsep + os.environ["PATH"]
        self.install("hermes")
        result = subprocess.run([sys.executable, str(UI_DIR / "scripts/doctor.py"),
                                 "--agents", "hermes", "--json"], env=self.env,
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report["targets"], report["passed"]), (1, 1))
        self.assertEqual(report["results"][0]["agent"], "hermes/default")


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


    def test_opencode_target_requires_the_lifecycle_plugin(self):
        # Final audit 2026-11-20 (P2): a gateway-only OpenCode config passed
        # doctor although no AE hook would ever run.
        with patch.object(sys, "path", [str(UI_DIR / "scripts"), *sys.path]):
            module = load_module("ae_doctor_opencode_test", UI_DIR / "scripts/doctor.py")
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "opencode"
            config.mkdir()
            gateway = {"type": "local", "command": ["python3", str(UI_DIR / "mcp-servers/gateway.py")]}
            path = config / "opencode.json"
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}):
                path.write_text(json.dumps({"mcp": {"servers": {"agent-enhancements": gateway}}}))
                (_, _, cfg), = module.targets(["opencode"])
                self.assertIn("plugin", cfg.get("diagnosis", ""))
                path.write_text(json.dumps({"mcp": {"servers": {"agent-enhancements": gateway}},
                                            "plugins": [str(UI_DIR / "opencode-plugin")]}))
                (_, _, cfg), = module.targets(["opencode"])
                self.assertEqual(cfg, gateway)

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
