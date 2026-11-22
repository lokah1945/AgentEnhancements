"""Regressions for the root maintenance scripts and the native CLI smoke harness."""

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[1]


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location(
        "smoke_native_clis", TESTS_DIR / "smoke-native-clis.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RootScriptsAreCheckoutRelative(unittest.TestCase):
    """update_mcp_servers.py / update_catalog.py must not depend on CWD or a fixed path."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ae-misc-root-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.checkout = self.tmp / "checkout"
        self.elsewhere = self.tmp / "elsewhere"
        self.elsewhere.mkdir()
        catalog_dir = self.checkout / "plugin-catalog"
        catalog_dir.mkdir(parents=True)
        for script in ("update_mcp_servers.py", "update_catalog.py"):
            shutil.copy2(REPO_ROOT / script, self.checkout / script)
        manifest = self.checkout / "plugins/tokens-gstack/plugin.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"id": "tokens-gstack"}), encoding="utf-8")
        (catalog_dir / "mcp-servers.json").write_text(
            json.dumps({"servers": [{"id": "filesystem-mcp", "for_plugins": ["all"]}]}),
            encoding="utf-8",
        )
        (catalog_dir / "catalog.json").write_text(
            json.dumps(
                {
                    "skills": [
                        {
                            "id": "tokens-gstack",
                            "manifest_path": "plugins/tokens-gstack/plugin.json",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def _run(self, script):
        return subprocess.run(
            [sys.executable, str(self.checkout / script)],
            cwd=self.elsewhere,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_update_mcp_servers_uses_its_own_checkout(self):
        result = self._run("update_mcp_servers.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Manifest not found", result.stdout)
        manifest = json.loads(
            (self.checkout / "plugins/tokens-gstack/plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["mcp_servers_suggested"], ["filesystem-mcp"])
        self.assertEqual(list(self.elsewhere.iterdir()), [])

    def test_update_catalog_uses_its_own_checkout(self):
        result = self._run("update_catalog.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        catalog = json.loads(
            (self.checkout / "plugin-catalog/catalog.json").read_text(encoding="utf-8")
        )
        self.assertEqual(catalog["skills"][0]["mcp_servers"], ["filesystem-mcp"])
        self.assertEqual(list(self.elsewhere.iterdir()), [])

    def test_scripts_have_no_hardcoded_checkout_path(self):
        for script in ("update_mcp_servers.py", "update_catalog.py"):
            text = (REPO_ROOT / script).read_text(encoding="utf-8")
            self.assertNotIn("/root/project/AgentEnhancements", text, script)


class SmokeFixtureLogsArePrivate(unittest.TestCase):
    def setUp(self):
        self.smoke = _load_smoke_module()
        self.log_dir = Path(tempfile.mkdtemp(prefix="ae-misc-logs-"))
        self.addCleanup(shutil.rmtree, self.log_dir, ignore_errors=True)

    def test_harness_has_no_fixed_tmp_log_path(self):
        text = (TESTS_DIR / "smoke-native-clis.py").read_text(encoding="utf-8")
        self.assertNotIn("/tmp/agentenhancements-fixture-", text)

    def test_log_is_created_private(self):
        path = self.smoke.write_fixture_log(self.log_dir, "codex", "stderr text")
        self.assertEqual(path.read_bytes(), b"stderr text")
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(
            self.smoke.write_fixture_log(self.log_dir, "opencode", None).read_bytes(), b""
        )

    def test_existing_file_is_not_reused(self):
        existing = self.log_dir / "fixture-codex.log"
        existing.write_text("planted")
        with self.assertRaises(FileExistsError):
            self.smoke.write_fixture_log(self.log_dir, "codex", b"secret")
        self.assertEqual(existing.read_text(), "planted")

    @unittest.skipUnless(hasattr(os, "symlink") and os.name == "posix", "POSIX symlinks")
    def test_symlink_is_not_followed(self):
        target = self.log_dir / "target"
        target.write_text("")
        (self.log_dir / "fixture-codex.log").symlink_to(target)
        with self.assertRaises(OSError):
            self.smoke.write_fixture_log(self.log_dir, "codex", b"secret")
        self.assertEqual(target.read_text(), "")


class AgentBrowserIgnoreRules(unittest.TestCase):
    def test_no_stale_hyphen_test_pattern(self):
        rules = (REPO_ROOT / "mcp-servers/agent_browser/.gitignore").read_text().split()
        self.assertNotIn("test-*.js", rules)


if __name__ == "__main__":
    unittest.main()
