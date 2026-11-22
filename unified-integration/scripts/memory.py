#!/usr/bin/env python3
"""
Universal Memory Utility for AI Coding Agents
Manages persistent memory across sessions and agents
"""

import sqlite3
import json
import os
import stat
import sys
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import memory_root

MEMORY_ROOT = memory_root()
DB_PATH = MEMORY_ROOT / "memory.db"
LIST_VALUE_LIMIT = 200


def _redactor() -> Callable[[str], str]:
    """Return the shared credential redactor, or identity when unavailable.

    Imported lazily so memory.py keeps working as a standalone utility.
    """
    try:
        from api_config import read_config, redact
        config, _ = read_config()
    except Exception:  # noqa: BLE001 - redaction is best effort here
        return lambda text: text
    return lambda text: redact(text, config)


class AgentMemory:
    def __init__(self, agent: str, project: Optional[str] = None):
        self.agent = agent
        self.project = project or str(Path.cwd().resolve())
        self._init_db()

    def _init_db(self):
        """Initialize database"""
        MEMORY_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
        MEMORY_ROOT.chmod(0o700)
        # Claim a private regular file before SQLite opens it. A pre-existing
        # symlink must never redirect schema/data writes or chmod to another
        # database, and a permissive umask must not expose a new database.
        descriptor = os.open(
            DB_PATH, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OSError("memory database must be a regular file")
            os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL,
                    project TEXT,
                    memory_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    UNIQUE(agent, project, memory_type, key)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_project ON memories(agent, project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON memories(expires_at)")
        DB_PATH.chmod(0o600)

    def save(self, key: str, value: str, memory_type: str = "session_context",
             metadata: Optional[Dict] = None, ttl_days: Optional[int] = None) -> None:
        """Save a memory"""
        expires_at = None
        if ttl_days is not None:
            from datetime import timedelta
            # SQLite format ("YYYY-MM-DD HH:MM:SS") so that comparisons
            # against datetime('now') work: the ISO "T" separator sorts
            # after a space and broke timely expiry cleanup.
            expires_at = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).strftime("%Y-%m-%d %H:%M:%S")

        meta_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories
                (agent, project, memory_type, key, value, metadata, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """, (self.agent, self.project, memory_type, key, value, meta_json, expires_at))

    def load(self, key: str, memory_type: str = "session_context") -> Optional[str]:
        """Load a memory"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT value FROM memories
                WHERE agent=? AND project=? AND memory_type=? AND key=?
                  AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY updated_at DESC LIMIT 1
            """, (self.agent, self.project, memory_type, key))
            row = cursor.fetchone()
            return row[0] if row else None

    def list(self, memory_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """List memories"""
        with sqlite3.connect(DB_PATH) as conn:
            if memory_type:
                cursor = conn.execute("""
                    SELECT memory_type, key, value, metadata, updated_at
                    FROM memories
                    WHERE agent=? AND project=? AND memory_type=?
                      AND (expires_at IS NULL OR expires_at > datetime('now'))
                    ORDER BY updated_at DESC LIMIT ?
                """, (self.agent, self.project, memory_type, limit))
            else:
                cursor = conn.execute("""
                    SELECT memory_type, key, value, metadata, updated_at
                    FROM memories
                    WHERE agent=? AND project=?
                      AND (expires_at IS NULL OR expires_at > datetime('now'))
                    ORDER BY updated_at DESC LIMIT ?
                """, (self.agent, self.project, limit))

            rows = cursor.fetchall()

        # Redact the full value before truncating it: a credential that
        # straddles the cut would otherwise survive as an unmatched prefix.
        redact = _redactor()
        memories = []
        for row in rows:
            value = redact(row[2])
            if len(value) > LIST_VALUE_LIMIT:
                value = value[:LIST_VALUE_LIMIT] + "..."
            memories.append({
                "type": row[0],
                "key": row[1],
                "value": value,
                "metadata": json.loads(row[3]) if row[3] else {},
                "updated": row[4]
            })
        return memories

    def delete(self, key: str, memory_type: str = "session_context") -> bool:
        """Delete a memory"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                DELETE FROM memories
                WHERE agent=? AND project=? AND memory_type=? AND key=?
            """, (self.agent, self.project, memory_type, key))
            return cursor.rowcount > 0

    def cleanup_expired(self) -> int:
        """Remove expired memories"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                DELETE FROM memories
                WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
            """)
            return cursor.rowcount


def _int_arg(raw: str, usage: str) -> int:
    """Parse an integer CLI argument, exiting with usage text on bad input."""
    try:
        return int(raw)
    except ValueError:
        print(usage)
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print("Usage: memory.py <agent> <command> [args...]")
        print("Commands: save <key> <value> [type] [ttl_days]")
        print("          load <key> [type]")
        print("          list [type] [limit]")
        print("          delete <key> [type]")
        print("          cleanup")
        sys.exit(1)

    agent = sys.argv[1]
    command = sys.argv[2]

    memory = AgentMemory(agent)

    if command == "save":
        if len(sys.argv) < 5:
            print("Usage: memory.py <agent> save <key> <value> [type] [ttl_days]")
            sys.exit(1)
        key = sys.argv[3]
        value = sys.argv[4]
        mem_type = sys.argv[5] if len(sys.argv) > 5 else "session_context"
        ttl = _int_arg(sys.argv[6], "Usage: memory.py <agent> save <key> <value> [type] [ttl_days]") if len(sys.argv) > 6 else None
        memory.save(key, value, mem_type, ttl_days=ttl)
        print(f"Saved: {key} ({mem_type})")

    elif command == "load":
        if len(sys.argv) < 4:
            print("Usage: memory.py <agent> load <key> [type]")
            sys.exit(1)
        key = sys.argv[3]
        mem_type = sys.argv[4] if len(sys.argv) > 4 else "session_context"
        value = memory.load(key, mem_type)
        if value is not None:
            print(value)
        else:
            print(f"Memory not found: {key}")
            sys.exit(1)

    elif command == "list":
        mem_type = sys.argv[3] if len(sys.argv) > 3 else None
        limit = _int_arg(sys.argv[4], "Usage: memory.py <agent> list [type] [limit]") if len(sys.argv) > 4 else 20
        memories = memory.list(mem_type, limit)
        for m in memories:
            print(f"[{m['type']}] {m['key']}: {m['value']} (updated: {m['updated']})")

    elif command == "delete":
        if len(sys.argv) < 4:
            print("Usage: memory.py <agent> delete <key> [type]")
            sys.exit(1)
        key = sys.argv[3]
        mem_type = sys.argv[4] if len(sys.argv) > 4 else "session_context"
        if memory.delete(key, mem_type):
            print(f"Deleted: {key}")
        else:
            print(f"Not found: {key}")

    elif command == "cleanup":
        count = memory.cleanup_expired()
        print(f"Cleaned up {count} expired memories")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
