#!/usr/bin/env python3
"""
Tests for AdaptivePreflightV2.
"""

import json
import tempfile
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from adaptive_preflight_v2 import (
    AdaptivePreflightV2, PreflightConfig, PreflightMode,
    PreflightResult, SelectedCapability
)
import registry


def test_preflight_mode_enum():
    """Test PreflightMode enum."""
    assert PreflightMode.LEGACY.value == 0
    assert PreflightMode.NATIVE_AUTO.value == 1
    assert PreflightMode.CUSTOM_ENDPOINT.value == 2


def test_preflight_config_defaults():
    """Test PreflightConfig defaults."""
    config = PreflightConfig()
    assert config.mode == PreflightMode.LEGACY
    assert config.max_skill_cards == 8
    assert config.token_budget == 400
    assert config.deadline_ms == 2000
    assert config.fallback_on_error == True


def test_adaptive_preflight_v2_init():
    """Test AdaptivePreflightV2 initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        preflight = AdaptivePreflightV2(base_dir, registry)

        assert preflight.base_dir == base_dir
        assert preflight.registry == registry
        assert isinstance(preflight.config, PreflightConfig)


def test_conflict_groups_defined():
    """Test conflict groups are defined."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        preflight = AdaptivePreflightV2(base_dir, registry)

        assert len(preflight.CONFLICT_GROUPS) > 0
        # Check expected conflict groups
        frameworks = set()
        for group in preflight.CONFLICT_GROUPS:
            frameworks.update(group)
        assert "django" in frameworks
        assert "react" in frameworks
        assert "aws" in frameworks


def test_mode_0_legacy_fallback():
    """Test Mode 0 (legacy) fallback behavior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        preflight = AdaptivePreflightV2(base_dir, registry)
        preflight.config.mode = PreflightMode.LEGACY

        # Mock fallback function
        def fallback_fn(agent, prompt):
            return "fallback result"

        event = {"hook_event_name": "UserPromptSubmit", "cwd": "/tmp", "session_id": "test"}
        result = preflight.run("claude-code", "test task", event, fallback_fn)

        assert result.mode == PreflightMode.LEGACY
        assert result.fallback_used == False


def test_mode_1_unsupported_fallback():
    """Test Mode 1 falls back to Mode 0 with warning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        preflight = AdaptivePreflightV2(base_dir, registry)
        preflight.config.mode = PreflightMode.NATIVE_AUTO
        preflight.config.fallback_on_error = True

        def fallback_fn(agent, prompt):
            return "fallback result"

        event = {"hook_event_name": "UserPromptSubmit", "cwd": "/tmp", "session_id": "test"}
        result = preflight.run("claude-code", "test task", event, fallback_fn)

        assert result.mode == PreflightMode.LEGACY
        assert result.fallback_used == True
        assert len(result.warnings) > 0
        assert "unsupported" in result.warnings[0].lower()


def test_mode_2_missing_config_fallback():
    """Test Mode 2 falls back when config missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        preflight = AdaptivePreflightV2(base_dir, registry)
        preflight.config.mode = PreflightMode.CUSTOM_ENDPOINT
        preflight.config.fallback_on_error = True
        # No endpoint_url or model_name set

        def fallback_fn(agent, prompt):
            return "fallback result"

        event = {"hook_event_name": "UserPromptSubmit", "cwd": "/tmp", "session_id": "test"}
        result = preflight.run("claude-code", "test task", event, fallback_fn)

        assert result.mode == PreflightMode.LEGACY
        assert result.fallback_used == True
        assert len(result.warnings) > 0


def test_preflight_result_dataclass():
    """Test PreflightResult dataclass."""
    result = PreflightResult(mode=PreflightMode.LEGACY)
    assert result.mode == PreflightMode.LEGACY
    assert result.skills == []
    assert result.plugins == []
    assert result.mcp_servers == []
    assert result.builtins == []
    assert result.lookups == []
    assert result.unresolved == []
    assert result.warnings == []
    assert result.token_estimate == 0
    assert result.fallback_used == False
    assert result.selector_latency_ms == 0
    assert result.abstained == False


def test_selected_capability_dataclass():
    """Test SelectedCapability dataclass."""
    cap = SelectedCapability(
        type="skill",
        id="skill:test-skill",
        name="test-skill",
        version="1.0.0",
        readiness="ready",
        readiness_reason="All dependencies satisfied",
        token_estimate=100,
    )
    assert cap.type == "skill"
    assert cap.id == "skill:test-skill"
    assert cap.readiness == "ready"
    assert cap.role == "optional"
    assert cap.conflict_with == []


def test_load_config_from_ui_api_json():
    """Test loading config from ui.api.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        # Create ui.api.json with preflight config
        ui_api = {
            "preflight": {
                "mode": 2,
                "endpoint_url": "https://api.example.com/v1",
                "model_name": "test-model",
                "api_key_ref": "TEST_KEY",
                "max_rounds": 3,
                "deadline_ms": 3000,
                "max_skill_cards": 10,
                "token_budget": 500,
                "fallback_on_error": False
            }
        }
        (base_dir / "ui.api.json").write_text(json.dumps(ui_api))

        preflight = AdaptivePreflightV2(base_dir, registry)

        assert preflight.config.mode == PreflightMode.CUSTOM_ENDPOINT
        assert preflight.config.endpoint_url == "https://api.example.com/v1"
        assert preflight.config.model_name == "test-model"
        assert preflight.config.api_key_ref == "TEST_KEY"
        assert preflight.config.max_rounds == 3
        assert preflight.config.deadline_ms == 3000
        assert preflight.config.max_skill_cards == 10
        assert preflight.config.token_budget == 500
        assert preflight.config.fallback_on_error == False


def test_load_config_env_override():
    """Test environment variable overrides."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        import os
        os.environ["AE_PREFLIGHT_MODE"] = "2"
        os.environ["AE_PREFLIGHT_DEADLINE_MS"] = "5000"
        os.environ["AE_MAX_SKILL_CARDS"] = "12"

        try:
            preflight = AdaptivePreflightV2(base_dir, registry)
            assert preflight.config.mode == PreflightMode.CUSTOM_ENDPOINT
            assert preflight.config.deadline_ms == 5000
            assert preflight.config.max_skill_cards == 12
        finally:
            del os.environ["AE_PREFLIGHT_MODE"]
            del os.environ["AE_PREFLIGHT_DEADLINE_MS"]
            del os.environ["AE_MAX_SKILL_CARDS"]


def test_build_selector_prompt():
    """Test selector prompt building."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        preflight = AdaptivePreflightV2(base_dir, registry)

        event = {"hook_event_name": "UserPromptSubmit", "cwd": "/tmp", "session_id": "test"}
        prompt = preflight._build_selector_prompt("claude-code", "build an MCP server", event)

        assert "claude-code" in prompt
        assert "build an MCP server" in prompt
        assert "CATALOG SUMMARY" in prompt
        assert "JSON only" in prompt


def test_detect_conflicts():
    """Test conflict detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        preflight = AdaptivePreflightV2(base_dir, registry)

        # Test django conflict
        conflicts = preflight._detect_conflicts("django-rest-framework", "skill")
        assert "flask" in conflicts or "fastapi" in conflicts

        # Test react conflict
        conflicts = preflight._detect_conflicts("react-component", "skill")
        assert "vue" in conflicts or "angular" in conflicts or "svelte" in conflicts


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])