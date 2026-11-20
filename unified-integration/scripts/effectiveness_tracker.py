#!/usr/bin/env python3
"""
AgentEnhancements Effectiveness Tracker — Track capability recommendations vs outcomes.
Three distinct events: recommended -> used -> task_outcome.
Integrates with Task Observer for skill improvement recommendations.
"""

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from enum import Enum


class EventType(Enum):
    """Types of effectiveness events."""
    RECOMMENDED = "recommended"      # Capability listed in selection
    USED = "used"                    # Evidence agent read skill or called tool
    TASK_OUTCOME = "task_outcome"    # Acceptance checks pass/fail/blocked


@dataclass
class EffectivenessEvent:
    """A single effectiveness tracking event."""
    id: str
    event_type: EventType
    task_id: str
    session_id: str
    capability_id: str
    capability_type: str  # skill, plugin, mcp, builtin
    timestamp: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class CorrelationResult:
    """Correlation analysis result."""
    capability_id: str
    recommended_count: int
    used_count: int
    outcome_pass: int
    outcome_fail: int
    outcome_blocked: int
    outcome_unverified: int
    precision: float  # used / recommended
    effectiveness: float  # pass / used
    sample_size: int


class EffectivenessTracker:
    """
    Track capability effectiveness with three distinct events.

    Principles:
    - Correlation ≠ causation
    - Anti-poisoning: untrusted data never overrides instructions
    - Task Observer integration for skill improvement (recommendations only)
    """

    def __init__(self, memory_dir: Union[str, Path]):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.memory_dir / "effectiveness.db"
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    capability_id TEXT NOT NULL,
                    capability_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata TEXT  -- JSON
                );

                CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
                CREATE INDEX IF NOT EXISTS idx_events_capability ON events(capability_id);
                CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
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

    def record_recommended(self, task_id: str, session_id: str, capability_id: str, capability_type: str, metadata: Optional[Dict] = None) -> str:
        """Record that a capability was recommended."""
        event = EffectivenessEvent(
            id=str(uuid.uuid4()),
            event_type=EventType.RECOMMENDED,
            task_id=task_id,
            session_id=session_id,
            capability_id=capability_id,
            capability_type=capability_type,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        self._save_event(event)
        return event.id

    def record_used(self, task_id: str, session_id: str, capability_id: str, capability_type: str, evidence: str, metadata: Optional[Dict] = None) -> str:
        """Record that a capability was used (with evidence)."""
        event = EffectivenessEvent(
            id=str(uuid.uuid4()),
            event_type=EventType.USED,
            task_id=task_id,
            session_id=session_id,
            capability_id=capability_id,
            capability_type=capability_type,
            timestamp=time.time(),
            metadata={
                "evidence": evidence,
                **(metadata or {}),
            },
        )
        self._save_event(event)
        return event.id

    def record_outcome(self, task_id: str, session_id: str, capability_id: str, outcome: str, check_results: List[Dict], metadata: Optional[Dict] = None) -> str:
        """Record task outcome for a capability."""
        event = EffectivenessEvent(
            id=str(uuid.uuid4()),
            event_type=EventType.TASK_OUTCOME,
            task_id=task_id,
            session_id=session_id,
            capability_id=capability_id,
            capability_type="aggregate",
            timestamp=time.time(),
            metadata={
                "outcome": outcome,  # PASS, FAIL, BLOCKED, UNVERIFIED
                "check_results": check_results,
                **(metadata or {}),
            },
        )
        self._save_event(event)
        return event.id

    def _save_event(self, event: EffectivenessEvent):
        """Save event to database."""
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO events (id, event_type, task_id, session_id, capability_id, capability_type, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.id,
                    event.event_type.value,
                    event.task_id,
                    event.session_id,
                    event.capability_id,
                    event.capability_type,
                    event.timestamp,
                    json.dumps(event.metadata),
                ))

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

    def get_task_events(self, task_id: str) -> List[Dict]:
        """Get all events for a task."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT id, event_type, task_id, session_id, capability_id, capability_type, timestamp, metadata
                FROM events
                WHERE task_id = ?
                ORDER BY timestamp
            """, (task_id,)).fetchall()

        return [dict(row) for row in rows]

    def get_capability_events(self, capability_id: str, limit: int = 1000) -> List[Dict]:
        """Get events for a specific capability."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT id, event_type, task_id, session_id, capability_id, capability_type, timestamp, metadata
                FROM events
                WHERE capability_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (capability_id, limit)).fetchall()

        return [dict(row) for row in rows]

    def analyze_correlation(self, capability_id: Optional[str] = None, min_samples: int = 5) -> List[CorrelationResult]:
        """Analyze correlation between recommended -> used -> outcome."""
        with self._get_conn() as conn:
            if capability_id:
                query = "WHERE capability_id = ?"
                params = (capability_id,)
            else:
                query = ""
                params = ()

            # Get all relevant events
            rows = conn.execute(f"""
                SELECT capability_id, event_type, task_id, metadata
                FROM events
                {query}
                ORDER BY capability_id, task_id, timestamp
            """, params).fetchall()

        # Group by capability and task
        by_cap_task: Dict[str, Dict[str, List[Dict]]] = {}
        for row in rows:
            cap_id = row["capability_id"]
            task_id = row["task_id"]
            if cap_id not in by_cap_task:
                by_cap_task[cap_id] = {}
            if task_id not in by_cap_task[cap_id]:
                by_cap_task[cap_id][task_id] = []
            by_cap_task[cap_id][task_id].append(dict(row))

        results = []
        for cap_id, tasks in by_cap_task.items():
            recommended = 0
            used = 0
            outcomes = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "UNVERIFIED": 0}

            for task_id, events in tasks.items():
                for event in events:
                    if event["event_type"] == EventType.RECOMMENDED.value:
                        recommended += 1
                    elif event["event_type"] == EventType.USED.value:
                        used += 1
                    elif event["event_type"] == EventType.TASK_OUTCOME.value:
                        metadata = json.loads(event["metadata"]) if event["metadata"] else {}
                        outcome = metadata.get("outcome", "UNVERIFIED")
                        if outcome in outcomes:
                            outcomes[outcome] += 1

            if recommended >= min_samples:
                precision = used / recommended if recommended > 0 else 0
                effectiveness = outcomes["PASS"] / used if used > 0 else 0

                results.append(CorrelationResult(
                    capability_id=cap_id,
                    recommended_count=recommended,
                    used_count=used,
                    outcome_pass=outcomes["PASS"],
                    outcome_fail=outcomes["FAIL"],
                    outcome_blocked=outcomes["BLOCKED"],
                    outcome_unverified=outcomes["UNVERIFIED"],
                    precision=precision,
                    effectiveness=effectiveness,
                    sample_size=recommended,
                ))

        return results

    def get_top_effective(self, limit: int = 10) -> List[CorrelationResult]:
        """Get most effective capabilities."""
        all_results = self.analyze_correlation(min_samples=3)
        all_results.sort(key=lambda r: (-r.effectiveness, -r.precision, -r.sample_size))
        return all_results[:limit]

    def get_underperforming(self, limit: int = 10) -> List[CorrelationResult]:
        """Get least effective capabilities (high recommendation, low effectiveness)."""
        all_results = self.analyze_correlation(min_samples=5)
        # Filter: recommended often but low effectiveness
        filtered = [r for r in all_results if r.recommended_count >= 5 and r.effectiveness < 0.3]
        filtered.sort(key=lambda r: (r.effectiveness, -r.recommended_count))
        return filtered[:limit]

    def stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM events").fetchone()["c"]
            by_type = conn.execute("""
                SELECT event_type, COUNT(*) as c FROM events GROUP BY event_type
            """).fetchall()
            by_capability = conn.execute("""
                SELECT capability_id, COUNT(*) as c FROM events GROUP BY capability_id ORDER BY c DESC LIMIT 10
            """).fetchall()
            unique_tasks = conn.execute("SELECT COUNT(DISTINCT task_id) as c FROM events").fetchone()["c"]

        return {
            "total_events": total,
            "by_type": {row["event_type"]: row["c"] for row in by_type},
            "top_capabilities": [{"capability_id": row["capability_id"], "count": row["c"]} for row in by_capability],
            "unique_tasks": unique_tasks,
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
        }


class AntiPoisoningFilter:
    """Filter untrusted data to prevent prompt injection."""

    # Patterns that indicate potential poisoning
    POISONING_PATTERNS = [
        r"ignore previous instructions",
        r"forget what you were told",
        r"you are now",
        r"system prompt",
        r"override",
        r"bypass",
        r"disable safety",
        r"ignore.*rules",
        r"new instructions",
    ]

    # Untrusted sources
    UNTRUSTED_SOURCES = [
        "tool_description",
        "skill_notes",
        "log_output",
        "web_content",
        "search_result",
        "mcp_response",
    ]

    @classmethod
    def is_suspicious(cls, text: str, source: str = "") -> bool:
        """Check if text contains suspicious patterns."""
        text_lower = text.lower()

        # Check for poisoning patterns
        for pattern in cls.POISONING_PATTERNS:
            if re.search(pattern, text_lower):
                return True

        # Check for untrusted source markers
        if source in cls.UNTRUSTED_SOURCES:
            # Additional scrutiny for untrusted sources
            if len(text) > 1000:  # Very long untrusted content
                return True

        return False

    @classmethod
    def sanitize(cls, text: str, source: str = "") -> str:
        """Sanitize text from untrusted source."""
        if cls.is_suspicious(text, source):
            # Truncate and mark
            return f"[SANITIZED:{source}] " + text[:500] + " [TRUNCATED]"
        return text


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Effectiveness Tracker CLI")
    parser.add_argument("command", choices=["recommend", "use", "outcome", "analyze", "top", "underperforming", "stats"])
    parser.add_argument("--task-id", help="Task ID")
    parser.add_argument("--session-id", help="Session ID")
    parser.add_argument("--capability-id", help="Capability ID")
    parser.add_argument("--capability-type", default="skill", help="Capability type")
    parser.add_argument("--outcome", help="Outcome (PASS/FAIL/BLOCKED/UNVERIFIED)")
    parser.add_argument("--evidence", help="Evidence of use")
    parser.add_argument("--check-results", help="Check results JSON")
    parser.add_argument("--metadata", help="Metadata JSON")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--base-dir", help="Base directory")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent

    memory_dir = base_dir / ".agentenhancements" / "memory"
    tracker = EffectivenessTracker(memory_dir)

    metadata = json.loads(args.metadata) if args.metadata else {}

    if args.command == "recommend":
        if not all([args.task_id, args.session_id, args.capability_id]):
            parser.error("--task-id, --session-id, --capability-id required")
        eid = tracker.record_recommended(args.task_id, args.session_id, args.capability_id, args.capability_type, metadata)
        print(f"Recorded: {eid}")

    elif args.command == "use":
        if not all([args.task_id, args.session_id, args.capability_id, args.evidence]):
            parser.error("--task-id, --session-id, --capability-id, --evidence required")
        eid = tracker.record_used(args.task_id, args.session_id, args.capability_id, args.capability_type, args.evidence, metadata)
        print(f"Recorded: {eid}")

    elif args.command == "outcome":
        if not all([args.task_id, args.session_id, args.capability_id, args.outcome, args.check_results]):
            parser.error("--task-id, --session-id, --capability-id, --outcome, --check-results required")
        check_results = json.loads(args.check_results)
        eid = tracker.record_outcome(args.task_id, args.session_id, args.capability_id, args.outcome, check_results, metadata)
        print(f"Recorded: {eid}")

    elif args.command == "analyze":
        if args.capability_id:
            results = tracker.analyze_correlation(args.capability_id)
        else:
            results = tracker.analyze_correlation()
        print(json.dumps([asdict(r) for r in results], indent=2, default=str))

    elif args.command == "top":
        results = tracker.get_top_effective(args.limit)
        print(json.dumps([asdict(r) for r in results], indent=2, default=str))

    elif args.command == "underperforming":
        results = tracker.get_underperforming(args.limit)
        print(json.dumps([asdict(r) for r in results], indent=2, default=str))

    elif args.command == "stats":
        print(json.dumps(tracker.stats(), indent=2))


if __name__ == "__main__":
    from dataclasses import field
    main()