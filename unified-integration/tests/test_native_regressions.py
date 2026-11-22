"""Regressions for native host adapters: symlinked configs, Hermes YAML
comments and null keys, and `--agent all` on hosts that are not installed."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from helpers import UI_DIR

sys.path.insert(0, str(UI_DIR / "scripts"))
import native_config  # noqa: E402

COMMENTED = """# Hermes config
model:
  default: foo  # my model
"""


class NativeRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ae-native-")
        self.home = Path(self.tmp.name)
        self.env = {**os.environ, "HOME": str(self.home),
                    "AGENT_ENHANCEMENTS_STATE_DIR": str(self.home / "ae-state"),
                    "XDG_CONFIG_HOME": str(self.home / ".config"),
                    "XDG_DATA_HOME": str(self.home / ".local/share"),
                    "HERMES_HOME": str(self.home / ".hermes"),
                    "CODEX_HOME": str(self.home / ".codex"),
                    "AGENT_MEMORY_ROOT": str(self.home / "memory"),
                    "AGENT_ENHANCEMENTS_API_FILE": str(self.home / "api.json")}

    def tearDown(self):
        self.tmp.cleanup()

    def run_native(self, *args):
        return subprocess.run(
            [sys.executable, str(UI_DIR / "scripts/native-integration.py"), *args],
            env=self.env, capture_output=True, text=True, timeout=60)

    def backups(self, path):
        return sorted(path.parent.glob(path.name + ".backup.*"))

    # -- native_config.write -------------------------------------------------

    def test_write_json_keeps_symlinked_config_linked(self):
        dotfiles = self.home / "dotfiles"
        dotfiles.mkdir()
        target = dotfiles / "settings.json"
        target.write_text('{"theme": "dark"}\n')
        link = self.home / ".claude" / "settings.json"
        link.parent.mkdir()
        link.symlink_to(Path("..") / "dotfiles" / "settings.json")
        native_config.write_json(link, {"theme": "dark", "added": True})
        self.assertTrue(link.is_symlink())
        self.assertIn('"added": true', target.read_text())
        self.assertEqual(self.backups(link), [])  # backup sits beside the target
        self.assertEqual(len(self.backups(target)), 1)

    def test_write_through_dangling_symlink_creates_target(self):
        target = self.home / "dotfiles" / "AGENTS.md"
        link = self.home / "AGENTS.md"
        link.symlink_to(target)
        native_config.merge_instructions(link, "hello")
        self.assertTrue(link.is_symlink())
        self.assertIn("hello", target.read_text())

    # -- Hermes --------------------------------------------------------------

    def hermes_config(self, text):
        path = self.home / ".hermes" / "config.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_hermes_null_mcp_servers_and_plugin_lists_install(self):
        path = self.hermes_config(
            "mcp_servers:\n#  time:\n#    command: uvx\nplugins:\n  enabled:\n  disabled:\n")
        result = self.run_native("--agent", "hermes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        import yaml
        doc = yaml.safe_load(path.read_text())
        self.assertIn("agent-enhancements", doc["mcp_servers"])
        self.assertEqual(doc["plugins"]["enabled"], ["agent-enhancements"])

    def test_hermes_rejects_non_list_plugin_entries(self):
        self.hermes_config("plugins:\n  disabled: agent-enhancements\n")
        result = self.run_native("--agent", "hermes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plugins.disabled must be a list", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_hermes_unchanged_commented_config_is_left_byte_identical(self):
        path = self.hermes_config(COMMENTED)
        first = self.run_native("--agent", "hermes", "--mcp-only")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("comments in", first.stderr)  # real change: warned
        self.assertEqual(len(self.backups(path)), 1)
        # Re-add a comment without changing the configuration semantically.
        commented = "# kept\n" + path.read_text()
        path.write_text(commented)
        second = self.run_native("--agent", "hermes", "--mcp-only")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(path.read_text(), commented)
        self.assertEqual(len(self.backups(path)), 1)
        self.assertNotIn("comments in", second.stderr)

    # -- --agent all -----------------------------------------------------------

    def test_agent_all_skips_hosts_that_are_not_installed(self):
        empty = self.home / "empty-bin"
        empty.mkdir()
        self.env["PATH"] = str(empty)
        result = self.run_native("--agent", "all", "--mcp-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home / ".claude.json").exists())
        self.assertFalse((self.home / ".codex" / "config.toml").exists())
        self.assertFalse((self.home / ".config" / "opencode").exists())
        self.assertFalse((self.home / ".hermes" / "config.yaml").exists())

    def test_agent_all_continues_after_one_host_fails(self):
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        for name in ("claude", "codex"):
            exe = bin_dir / name
            exe.write_text("#!/bin/sh\nexit 0\n")
            exe.chmod(0o755)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin"
        broken = self.home / ".claude.json"
        broken.write_text("[]\n")  # not an object: claude-code fails
        result = self.run_native("--agent", "all", "--mcp-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("claude-code", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(broken.read_text(), "[]\n")
        self.assertIn("agent-enhancements",
                      (self.home / ".codex" / "config.toml").read_text())

    def test_agent_all_continues_after_opencode_version_failure(self):
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        scripts = {"claude": "exit 0", "codex": "exit 0",
                   "opencode": "echo 'opencode v1.4.0'"}
        for name, body in scripts.items():
            exe = bin_dir / name
            exe.write_text(f"#!/bin/sh\n{body}\n")
            exe.chmod(0o755)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin"
        result = self.run_native("--agent", "all", "--mcp-only")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("OpenCode 2 is required", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("agent-enhancements", (self.home / ".claude.json").read_text())
        self.assertIn("agent-enhancements",
                      (self.home / ".codex" / "config.toml").read_text())
        self.assertFalse((self.home / ".config" / "opencode").exists())

    def test_agent_all_continues_after_unexpected_host_error(self):
        bin_dir = self.home / "bin"
        bin_dir.mkdir()
        for name in ("claude", "codex"):
            exe = bin_dir / name
            exe.write_text("#!/bin/sh\nexit 0\n")
            exe.chmod(0o755)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin"
        broken = self.home / ".claude.json"
        broken.write_text('{"mcpServers": []}\n')  # list, not object
        result = self.run_native("--agent", "all", "--mcp-only")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("[native] claude-code:", result.stderr)
        self.assertIn("agent-enhancements",
                      (self.home / ".codex" / "config.toml").read_text())


if __name__ == "__main__":
    unittest.main()
