#!/usr/bin/env python3
"""
Universal Memory Utility for AI Coding Agents
Manages persistent memory across sessions and agents
"""

import sqlite3
import json
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

MEMORY_ROOT = Path(os.environ.get("AGENT_MEMORY_ROOT", Path.home() / ".agent-memory"))
DB_PATH = MEMORY_ROOT / "memory.db"

class AgentMemory:
    def __init__(self, agent: str, project: Optional[str] = None):
        self.agent = agent
        self.project = project or Path.cwd().name
        self._init_db()

    def _init_db(self):
        """Initialize database"""
        MEMORY_ROOT.mkdir(parents=True, exist_ok=True)
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

    def save(self, key: str, value: str, memory_type: str = "session_context",
             metadata: Optional[Dict] = None, ttl_days: Optional[int] = None) -> None:
        """Save a memory"""
        expires_at = None
        if ttl_days:
            from datetime import timedelta
            # SQLite format ("YYYY-MM-DD HH:MM:SS") so that comparisons
            # against datetime('now') work: the ISO "T" separator sorts
            # after a space and broke timely expiry cleanup.
            expires_at = (datetime.now() + timedelta(days=ttl_days)).strftime("%Y-%m-%d %H:%M:%S")

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
                    ORDER BY updated_at DESC LIMIT ?
                """, (self.agent, self.project, memory_type, limit))
            else:
                cursor = conn.execute("""
                    SELECT memory_type, key, value, metadata, updated_at
                    FROM memories
                    WHERE agent=? AND project=?
                    ORDER BY updated_at DESC LIMIT ?
                """, (self.agent, self.project, limit))

            return [
                {
                    "type": row[0],
                    "key": row[1],
                    "value": row[2][:200] + "..." if len(row[2]) > 200 else row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                    "updated": row[4]
                }
                for row in cursor.fetchall()
            ]

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
        ttl = int(sys.argv[6]) if len(sys.argv) > 6 else None
        memory.save(key, value, mem_type, ttl_days=ttl)
        print(f"Saved: {key} ({mem_type})")

    elif command == "load":
        if len(sys.argv) < 4:
            print("Usage: memory.py <agent> load <key> [type]")
            sys.exit(1)
        key = sys.argv[3]
        mem_type = sys.argv[4] if len(sys.argv) > 4 else "session_context"
        value = memory.load(key, mem_type)
        if value:
            print(value)
        else:
            print(f"Memory not found: {key}")
            sys.exit(1)

    elif command == "list":
        mem_type = sys.argv[3] if len(sys.argv) > 3 else None
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 20
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
