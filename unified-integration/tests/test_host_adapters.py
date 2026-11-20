#!/usr/bin/env python3
"""Tests for host_adapters.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from host_adapters import (
    HOST_ADAPTER_MATRIX,
    get_adapter,
    generate_host_adapter_matrix,
    HostAdapter,
    ClaudeCodeAdapter,
    CodexAdapter,
    OpenCodeAdapter,
)


def test_all_hosts_defined():
    """Test all expected hosts are in matrix."""
    expected = [
        "claude-code", "codex", "opencode", "hermes",
        "cursor", "gemini", "copilot", "windsurf", "kiro"
    ]
    for host in expected:
        assert host in HOST_ADAPTER_MATRIX
        cap = HOST_ADAPTER_MATRIX[host]
        assert isinstance(cap.hooks, list)
        assert isinstance(cap.native_tools, list)
    print("✓ All hosts defined in matrix")


def test_claude_code_verified():
    """Test Claude Code is verified with full capabilities."""
    cap = HOST_ADAPTER_MATRIX["claude-code"]
    assert cap.verified == True
    assert cap.skills == True
    assert cap.mcp == True
    assert cap.memory == True
    assert cap.compression == True
    assert "SubagentStart" in cap.hooks
    assert "SubagentStop" in cap.hooks
    print("✓ Claude Code verified with full capabilities")


def test_codex_verified():
    """Test Codex is verified."""
    cap = HOST_ADAPTER_MATRIX["codex"]
    assert cap.verified == True
    assert cap.skills == True
    assert cap.mcp == True
    print("✓ Codex verified")


def test_opencode_verified():
    """Test OpenCode is verified."""
    cap = HOST_ADAPTER_MATRIX["opencode"]
    assert cap.verified == True
    assert cap.skills == True
    assert cap.mcp == True
    print("✓ OpenCode verified")


def test_cursor_partial():
    """Test Cursor has partial support (rules only)."""
    cap = HOST_ADAPTER_MATRIX["cursor"]
    assert cap.verified == True
    assert cap.skills == True
    assert cap.mcp == False  # No MCP support
    assert cap.hooks == []  # Uses rules, not hooks
    print("✓ Cursor partial support (rules only)")


def test_get_adapter_claude_code():
    """Test getting Claude Code adapter."""
    base_dir = Path(__file__).parent.parent.parent
    adapter = get_adapter("claude-code", base_dir)
    assert isinstance(adapter, ClaudeCodeAdapter)
    assert "SessionStart" in adapter.get_supported_events()
    assert "UserPromptSubmit" in adapter.get_supported_events()
    assert adapter.get_injection_method() == "hooks_additionalContext"
    print("✓ Claude Code adapter works")


def test_get_adapter_codex():
    """Test getting Codex adapter."""
    base_dir = Path(__file__).parent.parent.parent
    adapter = get_adapter("codex", base_dir)
    assert isinstance(adapter, CodexAdapter)
    assert "user_prompt_submit" in adapter.get_supported_events()
    assert adapter.get_injection_method() == "hooks_additionalContext"
    print("✓ Codex adapter works")


def test_get_adapter_opencode():
    """Test getting OpenCode adapter."""
    base_dir = Path(__file__).parent.parent.parent
    adapter = get_adapter("opencode", base_dir)
    assert isinstance(adapter, OpenCodeAdapter)
    assert "pre_llm_call" in adapter.get_supported_events()
    assert adapter.get_injection_method() == "plugin_context"
    print("✓ OpenCode adapter works")


def test_claude_code_hook_config():
    """Test Claude Code hook config generation."""
    base_dir = Path(__file__).parent.parent.parent
    adapter = get_adapter("claude-code", base_dir)
    config = adapter.build_hook_config("/path/runtime.py")

    assert "hooks" in config
    assert "SessionStart" in config["hooks"]
    assert "UserPromptSubmit" in config["hooks"]
    assert "PreToolUse" in config["hooks"]
    print("✓ Claude Code hook config works")


def test_codex_hook_config():
    """Test Codex hook config generation."""
    base_dir = Path(__file__).parent.parent.parent
    adapter = get_adapter("codex", base_dir)
    config = adapter.build_hook_config("/path/runtime.py")

    assert "hooks" in config
    assert "user_prompt_submit" in config["hooks"]
    assert "pre_tool_use" in config["hooks"]
    print("✓ Codex hook config works")


def test_opencode_plugin_config():
    """Test OpenCode plugin config generation."""
    base_dir = Path(__file__).parent.parent.parent
    adapter = get_adapter("opencode", base_dir)
    config = adapter.build_plugin_config("/path/runtime.py")

    assert "plugins" in config
    assert "mcp" in config
    print("✓ OpenCode plugin config works")


def test_payload_transformation():
    """Test payload transformation for each host."""
    base_dir = Path(__file__).parent.parent.parent

    # Claude Code
    adapter = get_adapter("claude-code", base_dir)
    payload = adapter.transform_payload("UserPromptSubmit", {"prompt": "test"})
    assert payload["prompt"] == "test"

    # Codex
    adapter = get_adapter("codex", base_dir)
    payload = adapter.transform_payload("user_prompt_submit", {"prompt": "test"})
    assert payload["event"] == "UserPromptSubmit"
    print("✓ Payload transformation works")


def test_injection_validation():
    """Test injection validation."""
    base_dir = Path(__file__).parent.parent.parent
    adapter = get_adapter("claude-code", base_dir)

    # Valid injection
    valid = adapter.validate_injection({"token_estimate": 300})
    assert valid == True

    # Exceeds budget
    invalid = adapter.validate_injection({"token_estimate": 500})
    assert invalid == False
    print("✓ Injection validation works")


def test_generate_host_matrix():
    """Test generating host adapter matrix."""
    base_dir = Path(__file__).parent.parent.parent
    matrix = generate_host_adapter_matrix(base_dir)

    assert "claude-code" in matrix
    assert "capabilities" in matrix["claude-code"]
    assert "supported_events" in matrix["claude-code"]
    assert "injection_method" in matrix["claude-code"]
    print("✓ Host matrix generation works")


if __name__ == "__main__":
    test_all_hosts_defined()
    test_claude_code_verified()
    test_codex_verified()
    test_opencode_verified()
    test_cursor_partial()
    test_get_adapter_claude_code()
    test_get_adapter_codex()
    test_get_adapter_opencode()
    test_claude_code_hook_config()
    test_codex_hook_config()
    test_opencode_plugin_config()
    test_payload_transformation()
    test_injection_validation()
    test_generate_host_matrix()
    print("\n✅ All host_adapters tests passed!")