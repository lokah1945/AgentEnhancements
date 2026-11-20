#!/usr/bin/env python3
"""Tests for load_skills.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from load_skills import LoadSkills, HOST_CAPABILITIES, CATEGORY_HOST_SUPPORT
from registry import SkillRegistry, ReadinessLevel


def test_host_capabilities_defined():
    """Test all expected hosts have capabilities defined."""
    expected = ["claude-code", "codex", "opencode", "hermes", "cursor", "gemini", "copilot", "windsurf", "kiro"]
    for host in expected:
        assert host in HOST_CAPABILITIES
        caps = HOST_CAPABILITIES[host]
        assert "hooks" in caps
        assert "skills" in caps
        assert "mcp" in caps
        assert "memory" in caps
        assert "compression" in caps
    print("✓ All host capabilities defined")


def test_category_host_support():
    """Test category to host support mapping."""
    for cat, hosts in CATEGORY_HOST_SUPPORT.items():
        assert isinstance(hosts, list)
        assert len(hosts) > 0
        for host in hosts:
            assert host in HOST_CAPABILITIES
    print("✓ Category host support valid")


def test_filter_by_host_claude_code():
    """Test filtering for Claude Code (full support)."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    all_skills = list(registry.discover_all_skills().values())
    filtered = loader.filter_by_host(all_skills, "claude-code")

    # Claude Code should support most skills
    assert len(filtered) > 0
    assert len(filtered) <= len(all_skills)
    print(f"✓ Claude Code filter: {len(filtered)}/{len(all_skills)} skills")


def test_filter_by_host_copilot():
    """Test filtering for Copilot (minimal support)."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    all_skills = list(registry.discover_all_skills().values())
    filtered = loader.filter_by_host(all_skills, "copilot")

    # Copilot has minimal support - should filter heavily
    assert len(filtered) <= len(all_skills)
    print(f"✓ Copilot filter: {len(filtered)}/{len(all_skills)} skills")


def test_filter_by_host_unknown():
    """Test filtering for unknown host (allows all)."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    all_skills = list(registry.discover_all_skills().values())
    filtered = loader.filter_by_host(all_skills, "unknown-host")

    # Unknown host should allow all
    assert len(filtered) == len(all_skills)
    print("✓ Unknown host allows all")


def test_load_on_demand():
    """Test on-demand skill loading."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    # Get a known skill
    skill = registry.get_skill("karpathy-skills")
    if not skill:
        print("⚠ karpathy-skills not found, skipping")
        return

    loaded = loader.load_on_demand([skill.slug], "claude-code")
    assert len(loaded) == 1
    assert loaded[0].entry.slug == skill.slug
    assert loaded[0].full_content
    assert loaded[0].readiness in ReadinessLevel
    print(f"✓ On-demand load: {loaded[0].entry.slug} - {loaded[0].readiness.value}")


def test_load_on_demand_caching():
    """Test that on-demand loading caches results."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    skill = registry.get_skill("karpathy-skills")
    if not skill:
        return

    loaded1 = loader.load_on_demand([skill.slug], "claude-code")
    loaded2 = loader.load_on_demand([skill.slug], "claude-code")

    # Should be same object (cached)
    assert loaded1[0] is loaded2[0]
    print("✓ On-demand caching works")


def test_get_minimal_set():
    """Test getting minimal skill set for a task."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    composition = loader.get_minimal_set(
        "build a typescript mcp server",
        "claude-code",
        max_tokens=400
    )

    assert hasattr(composition, 'primary')
    assert hasattr(composition, 'supporting')
    assert hasattr(composition, 'optional')
    assert composition.total_tokens <= 400
    print(f"✓ Minimal set: {len(composition.primary)} primary, {len(composition.supporting)} supporting")


def test_get_minimal_set_budget_respected():
    """Test that token budget is respected."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    composition = loader.get_minimal_set(
        "build a complete web application with database",
        "claude-code",
        max_tokens=100
    )

    assert composition.total_tokens <= 100
    print(f"✓ Budget respected: {composition.total_tokens} <= 100")


def test_get_minimal_set_host_filtering():
    """Test that host filtering is applied in minimal set."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    # Get composition for copilot (limited support)
    composition = loader.get_minimal_set(
        "typescript refactor",
        "copilot",
        max_tokens=400
    )

    # Should still work but may have fewer skills
    assert composition.total_tokens <= 400
    print(f"✓ Host filtering in minimal set: {len(composition.primary)} primary")


def test_get_skill_summary():
    """Test getting skill summary."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    skill = registry.get_skill("karpathy-skills")
    if not skill:
        return

    summary = loader.get_skill_summary(skill.slug, "claude-code")
    assert summary is not None
    assert summary["slug"] == skill.slug
    assert "readiness" in summary
    assert "host_compatible" in summary
    assert "estimated_tokens" in summary
    print(f"✓ Skill summary: {summary['slug']} - {summary['readiness']}")


def test_get_skill_summary_not_found():
    """Test skill summary for non-existent skill."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    summary = loader.get_skill_summary("non-existent-skill", "claude-code")
    assert summary is None
    print("✓ Non-existent skill returns None")


def test_host_compatibility_report():
    """Test host compatibility report."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    report = loader.get_host_compatibility_report("claude-code")
    assert "agent_type" in report
    assert "compatible_count" in report
    assert "incompatible_count" in report
    assert report["compatible_count"] + report["incompatible_count"] > 0
    print(f"✓ Host report: {report['compatible_count']} compatible, {report['incompatible_count']} incompatible")


def test_host_compatibility_report_all():
    """Test host compatibility report for all hosts."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    # Test each host
    for host in HOST_CAPABILITIES:
        report = loader.get_host_compatibility_report(host)
        assert report["agent_type"] == host
    print("✓ All host reports valid")


def test_stage_role_hints():
    """Test that stage/role hints are accepted."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    # Should accept stage/role without error
    composition = loader.get_minimal_set(
        "debug a typescript error",
        "claude-code",
        stage="debug",
        role="backend",
        max_tokens=400
    )
    assert composition.total_tokens <= 400
    print("✓ Stage/role hints accepted")


def test_context_parameter():
    """Test that context parameter is accepted."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    loader = LoadSkills(base_dir, registry)

    context = {
        "recent_tools": [{"tool": "read_file"}, {"tool": "write_file"}],
        "session_duration": 300
    }
    composition = loader.get_minimal_set(
        "continue the task",
        "claude-code",
        context=context,
        max_tokens=400
    )
    assert composition.total_tokens <= 400
    print("✓ Context parameter accepted")


if __name__ == "__main__":
    test_host_capabilities_defined()
    test_category_host_support()
    test_filter_by_host_claude_code()
    test_filter_by_host_copilot()
    test_filter_by_host_unknown()
    test_load_on_demand()
    test_load_on_demand_caching()
    test_get_minimal_set()
    test_get_minimal_set_budget_respected()
    test_get_minimal_set_host_filtering()
    test_get_skill_summary()
    test_get_skill_summary_not_found()
    test_host_compatibility_report()
    test_host_compatibility_report_all()
    test_stage_role_hints()
    test_context_parameter()
    print("\n✅ All load_skills tests passed!")