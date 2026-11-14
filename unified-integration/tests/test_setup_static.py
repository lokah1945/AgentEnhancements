"""Static checks on setup.sh and shipped scripts (policy regressions).

Covers CONTRACT §9.1 checks plus the specific defects fixed in this audit:
- F-24: BASE_DIR defaults to the script's repo, not /root.
- F-05: globstar enabled for prompt discovery.
- F-25: no ((count++)) abort under set -e.
- F-02/F-17: no shell interpolation of data into python -c sources.
- R003: no hardcoded /root paths in shipped runtime scripts.
"""
import re
import subprocess
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, REPO_DIR, run


class SetupStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (UI_DIR / "setup.sh").read_text()

    def test_bash_syntax_all_sh(self):
        for sh in sorted(UI_DIR.rglob("*.sh")):
            with self.subTest(script=str(sh.relative_to(UI_DIR))):
                rc, out, err = run(["bash", "-n", str(sh)])
                self.assertEqual(rc, 0, f"{sh}: {err}")

    def test_globstar_enabled(self):
        self.assertRegex(self.src, r"shopt -s globstar")

    def test_base_dir_self_locating(self):
        self.assertIn('BASE_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-$(cd "$SCRIPT_SOURCE_DIR/.." && pwd)}"', self.src)

    def test_no_arithmetic_postincrement(self):
        self.assertNotRegex(self.src, r"\(\(\w+\+\+\)\)")

    def test_no_python_c_data_interpolation(self):
        """python -c bodies must not splice shell data via ''' quotes."""
        self.assertNotIn("'''$", self.src)
        self.assertNotIn("$ALL_SKILLS_JSON'''", self.src)

    def test_no_backslash_dollar_in_json_blocks(self):
        r"""'\$' is an invalid JSON escape; must not appear (F-10 escape fix)."""
        self.assertNotIn("\\${", self.src)

    def test_merge_uses_env_vars(self):
        self.assertIn("os.environ['ENHANCEMENT_JSON']", self.src)
        self.assertIn("os.environ['TARGET_FILE']", self.src)
        self.assertNotIn("json.loads('$enhancement_json')", self.src)


class ShippedScriptTests(unittest.TestCase):
    def test_no_hardcoded_root_paths(self):
        for rel in [
            "launch-agent.sh",
            "compression/compress.sh",
            "scripts/load-skills.py",
            "scripts/compress.py",
            "scripts/memory.py",
            "memory/config.yaml",
        ]:
            with self.subTest(script=rel):
                content = (UI_DIR / rel).read_text()
                self.assertNotIn("/root/agent-enhancements", content,
                                 f"{rel} still hardcodes /root/agent-enhancements")

    def test_launch_agent_uses_set_euo_pipefail(self):
        content = (UI_DIR / "launch-agent.sh").read_text()
        self.assertIn("set -euo pipefail", content)
        self.assertIn("AGENT_ENHANCEMENTS_UNIFIED_DIR", content)

    def test_compress_sh_is_stream_safe(self):
        content = (UI_DIR / "compression" / "compress.sh").read_text()
        self.assertIn("mktemp", content)
        self.assertIn("trap", content)

    def test_aggregation_is_idempotent(self):
        """cp targets must be cleaned before copy (no nesting on re-runs)."""
        src = (UI_DIR / "setup.sh").read_text()
        self.assertRegex(src, r"rm -rf \"\$target_dir\"")
        self.assertRegex(src, r"rm -rf \"\$agent_target_dir\"")

    def test_agent_tool_whitelist_in_aggregation(self):
        src = (UI_DIR / "setup.sh").read_text()
        self.assertIn("claude-code|codex|cursor|gemini-cli|opencode|copilot|windsurf|kiro)", src)

    def test_gitignore_blocks_local_settings(self):
        gi = (REPO_DIR / ".gitignore").read_text()
        self.assertIn(".claude/settings.local.json", gi)
        self.assertIn("all-skills.json.tmp", gi)


if __name__ == "__main__":
    unittest.main()
