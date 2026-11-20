#!/usr/bin/env python3
"""
AgentEnhancements Memory System — SQLite-backed cross-session memory.
Supports parameterized queries, TTL cleanup, multiple memory types.
"""

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from contextlib import contextmanager
import hashlib


@dataclass
class MemoryEntry:
    """A single memory entry."""
    key: str
    value: Dict[str, Any]
    memory_type: str  # session_context, persistent, user_preference, skill_usage
    created_at: float
    updated_at: float
    expires_at: Optional[float] = None
    tags: List[str] = None
    session_id: str = ""
    agent_type: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MemoryManager:
    """
    Thread-safe memory manager with SQLite backend.
    Supports multiple memory types with different TTL policies.
    """

    # TTL policies in seconds
    TTL_POLICIES = {
        "session_context": 7 * 24 * 3600,      # 7 days
        "persistent": None,                     # Never expires
        "user_preference": 365 * 24 * 3600,    # 1 year
        "skill_usage": 30 * 24 * 3600,         # 30 days
        "task_observer": 14 * 24 * 3600,       # 14 days
    }

    def __init__(self, memory_dir: Union[str, Path]):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.memory_dir / "memory.db"
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,  -- JSON
                    memory_type TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    expires_at REAL,
                    tags TEXT,  -- JSON array
                    session_id TEXT,
                    agent_type TEXT,
                    UNIQUE(key, memory_type, session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type);
                CREATE INDEX IF NOT EXISTS idx_session_id ON memories(session_id);
                CREATE INDEX IF NOT EXISTS idx_expires_at ON memories(expires_at);
                CREATE INDEX IF NOT EXISTS idx_key_type_session ON memories(key, memory_type, session_id);
                CREATE INDEX IF NOT EXISTS idx_updated_at ON memories(updated_at);
            """)

    @contextmanager
    def _get_conn(self):
        """Get a database connection with proper configuration."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
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

    def _serialize_value(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def _deserialize_value(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        return json.loads(value)

    def _now(self) -> float:
        return time.time()

    def _compute_expires_at(self, memory_type: str) -> Optional[float]:
        """Compute expiration timestamp based on memory type."""
        ttl = self.TTL_POLICIES.get(memory_type)
        if ttl is None:
            return None
        return self._now() + ttl

    # =========================================================================
    # CORE OPERATIONS
    # =========================================================================
    def save(
        self,
        key: str,
        value: Any,
        memory_type: str = "session_context",
        session_id: str = "",
        agent_type: str = "",
        tags: Optional[List[str]] = None,
        ttl_override: Optional[int] = None
    ) -> bool:
        """
        Save a memory entry. Uses upsert semantics (merge on conflict).
        Returns True if saved successfully.
        """
        if memory_type not in self.TTL_POLICIES:
            raise ValueError(f"Unknown memory_type: {memory_type}")

        now = self._now()
        expires_at = self._compute_expires_at(memory_type)
        if ttl_override is not None:
            expires_at = now + ttl_override

        with self._lock:
            with self._get_conn() as conn:
                # Check if exists
                existing = conn.execute(
                    "SELECT value, created_at FROM memories WHERE key=? AND memory_type=? AND session_id=?",
                    (key, memory_type, session_id)
                ).fetchone()

                if existing:
                    # Merge with existing (preserve created_at)
                    created_at = existing["created_at"]
                    try:
                        old_value = self._deserialize_value(existing["value"])
                        if isinstance(old_value, dict) and isinstance(value, dict):
                            # Deep merge for dicts
                            merged = {**old_value, **value}
                            value = merged
                    except Exception:
                        pass  # Use new value as-is
                else:
                    created_at = now

                conn.execute("""
                    INSERT OR REPLACE INTO memories
                    (key, value, memory_type, created_at, updated_at, expires_at, tags, session_id, agent_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    key,
                    self._serialize_value(value),
                    memory_type,
                    created_at,
                    now,
                    expires_at,
                    json.dumps(tags or []),
                    session_id,
                    agent_type
                ))
        return True

    def load(
        self,
        key: str,
        memory_type: str = "session_context",
        session_id: str = "",
        default: Any = None
    ) -> Any:
        """Load a single memory entry."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM memories WHERE key=? AND memory_type=? AND session_id=?",
                (key, memory_type, session_id)
            ).fetchone()

        if not row:
            return default

        # Check expiration
        if row["expires_at"] and row["expires_at"] < self._now():
            self.delete(key, memory_type, session_id)
            return default

        return self._deserialize_value(row["value"])

    def delete(self, key: str, memory_type: str = "session_context", session_id: str = "") -> bool:
        """Delete a memory entry."""
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM memories WHERE key=? AND memory_type=? AND session_id=?",
                    (key, memory_type, session_id)
                )
                return cursor.rowcount > 0

    def query(
        self,
        memory_type: str = "session_context",
        session_id: str = "",
        key_prefix: str = "",
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "updated_at DESC"
    ) -> List[Dict[str, Any]]:
        """Query memories with filters."""
        with self._get_conn() as conn:
            sql = "SELECT key, value, memory_type, created_at, updated_at, expires_at, tags, session_id, agent_type FROM memories WHERE memory_type=?"
            params = [memory_type]

            if session_id:
                sql += " AND session_id=?"
                params.append(session_id)

            if key_prefix:
                sql += " AND key LIKE ?"
                params.append(f"{key_prefix}%")

            if tags:
                # Tag matching - all tags must be present
                for tag in tags:
                    sql += " AND tags LIKE ?"
                    params.append(f'%"{tag}"%')

            sql += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(sql, params).fetchall()

        results = []
        now = self._now()
        for row in rows:
            if row["expires_at"] and row["expires_at"] < now:
                continue  # Skip expired
            results.append({
                "key": row["key"],
                "data": self._deserialize_value(row["value"]),
                "memory_type": row["memory_type"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "session_id": row["session_id"],
                "agent_type": row["agent_type"],
            })
        return results

    def list_keys(
        self,
        memory_type: str = "session_context",
        session_id: str = "",
        limit: int = 100
    ) -> List[str]:
        """List all keys for a memory type."""
        with self._get_conn() as conn:
            sql = "SELECT DISTINCT key FROM memories WHERE memory_type=?"
            params = [memory_type]
            if session_id:
                sql += " AND session_id=?"
                params.append(session_id)
            sql += " ORDER BY key LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
        return [row["key"] for row in rows]

    # =========================================================================
    # SESSION-SPECIFIC OPERATIONS
    # =========================================================================
    def recall_session(self, session_id: str, max_age_days: int = 7) -> List[Dict[str, Any]]:
        """Recall all memories for a session within max_age_days."""
        cutoff = self._now() - (max_age_days * 24 * 3600)
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT key, value, memory_type, created_at, updated_at, tags
                FROM memories
                WHERE session_id=? AND created_at > ?
                ORDER BY updated_at DESC
            """, (session_id, cutoff)).fetchall()

        results = []
        for row in rows:
            results.append({
                "key": row["key"],
                "data": self._deserialize_value(row["value"]),
                "memory_type": row["memory_type"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
            })
        return results

    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get session summary if exists."""
        return self.load("summary", "session_context", session_id)

    # =========================================================================
    # CLEANUP & MAINTENANCE
    # =========================================================================
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count deleted."""
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
                    (self._now(),)
                )
                return cursor.rowcount

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """Remove all memories from sessions older than max_age_days."""
        cutoff = self._now() - (max_age_days * 24 * 3600)
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM memories WHERE session_id != '' AND created_at < ?",
                    (cutoff,)
                )
                return cursor.rowcount

    def vacuum(self):
        """Vacuum database to reclaim space."""
        with self._get_conn() as conn:
            conn.execute("VACUUM")

    def stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM memories").fetchone()["c"]
            by_type = conn.execute("""
                SELECT memory_type, COUNT(*) as c FROM memories GROUP BY memory_type
            """).fetchall()
            by_session = conn.execute("""
                SELECT session_id, COUNT(*) as c FROM memories WHERE session_id != '' GROUP BY session_id
            """).fetchall()
            expired = conn.execute("""
                SELECT COUNT(*) as c FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (self._now(),)).fetchone()["c"]
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "total_entries": total,
            "expired_entries": expired,
            "by_type": {row["memory_type"]: row["c"] for row in by_type},
            "active_sessions": len(by_session),
            "db_size_bytes": db_size,
            "db_path": str(self.db_path),
        }


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="AgentEnhancements Memory CLI")
    parser.add_argument("command", choices=["save", "load", "delete", "query", "list", "stats", "cleanup", "vacuum"])
    parser.add_argument("--key", help="Memory key")
    parser.add_argument("--value", help="Value to save (JSON)")
    parser.add_argument("--type", default="session_context", choices=["session_context", "persistent", "user_preference", "skill_usage", "task_observer"])
    parser.add_argument("--session", default="", help="Session ID")
    parser.add_argument("--agent", default="", help="Agent type")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--prefix", default="", help="Key prefix for query")
    parser.add_argument("--days", type=int, default=7, help="Max age for recall")

    args = parser.parse_args()

    memory_dir = os.getenv("AGENT_MEMORY_ROOT", ".agentenhancements/memory")
    mgr = MemoryManager(memory_dir)

    if args.command == "save":
        if not args.key:
            parser.error("--key required for save")
        value = json.loads(args.value) if args.value else {}
        tags = args.tags.split(",") if args.tags else None
        mgr.save(args.key, value, args.type, args.session, args.agent, tags)
        print(f"Saved: {args.key}")

    elif args.command == "load":
        if not args.key:
            parser.error("--key required for load")
        result = mgr.load(args.key, args.type, args.session)
        print(json.dumps(result, indent=2) if result else "Not found")

    elif args.command == "delete":
        if not args.key:
            parser.error("--key required for delete")
        mgr.delete(args.key, args.type, args.session)
        print(f"Deleted: {args.key}")

    elif args.command == "query":
        tags = args.tags.split(",") if args.tags else None
        results = mgr.query(args.type, args.session, args.prefix, tags, args.limit)
        for r in results:
            print(f"{r['key']} [{r['memory_type']}] {json.dumps(r['data'])[:80]}")

    elif args.command == "list":
        keys = mgr.list_keys(args.type, args.session, args.limit)
        for k in keys:
            print(k)

    elif args.command == "stats":
        print(json.dumps(mgr.stats(), indent=2))

    elif args.command == "cleanup":
        count = mgr.cleanup_expired()
        print(f"Cleaned up {count} expired entries")

    elif args.command == "vacuum":
        mgr.vacuum()
        print("Database vacuumed")


if __name__ == "__main__":
    main()