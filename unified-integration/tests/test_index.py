"""Invariants for the unified skills index (all-skills.json)."""
import json
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR

INDEX = UI_DIR / "skills" / "all-skills.json"


class IndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(INDEX.read_text())

    def test_top_level_schema(self):
        for key in ["version", "sources", "skills", "total_skills", "categories",
                    "agents_supported", "agent_skill_counts", "last_updated"]:
            self.assertIn(key, self.data, f"missing key: {key}")

    def test_total_matches_len(self):
        self.assertEqual(self.data["total_skills"], len(self.data["skills"]))

    def test_every_skill_has_required_fields(self):
        for skill in self.data["skills"]:
            for field in ["name", "category", "description", "risk", "source",
                          "tags", "tools", "when_to_use"]:
                self.assertIn(field, skill, f"skill {skill.get('name')} missing {field}")

    def test_categories_count_matches_skills(self):
        total = sum(self.data["categories"].values())
        self.assertEqual(total, len(self.data["skills"]))

    def test_agent_counts_are_subset_of_tools(self):
        for skill in self.data["skills"]:
            for tool in skill["tools"]:
                self.assertIn(tool, self.data["agent_skill_counts"])

    def test_agent_skill_counts_values_positive(self):
        for tool, count in self.data["agent_skill_counts"].items():
            self.assertGreater(count, 0, f"{tool} has count {count}")


if __name__ == "__main__":
    unittest.main()
