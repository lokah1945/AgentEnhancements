#!/usr/bin/env python3
"""Tests for native_integration.py"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from native_integration import NativeIntegration, AgentConfig


def test_agent_definitions():
    """Test all agent definitions exist."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    expected_agents = [
        "claude-code", "codex", "opencode", "hermes",
        "cursor", "gemini", "copilot", "windsurf", "kiro"
    ]

    for agent in expected_agents:
        assert agent in integration.agents
        info = integration.get_agent_info(agent)
        assert info["name"] == agent
        assert info["display_name"]
        assert info["config_dir"]
        print(f"✓ Agent defined: {agent}")


def test_claude_code_config():
    """Test Claude Code config generation."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    agent = integration.agents["claude-code"]
    assert "settings.json" in agent.config_files
    assert "CLAUDE.md" in agent.config_files

    # Validate settings.json is valid JSON
    settings = json.loads(agent.config_files["settings.json"])
    assert "hooks" in settings
    assert "SessionStart" in settings["hooks"]
    assert "UserPromptSubmit" in settings["hooks"]
    assert "env" in settings
    print("✓ Claude Code config valid")


def test_codex_config():
    """Test Codex config generation."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    agent = integration.agents["codex"]
    assert "AGENTS.md" in agent.config_files
    assert "hooks.json" in agent.config_files
    assert "config.toml" in agent.config_files

    hooks = json.loads(agent.config_files["hooks.json"])
    assert "hooks" in hooks
    print("✓ Codex config valid")


def test_opencode_config():
    """Test OpenCode config generation."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    agent = integration.agents["opencode"]
    assert "opencode.jsonc" in agent.config_files
    assert "AGENTS.md" in agent.config_files

    config = json.loads(agent.config_files["opencode.jsonc"])
    assert "plugins" in config
    assert "mcp" in config
    print("✓ OpenCode config valid")


def test_cursor_config():
    """Test Cursor config generation."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    agent = integration.agents["cursor"]
    assert "agent-enhancements.mdc" in agent.config_files

    content = agent.config_files["agent-enhancements.mdc"]
    assert content.startswith("---")
    assert "alwaysApply: true" in content
    print("✓ Cursor config valid")


def test_gemini_config():
    """Test Gemini CLI config generation."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    agent = integration.agents["gemini"]
    assert "GEMINI.md" in agent.config_files
    assert "config.yaml" in agent.config_files
    print("✓ Gemini config valid")


def test_copilot_config():
    """Test Copilot config generation."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    agent = integration.agents["copilot"]
    assert "config.yaml" in agent.config_files
    print("✓ Copilot config valid")


def test_windsurf_config():
    """Test Windsurf config generation."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    agent = integration.agents["windsurf"]
    assert "agent-enhancements.md" in agent.config_files
    print("✓ Windsurf config valid")


def test_kiro_config():
    """Test Kiro config generation."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    agent = integration.agents["kiro"]
    assert "config.yaml" in agent.config_files
    print("✓ Kiro config valid")


def test_install_skills_dry_run():
    """Test skill installation (dry run)."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        integration._install_skills(skills_dir, dry_run=True)
        # Dry run should not create files
        print("✓ Dry run install works")


def test_install_skills_real():
    """Test real skill installation."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        integration._install_skills(skills_dir, dry_run=False)

        # Should have installed skills
        skill_dirs = list(skills_dir.iterdir())
        assert len(skill_dirs) > 0

        # Check structure
        for skill_dir in skill_dirs[:3]:
            skill_file = skill_dir / "SKILL.md"
            assert skill_file.exists()
            content = skill_file.read_text()
            assert content.startswith("---")
    print("✓ Real skill install works")


def test_generate_launcher():
    """Test launcher script generation."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    with tempfile.NamedTemporaryFile(suffix='.sh', delete=False) as f:
        launcher_path = Path(f.name)

    try:
        integration.generate_launcher_script(launcher_path)
        assert launcher_path.exists()

        content = launcher_path.read_text()
        assert "claude-code" in content
        assert "codex" in content
        assert "opencode" in content
        assert "AGENT_ENHANCEMENTS_BASE_DIR" in content
    finally:
        launcher_path.unlink(missing_ok=True)

    print("✓ Launcher generation works")


def test_env_vars():
    """Test environment variables for agents."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    for agent_name in ["claude-code", "codex", "opencode", "hermes"]:
        agent = integration.agents[agent_name]
        assert "AGENT_ENHANCEMENTS_BASE_DIR" in agent.env_vars
        assert "AGENT_MEMORY_ROOT" in agent.env_vars
    print("✓ Env vars present")


def test_list_agents():
    """Test listing all agents."""
    base_dir = Path(__file__).parent.parent.parent
    integration = NativeIntegration(base_dir)

    agents = integration.list_agents()
    assert len(agents) == 9
    names = [a["name"] for a in agents]
    assert "claude-code" in names
    assert "codex" in names
    print("✓ List agents works")


if __name__ == "__main__":
    test_agent_definitions()
    test_claude_code_config()
    test_codex_config()
    test_opencode_config()
    test_cursor_config()
    test_gemini_config()
    test_copilot_config()
    test_windsurf_config()
    test_kiro_config()
    test_install_skills_dry_run()
    test_install_skills_real()
    test_generate_launcher()
    test_env_vars()
    test_list_agents()
    print("\n✅ All native integration tests passed!")