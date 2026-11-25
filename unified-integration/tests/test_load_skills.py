"""Tests for unified-integration/scripts/load-skills.py.

Regression coverage:
- F-09: SKILLS_DIR must honor AGENT_SKILLS_DIR and default to the repo,
  and load_skill must support BOTH directory (SKILL.md) and flat (.md) layouts.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module, run


class SkillsLoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        # directory-layout skill
        (root / "by-category" / "security" / "dirskill").mkdir(parents=True)
        (root / "by-category" / "security" / "dirskill" / "SKILL.md").write_text(
            "---\nname: dirskill\ndescription: dir skill\n---\nDirectory body\n"
        )
        # flat-layout skill
        (root / "by-category" / "general").mkdir(parents=True)
        (root / "by-category" / "general" / "flatskill.md").write_text(
            "---\nname: flatskill\ndescription: flat skill\n---\nFlat body\n"
        )
        # by-agent layout
        (root / "by-agent" / "claude-code" / "agentskill").mkdir(parents=True)
        (root / "by-agent" / "claude-code" / "agentskill" / "SKILL.md").write_text(
            "---\nname: agentskill\n---\nAgent body\n"
        )
        # index
        (root / "all-skills.json").write_text(json.dumps({
            "skills": [
                {"name": "dirskill", "category": "security", "description": "audit a pentest",
                 "tags": ["security"], "tools": ["claude-code"], "when_to_use": "audit a pentest"},
                {"name": "flatskill", "category": "general", "description": "misc helper",
                 "tags": [], "tools": [], "when_to_use": "misc helper"},
            ]
        }))
        self.root = root
        self.mod = load_module(
            "loadskills_test",
            UI_DIR / "scripts" / "load-skills.py",
            env={"AGENT_SKILLS_DIR": str(root)},
        )
        self.assertEqual(str(self.mod.SKILLS_DIR), str(root), "env override not honored")

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_directory_layout_skill(self):
        loader = self.mod.SkillsLoader("claude-code")
        skill = loader.load_skill("dirskill")
        self.assertEqual(skill.get("frontmatter", {}).get("name"), "dirskill")
        self.assertEqual(skill.get("body"), "Directory body")

    def test_load_flat_layout_skill(self):
        loader = self.mod.SkillsLoader("claude-code")
        skill = loader.load_skill("flatskill")
        self.assertEqual(skill.get("frontmatter", {}).get("name"), "flatskill")

    def test_load_by_agent_layout_skill(self):
        loader = self.mod.SkillsLoader("claude-code")
        skill = loader.load_skill("agentskill")
        self.assertIn("Agent body", skill.get("body", ""))

    def test_load_missing_returns_empty(self):
        loader = self.mod.SkillsLoader("claude-code")
        self.assertEqual(loader.load_skill("does-not-exist"), {})

    def test_find_skills_scores_agent_compat(self):
        loader = self.mod.SkillsLoader("claude-code")
        hits = loader.find_skills("audit a pentest")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["name"], "dirskill")

    def test_default_skills_dir_resolves_inside_repo(self):
        with patch.dict(os.environ):
            os.environ.pop("AGENT_SKILLS_DIR", None)
            mod = load_module("loadskills_default", UI_DIR / "scripts" / "load-skills.py")
        # A checkout is allowed under /root; compare to the actual repository.
        self.assertEqual(mod.SKILLS_DIR, UI_DIR / "skills")

    def test_compatibility_alone_does_not_match_unrelated_prompt(self):
        self.assertEqual(self.mod.SkillsLoader("claude-code").find_skills("zyxwvu"), [])

    def test_missing_registry_tree_does_not_raise(self):
        import shutil
        shutil.rmtree(self.root / "by-category")
        self.assertEqual(self.mod.SkillsLoader("claude-code").load_skill("nope"), {})

    def test_skill_path_rejects_traversal(self):
        loader = self.mod.SkillsLoader("claude-code")
        self.assertIsNone(loader.skill_path("../secret"))

    def test_load_rejects_symlink_outside_skills_directory(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "private.md"
            target.write_text("private fixture")
            link = self.root / "by-category" / "general" / "escaped.md"
            link.symlink_to(target)
            self.assertEqual(self.mod.SkillsLoader("claude-code").load_skill("escaped"), {})

    def test_load_preserves_markdown_without_complete_frontmatter(self):
        path = self.root / "by-category" / "general" / "raw.md"
        loader = self.mod.SkillsLoader("claude-code")
        for text in ("# Skill without a header\n", "---\nname: unclosed\n"):
            with self.subTest(text=text):
                path.write_text(text)
                self.assertEqual(loader.load_skill("raw"), {"raw": text, "file": str(path)})

    def test_load_preserves_raw_content_when_yaml_is_unavailable(self):
        path = self.root / "by-category" / "general" / "flatskill.md"
        stderr = io.StringIO()
        with patch.dict(sys.modules, {"yaml": None}), redirect_stderr(stderr):
            skill = self.mod.SkillsLoader("claude-code").load_skill("flatskill")
        self.assertEqual(skill, {"raw": path.read_text(), "file": str(path)})
        self.assertIn("PyYAML", stderr.getvalue())

    def test_agent_aliases_and_tool_prerequisites_remain_usable(self):
        loader = self.mod.SkillsLoader("codex")
        loader.skills_index["skills"][0]["tools"] = ["Codex", "python"]
        self.assertEqual(loader.find_skills("security")[0]["name"], "dirskill")
        loader.skills_index["skills"][0]["tools"] = ["Agent Skills", "python"]
        self.assertEqual(loader.find_skills("security")[0]["name"], "dirskill")

    def run_cli(self, *args):
        return run(
            [sys.executable, str(UI_DIR / "scripts" / "load-skills.py"), *args],
            env={"AGENT_SKILLS_DIR": str(self.root)},
            cwd=self.root,
        )

    def test_cli_displays_matches_for_agent_alias_and_multiword_task(self):
        status, stdout, stderr = self.run_cli("Claude", "audit", "a", "pentest")
        self.assertEqual(status, 0, stderr)
        self.assertIn("Skill: dirskill", stdout)
        self.assertIn("Description: audit a pentest", stdout)
        self.assertIn("Tags: security", stdout)

    def test_cli_omits_skill_for_incompatible_agent(self):
        status, stdout, stderr = self.run_cli("codex-cli", "audit", "a", "pentest")
        self.assertEqual(status, 0, stderr)
        self.assertEqual(stdout, "")

    def test_cli_treats_missing_index_as_empty(self):
        (self.root / "all-skills.json").unlink()
        status, stdout, stderr = self.run_cli("claude-code", "dirskill")
        self.assertEqual(status, 0, stderr)
        self.assertEqual(stdout, "")

    def test_cli_reports_usage_when_task_is_missing(self):
        status, stdout, stderr = self.run_cli("claude-code")
        self.assertEqual(status, 1, stderr)
        self.assertIn("<agent> <task_description>", stdout)


if __name__ == "__main__":
    unittest.main()
