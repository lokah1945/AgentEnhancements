"""Regression tests for the operational scripts.

* dispatch.sh must not route on short keywords found inside other words
  (pre-existing bug, not a regression of 07da4e00..df154215).
* mcp-test.sh is_configured must skip a malformed host config instead of
  crashing and hiding a valid entry in a later file.
* scripts/gen_agency_catalog.py must refresh agency entries that already
  exist in catalog.json (pre-existing since 6eebfc57).
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import REPO_DIR, UI_DIR, load_module, run

DISPATCH = UI_DIR / "scripts" / "dispatch.sh"
MCP_TEST = UI_DIR / "scripts" / "mcp-test.sh"
GEN_AGENCY = REPO_DIR / "scripts" / "gen_agency_catalog.py"


def dispatch_match(prompt):
    code, out, err = run(["bash", str(DISPATCH), "--dry-run", prompt])
    if code != 0:
        raise AssertionError(f"dispatch failed for {prompt!r}: {err}")
    for line in out.splitlines():
        if line.startswith("Skill match"):
            return line.split(":", 1)[1].strip().split()[0]
    raise AssertionError(f"no Skill match line for {prompt!r}:\n{out}")


class DispatchWordBoundaryTests(unittest.TestCase):
    ABSTAIN = [
        "register a new user endpoint",   # "gis" inside "register"
        # "fix the logistics module" now correctly matches karpathy-skills (word boundary "fix")
        "improve community docs",         # "unity" inside "community"
        "add an opportunity model",       # "unity" inside "opportunity"
        "nerd font install",              # "erd" inside "nerd"
        "add a sequence number column",   # bare "sequence"
    ]
    ROUTE = [
        ("build a gis layer", "gis"),
        ("unity game", "game-development"),
        ("draw an erd", "diagram-design"),
        ("draw a sequence diagram", "diagram-design"),
        ("make a beautiful pitch deck", "ppt-master"),
        ("write a prd for the new feature", "product"),
        ("answer this rfp", "sales"),
        ("set up a ppc budget", "paid-media"),
        ("hire an sre", "engineering"),
    ]

    def test_substrings_inside_words_abstain(self):
        for prompt in self.ABSTAIN:
            with self.subTest(prompt=prompt):
                self.assertEqual(dispatch_match(prompt), "none")

    def test_whole_word_keywords_still_route(self):
        for prompt, slug in self.ROUTE:
            with self.subTest(prompt=prompt):
                self.assertEqual(dispatch_match(prompt), slug)


class McpTestIsConfiguredTests(unittest.TestCase):
    SERVER = "graphrag-mcp"
    MALFORMED = {
        "top-level list": "[]",
        "server entry is a string": json.dumps({"mcpServers": {SERVER: "str"}}),
        "mcp key is a list": json.dumps({"mcp": []}),
        "gateway entry is a list": json.dumps({"mcpServers": {"agent-enhancements": []}}),
    }

    def setUp(self):
        if (REPO_DIR / ".mcp.json").exists():
            self.skipTest("a project .mcp.json would mask the host configs")
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.env = {
            "HOME": str(self.home),
            "CODEX_HOME": str(self.home / ".codex"),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
        env.update(self.env)
        proc = subprocess.run(["bash", str(MCP_TEST), "--server", self.SERVER],
                              capture_output=True, text=True, env=env, timeout=60)
        return proc.returncode, proc.stdout, proc.stderr

    def test_malformed_claude_config_does_not_hide_codex_entry(self):
        codex = self.home / ".codex"
        codex.mkdir()
        (codex / "config.toml").write_text(
            f'[mcp_servers.{self.SERVER}]\ncommand = "python"\n', encoding="utf-8")
        for label, text in self.MALFORMED.items():
            with self.subTest(label):
                (self.home / ".claude.json").write_text(text, encoding="utf-8")
                code, out, err = self._run()
                self.assertNotIn("Traceback", err)
                self.assertEqual(code, 0, f"{label}: {out}\n{err}")
                self.assertIn(f"{self.SERVER} (configured)", out)

    def test_only_malformed_configs_report_not_configured(self):
        (self.home / ".claude.json").write_text(
            self.MALFORMED["server entry is a string"], encoding="utf-8")
        code, out, err = self._run()
        self.assertNotIn("Traceback", err)
        self.assertEqual(code, 1, out)
        self.assertIn("not configured", out)


class GenAgencyCatalogUpsertTests(unittest.TestCase):
    def _load(self, tmp):
        mod = load_module("gen_agency_catalog_under_test", GEN_AGENCY)
        mod.CATALOG_DIR = tmp / "agency"
        mod.CATALOG_INDEX = tmp / "catalog.json"
        return mod

    def test_existing_entries_are_refreshed_in_place(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            mod = self._load(tmp)
            stale = {
                "id": "agency-engineering", "slug": "engineering",
                "name": "The Agency — Engineering (1 personas)",
                "category": "agency", "trigger_keywords": ["old"],
                "sub_skills_count": 1, "hand_note": "keep me",
            }
            other = {"id": "plain-plugin", "category": "code", "name": "Plain"}
            obsolete = {"id": "agency-obsolete", "category": "agency", "name": "Gone"}
            (tmp / "catalog.json").write_text(json.dumps({
                "categories": ["code"], "total_plugins": 3,
                "skills": [other, stale, obsolete],
            }), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mod.main(), 0)

            catalog = json.loads((tmp / "catalog.json").read_text(encoding="utf-8"))
            ids = [e["id"] for e in catalog["skills"]]
            self.assertEqual(ids[:2], ["plain-plugin", "agency-engineering"])
            self.assertNotIn("agency-obsolete", ids)
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(catalog["total_plugins"], len(ids))
            self.assertIn("agency", catalog["categories"])
            manifest = json.loads(
                (tmp / "agency" / "engineering.json").read_text(encoding="utf-8"))
            entry = catalog["skills"][1]
            self.assertEqual(entry["name"], manifest["name"])
            self.assertEqual(entry["trigger_keywords"], manifest["trigger_keywords"])
            self.assertEqual(entry["sub_skills_count"], len(manifest["sub_skills"]))
            self.assertEqual(entry["hand_note"], "keep me")

    def test_committed_catalog_matches_agency_manifests(self):
        catalog = json.loads(
            (REPO_DIR / "plugin-catalog" / "catalog.json").read_text(encoding="utf-8"))
        entries = [e for e in catalog["skills"] if e.get("category") == "agency"]
        self.assertTrue(entries)
        for entry in entries:
            with self.subTest(entry["id"]):
                manifest = json.loads((REPO_DIR / entry["manifest_path"]).read_text(
                    encoding="utf-8"))
                self.assertEqual(entry["name"], manifest["name"])
                self.assertEqual(entry["trigger_keywords"], manifest["trigger_keywords"])
                self.assertEqual(entry["sub_skills_count"], len(manifest["sub_skills"]))


if __name__ == "__main__":
    unittest.main()
