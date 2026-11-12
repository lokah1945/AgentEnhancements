"""Routing tests for the Anthropic document/technical skills in dispatch.sh.

The vendored anthropic-skills must be reachable from natural language in
both English and Indonesian, alongside the pre-existing plugin routing.
"""
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import REPO_DIR, run

DISPATCH = UI_DIR_DISPATCH = Path(__file__).resolve().parent.parent / "scripts" / "dispatch.sh"

CASES = [
    # (prompt, expected slug prefix)
    ("extract the form fields from invoice.pdf", "anthropic-skills/skills/pdf/"),
    ("create a word document report", "anthropic-skills/skills/docx/"),
    ("buat dokumen word laporan keuangan", "anthropic-skills/skills/docx/"),
    ("build an mcp server for my database", "anthropic-skills/skills/mcp-builder/"),
    ("make a new skill for deploying apps", "anthropic-skills/skills/skill-creator/"),
    ("test my webapp with playwright screenshots", "anthropic-skills/skills/webapp-testing/"),
    ("clean this excel spreadsheet and add formulas", "anthropic-skills/skills/xlsx/"),
    ("convert quarterly.pptx into a summary", "anthropic-skills/skills/pptx/"),
    ("integrate the claude api in my app", "anthropic-skills/skills/claude-api/"),
    # Pre-existing routing must keep working
    ("clone this app for me", "plugin-catalog/code/replica-skill/"),
    ("make a beautiful pitch deck", "plugin-catalog/design/ppt-master/"),
]


class DispatchAnthropicTests(unittest.TestCase):
    def test_routing_table(self):
        for prompt, expected_path in CASES:
            with self.subTest(prompt=prompt):
                code, out, err = run(
                    ["bash", str(DISPATCH), "--dry-run", prompt])
                self.assertEqual(code, 0, err)
                self.assertIn("Skill match", out)
                self.assertIn(expected_path, out,
                              f"{prompt!r} did not route to {expected_path}\n{out}")

    def test_explicit_skill_prefix_overrides_heuristics(self):
        code, out, err = run(
            ["bash", str(DISPATCH), "--dry-run", "[skill:docx] anything"])
        self.assertEqual(code, 0, err)
        self.assertIn("anthropic-skills/skills/docx/", out)

    def test_usage_requires_prompt(self):
        code, _, _ = run(["bash", str(DISPATCH)])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
