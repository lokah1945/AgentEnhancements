#!/usr/bin/env python3
"""Tests for evidence_store.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from evidence_store import EvidenceStore, EvidenceReporter, CheckResult, CheckStatus


def test_save_result():
    """Test saving check result as evidence."""
    base_dir = Path(__file__).parent.parent.parent
    memory_dir = base_dir / ".agentenhancements" / "memory"
    store = EvidenceStore(memory_dir)

    result = CheckResult(
        check_id="test_1",
        status=CheckStatus.PASS,
        command="echo test",
        exit_code=0,
        stdout="test",
        stderr="",
        duration_ms=100,
        timestamp="2024-01-01T00:00:00Z",
        scope=".",
        repo_commit="abc123",
        task_id="task-1",
        error_signature="",
    )

    eid = store.save_result(result, tags=["test", "regression"])
    assert eid > 0
    print("✓ Save result works")


def test_save_results_batch():
    """Test saving multiple results."""
    base_dir = Path(__file__).parent.parent.parent
    memory_dir = base_dir / ".agentenhancements" / "memory"
    store = EvidenceStore(memory_dir)

    results = [
        CheckResult(
            check_id=f"batch_{i}",
            status=CheckStatus.PASS,
            command="echo test",
            exit_code=0,
            stdout="test",
            stderr="",
            duration_ms=50,
            timestamp="2024-01-01T00:00:00Z",
            scope=".",
            repo_commit="abc123",
            task_id="task-batch",
            error_signature="",
        )
        for i in range(3)
    ]

    ids = store.save_results(results, tags=["batch"])
    assert len(ids) == 3
    assert all(isinstance(eid, int) for eid in ids)
    print("✓ Batch save works")


def test_get_evidence_for_task():
    """Test retrieving evidence for a task."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        store = EvidenceStore(memory_dir)

        result = CheckResult(
            check_id="task_test",
            status=CheckStatus.PASS,
            command="echo test",
            exit_code=0,
            stdout="test",
            stderr="",
            duration_ms=100,
            timestamp="2024-01-01T00:00:00Z",
            scope=".",
            repo_commit="abc123",
            task_id="task-evidence",
            error_signature="",
        )

        store.save_result(result)
        evidence = store.get_evidence_for_task("task-evidence")

        assert len(evidence) == 1
        assert evidence[0]["check_id"] == "task_test"
        assert evidence[0]["task_id"] == "task-evidence"
        print("✓ Get evidence for task works")


def test_get_evidence_for_check():
    """Test retrieving evidence for a check."""
    base_dir = Path(__file__).parent.parent.parent
    memory_dir = base_dir / ".agentenhancements" / "memory"
    store = EvidenceStore(memory_dir)

    result = CheckResult(
        check_id="check_specific",
        status=CheckStatus.PASS,
        command="echo test",
        exit_code=0,
        stdout="test",
        stderr="",
        duration_ms=100,
        timestamp="2024-01-01T00:00:00Z",
        scope=".",
        repo_commit="abc123",
        task_id="task-1",
        error_signature="",
    )

    store.save_result(result)
    evidence = store.get_evidence_for_check("check_specific")

    assert len(evidence) >= 1
    assert evidence[0]["check_id"] == "check_specific"
    print("✓ Get evidence for check works")


def test_task_summary():
    """Test task summary statistics."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        store = EvidenceStore(memory_dir)

        # Save mixed results
        for status in [CheckStatus.PASS, CheckStatus.PASS, CheckStatus.FAIL, CheckStatus.BLOCKED]:
            result = CheckResult(
                check_id=f"summary_{status.value}",
                status=status,
                command="test",
                exit_code=0 if status == CheckStatus.PASS else 1,
                stdout="",
                stderr="error" if status != CheckStatus.PASS else "",
                duration_ms=100,
                timestamp="2024-01-01T00:00:00Z",
                scope=".",
                repo_commit="abc123",
                task_id="task-summary",
                error_signature="sig" if status == CheckStatus.FAIL else "",
            )
            store.save_result(result)

        summary = store.get_task_summary("task-summary")

        assert summary["total_checks"] == 4
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["blocked"] == 1
        assert summary["success_rate"] == 0.5
        print("✓ Task summary works")


def test_repo_commit_summary():
    """Test repo commit summary."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        store = EvidenceStore(memory_dir)

        result = CheckResult(
            check_id="commit_test",
            status=CheckStatus.PASS,
            command="test",
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100,
            timestamp="2024-01-01T00:00:00Z",
            scope=".",
            repo_commit="commit-xyz",
            task_id="task-1",
            error_signature="",
        )

        store.save_result(result)
        summary = store.get_repo_commit_summary("commit-xyz")

        assert summary.get(CheckStatus.PASS.value, 0) >= 1
        print("✓ Repo commit summary works")


def test_cleanup_old_evidence():
    """Test cleanup of old evidence."""
    import tempfile
    tmpdir = tempfile.mkdtemp()
    try:
        memory_dir = Path(tmpdir)
        store = EvidenceStore(memory_dir)

        # Save with old timestamp (manually insert)
        import sqlite3
        db_path = memory_dir / "evidence.db"
        # Ensure table exists by saving a result first
        store.save_result(CheckResult(
            check_id="init", status=CheckStatus.PASS, command="init", exit_code=0,
            stdout="", stderr="", duration_ms=1, timestamp=time.time(),
            scope=".", repo_commit="init", task_id="init", error_signature=""
        ))
        # Now insert old entry (use correct table name 'evidence')
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("""
                INSERT INTO evidence (task_id, check_id, status, check_result, created_at, repo_commit, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("old_task", "old_1", "recommended", "{}", time.time() - 40*24*3600, "init", "[]"))

        # Save new
        result = CheckResult(
            check_id="new_test",
            status=CheckStatus.PASS,
            command="test",
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=100,
            timestamp="2024-01-01T00:00:00Z",
            scope=".",
            repo_commit="abc123",
            task_id="task-new",
            error_signature="",
        )
        store.save_result(result)

        # Cleanup with 30 days
        cleaned = store.cleanup_old_evidence(max_age_days=30)
        assert cleaned >= 1

        # New evidence should remain
        evidence = store.get_evidence_for_task("task-new")
        assert len(evidence) == 1
        print("✓ Cleanup old evidence works")
    finally:
        # Force close any remaining connections
        import gc
        gc.collect()
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_evidence_reporter():
    """Test evidence reporter formatting."""
    result = CheckResult(
        check_id="format_test",
        status=CheckStatus.PASS,
        command="echo test",
        exit_code=0,
        stdout="test",
        stderr="",
        duration_ms=100,
        timestamp="2024-01-01T00:00:00Z",
        scope=".",
        repo_commit="abc123",
        task_id="task-1",
        error_signature="",
    )

    formatted = EvidenceReporter.format_check_result(result)
    assert "✅" in formatted
    assert "format_test" in formatted
    assert "PASS" in formatted
    print("✓ Evidence reporter works")


def test_task_summary_format():
    """Test task summary formatting."""
    summary = {
        "task_id": "task-1",
        "total_checks": 5,
        "passed": 4,
        "failed": 1,
        "blocked": 0,
        "not_run": 0,
        "success_rate": 0.8,
        "by_status": {"PASS": 4, "FAIL": 1},
    }

    formatted = EvidenceReporter.format_task_summary(summary)
    assert "task-1" in formatted
    assert "5" in formatted
    assert "4" in formatted
    # Format is "80.0%" with .1% format
    assert "80.0%" in formatted
    print("✓ Task summary format works")


def test_stats():
    """Test evidence store stats."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        memory_dir = Path(tmpdir)
        store = EvidenceStore(memory_dir)

        stats = store.stats()
        assert "total_entries" in stats
        assert "by_status" in stats
        assert "db_size_bytes" in stats
        print("✓ Stats work")


if __name__ == "__main__":
    import time
    test_save_result()
    test_save_results_batch()
    test_get_evidence_for_task()
    test_get_evidence_for_check()
    test_task_summary()
    test_repo_commit_summary()
    test_cleanup_old_evidence()
    test_evidence_reporter()
    test_task_summary_format()
    test_stats()
    print("\n✅ All evidence_store tests passed!")