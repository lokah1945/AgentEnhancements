"""Tests for unified-integration/scripts/load-skills.py.

Regression coverage:
- F-09: SKILLS_DIR must honor AGENT_SKILLS_DIR and default to the repo,
  and load_skill must support BOTH directory (SKILL.md) and flat (.md) layouts.
"""
import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module


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
        mod = load_module("loadskills_default", UI_DIR / "scripts" / "load-skills.py")
        # default must NOT be a hardcoded /root path
        self.assertNotIn("/root/", str(mod.SKILLS_DIR))
        self.assertEqual(mod.SKILLS_DIR, UI_DIR / "skills")


if __name__ == "__main__":
    unittest.main()
