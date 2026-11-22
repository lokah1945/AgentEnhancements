#!/usr/bin/env python3
"""
AgentEnhancements Native Integration v2 — Generate native configurations for all supported agents.
Supports: Claude Code, Codex, OpenCode, Hermes, Cursor, Gemini CLI, Copilot, Windsurf, Kiro
Ported from DELL branch with ASUS merge strategy (preserve user config).
"""

import json
import os
import shutil
import sys
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

try:
    import tomlkit
except ImportError:
    tomlkit = None


@dataclass
class AgentConfig:
    """Configuration for a single agent."""
    name: str
    display_name: str
    config_dir: str
    config_files: Dict[str, str]  # filename -> content/template
    hooks: Dict[str, List[Dict]]
    skills_dir: str
    mcp_config: Dict
    env_vars: Dict[str, str]


class NativeIntegrationV2:
    """
    Generate and install native configurations for all supported AI coding agents.
    Uses ASUS merge strategy: preserves user hooks, MCP servers, credentials.
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

        # Common hook configuration - single entrypoint per ASUS
        common_hooks = {
            "SessionStart": [{
                "type": "command",
                "command": self._make_hook_command("SessionStart"),
                "timeout": 5000,
            }],
            "UserPromptSubmit": [{
                "type": "command",
                "command": self._make_hook_command("UserPromptSubmit"),
                "timeout": 10000,
            }],
            "PreToolUse": [{
                "type": "command",
                "command": self._make_hook_command("PreToolUse"),
                "timeout": 2000,
            }],
            "PostToolUse": [{
                "type": "command",
                "command": self._make_hook_command("PostToolUse"),
                "timeout": 2000,
            }],
            "Stop": [{
                "type": "command",
                "command": self._make_hook_command("Stop"),
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
                "settings.json": "",  # Will be merged
                "CLAUDE.md": self._claude_md_template(),
            },
            hooks=common_hooks,
            skills_dir="~/.claude/skills",
            mcp_config={"type": "gateway", "config": "~/.claude.json"},
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
                "hooks.json": "",  # Will be merged
                "config.toml": "",  # Will be merged
            },
            hooks=common_hooks,
            skills_dir="~/.codex/skills",
            mcp_config={"type": "gateway", "config": "~/.codex/config.toml"},
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
                    "command": self._make_hook_command("UserPromptSubmit"),
                    "timeout": 10000,
                }],
                "post_llm_call": [{
                    "type": "command",
                    "command": self._make_hook_command("PostToolUse"),
                    "timeout": 2000,
                }],
                "post_tool_call": [{
                    "type": "command",
                    "command": self._make_hook_command("PostToolUse"),
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
                "AGENT_MEMORY_ROOT": str(self.memory_root),
            }
        )

        # 7. COPILOT
        agents["copilot"] = AgentConfig(
            name="copilot",
            display_name="GitHub Copilot",
            config_dir="~/.config/github-copilot",
            config_files={
                "AGENTS.md": self._copilot_agents_md_template(),
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
            config_dir="~/.codeium/windsurf",
            config_files={
                "AGENTS.md": self._windsurf_agents_md_template(),
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
                "AGENTS.md": self._kiro_agents_md_template(),
            },
            hooks={},
            skills_dir="",
            mcp_config={},
            env_vars={}
        )

        return agents

    def _make_hook_command(self, event: str) -> str:
        """Create hook command with proper environment and Python resolution."""
        # Use shlex.join equivalent for safety (ASUS approach)
        runtime_python = sys.executable
        runtime_script = self.scripts_dir / "runtime.py"

        # Build environment variables to pass
        env_vars = {
            "AGENT_ENHANCEMENTS_BASE_DIR": str(self.ae_root),
            "AGENT_MEMORY_ROOT": str(self.memory_root),
            "AE_MAX_SKILL_CARDS": "8",
        }

        # Add any AE-specific env vars from current environment
        for key in ["AGENT_ENHANCEMENTS_API_FILE", "AE_FFMPEG_ALLOWED_ROOTS"]:
            if os.environ.get(key):
                env_vars[key] = os.environ[key]

        env_prefix = " ".join(f'{k}={shlex.quote(v)}' for k, v in env_vars.items())
        return f"{env_prefix} {shlex.quote(runtime_python)} {shlex.quote(str(runtime_script))} {event}"

    def install_agent(self, agent_name: str, dry_run: bool = False) -> bool:
        """Install configuration for a specific agent."""
        if agent_name not in self.agents:
            print(f"[WARN] Unknown agent: {agent_name}")
            return False

        agent = self.agents[agent_name]
        print(f"  Installing {agent.display_name}...")

        try:
            if agent_name == "claude-code":
                return self._install_claude_code(agent, dry_run)
            elif agent_name == "codex":
                return self._install_codex(agent, dry_run)
            elif agent_name == "opencode":
                return self._install_opencode(agent, dry_run)
            elif agent_name == "hermes":
                return self._install_hermes(agent, dry_run)
            elif agent_name in ("cursor", "gemini", "copilot", "windsurf", "kiro"):
                return self._install_reference_agent(agent, dry_run)
            else:
                print(f"  [WARN] No installer for agent: {agent_name}")
                return False
        except Exception as e:
            print(f"  [ERROR] Failed to install {agent.display_name}: {e}")
            if not dry_run:
                import traceback
                traceback.print_exc()
            return False

    def _install_claude_code(self, agent: AgentConfig, dry_run: bool) -> bool:
        """Install Claude Code configuration using ASUS merge strategy."""
        home = Path.home()
        config_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude"))

        # 1. Merge hooks into settings.json (ASUS merge_hooks strategy)
        settings_path = config_dir / "settings.json"
        if not dry_run:
            self._merge_claude_hooks(settings_path, "claude-code")

        # 2. Merge MCP servers into ~/.claude.json (ASUS merge_servers strategy)
        claude_json = home / ".claude.json"
        if os.environ.get("CLAUDE_CONFIG_DIR"):
            claude_json = config_dir / ".claude.json"
        if not dry_run:
            self._merge_claude_mcp(claude_json)

        # 3. Write CLAUDE.md
        claude_md = config_dir / "CLAUDE.md"
        if not dry_run:
            claude_md.write_text(agent.config_files["CLAUDE.md"])

        # 4. Link skills
        if not dry_run:
            self._link_skills(agent.skills_dir, "claude-code")

        print(f"    ✓ {agent.display_name} configured")
        return True

    def _merge_claude_hooks(self, settings_path: Path, agent: str) -> None:
        """Merge AE hooks into settings.json preserving user hooks (ASUS merge_hooks)."""
        from native_config import managed_integration_path, read_json, write_json

        def own_hook(handler: dict) -> bool:
            command = str(handler.get("command", ""))
            return "unified-integration/" in command and any(
                x in command for x in ["scripts/runtime.py", "-memory-hook.py"]
            )

        doc = read_json(settings_path)
        hooks = doc.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = {}
            doc["hooks"] = hooks

        for event, groups in list(hooks.items()):
            retained = []
            for group in groups:
                handlers = [h for h in group.get("hooks", []) if not own_hook(h)]
                if handlers:
                    retained.append({**group, "hooks": handlers})
            hooks[event] = retained

        # Add AE hooks for all events
        from project_paths import environment
        variables = environment()
        for name in ('AGENT_ENHANCEMENTS_API_FILE',):
            if os.environ.get(name):
                variables[name] = os.environ[name]

        runtime_python = sys.executable
        runtime_script = self.scripts_dir / "runtime.py"
        command = shlex.join(['env', *[f'{k}={v}' for k, v in variables.items()],
                              runtime_python, str(runtime_script), agent])

        EVENTS = ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop")
        for event in EVENTS:
            hooks.setdefault(event, []).append({
                "hooks": [{
                    "type": "command",
                    "command": command,
                    "timeout": 10,
                }]
            })

        write_json(settings_path, doc)

    def _merge_claude_mcp(self, claude_json: Path) -> None:
        """Merge AE MCP servers into ~/.claude.json preserving user servers (ASUS merge_servers)."""
        from native_config import managed_integration_path, read_json, write_json
        from api_config import BUILTINS, initialize

        initialize()
        template = json.loads((self.scripts_dir.parent / "mcp-servers/mcp.json.example").read_text())[
            "mcpServers"
        ]
        from project_paths import environment
        template['agent-enhancements'].setdefault('env', {}).update(environment())
        for name in ("AGENT_ENHANCEMENTS_API_FILE", "AGENT_MEMORY_ROOT", "AE_FFMPEG_ALLOWED_ROOTS"):
            if os.environ.get(name):
                template["agent-enhancements"].setdefault("env", {})[name] = os.environ[name]

        block = {
            name: {
                **cfg,
                "command": sys.executable,
                "args": [
                    arg.replace("PLACEHOLDER_REPO_ROOT", str(self.ae_root)) for arg in cfg["args"]
                ],
            }
            for name, cfg in template.items()
        }

        doc = read_json(claude_json)
        existing = doc.setdefault("mcpServers", {})

        # Retire only our previous direct entries
        for name in BUILTINS:
            old = existing.get(name)
            if isinstance(old, dict):
                command = old.get("args", old.get("command", []))
                if isinstance(command, list) and any(
                    managed_integration_path(arg, "mcp-servers", "gateway.py")
                    for arg in command
                ):
                    del existing[name]

        for name, cfg in block.items():
            old = existing.get(name)
            if old is not None and old != cfg:
                old_args = old.get("args", old.get("command", []))
                if not isinstance(old_args, list) or not any(
                    managed_integration_path(arg, "mcp-servers", "gateway.py")
                    for arg in old_args
                ):
                    print(f"[native] preserving user server: {name}", file=sys.stderr)
                    continue
            merged = {**(old or {}), **cfg}
            for field in ("disabled", "codemode"):
                if old and field in old:
                    merged[field] = old[field]
            for field in ("env", "environment"):
                if field in cfg and old and isinstance(old.get(field), dict):
                    merged[field] = {
                        key: value for key, value in {**old[field], **cfg[field]}.items()
                        if key not in {"AGENT_ENHANCEMENTS_MODEL_FILE"}
                    }
            existing[name] = merged

        write_json(claude_json, doc)

    def _install_codex(self, agent: AgentConfig, dry_run: bool) -> bool:
        """Install Codex configuration."""
        home = Path.home()
        config_dir = Path(os.environ.get("CODEX_HOME", home / ".codex"))

        if not dry_run:
            config_dir.mkdir(parents=True, exist_ok=True)

            # Merge hooks into hooks.json
            hooks_path = config_dir / "hooks.json"
            self._merge_codex_hooks(hooks_path, "codex")

            # Merge MCP into config.toml
            config_path = config_dir / "config.toml"
            self._merge_codex_mcp(config_path)

            # Write AGENTS.md
            agents_md = config_dir / "AGENTS.md"
            agents_md.write_text(agent.config_files["AGENTS.md"])

            # Link skills
            self._link_skills(agent.skills_dir, "codex")

        print(f"    ✓ {agent.display_name} configured")
        return True

    def _merge_codex_hooks(self, hooks_path: Path, agent: str) -> None:
        """Merge AE hooks into Codex hooks.json."""
        from native_config import read_json, write_json

        def own_hook(handler: dict) -> bool:
            command = str(handler.get("command", ""))
            return "unified-integration/" in command and "runtime.py" in command

        doc = read_json(hooks_path)
        hooks = doc.setdefault("hooks", {})
        if not isinstance(hooks, dict):
            hooks = {}
            doc["hooks"] = hooks

        for event, groups in list(hooks.items()):
            retained = []
            for group in groups:
                handlers = [h for h in group.get("hooks", []) if not own_hook(h)]
                if handlers:
                    retained.append({**group, "hooks": handlers})
            hooks[event] = retained

        runtime_python = sys.executable
        runtime_script = self.scripts_dir / "runtime.py"
        command = shlex.join(['env',
                              f'AGENT_ENHANCEMENTS_BASE_DIR={self.ae_root}',
                              f'AGENT_MEMORY_ROOT={self.memory_root}',
                              f'AE_MAX_SKILL_CARDS=8',
                              runtime_python, str(runtime_script), agent])

        EVENTS = ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop")
        for event in EVENTS:
            hooks.setdefault(event, []).append({
                "hooks": [{
                    "type": "command",
                    "command": command,
                    "timeout": 10000,
                }]
            })

        write_json(hooks_path, doc)

    def _merge_codex_mcp(self, config_path: Path) -> None:
        """Merge AE MCP servers into Codex config.toml."""
        if tomlkit is None:
            return

        from api_config import initialize
        from project_paths import environment

        initialize()
        template = json.loads((self.scripts_dir.parent / "mcp-servers/mcp.json.example").read_text())[
            "mcpServers"
        ]
        template['agent-enhancements'].setdefault('env', {}).update(environment())

        block = {
            name: {
                **cfg,
                "command": sys.executable,
                "args": [
                    arg.replace("PLACEHOLDER_REPO_ROOT", str(self.ae_root)) for arg in cfg["args"]
                ],
            }
            for name, cfg in template.items()
        }

        doc = tomlkit.parse(config_path.read_text()) if config_path.exists() else tomlkit.document()
        mcp_servers = doc.setdefault("mcp_servers", tomlkit.table())

        for name, cfg in block.items():
            mcp_servers[name] = cfg

        config_path.write_text(tomlkit.dumps(doc))

    def _install_opencode(self, agent: AgentConfig, dry_run: bool) -> bool:
        """Install OpenCode configuration."""
        home = Path.home()
        config_dir = Path(os.environ.get("OPENCODE_CONFIG_DIR", home / ".config" / "opencode"))

        if not dry_run:
            config_dir.mkdir(parents=True, exist_ok=True)

            # Write opencode.jsonc
            opencode_jsonc = config_dir / "opencode.jsonc"
            opencode_jsonc.write_text(agent.config_files["opencode.jsonc"])

            # Write AGENTS.md
            agents_md = config_dir / "AGENTS.md"
            agents_md.write_text(agent.config_files["AGENTS.md"])

            # Link skills
            self._link_skills(agent.skills_dir, "opencode")

        print(f"    ✓ {agent.display_name} configured")
        return True

    def _install_hermes(self, agent: AgentConfig, dry_run: bool) -> bool:
        """Install Hermes configuration."""
        home = Path.home()
        config_dir = Path(os.environ.get("HERMES_HOME", home / ".config" / "hermes"))

        if not dry_run:
            config_dir.mkdir(parents=True, exist_ok=True)

            # Write config.yaml
            config_yaml = config_dir / "config.yaml"
            config_yaml.write_text(agent.config_files["config.yaml"])

            # Write SOUL.md
            soul_md = config_dir / "SOUL.md"
            soul_md.write_text(agent.config_files["SOUL.md"])

            # Link skills
            self._link_skills(agent.skills_dir, "hermes")

        print(f"    ✓ {agent.display_name} configured")
        return True

    def _install_reference_agent(self, agent: AgentConfig, dry_run: bool) -> bool:
        """Install reference configuration for agents without native hook support."""
        home = Path.home()
        config_dir = Path(os.path.expanduser(agent.config_dir))

        if not dry_run:
            config_dir.mkdir(parents=True, exist_ok=True)

            for filename, content in agent.config_files.items():
                if content:
                    (config_dir / filename).write_text(content)

        print(f"    ✓ {agent.display_name} reference config written")
        return True

    def _link_skills(self, skills_dir: str, agent: str) -> None:
        """Link skills directory for agent native discovery."""
        source = self.skills_source
        if not source.exists():
            return

        target = Path(os.path.expanduser(skills_dir))
        target.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing link/directory
        if target.exists() or target.is_symlink():
            if target.is_symlink():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        # Create symlink (or junction on Windows without admin)
        try:
            target.symlink_to(source)
        except OSError:
            # Fallback: copy on Windows without symlink privilege
            shutil.copytree(source, target, dirs_exist_ok=True)

    # =========================================================================
    # CONFIG TEMPLATES
    # =========================================================================

    def _claude_md_template(self) -> str:
        return f"""# AgentEnhancements Configuration for Claude Code

This file is managed by AgentEnhancements. Do not edit directly.

## Installed Enhancements

- **Skills Registry**: {self.ae_root}/skills (linked to ~/.claude/skills/)
- **Memory**: {self.memory_root}
- **MCP Gateway**: agent-enhancements (via ~/.claude.json)
- **Context Compression**: headroom (Python fallback available)
- **Adaptive Preflight**: Mode 0 (legacy), Mode 2 (custom endpoint)

## Usage

Skills are auto-discovered via `registry.py map "<task>"` and injected as
candidate cards on UserPromptSubmit. Use `/hooks` to verify hook installation.
"""

    def _codex_agents_md_template(self) -> str:
        return f"""# AgentEnhancements for Codex

Managed by AgentEnhancements — {self.ae_root}

## Skills
Available via registry: `python unified-integration/scripts/registry.py map "<task>"`

## Memory
Persistent memory at: {self.memory_root}

## MCP
Gateway configured in ~/.codex/config.toml
"""

    def _opencode_config_template(self) -> str:
        return f"""{{
  "$schema": "https://opencode.dev/schema.json",
  "agentEnhancements": {{
    "baseDir": "{self.ae_root}",
    "memoryRoot": "{self.memory_root}",
    "maxSkillCards": 8
  }}
}}"""

    def _opencode_agents_md_template(self) -> str:
        return f"""# AgentEnhancements for OpenCode

Managed by AgentEnhancements — {self.ae_root}

## Skills
Available via registry: `python unified-integration/scripts/registry.py map "<task>"`
"""

    def _hermes_config_template(self) -> str:
        return f"""# AgentEnhancements Hermes Configuration
base_dir: "{self.ae_root}"
memory_root: "{self.memory_root}"
max_skill_cards: 8
"""

    def _hermes_soul_template(self) -> str:
        return f"""# Hermes SOUL — AgentEnhancements Integration

Managed by AgentEnhancements — {self.ae_root}

## Available Capabilities
- Skill Registry (3,000+ skills)
- Persistent Memory
- Context Compression
- MCP Gateway
"""

    def _cursor_main_rule_template(self) -> str:
        return f"""---
description: AgentEnhancements integration for Cursor
globs: []
alwaysApply: false
---
# AgentEnhancements for Cursor

Managed by AgentEnhancements — {self.ae_root}

## Skills Registry
Available via: `python unified-integration/scripts/registry.py map "<task>"`

## Memory
Persistent memory at: {self.memory_root}

## MCP Gateway
Reference configuration only — manual setup required.
"""

    def _gemini_md_template(self) -> str:
        return f"""# AgentEnhancements for Gemini CLI

Managed by AgentEnhancements — {self.ae_root}

## Skills
Search registry: `python unified-integration/scripts/registry.py map "<task>"`

## Memory
Persistent memory at: {self.memory_root}
"""

    def _gemini_config_template(self) -> str:
        return f"""# AgentEnhancements Gemini Configuration
base_dir: "{self.ae_root}"
memory_root: "{self.memory_root}"
"""

    def _copilot_agents_md_template(self) -> str:
        return f"""# AgentEnhancements for GitHub Copilot

Managed by AgentEnhancements — {self.ae_root}

## Skills Registry
Available via: `python unified-integration/scripts/registry.py map "<task>"`

## Memory
Persistent memory at: {self.memory_root}
"""

    def _windsurf_agents_md_template(self) -> str:
        return f"""# AgentEnhancements for Windsurf

Managed by AgentEnhancements — {self.ae_root}

## Skills Registry
Available via: `python unified-integration/scripts/registry.py map "<task>"`

## Memory
Persistent memory at: {self.memory_root}
"""

    def _kiro_agents_md_template(self) -> str:
        return f"""# AgentEnhancements for Kiro

Managed by AgentEnhancements — {self.ae_root}

## Skills Registry
Available via: `python unified-integration/scripts/registry.py map "<task>"`

## Memory
Persistent memory at: {self.memory_root}
"""


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Native Integration v2")
    parser.add_argument("command", choices=["list", "install", "detect"])
    parser.add_argument("--agents", nargs="+", help="Agents to install")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--base-dir", type=Path, help="Base directory")
    args = parser.parse_args()

    base_dir = args.base_dir or Path(__file__).resolve().parent.parent.parent
    integration = NativeIntegrationV2(base_dir)

    if args.command == "list":
        for name, agent in integration.agents.items():
            print(f"  {name}: {agent.display_name}")
    elif args.command == "detect":
        # Delegate to installer detect
        from installer import UnifiedInstaller, InstallConfig
        config = InstallConfig(base_dir=base_dir, verbose=True)
        installer = UnifiedInstaller(config)
        installer._detect_agents()
        for agent in installer.detected_agents:
            status = "✓" if agent.exists else "✗"
            print(f"  {status} {agent.display_name}: {agent.config_path}")
    elif args.command == "install":
        agents = args.agents
        if not agents:
            from installer import UnifiedInstaller, InstallConfig
            config = InstallConfig(base_dir=base_dir, dry_run=args.dry_run)
            installer = UnifiedInstaller(config)
            installer._detect_agents()
            agents = [a.name for a in installer.detected_agents if a.exists]

        for agent in agents:
            integration.install_agent(agent, args.dry_run)


if __name__ == "__main__":
    main()