#!/usr/bin/env python3
"""
Tests for Unified Installer core.
"""

import json
import tempfile
import shutil
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from installer import UnifiedInstaller, InstallConfig, DetectedAgent


def test_installer_config_creation():
    """Test InstallConfig creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        config = InstallConfig(base_dir=base_dir)
        assert config.base_dir == base_dir
        assert config.dry_run == False
        assert config.agents is None


def test_detected_agent_dataclass():
    """Test DetectedAgent dataclass."""
    agent = DetectedAgent(
        name="claude-code",
        display_name="Claude Code",
        config_path=Path("/home/user/.claude"),
        exists=True
    )
    assert agent.name == "claude-code"
    assert agent.exists == True


def test_unified_installer_init():
    """Test UnifiedInstaller initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir).resolve()
        config = InstallConfig(base_dir=base_dir, dry_run=True)
        installer = UnifiedInstaller(config)
        assert installer.base_dir.resolve() == base_dir
        assert installer.config.dry_run == True


def test_prepare_directories_dry_run():
    """Test _prepare_directories in dry-run mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        config = InstallConfig(base_dir=base_dir, dry_run=True)
        installer = UnifiedInstaller(config)
        installer._prepare_directories()

        # In dry-run, directories should not be created
        assert not (base_dir / ".agentenhancements").exists()


def test_prepare_directories_real():
    """Test _prepare_directories creates directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        config = InstallConfig(base_dir=base_dir, dry_run=False)
        installer = UnifiedInstaller(config)
        installer._prepare_directories()

        assert (base_dir / ".agentenhancements" / "memory").exists()
        assert (base_dir / "unified-integration" / "config").exists()
        assert (base_dir / "unified-integration" / "hooks").exists()


def test_agent_detection_structure():
    """Test AGENT_PATHS structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        config = InstallConfig(base_dir=base_dir)
        installer = UnifiedInstaller(config)

        # Check all expected agents are defined
        expected_agents = {
            "claude-code", "codex", "opencode", "hermes",
            "cursor", "gemini", "copilot", "windsurf", "kiro"
        }
        assert set(installer.AGENT_PATHS.keys()) == expected_agents

        # Check each has required fields
        for name, info in installer.AGENT_PATHS.items():
            assert "display_name" in info
            assert "config_env" in info
            assert "default_path" in info
            assert callable(info["default_path"])


def test_detect_agents_creates_detected_list():
    """Test _detect_agents populates detected_agents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        config = InstallConfig(base_dir=base_dir, dry_run=True)
        installer = UnifiedInstaller(config)
        installer._detect_agents()

        assert len(installer.detected_agents) == 9
        for agent in installer.detected_agents:
            assert isinstance(agent, DetectedAgent)
            assert agent.name in installer.AGENT_PATHS


def test_determine_selected_agents_auto():
    """Test _determine_selected_agents with auto-detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir).resolve()
        # Create a fake home dir with no agent configs
        fake_home = base_dir / "fake_home"
        fake_home.mkdir()

        config = InstallConfig(base_dir=base_dir, dry_run=True)
        installer = UnifiedInstaller(config)

        # Override home for detection
        installer._detect_agents(override_home=fake_home)
        installer._determine_selected_agents()

        # No agents should be selected (none exist in fake home)
        assert installer.selected_agents == []


def test_determine_selected_agents_explicit():
    """Test _determine_selected_agents with explicit agents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        config = InstallConfig(base_dir=base_dir, dry_run=True, agents=["claude-code", "codex"])
        installer = UnifiedInstaller(config)
        installer._detect_agents()
        installer._determine_selected_agents()

        assert installer.selected_agents == ["claude-code", "codex"]


def test_detected_agents_sh_created():
    """Test detected-agents.sh is created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir).resolve()
        # Create a fake home dir with no agent configs
        fake_home = base_dir / "fake_home"
        fake_home.mkdir()

        config = InstallConfig(base_dir=base_dir, dry_run=False, agents=["claude-code"])
        installer = UnifiedInstaller(config)

        # Override home for detection
        installer._detect_agents(override_home=fake_home)
        installer._determine_selected_agents()

        detected_sh = installer.config_dir / "detected-agents.sh"
        assert detected_sh.exists()
        content = detected_sh.read_text()
        assert "AGENTS=(claude-code)" in content


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])