#!/usr/bin/env python3
"""
AgentEnhancements Native Integration — Generate native configurations for all supported agents.
Supports: Claude Code, Codex, OpenCode, Hermes, Cursor, Gemini CLI, Copilot, Windsurf, Kiro
"""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    name: str
    display_name: str
    config_dir: str
    config_files: Dict[str, str]  # filename -> content/template
    hooks: Dict[str, List[Dict]]  # hook event -> hook configs
    skills_dir: str
    mcp_config: Dict
    env_vars: Dict[str, str]


class NativeIntegration:
    """
    Generate and install native configurations for all supported AI coding agents.
    """

    def __init__(self, base_dir: Path, ae_config: Optional[Dict] = None):
        self.base_dir = base_dir
        self.ae_config = ae_config or {}
        self.ae_root = base_dir
        self.scripts_dir = base_dir / "unified-integration" / "scripts"
        self.hooks_dir = base_dir / "unified-integration" / "hooks"
        self.skills_source = base_dir / "skills"
        self.memory_root = base_dir / ".agentenhancements" / "memory"

        # Define all supported agents
        self.agents = self._define_agents()

    def _define_agents(self) -> Dict[str, AgentConfig]:
        """Define configurations for all supported agents."""
        runtime_python = sys.executable
        runtime_script = self.scripts_dir / "runtime.py"

        # Common hook configuration
        common_hooks = {
            "SessionStart": [{
                "type": "command",
                "command": f"{runtime_python} {runtime_script} SessionStart",
                "timeout": 5000,
            }],
            "UserPromptSubmit": [{
                "type": "command",
                "command": f"{runtime_python} {runtime_script} UserPromptSubmit",
                "timeout": 10000,
            }],
            "PreToolUse": [{
                "type": "command",
                "command": f"{runtime_python} {runtime_script} PreToolUse",
                "timeout": 2000,
            }],
            "PostToolUse": [{
                "type": "command",
                "command": f"{runtime_python} {runtime_script} PostToolUse",
                "timeout": 2000,
            }],
            "Stop": [{
                "type": "command",
                "command": f"{runtime_python} {runtime_script} Stop",
                "timeout": 5000,
            }],
        }

        agents = {}

        # 1. CLAUDE CODE
        agents["claude-code"] = AgentConfig(
            name="claude-code",
            display_name="Claude Code",
            config_dir="~/.claude",
            config_files={
                "settings.json": self._claude_settings_template(),
                "CLAUDE.md": self._claude_md_template(),
            },
            hooks=common_hooks,
            skills_dir="~/.claude/skills",
            mcp_config={"type": "gateway", "config": "~/.claude/mcp.json"},
            env_vars={
                "AGENT_ENHANCEMENTS_BASE_DIR": str(self.ae_root),
                "AGENT_MEMORY_ROOT": str(self.memory_root),
                "AE_MAX_SKILL_CARDS": "8",
            }
        )

        # 2. CODEX
        agents["codex"] = AgentConfig(
            name="codex",
            display_name="Codex CLI",
            config_dir="~/.codex",
            config_files={
                "AGENTS.md": self._codex_agents_md_template(),
                "hooks.json": self._codex_hooks_template(),
                "config.toml": self._codex_config_template(),
            },
            hooks=common_hooks,
            skills_dir="~/.codex/skills",
            mcp_config={"type": "gateway", "config": "~/.codex/mcp.json"},
            env_vars={
                "AGENT_ENHANCEMENTS_BASE_DIR": str(self.ae_root),
                "AGENT_MEMORY_ROOT": str(self.memory_root),
                "AE_MAX_SKILL_CARDS": "8",
            }
        )

        # 3. OPENCODE
        agents["opencode"] = AgentConfig(
            name="opencode",
            display_name="OpenCode 2",
            config_dir="~/.config/opencode",
            config_files={
                "opencode.jsonc": self._opencode_config_template(),
                "AGENTS.md": self._opencode_agents_md_template(),
            },
            hooks=common_hooks,
            skills_dir="~/.config/opencode/skills",
            mcp_config={"type": "native", "plugin": "opencode-plugin"},
            env_vars={
                "AGENT_ENHANCEMENTS_BASE_DIR": str(self.ae_root),
                "AGENT_MEMORY_ROOT": str(self.memory_root),
                "AE_MAX_SKILL_CARDS": "8",
            }
        )

        # 4. HERMES
        agents["hermes"] = AgentConfig(
            name="hermes",
            display_name="Hermes",
            config_dir="~/.config/hermes",
            config_files={
                "config.yaml": self._hermes_config_template(),
                "SOUL.md": self._hermes_soul_template(),
            },
            hooks={
                "pre_llm_call": [{
                    "type": "command",
                    "command": f"{runtime_python} {runtime_script} UserPromptSubmit",
                    "timeout": 10000,
                }],
                "post_llm_call": [{
                    "type": "command",
                    "command": f"{runtime_python} {runtime_script} PostToolUse",
                    "timeout": 2000,
                }],
                "post_tool_call": [{
                    "type": "command",
                    "command": f"{runtime_python} {runtime_script} PostToolUse",
                    "timeout": 2000,
                }],
            },
            skills_dir="~/.config/hermes/skills",
            mcp_config={"type": "native"},
            env_vars={
                "AGENT_ENHANCEMENTS_BASE_DIR": str(self.ae_root),
                "AGENT_MEMORY_ROOT": str(self.memory_root),
            }
        )

        # 5. CURSOR
        agents["cursor"] = AgentConfig(
            name="cursor",
            display_name="Cursor",
            config_dir="~/.cursor/rules",
            config_files={
                "agent-enhancements.mdc": self._cursor_main_rule_template(),
            },
            hooks={},  # Cursor uses rules, not hooks
            skills_dir="~/.cursor/rules/agent-enhancements-skills",
            mcp_config={},
            env_vars={}
        )

        # 6. GEMINI CLI
        agents["gemini"] = AgentConfig(
            name="gemini",
            display_name="Gemini CLI",
            config_dir="~/.gemini",
            config_files={
                "GEMINI.md": self._gemini_md_template(),
                "config.yaml": self._gemini_config_template(),
            },
            hooks={},
            skills_dir="",
            mcp_config={},
            env_vars={
                "AGENT_ENHANCEMENTS_BASE_DIR": str(self.ae_root),
            }
        )

        # 7. GITHUB COPILOT
        agents["copilot"] = AgentConfig(
            name="copilot",
            display_name="GitHub Copilot CLI",
            config_dir="~/.config/github-copilot",
            config_files={
                "config.yaml": self._copilot_config_template(),
            },
            hooks={},
            skills_dir="",
            mcp_config={},
            env_vars={}
        )

        # 8. WINDSURF
        agents["windsurf"] = AgentConfig(
            name="windsurf",
            display_name="Windsurf",
            config_dir="~/.codeium/windsurf/rules",
            config_files={
                "agent-enhancements.md": self._windsurf_rule_template(),
            },
            hooks={},
            skills_dir="",
            mcp_config={},
            env_vars={}
        )

        # 9. KIRO
        agents["kiro"] = AgentConfig(
            name="kiro",
            display_name="Kiro",
            config_dir="~/.kiro",
            config_files={
                "config.yaml": self._kiro_config_template(),
            },
            hooks={},
            skills_dir="",
            mcp_config={},
            env_vars={}
        )

        return agents

    # =========================================================================
    # TEMPLATE METHODS
    # =========================================================================
    def _claude_settings_template(self) -> str:
        return json.dumps({
            "hooks": {
                "SessionStart": [
                    {"type": "command", "command": f"{sys.executable} {self.scripts_dir}/runtime.py SessionStart", "timeout": 5000}
                ],
                "UserPromptSubmit": [
                    {"type": "command", "command": f"{sys.executable} {self.scripts_dir}/runtime.py UserPromptSubmit", "timeout": 10000}
                ],
                "PreToolUse": [
                    {"type": "command", "command": f"{sys.executable} {self.scripts_dir}/runtime.py PreToolUse", "timeout": 2000}
                ],
                "PostToolUse": [
                    {"type": "command", "command": f"{sys.executable} {self.scripts_dir}/runtime.py PostToolUse", "timeout": 2000}
                ],
                "Stop": [
                    {"type": "command", "command": f"{sys.executable} {self.scripts_dir}/runtime.py Stop", "timeout": 5000}
                ]
            },
            "env": {
                "AGENT_ENHANCEMENTS_BASE_DIR": str(self.ae_root),
                "AGENT_MEMORY_ROOT": str(self.memory_root),
                "AE_MAX_SKILL_CARDS": "8"
            }
        }, indent=2)

    def _claude_md_template(self) -> str:
        return f"""# AgentEnhancements — Claude Code Integration

This file is managed by AgentEnhancements. Do not edit directly.

## Configuration
- **AE Root**: {self.ae_root}
- **Memory**: {self.memory_root}
- **Skills**: ~/.claude/skills/

## Available Commands
- `registry.py map "<task>"` — Find relevant skills
- `memory.py save/load/list` — Cross-session memory
- `compression.py compress` — Context compression

## Hook Events
All lifecycle events (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop) are handled automatically.
"""

    def _codex_agents_md_template(self) -> str:
        return f"""# AgentEnhancements — Codex Integration

Managed by AgentEnhancements. AE Root: {self.ae_root}

## Skills
Installed to ~/.codex/skills/

## Hooks
See hooks.json for lifecycle hook configuration.
"""

    def _codex_hooks_template(self) -> str:
        return json.dumps({
            "hooks": {
                "user_prompt_submit": [
                    {"command": f"{sys.executable} {self.scripts_dir}/runtime.py UserPromptSubmit", "timeout": 10000}
                ],
                "pre_tool_use": [
                    {"command": f"{sys.executable} {self.scripts_dir}/runtime.py PreToolUse", "timeout": 2000}
                ],
                "post_tool_use": [
                    {"command": f"{sys.executable} {self.scripts_dir}/runtime.py PostToolUse", "timeout": 2000}
                ],
                "session_start": [
                    {"command": f"{sys.executable} {self.scripts_dir}/runtime.py SessionStart", "timeout": 5000}
                ],
                "session_end": [
                    {"command": f"{sys.executable} {self.scripts_dir}/runtime.py Stop", "timeout": 5000}
                ]
            }
        }, indent=2)

    def _codex_config_template(self) -> str:
        return f"""# Codex Configuration for AgentEnhancements
[agent_enhancements]
base_dir = "{self.ae_root}"
memory_root = "{self.memory_root}"
max_skill_cards = 8
"""

    def _opencode_config_template(self) -> str:
        return json.dumps({
            "$schema": "https://opencode.ai/config.json",
            "plugins": [
                {"name": "agent-enhancements", "path": str(self.ae_root / "unified-integration" / "opencode-plugin")}
            ],
            "mcp": {
                "servers": {
                    "ae-gateway": {
                        "command": [sys.executable, str(self.scripts_dir / "gateway.py"), "run-builtin", "--builtin", "filesystem"]
                    }
                }
            },
            "env": {
                "AGENT_ENHANCEMENTS_BASE_DIR": str(self.ae_root),
                "AGENT_MEMORY_ROOT": str(self.memory_root)
            }
        }, indent=2)

    def _opencode_agents_md_template(self) -> str:
        return f"""# AgentEnhancements — OpenCode Integration

Managed by AgentEnhancements. AE Root: {self.ae_root}

## Plugin
Loaded via opencode.jsonc plugin system.

## Skills
Available via native skill discovery in ~/.config/opencode/skills/
"""

    def _hermes_config_template(self) -> str:
        return f"""# Hermes Configuration for AgentEnhancements
profile: agent-enhancements
plugins:
  - agent-enhancements
env:
  AGENT_ENHANCEMENTS_BASE_DIR: "{self.ae_root}"
  AGENT_MEMORY_ROOT: "{self.memory_root}"
"""

    def _hermes_soul_template(self) -> str:
        return f"""# AgentEnhancements — Hermes SOUL

This profile integrates AgentEnhancements capabilities.

AE Root: {self.ae_root}
Memory: {self.memory_root}

## Capabilities
- Skill discovery via registry
- Cross-session memory
- MCP gateway access
"""

    def _cursor_main_rule_template(self) -> str:
        return """---
description: AgentEnhancements — Centralized system prompt (Karpathy + Anthropic patterns)
globs: ["**/*"]
alwaysApply: true
---
# AgentEnhancements — Centralized System Prompt

This rule loads all AgentEnhancements skills. Individual skills are in `.cursor/rules/agent-enhancements-*.mdc`.

See `skills/**/SKILL.md` for full skill specifications.

## Core Principles
1. **First principles before code** — State input → output → function in 1-2 sentences
2. **Minimal by default** — Functions ≤30 lines, no abstraction until 3× duplication
3. **Skill-aware routing** — Load matching skill spec before acting on file formats/tasks
4. **Verify by execution** — Run code, show output, fail fast on missing prerequisites
5. **No-bullshit review** — Delete over refactor; praise shorter, faster, more correct code

## Skill Discovery
To discover skills by keyword:
```bash
python3 unified-integration/scripts/registry.py map "<task description>"
```
"""

    def _gemini_md_template(self) -> str:
        return f"""# AgentEnhancements — Gemini CLI Integration

Managed by AgentEnhancements. AE Root: {self.ae_root}

## Configuration
This file provides reference for Gemini CLI to discover AgentEnhancements capabilities.

## Skills
Use the registry to find relevant skills:
```bash
python3 unified-integration/scripts/registry.py map "<task>"
```

## Memory
Cross-session memory available via:
```bash
python3 unified-integration/scripts/memory.py save/load/list
```
"""

    def _gemini_config_template(self) -> str:
        return f"""# Gemini CLI Config for AgentEnhancements
agent_enhancements:
  base_dir: "{self.ae_root}"
  memory_root: "{self.memory_root}"
"""

    def _copilot_config_template(self) -> str:
        return f"""# GitHub Copilot Config for AgentEnhancements
agent_enhancements:
  base_dir: "{self.ae_root}"
  # Reference only - use via launcher
"""

    def _windsurf_rule_template(self) -> str:
        return f"""# AgentEnhancements — Windsurf Rule

Managed by AgentEnhancements. AE Root: {self.ae_root}

## Capabilities
- Skill catalog via registry.py
- Cross-session memory via memory.py
- Context compression via compression.py

## Usage
```bash
python3 unified-integration/scripts/registry.py map "<task>"
```
"""

    def _kiro_config_template(self) -> str:
        return f"""# Kiro Config for AgentEnhancements
agent_enhancements:
  base_dir: "{self.ae_root}"
  # Reference only - use via launcher
"""

    # =========================================================================
    # INSTALLATION
    # =========================================================================
    def install_agent(self, agent_name: str, dry_run: bool = False) -> bool:
        """Install configuration for a specific agent."""
        agent = self.agents.get(agent_name)
        if not agent:
            print(f"Unknown agent: {agent_name}")
            return False

        config_dir = Path(os.path.expanduser(agent.config_dir))
        if not dry_run:
            config_dir.mkdir(parents=True, exist_ok=True)

        # Write config files
        for filename, content in agent.config_files.items():
            filepath = config_dir / filename
            if not dry_run:
                # Backup existing if different
                if filepath.exists():
                    existing = filepath.read_text()
                    if existing != content:
                        backup = filepath.with_suffix(filepath.suffix + ".bak")
                        shutil.copy2(filepath, backup)
                filepath.write_text(content)
            print(f"  {'[DRY RUN] ' if dry_run else ''}Writing {filepath}")

        # Install skills
        if agent.skills_dir:
            skills_dir = Path(os.path.expanduser(agent.skills_dir))
            self._install_skills(skills_dir, dry_run)

        # Set environment variables (print for user to add to shell)
        for key, value in agent.env_vars.items():
            print(f"  Export: {key}={value}")

        return True

    def _install_skills(self, target_dir: Path, dry_run: bool = False):
        """Install skills to target directory."""
        if not self.skills_source.exists():
            return

        target_dir.mkdir(parents=True, exist_ok=True)

        for skill_file in sorted(self.skills_source.rglob("SKILL.md")):
            rel = skill_file.relative_to(self.skills_source)
            slug = rel.parts[-2]  # parent directory
            target = target_dir / slug / "SKILL.md"

            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                # Only write if different (idempotent)
                if target.exists():
                    existing = target.read_text()
                    new_content = skill_file.read_text()
                    if existing == new_content:
                        continue
                shutil.copy2(skill_file, target)
            print(f"  {'[DRY RUN] ' if dry_run else ''}Skill: {slug}")

    def install_all(self, dry_run: bool = False) -> Dict[str, bool]:
        """Install configurations for all agents."""
        results = {}
        for name in self.agents:
            print(f"\nInstalling {self.agents[name].display_name}...")
            results[name] = self.install_agent(name, dry_run)
        return results

    def generate_launcher_script(self, output_path: Path) -> bool:
        """Generate unified launcher script."""
        launcher = f"""#!/usr/bin/env bash
# AgentEnhancements Unified Launcher
# Generated by native_integration.py

AE_ROOT="{self.ae_root}"
export AGENT_ENHANCEMENTS_BASE_DIR="$AE_ROOT"
export AGENT_MEMORY_ROOT="$AE_ROOT/.agentenhancements/memory"
export AE_MAX_SKILL_CARDS=8

case "$1" in
    claude|claude-code)
        shift
        exec claude "$@"
        ;;
    codex)
        shift
        exec codex "$@"
        ;;
    opencode)
        shift
        exec opencode "$@"
        ;;
    hermes)
        shift
        exec hermes "$@"
        ;;
    cursor)
        shift
        exec cursor "$@"
        ;;
    gemini)
        shift
        exec gemini "$@"
        ;;
    copilot)
        shift
        exec gh copilot "$@"
        ;;
    windsurf)
        shift
        exec windsurf "$@"
        ;;
    kiro)
        shift
        exec kiro "$@"
        ;;
    *)
        echo "Usage: $0 <agent> [args...]"
        echo "Agents: claude-code, codex, opencode, hermes, cursor, gemini, copilot, windsurf, kiro"
        exit 1
        ;;
esac
"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(launcher)
        try:
            output_path.chmod(0o755)
        except Exception:
            pass  # chmod may not work on Windows
        return True

    def get_agent_info(self, agent_name: str) -> Optional[Dict]:
        """Get agent configuration info."""
        agent = self.agents.get(agent_name)
        if not agent:
            return None
        return {
            "name": agent.name,
            "display_name": agent.display_name,
            "config_dir": agent.config_dir,
            "config_files": list(agent.config_files.keys()),
            "hooks": list(agent.hooks.keys()),
            "skills_dir": agent.skills_dir,
            "has_mcp": bool(agent.mcp_config),
            "env_vars": list(agent.env_vars.keys()),
        }

    def list_agents(self) -> List[Dict]:
        """List all supported agents."""
        return [self.get_agent_info(name) for name in self.agents]


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Native Integration CLI")
    parser.add_argument("command", choices=["install", "install-all", "list", "info", "generate-launcher"])
    parser.add_argument("agent", nargs="?", help="Agent name")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", "-o", help="Output path for launcher")

    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    integration = NativeIntegration(base_dir)

    if args.command == "list":
        for info in integration.list_agents():
            print(f"{info['name']}: {info['display_name']}")
            print(f"  Config: {info['config_dir']}")
            print(f"  Files: {', '.join(info['config_files'])}")
            print(f"  Hooks: {', '.join(info['hooks']) if info['hooks'] else 'None (rules-based)'}")
            print(f"  Skills: {info['skills_dir'] or 'N/A'}")
            print(f"  MCP: {'Yes' if info['has_mcp'] else 'No'}")
            print()

    elif args.command == "info":
        if not args.agent:
            parser.error("Agent name required")
        info = integration.get_agent_info(args.agent)
        if info:
            print(json.dumps(info, indent=2))
        else:
            print(f"Unknown agent: {args.agent}")

    elif args.command == "install":
        if not args.agent:
            parser.error("Agent name required")
        integration.install_agent(args.agent, args.dry_run)

    elif args.command == "install-all":
        integration.install_all(args.dry_run)

    elif args.command == "generate-launcher":
        output = Path(args.output) if args.output else base_dir / "unified-integration" / "launch-agent.sh"
        integration.generate_launcher_script(output)
        print(f"Launcher generated: {output}")


if __name__ == "__main__":
    main()