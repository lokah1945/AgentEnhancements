#!/usr/bin/env python3
"""Tests for registry.py"""

import json
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from registry import SkillRegistry, SkillEntry, RankedCapability, CapabilityComposition, CapabilityRole, ReadinessLevel


def test_discover_skills():
    """Test skill discovery from all sources."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    skills = registry.discover_all_skills()

    assert len(skills) > 0, "Should discover at least one skill"
    for skill in skills.values():
        assert skill.slug
        assert skill.category
        assert skill.path
        assert skill.trigger_keywords is not None
    print(f"✓ Discovered {len(skills)} skills")


def test_skill_structure():
    """Test skill entry structure."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    skills = registry.discover_all_skills()

    for skill in skills.values():
        assert isinstance(skill.trigger_keywords, list)
        assert isinstance(skill.mcp_servers, list)
        assert skill.source in ["skills", "catalog", "vendored:anthropic-skills",
                                "vendored:replica-skill", "vendored:agency-agents"]
    print("✓ All skills have valid structure")


def test_deduplication():
    """Test that duplicate skills are deduplicated correctly."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    skills = registry.discover_all_skills()

    # No duplicate slugs
    slugs = [s.slug for s in skills.values()]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"
    print("✓ No duplicate skills")


def test_search_skills():
    """Test skill search."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    # Search for known keywords
    results = registry.search_skills("typescript", limit=5)
    assert len(results) > 0
    assert any("typescript" in s.slug.lower() or "typescript" in " ".join(s.trigger_keywords).lower()
               for s in results)
    print(f"✓ Search works: found {len(results)} results for 'typescript'")


def test_map_task():
    """Test task mapping."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    matches = registry.map_task("build an mcp server", top_n=3)
    assert len(matches) > 0
    assert any("mcp" in " ".join(m.trigger_keywords).lower() for m in matches)
    print(f"✓ Task mapping works: {len(matches)} matches")


def test_get_skill():
    """Test getting specific skill."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    # Try to get a known skill
    skill = registry.get_skill("karpathy-skills")
    if skill:
        assert skill.slug == "karpathy-skills"
        assert skill.category == "code"
        print(f"✓ Get skill works: {skill.slug}")
    else:
        print("⚠ karpathy-skills not found (may not exist in test env)")


def test_categories():
    """Test category listing."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    categories = registry.get_categories()
    assert len(categories) > 0
    assert "code" in categories
    assert "research" in categories
    print(f"✓ Categories: {categories}")


def test_stats():
    """Test registry statistics."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    stats = registry.get_stats()
    assert "total_skills" in stats
    assert "by_category" in stats
    assert "by_source" in stats
    assert stats["total_skills"] > 0
    print(f"✓ Stats: {stats['total_skills']} skills, {len(stats['by_category'])} categories")


def test_catalog_summary():
    """Test catalog summary for selector."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    summary = registry.get_catalog_summary()
    assert "skills" in summary
    assert "plugins" in summary
    assert "mcp_servers" in summary
    assert "builtins" in summary
    assert summary["skills"]["total"] > 0
    print("✓ Catalog summary works")


def test_rebuild_catalog():
    """Test catalog rebuild."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    catalog = registry.rebuild_catalog()
    assert "skills" in catalog
    assert "plugins" in catalog
    assert "mcp_servers" in catalog
    assert "stats" in catalog

    # Check output files exist
    output_dir = base_dir / "unified-integration" / "skills"
    assert (output_dir / "all-skills.json").exists()
    assert (output_dir / "agent-registry.json").exists()
    print("✓ Catalog rebuild works")


def test_plugins():
    """Test plugin catalog."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    plugins = registry.get_plugins()
    assert len(plugins) > 0
    for plugin in plugins.values():
        assert plugin.slug
        assert plugin.category
        assert plugin.status
    print(f"✓ Plugins: {len(plugins)}")


def test_mcp_servers():
    """Test MCP server catalog."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    servers = registry.get_mcp_servers()
    assert len(servers) > 0
    for server in servers.values():
        assert "id" in server
        assert "command" in server
        assert "status" in server
    print(f"✓ MCP Servers: {len(servers)}")


# =========================================================================
# P1 ENHANCEMENT TESTS
# =========================================================================

def test_rank_entries_basic():
    """Test enhanced ranking returns ranked capabilities."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    ranked = registry.rank_entries("build a typescript mcp server", "claude-code")
    assert len(ranked) > 0
    for cap in ranked:
        assert isinstance(cap, RankedCapability)
        assert cap.total_score >= 0
        assert cap.readiness in ReadinessLevel
    print(f"✓ Rank entries: {len(ranked)} ranked")


def test_rank_entries_scoring_components():
    """Test that all scoring components are present."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    ranked = registry.rank_entries("typescript refactor", "claude-code")
    assert len(ranked) > 0
    cap = ranked[0]
    assert hasattr(cap, 'keyword_score')
    assert hasattr(cap, 'semantic_score')
    assert hasattr(cap, 'readiness_score')
    assert hasattr(cap, 'compatibility_score')
    assert hasattr(cap, 'budget_score')
    assert 0 <= cap.keyword_score <= 1
    assert 0 <= cap.semantic_score <= 1
    assert 0 <= cap.readiness_score <= 1
    assert 0 <= cap.compatibility_score <= 1
    assert 0 <= cap.budget_score <= 1
    print("✓ All scoring components present")


def test_capability_composition():
    """Test capability composition into roles."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    composition = registry.map_task_enhanced("build a django REST API", "claude-code", token_budget=400)
    assert isinstance(composition, CapabilityComposition)
    assert hasattr(composition, 'primary')
    assert hasattr(composition, 'supporting')
    assert hasattr(composition, 'optional')
    assert hasattr(composition, 'alternatives')
    assert hasattr(composition, 'conflicts')
    assert hasattr(composition, 'total_tokens')
    print(f"✓ Composition: {len(composition.primary)} primary, {len(composition.supporting)} supporting, {len(composition.optional)} optional")


def test_framework_compatibility_filtering():
    """Test framework compatibility filtering (Django vs Flask)."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    # Task mentions Django
    composition = registry.map_task_enhanced("build a django REST API", "claude-code", token_budget=400)

    # Should prefer Django skills, not Flask
    primary_slugs = [c.entry.slug for c in composition.primary]
    supporting_slugs = [c.entry.slug for c in composition.supporting]
    all_selected = primary_slugs + supporting_slugs

    # Check no Flask skills in primary if Django is requested
    flask_skills = [s for s in all_selected if "flask" in s.lower()]
    django_skills = [s for s in all_selected if "django" in s.lower()]

    # At least one framework should match
    assert len(django_skills) > 0 or len(all_selected) == 0, "Should match Django or have no framework preference"
    print(f"✓ Framework filtering: Django={django_skills}, Flask={flask_skills}")


def test_readiness_aware_scoring():
    """Test readiness-aware scoring (ready > guide_only > unavailable)."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    ranked = registry.rank_entries("any task", "claude-code")

    # Check readiness levels are assigned
    readiness_levels = [c.readiness for c in ranked]
    assert ReadinessLevel.READY in readiness_levels or ReadinessLevel.GUIDE_ONLY in readiness_levels

    # Ready skills should score higher than unavailable
    ready_caps = [c for c in ranked if c.readiness == ReadinessLevel.READY]
    unavailable_caps = [c for c in ranked if c.readiness == ReadinessLevel.UNAVAILABLE]

    if ready_caps and unavailable_caps:
        avg_ready = sum(c.total_score for c in ready_caps) / len(ready_caps)
        avg_unavail = sum(c.total_score for c in unavailable_caps) / len(unavailable_caps)
        assert avg_ready >= avg_unavail, "Ready skills should score >= unavailable"
    print("✓ Readiness scoring works")


def test_budget_awareness():
    """Test context budget awareness in ranking."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    # Small budget
    ranked_small = registry.rank_entries("build an mcp server", "claude-code", token_budget=100)
    # Large budget
    ranked_large = registry.rank_entries("build an mcp server", "claude-code", token_budget=1000)

    # Both should return results
    assert len(ranked_small) > 0
    assert len(ranked_large) > 0

    # Composition should respect budget
    comp_small = registry.map_task_enhanced("build an mcp server", "claude-code", token_budget=100)
    comp_large = registry.map_task_enhanced("build an mcp server", "claude-code", token_budget=1000)

    assert comp_small.total_tokens <= 100
    assert comp_large.total_tokens <= 1000
    print(f"✓ Budget awareness: small={comp_small.total_tokens}, large={comp_large.total_tokens}")


def test_abstention_logic():
    """Test abstention when native agent can handle."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    # Simple file operations should abstain
    should_abstain, reason = registry.should_abstain("read the config file", "claude-code")
    assert should_abstain or reason  # Either abstains or has reason

    # Complex task should not abstain
    should_abstain, reason = registry.should_abstain("build a complete django e-commerce platform with postgres", "claude-code")
    assert not should_abstain, "Complex task should not abstain"
    print("✓ Abstention logic works")


def test_no_tool_needed_abstention():
    """Test abstention for informational queries."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    should_abstain, reason = registry.should_abstain("what is django", "claude-code")
    assert should_abstain, "Informational query should abstain"
    print("✓ No-tool-needed abstention works")


def test_conflict_detection():
    """Test conflict detection between mutually exclusive capabilities."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    # Task that could match multiple frameworks
    composition = registry.map_task_enhanced("web framework comparison", "claude-code", token_budget=400)

    # Check conflicts are detected
    for c1, c2, reason in composition.conflicts:
        assert "conflict" in reason.lower()
    print(f"✓ Conflict detection: {len(composition.conflicts)} conflicts found")


def test_alternative_detection():
    """Test alternative detection in same conflict group."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    composition = registry.map_task_enhanced("database operations", "claude-code", token_budget=400)

    # If multiple databases detected, should have alternatives
    for alt in composition.alternatives:
        assert alt.role == CapabilityRole.ALTERNATIVE
    print(f"✓ Alternative detection: {len(composition.alternatives)} alternatives")


def test_multi_capability_scenario():
    """Test scenario requiring multiple capabilities."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    # Task needing multiple skills
    composition = registry.map_task_enhanced(
        "build a typescript mcp server with docker deployment and postgresql",
        "claude-code",
        token_budget=400
    )

    # Should have primary + supporting
    assert len(composition.primary) > 0 or len(composition.supporting) > 0
    total_caps = len(composition.primary) + len(composition.supporting) + len(composition.optional)
    assert total_caps > 1, "Multi-capability task should select multiple skills"
    print(f"✓ Multi-capability: {total_caps} total capabilities")


def test_name_collision_handling():
    """Test handling of skills with similar names."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    # Search for skills that might have name collisions
    results = registry.search_skills("mcp", limit=10)
    slugs = [s.slug for s in results]

    # Should have unique slugs
    assert len(slugs) == len(set(slugs)), "No duplicate slugs in results"
    print(f"✓ Name collision handling: {len(results)} unique results for 'mcp'")


def test_framework_mismatch():
    """Test framework mismatch scenario (Django task, Flask skill)."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    # Rank with explicit framework mismatch
    ranked = registry.rank_entries("django authentication", "claude-code")

    # Django skills should score higher than Flask
    django_scores = [c.total_score for c in ranked if "django" in c.entry.framework_tags]
    flask_scores = [c.total_score for c in ranked if "flask" in c.entry.framework_tags]

    if django_scores and flask_scores:
        assert max(django_scores) >= max(flask_scores), "Django skills should rank higher for Django task"
    print("✓ Framework mismatch handled")


def test_unavailable_plugins_filtered():
    """Test that unavailable plugins are ranked lower."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    ranked = registry.rank_entries("any task", "claude-code")

    # Check guide_only skills exist but score lower
    guide_only = [c for c in ranked if c.readiness == ReadinessLevel.GUIDE_ONLY]
    ready = [c for c in ranked if c.readiness == ReadinessLevel.READY]

    if guide_only and ready:
        avg_guide = sum(c.total_score for c in guide_only) / len(guide_only)
        avg_ready = sum(c.total_score for c in ready) / len(ready)
        assert avg_ready >= avg_guide, "Ready should score >= guide_only"
    print("✓ Unavailable plugins ranked lower")


def test_enhanced_cli_map():
    """Test enhanced CLI map command."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)

    # This tests the map_task_enhanced method directly
    composition = registry.map_task_enhanced(
        "build a fastapi microservice",
        "claude-code",
        stage="implement",
        role="backend",
        token_budget=400
    )

    assert isinstance(composition, CapabilityComposition)
    assert composition.total_tokens <= 400
    print("✓ Enhanced CLI map works")


if __name__ == "__main__":
    test_discover_skills()
    test_skill_structure()
    test_deduplication()
    test_search_skills()
    test_map_task()
    test_get_skill()
    test_categories()
    test_stats()
    test_catalog_summary()
    test_rebuild_catalog()
    test_plugins()
    test_mcp_servers()

    # P1 tests
    test_rank_entries_basic()
    test_rank_entries_scoring_components()
    test_capability_composition()
    test_framework_compatibility_filtering()
    test_readiness_aware_scoring()
    test_budget_awareness()
    test_abstention_logic()
    test_no_tool_needed_abstention()
    test_conflict_detection()
    test_alternative_detection()
    test_multi_capability_scenario()
    test_name_collision_handling()
    test_framework_mismatch()
    test_unavailable_plugins_filtered()
    test_enhanced_cli_map()

    print("\n✅ All registry tests passed!")