"""Behavioral coverage for unified-integration/scripts/load-skills.py.

Complements test_load_skills.py with the paths it leaves unexercised:
missing index, host-compatibility filtering, result shape and limits,
skill_path resolution order and containment, frontmatter parsing edge
cases (no frontmatter, unterminated, empty, PyYAML missing) and the CLI
entry point both in-process and as a real subprocess.
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
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module

SCRIPT = UI_DIR / "scripts" / "load-skills.py"


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class _Base(unittest.TestCase):
    """Isolated AGENT_SKILLS_DIR tree plus a freshly imported module."""

    index = {
        "skills": [
            {"name": "pentest-audit", "category": "security",
             "description": "audit a web application with a pentest checklist",
             "tags": ["security", "pentest"], "tools": ["claude-code"],
             "when_to_use": "audit a web application pentest"},
            {"name": "gemini-pentest", "category": "security",
             "description": "audit a web application with a pentest checklist",
             "tags": ["security"], "tools": ["gemini-cli"],
             "when_to_use": "audit a web application pentest"},
            {"name": "generic-pentest", "category": "security",
             "description": "pentest audit for any web application",
             "tags": ["pentest"], "tools": ["python", "git"],
             "when_to_use": "pentest audit web application"},
        ]
    }

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.root = self.base / "skills"
        self.root.mkdir()
        if self.index is not None:
            _write(self.root / "all-skills.json", json.dumps(self.index))
        self.mod = load_module(
            "loadskills_cov_%s" % id(self), SCRIPT,
            env={"AGENT_SKILLS_DIR": str(self.root)},
        )

    def tearDown(self):
        sys.modules.pop("loadskills_cov_%s" % id(self), None)
        self._tmp.cleanup()

    def loader(self, agent="claude-code"):
        return self.mod.SkillsLoader(agent)


class IndexLoadingTests(_Base):
    index = None

    def test_missing_index_yields_empty_skill_list(self):
        loader = self.loader()
        self.assertEqual(loader.skills_index, {"skills": []})
        self.assertEqual(loader.find_skills("audit a web application pentest"), [])

    def test_index_is_read_at_construction(self):
        _write(self.root / "all-skills.json", json.dumps({"skills": [{"name": "x"}]}))
        self.assertEqual(self.loader().skills_index["skills"][0]["name"], "x")


class AgentAliasTests(_Base):
    def test_agent_names_are_casefolded_and_aliased(self):
        cases = {"Claude": "claude-code", "CODEX-CLI": "codex", "gemini": "gemini-cli",
                 "Hermes": "hermes", "Kiro": "kiro"}
        for given, expected in cases.items():
            with self.subTest(agent=given):
                self.assertEqual(self.loader(given).agent, expected)

    def test_unknown_agent_is_kept_casefolded(self):
        self.assertEqual(self.loader("MyAgent").agent, "myagent")


class FindSkillsTests(_Base):
    QUERY = "audit a web application pentest"

    def names(self, agent, query=None, **kw):
        return [s["name"] for s in self.loader(agent).find_skills(query or self.QUERY, **kw)]

    def test_skills_declaring_other_hosts_are_filtered_out(self):
        names = self.names("claude")
        self.assertIn("pentest-audit", names)
        self.assertNotIn("gemini-pentest", names)

    def test_host_filter_is_symmetric_for_other_agents(self):
        names = self.names("gemini")
        self.assertIn("gemini-pentest", names)
        self.assertNotIn("pentest-audit", names)

    def test_prerequisite_only_tools_do_not_exclude_any_agent(self):
        for agent in ("claude-code", "gemini-cli", "unknown-host"):
            with self.subTest(agent=agent):
                self.assertIn("generic-pentest", self.names(agent))

    def test_unknown_agent_excludes_every_host_specific_skill(self):
        self.assertEqual(self.names("unknown-host"), ["generic-pentest"])

    def test_missing_or_null_tools_are_treated_as_universal(self):
        loader = self.loader("codex")
        loader.skills_index["skills"][2].pop("tools")
        self.assertIn("generic-pentest", [s["name"] for s in loader.find_skills(self.QUERY)])
        loader.skills_index["skills"][2]["tools"] = None
        self.assertIn("generic-pentest", [s["name"] for s in loader.find_skills(self.QUERY)])

    def test_results_are_the_original_records_without_ranking_metadata(self):
        hits = self.loader().find_skills(self.QUERY)
        self.assertTrue(hits)
        originals = self.loader().skills_index["skills"]
        for hit in hits:
            self.assertIn(hit, originals)
            for internal in ("_skill", "type", "natively_linked_by_default"):
                self.assertNotIn(internal, hit)

    def test_find_skills_does_not_mutate_the_index(self):
        loader = self.loader()
        before = json.loads(json.dumps(loader.skills_index))
        loader.find_skills(self.QUERY)
        self.assertEqual(loader.skills_index, before)

    def test_max_results_caps_the_result_count(self):
        self.assertEqual(len(self.names("claude-code", max_results=1)), 1)
        self.assertEqual(self.names("claude-code", max_results=0), [])

    def test_empty_query_abstains(self):
        self.assertEqual(self.loader().find_skills(""), [])


class SkillPathTests(_Base):
    def test_rejects_names_that_are_not_a_single_path_component(self):
        loader = self.loader()
        for bad in ("", ".", "..", "a/b", "../x", "/etc/passwd"):
            with self.subTest(name=bad):
                self.assertIsNone(loader.skill_path(bad))
                self.assertEqual(loader.load_skill(bad), {})

    def test_directory_layout_wins_over_flat_layout_in_same_category(self):
        cat = self.root / "by-category" / "general"
        d = _write(cat / "dup" / "SKILL.md", "dir")
        _write(cat / "dup.md", "flat")
        self.assertEqual(self.loader().skill_path("dup"), d)

    def test_categories_are_searched_in_sorted_order_before_by_agent(self):
        first = _write(self.root / "by-category" / "aaa" / "same.md", "a")
        _write(self.root / "by-category" / "zzz" / "same.md", "z")
        _write(self.root / "by-agent" / "claude-code" / "same.md", "agent")
        self.assertEqual(self.loader().skill_path("same"), first)

    def test_by_agent_lookup_uses_the_resolved_agent_alias(self):
        p = _write(self.root / "by-agent" / "codex" / "only-codex.md", "x")
        self.assertEqual(self.loader("codex-cli").skill_path("only-codex"), p)
        self.assertIsNone(self.loader("claude").skill_path("only-codex"))

    def test_stray_files_in_by_category_are_ignored(self):
        _write(self.root / "by-category" / "README.md", "not a category")
        p = _write(self.root / "by-category" / "general" / "ok.md", "ok")
        self.assertEqual(self.loader().skill_path("ok"), p)

    def test_directory_named_like_flat_file_is_not_a_skill(self):
        (self.root / "by-category" / "general" / "weird.md").mkdir(parents=True)
        self.assertIsNone(self.loader().skill_path("weird"))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlink_escaping_skills_dir_is_refused(self):
        outside = _write(self.base / "outside" / "SKILL.md", "---\nname: evil\n---\nsecret\n")
        cat = self.root / "by-category" / "general"
        cat.mkdir(parents=True)
        os.symlink(outside.parent, cat / "evil")
        os.symlink(outside, cat / "evil2.md")
        loader = self.loader()
        self.assertIsNone(loader.skill_path("evil"))
        self.assertIsNone(loader.skill_path("evil2"))
        self.assertEqual(loader.load_skill("evil"), {})

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlink_inside_skills_dir_is_allowed(self):
        target = _write(self.root / "by-category" / "real" / "inner" / "SKILL.md",
                        "---\nname: inner\n---\nbody\n")
        alias = self.root / "by-category" / "alias"
        alias.mkdir(parents=True)
        os.symlink(target.parent, alias / "linked")
        self.assertEqual(self.loader().load_skill("linked")["frontmatter"], {"name": "inner"})


class ParseSkillTests(_Base):
    def skill(self, text, name="s"):
        _write(self.root / "by-category" / "c" / name / "SKILL.md", text)
        return self.loader().load_skill(name)

    def test_frontmatter_and_body_are_split_and_body_stripped(self):
        out = self.skill("---\nname: s\ntags: [a, b]\n---\n\n  Body text\n\n")
        self.assertEqual(out["frontmatter"], {"name": "s", "tags": ["a", "b"]})
        self.assertEqual(out["body"], "Body text")
        self.assertTrue(out["file"].endswith(os.path.join("c", "s", "SKILL.md")))
        self.assertNotIn("raw", out)

    def test_body_may_contain_horizontal_rules(self):
        out = self.skill("---\nname: s\n---\nintro\n---\nmore\n")
        self.assertEqual(out["body"], "intro\n---\nmore")

    def test_no_frontmatter_returns_raw_content(self):
        text = "# Title\n\nJust markdown.\n"
        out = self.skill(text)
        self.assertEqual(out["raw"], text)
        self.assertNotIn("frontmatter", out)

    def test_unterminated_frontmatter_returns_raw_content(self):
        text = "---\nname: s\nno closing fence\n"
        out = self.skill(text)
        self.assertEqual(out["raw"], text)
        self.assertEqual(set(out), {"raw", "file"})

    def test_empty_frontmatter_parses_to_none(self):
        out = self.skill("---\n---\nbody\n")
        self.assertIsNone(out["frontmatter"])
        self.assertEqual(out["body"], "body")

    def test_missing_pyyaml_falls_back_to_raw_with_warning(self):
        text = "---\nname: s\n---\nbody\n"
        _write(self.root / "by-category" / "c" / "s" / "SKILL.md", text)
        loader = self.loader()
        err = io.StringIO()
        with mock.patch.dict(sys.modules, {"yaml": None}), contextlib.redirect_stderr(err):
            out = loader.load_skill("s")
        self.assertEqual(out["raw"], text)
        self.assertNotIn("frontmatter", out)
        self.assertIn("PyYAML is not installed", err.getvalue())

    def test_flat_skill_without_frontmatter(self):
        p = _write(self.root / "by-category" / "c" / "plain.md", "plain text")
        self.assertEqual(self.loader().load_skill("plain"), {"raw": "plain text", "file": str(p)})

    # BUG: _parse_skill splits on the first "---" substring anywhere, not on a
    # closing fence line, so a frontmatter value containing "---" truncates
    # the frontmatter and leaks the rest into the body (silently wrong data).
    def test_triple_dash_inside_frontmatter_value_is_preserved(self):
        out = self.skill("---\nname: s\ndescription: before---after\n---\nBody\n")
        self.assertEqual(out["frontmatter"],
                         {"name": "s", "description": "before---after"})
        self.assertEqual(out["body"], "Body")

    def test_closing_fence_may_carry_trailing_whitespace_and_crlf(self):
        out = self.skill("---\r\nname: s\r\n---  \r\nBody\r\n")
        self.assertEqual(out["frontmatter"], {"name": "s"})
        self.assertEqual(out["body"], "Body")

    def test_indented_or_inline_dashes_are_not_a_closing_fence(self):
        text = "---\nname: s\nnote: |\n  ---\n  kept\n---\nBody\n"
        out = self.skill(text)
        self.assertEqual(out["frontmatter"], {"name": "s", "note": "---\nkept\n"})
        self.assertEqual(out["body"], "Body")

    def test_opening_line_must_be_a_bare_fence(self):
        text = "----\nname: s\n---\nBody\n"
        out = self.skill(text)
        self.assertEqual(out, {"raw": text, "file": out["file"]})


class MainInProcessTests(_Base):
    def run_main(self, *argv):
        out = io.StringIO()
        code = 0
        with mock.patch.object(sys, "argv", ["load-skills.py", *argv]), \
                contextlib.redirect_stdout(out):
            try:
                self.mod.main()
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue()

    def test_usage_when_task_missing(self):
        for argv in ((), ("claude",)):
            with self.subTest(argv=argv):
                code, out = self.run_main(*argv)
                self.assertEqual(code, 1)
                self.assertIn("Usage: load-skills.py <agent> <task_description>", out)

    def test_prints_matching_skill_cards(self):
        code, out = self.run_main("claude", "audit", "a", "web", "application", "pentest")
        self.assertEqual(code, 0)
        self.assertIn("Skill: pentest-audit\n", out)
        self.assertIn("  Description: audit a web application with a pentest checklist", out)
        self.assertIn("  Tags: security, pentest", out)
        self.assertNotIn("gemini-pentest", out)

    def test_missing_fields_use_placeholders(self):
        index = {"skills": [{"when_to_use": "audit web application pentest", "tools": []}]}
        _write(self.root / "all-skills.json", json.dumps(index))
        code, out = self.run_main("claude", "audit web application pentest")
        self.assertEqual(code, 0)
        self.assertIn("Skill: Unknown", out)
        self.assertIn("  Description: N/A", out)
        self.assertIn("  Tags: \n", out)

    def test_no_match_prints_nothing(self):
        code, out = self.run_main("claude", "zyxwvu")
        self.assertEqual((code, out), (0, ""))


class CliSubprocessTests(_Base):
    def cli(self, *args):
        env = dict(os.environ)
        env["AGENT_SKILLS_DIR"] = str(self.root)
        env["HOME"] = str(self.base / "home")
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True,
                              text=True, env=env, timeout=30)

    def test_cli_end_to_end_uses_env_skills_dir(self):
        proc = self.cli("gemini", "audit a web application pentest")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Skill: gemini-pentest", proc.stdout)
        self.assertNotIn("Skill: pentest-audit", proc.stdout)

    def test_cli_usage_exit_code(self):
        proc = self.cli("claude")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Usage:", proc.stdout)


class LoadSkillsExtraTests(_Base):
    """Additional tests to cover missing branches in load-skills.py."""

    def test_missing_index_file_returns_empty_skills(self):
        # Remove the index file to test missing index handling
        (self.root / "all-skills.json").unlink()
        loader = self.loader()
        self.assertEqual(loader.skills_index, {"skills": []})
        self.assertEqual(loader.find_skills("anything"), [])

    def test_prerequisite_only_tools_do_not_exclude(self):
        # Skills with only prerequisite tools (python, git) should be compatible with all agents
        index = {"skills": [{"name": "test-skill", "tools": ["python", "git"],
                            "when_to_use": "test", "description": "test",
                            "tags": ["test"]}]}
        _write(self.root / "all-skills.json", json.dumps(index))
        loader = self.loader("unknown-host")
        results = loader.find_skills("test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "test-skill")

    def test_missing_tools_treated_as_universal(self):
        index = {"skills": [{"name": "test-skill", "when_to_use": "test",
                            "description": "test", "tags": ["test"]}]}
        _write(self.root / "all-skills.json", json.dumps(index))
        loader = self.loader("unknown-host")
        results = loader.find_skills("test")
        self.assertEqual(len(results), 1)

    def test_null_tools_treated_as_universal(self):
        index = {"skills": [{"name": "test-skill", "tools": None,
                            "when_to_use": "test", "description": "test",
                            "tags": ["test"]}]}
        _write(self.root / "all-skills.json", json.dumps(index))
        loader = self.loader("unknown-host")
        results = loader.find_skills("test")
        self.assertEqual(len(results), 1)

    def test_skill_path_rejects_invalid_names(self):
        loader = self.loader()
        for bad in ("", ".", "..", "a/b", "../x", "/etc/passwd"):
            with self.subTest(name=bad):
                self.assertIsNone(loader.skill_path(bad))
                self.assertEqual(loader.load_skill(bad), {})

    def test_skill_path_directory_traversal_prevented(self):
        loader = self.loader()
        # Create a skill outside the skills dir
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "evil.md").write_text("---\nname: evil\n---\nsecret\n")
        # Try to access via path traversal
        self.assertIsNone(loader.skill_path("../outside/evil"))
        self.assertEqual(loader.load_skill("../outside/evil"), {})

    def test_parse_skill_no_frontmatter_returns_raw(self):
        loader = self.loader()
        _write(self.root / "by-category" / "c" / "plain.md", "plain text")
        result = loader.load_skill("plain")
        self.assertEqual(result, {"raw": "plain text", "file": str(self.root / "by-category" / "c" / "plain.md")})

    def test_parse_skill_unterminated_frontmatter_returns_raw(self):
        loader = self.loader()
        text = "---\nname: s\nno closing fence\n"
        _write(self.root / "by-category" / "c" / "s" / "SKILL.md", text)
        result = loader.load_skill("s")
        self.assertEqual(result, {"raw": text, "file": str(self.root / "by-category" / "c" / "s" / "SKILL.md")})

    def test_parse_skill_empty_frontmatter_returns_none(self):
        loader = self.loader()
        text = "---\n---\nbody\n"
        _write(self.root / "by-category" / "c" / "s" / "SKILL.md", text)
        result = loader.load_skill("s")
        self.assertIsNone(result["frontmatter"])
        self.assertEqual(result["body"], "body")

    def test_parse_skill_missing_pyyaml_falls_back_to_raw(self):
        loader = self.loader()
        text = "---\nname: s\n---\nbody\n"
        _write(self.root / "by-category" / "c" / "s" / "SKILL.md", text)
        err = io.StringIO()
        with mock.patch.dict(sys.modules, {"yaml": None}), contextlib.redirect_stderr(err):
            result = loader.load_skill("s")
        self.assertEqual(result["raw"], text)
        self.assertNotIn("frontmatter", result)
        self.assertIn("PyYAML is not installed", err.getvalue())

    def test_parse_skill_frontmatter_with_triple_dash_in_value(self):
        loader = self.loader()
        text = "---\nname: s\ndescription: before---after\n---\nBody\n"
        _write(self.root / "by-category" / "c" / "s" / "SKILL.md", text)
        result = loader.load_skill("s")
        self.assertEqual(result["frontmatter"], {"name": "s", "description": "before---after"})
        self.assertEqual(result["body"], "Body")

    def test_parse_skill_closing_fence_with_whitespace_and_crlf(self):
        loader = self.loader()
        text = "---\r\nname: s\r\n---  \r\nBody\r\n"
        _write(self.root / "by-category" / "c" / "s" / "SKILL.md", text)
        result = loader.load_skill("s")
        self.assertEqual(result["frontmatter"], {"name": "s"})
        self.assertEqual(result["body"], "Body")

    def test_parse_skill_indented_dashes_not_closing_fence(self):
        loader = self.loader()
        text = "---\nname: s\nnote: |\n  ---\n  kept\n---\nBody\n"
        _write(self.root / "by-category" / "c" / "s" / "SKILL.md", text)
        result = loader.load_skill("s")
        self.assertEqual(result["frontmatter"], {"name": "s", "note": "---\nkept\n"})
        self.assertEqual(result["body"], "Body")

    def test_parse_skill_opening_line_must_be_bare_fence(self):
        loader = self.loader()
        text = "----\nname: s\n---\nBody\n"
        _write(self.root / "by-category" / "c" / "s" / "SKILL.md", text)
        result = loader.load_skill("s")
        self.assertEqual(result, {"raw": text, "file": str(self.root / "by-category" / "c" / "s" / "SKILL.md")})

    def test_find_skills_empty_query_returns_empty(self):
        loader = self.loader()
        self.assertEqual(loader.find_skills(""), [])

    def test_find_skills_max_results_zero_returns_empty(self):
        loader = self.loader()
        self.assertEqual(loader.find_skills("test", max_results=0), [])

    def test_find_skills_does_not_mutate_index(self):
        loader = self.loader()
        before = json.loads(json.dumps(loader.skills_index))
        loader.find_skills("audit a web application pentest")
        self.assertEqual(loader.skills_index, before)

    def test_results_are_original_records_without_ranking_metadata(self):
        loader = self.loader()
        hits = loader.find_skills("audit a web application pentest")
        self.assertTrue(hits)
        originals = loader.skills_index["skills"]
        for hit in hits:
            self.assertIn(hit, originals)
            for internal in ("_skill", "type", "natively_linked_by_default"):
                self.assertNotIn(internal, hit)


if __name__ == "__main__":
    unittest.main()
