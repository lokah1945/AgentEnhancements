"""Exercise generated inventory and drift checks against small canonical inputs."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/generate_capability_counts.py"


class CapabilityCountsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ae-counts-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = {key: value for key, value in os.environ.items()
                    if key in ("PATH", "LANG", "SYSTEMROOT")}
        self.env.update(HOME=str(self.root / "home"),
                        AGENT_MEMORY_ROOT=str(self.root / "memory"),
                        XDG_CONFIG_HOME=str(self.root / "config"),
                        XDG_DATA_HOME=str(self.root / "data"),
                        CODEX_HOME=str(self.root / "codex"))
        skills = [
            {"name": "alpha", "source": "A", "source_path": "vendor-a/skills/alpha/SKILL.md"},
            {"name": "beta", "source": "A", "source_path": "vendor-a/skills/beta/SKILL.md"},
            {"name": "observer", "source": "B", "source_path": "vendor-b/SKILL.md"},
        ]
        for item in skills:
            self.write(item["source_path"], "---\nname: fixture\n---\n")
        self.write("vendor-a/skills/overridden/SKILL.md", "overridden record")
        self.write("vendor-a/skills/alpha/references/nested/SKILL.md", "not an aggregated source record")
        self.write_json("unified-integration/skills/all-skills.json", {
            "skills": skills, "sources": ["A", "B"], "total_skills": 3,
        })
        plugins = [
            {"slug": "one", "category": "code", "status": "integrated",
             "vendored": True, "source_url": "https://example.test/one"},
            {"slug": "two", "category": "research", "status": "integrated-ready",
             "vendored": False, "source_url": "https://example.test/two"},
        ]
        self.write_json("plugin-catalog/catalog.json", {"skills": plugins, "total_plugins": 2})
        servers = [
            {"id": "local", "status": "built", "priority": "P1"},
            {"id": "router", "status": "built", "priority": "P1"},
            {"id": "external-built", "status": "built", "priority": "P0"},
            {"id": "remote", "status": "to-install", "priority": "P2"},
        ]
        self.write_json("plugin-catalog/mcp-servers.json", {"servers": servers})
        self.write("unified-integration/scripts/registry.py", (
            'DEFAULT_NATIVE_SOURCES = ("A",)\n'
            'BUILT_IN_CAPABILITIES = [{"id": "capability:memory"}, {"id": "capability:registry"}]\n'
        ))
        self.write("unified-integration/scripts/api_config.py", (
            'BUILTINS = ("local", "router")\n'
            'DEFAULT_DISABLED = frozenset({"router"})\n'
        ))
        self.write("unified-integration/scripts/link-skills.sh", (
            'DEFAULT_SOURCES="A"\nCURATED_SOURCES="B"\n'
        ))
        self.write("LICENSE", "| vendor-a/ | upstream | MIT |\n| vendor-b/ | upstream | MIT |\n")
        for name in ("README.md", "README_INTEGRATION.md"):
            self.write(name, "# Fixture\n\n<!-- ae:counts:summary:begin -->\nold\n<!-- ae:counts:summary:end -->\n")
        self.write("docs/CAPABILITY_COUNTS.md", "# Inventory\n\n<!-- ae:counts:inventory:begin -->\nold\n<!-- ae:counts:inventory:end -->\n")

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def write_json(self, name, value):
        self.write(name, json.dumps(value))

    def invoke(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *args],
            text=True, capture_output=True, env=self.env, timeout=20,
        )

    def test_inventory_distinguishes_raw_records_status_and_bundled_backends(self):
        result = self.invoke("--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["skills"], {"total": 3, "sources": 2, "raw_records": 4,
                                         "collapsed_records": 1,
                                         "by_source": {"A": 2, "B": 1},
                                         "raw_by_source": {"A": 3, "B": 1}})
        self.assertEqual(data["mcp"]["by_status"], {"built": 3, "to-install": 1})
        self.assertEqual(data["mcp"]["bundled_backends"], 2)
        self.assertEqual(data["mcp"]["default_enabled_backends"], 1)
        self.assertEqual(data["mcp"]["external_built"], ["external-built"])
        self.assertEqual(data["plugins"]["by_status"], {"integrated": 1, "integrated-ready": 1})
        self.assertEqual(data["native"]["default_skills"], 2)
        self.assertEqual(data["native"]["curated_skills"], 1)
        self.assertEqual(data["registry_entries"], 11)

    def test_write_is_repeatable_and_check_detects_generated_drift(self):
        self.assertEqual(self.invoke("--write").returncode, 0)
        path = self.root / "README.md"
        before = path.read_bytes(), path.stat().st_mtime_ns
        self.assertEqual(self.invoke("--write").returncode, 0)
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
        self.assertEqual(self.invoke("--check").returncode, 0)
        path.write_text(path.read_text().replace("3 specialized", "99 specialized"))
        result = self.invoke("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README.md", result.stderr)

    def test_repository_description_is_generated_and_checked(self):
        self.assertEqual(self.invoke("--write").returncode, 0)
        path = self.root / "docs/repository-description.txt"
        self.assertTrue(path.is_file(), "remote description needs a canonical generated value")
        self.assertIn("3 skills", path.read_text())
        path.write_text("Old description with 999 skills\n")
        result = self.invoke("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository-description.txt", result.stderr)

    def test_check_rejects_conflicting_claim_outside_generated_blocks(self):
        self.assertEqual(self.invoke("--write").returncode, 0)
        path = self.root / "README_INTEGRATION.md"
        path.write_text(path.read_text() + "\nThe library has 999 unique skills.\n")
        result = self.invoke("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("README_INTEGRATION.md", result.stderr)
        self.assertIn("claim", result.stderr.lower())

    def test_historical_evidence_is_not_rewritten_or_checked_as_current_claim(self):
        self.write("docs/audit/old.md", "Historical: 999 unique skills.\n")
        self.assertEqual(self.invoke("--write").returncode, 0)
        self.assertEqual(self.invoke("--check").returncode, 0)
        self.assertEqual((self.root / "docs/audit/old.md").read_text(), "Historical: 999 unique skills.\n")

    def test_current_claim_check_accepts_punctuation_without_a_numeric_claim(self):
        self.assertEqual(self.invoke("--write").returncode, 0)
        path = self.root / "README.md"
        path.write_text(path.read_text() + "\nSkills, MCP servers and plugins share a registry.\n")
        result = self.invoke("--check")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_count_generation_refuses_disagreement_between_native_defaults(self):
        self.write("unified-integration/scripts/link-skills.sh", 'DEFAULT_SOURCES="B"\nCURATED_SOURCES="B"\n')
        result = self.invoke("--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("default", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
