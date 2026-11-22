"""Task Observer regression tests for audited defects.

Rollback backup selection: backups live in skill-updates/rollback/ as
"<skill>-<YYYYmmddTHHMMSSZ>". A "<skill>-*" glob also matched a different
skill whose name extends the target (agent-memory vs agent-memory-mcp), and
because a letter sorts after a digit that foreign backup was picked as the
"newest" and restored over the target. All fixtures are synthetic temp
trees; the repository's skill trees are never touched.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module

SCRIPT = UI_DIR / "scripts/task-observer.py"


class RollbackBackupSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.ws = base / "memory" / "task-observer"
        self.skills = base / "skills"
        self.mod = load_module(
            "task_observer_regressions_test", SCRIPT,
            env={"AGENT_MEMORY_ROOT": str(base / "memory")},
        )
        skills = self.skills
        self.mod._canonical_source = (
            lambda name: skills / name
            if (skills / name / "SKILL.md").is_file() else None
        )
        self.rollback_dir = self.ws / "skill-updates" / "rollback"
        self.rollback_dir.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _tree(self, path, text):
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(text, encoding="utf-8")

    def test_rollback_ignores_backup_of_longer_named_skill(self):
        self._tree(self.skills / "agent-memory", "live agent-memory\n")
        self._tree(self.skills / "agent-memory-mcp", "live agent-memory-mcp\n")
        self._tree(self.rollback_dir / "agent-memory-20261101T000000Z",
                   "backup agent-memory\n")
        # Older stamp, but sorts last under a "agent-memory-*" glob.
        self._tree(self.rollback_dir / "agent-memory-mcp-20261001T000000Z",
                   "backup agent-memory-mcp\n")

        out = self.mod.rollback(self.ws, "agent-memory")

        self.assertTrue(out.startswith("rolled back"), out)
        self.assertIn("agent-memory-20261101T000000Z", out)
        self.assertEqual(
            (self.skills / "agent-memory" / "SKILL.md").read_text(),
            "backup agent-memory\n",
        )
        # The other skill's tree is untouched.
        self.assertEqual(
            (self.skills / "agent-memory-mcp" / "SKILL.md").read_text(),
            "live agent-memory-mcp\n",
        )

    def test_rollback_picks_newest_own_backup(self):
        self._tree(self.skills / "angular", "live\n")
        self._tree(self.rollback_dir / "angular-20261001T000000Z", "old\n")
        self._tree(self.rollback_dir / "angular-20261101T000000Z", "new\n")
        self._tree(self.rollback_dir / "angular-migration-20261201T000000Z",
                   "foreign\n")
        out = self.mod.rollback(self.ws, "angular")
        self.assertTrue(out.startswith("rolled back"), out)
        self.assertEqual(
            (self.skills / "angular" / "SKILL.md").read_text(), "new\n")

    def test_rollback_refuses_when_only_foreign_backups_exist(self):
        self._tree(self.skills / "angular", "live\n")
        self._tree(self.rollback_dir / "angular-migration-20261201T000000Z",
                   "foreign\n")
        out = self.mod.rollback(self.ws, "angular")
        self.assertTrue(out.startswith("refused"), out)
        self.assertEqual(
            (self.skills / "angular" / "SKILL.md").read_text(), "live\n")


if __name__ == "__main__":
    unittest.main()
