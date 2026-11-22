#!/usr/bin/env python3
"""
AgentEnhancements Memory System v2 — SQLite-backed cross-session memory.
Ported from DELL branch with ASUS security hardening (chmod, O_NOFOLLOW).
Supports parameterized queries, TTL cleanup, multiple memory types, thread safety.
"""

import json
import os
import sqlite3
import threading
import time
import stat
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
    Includes ASUS security hardening: restrictive permissions, anti-symlink.
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
        # Secure directory permissions (ASUS hardening)
        try:
            self.memory_dir.chmod(0o700)
        except OSError:
            pass

        self.db_path = self.memory_dir / "memory.db"
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema with security hardening."""
        # ASUS: Claim private regular file before SQLite opens it
        # Prevents symlink attacks and permissive umask exposure
        descriptor = os.open(
            self.db_path,
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
            0o600
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OSError("memory database must be a regular file")
        finally:
            os.close(descriptor)

        # Ensure file permissions are restrictive
        try:
            os.chmod(self.db_path, 0o600)
        except OSError:
            pass

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
            # Enable WAL mode for better concurrent access on Windows
            conn.execute("PRAGMA journal_mode=WAL")

        # Ensure file permissions after SQLite creates it
        try:
            self.db_path.chmod(0o600)
        except OSError:
            pass

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

        tags_json = json.dumps(tags) if tags else None
        value_json = self._serialize_value(value)

        with self._lock:
            with self._get_conn() as conn:
                # Check if exists
                existing = conn.execute(
                    "SELECT value, created_at FROM memories WHERE key=? AND memory_type=? AND session_id=?",
                    (key, memory_type, session_id)
                ).fetchone()

                if existing:
                    # Merge with existing value (shallow merge for dicts)
                    try:
                        existing_value = self._deserialize_value(existing["value"])
                        if isinstance(existing_value, dict) and isinstance(value, dict):
                            merged = {**existing_value, **value}
                            value_json = self._serialize_value(merged)
                    except Exception:
                        pass  # Use new value as-is

                    conn.execute("""
                        UPDATE memories
                        SET value=?, updated_at=?, expires_at=?, tags=?, agent_type=?
                        WHERE key=? AND memory_type=? AND session_id=?
                    """, (value_json, now, expires_at, tags_json, agent_type, key, memory_type, session_id))
                else:
                    conn.execute("""
                        INSERT INTO memories
                        (key, value, memory_type, created_at, updated_at, expires_at, tags, session_id, agent_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (key, value_json, memory_type, now, now, expires_at, tags_json, session_id, agent_type))

        return True

    def load(
        self,
        key: str,
        memory_type: str = "session_context",
        session_id: str = "",
        agent_type: str = ""
    ) -> Optional[Any]:
        """Load a memory entry."""
        with self._lock:
            with self._get_conn() as conn:
                # Try exact match first
                row = conn.execute("""
                    SELECT value FROM memories
                    WHERE key=? AND memory_type=? AND session_id=?
                      AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY updated_at DESC LIMIT 1
                """, (key, memory_type, session_id, self._now())).fetchone()

                # If not found and session_id provided, try without session_id (global fallback)
                if not row and session_id:
                    row = conn.execute("""
                        SELECT value FROM memories
                        WHERE key=? AND memory_type=? AND session_id=''
                          AND (expires_at IS NULL OR expires_at > ?)
                        ORDER BY updated_at DESC LIMIT 1
                    """, (key, memory_type, self._now())).fetchone()

                return self._deserialize_value(row["value"]) if row else None

    def delete(
        self,
        key: str,
        memory_type: str = "session_context",
        session_id: str = ""
    ) -> bool:
        """Delete a memory entry."""
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute("""
                    DELETE FROM memories WHERE key=? AND memory_type=? AND session_id=?
                """, (key, memory_type, session_id))
                return cursor.rowcount > 0

    def list(
        self,
        memory_type: Optional[str] = None,
        session_id: str = "",
        agent_type: str = "",
        limit: int = 20,
        include_expired: bool = False
    ) -> List[Dict]:
        """List memories with filtering."""
        with self._lock:
            with self._get_conn() as conn:
                conditions = []
                params = []

                if memory_type:
                    conditions.append("memory_type = ?")
                    params.append(memory_type)
                if session_id:
                    conditions.append("session_id = ?")
                    params.append(session_id)
                if agent_type:
                    conditions.append("agent_type = ?")
                    params.append(agent_type)
                if not include_expired:
                    conditions.append("(expires_at IS NULL OR expires_at > ?)")
                    params.append(self._now())

                where_clause = " AND ".join(conditions) if conditions else "1=1"
                params.append(limit)

                query = f"""
                    SELECT key, value, memory_type, created_at, updated_at, expires_at, tags, session_id, agent_type
                    FROM memories
                    WHERE {where_clause}
                    ORDER BY updated_at DESC LIMIT ?
                """

                cursor = conn.execute(query, params)
                results = []
                for row in cursor.fetchall():
                    try:
                        value = self._deserialize_value(row["value"])
                        # Truncate long values for listing
                        if isinstance(value, str) and len(value) > 200:
                            value = value[:200] + "..."
                        elif isinstance(value, dict):
                            value = str(value)[:200] + "..."
                    except Exception:
                        value = str(row["value"])[:200] + "..."

                    results.append({
                        "key": row["key"],
                        "value": value,
                        "memory_type": row["memory_type"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "expires_at": row["expires_at"],
                        "tags": json.loads(row["tags"]) if row["tags"] else [],
                        "session_id": row["session_id"],
                        "agent_type": row["agent_type"],
                    })
                return results

    def recall_session(
        self,
        session_id: str,
        max_age_days: int = 7,
        limit: int = 10
    ) -> List[Dict]:
        """Recall memories for a specific session within max_age_days."""
        cutoff = self._now() - (max_age_days * 24 * 3600)
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute("""
                    SELECT key, value, memory_type, updated_at
                    FROM memories
                    WHERE session_id = ? AND updated_at > ?
                      AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY updated_at DESC LIMIT ?
                """, (session_id, cutoff, self._now(), limit))

                results = []
                for row in cursor.fetchall():
                    try:
                        value = self._deserialize_value(row["value"])
                    except Exception:
                        value = str(row["value"])
                    results.append({
                        "key": row["key"],
                        "value": value,
                        "type": row["memory_type"],
                        "updated": row["updated_at"],
                    })
                return results

    def cleanup_expired(self) -> int:
        """Remove expired memory entries. Returns count of removed entries."""
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
                    (self._now(),)
                )
                return cursor.rowcount

    def stats(self) -> Dict:
        """Get memory database statistics."""
        with self._lock:
            with self._get_conn() as conn:
                # Total entries
                total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

                # By type
                by_type = {}
                cursor = conn.execute("SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type")
                for row in cursor.fetchall():
                    by_type[row[0]] = row[1]

                # By agent
                by_agent = {}
                cursor = conn.execute("SELECT agent_type, COUNT(*) FROM memories WHERE agent_type != '' GROUP BY agent_type")
                for row in cursor.fetchall():
                    by_agent[row[0]] = row[1]

                # Database size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

                return {
                    "db_path": str(self.db_path),
                    "db_size_bytes": db_size,
                    "total_entries": total,
                    "by_type": by_type,
                    "by_agent": by_agent,
                    "ttl_policies": {k: v for k, v in self.TTL_POLICIES.items()},
                }

    # =========================================================================
    # CLI INTERFACE
    # =========================================================================
    @classmethod
    def cli(cls, args: List[str]) -> int:
        """Command-line interface."""
        import argparse
        parser = argparse.ArgumentParser(description="AgentEnhancements Memory Manager v2")
        parser.add_argument("--dir", type=Path, default=Path.cwd() / ".agentenhancements" / "memory",
                           help="Memory directory")

        subparsers = parser.add_subparsers(dest="command", required=True)

        # Save
        save_parser = subparsers.add_parser("save", help="Save a memory entry")
        save_parser.add_argument("key", help="Memory key")
        save_parser.add_argument("value", help="Memory value (JSON)")
        save_parser.add_argument("--type", default="session_context", choices=list(cls.TTL_POLICIES.keys()))
        save_parser.add_argument("--session", default="")
        save_parser.add_argument("--agent", default="")
        save_parser.add_argument("--tags", nargs="*")
        save_parser.add_argument("--ttl", type=int, help="TTL override in seconds")

        # Load
        load_parser = subparsers.add_parser("load", help="Load a memory entry")
        load_parser.add_argument("key", help="Memory key")
        load_parser.add_argument("--type", default="session_context", choices=list(cls.TTL_POLICIES.keys()))
        load_parser.add_argument("--session", default="")
        load_parser.add_argument("--agent", default="")

        # List
        list_parser = subparsers.add_parser("list", help="List memories")
        list_parser.add_argument("--type", choices=list(cls.TTL_POLICIES.keys()))
        list_parser.add_argument("--session", default="")
        list_parser.add_argument("--agent", default="")
        list_parser.add_argument("--limit", type=int, default=20)
        list_parser.add_argument("--include-expired", action="store_true")

        # Recall
        recall_parser = subparsers.add_parser("recall", help="Recall session memories")
        recall_parser.add_argument("session_id", help="Session ID")
        recall_parser.add_argument("--max-age", type=int, default=7)
        recall_parser.add_argument("--limit", type=int, default=10)

        # Cleanup
        subparsers.add_parser("cleanup", help="Remove expired entries")

        # Stats
        subparsers.add_parser("stats", help="Show database statistics")

        parsed = parser.parse_args(args)
        mgr = cls(parsed.dir)

        if parsed.command == "save":
            try:
                value = json.loads(parsed.value)
            except json.JSONDecodeError:
                value = parsed.value
            mgr.save(parsed.key, value, parsed.type, parsed.session, parsed.agent, parsed.tags, parsed.ttl)
            print(f"Saved: {parsed.key}")
        elif parsed.command == "load":
            value = mgr.load(parsed.key, parsed.type, parsed.session, parsed.agent)
            if value is not None:
                print(json.dumps(value, ensure_ascii=False, indent=2))
            else:
                print(f"Not found: {parsed.key}")
                return 1
        elif parsed.command == "list":
            items = mgr.list(parsed.type, parsed.session, parsed.agent, parsed.limit, parsed.include_expired)
            for item in items:
                print(f"  {item['key']} ({item['memory_type']}): {item['value']}")
        elif parsed.command == "recall":
            items = mgr.recall_session(parsed.session_id, parsed.max_age, parsed.limit)
            for item in items:
                print(f"  {item['key']} ({item['type']}): {item['value']}")
        elif parsed.command == "cleanup":
            count = mgr.cleanup_expired()
            print(f"Removed {count} expired entries")
        elif parsed.command == "stats":
            stats = mgr.stats()
            print(json.dumps(stats, indent=2, default=str))

        return 0


def main():
    import sys
    sys.exit(MemoryManager.cli(sys.argv[1:]))


if __name__ == "__main__":
    main()