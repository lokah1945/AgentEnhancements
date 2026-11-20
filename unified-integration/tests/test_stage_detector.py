#!/usr/bin/env python3
"""Tests for stage_detector.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage_detector import StageDetector, TaskStage, AgentRole


def test_stage_detection_understand():
    """Test detection of understand stage."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    result = detector.detect_from_prompt("explore the codebase and understand the architecture")
    assert result.stage == TaskStage.UNDERSTAND
    assert result.confidence > 0
    print("✓ Understand stage detected")


def test_stage_detection_plan():
    """Test detection of plan stage."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    result = detector.detect_from_prompt("create a plan for implementing user authentication")
    assert result.stage == TaskStage.PLAN
    assert result.confidence > 0
    print("✓ Plan stage detected")


def test_stage_detection_implement():
    """Test detection of implement stage."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    result = detector.detect_from_prompt("build a REST API endpoint for user registration")
    assert result.stage == TaskStage.IMPLEMENT
    assert result.confidence > 0
    print("✓ Implement stage detected")


def test_stage_detection_debug():
    """Test detection of debug stage."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    result = detector.detect_from_prompt("debug the memory leak in the data processing pipeline")
    assert result.stage == TaskStage.DEBUG
    assert result.confidence > 0
    print("✓ Debug stage detected")


def test_stage_detection_verify():
    """Test detection of verify stage."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    result = detector.detect_from_prompt("run integration tests and verify the deployment")
    assert result.stage == TaskStage.VERIFY
    assert result.confidence > 0
    print("✓ Verify stage detected")


def test_stage_detection_release():
    """Test detection of release stage."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    result = detector.detect_from_prompt("deploy the application to production")
    assert result.stage == TaskStage.RELEASE
    assert result.confidence > 0
    print("✓ Release stage detected")


def test_stage_detection_unknown():
    """Test unknown stage for ambiguous prompts."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    result = detector.detect_from_prompt("hello world")
    assert result.stage == TaskStage.UNKNOWN
    assert result.confidence == 0.0
    print("✓ Unknown stage for ambiguous prompt")


def test_subagent_event_detection():
    """Test detection from SubagentStart event."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    event = {
        "subagent_id": "sub-123",
        "task": "fix the authentication bug",
        "role": "debugger",
    }
    result = detector.detect_from_subagent_event(event)
    assert result.stage == TaskStage.DEBUG
    assert result.role == AgentRole.SUBAGENT
    assert result.subagent_id == "sub-123"
    assert result.subagent_task == "fix the authentication bug"
    print("✓ Subagent event detection works")


def test_continuation_detection():
    """Test detection from continuation context."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    context = {
        "recent_tools": [
            {"tool": "read_file"},
            {"tool": "grep"},
            {"tool": "bash"},
        ],
        "session_duration": 300,
    }
    result = detector.detect_from_continuation(context)
    assert result.stage in (TaskStage.UNDERSTAND, TaskStage.IMPLEMENT)
    print(f"✓ Continuation detection: {result.stage.value}")


def test_explicit_stage_hint():
    """Test explicit stage hint in context."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    context = {"stage": "debug"}
    result = detector.detect_from_prompt("some task", context)
    assert result.stage == TaskStage.DEBUG
    assert "explicit_stage" in result.signals
    print("✓ Explicit stage hint works")


def test_stage_guidance():
    """Test stage guidance retrieval."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    guidance = detector.get_stage_guidance(TaskStage.IMPLEMENT)
    assert "priority_capabilities" in guidance
    assert "suggested_skills" in guidance
    assert "avoid" in guidance
    print("✓ Stage guidance retrieved")


def test_role_detection_reviewer():
    """Test reviewer role detection."""
    base_dir = Path(__file__).parent.parent.parent
    detector = StageDetector(base_dir)

    event = {
        "subagent_id": "review-1",
        "task": "review the security changes",
        "role": "reviewer",
    }
    result = detector.detect_from_subagent_event(event)
    assert result.role == AgentRole.REVIEWER
    print("✓ Reviewer role detected")


if __name__ == "__main__":
    test_stage_detection_understand()
    test_stage_detection_plan()
    test_stage_detection_implement()
    test_stage_detection_debug()
    test_stage_detection_verify()
    test_stage_detection_release()
    test_stage_detection_unknown()
    test_subagent_event_detection()
    test_continuation_detection()
    test_explicit_stage_hint()
    test_stage_guidance()
    test_role_detection_reviewer()
    print("\n✅ All stage_detector tests passed!")