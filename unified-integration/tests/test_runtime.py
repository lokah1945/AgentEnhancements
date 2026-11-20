#!/usr/bin/env python3
"""Tests for runtime.py"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from runtime import HookRuntime, HookContext


def test_session_start():
    """Test SessionStart hook."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {"base_dir": tmpdir}
        runtime = HookRuntime(config)

        payload = {}
        result = runtime.on_session_start(payload)

        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in result["hookSpecificOutput"]

        context = json.loads(result["hookSpecificOutput"]["additionalContext"])
        assert context["type"] == "session_start"
        assert "session_id" in context
        assert "recalled_memories" in context
    print("✓ SessionStart works")


def test_user_prompt_submit():
    """Test UserPromptSubmit hook."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {"base_dir": tmpdir}
        runtime = HookRuntime(config)

        payload = {"prompt": "build a typescript mcp server"}
        result = runtime.on_user_prompt_submit(payload)

        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        assert "additionalContext" in result["hookSpecificOutput"]

        context = json.loads(result["hookSpecificOutput"]["additionalContext"])
        assert context["type"] == "capability_package"
        assert "selected_skills" in context
        assert "selected_plugins" in context
        assert "selected_mcp_servers" in context
        assert "token_estimate" in context
    print("✓ UserPromptSubmit works")


def test_pre_tool_use():
    """Test PreToolUse hook."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {"base_dir": tmpdir}
        runtime = HookRuntime(config)

        payload = {"tool_name": "read_file", "tool_input": {"path": "test.py"}}
        result = runtime.on_pre_tool_use(payload)

        assert result["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert len(runtime._tool_calls) == 1
        assert runtime._tool_calls[0]["tool"] == "read_file"
    print("✓ PreToolUse works")


def test_post_tool_use():
    """Test PostToolUse hook."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {"base_dir": tmpdir}
        runtime = HookRuntime(config)

        # First pre
        runtime.on_pre_tool_use({"tool_name": "write_file", "tool_input": {"path": "test.py"}})

        # Then post
        payload = {"tool_name": "write_file", "tool_result": {"success": True}}
        result = runtime.on_post_tool_use(payload)

        assert result["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert len(runtime._tool_calls) == 1
        assert "result_summary" in runtime._tool_calls[0]
    print("✓ PostToolUse works")


def test_stop():
    """Test Stop hook."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {"base_dir": tmpdir}
        runtime = HookRuntime(config)

        # Add some tool calls
        runtime.on_pre_tool_use({"tool_name": "tool1", "tool_input": {}})
        runtime.on_pre_tool_use({"tool_name": "tool2", "tool_input": {}})

        payload = {}
        result = runtime.on_stop(payload)

        assert result["hookSpecificOutput"]["hookEventName"] == "Stop"
        assert "additionalContext" in result["hookSpecificOutput"]

        context = json.loads(result["hookSpecificOutput"]["additionalContext"])
        assert "session_summary" in context
        summary = context["session_summary"]
        assert summary["tool_calls_count"] == 2
        assert set(summary["tools_used"]) == {"tool1", "tool2"}
    print("✓ Stop works")


def test_hook_chaining():
    """Test full hook chain."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {"base_dir": tmpdir}
        runtime = HookRuntime(config)

        # Session start
        runtime.on_session_start({})

        # User prompt
        runtime.on_user_prompt_submit({"prompt": "test task"})

        # Tool calls
        runtime.on_pre_tool_use({"tool_name": "read", "tool_input": {}})
        runtime.on_post_tool_use({"tool_name": "read", "tool_result": {"data": "x"}})

        runtime.on_pre_tool_use({"tool_name": "write", "tool_input": {}})
        runtime.on_post_tool_use({"tool_name": "write", "tool_result": {"ok": True}})

        # Stop
        result = runtime.on_stop({})

        summary = json.loads(result["hookSpecificOutput"]["additionalContext"])["session_summary"]
        assert summary["tool_calls_count"] == 2
        assert summary["duration_seconds"] >= 0
    print("✓ Hook chaining works")


def test_memory_integration():
    """Test memory is saved during hooks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {"base_dir": tmpdir}
        runtime = HookRuntime(config)

        runtime.on_user_prompt_submit({"prompt": "test"})

        # Check memory was saved - query for prompt entries
        prompt_mems = runtime.memory.query("session_context", session_id=runtime.session_id, key_prefix="")
        # Find prompt entry
        prompt_found = any("prompt" in m["data"] for m in prompt_mems)
        assert prompt_found, "Prompt should be saved in memory"

        # Check selection memory - query all and filter
        all_mems = runtime.memory.query("session_context", session_id=runtime.session_id, key_prefix="")
        selection_found = any("selected_skills" in str(m["data"]) for m in all_mems)
        assert selection_found, "Selection should be saved in memory"
    print("✓ Memory integration works")


if __name__ == "__main__":
    test_session_start()
    test_user_prompt_submit()
    test_pre_tool_use()
    test_post_tool_use()
    test_stop()
    test_hook_chaining()
    test_memory_integration()
    print("\n✅ All runtime tests passed!")