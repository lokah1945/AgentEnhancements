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

    def test_catalog_search_can_find_blocked_entries_in_a_bounded_json_page(self):
        from context_budget import MAX_SEARCH_PAGE, approx_tokens

        command = [sys.executable, str(UI_DIR / 'scripts/registry.py'), 'search',
                   'figma design ' * 500, '--type', 'mcp', '--json']
        default = subprocess.check_output(command, text=True, env=self.environment, timeout=10)
        catalog = subprocess.check_output([*command, '--catalog'], text=True,
                                          env=self.environment, timeout=10)
        self.assertNotIn('mcp:figma-mcp', default)
        figma = next(card for card in json.loads(catalog)['cards'] if card['id'] == 'mcp:figma-mcp')
        self.assertEqual(figma['ready'], 'no')
        self.assertEqual(figma['blocker'], 'not_configured')
        self.assertLessEqual(approx_tokens(catalog), MAX_SEARCH_PAGE)

    def test_missing_skill_files_are_not_reported_ready(self):
        entry = {"type": "skill", "name": "missing-discovery-skill",
                 "path": "unified-integration/skills/missing-discovery-skill/SKILL.md",
                 "source_path": "missing-source/SKILL.md"}
        state = self.registry.entry_readiness(entry)
        self.assertEqual(state["ready"], "no")
        self.assertTrue(state["blocker"])

    def test_offensive_skills_are_labelled_on_every_card(self):
        # Final audit 2026-11-20 (P2): an ordinary staging security request
        # put an "AUTHORIZED USE ONLY" offensive skill first, unlabelled.
        runtime = import_file("discovery_quality_runtime", UI_DIR / "scripts" / "runtime.py")
        cards = runtime.skill_context(
            "codex", "test the security of the login api on our staging server")
        offensive = {s["name"] for s in self.loader.skills_index["skills"] if s.get("risk") == "offensive"}
        lines = [line for line in cards.splitlines() if line.startswith("- ")]
        self.assertTrue(any(line[2:].split(":")[0] in offensive for line in lines), cards)
        for line in lines:
            labelled = "[risk: offensive - needs explicit authorization]" in line
            self.assertEqual(labelled, line[2:].split(":")[0] in offensive, line)
        entry = {"type": "skill", "id": "skill:fixture", "name": "fixture", "risk": "offensive",
                 "path": "missing/SKILL.md"}
        rendered = self.registry._format_card(self.registry._card(entry))
        self.assertIn("risk: offensive - needs explicit authorization", rendered)
        entry["risk"] = "safe"
        self.assertNotIn("risk:", self.registry._format_card(self.registry._card(entry)))

    def test_plugin_guides_are_not_reported_as_built_in_capabilities(self):
        # Final audit 2026-11-20 (P2): every catalog plugin was reported
        # ready "built-in" although AE ships only its guide (CONTRACT 8.1).
        for vendored in ("False", "True"):
            state = self.registry.entry_readiness(
                {"type": "plugin", "name": "fixture-plugin", "vendored": vendored,
                 "path": "plugin-catalog/code/agent-skills-addyosmani/SKILL.md"})
            self.assertEqual(state["ready"], "yes")
            self.assertIn("guide only", state["how"])
            self.assertNotIn("built-in", state["how"])
        self.assertEqual(self.registry.entry_readiness(
            {"type": "capability", "name": "memory"})["how"], "built-in")
        self.assertEqual(self.registry.entry_readiness(
            {"type": "plugin", "path": "missing/SKILL.md"}),
            {"ready": "no", "blocker": "guide_file_unavailable"})

    def test_ready_cards_print_how_they_are_ready(self):
        card = self.registry._card({"type": "plugin", "id": "plugin:fixture",
                                    "name": "fixture", "vendored": "False",
                                    "path": "plugin-catalog/code/agent-skills-addyosmani/SKILL.md"}, score=2.5)
        rendered = self.registry._format_card(card)
        self.assertNotIn("ready: yes ()", rendered)
        self.assertIn("ready: yes (guide only", rendered)
        self.assertNotIn("query term", rendered)

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
