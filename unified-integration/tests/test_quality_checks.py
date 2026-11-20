#!/usr/bin/env python3
"""Tests for quality_checks.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from quality_checks import (
    AcceptanceDeriver, CheckRunner, CheckResult, CheckStatus,
    ChangeType, CheckSource, AcceptanceCheck
)


def test_change_type_detection():
    """Test change type detection from request."""
    base_dir = Path(__file__).parent.parent.parent
    deriver = AcceptanceDeriver(base_dir)

    # Auth/tenant/billing
    ct = deriver.detect_change_type("", "implement auth with jwt tokens")
    assert ct == ChangeType.AUTH_TENANT_BILLING

    # Database migration
    ct = deriver.detect_change_type("", "run database migration for users table")
    assert ct == ChangeType.DATABASE_MIGRATION

    # Deployment
    ct = deriver.detect_change_type("", "deploy to production via ci/cd")
    assert ct == ChangeType.DEPLOYMENT_RELEASE

    # Bug fix
    ct = deriver.detect_change_type("", "fix the login bug")
    assert ct == ChangeType.BUG_FIX_LOCAL

    # Feature
    ct = deriver.detect_change_type("", "implement new user dashboard")
    assert ct == ChangeType.FEATURE_MODULE

    # Rename/format
    ct = deriver.detect_change_type("", "rename variables and format code")
    assert ct == ChangeType.RENAME_TEXT_FORMAT

    print("✓ Change type detection works")


def test_derive_from_request():
    """Test deriving checks from user request."""
    base_dir = Path(__file__).parent.parent.parent
    deriver = AcceptanceDeriver(base_dir)

    request = "Build a REST API with acceptance criteria: must handle 1000 req/s, must use JWT auth"
    checks = deriver.derive_from_request(request)

    assert len(checks) >= 2  # Should find both criteria
    for c in checks:
        assert c.source == CheckSource.USER_REQUEST
        assert c.required == True
    print(f"✓ Derived {len(checks)} checks from request")


def test_select_by_risk():
    """Test risk-adaptive check selection."""
    base_dir = Path(__file__).parent.parent.parent
    deriver = AcceptanceDeriver(base_dir)

    # Bug fix local
    checks = deriver.select_by_risk(ChangeType.BUG_FIX_LOCAL, "fix login bug")
    check_ids = [c.check_id for c in checks]
    assert "reproduction_test" in check_ids
    assert "focused_unit_test" in check_ids
    assert "nearest_regression_test" in check_ids
    print(f"✓ Bug fix checks: {check_ids}")

    # Feature module
    checks = deriver.select_by_risk(ChangeType.FEATURE_MODULE, "add new feature")
    check_ids = [c.check_id for c in checks]
    assert "unit_tests" in check_ids
    assert "integration_tests" in check_ids
    assert "contract_api_tests" in check_ids
    print(f"✓ Feature checks: {check_ids}")

    # Auth change
    checks = deriver.select_by_risk(ChangeType.AUTH_TENANT_BILLING, "add auth")
    check_ids = [c.check_id for c in checks]
    assert "security_tests" in check_ids
    assert "access_control_tests" in check_ids
    print(f"✓ Auth checks: {check_ids}")


def test_check_catalog():
    """Test check catalog completeness."""
    base_dir = Path(__file__).parent.parent.parent
    deriver = AcceptanceDeriver(base_dir)

    catalog = deriver._check_catalog
    assert len(catalog) > 15  # Should have many checks

    # Verify required fields
    for check in catalog.values():
        assert check.check_id
        assert check.name
        assert check.command
        assert check.expected_result
        assert check.source in CheckSource
        assert isinstance(check.required, bool)
    print(f"✓ Check catalog: {len(catalog)} checks")


def test_check_runner_pass():
    """Test running a passing check."""
    base_dir = Path(__file__).parent.parent.parent
    runner = CheckRunner(base_dir)

    check = AcceptanceCheck(
        check_id="test_pass",
        name="Test Pass",
        description="Echo test",
        source=CheckSource.HEURISTIC,
        change_types=[ChangeType.UNKNOWN],
        command="echo 'hello'",
        expected_result="hello",
    )

    result = runner.run_check(check, "task-1", "abc123")
    assert result.status == CheckStatus.PASS
    assert result.exit_code == 0
    assert result.task_id == "task-1"
    assert result.repo_commit == "abc123"
    print("✓ Check runner PASS works")


def test_check_runner_fail():
    """Test running a failing check."""
    base_dir = Path(__file__).parent.parent.parent
    runner = CheckRunner(base_dir)

    check = AcceptanceCheck(
        check_id="test_fail",
        name="Test Fail",
        description="Exit with error",
        source=CheckSource.HEURISTIC,
        change_types=[ChangeType.UNKNOWN],
        command="exit 1",
        expected_result="success",
    )

    result = runner.run_check(check, "task-1")
    assert result.status == CheckStatus.FAIL
    assert result.exit_code == 1
    assert result.error_signature
    print("✓ Check runner FAIL works")


def test_check_runner_blocked():
    """Test blocked check (command not found)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        runner = CheckRunner(base_dir)

        check = AcceptanceCheck(
            check_id="test_blocked",
            name="Test Blocked",
            description="Non-existent command",
            source=CheckSource.HEURISTIC,
            change_types=[ChangeType.UNKNOWN],
            command="nonexistent_command_xyz_123",
            expected_result="success",
        )

        result = runner.run_check(check, "task-1")
        assert result.status == CheckStatus.BLOCKED
        print("✓ Check runner BLOCKED works")


def test_run_checks_batch():
    """Test running multiple checks."""
    base_dir = Path(__file__).parent.parent.parent
    runner = CheckRunner(base_dir)

    checks = [
        AcceptanceCheck(
            check_id=f"batch_{i}",
            name=f"Batch {i}",
            description="Echo test",
            source=CheckSource.HEURISTIC,
            change_types=[ChangeType.UNKNOWN],
            command="echo 'test'",
            expected_result="test",
        )
        for i in range(3)
    ]

    results = runner.run_checks(checks, "task-batch")
    assert len(results) == 3
    assert all(r.status == CheckStatus.PASS for r in results)
    print("✓ Batch check running works")


def test_acceptance_check_structure():
    """Test AcceptanceCheck structure."""
    check = AcceptanceCheck(
        check_id="test_1",
        name="Test Check",
        description="Description",
        source=CheckSource.USER_REQUEST,
        change_types=[ChangeType.BUG_FIX_LOCAL],
        command="python3 -m pytest",
        expected_result="All tests pass",
        working_dir=".",
        timeout_seconds=60,
        required=True,
        tags=["test", "regression"],
    )

    assert check.check_id == "test_1"
    assert check.required == True
    assert "regression" in check.tags
    print("✓ AcceptanceCheck structure valid")


if __name__ == "__main__":
    test_change_type_detection()
    test_derive_from_request()
    test_select_by_risk()
    test_check_catalog()
    test_check_runner_pass()
    test_check_runner_fail()
    test_check_runner_blocked()
    test_run_checks_batch()
    test_acceptance_check_structure()
    print("\n✅ All quality_checks tests passed!")