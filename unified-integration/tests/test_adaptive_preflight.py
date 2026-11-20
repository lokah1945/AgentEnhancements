#!/usr/bin/env python3
"""Tests for adaptive_preflight.py"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from adaptive_preflight import AdaptivePreflight, PreflightMode, PreflightConfig
from registry import SkillRegistry


def test_mode_0_legacy():
    """Test Mode 0 (legacy) preflight."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    preflight = AdaptivePreflight(base_dir, registry)

    # Force mode 0
    preflight.config.mode = PreflightMode.LEGACY

    result = preflight.run(
        task_description="build a typescript mcp server",
        agent_type="claude-code",
        session_id="test123"
    )

    assert result.mode == PreflightMode.LEGACY
    assert len(result.skills) > 0
    assert result.token_estimate > 0
    assert not result.fallback_used
    print(f"✓ Mode 0: {len(result.skills)} skills, {result.token_estimate} tokens")


def test_mode_0_no_fallback():
    """Test Mode 0 doesn't use fallback."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    preflight = AdaptivePreflight(base_dir, registry)
    preflight.config.mode = PreflightMode.LEGACY

    result = preflight.run("any task", "claude-code", "s1")
    assert not result.fallback_used
    print("✓ Mode 0 no fallback")


def test_readiness_checks():
    """Test readiness checking for skills, plugins, MCP."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    preflight = AdaptivePreflight(base_dir, registry)

    # Check skill readiness
    skill = registry.get_skill("karpathy-skills")
    if skill:
        readiness = preflight._check_skill_readiness(skill, "claude-code")
        assert readiness["status"] in ["ready", "guide_only", "unavailable", "missing_credentials", "not_installed"]
        print(f"✓ Skill readiness: {readiness}")

    # Check plugin readiness
    plugins = registry.get_plugins()
    if plugins:
        plugin = list(plugins.values())[0]
        readiness = preflight._check_plugin_readiness(plugin, "claude-code")
        assert readiness["status"] in ["ready", "guide_only", "unavailable", "missing_credentials", "not_installed"]
        print(f"✓ Plugin readiness: {readiness}")


def test_mcp_matching():
    """Test MCP server matching."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    preflight = AdaptivePreflight(base_dir, registry)

    matches = preflight._match_mcp_servers("search the web", None)
    # Should find web-search-mcp
    assert any("web" in m["id"] or "search" in m["id"] for m in matches)
    print(f"✓ MCP matching: {len(matches)} matches")


def test_plugin_matching():
    """Test plugin matching."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    preflight = AdaptivePreflight(base_dir, registry)

    matches = preflight._match_plugins("typescript refactor")
    assert len(matches) > 0
    print(f"✓ Plugin matching: {len(matches)} matches")


def test_builtins():
    """Test builtin capabilities."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    preflight = AdaptivePreflight(base_dir, registry)

    builtins = preflight._get_builtins("claude-code")
    assert len(builtins) >= 3
    assert any(b.id == "registry_search" for b in builtins)
    assert any(b.id == "memory_save" for b in builtins)
    print(f"✓ Builtins: {len(builtins)}")


def test_token_estimation():
    """Test token estimation."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    preflight = AdaptivePreflight(base_dir, registry)

    skill = registry.get_skill("karpathy-skills")
    if skill:
        tokens = preflight._estimate_skill_tokens(skill)
        assert tokens > 0
        print(f"✓ Token estimation: {tokens} tokens")


def test_config_loading():
    """Test config loading from ui.api.json."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        registry = SkillRegistry(base_dir)

        # Should not crash even without ui.api.json
        preflight = AdaptivePreflight(base_dir, registry)
        assert preflight.config.mode == PreflightMode.LEGACY
    print("✓ Config loading works")


def test_selector_prompt():
    """Test selector prompt building."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    preflight = AdaptivePreflight(base_dir, registry)

    prompt = preflight._build_selector_prompt("test task", "claude-code", {})
    assert "test task" in prompt
    assert "claude-code" in prompt
    assert "selected_skills" in prompt
    print("✓ Selector prompt building works")


def test_parse_selector_response():
    """Test parsing selector response."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    preflight = AdaptivePreflight(base_dir, registry)

    # Valid JSON
    response = '{"selected_skills": ["skill1"], "selected_plugins": [], "selected_mcp": [], "reasoning": "test"}'
    parsed = preflight._parse_selector_response(response)
    assert parsed["selected_skills"] == ["skill1"]

    # JSON in markdown
    response = '```json\n{"selected_skills": ["skill2"]}\n```'
    parsed = preflight._parse_selector_response(response)
    assert parsed["selected_skills"] == ["skill2"]
    print("✓ Selector response parsing works")


if __name__ == "__main__":
    test_mode_0_legacy()
    test_mode_0_no_fallback()
    test_readiness_checks()
    test_mcp_matching()
    test_plugin_matching()
    test_builtins()
    test_token_estimation()
    test_config_loading()
    test_selector_prompt()
    test_parse_selector_response()
    print("\n✅ All adaptive preflight tests passed!")