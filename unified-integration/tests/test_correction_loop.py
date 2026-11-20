#!/usr/bin/env python3
"""Tests for correction_loop.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from correction_loop import (
    FailureAnalyzer, CorrectionPlanner, LoopController,
    FailureCategory, Hypothesis, CorrectionStep
)
from quality_checks import CheckResult, CheckStatus
from registry import SkillRegistry


def test_failure_categorization():
    """Test categorizing failures from error output."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    analyzer = FailureAnalyzer(base_dir, registry)

    # Syntax error
    result = CheckResult(
        check_id="syntax_test",
        status=CheckStatus.FAIL,
        command="python3 -m py_compile test.py",
        exit_code=1,
        stdout="",
        stderr="SyntaxError: invalid syntax",
        duration_ms=100,
        timestamp="2024-01-01T00:00:00Z",
        scope=".",
        repo_commit="abc123",
        task_id="task-1",
        error_signature="SyntaxError: invalid syntax",
    )

    category = analyzer._categorize_failure(result)
    assert category == FailureCategory.SYNTAX_ERROR
    print("✓ Syntax error categorization works")

    # Type error
    result = CheckResult(
        check_id="type_test",
        status=CheckStatus.FAIL,
        command="mypy test.py",
        exit_code=1,
        stdout="",
        stderr="TypeError: argument 1 has incompatible type",
        duration_ms=100,
        timestamp="2024-01-01T00:00:00Z",
        scope=".",
        repo_commit="abc123",
        task_id="task-1",
        error_signature="TypeError",
    )

    category = analyzer._categorize_failure(result)
    assert category == FailureCategory.TYPE_ERROR
    print("✓ Type error categorization works")

    # Test failure
    result = CheckResult(
        check_id="test_test",
        status=CheckStatus.FAIL,
        command="pytest test.py",
        exit_code=1,
        stdout="",
        stderr="AssertionError: expected 2, got 3",
        duration_ms=100,
        timestamp="2024-01-01T00:00:00Z",
        scope=".",
        repo_commit="abc123",
        task_id="task-1",
        error_signature="AssertionError",
    )

    category = analyzer._categorize_failure(result)
    assert category == FailureCategory.TEST_FAILURE
    print("✓ Test failure categorization works")

    # Import error
    result = CheckResult(
        check_id="import_test",
        status=CheckStatus.FAIL,
        command="python3 test.py",
        exit_code=1,
        stdout="",
        stderr="ModuleNotFoundError: No module named 'missing_module'",
        duration_ms=100,
        timestamp="2024-01-01T00:00:00Z",
        scope=".",
        repo_commit="abc123",
        task_id="task-1",
        error_signature="ModuleNotFoundError",
    )

    category = analyzer._categorize_failure(result)
    assert category == FailureCategory.IMPORT_ERROR
    print("✓ Import error categorization works")


def test_hypothesis_generation():
    """Test generating hypotheses for failures."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    analyzer = FailureAnalyzer(base_dir, registry)

    # Syntax error hypothesis
    result = CheckResult(
        check_id="syntax_test",
        status=CheckStatus.FAIL,
        command="python3 -m py_compile test.py",
        exit_code=1,
        stdout="",
        stderr="SyntaxError: invalid syntax at line 10",
        duration_ms=100,
        timestamp="2024-01-01T00:00:00Z",
        scope=".",
        repo_commit="abc123",
        task_id="task-1",
        error_signature="SyntaxError: invalid syntax",
    )

    hypotheses = analyzer.analyze_failure(result)
    assert len(hypotheses) > 0
    hyp = hypotheses[0]
    assert isinstance(hyp, Hypothesis)
    assert hyp.category == FailureCategory.SYNTAX_ERROR
    assert hyp.confidence > 0.5
    assert hyp.test_command
    print("✓ Hypothesis generation works")


def test_capability_recommendation():
    """Test capability recommendation for failure categories."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    analyzer = FailureAnalyzer(base_dir, registry)

    # Each category should have a capability recommendation
    for category in FailureCategory:
        cap = analyzer._recommend_capability(category)
        if category != FailureCategory.UNKNOWN:
            # May return None if no skill matches, but should not error
            print(f"  {category.value}: {cap}")
    print("✓ Capability recommendation works")


def test_correction_planner():
    """Test planning correction steps."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    planner = CorrectionPlanner(base_dir, registry)

    result = CheckResult(
        check_id="syntax_test",
        status=CheckStatus.FAIL,
        command="python3 -m py_compile test.py",
        exit_code=1,
        stdout="",
        stderr="SyntaxError: invalid syntax",
        duration_ms=100,
        timestamp="2024-01-01T00:00:00Z",
        scope=".",
        repo_commit="abc123",
        task_id="task-1",
        error_signature="SyntaxError: invalid syntax",
    )

    steps = planner.plan_correction(result)
    assert len(steps) > 0
    for step in steps:
        assert isinstance(step, CorrectionStep)
        assert step.hypothesis
        assert step.change_description
        assert step.verification_checks
    print(f"✓ Correction planner: {len(steps)} steps")


def test_verification_checks():
    """Test getting verification checks for categories."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    planner = CorrectionPlanner(base_dir, registry)

    for category in FailureCategory:
        checks = planner._get_verification_checks(category)
        assert isinstance(checks, list)
    print("✓ Verification checks work")


def test_loop_controller():
    """Test loop controller status."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    controller = LoopController(base_dir, registry)

    status = controller.get_status()
    assert status["iteration"] == 0
    assert status["max_iterations"] == 5
    assert status["total_tokens"] == 0
    assert status["should_stop"] == False
    print("✓ Loop controller initial status works")

    # Test should_continue with failing results
    from quality_checks import CheckResult, CheckStatus
    results = [
        CheckResult(
            check_id="fail_1",
            status=CheckStatus.FAIL,
            command="test",
            exit_code=1,
            stdout="",
            stderr="error",
            duration_ms=100,
            timestamp="2024-01-01T00:00:00Z",
            scope=".",
            repo_commit="abc123",
            task_id="task-1",
            error_signature="error",
        )
    ]
    assert controller.should_continue(results) == True
    print("✓ Should continue with failures")

    # Test should_continue with all passing
    results = [
        CheckResult(
            check_id="pass_1",
            status=CheckStatus.PASS,
            command="test",
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100,
            timestamp="2024-01-01T00:00:00Z",
            scope=".",
            repo_commit="abc123",
            task_id="task-1",
            error_signature="",
        )
    ]
    assert controller.should_continue(results) == False
    print("✓ Should stop with all passing")


def test_loop_iteration():
    """Test running a loop iteration."""
    base_dir = Path(__file__).parent.parent.parent
    registry = SkillRegistry(base_dir)
    controller = LoopController(base_dir, registry)

    result = CheckResult(
        check_id="syntax_fail",
        status=CheckStatus.FAIL,
        command="python3 -m py_compile test.py",
        exit_code=1,
        stdout="",
        stderr="SyntaxError: invalid syntax",
        duration_ms=100,
        timestamp="2024-01-01T00:00:00Z",
        scope=".",
        repo_commit="abc123",
        task_id="task-1",
        error_signature="SyntaxError",
    )

    steps = controller.run_iteration([result])
    assert len(steps) > 0
    assert controller.iteration == 1
    assert controller.total_tokens > 0
    print(f"✓ Loop iteration: {len(steps)} steps, {controller.total_tokens} tokens")


if __name__ == "__main__":
    test_failure_categorization()
    test_hypothesis_generation()
    test_capability_recommendation()
    test_correction_planner()
    test_verification_checks()
    test_loop_controller()
    test_loop_iteration()
    print("\n✅ All correction_loop tests passed!")