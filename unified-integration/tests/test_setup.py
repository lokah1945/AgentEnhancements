#!/usr/bin/env python3
"""Tests for setup.py"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from setup import UnifiedSetup


def test_prepare_directories():
    """Test directory preparation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup = UnifiedSetup(Path(tmpdir))
        setup._prepare_directories(dry_run=False)

        assert (Path(tmpdir) / ".agentenhancements" / "memory").exists()
        assert (Path(tmpdir) / ".agentenhancements" / "cache").exists()
        assert (Path(tmpdir) / ".agentenhancements" / "logs").exists()
        assert (Path(tmpdir) / "unified-integration" / "config").exists()
    print("✓ Directory preparation works")


def test_build_catalog():
    """Test catalog building."""
    base_dir = Path(__file__).parent.parent.parent
    setup = UnifiedSetup(base_dir)

    # Just verify it doesn't crash
    setup._build_catalog(dry_run=True)
    print("✓ Catalog building works")


def test_detect_agents():
    """Test agent detection."""
    base_dir = Path(__file__).parent.parent.parent
    setup = UnifiedSetup(base_dir)

    agents = setup._detect_agents()
    # Should return list (may be empty in test env)
    assert isinstance(agents, list)
    print(f"✓ Agent detection: {agents}")


def test_save_config():
    """Test config saving."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup = UnifiedSetup(Path(tmpdir))
        setup._save_config(dry_run=False)

        config_file = Path(tmpdir) / "unified-integration" / "config" / "runtime.json"
        assert config_file.exists()

        config = json.loads(config_file.read_text())
        assert "base_dir" in config
        assert "memory_root" in config
        assert "max_skill_cards" in config
    print("✓ Config saving works")


def test_generate_launcher():
    """Test launcher generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup = UnifiedSetup(Path(tmpdir))
        setup._generate_launcher(dry_run=False)

        launcher = Path(tmpdir) / "unified-integration" / "launch-agent.sh"
        assert launcher.exists()

        content = launcher.read_text()
        assert "claude-code" in content
        assert "codex" in content
        assert "AGENT_ENHANCEMENTS_BASE_DIR" in content
    print("✓ Launcher generation works")


def test_full_setup_dry_run():
    """Test full setup in dry-run mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup = UnifiedSetup(Path(tmpdir))
        # Should not crash
        setup.run(agents=["claude-code"], dry_run=True)
    print("✓ Full setup dry-run works")


if __name__ == "__main__":
    test_prepare_directories()
    test_build_catalog()
    test_detect_agents()
    test_save_config()
    test_generate_launcher()
    test_full_setup_dry_run()
    print("\n✅ All setup tests passed!")