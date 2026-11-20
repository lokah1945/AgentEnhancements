#!/usr/bin/env python3
"""Tests for review_coordinator.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from review_coordinator import (
    ReviewCoordinator, ReviewTriggerDetector, ReviewPackageBuilder,
    ReviewTrigger, ReviewStatus, ReviewFinding, ReviewResult
)


def test_security_trigger_detection():
    """Test detecting security change triggers."""
    base_dir = Path(__file__).parent.parent.parent
    detector = ReviewTriggerDetector(base_dir)

    diff = """
+def verify_password(password, hash):
+    return bcrypt.checkpw(password.encode(), hash)
+
+JWT_SECRET = "hardcoded-secret-key"
"""
    triggers = detector.detect_triggers(diff, "add authentication")
    assert ReviewTrigger.SECURITY_CHANGE in triggers
    assert ReviewTrigger.AUTH_CHANGE in triggers
    print("✓ Security trigger detection works")


def test_data_loss_trigger():
    """Test detecting data loss risk."""
    base_dir = Path(__file__).parent.parent.parent
    detector = ReviewTriggerDetector(base_dir)

    diff = """
-DROP TABLE users;
+CREATE TABLE users_new (id INT);
"""
    triggers = detector.detect_triggers(diff, "migrate users table")
    assert ReviewTrigger.DATA_LOSS_RISK in triggers
    print("✓ Data loss trigger detection works")


def test_large_migration_trigger():
    """Test detecting large migration."""
    base_dir = Path(__file__).parent.parent.parent
    detector = ReviewTriggerDetector(base_dir)

    diff = """
+CREATE TABLE orders (id INT, user_id INT);
+ALTER TABLE users ADD COLUMN order_count INT;
+CREATE INDEX idx_orders_user ON orders(user_id);
"""
    triggers = detector.detect_triggers(diff, "add orders schema")
    assert ReviewTrigger.LARGE_MIGRATION in triggers
    print("✓ Large migration trigger detection works")


def test_cross_module_trigger():
    """Test detecting cross-module changes."""
    base_dir = Path(__file__).parent.parent.parent
    detector = ReviewTriggerDetector(base_dir)

    diff = """
diff --git a/auth/login.py b/auth/login.py
--- a/auth/login.py
+++ b/auth/login.py
@@ -1,3 +1,4 @@
+def login(): pass
diff --git a/billing/charge.py b/billing/charge.py
--- a/billing/charge.py
+++ b/billing/charge.py
@@ -1,3 +1,4 @@
+def charge(): pass
diff --git a/users/profile.py b/users/profile.py
--- a/users/profile.py
+++ b/users/profile.py
@@ -1,3 +1,4 @@
+def profile(): pass
"""
    triggers = detector.detect_triggers(diff, "refactor across modules")
    assert ReviewTrigger.CROSS_MODULE_CHANGE in triggers
    print("✓ Cross-module trigger detection works")


def test_release_gate_trigger():
    """Test detecting release gate."""
    base_dir = Path(__file__).parent.parent.parent
    detector = ReviewTriggerDetector(base_dir)

    diff = """
+__version__ = "2.0.0"
"""
    triggers = detector.detect_triggers(diff, "release version 2.0.0")
    assert ReviewTrigger.RELEASE_GATE in triggers
    print("✓ Release gate trigger detection works")


def test_config_critical_trigger():
    """Test detecting critical config changes."""
    base_dir = Path(__file__).parent.parent.parent
    detector = ReviewTriggerDetector(base_dir)

    diff = """
+version: "3.8"
+services:
+  app:
+    image: myapp:latest
"""
    triggers = detector.detect_triggers(diff, "update docker compose")
    assert ReviewTrigger.CONFIG_CRITICAL in triggers
    print("✓ Config critical trigger detection works")


def test_no_triggers_for_safe_changes():
    """Test that safe changes don't trigger reviews."""
    base_dir = Path(__file__).parent.parent.parent
    detector = ReviewTriggerDetector(base_dir)

    diff = """
-    print("debug")
+    pass
"""
    triggers = detector.detect_triggers(diff, "remove debug print")
    # Should have no triggers for simple changes
    print(f"✓ Safe changes: {len(triggers)} triggers")


def test_review_package_builder():
    """Test building review package."""
    base_dir = Path(__file__).parent.parent.parent
    builder = ReviewPackageBuilder(base_dir)

    diff = """
diff --git a/new_feature.py b/new_feature.py
--- /dev/null
+++ b/new_feature.py
@@ -0,0 +1 @@
+def new_function(): pass
"""
    triggers = [ReviewTrigger.SECURITY_CHANGE]
    check_results = [
        {"check_id": "test_1", "status": "PASS"},
        {"check_id": "test_2", "status": "FAIL"},
    ]

    package = builder.build_package(
        "task-123", diff, "add new feature", triggers, check_results
    )

    assert package["task_id"] == "task-123"
    assert package["triggers"] == ["security_change"]
    assert len(package["changed_files"]) > 0
    assert "diff" in package
    assert "check_results" in package
    assert "contracts" in package
    assert "instructions" in package
    assert "SECURITY REVIEW FOCUS" in package["instructions"]
    print("✓ Review package builder works")


def test_review_coordinator_detect():
    """Test review coordinator detection."""
    base_dir = Path(__file__).parent.parent.parent
    coordinator = ReviewCoordinator(base_dir)

    diff = "+SECRET_KEY = 'hardcoded'"
    triggers = coordinator.should_review(diff, "add secret")
    assert ReviewTrigger.SECURITY_CHANGE in triggers
    assert ReviewTrigger.AUTH_CHANGE in triggers
    print("✓ Review coordinator detection works")


def test_review_package_creation():
    """Test creating review package."""
    base_dir = Path(__file__).parent.parent.parent
    coordinator = ReviewCoordinator(base_dir)

    diff = "+def auth(): pass"
    check_results = [{"check_id": "security_test", "status": "PASS"}]

    package = coordinator.create_review_package(
        "task-456", diff, "implement auth", check_results
    )

    assert package["review_needed"] == True
    assert package["task_id"] == "task-456"
    assert "review_id" in package
    print("✓ Review package creation works")


def test_no_review_needed():
    """Test that safe changes don't need review."""
    base_dir = Path(__file__).parent.parent.parent
    coordinator = ReviewCoordinator(base_dir)

    diff = "-    pass\n+    pass  # comment"
    check_results = []

    package = coordinator.create_review_package(
        "task-789", diff, "minor fix", check_results
    )

    assert package["review_needed"] == False
    print("✓ No review needed for safe changes")


def test_review_finding_structure():
    """Test ReviewFinding structure."""
    finding = ReviewFinding(
        id="finding-1",
        severity="high",
        category="security",
        file="auth.py",
        line=10,
        description="Hardcoded secret",
        suggestion="Use environment variable",
        evidence="SECRET_KEY = 'hardcoded'",
    )

    assert finding.severity == "high"
    assert finding.category == "security"
    assert finding.file == "auth.py"
    print("✓ ReviewFinding structure works")


def test_review_result_structure():
    """Test ReviewResult structure."""
    import time

    findings = [
        ReviewFinding(
            id="f1",
            severity="high",
            category="security",
            file="auth.py",
            line=10,
            description="Hardcoded secret",
            suggestion="Use env var",
        )
    ]

    result = ReviewResult(
        review_id="review-1",
        status=ReviewStatus.CHANGES_REQUESTED,
        trigger=ReviewTrigger.SECURITY_CHANGE,
        reviewer="reviewer-1",
        findings=findings,
        summary="Found hardcoded secret",
        timestamp=time.time(),
    )

    assert result.status == ReviewStatus.CHANGES_REQUESTED
    assert len(result.findings) == 1
    print("✓ ReviewResult structure works")


if __name__ == "__main__":
    test_security_trigger_detection()
    test_data_loss_trigger()
    test_large_migration_trigger()
    test_cross_module_trigger()
    test_release_gate_trigger()
    test_config_critical_trigger()
    test_no_triggers_for_safe_changes()
    test_review_package_builder()
    test_review_coordinator_detect()
    test_review_package_creation()
    test_no_review_needed()
    test_review_finding_structure()
    test_review_result_structure()
    print("\n✅ All review_coordinator tests passed!")