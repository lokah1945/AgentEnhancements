"""Tests for native skill activation (scripts/link-skills.sh).

Runs the linker against an isolated HOME so the assertions never touch
the developer's real ~/.claude/skills or ~/.agents/skills.
"""
import os
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, run

LINKER = UI_DIR / "scripts" / "link-skills.sh"
# Registry state comes from the last setup.sh aggregation run (by-category
# tree). The committed all-skills.json guarantees the index exists.
REGISTRY_SKILLS = UI_DIR / "skills" / "by-category"


class LinkSkillsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.TemporaryDirectory()
        cls.home_path = Path(cls.home.name)
        # by-category may be absent in a bare checkout (gitignored tree);
        # the linker must then fail cleanly. When present (post-setup),
        # the full assertions run.
        cls.registry_present = (
            REGISTRY_SKILLS.is_dir()
            and (REGISTRY_SKILLS / "general" / "docx" / "SKILL.md").is_file()
        )

    @classmethod
    def tearDownClass(cls):
        cls.home.cleanup()

    def _link(self, *args):
        env = {"HOME": str(self.home_path)}
        return run(["bash", str(LINKER), *args], env=env)

    def test_status_reports_targets(self):
        code, out, err = self._link("--status")
        self.assertEqual(code, 0, err)
        self.assertIn(".claude/skills", out)
        self.assertIn(".agents/skills", out)

    def test_default_set_links_only_the_ambient_observer(self):
        """Context-frugal default (CONTRACT.md §8.4): the ambient
        task-observer is natively linked; everything else stays reachable
        through on-demand discovery, not native metadata."""
        if not self.registry_present:
            self.skipTest("by-category registry not built (run setup.sh)")
        code, out, err = self._link("--quiet")
        self.assertEqual(code, 0, err)
        claude = self.home_path / ".claude" / "skills"
        agents = self.home_path / ".agents" / "skills"
        self.assertEqual(list(claude.iterdir()), [claude / "task-observer"])
        self.assertEqual(list(agents.iterdir()), [agents / "task-observer"])
        # The default link must resolve to a real SKILL.md.
        target = claude / "task-observer"
        self.assertTrue(target.is_symlink(), "task-observer not linked in .claude")
        self.assertTrue((target / "SKILL.md").is_file(),
                        "task-observer link does not resolve to a SKILL.md")
        self.assertTrue((agents / "task-observer" / "SKILL.md").is_file())

    def test_linking_is_idempotent(self):
        if not self.registry_present:
            self.skipTest("by-category registry not built (run setup.sh)")
        self._link("--quiet")
        claude = self.home_path / ".claude" / "skills"
        before = sorted(p.name for p in claude.iterdir())
        code, _, err = self._link("--quiet")
        self.assertEqual(code, 0, err)
        after = sorted(p.name for p in claude.iterdir())
        self.assertEqual(before, after)

    def test_user_owned_entries_are_never_touched(self):
        if not self.registry_present:
            self.skipTest("by-category registry not built (run setup.sh)")
        self._link("--quiet")
        claude = self.home_path / ".claude" / "skills"
        user_skill = claude / "my-own-skill"
        user_skill.mkdir()
        (user_skill / "SKILL.md").write_text("user content\n")
        foreign = claude / "foreign-link"
        foreign.symlink_to("/definitely/not/ours")
        code, _, err = self._link("--quiet")
        self.assertEqual(code, 0, err)
        self.assertEqual((user_skill / "SKILL.md").read_text(), "user content\n")
        self.assertTrue(foreign.is_symlink())
        # unlink must keep both
        code, _, err = self._link("--unlink", "--quiet")
        self.assertEqual(code, 0, err)
        self.assertTrue((user_skill / "SKILL.md").is_file())
        self.assertTrue(foreign.is_symlink())

    def test_named_link_and_unlink(self):
        if not self.registry_present:
            self.skipTest("by-category registry not built (run setup.sh)")
        code, _, err = self._link("git-workflow", "--quiet")
        self.assertEqual(code, 0, err)
        claude = self.home_path / ".claude" / "skills"
        self.assertTrue((claude / "git-workflow" / "SKILL.md").is_file())
        code, _, err = self._link("--unlink", "git-workflow", "--quiet")
        self.assertEqual(code, 0, err)
        self.assertFalse((claude / "git-workflow").exists())

    def test_unknown_skill_fails_cleanly(self):
        code, _, err = self._link("definitely-not-a-skill-xyz", "--quiet")
        self.assertNotEqual(code, 0)
        self.assertIn("no skills matched", err)

    def test_custom_targets_via_env(self):
        if not self.registry_present:
            self.skipTest("by-category registry not built (run setup.sh)")
        custom = self.home_path / "custom-skills"
        env = {
            "HOME": str(self.home_path),
            "AGENT_SKILLS_NATIVE_TARGETS": str(custom),
        }
        code, _, err = run(["bash", str(LINKER), "docx", "--quiet"], env=env)
        self.assertEqual(code, 0, err)
        self.assertTrue((custom / "docx" / "SKILL.md").is_file())

    def test_unlink_all_removes_only_registry_links(self):
        if not self.registry_present:
            self.skipTest("by-category registry not built (run setup.sh)")
        self._link("--quiet")
        code, _, err = self._link("--unlink", "--quiet")
        self.assertEqual(code, 0, err)
        claude = self.home_path / ".claude" / "skills"
        agents = self.home_path / ".agents" / "skills"
        self.assertEqual(list(claude.iterdir()), [])
        self.assertEqual(list(agents.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
