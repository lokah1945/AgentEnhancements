#!/usr/bin/env python3
"""
AgentEnhancements Unified Setup — Complete installation for all supported agents.
Installs skills, native configs, MCP gateway, memory, compression, and hooks.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from native_integration import NativeIntegration
from registry import SkillRegistry


class UnifiedSetup:
    """Complete AgentEnhancements setup."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.ae_root = self.base_dir
        self.scripts_dir = self.base_dir / "unified-integration" / "scripts"
        self.hooks_dir = self.base_dir / "unified-integration" / "hooks"
        self.skills_source = self.base_dir / "skills"
        self.memory_root = self.base_dir / ".agentenhancements" / "memory"
        self.config_dir = self.base_dir / "unified-integration" / "config"

        # Runtime config
        self.config = {
            "base_dir": str(self.ae_root),
            "memory_root": str(self.memory_root),
            "max_skill_cards": 8,
            "compression_budget": 200000,
            "compression_trigger": 0.75,
            "preflight_mode": 0,
        }

    def run(self, agents: Optional[List[str]] = None, dry_run: bool = False) -> bool:
        """Run complete setup."""
        print("🔧 AgentEnhancements Unified Setup")
        print(f"Repo: {self.ae_root}")
        print("")

        # 1. Prepare directories
        self._prepare_directories(dry_run)

        # 2. Build skill catalog
        self._build_catalog(dry_run)

        # 3. Install native integrations
        self._install_native(agents, dry_run)

        # 4. Setup memory system
        self._setup_memory(dry_run)

        # 5. Setup compression
        self._setup_compression(dry_run)

        # 6. Setup MCP gateway
        self._setup_mcp(dry_run)

        # 7. Generate launcher
        self._generate_launcher(dry_run)

        # 8. Save runtime config
        self._save_config(dry_run)

        print("\n✅ Setup complete!")
        self._print_next_steps()
        return True

    def _prepare_directories(self, dry_run: bool):
        """Prepare all required directories."""
        print("📁 Preparing directories...")
        dirs = [
            self.memory_root,
            self.config_dir,
            self.hooks_dir,
            self.ae_root / ".agentenhancements" / "cache",
            self.ae_root / ".agentenhancements" / "logs",
        ]
        for d in dirs:
            if not dry_run:
                d.mkdir(parents=True, exist_ok=True)
            print(f"  {'[DRY RUN] ' if dry_run else ''}{d}")

    def _build_catalog(self, dry_run: bool):
        """Build unified skill catalog."""
        print("\n📋 Building skill catalog...")
        registry = SkillRegistry(self.ae_root)
        catalog = registry.rebuild_catalog()
        stats = catalog["stats"]
        print(f"  Skills: {stats['total_skills']}")
        print(f"  Categories: {len(stats['by_category'])}")
        print(f"  Sources: {stats['by_source']}")

    def _install_native(self, agents: Optional[List[str]], dry_run: bool):
        """Install native configurations for agents."""
        print("\n🤖 Installing native integrations...")

        integration = NativeIntegration(self.ae_root)

        if agents is None:
            # Auto-detect installed agents
            agents = self._detect_agents()
            print(f"  Detected agents: {', '.join(agents)}")

        for agent_name in agents:
            if agent_name in integration.agents:
                print(f"  Installing {integration.agents[agent_name].display_name}...")
                integration.install_agent(agent_name, dry_run)
            else:
                print(f"  ⚠️  Unknown agent: {agent_name}")

    def _detect_agents(self) -> List[str]:
        """Detect which agents are installed."""
        detected = []
        home = Path.home()

        checks = {
            "claude-code": home / ".claude",
            "codex": home / ".codex",
            "opencode": home / ".config" / "opencode",
            "hermes": home / ".config" / "hermes",
            "cursor": home / ".cursor",
            "gemini": home / ".gemini",
            "copilot": home / ".config" / "github-copilot",
            "windsurf": home / ".codeium" / "windsurf",
            "kiro": home / ".kiro",
        }

        for agent, path in checks.items():
            if path.exists():
                detected.append(agent)

        return detected

    def _setup_memory(self, dry_run: bool):
        """Initialize memory system."""
        print("\n💾 Setting up memory system...")
        if not dry_run:
            # Import and initialize
            sys.path.insert(0, str(self.scripts_dir))
            from memory import MemoryManager
            mgr = MemoryManager(self.memory_root)
            stats = mgr.stats()
            print(f"  Database: {stats['db_path']}")
            print(f"  Size: {stats['db_size_bytes']} bytes")
        else:
            print(f"  [DRY RUN] Would initialize: {self.memory_root}")

    def _setup_compression(self, dry_run: bool):
        """Setup context compression."""
        print("\n🗜️  Setting up context compression...")

        # Check for headroom binary
        headroom_paths = [
            self.ae_root / "headroom" / "target" / "release" / "headroom",
            Path(shutil.which("headroom") or ""),
        ]

        headroom_found = False
        for p in headroom_paths:
            if p.exists():
                print(f"  Headroom binary found: {p}")
                headroom_found = True
                break

        if not headroom_found:
            print("  Headroom binary not found - will use Python fallback")
            print("  To build headroom: cd headroom && cargo build --release")

        # Write compression config
        config = {
            "mode": "auto",
            "budget": self.config["compression_budget"],
            "trigger": self.config["compression_trigger"],
            "headroom_binary": str(headroom_paths[0]) if headroom_found else "",
            "max_input_chars": 50000,
            "preserve_recent": 10,
            "strip_thinking": True,
        }

        config_file = self.config_dir / "compression.yaml"
        if not dry_run:
            import yaml
            config_file.write_text(yaml.dump(config))
        print(f"  Config: {config_file}")

    def _setup_mcp(self, dry_run: bool):
        """Setup MCP gateway and servers."""
        print("\n🔌 Setting up MCP gateway...")

        # Check for MCP servers
        mcp_path = self.ae_root / "plugin-catalog" / "mcp-servers.json"
        if mcp_path.exists():
            data = json.loads(mcp_path.read_text())
            servers = data.get("mcp-servers", {})
            available = sum(1 for s in servers.values() if s.get("status") == "available")
            built = sum(1 for s in servers.values() if s.get("status") == "built")
            planned = sum(1 for s in servers.values() if s.get("status") == "planned")
            print(f"  MCP Servers: {available} available, {built} built, {planned} planned")

        # Write gateway config
        gateway_config = {
            "auto_start_priority": 1,
            "health_check_interval": 30,
            "default_timeout": 30,
        }

        config_file = self.config_dir / "gateway.yaml"
        if not dry_run:
            import yaml
            config_file.write_text(yaml.dump(gateway_config))
        print(f"  Gateway config: {config_file}")

    def _generate_launcher(self, dry_run: bool):
        """Generate unified launcher script."""
        print("\n🚀 Generating launcher...")
        integration = NativeIntegration(self.ae_root)
        launcher_path = self.ae_root / "unified-integration" / "launch-agent.sh"
        if not dry_run:
            integration.generate_launcher_script(launcher_path)
        print(f"  Launcher: {launcher_path}")

    def _save_config(self, dry_run: bool):
        """Save runtime configuration."""
        print("\n⚙️  Saving runtime config...")
        config_file = self.config_dir / "runtime.json"
        if not dry_run:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(json.dumps(self.config, indent=2))
        print(f"  Config: {config_file}")

    def _print_next_steps(self):
        """Print next steps for user."""
        print("\n📝 Next steps:")
        print("  1. Restart your AI coding agent to load new hooks/configs")
        print("  2. Test skill discovery:")
        print(f"     python3 {self.scripts_dir}/registry.py map \"typescript refactor\"")
        print("  3. Test memory:")
        print(f"     python3 {self.scripts_dir}/memory.py save test_key test_value")
        print("  4. Test compression:")
        print(f"     python3 {self.scripts_dir}/compression.py compress session.log")
        print("  5. Launch enhanced agent:")
        print(f"     {self.ae_root}/unified-integration/launch-agent.sh claude-code")
        print("")
        print("  Configuration files:")
        print(f"    - Runtime: {self.config_dir}/runtime.json")
        print(f"    - Compression: {self.config_dir}/compression.yaml")
        print(f"    - Gateway: {self.config_dir}/gateway.yaml")
        print(f"    - Memory: {self.memory_root}/memory.db")


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="AgentEnhancements Unified Setup")
    parser.add_argument("command", nargs="?", default="install", choices=["install", "detect", "catalog", "memory", "compression", "mcp", "launcher"])
    parser.add_argument("--agents", nargs="+", help="Specific agents to install")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--base-dir", help="Base directory (default: auto-detect)")

    args = parser.parse_args()

    base_dir = Path(args.base_dir) if args.base_dir else None
    setup = UnifiedSetup(base_dir)

    if args.command == "install":
        setup.run(agents=args.agents, dry_run=args.dry_run)

    elif args.command == "detect":
        agents = setup._detect_agents()
        print("Detected agents:", ", ".join(agents) if agents else "None")

    elif args.command == "catalog":
        registry = SkillRegistry(setup.ae_root)
        catalog = registry.rebuild_catalog()
        print(json.dumps(catalog["stats"], indent=2))

    elif args.command == "memory":
        from memory import MemoryManager
        mgr = MemoryManager(setup.memory_root)
        print(json.dumps(mgr.stats(), indent=2))

    elif args.command == "compression":
        from compression import ContextCompressor, load_config
        config = load_config(setup.config_dir / "compression.yaml")
        compressor = ContextCompressor(config)
        print(json.dumps({
            "mode": config.mode.value,
            "budget": config.budget,
            "headroom_found": compressor._headroom_path is not None,
            "headroom_path": compressor._headroom_path,
        }, indent=2))

    elif args.command == "mcp":
        from gateway import MCPGateway
        gateway = MCPGateway(setup.ae_root)
        print(json.dumps(gateway.get_all_status(), indent=2))

    elif args.command == "launcher":
        integration = NativeIntegration(setup.ae_root)
        integration.generate_launcher_script(setup.ae_root / "unified-integration" / "launch-agent.sh")
        print("Launcher generated")


if __name__ == "__main__":
    main()