"""Modular skills tree regression tests.

Covers the /skills/ scaffold introduced in the v2 integration round:
- T-1: catalog.json integrity (21 plugins, 5 categories, unique ids/slugs,
       every manifest_path and guide_path resolves).
- T-2: skills/manifest.json stays in sync with plugin-catalog/catalog.json
       (regenerate with scripts/generate_skills_index.py when it drifts).
- T-3: the scaffold script is idempotent - running it twice leaves the tree
       byte-identical (lesson from audit finding H-2).
- T-4: every scaffolded plugin dir is self-contained (SKILL.md + manifest.json
       both resolve through the symlinks).
- T-5: mcp-servers.json description/count consistency with catalog.json.
- T-6: category READMEs exist for all 5 categories and list every plugin slug.
- T-7: .cursorrules routes every cataloged plugin slug (skill table coverage).
- T-8: README_INTEGRATION.md documents every cataloged plugin slug.
"""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import REPO_DIR

CATALOG_PATH = REPO_DIR / "plugin-catalog" / "catalog.json"
MCP_PATH = REPO_DIR / "plugin-catalog" / "mcp-servers.json"
SKILLS_DIR = REPO_DIR / "skills"
SKILLS_MANIFEST = SKILLS_DIR / "manifest.json"
SCAFFOLD_SCRIPT = REPO_DIR / "scripts" / "scaffold_modular_skills.sh"
INDEX_SCRIPT = REPO_DIR / "scripts" / "generate_skills_index.py"
CURSORRULES = REPO_DIR / ".cursorrules"
README_INTEGRATION = REPO_DIR / "README_INTEGRATION.md"

CATEGORIES = [
    "code",
    "research",
    "tokens-optimization",
    "design",
    "multimedia-writing",
]


def _load(path):
    return json.loads(Path(path).read_text())


class TestCatalogIntegrity(unittest.TestCase):
    """T-1: catalog.json integrity."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = _load(CATALOG_PATH)

    def test_plugin_count(self):
        self.assertEqual(self.catalog["total_plugins"], 21)
        self.assertEqual(len(self.catalog["skills"]), 21)

    def test_categories_complete(self):
        self.assertEqual(set(self.catalog["categories"]), set(CATEGORIES))

    def test_unique_ids_and_slugs(self):
        ids = [s["id"] for s in self.catalog["skills"]]
        slugs = [s["slug"] for s in self.catalog["skills"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate plugin ids")
        self.assertEqual(len(slugs), len(set(slugs)), "duplicate plugin slugs")

    def test_referenced_paths_resolve(self):
        for entry in self.catalog["skills"]:
            manifest = REPO_DIR / entry["manifest_path"]
            guide = REPO_DIR / entry["guide_path"]
            self.assertTrue(
                manifest.is_file(),
                f"manifest missing for {entry['slug']}: {manifest}",
            )
            self.assertTrue(
                guide.is_file(),
                f"SKILL.md missing for {entry['slug']}: {guide}",
            )

    def test_every_plugin_declares_source_url(self):
        for entry in self.catalog["skills"]:
            self.assertTrue(
                entry.get("source_url", "").startswith("https://github.com/"),
                f"{entry['slug']} has no upstream source_url",
            )

    def test_category_counts(self):
        counts = {"code": 4, "research": 5, "tokens-optimization": 4,
                  "design": 4, "multimedia-writing": 4}
        for entry in self.catalog["skills"]:
            counts[entry["category"]] -= 1
        self.assertEqual(
            counts, {k: 0 for k in counts},
            f"category plugin counts drifted: {counts}",
        )


class TestSkillsManifestSync(unittest.TestCase):
    """T-2: skills/manifest.json mirrors the catalog."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = _load(CATALOG_PATH)
        cls.manifest = _load(SKILLS_MANIFEST)

    def test_total_matches_catalog(self):
        self.assertEqual(self.manifest["total_plugins"],
                         self.catalog["total_plugins"])

    def test_plugin_set_matches_catalog(self):
        cat_ids = {s["id"] for s in self.catalog["skills"]}
        tree_ids = {p["id"] for p in self.manifest["plugins"]}
        self.assertEqual(cat_ids, tree_ids)

    def test_paths_are_canonical(self):
        for plugin in self.manifest["plugins"]:
            self.assertEqual(plugin["path"],
                             f"skills/{plugin['category']}/{plugin['slug']}")


class TestScaffoldIdempotency(unittest.TestCase):
    """T-3: scaffold script produces a byte-stable tree (H-2 lesson)."""

    def test_double_run_is_stable(self):
        if not SCAFFOLD_SCRIPT.is_file():
            self.skipTest("scaffold script not present")
        snapshot = sorted(
            str(p.relative_to(REPO_DIR))
            for p in SKILLS_DIR.rglob("*")
            if p.is_file() and p.name != "README.md" and p.name != "manifest.json"
        )
        content_before = {
            str(p.relative_to(REPO_DIR)): p.read_bytes()
            for p in SKILLS_DIR.rglob("*")
            if p.is_file() and not p.is_symlink()
        }
        for _ in range(2):
            result = subprocess.run(
                ["bash", str(SCAFFOLD_SCRIPT)],
                capture_output=True, text=True, cwd=REPO_DIR, timeout=120,
            )
            self.assertEqual(result.returncode, 0,
                             f"scaffold failed: {result.stderr[-500:]}")
        snapshot_after = sorted(
            str(p.relative_to(REPO_DIR))
            for p in SKILLS_DIR.rglob("*")
            if p.is_file() and p.name != "README.md" and p.name != "manifest.json"
        )
        self.assertEqual(snapshot, snapshot_after,
                         "scaffold not idempotent: file set changed")
        content_after = {
            str(p.relative_to(REPO_DIR)): p.read_bytes()
            for p in SKILLS_DIR.rglob("*")
            if p.is_file() and not p.is_symlink()
        }
        self.assertEqual(content_before, content_after,
                         "scaffold not idempotent: file content changed")


class TestTreeSelfContained(unittest.TestCase):
    """T-4: every plugin dir exposes SKILL.md + manifest.json."""

    def test_plugin_dirs_complete(self):
        catalog = _load(CATALOG_PATH)
        missing = []
        for entry in catalog["skills"]:
            plugin_dir = SKILLS_DIR / entry["category"] / entry["slug"]
            for fname in ("SKILL.md", "manifest.json"):
                target = plugin_dir / fname
                if not (target.exists() and target.resolve().is_file()):
                    missing.append(str(target.relative_to(REPO_DIR)))
        self.assertEqual(missing, [], f"incomplete plugin dirs: {missing}")

    def test_manifest_json_payload_valid(self):
        catalog = _load(CATALOG_PATH)
        for entry in catalog["skills"]:
            link = SKILLS_DIR / entry["category"] / entry["slug"] / "manifest.json"
            if link.exists():
                payload = _load(link)
                self.assertEqual(payload.get("slug"), entry["slug"])


class TestMcpServerManifest(unittest.TestCase):
    """T-5: mcp-servers.json consistency with the plugin catalog."""

    @classmethod
    def setUpClass(cls):
        cls.mcp = _load(MCP_PATH)
        cls.catalog = _load(CATALOG_PATH)

    def test_known_server_count(self):
        self.assertEqual(len(self.mcp["servers"]), 38)

    def test_priority_split_sums(self):
        by_p = {}
        for s in self.mcp["servers"]:
            by_p[s["priority"]] = by_p.get(s["priority"], 0) + 1
        self.assertEqual(sum(by_p.values()), 38)
        self.assertEqual(by_p.get("P0"), 5)
        self.assertTrue(by_p.get("P1", 0) >= 20)

    def test_description_mentions_plugin_count(self):
        desc = self.mcp.get("description", "")
        self.assertIn("21 plugin", desc,
                      "description must reference the 21-plugin catalog")

    def test_for_plugins_reference_catalog_slugs(self):
        slugs = {s["slug"] for s in self.catalog["skills"]} | {"all"}
        for server in self.mcp["servers"]:
            for slug in server.get("for_plugins", []):
                self.assertIn(
                    slug, slugs,
                    f"{server['id']} references unknown plugin {slug}",
                )


class TestCategoryReadmes(unittest.TestCase):
    """T-6: category READMEs exist and enumerate every plugin."""

    def test_all_categories_have_readme(self):
        for cat in CATEGORIES:
            readme = SKILLS_DIR / cat / "README.md"
            self.assertTrue(readme.is_file(), f"missing {readme}")

    def test_readmes_list_every_plugin(self):
        catalog = _load(CATALOG_PATH)
        for cat in CATEGORIES:
            readme = (SKILLS_DIR / cat / "README.md").read_text()
            for entry in catalog["skills"]:
                if entry["category"] == cat:
                    self.assertIn(
                        f"`{entry['slug']}`", readme,
                        f"{cat}/README.md does not list {entry['slug']}",
                    )


class TestCursorrulesCoverage(unittest.TestCase):
    """T-7: .cursorrules routes every cataloged plugin."""

    def test_every_slug_routed(self):
        rules = CURSORRULES.read_text()
        catalog = _load(CATALOG_PATH)
        unrouted = [
            entry["slug"] for entry in catalog["skills"]
            if f"skills/{entry['category']}/{entry['slug']}" not in rules
        ]
        self.assertEqual(unrouted, [],
                         f".cursorrules does not route: {unrouted}")


class TestIntegrationReadmeCoverage(unittest.TestCase):
    """T-8: README_INTEGRATION.md documents every cataloged plugin."""

    def test_every_slug_documented(self):
        doc = README_INTEGRATION.read_text()
        catalog = _load(CATALOG_PATH)
        missing = [
            entry["slug"] for entry in catalog["skills"]
            if f"`{entry['slug']}`" not in doc
        ]
        self.assertEqual(missing, [],
                         f"README_INTEGRATION.md missing: {missing}")

    def test_declares_accurate_totals(self):
        doc = README_INTEGRATION.read_text()
        self.assertIn("17 / 17", doc)
        self.assertIn("**21 plugins**", doc)
        self.assertIn("38 MCP servers", doc)


if __name__ == "__main__":
    unittest.main()
