#!/usr/bin/env python3
"""
Memory hook for kiro
This script is called by the agent to save/load memory
Uses parameterized queries to prevent SQL injection
"""

import sqlite3
import sys
import os
import json
from datetime import datetime

AGENT = "kiro"
MEMORY_ROOT = os.environ.get("AGENT_MEMORY_ROOT", os.path.expanduser("~/.agent-memory"))
DB_PATH = os.path.join(MEMORY_ROOT, "memory.db")

def init_db():
    os.makedirs(MEMORY_ROOT, exist_ok=True)
    os.makedirs(os.path.join(MEMORY_ROOT, "projects"), exist_ok=True)
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
                embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(agent, project, memory_type, key)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_project ON memories(agent, project)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON memories(expires_at)")

def save_memory(key, value, memory_type="session_context", project=None, metadata=None, ttl_days=None):
    if project is None:
        project = os.path.basename(os.getcwd())

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
        """, (AGENT, project, memory_type, key, value, meta_json, expires_at))

def load_memory(key, memory_type="session_context", project=None):
    if project is None:
        project = os.path.basename(os.getcwd())

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT value FROM memories
            WHERE agent=? AND project=? AND memory_type=? AND key=?
            ORDER BY updated_at DESC LIMIT 1
        """, (AGENT, project, memory_type, key))
        row = cursor.fetchone()
        return row[0] if row else None

def list_memories(memory_type=None, project=None, limit=20):
    if project is None:
        project = os.path.basename(os.getcwd())

    with sqlite3.connect(DB_PATH) as conn:
        if memory_type:
            cursor = conn.execute("""
                SELECT memory_type, key, value, metadata, updated_at
                FROM memories
                WHERE agent=? AND project=? AND memory_type=?
                ORDER BY updated_at DESC LIMIT ?
            """, (AGENT, project, memory_type, limit))
        else:
            cursor = conn.execute("""
                SELECT memory_type, key, value, metadata, updated_at
                FROM memories
                WHERE agent=? AND project=?
                ORDER BY updated_at DESC LIMIT ?
            """, (AGENT, project, limit))

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

def delete_memory(key, memory_type="session_context", project=None):
    if project is None:
        project = os.path.basename(os.getcwd())

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            DELETE FROM memories
            WHERE agent=? AND project=? AND memory_type=? AND key=?
        """, (AGENT, project, memory_type, key))
        return cursor.rowcount > 0

def cleanup_expired():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            DELETE FROM memories
            WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
        """)
        return cursor.rowcount

def main():
    if len(sys.argv) < 2:
        print("Usage: memory-hook.py <command> [args...]")
        print("Commands: save <key> <value> [type] [project] [ttl_days]")
        print("          load <key> [type] [project]")
        print("          list [type] [project] [limit]")
        print("          delete <key> [type] [project]")
        print("          cleanup")
        sys.exit(1)

    init_db()
    command = sys.argv[1]

    if command == "save":
        if len(sys.argv) < 4:
            print("Usage: memory-hook.py save <key> <value> [type] [project] [ttl_days]")
            sys.exit(1)
        key = sys.argv[2]
        value = sys.argv[3]
        mem_type = sys.argv[4] if len(sys.argv) > 4 else "session_context"
        project = sys.argv[5] if len(sys.argv) > 5 else None
        ttl = int(sys.argv[6]) if len(sys.argv) > 6 else None
        save_memory(key, value, mem_type, project, ttl_days=ttl)
        print(f"Saved: {key} ({mem_type})")

    elif command == "load":
        if len(sys.argv) < 3:
            print("Usage: memory-hook.py load <key> [type] [project]")
            sys.exit(1)
        key = sys.argv[2]
        mem_type = sys.argv[3] if len(sys.argv) > 3 else "session_context"
        project = sys.argv[4] if len(sys.argv) > 4 else None
        value = load_memory(key, mem_type, project)
        if value:
            print(value)
        else:
            print(f"Memory not found: {key}", file=sys.stderr)
            sys.exit(1)

    elif command == "list":
        mem_type = sys.argv[2] if len(sys.argv) > 2 else None
        project = sys.argv[3] if len(sys.argv) > 3 else None
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 20
        memories = list_memories(mem_type, project, limit)
        for m in memories:
            print(f"[{m['type']}] {m['key']}: {m['value']} (updated: {m['updated']})")

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: memory-hook.py delete <key> [type] [project]")
            sys.exit(1)
        key = sys.argv[2]
        mem_type = sys.argv[3] if len(sys.argv) > 3 else "session_context"
        project = sys.argv[4] if len(sys.argv) > 4 else None
        if delete_memory(key, mem_type, project):
            print(f"Deleted: {key}")
        else:
            print(f"Not found: {key}")
            sys.exit(1)

    elif command == "cleanup":
        count = cleanup_expired()
        print(f"Cleaned up {count} expired memories")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
