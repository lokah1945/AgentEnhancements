"""Regression tests for the 2026-11-15 audit remediation batch.

Covers: catalog cross-reference validation (AE-19), catalog-test agency
coverage (AE-07), REA upstream identity + honest abstain routing,
task-router python denylist + default-off opt-in (AE-10), and the
timestamp-preservation contracts (AE-14).
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

import os
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import REPO_DIR, UI_DIR, run

SCRIPTS = UI_DIR / "scripts"


class CatalogCrossReferenceTests(unittest.TestCase):
    """AE-19: catalog <-> roadmap refs must be validated, not assumed."""

    def test_no_dangling_mcp_refs(self):
        cat = json.loads((REPO_DIR / "plugin-catalog/catalog.json").read_text())
        road = {s["id"] for s in json.loads(
            (REPO_DIR / "plugin-catalog/mcp-servers.json").read_text())["servers"]}
        dangling = [(p["id"], m) for p in cat["skills"]
                    for m in p.get("mcp_servers", []) if m not in road]
        self.assertEqual(dangling, [])

    def test_validator_catches_dangling_ref(self):
        """The validator must fail on a fabricated suggested server."""
        import tempfile
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "catalog_validate", SCRIPTS / "catalog-validate.py")
        catalog_validate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(catalog_validate)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "plugin-catalog").mkdir()
            (root / "plugin-catalog/mcp-servers.json").write_text(
                json.dumps({"servers": [{"id": "real-mcp"}]}))
            catdir = root / "plugin-catalog/code"
            catdir.mkdir()
            (catdir / "bad.json").write_text(json.dumps({
                "id": "code-bad", "slug": "bad", "category": "code",
                "status": "integrated-ready",
                "mcp_servers_suggested": ["ghost-mcp"],
                "skill_files": [],
            }))
            errors, warnings = [], []
            catalog_validate.validate_category(
                root, "code", errors, warnings, {"real-mcp"})
            self.assertTrue(any("ghost-mcp" in e for e in errors), errors)

    def test_nexus_subskill_paths_resolve(self):
        nexus = json.loads(
            (REPO_DIR / "plugin-catalog/agency/nexus.json").read_text())
        self.assertTrue(nexus["sub_skills"])
        for sub in nexus["sub_skills"]:
            self.assertTrue((REPO_DIR / sub["path"]).is_file(),
                            f"missing {sub['path']} for {sub['slug']}")


class CatalogTestAgencyTests(unittest.TestCase):
    """AE-07: catalog-test.sh must cover agency packs."""

    @unittest.skipIf(os.name == 'nt', "jq not available on Windows")
    def test_agency_slug_smoke(self):
        code, out, err = run(["bash", str(SCRIPTS / "catalog-test.sh"), "nexus"])
        self.assertEqual(code, 0, err)
        self.assertIn("Test selesai untuk nexus", out)


class RoutingTests(unittest.TestCase):
    """REA identity + honest abstain fallback (master prompt / ROUTER_POLICY 1.2)."""

    def _route(self, prompt):
        code, out, err = run(["bash", str(SCRIPTS / "dispatch.sh"),
                              "--dry-run", prompt])
        self.assertEqual(code, 0, err)
        for line in out.splitlines():
            if line.startswith("Skill match"):
                return line.split(":", 1)[1].strip()
        self.fail(f"no Skill match line in output:\n{out}")

    def test_rea_routes_reverse_engineering(self):
        self.assertIn("rea", self._route("reverse engineer this APK"))
        self.assertIn("rea", self._route("decompile this electron app"))

    def test_generic_investigation_goes_to_understand_anything(self):
        self.assertIn("understand-anything",
                      self._route("investigate why the API returns 502"))

    def test_unmatched_prompt_abstains(self):
        self.assertIn("none", self._route("write a haiku about the sea"))

    def test_clone_still_routes_to_replica(self):
        self.assertIn("replica-skill", self._route("clone this app for me"))

    def test_rea_manifest_matches_upstream_identity(self):
        rea = json.loads((REPO_DIR / "plugin-catalog/research/rea.json").read_text())
        self.assertEqual(rea["name"], "REA (Reverse Engineer Anything)")
        self.assertEqual(rea["source"]["license"], "MIT")
        self.assertNotIn("Reason-Explain-Act", json.dumps(rea))

    def test_rea_catalog_role_matches_reverse_engineering_guide(self):
        catalog = json.loads((REPO_DIR / "plugin-catalog/catalog.json").read_text())
        rea = next(item for item in catalog["orchestrators"] if item["slug"] == "rea")
        self.assertEqual(rea["role"], "reverse-engineering")
        self.assertIn("binary", rea["for_mode"])


class TaskRouterHardeningTests(unittest.TestCase):
    """AE-10: python denylist + default-off."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(UI_DIR / "mcp-servers"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tr_server", UI_DIR / "mcp-servers/task-router-mcp/server.py")
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def test_python_root_wipe_refused(self):
        for code in (
            'import shutil; shutil.rmtree("/")',
            'import os; os.removedirs("/")',
            'import os; os.system("rm -rf /")',
        ):
            result = self.mod.TOOLS["dispatch"](kind="python", code=code)
            self.assertIn("error", result, code)
            self.assertIn("refused", result["error"])

    def test_python_benign_still_runs(self):
        task = self.mod.TOOLS["dispatch"](kind="python", code="print(2+2)")
        self.assertIn("task_id", task)

    def test_task_router_hidden_by_default(self):
        sys.path.insert(0, str(SCRIPTS))
        os.environ["AGENT_ENHANCEMENTS_API_FILE"] = "/nonexistent.json"
        try:
            import api_config
            self.assertFalse(api_config.server_state("task-router-mcp")["visible"])
            self.assertEqual(
                api_config.server_state("task-router-mcp")["reason"],
                "disabled_by_default")
            self.assertTrue(api_config.server_state("embeddings-mcp")["visible"])
        finally:
            del os.environ["AGENT_ENHANCEMENTS_API_FILE"]


class TimestampPreservationTests(unittest.TestCase):
    """AE-14: builders must not rewrite when only the timestamp changes."""

    def test_registry_build_preserves_timestamp(self):
        import tempfile
        sys.path.insert(0, str(SCRIPTS))
        import registry
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "reg.json"
            self.assertEqual(registry.cmd_build(str(out), quiet=True), 0)
            first = json.loads(out.read_text())
            import time
            time.sleep(0.05)
            self.assertEqual(registry.cmd_build(str(out), quiet=True), 0)
            second = json.loads(out.read_text())
            self.assertEqual(first["generated_at"], second["generated_at"])


if __name__ == "__main__":
    unittest.main()
