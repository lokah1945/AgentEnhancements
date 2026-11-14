"""Hardening regression tests for the 2026-11 end-to-end audit fixes.

Covers:
- H-1: ~/.claude/CLAUDE.md must be merged with markers, never overwritten
       (personal instructions survive re-runs, matching the README claim).
- H-2: the index builder must sort skills by name (deterministic output;
       unsorted output produced a ~50k-line diff on every regeneration).
- L-1: skill names "." / ".." / empty must be rejected during aggregation.
- M-2: config merge failures (malformed user JSON / missing PyYAML) must
       not abort the whole setup.
- M-3/M-4: README and generated-template capability counts stay accurate.
"""
import json
import re
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import REPO_DIR, UI_DIR


class ClaudeMdPreservationTests(unittest.TestCase):
    """H-1: CLAUDE.md is marker-guarded, like the other instruction files."""

    @classmethod
    def setUpClass(cls):
        cls.src = (UI_DIR / "setup.sh").read_text()

    def test_claude_md_merged_with_markers(self):
        self.assertIn('merge_agents_md "$CLAUDE_DIR/CLAUDE.md"',
                      self.src,
                      "create_claude_code_config must merge CLAUDE.md via merge_agents_md")

    def test_claude_md_never_blindly_overwritten(self):
        self.assertNotIn('cat > "$CLAUDE_DIR/CLAUDE.md"',
                         self.src,
                         "CLAUDE.md must not be overwritten with cat > (data loss)")


class DeterministicIndexTests(unittest.TestCase):
    """H-2: the committed index must only change when content changes."""

    @classmethod
    def setUpClass(cls):
        cls.src = (UI_DIR / "setup.sh").read_text()

    def test_index_builder_sorts_by_name(self):
        self.assertIn("skills.sort(key=lambda s: s['name'])", self.src)

    def test_committed_index_is_sorted(self):
        index = json.loads((UI_DIR / "skills" / "all-skills.json").read_text())
        names = [s["name"] for s in index["skills"]]
        self.assertEqual(names, sorted(names),
                         "committed all-skills.json must be sorted by name")

    def test_registry_entries_are_sorted(self):
        registry = json.loads((UI_DIR / "skills" / "agent-registry.json").read_text())
        skill_names = [e["name"] for e in registry["entries"] if e["type"] == "skill"]
        self.assertEqual(skill_names, sorted(skill_names))


class SkillNameGuardTests(unittest.TestCase):
    """L-1: path-relative skill names must be rejected at aggregation."""

    @classmethod
    def setUpClass(cls):
        cls.src = (UI_DIR / "setup.sh").read_text()

    def test_dot_and_dotdot_names_rejected(self):
        self.assertIn('[ "$skill_name" = "." ] || [ "$skill_name" = ".." ]',
                      self.src,
                      "aggregation must skip skill names '.' and '..'")


class NonFatalMergeTests(unittest.TestCase):
    """M-2: a broken per-user config must not abort the whole setup."""

    @classmethod
    def setUpClass(cls):
        cls.src = (UI_DIR / "setup.sh").read_text()

    def test_json_merge_failure_restores_backup(self):
        self.assertIn('Merge failed for $target_file (existing file not valid JSON?)', self.src)
        self.assertIn('cp "$backup_file" "$target_file"', self.src)

    def test_yaml_merge_checks_pyyaml_first(self):
        self.assertIn('python3 -c "import yaml" 2>/dev/null', self.src)
        self.assertIn("PyYAML is not installed - skipping YAML merge", self.src)


class DocumentationConsistencyTests(unittest.TestCase):
    """M-3/M-4: shipped capability counts match the shipped data files."""

    def test_readme_mcp_count_matches_roadmap(self):
        readme = (REPO_DIR / "README.md").read_text()
        servers = json.loads(
            (REPO_DIR / "plugin-catalog" / "mcp-servers.json").read_text()
        )["servers"]
        m = re.search(r"roadmap\*\* of (\d+) candidate MCP servers", readme)
        self.assertIsNotNone(m, "README must state the MCP roadmap size")
        self.assertEqual(int(m.group(1)), len(servers),
                         "README MCP count must match mcp-servers.json")

    def test_readme_skill_count_matches_index(self):
        readme = (REPO_DIR / "README.md").read_text()
        index = json.loads((UI_DIR / "skills" / "all-skills.json").read_text())
        m = re.search(r"\*{2}([\d,]+) specialized skills/agents\*{2}", readme)
        self.assertIsNotNone(m, "README must state the index size")
        stated = int(m.group(1).replace(",", ""))
        self.assertEqual(stated, index["total_skills"],
                         "README skill count must match all-skills.json")

    def test_universal_prompt_no_stale_counts(self):
        prompt = (UI_DIR / "prompts" / "universal-system-prompt.txt").read_text()
        self.assertNotIn("2,884", prompt, "universal prompt carries a stale count")
        self.assertRegex(prompt, r"3,000\+ curated skills")

    def test_registry_stats_match_index(self):
        registry = json.loads((UI_DIR / "skills" / "agent-registry.json").read_text())
        index = json.loads((UI_DIR / "skills" / "all-skills.json").read_text())
        by_type = registry["stats"]["by_type"]
        self.assertEqual(by_type.get("skill"), index["total_skills"])
        self.assertEqual(registry["stats"]["total"],
                         sum(by_type.values()))


if __name__ == "__main__":
    unittest.main()
