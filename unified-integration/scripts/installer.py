#!/usr/bin/env python3
"""
AgentEnhancements Unified Installer Core — Shared installation logic for all platforms.
Called by setup.sh (Linux/macOS/WSL/Git Bash) and setup.ps1 (Windows PowerShell).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add scripts to path for imports
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from native_integration_v2 import NativeIntegrationV2 as NativeIntegration
from registry import cmd_build
from memory_v2 import MemoryManager
from context_compression import ContextCompressor, CompressionConfig, CompressionMode, load_config


@dataclass
class InstallConfig:
    """Configuration for installation."""
    base_dir: Path
    agents: Optional[List[str]] = None
    dry_run: bool = False
    force: bool = False
    skip_hooks: bool = False
    skip_mcp: bool = False
    skip_memory: bool = False
    skip_compression: bool = False
    skip_skills: bool = False
    verbose: bool = False


@dataclass
class DetectedAgent:
    """Detected agent information."""
    name: str
    display_name: str
    config_path: Path
    exists: bool


class UnifiedInstaller:
    """Core installation logic shared across platforms."""

    # Agent detection paths (cross-platform)
    AGENT_PATHS = {
        "claude-code": {
            "display_name": "Claude Code",
            "config_env": "CLAUDE_CONFIG_DIR",
            "default_path": lambda home: home / ".claude",
        },
        "codex": {
            "display_name": "Codex CLI",
            "config_env": "CODEX_HOME",
            "default_path": lambda home: home / ".codex",
        },
        "opencode": {
            "display_name": "OpenCode 2",
            "config_env": "OPENCODE_CONFIG_DIR",
            "default_path": lambda home: home / ".config" / "opencode",
        },
        "hermes": {
            "display_name": "Hermes",
            "config_env": "HERMES_HOME",
            "default_path": lambda home: home / ".config" / "hermes",
        },
        "cursor": {
            "display_name": "Cursor",
            "config_env": "CURSOR_CONFIG_DIR",
            "default_path": lambda home: home / ".cursor",
        },
        "gemini": {
            "display_name": "Gemini CLI",
            "config_env": "GEMINI_CONFIG_DIR",
            "default_path": lambda home: home / ".gemini",
        },
        "copilot": {
            "display_name": "GitHub Copilot",
            "config_env": "COPILOT_CONFIG_DIR",
            "default_path": lambda home: home / ".config" / "github-copilot",
        },
        "windsurf": {
            "display_name": "Windsurf",
            "config_env": "WINDSURF_CONFIG_DIR",
            "default_path": lambda home: home / ".codeium" / "windsurf",
        },
        "kiro": {
            "display_name": "Kiro",
            "config_env": "KIRO_CONFIG_DIR",
            "default_path": lambda home: home / ".kiro",
        },
    }

    def __init__(self, config: InstallConfig):
        self.config = config
        self.base_dir = config.base_dir.resolve()
        self.ae_root = self.base_dir
        self.scripts_dir = self.base_dir / "unified-integration" / "scripts"
        self.hooks_dir = self.base_dir / "unified-integration" / "hooks"
        self.skills_source = self.base_dir / "skills"
        self.memory_root = self.base_dir / ".agentenhancements" / "memory"
        self.config_dir = self.base_dir / "unified-integration" / "config"
        self.cache_dir = self.base_dir / ".agentenhancements" / "cache"
        self.logs_dir = self.base_dir / ".agentenhancements" / "logs"

        # Runtime config
        self.runtime_config = {
            "base_dir": str(self.ae_root),
            "memory_root": str(self.memory_root),
            "max_skill_cards": 8,
            "compression_budget": 200000,
            "compression_trigger": 0.75,
            "preflight_mode": 0,
        }

        self.detected_agents: List[DetectedAgent] = []
        self.selected_agents: List[str] = []

    def log_info(self, msg: str) -> None:
        print(f"[INFO] {msg}")

    def log_success(self, msg: str) -> None:
        print(f"[SUCCESS] {msg}")

    def log_warn(self, msg: str) -> None:
        print(f"[WARN] {msg}")

    def log_error(self, msg: str) -> None:
        print(f"[ERROR] {msg}", file=sys.stderr)

    def log_verbose(self, msg: str) -> None:
        if self.config.verbose:
            print(f"[DEBUG] {msg}")

    def run(self) -> bool:
        """Run complete installation."""
        self.log_info("AgentEnhancements Unified Installer")
        self.log_info(f"Repo: {self.ae_root}")
        print("")

        try:
            # 1. Prepare directories
            self._prepare_directories()

            # 2. Detect agents
            self._detect_agents()

            # 3. Determine selected agents
            self._determine_selected_agents()

            # 4. Build skill catalog
            if not self.config.skip_skills:
                self._build_catalog()

            # 5. Install native integrations
            if not self.config.skip_hooks:
                self._install_native()

            # 6. Setup memory system
            if not self.config.skip_memory:
                self._setup_memory()

            # 7. Setup compression
            if not self.config.skip_compression:
                self._setup_compression()

            # 8. Setup MCP gateway
            if not self.config.skip_mcp:
                self._setup_mcp()

            # 9. Generate launcher
            self._generate_launcher()

            # 10. Save runtime config
            self._save_config()

            print("\n[PASS] Setup complete!")
            self._print_next_steps()
            return True

        except Exception as e:
            self.log_error(f"Setup failed: {e}")
            if self.config.verbose:
                import traceback
                traceback.print_exc()
            return False

    def _prepare_directories(self) -> None:
        """Prepare all required directories."""
        self.log_info("Preparing directories...")
        dirs = [
            self.memory_root,
            self.config_dir,
            self.hooks_dir,
            self.cache_dir,
            self.logs_dir,
        ]
        for d in dirs:
            if not self.config.dry_run:
                d.mkdir(parents=True, exist_ok=True)
                # Secure permissions on Windows (no-op on Unix)
                try:
                    d.chmod(0o700)
                except OSError:
                    pass
            self.log_verbose(f"  {'[DRY RUN] ' if self.config.dry_run else ''}{d}")

    def _detect_agents(self, override_home: Optional[Path] = None) -> None:
        """Detect which agents are installed."""
        self.log_info("Detecting available AI coding agents...")
        home = override_home or Path.home()

        for agent_name, agent_info in self.AGENT_PATHS.items():
            config_path = None
            env_var = agent_info.get("config_env")
            if env_var and os.environ.get(env_var):
                config_path = Path(os.environ[env_var]).expanduser().resolve()
            else:
                config_path = agent_info["default_path"](home).expanduser().resolve()

            exists = config_path.exists()
            detected = DetectedAgent(
                name=agent_name,
                display_name=agent_info["display_name"],
                config_path=config_path,
                exists=exists
            )
            self.detected_agents.append(detected)

            if exists:
                self.log_success(f"Found: {agent_info['display_name']} ({config_path})")
            elif self.config.verbose:
                self.log_verbose(f"  Not found: {agent_info['display_name']} ({config_path})")

    def _determine_selected_agents(self) -> None:
        """Determine which agents to configure."""
        if self.config.agents:
            # User-specified agents
            self.selected_agents = self.config.agents
            self.log_info(f"Using user-specified agents: {', '.join(self.selected_agents)}")
        else:
            # Auto-detect: use agents that exist
            self.selected_agents = [a.name for a in self.detected_agents if a.exists]
            if self.selected_agents:
                self.log_info(f"Auto-detected agents: {', '.join(self.selected_agents)}")
            else:
                self.log_warn("No AI coding agents detected in PATH. Setup will still configure files for manual use.")

        # Validate selected agents
        valid_agents = set(self.AGENT_PATHS.keys())
        for agent in self.selected_agents:
            if agent not in valid_agents:
                self.log_warn(f"Unknown agent: {agent} (valid: {', '.join(sorted(valid_agents))})")

        # Save detected agents for native integration
        detected_sh = self.config_dir / "detected-agents.sh"
        if not self.config.dry_run:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            agents_array = " ".join(self.selected_agents) if self.selected_agents else ""
            detected_sh.write_text(f"AGENTS=({agents_array})\n")

    def _build_catalog(self) -> None:
        """Build unified skill catalog using ASUS registry cmd_build."""
        self.log_info("Building skill catalog...")
        # ASUS registry uses cmd_build() which reads from all-skills.json
        # (created by setup.sh aggregate_skills) and plugin-catalog/
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "registry", "build"
        ], cwd=self.ae_root, capture_output=True, text=True)
        if result.returncode == 0:
            self.log_success(result.stdout.strip())
        else:
            self.log_warn(f"Registry build warning: {result.stderr.strip()}")

    def _install_native(self) -> None:
        """Install native configurations for agents."""
        self.log_info("Installing native integrations...")

        integration = NativeIntegration(self.ae_root)

        for agent_name in self.selected_agents:
            if agent_name in integration.agents:
                self.log_info(f"  Installing {integration.agents[agent_name].display_name}...")
                integration.install_agent(agent_name, self.config.dry_run)
            else:
                self.log_warn(f"  Unknown agent: {agent_name}")

    def _setup_memory(self) -> None:
        """Initialize memory system."""
        self.log_info("Setting up memory system...")
        if not self.config.dry_run:
            mgr = MemoryManager(self.memory_root)
            stats = mgr.stats()
            self.log_info(f"  Database: {stats['db_path']}")
            self.log_info(f"  Size: {stats['db_size_bytes']} bytes")
        else:
            self.log_verbose(f"  [DRY RUN] Would initialize: {self.memory_root}")

    def _setup_compression(self) -> None:
        """Setup context compression using DELL ContextCompressor."""
        self.log_info("Setting up context compression...")

        # Use the new context_compression module to find headroom
        compressor = ContextCompressor()
        headroom_binary = str(compressor._headroom_path) if compressor._headroom_path else ""

        if headroom_binary:
            self.log_info(f"  Headroom binary found: {headroom_binary}")
        else:
            self.log_warn("  Headroom binary not found - will use Python fallback")
            self.log_info("  To build headroom: cd headroom && cargo build --release")

        # Write compression config
        config = {
            "mode": "auto",
            "budget": self.runtime_config["compression_budget"],
            "trigger": self.runtime_config["compression_trigger"],
            "headroom_binary": headroom_binary,
            "max_input_chars": 50000,
            "preserve_recent": 10,
            "strip_thinking": True,
        }

        config_file = self.config_dir / "compression.yaml"
        if not self.config.dry_run:
            import yaml
            config_file.write_text(yaml.dump(config))
        self.log_info(f"  Config: {config_file}")

    def _setup_mcp(self) -> None:
        """Setup MCP gateway and servers."""
        self.log_info("Setting up MCP gateway...")

        if not self.config.dry_run:
            # Run setup-mcp.sh to prepare MCP runtime
            setup_mcp = self.scripts_dir.parent / "setup-mcp.sh"
            if setup_mcp.exists():
                try:
                    result = subprocess.run(
                        ["bash", str(setup_mcp), "--prepare"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=self.ae_root,
                    )
                    if result.returncode == 0:
                        self.log_success("  MCP runtime prepared")
                    else:
                        self.log_warn(f"  MCP setup warning: {result.stderr.strip()}")
                except Exception as e:
                    self.log_warn(f"  MCP setup failed: {e}")

    def _generate_launcher(self) -> None:
        """Generate launch agent script."""
        self.log_info("Generating launcher...")

        launcher = self.ae_root / "unified-integration" / "launch-agent.sh"
        if not self.config.dry_run:
            # Make executable
            launcher.chmod(0o755)
        self.log_info(f"  Launcher: {launcher}")

    def _save_config(self) -> None:
        """Save runtime configuration."""
        self.log_info("Saving runtime configuration...")

        config_file = self.config_dir / "runtime.json"
        if not self.config.dry_run:
            import json
            config_file.write_text(json.dumps(self.runtime_config, indent=2))
        self.log_info(f"  Config: {config_file}")

    def _print_next_steps(self) -> None:
        """Print next steps for user."""
        print("\nNext steps:")
        print("  1. Restart your AI coding agent (Claude Code, Codex, etc.)")
        print("  2. Run 'registry.py map \"<task>\"' to discover relevant skills")
        print("  3. Check hooks are active via agent's hook inspection (e.g., '/hooks' in Claude Code)")
        if self.selected_agents:
            print(f"  4. Configured agents: {', '.join(self.selected_agents)}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AgentEnhancements Unified Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m installer install                    # Auto-detect and install
  python -m installer install --agents claude-code codex  # Specific agents
  python -m installer install --dry-run          # Preview changes
  python -m installer install --verbose          # Debug output
  python -m installer detect                     # Only detect agents
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Install command
    install_parser = subparsers.add_parser("install", help="Run installation")
    install_parser.add_argument("--agents", nargs="+", help="Specific agents to configure")
    install_parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    install_parser.add_argument("--force", action="store_true", help="Force reinstall")
    install_parser.add_argument("--skip-hooks", action="store_true", help="Skip hook installation")
    install_parser.add_argument("--skip-mcp", action="store_true", help="Skip MCP setup")
    install_parser.add_argument("--skip-memory", action="store_true", help="Skip memory setup")
    install_parser.add_argument("--skip-compression", action="store_true", help="Skip compression setup")
    install_parser.add_argument("--skip-skills", action="store_true", help="Skip skill catalog build")
    install_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    install_parser.add_argument("--base-dir", type=Path, help="Base directory (default: repo root)")

    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect available agents")
    detect_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    detect_parser.add_argument("--base-dir", type=Path, help="Base directory (default: repo root)")

    args = parser.parse_args()

    # Determine base directory
    if args.base_dir:
        base_dir = args.base_dir.resolve()
    else:
        base_dir = Path(__file__).resolve().parent.parent.parent

    if args.command == "detect":
        config = InstallConfig(base_dir=base_dir, verbose=args.verbose)
        installer = UnifiedInstaller(config)
        installer._detect_agents()
        for agent in installer.detected_agents:
            status = "✓" if agent.exists else "✗"
            print(f"  {status} {agent.display_name}: {agent.config_path}")
        return 0

    elif args.command == "install":
        config = InstallConfig(
            base_dir=base_dir,
            agents=args.agents,
            dry_run=args.dry_run,
            force=args.force,
            skip_hooks=args.skip_hooks,
            skip_mcp=args.skip_mcp,
            skip_memory=args.skip_memory,
            skip_compression=args.skip_compression,
            skip_skills=args.skip_skills,
            verbose=args.verbose,
        )
        installer = UnifiedInstaller(config)
        success = installer.run()
        return 0 if success else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())