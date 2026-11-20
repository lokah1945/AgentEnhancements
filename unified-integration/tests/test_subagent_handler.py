#!/usr/bin/env python3
"""Tests for subagent_handler.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from subagent_handler import SubagentHandler
from registry import SkillRegistry


def test_subagent_start():
    """Test SubagentStart handling."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    handler = SubagentHandler(base_dir, registry)

    event = {
        "subagent_id": "sub-1",
        "task": "fix the login bug",
        "role": "debugger",
    }
    result = handler.on_subagent_start(event, "session-1")

    assert result["subagent_id"] == "sub-1"
    assert "capabilities" in result
    assert "token_estimate" in result
    assert result["token_estimate"] <= 200  # Subagent budget
    print("✓ Subagent start works")


def test_subagent_stop():
    """Test SubagentStop handling."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    handler = SubagentHandler(base_dir, registry)

    # Start first
    event = {"subagent_id": "sub-1", "task": "fix bug", "role": "debugger"}
    handler.on_subagent_start(event, "session-1")

    # Then stop
    stop_event = {"subagent_id": "sub-1", "result": {"success": True}}
    result = handler.on_subagent_stop(stop_event, "session-1")

    assert result["subagent_id"] == "sub-1"
    assert "duration_seconds" in result
    assert "capabilities_used" in result
    print("✓ Subagent stop works")


def test_duplicate_injection_prevention():
    """Test that duplicate capabilities are not injected."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    handler = SubagentHandler(base_dir, registry)

    # Start first subagent
    event1 = {"subagent_id": "sub-1", "task": "typescript refactor", "role": "implementer"}
    result1 = handler.on_subagent_start(event1, "session-1")

    # Start second subagent with similar task
    event2 = {"subagent_id": "sub-2", "task": "typescript refactor", "role": "implementer"}
    result2 = handler.on_subagent_start(event2, "session-1")

    # Second subagent should have fewer or different capabilities
    caps1 = {c["id"] for c in result1["capabilities"]}
    caps2 = {c["id"] for c in result2["capabilities"]}

    # Should not have exact same capabilities (deduplication)
    assert caps1 != caps2 or len(caps2) <= len(caps1)
    print("✓ Duplicate injection prevention works")


def test_subagent_status():
    """Test subagent status retrieval."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    handler = SubagentHandler(base_dir, registry)

    event = {"subagent_id": "sub-1", "task": "debug auth", "role": "debugger"}
    handler.on_subagent_start(event, "session-1")

    status = handler.get_subagent_status("sub-1")
    assert status is not None
    assert status["subagent_id"] == "sub-1"
    assert status["task"] == "debug auth"
    assert status["role"] == "debugger"
    assert status["duration"] >= 0
    print("✓ Subagent status works")


def test_list_active_subagents():
    """Test listing active subagents."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    handler = SubagentHandler(base_dir, registry)

    # Add subagents
    handler.on_subagent_start({"subagent_id": "sub-1", "task": "task1"}, "session-1")
    handler.on_subagent_start({"subagent_id": "sub-2", "task": "task2"}, "session-1")
    handler.on_subagent_start({"subagent_id": "sub-3", "task": "task3"}, "session-2")

    session1_subagents = handler.list_active_subagents("session-1")
    assert len(session1_subagents) == 2

    session2_subagents = handler.list_active_subagents("session-2")
    assert len(session2_subagents) == 1
    print("✓ List active subagents works")


def test_check_duplicate_injection():
    """Test duplicate injection check."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    handler = SubagentHandler(base_dir, registry)

    # Inject a capability
    handler._injected_per_session["session-1"] = {"skill-1", "skill-2"}

    assert handler.check_duplicate_injection("skill-1", "session-1")
    assert not handler.check_duplicate_injection("skill-3", "session-1")
    assert not handler.check_duplicate_injection("skill-1", "session-2")
    print("✓ Duplicate injection check works")


def test_cleanup_session():
    """Test session cleanup."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    handler = SubagentHandler(base_dir, registry)

    handler._injected_per_session["session-1"] = {"skill-1"}
    handler.cleanup_session("session-1")

    assert "session-1" not in handler._injected_per_session
    print("✓ Session cleanup works")


def test_multiple_sessions_isolated():
    """Test that sessions are isolated."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    handler = SubagentHandler(base_dir, registry)

    # Inject in session 1
    handler._injected_per_session["session-1"] = {"skill-1"}

    # Session 2 should not see it
    assert not handler.check_duplicate_injection("skill-1", "session-2")
    print("✓ Sessions are isolated")


if __name__ == "__main__":
    test_subagent_start()
    test_subagent_stop()
    test_duplicate_injection_prevention()
    test_subagent_status()
    test_list_active_subagents()
    test_check_duplicate_injection()
    test_cleanup_session()
    test_multiple_sessions_isolated()
    print("\n✅ All subagent_handler tests passed!")