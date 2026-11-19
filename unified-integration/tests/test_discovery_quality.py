"""Discovery regressions through real catalog and prompt-submit behavior.

These catch divergent loader ranking/abstention, untranslated domain words,
and requested-host aliases silently excluding compatible skills. The corpus
benchmark is an independent measurement command, not a prompt-to-ID router.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discovery_benchmark import FIXTURE, import_file, isolated_environment
from helpers import REPO_DIR, UI_DIR


class DiscoveryQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.isolation = isolated_environment(REPO_DIR)
        cls.environment = cls.isolation.__enter__()
        scripts = UI_DIR / "scripts"
        sys.path.insert(0, str(scripts))
        cls.registry = import_file("discovery_quality_registry", scripts / "registry.py")
        cls.loader_module = import_file("discovery_quality_loader", scripts / "load-skills.py")
        cls.loader = cls.loader_module.SkillsLoader("codex")
        cls.entries = cls.registry.load_skill_entries()

    @classmethod
    def tearDownClass(cls):
        cls.isolation.__exit__(None, None, None)

    def test_bilingual_fixture_has_resolving_acceptable_alternatives(self):
        cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), 50)
        self.assertEqual(len({case["id"] for case in cases}), 50)
        self.assertEqual(sum(case["language"] == "en" for case in cases), 25)
        self.assertEqual(sum(case["language"] == "id" for case in cases), 25)
        known = {entry["id"] for entry in self.registry.load_all_entries()}
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertLessEqual(set(case["acceptable_ids"]), known)
                if case["kind"] in {"positive", "ambiguous"}:
                    self.assertTrue(case["acceptable_ids"])
                if case.get("unavailable_id"):
                    self.assertTrue(case["unavailable_id"] in known, case["unavailable_id"])

    def test_loader_prefers_document_format_over_generic_workflow_words(self):
        cases = (
            ("Prepare a formal offer letter as a Word document.", "docx"),
            ("Clean this Excel workbook and add formulas for the totals.", "xlsx"),
            ("Ubah hasil kuartalan menjadi presentasi PowerPoint.", "pptx"),
            ("Bangun server MCP yang menyediakan API inventaris kami sebagai tool.", "mcp-builder"),
        )
        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                matches = self.loader.find_skills(prompt)
                self.assertTrue(matches)
                self.assertEqual(matches[0]["name"], expected)

    def test_loader_abstains_when_ordinary_tools_are_sufficient(self):
        for prompt in (
            "Thanks, that answers my question.", "What is 17 multiplied by 23?",
            "Berapa hasil 17 dikali 23?", "Translate good morning into Indonesian.",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual([item["name"] for item in self.loader.find_skills(prompt)], [])

    def test_requested_agent_alias_keeps_host_compatible_workflow(self):
        for agent in ("codex", "Codex", "codex-cli"):
            with self.subTest(agent=agent):
                matches = self.loader_module.SkillsLoader(agent).find_skills("requesting-code-review")
                self.assertTrue(matches)
                self.assertEqual(matches[0]["name"], "requesting-code-review")

    def test_registry_understands_indonesian_technical_domain_words(self):
        cases = (
            ("arsitektur perangkat lunak", {"architecture", "software-architecture"}),
            ("graf pengetahuan entitas hubungan", {"agency-engineering-knowledge-graph-engineer"}),
        )
        for prompt, acceptable in cases:
            with self.subTest(prompt=prompt):
                ranked = self.registry.rank_entries(self.entries, prompt, limit=3)
                self.assertTrue(acceptable & {entry["name"] for _, entry in ranked}, ranked)

    def test_actual_prompt_hook_abstains_for_simple_translation(self):
        process = subprocess.run(
            [sys.executable, str(UI_DIR / "scripts/runtime.py"), "codex"],
            input=json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "discovery-negative",
                              "cwd": str(REPO_DIR), "prompt": "Translate good morning into Indonesian."}),
            text=True, capture_output=True, env=self.environment, timeout=20,
        )
        self.assertEqual(process.returncode, 0)
        self.assertEqual(process.stderr, "")
        self.assertEqual(process.stdout.strip(), "")

    def test_unconfigured_mcp_is_not_advertised_callable(self):
        entries = self.registry.usable_entries(self.registry.load_all_entries())
        visible = {entry["id"] for entry in entries}
        for identifier in ("mcp:figma-mcp", "mcp:tavily-mcp"):
            with self.subTest(identifier=identifier):
                self.assertNotIn(identifier, visible)
                entry = self.registry.find_entry(identifier)
                state = self.registry.entry_readiness(entry)
                self.assertEqual(state["ready"], "no")
                self.assertTrue(state["blocker"])

    def test_external_built_server_does_not_claim_bundled_activation(self):
        from api_config import BUILTINS
        for entry in self.registry.load_mcp_entries():
            if entry["status"] == "built" and entry["name"] not in BUILTINS:
                self.assertNotIn("loaded automatically", entry["activation"])
                self.assertIn("command", entry["activation"])

    def test_missing_skill_files_are_not_reported_ready(self):
        entry = {"type": "skill", "name": "missing-discovery-skill",
                 "path": "unified-integration/skills/missing-discovery-skill/SKILL.md",
                 "source_path": "missing-source/SKILL.md"}
        state = self.registry.entry_readiness(entry)
        self.assertEqual(state["ready"], "no")
        self.assertTrue(state["blocker"])

    def test_vendored_source_remains_available_without_aggregation(self):
        entry = {"type": "skill", "name": "docx", "path": "missing-aggregation/SKILL.md",
                 "source_path": "anthropic-skills/skills/docx/SKILL.md"}
        state = self.registry.entry_readiness(entry)
        self.assertEqual(state["ready"], "yes")
        self.assertNotIn("natively linked", state.get("how", ""))

    def test_skill_path_override_accepts_files_but_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory(prefix="ae-discovery-files-") as directory:
            root = Path(directory)
            allowed = root / "skills"
            allowed.mkdir()
            local = allowed / "SKILL.md"
            local.write_text("Local skill guidance", encoding="utf-8")
            outside = root / "outside.md"
            outside.write_text("Outside guidance", encoding="utf-8")
            escaped = allowed / "escape.md"
            escaped.symlink_to(outside)
            with patch.dict(os.environ, {"AGENT_SKILLS_DIR": str(allowed)}):
                for path, expected in ((local, "yes"), (outside, "no"), (escaped, "no")):
                    with self.subTest(path=path):
                        state = self.registry.entry_readiness({"type": "skill", "name": "local",
                                                               "path": str(path)})
                        self.assertEqual(state["ready"], expected)
                local.unlink()
                self.assertEqual(self.registry.entry_readiness({
                    "type": "skill", "name": "local", "path": str(local),
                })["ready"], "no")

    def test_foreign_native_name_does_not_claim_the_registry_skill_loaded(self):
        with tempfile.TemporaryDirectory(prefix="ae-discovery-native-") as directory:
            root = Path(directory)
            foreign = root / "docx"
            foreign.mkdir()
            (foreign / "SKILL.md").write_text("Unrelated user-owned guidance", encoding="utf-8")
            with patch.dict(os.environ, {"AGENT_SKILLS_NATIVE_TARGETS": str(root)}):
                state = self.registry.entry_readiness({
                    "type": "skill", "name": "docx", "natively_linked_by_default": True,
                    "source_path": "anthropic-skills/skills/docx/SKILL.md",
                })
                self.assertEqual(state["ready"], "yes")
                self.assertNotIn("natively linked", state.get("how", ""))

    def test_native_link_to_the_selected_skill_is_reported_loaded(self):
        with tempfile.TemporaryDirectory(prefix="ae-discovery-linked-") as directory:
            root = Path(directory)
            source = REPO_DIR / "anthropic-skills/skills/docx"
            (root / "docx").symlink_to(source, target_is_directory=True)
            with patch.dict(os.environ, {"AGENT_SKILLS_NATIVE_TARGETS": str(root)}):
                state = self.registry.entry_readiness({
                    "type": "skill", "name": "docx", "natively_linked_by_default": True,
                    "source_path": "anthropic-skills/skills/docx/SKILL.md",
                })
                self.assertEqual(state, {"ready": "yes", "how": "natively linked"})


if __name__ == "__main__":
    unittest.main()
