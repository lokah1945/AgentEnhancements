"""Regression tests for registry.py lookup/detail and catalog-validate.py.

Covers three audit findings:
  * ``registry.py show --json`` must stay valid JSON when the detail page
    exceeds MAX_DETAIL_PAGE (the old clamp cut the serialized text).
  * ``find_entry`` must not resolve a bare type prefix to an arbitrary
    entry, and a typed prefix must constrain the name/slug pass.
  * ``catalog-validate.py`` must fail when a manifest is missing from
    plugin-catalog/catalog.json (index <- manifest direction).
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module  # noqa: E402

SCRIPTS = UI_DIR / "scripts"

ENTRIES = [
    {"id": "skill:00-first", "type": "skill", "name": "00-first",
     "description": "first skill"},
    {"id": "skill:docx", "type": "skill", "name": "docx",
     "description": "word documents"},
    {"id": "plugin:code-sample", "type": "plugin", "name": "Sample Plugin",
     "slug": "sample", "description": "a plugin"},
    {"id": "mcp:real-mcp", "type": "mcp", "name": "real-mcp",
     "description": "an mcp server"},
]


class FindEntryPrefixTest(unittest.TestCase):
    def setUp(self):
        self.reg = load_module("registry_regress_find", SCRIPTS / "registry.py")
        patcher = mock.patch.object(self.reg, "load_all_entries",
                                    return_value=[dict(e) for e in ENTRIES])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_bare_prefix_names_nothing(self):
        for needle in ("skill:", "plugin:", "mcp:", "capability:", "skill:  "):
            with self.subTest(needle=needle):
                self.assertIsNone(self.reg.find_entry(needle))

    def test_typed_prefix_constrains_name_pass(self):
        self.assertIsNone(self.reg.find_entry("mcp:docx"))
        self.assertIsNone(self.reg.find_entry("plugin:docx"))
        self.assertEqual(self.reg.find_entry("skill:DOCX")["id"], "skill:docx")
        self.assertEqual(self.reg.find_entry("plugin:sample")["id"],
                         "plugin:code-sample")

    def test_untyped_name_and_id_still_resolve(self):
        self.assertEqual(self.reg.find_entry("docx")["id"], "skill:docx")
        self.assertEqual(self.reg.find_entry("sample")["id"],
                         "plugin:code-sample")
        self.assertEqual(self.reg.find_entry("mcp:real-mcp")["id"],
                         "mcp:real-mcp")
        self.assertIsNone(self.reg.find_entry(""))


class ShowJsonBudgetTest(unittest.TestCase):
    def setUp(self):
        self.reg = load_module("registry_regress_show", SCRIPTS / "registry.py")
        patcher = mock.patch.object(
            self.reg, "entry_readiness",
            return_value={"ready": True, "how": "test"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _show_json(self, entry):
        out = io.StringIO()
        with mock.patch.object(self.reg, "find_entry", return_value=entry), \
                contextlib.redirect_stdout(out):
            rc = self.reg.cmd_show(entry["id"], as_json=True)
        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertLessEqual(self.reg.approx_tokens(text.strip()),
                             self.reg.MAX_DETAIL_PAGE)
        return json.loads(text)

    def test_oversized_description_stays_valid_json(self):
        entry = {"id": "skill:docx", "type": "skill", "name": "docx",
                 "source": "anthropic-skills", "category": "general",
                 "description": "\n".join(
                     "word document handling line %d" % i for i in range(1200)),
                 "when_to_use": "use it " * 2000}
        data = self._show_json(entry)
        self.assertTrue(data["truncated"])
        self.assertEqual(data["id"], "skill:docx")
        self.assertIn("trimmed", data["description"])
        self.assertLess(len(data["description"]), len(entry["description"]))

    def test_oversized_lists_fall_back_to_slim_page(self):
        entry = {"id": "skill:big", "type": "skill", "name": "big",
                 "description": "short",
                 "tags": ["tag-%d-%s" % (i, "x" * 400) for i in range(200)],
                 "triggers": ["t" * 5000 for _ in range(8)]}
        data = self._show_json(entry)
        self.assertTrue(data["truncated"])
        self.assertEqual(data["id"], "skill:big")

    def test_small_entry_is_untouched(self):
        entry = {"id": "skill:docx", "type": "skill", "name": "docx",
                 "description": "word documents"}
        data = self._show_json(entry)
        self.assertNotIn("truncated", data)
        self.assertEqual(data["description"], "word documents")


class CatalogIndexCompletenessTest(unittest.TestCase):
    def setUp(self):
        self.cv = load_module("catalog_validate_regress",
                              SCRIPTS / "catalog-validate.py")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        catalog = self.root / "plugin-catalog"
        catalog.mkdir()
        (catalog / "mcp-servers.json").write_text(
            json.dumps({"servers": [{"id": "real-mcp"}]}))
        skills = []
        for category, slugs in self.cv.EXPECTED_PLUGINS.items():
            cat_dir = catalog / category
            cat_dir.mkdir()
            for slug in sorted(slugs):
                manifest = {f: "x" for f in self.cv.EXPECTED_FIELDS}
                manifest.update({
                    "id": f"{category}-{slug}", "slug": slug,
                    "category": category, "status": "integrated",
                    "capabilities": ["c"],
                    "mcp_servers_suggested": ["real-mcp"],
                })
                (cat_dir / f"{slug}.json").write_text(json.dumps(manifest))
                (cat_dir / slug).mkdir()
                (cat_dir / slug / "SKILL.md").write_text("# guide\n")
                skills.append({
                    "id": f"{category}-{slug}", "slug": slug,
                    "category": category,
                    "manifest_path": f"plugin-catalog/{category}/{slug}.json",
                    "mcp_servers": ["real-mcp"],
                })
        self.skills = skills
        self._write_index(skills)

    def _write_index(self, skills, total=None):
        (self.root / "plugin-catalog" / "catalog.json").write_text(json.dumps({
            "total_plugins": len(skills) if total is None else total,
            "skills": skills,
        }))

    def _main(self, *extra):
        out = io.StringIO()
        argv = ["catalog-validate.py", "--root", str(self.root), *extra]
        with mock.patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(out):
            rc = self.cv.main()
        return rc, out.getvalue()

    def test_complete_catalog_passes(self):
        rc, out = self._main("--strict")
        self.assertEqual(rc, 0, out)
        self.assertIn("ALL CHECKS PASSED", out)

    def test_manifest_missing_from_index_fails(self):
        dropped = self.skills[0]
        self._write_index(self.skills[1:])
        rc, out = self._main()
        self.assertEqual(rc, 1, out)
        self.assertIn(f"manifest {dropped['category']}/{dropped['slug']} "
                      "tidak terdaftar di index", out)
        self.assertNotIn("ALL CHECKS PASSED", out)

    def test_total_plugins_mismatch_fails(self):
        self._write_index(self.skills, total=len(self.skills) + 1)
        rc, out = self._main()
        self.assertEqual(rc, 1, out)
        self.assertIn("total_plugins", out)


class LimitFlagValidationTest(unittest.TestCase):
    """``--limit`` must reject bad values with exit 2, not a traceback."""

    def setUp(self):
        self.reg = load_module("registry_regress_limit", SCRIPTS / "registry.py")
        patcher = mock.patch.object(self.reg, "load_all_entries",
                                    return_value=[dict(e) for e in ENTRIES])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.reg.main(["registry.py", *args])
        return rc, out.getvalue(), err.getvalue()

    def test_bad_limits_exit_2_with_message(self):
        for command in ("search", "map"):
            for bad in ("abc", "0", "-3", "1.5"):
                with self.subTest(command=command, value=bad):
                    rc, _out, err = self._main(command, "docs", "--limit", bad)
                    self.assertEqual(rc, 2)
                    self.assertIn("--limit must be a positive integer", err)

    def test_valid_limit_still_accepted(self):
        with mock.patch.object(self.reg, "cmd_search", return_value=0) as cs:
            rc, _out, _err = self._main("search", "docs", "--limit", "3")
        self.assertEqual(rc, 0)
        self.assertEqual(cs.call_args.kwargs["limit"], 3)
        with mock.patch.object(self.reg, "cmd_map", return_value=0) as cm:
            rc, _out, _err = self._main("map", "docs", "--limit", "4")
        self.assertEqual(rc, 0)
        self.assertEqual(cm.call_args.kwargs["limit"], 4)


if __name__ == "__main__":
    unittest.main()
