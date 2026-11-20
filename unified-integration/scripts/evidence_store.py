#!/usr/bin/env python3
"""
AgentEnhancements Evidence Store — Persistent storage for check results.
Integrates with memory system for cross-session evidence tracking.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from quality_checks import CheckResult, CheckStatus


@dataclass
class EvidenceEntry:
    """An evidence entry linking check results to tasks."""
    id: int
    task_id: str
    check_id: str
    status: str
    check_result: Dict  # Full CheckResult as dict
    created_at: float
    repo_commit: str
    tags: List[str]


class EvidenceStore:
    """
    Store and query check evidence with full provenance.

    Features:
    - SQLite backend with parameterized queries
    - TTL-based cleanup
    - Full evidence retrieval for audit
    - Integration with memory system
    """

    TTL_DAYS = 30  # Keep evidence for 30 days

    def __init__(self, memory_dir: Union[str, Path]):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.memory_dir / "evidence.db"
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    check_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    check_result TEXT NOT NULL,  -- JSON
                    created_at REAL NOT NULL,
                    repo_commit TEXT,
                    tags TEXT,  -- JSON array
                    UNIQUE(task_id, check_id, created_at)
                );

                CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence(task_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_check ON evidence(check_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_status ON evidence(status);
                CREATE INDEX IF NOT EXISTS idx_evidence_created ON evidence(created_at);
                CREATE INDEX IF NOT EXISTS idx_evidence_commit ON evidence(repo_commit);
            """)

    @contextmanager
    def _get_conn(self):
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_result(self, result: CheckResult, tags: Optional[List[str]] = None) -> int:
        """Save a check result as evidence."""
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute("""
                    INSERT INTO evidence
                    (task_id, check_id, status, check_result, created_at, repo_commit, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.task_id,
                    result.check_id,
                    result.status.value,
                    json.dumps(asdict(result), default=str),
                    time.time(),
                    result.repo_commit,
                    json.dumps(tags or []),
                ))
                return cursor.lastrowid

    def save_results(self, results: List[CheckResult], tags: Optional[List[str]] = None) -> List[int]:
        """Save multiple check results."""
        return [self.save_result(r, tags) for r in results]

    def get_evidence_for_task(self, task_id: str) -> List[Dict]:
        """Get all evidence for a task."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT id, task_id, check_id, status, check_result, created_at, repo_commit, tags
                FROM evidence
                WHERE task_id = ?
                ORDER BY created_at DESC
            """, (task_id,)).fetchall()

        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "task_id": row["task_id"],
                "check_id": row["check_id"],
                "status": row["status"],
                "check_result": json.loads(row["check_result"]),
                "created_at": row["created_at"],
                "repo_commit": row["repo_commit"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
            })
        return results

    def get_evidence_for_check(self, check_id: str, limit: int = 100) -> List[Dict]:
        """Get recent evidence for a specific check."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT id, task_id, check_id, status, check_result, created_at, repo_commit, tags
                FROM evidence
                WHERE check_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (check_id, limit)).fetchall()

        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "task_id": row["task_id"],
                "check_id": row["check_id"],
                "status": row["status"],
                "check_result": json.loads(row["check_result"]),
                "created_at": row["created_at"],
                "repo_commit": row["repo_commit"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
            })
        return results

    def get_task_summary(self, task_id: str) -> Dict:
        """Get summary of check results for a task."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM evidence
                WHERE task_id = ?
                GROUP BY status
            """, (task_id,)).fetchall()

        summary = {row["status"]: row["count"] for row in rows}
        total = sum(summary.values())
        passed = summary.get(CheckStatus.PASS.value, 0)
        failed = summary.get(CheckStatus.FAIL.value, 0)
        blocked = summary.get(CheckStatus.BLOCKED.value, 0)
        not_run = summary.get(CheckStatus.NOT_RUN.value, 0)

        return {
            "task_id": task_id,
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "not_run": not_run,
            "success_rate": passed / total if total > 0 else 0.0,
            "by_status": summary,
        }

    def get_repo_commit_summary(self, repo_commit: str) -> Dict:
        """Get summary of checks for a commit."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM evidence
                WHERE repo_commit = ?
                GROUP BY status
            """, (repo_commit,)).fetchall()

        return {row["status"]: row["count"] for row in rows}

    def cleanup_old_evidence(self, max_age_days: int = None) -> int:
        """Remove evidence older than max_age_days."""
        if max_age_days is None:
            max_age_days = self.TTL_DAYS

        cutoff = time.time() - (max_age_days * 24 * 3600)
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM evidence WHERE created_at < ?",
                    (cutoff,)
                )
                return cursor.rowcount

    def stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM evidence").fetchone()["c"]
            by_status = conn.execute("""
                SELECT status, COUNT(*) as c FROM evidence GROUP BY status
            """).fetchall()
            by_task = conn.execute("""
                SELECT task_id, COUNT(*) as c FROM evidence GROUP BY task_id ORDER BY c DESC LIMIT 10
            """).fetchall()
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "total_entries": total,
            "by_status": {row["status"]: row["c"] for row in by_status},
            "top_tasks": [{"task_id": row["task_id"], "count": row["c"]} for row in by_task],
            "db_size_bytes": db_size,
            "db_path": str(self.db_path),
        }


class EvidenceReporter:
    """Format evidence for human consumption."""

    @staticmethod
    def format_check_result(result: CheckResult) -> str:
        """Format a single check result."""
        status_icon = {
            CheckStatus.PASS: "✅",
            CheckStatus.FAIL: "❌",
            CheckStatus.NOT_RUN: "⏸️",
            CheckStatus.BLOCKED: "🚫",
            CheckStatus.NOT_APPLICABLE: "➖",
            CheckStatus.UNVERIFIED: "❓",
        }
        icon = status_icon.get(result.status, "❓")

        lines = [
            f"{icon} {result.check_id}: {result.status.value}",
            f"  Command: {result.command}",
            f"  Duration: {result.duration_ms}ms",
            f"  Timestamp: {result.timestamp}",
        ]

        if result.status == CheckStatus.FAIL:
            lines.append(f"  Exit code: {result.exit_code}")
            if result.error_signature:
                lines.append(f"  Error: {result.error_signature}")
            elif result.stderr:
                lines.append(f"  Stderr: {result.stderr[:200]}")

        return "\n".join(lines)

    @staticmethod
    def format_task_summary(summary: Dict) -> str:
        """Format task summary."""
        lines = [
            f"Task: {summary['task_id']}",
            f"Total checks: {summary['total_checks']}",
            f"Passed: {summary['passed']} | Failed: {summary['failed']} | Blocked: {summary['blocked']} | Not run: {summary['not_run']}",
            f"Success rate: {summary['success_rate']:.1%}",
        ]
        return "\n".join(lines)

    @staticmethod
    def generate_report(task_id: str, evidence_store: EvidenceStore) -> str:
        """Generate full report for a task."""
        summary = evidence_store.get_task_summary(task_id)
        evidence = evidence_store.get_evidence_for_task(task_id)

        lines = [
            "=" * 60,
            "EVIDENCE REPORT",
            "=" * 60,
            EvidenceReporter.format_task_summary(summary),
            "",
            "DETAILED RESULTS:",
            "-" * 60,
        ]

        for ev in evidence:
            cr = ev["check_result"]
            result = CheckResult(**cr)
            lines.append(EvidenceReporter.format_check_result(result))
            lines.append("")

        return "\n".join(lines)


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Evidence Store CLI")
    parser.add_argument("command", choices=["save", "task", "check", "summary", "report", "cleanup", "stats"])
    parser.add_argument("--task-id", help="Task ID")
    parser.add_argument("--check-id", help="Check ID")
    parser.add_argument("--result", help="CheckResult JSON")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--repo-commit", help="Repo commit")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-dir", help="Base directory")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent

    memory_dir = base_dir / ".agentenhancements" / "memory"
    store = EvidenceStore(memory_dir)

    if args.command == "save":
        if not args.result:
            parser.error("--result required")
        result = CheckResult(**json.loads(args.result))
        tags = args.tags.split(",") if args.tags else None
        eid = store.save_result(result, tags)
        print(f"Saved evidence ID: {eid}")

    elif args.command == "task":
        if not args.task_id:
            parser.error("--task-id required")
        evidence = store.get_evidence_for_task(args.task_id)
        print(json.dumps(evidence, indent=2, default=str))

    elif args.command == "check":
        if not args.check_id:
            parser.error("--check-id required")
        evidence = store.get_evidence_for_check(args.check_id, args.limit)
        print(json.dumps(evidence, indent=2, default=str))

    elif args.command == "summary":
        if not args.task_id:
            parser.error("--task-id required")
        summary = store.get_task_summary(args.task_id)
        print(json.dumps(summary, indent=2, default=str))

    elif args.command == "report":
        if not args.task_id:
            parser.error("--task-id required")
        report = EvidenceReporter.generate_report(args.task_id, store)
        print(report)

    elif args.command == "cleanup":
        count = store.cleanup_old_evidence(args.days)
        print(f"Cleaned up {count} old evidence entries")

    elif args.command == "stats":
        print(json.dumps(store.stats(), indent=2))


if __name__ == "__main__":
    main()