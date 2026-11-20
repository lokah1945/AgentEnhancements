#!/usr/bin/env python3
"""Tests for gateway.py"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from gateway import MCPGateway, MCPServerConfig, BuiltinMCPServer, FilesystemMCPServer, GitMCPServer


def test_gateway_load_config():
    """Test loading MCP server configs."""
    base_dir = Path(__file__).parent.parent.parent
    gateway = MCPGateway(base_dir)

    assert len(gateway.servers) > 0
    for sid, instance in gateway.servers.items():
        assert instance.config.id == sid
        assert instance.config.command
    print(f"✓ Config loading: {len(gateway.servers)} servers")


def test_server_status():
    """Test server status reporting."""
    base_dir = Path(__file__).parent.parent.parent
    gateway = MCPGateway(base_dir)

    for sid in gateway.servers:
        status = gateway.get_server_status(sid)
        assert status is not None
        assert status["id"] == sid
        assert "status" in status
        assert "health" in status
    print("✓ Status reporting works")


def test_list_tools_empty():
    """Test listing tools when no servers running."""
    base_dir = Path(__file__).parent.parent.parent
    gateway = MCPGateway(base_dir)

    tools = gateway.list_tools()
    # Should be empty since servers not started
    assert isinstance(tools, dict)
    print("✓ List tools (empty) works")


def test_builtin_filesystem():
    """Test built-in filesystem MCP server."""
    server = FilesystemMCPServer()

    # Test tool registration
    assert "read_file" in server.tools
    assert "write_file" in server.tools
    assert "list_dir" in server.tools
    assert "glob" in server.tools

    # Test read_file handler
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        tmp_path = f.name

    try:
        result = server.tools["read_file"]["handler"]({"path": tmp_path})
        assert "content" in result
        assert result["content"] == "test content"
    finally:
        import os
        os.unlink(tmp_path)

    print("✓ Filesystem MCP server works")


def test_builtin_git():
    """Test built-in git MCP server."""
    server = GitMCPServer()

    assert "git_status" in server.tools
    assert "git_log" in server.tools
    assert "git_diff" in server.tools

    # Test in a git repo if git available
    import shutil
    import subprocess
    if shutil.which("git"):
        result = subprocess.run(["git", "status"], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        if result.returncode == 0:
            tool_result = server.tools["git_status"]["handler"]({"repo_path": "."})
            assert "output" in tool_result
            print("✓ Git MCP server works")
        else:
            print("⚠ Git MCP server test skipped (not a git repo)")
    else:
        print("⚠ Git MCP server test skipped (git not installed)")


def test_gateway_shutdown():
    """Test gateway shutdown."""
    base_dir = Path(__file__).parent.parent.parent
    gateway = MCPGateway(base_dir)

    # Should not error
    gateway.shutdown()
    print("✓ Gateway shutdown works")


def test_server_config():
    """Test MCPServerConfig creation."""
    config = MCPServerConfig(
        id="test-server",
        name="Test Server",
        command=["python", "-m", "test"],
        env={"KEY": "value"},
        tools=["tool1", "tool2"],
    )
    assert config.id == "test-server"
    assert config.command == ["python", "-m", "test"]
    assert config.env == {"KEY": "value"}
    print("✓ Server config works")


if __name__ == "__main__":
    test_gateway_load_config()
    test_server_status()
    test_list_tools_empty()
    test_builtin_filesystem()
    test_builtin_git()
    test_gateway_shutdown()
    test_server_config()
    print("\n✅ All gateway tests passed!")