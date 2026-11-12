"""Tests for the unified capability registry (scripts/registry.py).

Covers the all-in-one mapping surface: skills (aggregated index),
plugins (catalog), MCP servers (roadmap) and built-in capabilities,
plus the anthropic-skills integration that motivated it.
"""
import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import REPO_DIR, UI_DIR, load_module, run

REGISTRY_SCRIPT = UI_DIR / "scripts" / "registry.py"


class RegistryModuleTests(unittest.TestCase):
    """Unit tests against the committed index and catalog."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_module("registry_test", REGISTRY_SCRIPT)

    def test_skills_from_committed_index(self):
        entries = self.mod.load_skill_entries()
        self.assertGreater(len(entries), 3000)
        names = {e["name"] for e in entries}
        # The official Anthropic document skills must be in the index.
        for expected in ("docx", "pdf", "pptx", "xlsx", "mcp-builder",
                         "skill-creator", "webapp-testing", "claude-api"):
            self.assertIn(expected, names)

    def test_anthropic_skills_are_natively_linked_by_default(self):
        entries = [e for e in self.mod.load_skill_entries()
                   if e["source"] == "anthropic-skills"]
        self.assertEqual(len(entries), 19)
        for entry in entries:
            self.assertTrue(entry["natively_linked_by_default"])
            self.assertTrue(entry["description"].strip())
            self.assertIn("anthropic-skills/skills/", entry["source_path"])

    def test_no_block_scalar_placeholder_descriptions(self):
        markers = {">", ">-", ">+", "|", "|-", "|+"}
        for entry in self.mod.load_skill_entries():
            self.assertNotIn((entry["description"] or "").strip(), markers,
                             f"{entry['name']} kept a block-scalar placeholder")

    def test_plugin_and_mcp_entries(self):
        plugins = self.mod.load_plugin_entries()
        mcps = self.mod.load_mcp_entries()
        self.assertEqual(len(plugins), 21)
        self.assertGreaterEqual(len(mcps), 36)
        self.assertIn("plugin:anthropic-skills", {p["id"] for p in plugins})
        self.assertIn("plugin:ppt-master", {p["id"] for p in plugins})

    def test_capability_entries_have_usage(self):
        caps = self.mod.load_capability_entries()
        self.assertGreaterEqual(len(caps), 7)
        for cap in caps:
            self.assertTrue(cap["usage"].strip(), f"{cap['name']} lacks usage")

    def test_document_skill_ranks_first_for_format_queries(self):
        entries = self.mod.load_skill_entries()
        cases = {
            "create a powerpoint presentation from this data": "pptx",
            "clean up this excel spreadsheet and add formulas": "xlsx",
            "extract text from a scanned pdf and merge two forms": "pdf",
            "buat dokumen word laporan keuangan": "docx",
            "build an mcp server for my api": "mcp-builder",
        }
        for query, expected in cases.items():
            ranked = self.mod.rank_entries(entries, query, limit=3)
            self.assertTrue(ranked, f"no matches for {query!r}")
            self.assertEqual(ranked[0][1]["name"], expected,
                             f"{query!r} -> {[e['name'] for _, e in ranked]}")

    def test_rank_entries_empty_query(self):
        self.assertEqual(self.mod.rank_entries(self.mod.load_skill_entries(), ""), [])

    def test_build_writes_registry_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "agent-registry.json"
            code = run([sys.executable, str(REGISTRY_SCRIPT), "build",
                        "--out", str(out), "--quiet"])[0]
            self.assertEqual(code, 0)
            data = json.loads(out.read_text())
            types = {e["type"] for e in data["entries"]}
            self.assertEqual(types, {"skill", "plugin", "mcp", "capability"})
            self.assertEqual(data["stats"]["by_type"]["plugin"], 21)
            self.assertGreaterEqual(data["stats"]["by_type"]["skill"], 3000)
            self.assertGreaterEqual(data["stats"]["by_type"]["mcp"], 36)
            self.assertGreaterEqual(data["stats"]["by_type"]["capability"], 7)


class RegistryCliTests(unittest.TestCase):
    """End-to-end CLI coverage (human and JSON output)."""

    def _run(self, *args):
        return run([sys.executable, str(REGISTRY_SCRIPT), *args])

    def test_map_json_is_valid_and_structured(self):
        code, out, err = self._run("map", "create a word document", "--json")
        self.assertEqual(code, 0, err)
        plan = json.loads(out)
        for key in ("task", "skills", "plugins", "mcp_servers",
                    "always_available", "hints"):
            self.assertIn(key, plan)
        self.assertEqual(plan["skills"][0]["name"], "docx")
        self.assertTrue(plan["skills"][0]["natively_linked_by_default"])

    def test_map_human_output(self):
        code, out, err = self._run("map", "extract pdf form fields")
        self.assertEqual(code, 0, err)
        self.assertIn("Capability Map", out)
        self.assertIn("pdf", out)

    def test_search_type_filter(self):
        code, out, err = self._run("search", "pdf", "--type", "capability")
        self.assertEqual(code, 0, err)
        self.assertNotIn("skill, anthropic-skills", out)

    def test_show_by_id_and_name(self):
        code, out, _ = self._run("show", "skill:docx")
        self.assertEqual(code, 0)
        self.assertIn("anthropic-skills", out)
        code, out, _ = self._run("show", "mcp-builder")
        self.assertEqual(code, 0)
        self.assertIn("anthropic-skills/skills/mcp-builder/SKILL.md", out)

    def test_show_unknown_fails_cleanly(self):
        code, _, err = self._run("show", "definitely-not-a-skill-xyz")
        self.assertEqual(code, 1)
        self.assertIn("not found", err)

    def test_stats_reports_all_types(self):
        code, out, _ = self._run("stats")
        self.assertEqual(code, 0)
        for expected in ("skill", "plugin", "mcp", "capability"):
            self.assertIn(expected, out)

    def test_list_type_plugin(self):
        code, out, _ = self._run("list", "--type", "plugin")
        self.assertEqual(code, 0)
        self.assertIn("plugin:anthropic-skills", out)

    def test_unknown_command_fails(self):
        code, _, _ = self._run("explode")
        self.assertEqual(code, 2)

    def test_committed_registry_in_repo(self):
        committed = UI_DIR / "skills" / "agent-registry.json"
        self.assertTrue(committed.is_file(), "agent-registry.json must be committed")
        data = json.loads(committed.read_text())
        self.assertEqual(data["stats"]["by_type"]["plugin"], 21)


if __name__ == "__main__":
    unittest.main()
