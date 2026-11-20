#!/usr/bin/env python3
"""
AgentEnhancements Host Adapters — Verified host integration matrix.
Documents and implements host-specific event handling for verified capabilities.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum


class HostEvent(Enum):
    """Standardized host events."""
    SESSION_START = "session_start"
    USER_PROMPT_SUBMIT = "user_prompt_submit"
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    STOP = "stop"
    SUBAGENT_START = "subagent_start"
    SUBAGENT_STOP = "subagent_stop"


@dataclass
class HostCapability:
    """Capability support for a host."""
    hooks: List[str] = field(default_factory=list)
    skills: bool = False
    mcp: bool = False
    memory: bool = False
    compression: bool = False
    native_tools: List[str] = field(default_factory=list)
    min_version: str = ""
    verified: bool = False
    notes: str = ""


# Verified Host Adapter Matrix
# Based on official documentation and testing
HOST_ADAPTER_MATRIX = {
    "claude-code": HostCapability(
        hooks=[
            "SessionStart",
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
            "Stop",
            "SubagentStart",
            "SubagentStop",
        ],
        skills=True,
        mcp=True,
        memory=True,
        compression=True,
        native_tools=[
            "read_file", "write_file", "edit_file", "bash",
            "glob", "grep", "task", "todo", "webfetch"
        ],
        min_version="1.0.0",
        verified=True,
        notes="Full native lifecycle integration via settings.json hooks. Subagent events available.",
    ),
    "codex": HostCapability(
        hooks=[
            "user_prompt_submit",
            "pre_tool_use",
            "post_tool_use",
            "session_start",
            "session_end",
        ],
        skills=True,
        mcp=True,
        memory=True,
        compression=True,
        native_tools=[
            "read", "write", "edit", "bash",
            "glob", "grep", "patch", "apply_patch"
        ],
        min_version="0.167.0",
        verified=True,
        notes="Native hooks via hooks.json. Tool catalog may require session refresh for new MCP tools.",
    ),
    "opencode": HostCapability(
        hooks=[
            "pre_llm_call",
            "post_llm_call",
            "post_tool_call",
        ],
        skills=True,
        mcp=True,
        memory=True,
        compression=True,
        native_tools=[
            "read", "write", "edit", "bash",
            "glob", "grep"
        ],
        min_version="2.0.0",
        verified=True,
        notes="Plugin-based integration via opencode.jsonc. MCP gateway via native plugin.",
    ),
    "hermes": HostCapability(
        hooks=[
            "pre_llm_call",
            "post_llm_call",
            "post_tool_call",
        ],
        skills=True,
        mcp=True,
        memory=False,
        compression=False,
        native_tools=[],
        min_version="0.1.0",
        verified=False,
        notes="Profile-based integration. Limited hook events. Memory/compression not natively supported.",
    ),
    "cursor": HostCapability(
        hooks=[],  # Uses rules, not hooks
        skills=True,
        mcp=False,
        memory=True,
        compression=True,
        native_tools=[],
        min_version="0.40.0",
        verified=True,
        notes="Global MDC rules for skill discovery. No native hook system. MCP not supported.",
    ),
    "gemini": HostCapability(
        hooks=[],
        skills=False,
        mcp=False,
        memory=True,
        compression=True,
        native_tools=[],
        min_version="1.0.0",
        verified=False,
        notes="Reference config only (GEMINI.md). No native skill discovery or hooks.",
    ),
    "copilot": HostCapability(
        hooks=[],
        skills=False,
        mcp=False,
        memory=False,
        compression=False,
        native_tools=[],
        min_version="1.0.0",
        verified=False,
        notes="Reference config only. Use via launcher.",
    ),
    "windsurf": HostCapability(
        hooks=[],
        skills=True,
        mcp=False,
        memory=True,
        compression=True,
        native_tools=[],
        min_version="1.0.0",
        verified=False,
        notes="Global rule file. No hook system. Skills via rule reference.",
    ),
    "kiro": HostCapability(
        hooks=[],
        skills=False,
        mcp=False,
        memory=False,
        compression=False,
        native_tools=[],
        min_version="1.0.0",
        verified=False,
        notes="Reference config only. Use via launcher.",
    ),
}


class HostAdapter:
    """Base class for host-specific adapters."""

    def __init__(self, host_name: str, base_dir: Path):
        self.host_name = host_name
        self.base_dir = base_dir
        self.capability = HOST_ADAPTER_MATRIX.get(host_name)

    def get_supported_events(self) -> List[str]:
        """Get list of supported hook events."""
        if self.capability:
            return self.capability.hooks
        return []

    def get_injection_method(self) -> str:
        """Get method for context injection."""
        if self.host_name == "claude-code":
            return "hooks_additionalContext"
        elif self.host_name == "codex":
            return "hooks_additionalContext"
        elif self.host_name == "opencode":
            return "plugin_context"
        elif self.host_name in ("cursor", "windsurf"):
            return "rule_file"
        else:
            return "reference_only"

    def transform_payload(self, event: str, payload: Dict) -> Dict:
        """Transform host-specific payload to standard format."""
        # Default: pass through
        return payload

    def validate_injection(self, injection: Dict) -> bool:
        """Validate injection payload for this host."""
        # Check token budget
        token_estimate = injection.get("token_estimate", 0)
        if token_estimate > 400:
            return False
        return True


class ClaudeCodeAdapter(HostAdapter):
    """Claude Code specific adapter."""

    def __init__(self, base_dir: Path):
        super().__init__("claude-code", base_dir)

    def transform_payload(self, event: str, payload: Dict) -> Dict:
        """Transform Claude Code payload."""
        if event == "UserPromptSubmit":
            return {
                "prompt": payload.get("prompt", ""),
                "session_id": payload.get("session_id", ""),
            }
        elif event in ("PreToolUse", "PostToolUse"):
            return {
                "tool_name": payload.get("tool_name", ""),
                "tool_input": payload.get("tool_input", {}),
                "tool_result": payload.get("tool_result", {}),
            }
        return payload

    def build_hook_config(self, runtime_path: str) -> Dict:
        """Build settings.json hook configuration."""
        python = "python3"
        return {
            "hooks": {
                "SessionStart": [
                    {"type": "command", "command": f"{python} {runtime_path} SessionStart", "timeout": 5000}
                ],
                "UserPromptSubmit": [
                    {"type": "command", "command": f"{python} {runtime_path} UserPromptSubmit", "timeout": 10000}
                ],
                "PreToolUse": [
                    {"type": "command", "command": f"{python} {runtime_path} PreToolUse", "timeout": 2000}
                ],
                "PostToolUse": [
                    {"type": "command", "command": f"{python} {runtime_path} PostToolUse", "timeout": 2000}
                ],
                "Stop": [
                    {"type": "command", "command": f"{python} {runtime_path} Stop", "timeout": 5000}
                ],
            }
        }


class CodexAdapter(HostAdapter):
    """Codex CLI specific adapter."""

    def __init__(self, base_dir: Path):
        super().__init__("codex", base_dir)

    def transform_payload(self, event: str, payload: Dict) -> Dict:
        """Transform Codex payload."""
        # Codex uses different event names
        event_map = {
            "user_prompt_submit": "UserPromptSubmit",
            "pre_tool_use": "PreToolUse",
            "post_tool_use": "PostToolUse",
            "session_start": "SessionStart",
            "session_end": "Stop",
        }
        std_event = event_map.get(event, event)
        return {"event": std_event, **payload}

    def build_hook_config(self, runtime_path: str) -> Dict:
        """Build hooks.json configuration."""
        python = "python3"
        return {
            "hooks": {
                "user_prompt_submit": [
                    {"command": f"{python} {runtime_path} UserPromptSubmit", "timeout": 10000}
                ],
                "pre_tool_use": [
                    {"command": f"{python} {runtime_path} PreToolUse", "timeout": 2000}
                ],
                "post_tool_use": [
                    {"command": f"{python} {runtime_path} PostToolUse", "timeout": 2000}
                ],
                "session_start": [
                    {"command": f"{python} {runtime_path} SessionStart", "timeout": 5000}
                ],
                "session_end": [
                    {"command": f"{python} {runtime_path} Stop", "timeout": 5000}
                ],
            }
        }


class OpenCodeAdapter(HostAdapter):
    """OpenCode specific adapter."""

    def __init__(self, base_dir: Path):
        super().__init__("opencode", base_dir)

    def build_plugin_config(self, runtime_path: str) -> Dict:
        """Build opencode.jsonc plugin configuration."""
        runtime_path = Path(runtime_path)
        return {
            "$schema": "https://opencode.ai/config.json",
            "plugins": [
                {"name": "agent-enhancements", "path": str(self.base_dir / "unified-integration" / "opencode-plugin")}
            ],
            "mcp": {
                "servers": {
                    "ae-gateway": {
                        "command": ["python3", str(runtime_path.parent / "gateway.py"), "run-builtin", "--builtin", "filesystem"]
                    }
                }
            }
        }


def get_adapter(host_name: str, base_dir: Path) -> HostAdapter:
    """Get adapter instance for host."""
    adapters = {
        "claude-code": ClaudeCodeAdapter,
        "codex": CodexAdapter,
        "opencode": OpenCodeAdapter,
    }
    adapter_class = adapters.get(host_name)
    if adapter_class:
        return adapter_class(base_dir)
    # For hosts without specific adapters, return base adapter
    return HostAdapter(host_name, base_dir)


def generate_host_adapter_matrix(base_dir: Path) -> Dict:
    """Generate documentation matrix for all hosts."""
    matrix = {}
    for host_name, cap in HOST_ADAPTER_MATRIX.items():
        adapter = get_adapter(host_name, base_dir)
        matrix[host_name] = {
            "capabilities": asdict(cap),
            "supported_events": adapter.get_supported_events(),
            "injection_method": adapter.get_injection_method(),
            "adapter_class": type(adapter).__name__,
        }
    return matrix


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Host Adapters CLI")
    parser.add_argument("command", choices=["matrix", "adapter", "verify", "generate-config"])
    parser.add_argument("--host", help="Host name")
    parser.add_argument("--event", help="Event name")
    parser.add_argument("--payload", help="Payload JSON")
    parser.add_argument("--runtime-path", help="Runtime script path")
    parser.add_argument("--base-dir", help="Base directory")
    parser.add_argument("--output", help="Output file")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent

    if args.command == "matrix":
        matrix = generate_host_adapter_matrix(base_dir)
        output = json.dumps(matrix, indent=2)
        if args.output:
            Path(args.output).write_text(output)
        else:
            print(output)

    elif args.command == "adapter":
        if not args.host:
            parser.error("--host required")
        adapter = get_adapter(args.host, base_dir)
        print(json.dumps({
            "host": args.host,
            "supported_events": adapter.get_supported_events(),
            "injection_method": adapter.get_injection_method(),
        }, indent=2))

    elif args.command == "verify":
        if not args.host or not args.event or not args.payload:
            parser.error("--host, --event, --payload required")
        adapter = get_adapter(args.host, base_dir)
        payload = json.loads(args.payload)
        transformed = adapter.transform_payload(args.event, payload)
        valid = adapter.validate_injection(transformed)
        print(json.dumps({
            "valid": valid,
            "transformed": transformed,
        }, indent=2))

    elif args.command == "generate-config":
        if not args.host or not args.runtime_path:
            parser.error("--host and --runtime-path required")
        adapter = get_adapter(args.host, base_dir)
        if hasattr(adapter, "build_hook_config"):
            config = adapter.build_hook_config(args.runtime_path)
        elif hasattr(adapter, "build_plugin_config"):
            config = adapter.build_plugin_config(args.runtime_path)
        else:
            config = {}
        output = json.dumps(config, indent=2)
        if args.output:
            Path(args.output).write_text(output)
        else:
            print(output)


if __name__ == "__main__":
    from dataclasses import field
    main()