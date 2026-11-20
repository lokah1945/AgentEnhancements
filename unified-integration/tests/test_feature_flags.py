#!/usr/bin/env python3
"""Tests for feature_flags.py"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from feature_flags import (
    FeatureFlags, FeatureFlag, FeatureConfig,
    MetricsCollector, ABTestManager
)


def test_default_flags():
    """Test default flag configurations."""
    base_dir = Path(__file__).parent.parent.parent
    config_path = base_dir / "unified-integration" / "config" / "feature_flags.json"
    flags = FeatureFlags(config_path)

    all_flags = flags.list_flags()
    assert len(all_flags) == len(FeatureFlag)

    # Check core flags exist
    flag_names = [f["flag"] for f in all_flags]
    assert "preflight_mode" in flag_names
    assert "quality_guidance" in flag_names
    assert "mcp_gateway" in flag_names
    assert "memory_persistence" in flag_names
    print(f"✓ Default flags: {len(all_flags)} flags")


def test_flag_enabled_disabled():
    """Test enabling/disabling flags."""
    base_dir = Path(__file__).parent.parent.parent
    config_path = base_dir / "unified-integration" / "config" / "feature_flags.json"
    flags = FeatureFlags(config_path)

    # Test global enable
    flags.set_enabled(FeatureFlag.QUALITY_GUIDANCE, True)
    assert flags.is_enabled(FeatureFlag.QUALITY_GUIDANCE) == True

    # Test global disable
    flags.set_enabled(FeatureFlag.QUALITY_GUIDANCE, False)
    assert flags.is_enabled(FeatureFlag.QUALITY_GUIDANCE) == False

    # Test host-specific override
    flags.set_enabled(FeatureFlag.QUALITY_GUIDANCE, True, "claude-code")
    assert flags.is_enabled(FeatureFlag.QUALITY_GUIDANCE, "claude-code") == True
    assert flags.is_enabled(FeatureFlag.QUALITY_GUIDANCE, "codex") == False
    print("✓ Flag enable/disable works")


def test_rollout_percentage():
    """Test rollout percentage."""
    base_dir = Path(__file__).parent.parent.parent
    config_path = base_dir / "unified-integration" / "config" / "feature_flags.json"
    flags = FeatureFlags(config_path)

    # Set 50% rollout
    flags.set_rollout(FeatureFlag.STAGE_HINTS, 50.0)
    config = flags.get_config(FeatureFlag.STAGE_HINTS)
    assert config.rollout_percentage == 50.0

    # Test invalid percentage
    assert flags.set_rollout(FeatureFlag.STAGE_HINTS, 150.0) == False
    assert flags.set_rollout(FeatureFlag.STAGE_HINTS, -10.0) == False
    print("✓ Rollout percentage works")


def test_host_overrides():
    """Test host-specific overrides."""
    base_dir = Path(__file__).parent.parent.parent
    config_path = base_dir / "unified-integration" / "config" / "feature_flags.json"
    flags = FeatureFlags(config_path)

    # Set host override
    flags.set_enabled(FeatureFlag.SUBAGENT_SUPPORT, True, "claude-code")
    flags.set_enabled(FeatureFlag.SUBAGENT_SUPPORT, False, "codex")

    overrides = flags.get_host_overrides(FeatureFlag.SUBAGENT_SUPPORT)
    assert overrides.get("claude-code") == True
    assert overrides.get("codex") == False
    print("✓ Host overrides work")


def test_all_flags_for_host():
    """Test getting all flags for a host."""
    base_dir = Path(__file__).parent.parent.parent
    config_path = base_dir / "unified-integration" / "config" / "feature_flags.json"
    flags = FeatureFlags(config_path)

    all_flags = flags.get_all_flags("claude-code")
    assert len(all_flags) == len(FeatureFlag)
    assert all(isinstance(v, bool) for v in all_flags.values())
    print("✓ All flags for host works")


def test_metrics_collection():
    """Test metrics recording and retrieval."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        metrics = MetricsCollector(memory_dir)

        # Record some metrics
        metrics.record("task_success", 1.0, task_id="task-1", host="claude-code", variant="treatment")
        metrics.record("task_success", 1.0, task_id="task-2", host="claude-code", variant="treatment")
        metrics.record("task_success", 0.0, task_id="task-3", host="claude-code", variant="control")
        metrics.record("latency_ms", 150.0, task_id="task-1", host="claude-code", variant="treatment")
        metrics.record("latency_ms", 200.0, task_id="task-3", host="claude-code", variant="control")

        # Get summary
        summary = metrics.get_summary("task_success", "treatment")
        assert summary["count"] == 2
        assert summary["mean"] == 1.0

        summary = metrics.get_summary("task_success", "control")
        assert summary["count"] == 1
        assert summary["mean"] == 0.0

        # Latency summary
        latency = metrics.get_summary("latency_ms", "treatment")
        assert latency["count"] == 1
        assert latency["mean"] == 150.0

    print("✓ Metrics collection works")


def test_metrics_batch():
    """Test batch metric recording."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        metrics = MetricsCollector(memory_dir)

        batch = [
            {"metric_name": "batch_test", "metric_value": float(i), "variant": "treatment"}
            for i in range(10)
        ]
        metrics.record_batch(batch)

        summary = metrics.get_summary("batch_test", "treatment")
        assert summary["count"] == 10
        assert summary["mean"] == 4.5  # (0+1+...+9)/10
        print("✓ Metrics batch recording works")


def test_compare_variants():
    """Test variant comparison."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        metrics = MetricsCollector(memory_dir)

        # Control: lower success
        for _ in range(20):
            metrics.record("success_rate", 0.7, variant="control")
        # Treatment: higher success
        for _ in range(20):
            metrics.record("success_rate", 0.9, variant="treatment")

        comparison = metrics.compare_variants("success_rate")
        assert comparison["control"]["mean"] == 0.7
        assert comparison["treatment"]["mean"] == 0.9
        assert abs(comparison["difference"] - 0.2) < 0.001  # Floating point tolerance
        assert abs(comparison["relative_change"] - 0.2857) < 0.01  # 0.2/0.7
        print("✓ Variant comparison works")


def test_ab_test_assignment():
    """Test A/B test variant assignment."""
    base_dir = Path(__file__).parent.parent.parent
    config_path = base_dir / "unified-integration" / "config" / "feature_flags.json"
    flags = FeatureFlags(config_path)
    memory_dir = base_dir / ".agentenhancements" / "memory"
    metrics = MetricsCollector(memory_dir)
    ab_test = ABTestManager(flags, metrics)

    # Enable feature for testing
    flags.set_enabled(FeatureFlag.QUALITY_GUIDANCE, True)

    # Assign variants
    variant1 = ab_test.assign_variant("task-1", "claude-code", FeatureFlag.QUALITY_GUIDANCE)
    variant2 = ab_test.assign_variant("task-2", "claude-code", FeatureFlag.QUALITY_GUIDANCE)
    variant3 = ab_test.assign_variant("task-3", "claude-code", FeatureFlag.QUALITY_GUIDANCE)

    # Should get some of each
    variants = {variant1, variant2, variant3}
    assert "control" in variants or "treatment" in variants
    print(f"✓ A/B assignment: {variants}")

    # Same task should get same variant
    variant1_again = ab_test.assign_variant("task-1", "claude-code", FeatureFlag.QUALITY_GUIDANCE)
    assert variant1_again == variant1
    print("✓ Consistent assignment works")


def test_ab_test_metric_recording():
    """Test recording metrics for assigned variant."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(__file__).parent.parent.parent
        config_path = base_dir / "unified-integration" / "config" / "feature_flags.json"
        flags = FeatureFlags(config_path)
        memory_dir = Path(tmpdir)
        metrics = MetricsCollector(memory_dir)
        ab_test = ABTestManager(flags, metrics)

        flags.set_enabled(FeatureFlag.QUALITY_GUIDANCE, True)
        variant = ab_test.assign_variant("task-ab-1", "claude-code", FeatureFlag.QUALITY_GUIDANCE)

        ab_test.record_metric("task-ab-1", "success", 1.0)
        ab_test.record_metric("task-ab-1", "latency", 100.0)

        # Check metrics were recorded with correct variant
        summary = metrics.get_summary("success", variant)
        assert summary["count"] == 1
        assert summary["mean"] == 1.0
        print("✓ A/B metric recording works")


if __name__ == "__main__":
    test_default_flags()
    test_flag_enabled_disabled()
    test_rollout_percentage()
    test_host_overrides()
    test_all_flags_for_host()
    test_metrics_collection()
    test_metrics_batch()
    test_compare_variants()
    test_ab_test_assignment()
    test_ab_test_metric_recording()
    print("\n✅ All feature_flags tests passed!")