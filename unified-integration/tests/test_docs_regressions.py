#!/usr/bin/env python3
"""Regression checks that keep user-facing docs consistent with the code."""

import ast
import json
import re
import unittest
from pathlib import Path

UI = Path(__file__).resolve().parent.parent
ROOT = UI.parent

NUMBER_WORDS = {"nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


def read(relpath):
    return (ROOT / relpath).read_text(encoding="utf-8")


def bundled_servers():
    return sorted(p.name for p in (UI / "mcp-servers").iterdir()
                  if p.is_dir() and (p / "server.py").is_file())


def setup_default(variable):
    match = re.search(r"\$\{%s:-(\w+)\}" % re.escape(variable),
                      (UI / "setup.sh").read_text(encoding="utf-8"))
    return match.group(1) if match else None


class InHouseServerCountTests(unittest.TestCase):
    def test_server_counts_match_bundled_directories(self):
        expected = len(bundled_servers())
        for relpath in ("README.md", "README_INTEGRATION.md"):
            counts = [int(n) for n in re.findall(
                r"(\d+) in-house MCP servers", read(relpath))]
            self.assertTrue(counts, relpath)
            self.assertEqual(set(counts), {expected}, relpath)
        agents = re.search(r"gateway loads the (\w+) bundled backends",
                           read("docs/AGENTS.md"))
        self.assertIsNotNone(agents)
        self.assertEqual(NUMBER_WORDS.get(agents.group(1)), expected)

    def test_env_vars_mentions_every_bundled_server(self):
        text = read("docs/ENV_VARS.md")
        for name in bundled_servers():
            short = name[:-len("-mcp")] if name.endswith("-mcp") else name
            self.assertTrue(name in text or short in text, name)


class IntegrationTreeTests(unittest.TestCase):
    def test_tree_has_no_missing_hooks_directory(self):
        text = read("README_INTEGRATION.md")
        self.assertFalse((UI / "hooks").exists())
        self.assertNotRegex(text, r"│   ├── hooks/")
        self.assertIn("memory/hooks/", text)
        self.assertTrue((UI / "memory" / "hooks").is_dir())

    def test_pipeline_does_not_aggregate_guide_tree(self):
        text = read("README_INTEGRATION.md")
        self.assertNotIn("scans all SKILL.md", text)
        self.assertNotIn("per-agent install mapping", text)
        self.assertIn("aggregate_skills()", text)
        self.assertRegex((UI / "setup.sh").read_text(encoding="utf-8"),
                         r"(?m)^aggregate_skills\(\) \{")


class PreflightModeTests(unittest.TestCase):
    """Schema and user docs must match the implemented 0/1 mode contract."""

    def test_schema_enum_matches_implemented_modes(self):
        schema = json.loads((UI / "config/ui.api.schema.json").read_text())
        mode = schema["properties"]["preflight"]["properties"]["mode"]
        self.assertEqual(mode["enum"], [0, 1])

    def test_example_config_has_no_mode_2(self):
        text = (UI / "config/ui.api.example.json").read_text(encoding="utf-8")
        self.assertNotIn('"mode": 2', text)
        self.assertNotIn("host-native selection", text)

    def test_user_docs_do_not_advertise_mode_2(self):
        self.assertNotIn("mode 2 (custom", read("README.md").lower())
        self.assertNotIn("optional preflight Mode 2", read("docs/API.md"))
        adaptive = read("docs/ADAPTIVE_PREFLIGHT.md")
        self.assertIn("two implemented modes", adaptive)
        self.assertNotIn('"mode": 2', adaptive)


class ClaimTests(unittest.TestCase):
    def test_readme_memory_load_passes_saved_type(self):
        text = read("README.md")
        saved = re.search(r'save \\\s*\n\s*"(\w+)" "[^"]*" "(\w+)"', text)
        self.assertIsNotNone(saved)
        key, mem_type = saved.groups()
        # Shell line continuations are layout only (markdownlint MD013).
        joined = re.sub(r"\s*\\\s*\n\s*", " ", text)
        self.assertIn(f'load "{key}" "{mem_type}"', joined)

    def test_system_launcher_opt_in_is_documented(self):
        self.assertEqual(setup_default("INSTALL_SYSTEM_LAUNCHER"), "0")
        for relpath in ("docs/ENV_VARS.md", "docs/CONFIGURATION.md",
                        "README.md", "docs/AGENTS.md"):
            self.assertIn("INSTALL_SYSTEM_LAUNCHER", read(relpath), relpath)
        for relpath in ("README.md", "docs/AGENTS.md"):
            self.assertNotIn("when /usr/local/bin is writable", read(relpath))

    def test_architecture_headroom_build_default_matches_setup(self):
        self.assertEqual(setup_default("AGENT_ENHANCEMENTS_BUILD_HEADROOM"), "1")
        text = " ".join(read("docs/ARCHITECTURE.md").split())
        self.assertIn("builds it by default", text)
        self.assertIn("AGENT_ENHANCEMENTS_BUILD_HEADROOM=0", text)

    def test_claude_code_hooks_list_every_installed_event(self):
        source = (UI / "scripts" / "native-integration.py").read_text(
            encoding="utf-8")
        events = None
        for node in ast.parse(source).body:
            if (isinstance(node, ast.Assign)
                    and any(getattr(t, "id", None) == "EVENTS"
                            for t in node.targets)):
                events = ast.literal_eval(node.value)
        self.assertTrue(events)
        text = read("docs/AGENTS.md")
        section = text.split("#### Claude Code", 1)[1].split("####", 1)[0]
        for event in events:
            self.assertIn(f"`{event}`", section, event)

    def test_configuration_mode1_custom_and_retired_overrides(self):
        text = " ".join(read("docs/CONFIGURATION.md").split())
        self.assertNotIn("Claude Code and Codex only", text)
        self.assertNotIn("mode1_native_selection_unavailable", text)
        self.assertIn("mode_not_0_or_1", text)
        self.assertIn("former host-native selection mode was removed", text)
        self.assertNotIn("**Variable:** `XDG_DATA_HOME`", text)
        self.assertNotIn("model-file overrides remain", text)

    def test_preflight_test_count_is_not_stale(self):
        text = read("docs/ADAPTIVE_PREFLIGHT.md")
        claimed = re.search(r"test_adaptive_preflight\.py` - (\d+) regression",
                            text)
        if claimed:
            actual = len(re.findall(
                r"^\s*def test", (UI / "tests" / "test_adaptive_preflight.py")
                .read_text(encoding="utf-8"), re.M))
            self.assertEqual(int(claimed.group(1)), actual)


class HistoricalReportTests(unittest.TestCase):
    CURRENT = "ENTERPRISE_RELEASE_2026-11-23.md"
    SUPERSEDED = (
        "AuditReport/ae-benchmark-report-20261117.md",
        "AuditReport/ae-final-production-report-20261117.md",
        "AuditReport/ae-comprehensive-benchmark-report-20261117.md",
        "mcp-servers/agent_browser/AUDIT_REPORT.md",
        "docs/audit/FINAL_PRODUCTION_READINESS_2026-11-22.md",
        "docs/audit/PRODUCTION_READINESS_AUDIT.md",
        "docs/audit/AuditReport1611202601.md",
    )

    def test_superseded_reports_link_current_status(self):
        for relpath in self.SUPERSEDED:
            path = ROOT / relpath
            head = "\n".join(path.read_text(encoding="utf-8")
                             .splitlines()[:15])
            match = re.search(r"Historical record, superseded by \[[^\]]+\]"
                              r"\(([^)]+)\)", head)
            self.assertIsNotNone(match, relpath)
            target = (path.parent / match.group(1)).resolve()
            self.assertEqual(target.name, self.CURRENT, relpath)
            self.assertTrue(target.is_file(), relpath)

    def test_audit_index_names_current_status(self):
        text = read("docs/audit/README.md")
        self.assertIn(f"]({self.CURRENT})", text)
        self.assertTrue((ROOT / "docs" / "audit" / self.CURRENT).is_file())


def literal_assignment(relpath, name):
    """Return the literal value assigned to ``name`` at module level."""
    source = (ROOT / relpath).read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if (isinstance(node, ast.Assign)
                and any(getattr(t, "id", None) == name for t in node.targets)):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {relpath}")


class StoragePathTests(unittest.TestCase):
    """MCP READMEs must name the private storage locations the code uses."""

    CASES = {
        "graphrag-mcp": ('STORE_DIR = STATE_ROOT / "mcp" / "graphrag"',
                         "$AGENT_MEMORY_ROOT/mcp/graphrag/"),
        "arxiv-mcp": ('CACHE_DIR = memory_root() / "mcp" / "arxiv-cache"',
                      "$AGENT_MEMORY_ROOT/mcp/arxiv-cache"),
        "google-news-mcp": ('CACHE_DIR = memory_root() / "mcp" / "news-cache"',
                            "$AGENT_MEMORY_ROOT/mcp/news-cache"),
        "task-router-mcp": ("prepare() / 'cache/tasks'",
                            ".agentenhancements/cache/tasks/"),
    }

    def test_readmes_match_server_storage(self):
        for name, (code, documented) in self.CASES.items():
            server = (UI / "mcp-servers" / name / "server.py").read_text(
                encoding="utf-8")
            readme = (UI / "mcp-servers" / name / "README.md").read_text(
                encoding="utf-8")
            self.assertIn(code, server, name)
            self.assertIn(documented, readme, name)
            self.assertNotIn("/tmp/", readme, name)


class BundledCountTemplateTests(unittest.TestCase):
    def test_mcp_json_example_count_matches_builtins(self):
        import json
        builtins = literal_assignment("unified-integration/scripts/api_config.py",
                                      "BUILTINS")
        comment = json.loads(read("unified-integration/mcp-servers/"
                                  "mcp.json.example"))["_comment"]
        match = re.search(r"(\w+) bundled implementations", comment)
        self.assertIsNotNone(match)
        self.assertEqual(NUMBER_WORDS.get(match.group(1).lower()), len(builtins))


class ReleaseDocClaimTests(unittest.TestCase):
    def test_contributing_commit_check_is_advisory(self):
        workflow = read(".github/workflows/ci.yml")
        self.assertIn("::warning file=COMMIT_EDITMSG::non-conventional", workflow)
        text = " ".join(read("docs/CONTRIBUTING.md").split())
        self.assertNotIn("CI validates conventional subjects", text)
        self.assertIn("advisory", text)

    def test_security_audit_c03_resolved_with_existing_files(self):
        text = read("docs/audit/SECURITY_AUDIT.md")
        section = text.split("### C-03", 1)[1].split("###", 1)[0]
        self.assertIn("RESOLVED", section)
        for relpath in (".github/workflows/dependency-audit.yml",
                        ".github/dependabot.yml"):
            self.assertIn(relpath, section)
            self.assertTrue((ROOT / relpath).is_file(), relpath)
        self.assertNotIn("No `pip-audit` / `safety` in CI", text)

    def test_license_covers_in_house_mcp_servers(self):
        self.assertTrue((ROOT / "mcp-servers" / "agent_browser"
                         / "package.json").is_file())
        scope = " ".join(read("LICENSE").split("NOTICE")[1]
                         .split("VENDORED")[0].split())
        self.assertIn("mcp-servers/", scope)
        self.assertIn("agent_browser", scope)

    def test_readme_states_python_minimum_and_agent_browser(self):
        minimum = literal_assignment(
            "unified-integration/scripts/runtime_dependencies.py", "MIN_PYTHON")
        text = read("README.md")
        self.assertIn("Python >= %d.%d" % tuple(minimum), text)
        tree = text.split("## Architecture", 1)[1].split("\n---", 1)[0]
        self.assertRegex(tree, r"├── mcp-servers/\n│   └── agent_browser/")


class KarpathyFidelityTests(unittest.TestCase):
    """MASTER_PROMPT §7: upstream principles must survive in routed surfaces."""

    PRINCIPLES = (
        "Think Before Coding", "Simplicity First",
        "Surgical Changes", "Goal-Driven Execution",
    )

    def test_routed_skill_keeps_all_four_upstream_principles(self):
        text = read("plugin-catalog/code/karpathy-skills/SKILL.md")
        for principle in self.PRINCIPLES:
            self.assertIn(principle, text)

    def test_shared_prompt_exposes_all_four_principles(self):
        text = read("unified-integration/prompts/consolidated-system-prompt.txt")
        for principle in self.PRINCIPLES:
            self.assertIn(principle, text)

    def test_manifest_describes_general_coding_and_principle_names(self):
        doc = json.loads(read("plugin-catalog/code/karpathy-skills.json"))
        keywords = [k.lower() for k in doc["trigger_keywords"]]
        for principle in self.PRINCIPLES:
            self.assertIn(principle.lower(), keywords)
        joined = " ".join(
            [doc["description"]] + doc["capabilities"]
            + doc["trigger_keywords"] + doc["best_for"]
        ).lower()
        for term in ("review", "refactor"):
            self.assertIn(term, joined)
        self.assertNotIn("numpy/torch codegen", doc["capabilities"])
        self.assertEqual(doc["mcp_servers_suggested"], [])


if __name__ == "__main__":
    unittest.main()
