"""Native event/configuration regression tests; no model or API calls."""

import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import UI_DIR, load_module, run


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.memory = self.root / "memory"
        skill = self.root / "skills/by-category/security/security-audit"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: security-audit\ndescription: security audit\n---\nAudit carefully"
        )
        (self.root / "skills/all-skills.json").write_text(
            json.dumps(
                {
                    "skills": [
                        {
                            "name": "security-audit",
                            "category": "security",
                            "description": "security audit",
                            "tools": [],
                            "tags": ["security"],
                        }
                    ]
                }
            )
        )

    def tearDown(self):
        self.tmp.cleanup()

    def event(self, name, agent="claude-code", project="a/repo", **data):
        payload = {
            "hook_event_name": name,
            "session_id": "fixture-session",
            "cwd": str(self.root / project),
            **data,
        }
        rc, out, err = run(
            [sys.executable, str(UI_DIR / "scripts/runtime.py"), agent],
            env={
                "AGENT_MEMORY_ROOT": str(self.memory),
                "AGENT_SKILLS_DIR": str(self.root / "skills"),
            },
            input_text=json.dumps(payload),
        )
        self.assertEqual(rc, 0, err)
        self.assertEqual(err, "")
        return json.loads(out) if out.strip() else {}

    def rows(self):
        with sqlite3.connect(self.memory / "memory.db") as conn:
            return conn.execute("SELECT key, value, project FROM memories").fetchall()

    def test_all_native_agents_accept_stdin_events_and_restore_sessions(self):
        for agent in ["claude-code", "codex", "opencode"]:
            with self.subTest(agent=agent):
                self.event("UserPromptSubmit", agent, prompt="Run a security audit")
                self.event("Stop", agent, last_assistant_message="Fixed the parser bug")
                output = self.event("SessionStart", agent)
                self.assertIn(
                    "Fixed the parser bug",
                    output["hookSpecificOutput"]["additionalContext"],
                )

    def test_prompt_routes_skill_without_a_manual_command(self):
        result = self.event("UserPromptSubmit", prompt="security audit")
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(
            result["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit"
        )
        self.assertIn("security-audit/SKILL.md", context)

    def test_same_basename_repositories_do_not_share_memory(self):
        self.event(
            "UserPromptSubmit", project="first/repo", prompt="private project note"
        )
        self.assertEqual(self.event("SessionStart", project="second/repo"), {})

    def test_tool_input_and_output_are_never_stored(self):
        self.event(
            "PostToolUse",
            tool_name="Bash",
            tool_input={"command": "PRIVATE_INPUT"},
            tool_response="PRIVATE_OUTPUT",
        )
        values = json.dumps(self.rows())
        self.assertIn("Bash", values)
        self.assertNotIn("PRIVATE_INPUT", values)
        self.assertNotIn("PRIVATE_OUTPUT", values)

    def test_credentials_are_redacted_in_prompt_and_summary(self):
        secret = "github_pat_" + "x" * 35
        self.event("UserPromptSubmit", prompt=f"Fix auth with {secret}")
        self.event("Stop", last_assistant_message="password=hidden-password")
        values = json.dumps(self.rows())
        self.assertNotIn(secret, values)
        self.assertNotIn("hidden-password", values)
        self.assertIn("[redacted]", values)

    def test_corrupt_event_does_not_block_cli(self):
        rc, out, err = run(
            [sys.executable, str(UI_DIR / "scripts/runtime.py"), "codex"],
            input_text="bad json",
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertIn("hook skipped", err)

    def test_expired_notes_are_not_replayed(self):
        self.event("UserPromptSubmit", prompt="expired note")
        with sqlite3.connect(self.memory / "memory.db") as conn:
            conn.execute("UPDATE memories SET expires_at='2000-01-01 00:00:00'")
        self.assertEqual(self.event("SessionStart"), {})


class UpdateFlowTests(unittest.TestCase):
    def test_piped_installer_bootstraps_the_complete_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            binaries = base / "bin"
            binaries.mkdir()
            git = binaries / "git"
            git.write_text(
                "#!/bin/bash\nset -euo pipefail\n"
                'mkdir -p "$3/unified-integration"\n'
                'printf \'#!/bin/bash\\nprintf "bootstrap-complete\\\\n"\\n\' > "$3/unified-integration/setup.sh"\n'
            )
            git.chmod(0o755)
            rc, out, err = run(
                ["bash"],
                input_text=(UI_DIR / "setup.sh").read_text(),
                env={
                    "AGENT_ENHANCEMENTS_BASE_DIR": str(base / "clone"),
                    "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
                },
            )
            self.assertEqual(rc, 0, err)
            self.assertIn("bootstrap-complete", out)

    def test_setup_is_fully_drained_and_failures_propagate(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            setup = base / "unified-integration/setup.sh"
            setup.parent.mkdir()
            marker = base / "finished"
            setup.write_text(
                '#!/bin/bash\nfor i in {1..50}; do echo "skill $i"; done\n'
                + f'touch "{marker}"\nexit 7\n'
            )
            setup.chmod(0o755)
            rc, out, err = run(
                ["bash", str(UI_DIR / "update-skills.sh")],
                env={"AGENT_ENHANCEMENTS_BASE_DIR": str(base)},
            )
            self.assertNotEqual(rc, 0)
            self.assertTrue(marker.exists())
            self.assertIn("update is incomplete", out)


class OpenCodePluginTests(unittest.TestCase):
    @unittest.skipUnless(
        shutil.which("node"), "node is required for the OpenCode plugin test"
    )
    def test_prompt_context_and_idle_hooks_use_the_shared_runtime(self):
        rc, out, err = run(["node", str(UI_DIR / "tests/test-opencode-plugin.mjs")])
        self.assertEqual(rc, 0, err)
        self.assertIn("integration: OK", out)


@unittest.skipUnless(
    importlib.util.find_spec("tomlkit") and importlib.util.find_spec("json5"),
    "run with the isolated runtime prepared by setup-mcp.sh",
)
class NativeConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ae config's ")
        self.home = Path(self.tmp.name)
        self.env = {
            "HOME": str(self.home),
            "CODEX_HOME": str(self.home / ".codex"),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "AGENT_ENHANCEMENTS_API_FILE": str(self.home / "ui.api.json"),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, agent="all"):
        rc, out, err = run(
            [
                sys.executable,
                str(UI_DIR / "scripts/native-integration.py"),
                "--agent",
                agent,
            ],
            env=self.env,
        )
        self.assertEqual(rc, 0, err)

    def test_claude_preserves_hooks_and_uses_user_mcp_location(self):
        path = self.home / ".claude/settings.json"
        path.parent.mkdir()
        user_hook = {"type": "command", "command": "echo user-owned"}
        path.write_text(
            json.dumps(
                {
                    "env": {"CUSTOM": "unchanged"},
                    "hooks": {
                        "Stop": [{"hooks": [user_hook]}],
                    },
                }
            )
        )
        self.install("claude-code")
        self.install("claude-code")
        config = json.loads(path.read_text())
        handlers = [h for g in config["hooks"]["Stop"] for h in g["hooks"]]
        self.assertIn(user_hook, handlers)
        self.assertEqual(len(handlers), 2)
        self.assertEqual(config["env"]["CUSTOM"], "unchanged")
        self.assertEqual(
            len(json.loads((self.home / ".claude.json").read_text())["mcpServers"]), 1
        )
        self.assertFalse((self.home / ".claude/mcp.json").exists())

    def test_codex_preserves_toml_comments_and_existing_server(self):
        import tomlkit

        path = self.home / ".codex/config.toml"
        path.parent.mkdir()
        path.write_text(
            '# personal comment\nmodel = "personal-model"\n[mcp_servers.personal]\ncommand = "custom"\n'
        )
        self.install("codex")
        content = path.read_text()
        self.install("codex")
        self.assertEqual(path.read_text(), content)
        doc = tomlkit.parse(content)
        self.assertIn("# personal comment", content)
        self.assertEqual(doc["model"], "personal-model")
        self.assertEqual(doc["mcp_servers"]["personal"]["command"], "custom")
        self.assertEqual(len(doc["mcp_servers"]), 2)
        hooks = json.loads((path.parent / "hooks.json").read_text())["hooks"]
        self.assertIn("SessionStart", hooks)
        self.assertIn("UserPromptSubmit", hooks)

    def test_custom_claude_auth_moves_to_central_file_without_changing_provider(self):
        path = self.home / ".claude/settings.json"
        path.parent.mkdir()
        path.write_text(
            json.dumps(
                {
                    "env": {
                        "ANTHROPIC_AUTH_TOKEN": "fixture-custom-token",
                        "ANTHROPIC_API_KEY": "fixture-custom-key",
                        "ANTHROPIC_BASE_URL": "http://127.0.0.1:1234",
                        "ANTHROPIC_MODEL": "custom-model",
                    }
                }
            )
        )
        self.install("claude-code")
        doc = json.loads(path.read_text())
        self.assertEqual(doc["env"]["ANTHROPIC_MODEL"], "custom-model")
        self.assertEqual(doc["env"]["ANTHROPIC_BASE_URL"], "http://127.0.0.1:1234")
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", doc["env"])
        self.assertNotIn("ANTHROPIC_API_KEY", doc["env"])
        self.assertIn("api_config.py", doc["apiKeyHelper"])
        api_path = Path(self.env["AGENT_ENHANCEMENTS_API_FILE"])
        api = json.loads(api_path.read_text())
        self.assertEqual(
            api["api_keys"]["ANTHROPIC_AUTH_TOKEN"], "fixture-custom-token"
        )
        api["api_keys"]["ANTHROPIC_AUTH_TOKEN"] = ""
        api["api_keys"]["ANTHROPIC_API_KEY"] = ""
        api_path.write_text(json.dumps(api))
        self.install("claude-code")
        self.assertEqual(
            json.loads(api_path.read_text())["api_keys"]["ANTHROPIC_AUTH_TOKEN"], ""
        )

    def test_opencode_edits_existing_jsonc_and_preserves_user_arrays(self):
        path = self.home / ".config/opencode/opencode.jsonc"
        path.parent.mkdir(parents=True)
        path.write_text(
            '// user config\n{"instructions":["personal.md"],"plugins":["custom"],"skills":["team"],}'
        )
        self.install("opencode")
        content = path.read_text()
        self.install("opencode")
        self.assertEqual(path.read_text(), content)
        doc = json.loads(content)
        self.assertIn("personal.md", doc["instructions"])
        self.assertIn("custom", doc["plugins"])
        self.assertIn("team", doc["skills"])
        self.assertEqual(len(doc["mcp"]["servers"]), 1)
        self.assertTrue(
            all(
                c["type"] == "local" and isinstance(c["command"], list)
                for c in doc["mcp"]["servers"].values()
            )
        )
        self.assertFalse(path.with_suffix(".json").exists())
        self.assertTrue(list(path.parent.glob("*.backup.*")))

    def test_opencode_migrates_v1_server_shape_and_environment(self):
        path = self.home / ".config/opencode/opencode.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "mcp": {
                        "personal": {
                            "type": "local",
                            "command": ["custom"],
                            "enabled": False,
                            "env": {"CUSTOM": "preserved"},
                        }
                    }
                }
            )
        )
        self.install("opencode")
        mcp = json.loads(path.read_text())["mcp"]
        self.assertEqual(list(mcp), ["servers"])
        self.assertTrue(mcp["servers"]["personal"]["disabled"])
        self.assertEqual(
            mcp["servers"]["personal"]["environment"], {"CUSTOM": "preserved"}
        )
        self.assertFalse(mcp["servers"]["agent-enhancements"]["codemode"])

    def test_user_server_name_collision_is_preserved(self):
        path = self.home / ".claude.json"
        path.write_text(
            json.dumps({"mcpServers": {"style-mcp": {"command": "custom-user"}}})
        )
        self.install("claude-code")
        self.assertEqual(
            json.loads(path.read_text())["mcpServers"]["style-mcp"]["command"],
            "custom-user",
        )

    def test_custom_claude_config_dir_uses_its_inner_global_file(self):
        custom = self.home / "custom-claude"
        self.env["CLAUDE_CONFIG_DIR"] = str(custom)
        self.install("claude-code")
        doc = json.loads((custom / ".claude.json").read_text())
        self.assertIn("agent-enhancements", doc["mcpServers"])
        self.assertFalse(self.home.joinpath("custom-claude.json").exists())

    def test_malformed_user_config_is_untouched_and_setup_reports_failure(self):
        path = self.home / ".claude/settings.json"
        path.parent.mkdir()
        path.write_text("{INVALID USER FILE")
        rc, out, err = run(
            [
                sys.executable,
                str(UI_DIR / "scripts/native-integration.py"),
                "--agent",
                "claude-code",
            ],
            env=self.env,
        )
        self.assertNotEqual(rc, 0)
        self.assertEqual(path.read_text(), "{INVALID USER FILE")


if __name__ == "__main__":
    unittest.main()
