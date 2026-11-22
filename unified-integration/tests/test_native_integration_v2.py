#!/usr/bin/env python3
"""
Tests for NativeIntegrationV2.
"""

import tempfile
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from native_integration_v2 import NativeIntegrationV2, AgentConfig


def test_native_integration_v2_init():
    """Test NativeIntegrationV2 initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        assert integration.base_dir == base_dir
        assert integration.ae_root == base_dir


def test_all_agents_defined():
    """Test all 9 agents are defined."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        expected_agents = {
            "claude-code", "codex", "opencode", "hermes",
            "cursor", "gemini", "copilot", "windsurf", "kiro"
        }
        assert set(integration.agents.keys()) == expected_agents


def test_agent_config_structure():
    """Test each agent has required config structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        # Reference agents don't have skills_dir or hooks
        ref_agents = {"cursor", "gemini", "copilot", "windsurf", "kiro"}
        hook_agents = {"claude-code", "codex", "opencode", "hermes"}

        for name, agent in integration.agents.items():
            assert isinstance(agent, AgentConfig)
            assert agent.name == name
            assert agent.display_name
            assert agent.config_dir
            assert isinstance(agent.config_files, dict)
            assert isinstance(agent.hooks, dict)
            assert isinstance(agent.mcp_config, dict)
            assert isinstance(agent.env_vars, dict)

            if name in hook_agents:
                assert agent.skills_dir, f"{name} should have skills_dir"
                assert agent.hooks, f"{name} should have hooks"
            elif name in ref_agents:
                # Reference agents may have empty skills_dir and hooks
                pass


def test_common_hooks_defined():
    """Test common hooks are defined for hook-based agents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        hook_agents = ["claude-code", "codex", "opencode"]
        for name in hook_agents:
            agent = integration.agents[name]
            assert "SessionStart" in agent.hooks
            assert "UserPromptSubmit" in agent.hooks
            assert "PreToolUse" in agent.hooks
            assert "PostToolUse" in agent.hooks
            assert "Stop" in agent.hooks

            # Each hook should have at least one handler
            for event, handlers in agent.hooks.items():
                assert len(handlers) > 0
                assert handlers[0]["type"] == "command"
                assert "runtime.py" in handlers[0]["command"]


def test_reference_agents_no_hooks():
    """Test reference agents have no hooks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        ref_agents = ["cursor", "gemini", "copilot", "windsurf", "kiro"]
        for name in ref_agents:
            agent = integration.agents[name]
            assert agent.hooks == {}


def test_hermes_hooks():
    """Test Hermes has correct hook events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        agent = integration.agents["hermes"]
        assert "pre_llm_call" in agent.hooks
        assert "post_llm_call" in agent.hooks
        assert "post_tool_call" in agent.hooks


def test_claude_md_template():
    """Test CLAUDE.md template generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        template = integration._claude_md_template()
        assert "AgentEnhancements" in template
        assert str(base_dir) in template


def test_codex_agents_md_template():
    """Test Codex AGENTS.md template."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        template = integration._codex_agents_md_template()
        assert "AgentEnhancements" in template
        assert "registry.py" in template


def test_opencode_config_template():
    """Test OpenCode JSONC template."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        template = integration._opencode_config_template()
        assert "agentEnhancements" in template
        assert str(base_dir) in template


def test_cursor_rule_template():
    """Test Cursor .mdc rule template."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        template = integration._cursor_main_rule_template()
        assert "AgentEnhancements" in template
        assert "alwaysApply: false" in template


def test_gemini_templates():
    """Test Gemini templates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        md_template = integration._gemini_md_template()
        assert "AgentEnhancements" in md_template

        yaml_template = integration._gemini_config_template()
        assert "base_dir" in yaml_template


def test_make_hook_command():
    """Test _make_hook_command generates safe command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        cmd = integration._make_hook_command("UserPromptSubmit")

        # Should contain Python executable and runtime.py
        import sys
        assert sys.executable in cmd
        assert "runtime.py" in cmd
        assert "UserPromptSubmit" in cmd
        # Should have env vars
        assert "AGENT_ENHANCEMENTS_BASE_DIR" in cmd
        assert "AGENT_MEMORY_ROOT" in cmd


def test_install_unknown_agent():
    """Test installing unknown agent returns False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        integration = NativeIntegrationV2(base_dir)

        result = integration.install_agent("unknown-agent", dry_run=True)
        assert result == False


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])