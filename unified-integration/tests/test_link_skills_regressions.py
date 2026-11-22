"""Regression tests for scripts/link-skills.sh audit findings.

Each test builds a synthetic registry (AGENT_SKILLS_DIR) and private
link targets, so nothing depends on a built by-category tree or touches
the developer's real skill directories.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, run

LINKER = UI_DIR / "scripts" / "link-skills.sh"


class LinkSkillsRegressionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.skills = self.root / "registry"
        self.target = self.root / "target"
        self.target.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def _registry(self, skills):
        entries = []
        for name, source in skills:
            skill_dir = self.skills / "by-category" / "general" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: test skill\n---\n"
            )
            entries.append({"name": name, "category": "general", "source": source})
        (self.skills / "all-skills.json").write_text(json.dumps({"skills": entries}))

    def _link(self, *args, cwd=None):
        env = {
            "HOME": str(self.home),
            "AGENT_SKILLS_DIR": str(self.skills),
            "AGENT_SKILLS_NATIVE_TARGETS": str(self.target),
        }
        return run(["bash", str(LINKER), *args], env=env, cwd=cwd)

    def test_set_matches_source_case_insensitively(self):
        self._registry([("alpha", "Superpowers"), ("beta", "Other")])
        for spelling in ("superpowers", "Superpowers", "SUPERPOWERS"):
            with self.subTest(spelling=spelling):
                code, _, err = self._link("--set", spelling, "--quiet")
                self.assertEqual(code, 0, err)
                self.assertTrue((self.target / "alpha").is_symlink())
                self.assertFalse((self.target / "beta").exists())

    def test_skill_names_stay_case_sensitive(self):
        self._registry([("alpha", "Superpowers")])
        code, _, _ = self._link("ALPHA", "--quiet")
        self.assertNotEqual(code, 0)
        self.assertFalse((self.target / "ALPHA").exists())

    def test_migrate_removes_only_exact_stale_links(self):
        """Stale names with spaces or glob characters must not expand."""
        self._registry([("alpha", "Superpowers")])
        missing = self.skills / "by-category" / "general" / "gone"
        for name in ("foo bar", "x*"):
            os.symlink(missing, self.target / name)
        # User-owned entries a split or glob would wrongly hit.
        for name in ("foo", "bar", "xyz"):
            (self.target / name).write_text("user data")
        code, _, err = self._link("--migrate", cwd=self.target)
        self.assertEqual(code, 0, err)
        for name in ("foo bar", "x*"):
            self.assertFalse(os.path.lexists(self.target / name), name)
        for name in ("foo", "bar", "xyz"):
            self.assertEqual((self.target / name).read_text(), "user data", name)


if __name__ == "__main__":
    unittest.main()
