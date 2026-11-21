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

    def test_setup_prompts_never_rewrites_existing_prompt_files(self):
        # Final audit 2026-11-20 (P2): every setup run copied a third-party
        # prompt picked by a locale-dependent glob over the tracked
        # prompts/*.txt files, leaving the checkout dirty.
        import tempfile
        functions = re.findall(
            r"^(?:install_prompt|setup_prompts)\(\) \{.*?^\}", self.src, re.S | re.M)
        self.assertEqual(len(functions), 2)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "system-prompts-and-models-of-ai-tools/Open Source prompts/Codex CLI"
            source.mkdir(parents=True)
            (source / "Prompt.txt").write_text("vendored prompt\n")
            prompts = base / "unified-integration/prompts"
            prompts.mkdir(parents=True)
            kept = prompts / "codex-system-prompt.txt"
            kept.write_text("tracked prompt\n")
            script = "\n".join([
                "set -euo pipefail", "shopt -s globstar nullglob",
                "log_info() { :; }; log_success() { :; }; log_warn() { :; }",
                *functions,
                f"BASE_DIR={str(base)!r}; UNIFIED_DIR={str(base / 'unified-integration')!r}",
                "AGENTS=(codex)", "setup_prompts", "rm \"$UNIFIED_DIR/prompts/codex-system-prompt.txt\"",
                "setup_prompts"])
            first = subprocess.run(["bash", "-c", "\n".join(script.split("\n")[:-2])],
                                   capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(kept.read_text(), "tracked prompt\n")
            second = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(kept.read_text(), "vendored prompt\n")

    def test_private_runtime_logs_are_never_committable(self):
        # Final audit 2026-11-20 (P2): consent and audit JSONL are written to
        # unified-integration/memory/audit/, which was not ignored.
        for path in ("unified-integration/memory/audit/consent.jsonl",
                     "unified-integration/memory/audit/mcp-calls.jsonl",
                     ".agentenhancements/memory/memory.db", "ui.api.json"):
            result = subprocess.run(["git", "-C", str(REPO_DIR), "check-ignore", "-q", path])
            self.assertEqual(result.returncode, 0, f"{path} is not ignored")

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
        # merge_yaml_config passes its payload through the environment
        # (R003/F-10); the dead merge_json_config was removed (AE-20), so
        # the surviving contract is ENHANCEMENT_YAML + TARGET_FILE.
        self.assertIn("os.environ['ENHANCEMENT_YAML']", self.src)
        self.assertIn("os.environ['TARGET_FILE']", self.src)
        self.assertNotIn("json.loads('$enhancement_json')", self.src)
        self.assertNotIn("yaml.safe_load('$enhancement_yaml')", self.src)


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
        payload = 'function first() {\n  same();\n}\nfunction second() {\n  same();\n}\n'
        rc, out, err = run(["bash", str(UI_DIR / "compression/compress.sh"), "-", "code"],
                           input_text=payload, env={"HEADROOM_BIN": "/nonexistent/headroom"})
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.rstrip("\n"), payload.rstrip("\n"))

    def test_aggregation_is_idempotent(self):
        """cp targets must be cleaned before copy (no nesting on re-runs)."""
        src = (UI_DIR / "setup.sh").read_text()
        self.assertRegex(src, r"rm -rf \"\$target_dir\"")
        self.assertRegex(src, r"rm -rf \"\$agent_target_dir\"")

    def test_agent_tool_whitelist_in_aggregation(self):
        src = (UI_DIR / "setup.sh").read_text()
        self.assertIn("claude-code|codex|cursor|gemini-cli|opencode|copilot|windsurf|kiro|hermes)", src)

    def test_gitignore_blocks_local_settings(self):
        gi = (REPO_DIR / ".gitignore").read_text()
        self.assertIn(".claude/settings.local.json", gi)
        self.assertIn("all-skills.json.tmp", gi)


if __name__ == "__main__":
    unittest.main()
