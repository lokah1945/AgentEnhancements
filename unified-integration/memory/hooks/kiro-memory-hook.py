#!/usr/bin/env python3
"""
Memory hook for kiro
This script is called by the agent to save/load memory
Uses parameterized queries to prevent SQL injection
"""

import sqlite3
import stat
import sys
import os
import json
from datetime import datetime, timezone

AGENT = "kiro"
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from project_paths import memory_root
MEMORY_ROOT = str(memory_root())
DB_PATH = os.path.join(MEMORY_ROOT, "memory.db")
# Same CLI bounds as scripts/memory.py, which writes the same table: a TTL is
# a positive number of days and a list limit a positive row count.
TTL_DAYS_MAX = 36500
LIST_LIMIT_MAX = 10000

def _redactor():
    """Resolve config once per listing call, not once per row and field."""
    try:
        from api_config import read_config, redact
        config, _ = read_config()
        return lambda text: redact(text, config)
    except Exception:
        return lambda text: text


def _display(value: str, redactor) -> str:
    text = redactor(value)
    return text[:200] + "..." if len(text) > 200 else text


def _metadata(value: str, redactor) -> dict:
    """Parse metadata after redaction; never leak raw secret text."""
    if not value:
        return {}
    try:
        return json.loads(redactor(value))
    except (TypeError, ValueError):
        return {"redacted": True}

def init_db():
    if os.path.islink(DB_PATH):
        raise OSError("Refusing symlinked memory database")
    os.makedirs(MEMORY_ROOT, exist_ok=True, mode=0o700)
    os.chmod(MEMORY_ROOT, 0o700)
    os.makedirs(os.path.join(MEMORY_ROOT, "projects"), exist_ok=True)
    descriptor = os.open(DB_PATH, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError("Memory database must be a regular file")
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
        project = os.path.realpath(os.getcwd())

    # ttl_days None never expires; a non-positive value stores an already
    # expired row (the same meaning as AgentMemory.save in memory.py).
    expires_at = None
    if ttl_days is not None:
        from datetime import timedelta
        try:
            expiry = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        except OverflowError as error:
            raise ValueError(f"ttl_days out of range: {ttl_days}") from error
        # SQLite format ("YYYY-MM-DD HH:MM:SS") so that comparisons
        # against datetime('now') work: the ISO "T" separator sorts
        # after a space and broke timely expiry cleanup.
        expires_at = expiry.strftime("%Y-%m-%d %H:%M:%S")

    meta_json = json.dumps(metadata) if metadata else None

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO memories
            (agent, project, memory_type, key, value, metadata, updated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
        """, (AGENT, project, memory_type, key, value, meta_json, expires_at))

def load_memory(key, memory_type="session_context", project=None):
    if project is None:
        project = os.path.realpath(os.getcwd())

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT value FROM memories
            WHERE agent=? AND project=? AND memory_type=? AND key=?
              AND (expires_at IS NULL OR expires_at > datetime('now'))
            ORDER BY updated_at DESC LIMIT 1
        """, (AGENT, project, memory_type, key))
        row = cursor.fetchone()
        return row[0] if row else None

def list_memories(memory_type=None, project=None, limit=20):
    if project is None:
        project = os.path.realpath(os.getcwd())
    redactor = _redactor()

    with sqlite3.connect(DB_PATH) as conn:
        if memory_type:
            cursor = conn.execute("""
                SELECT memory_type, key, value, metadata, updated_at
                FROM memories
                WHERE agent=? AND project=? AND memory_type=?
                  AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY updated_at DESC LIMIT ?
            """, (AGENT, project, memory_type, limit))
        else:
            cursor = conn.execute("""
                SELECT memory_type, key, value, metadata, updated_at
                FROM memories
                WHERE agent=? AND project=?
                  AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY updated_at DESC LIMIT ?
            """, (AGENT, project, limit))

        return [
            {
                "type": row[0],
                "key": redactor(row[1]),
                "value": _display(row[2], redactor),
                "metadata": _metadata(row[3], redactor),
                "updated": row[4]
            }
            for row in cursor.fetchall()
        ]

def delete_memory(key, memory_type="session_context", project=None):
    if project is None:
        project = os.path.realpath(os.getcwd())

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

def _int_arg(raw, usage, lo, hi):
    """Parse an integer CLI argument within [lo, hi], else print usage and exit 1."""
    try:
        value = int(raw)
    except (ValueError, OverflowError):
        value = None
    if value is None or value < lo or value > hi:
        print(usage)
        sys.exit(1)
    return value

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
    os.chmod(DB_PATH, 0o600)
    command = sys.argv[1]

    if command == "save":
        if len(sys.argv) < 4:
            print("Usage: memory-hook.py save <key> <value> [type] [project] [ttl_days]")
            sys.exit(1)
        key = sys.argv[2]
        value = sys.argv[3]
        mem_type = sys.argv[4] if len(sys.argv) > 4 else "session_context"
        project = sys.argv[5] if len(sys.argv) > 5 else None
        ttl = _int_arg(
            sys.argv[6],
            "Usage: memory-hook.py save <key> <value> [type] [project] [ttl_days]\n"
            f"ttl_days must be an integer from 1 to {TTL_DAYS_MAX}",
            1, TTL_DAYS_MAX,
        ) if len(sys.argv) > 6 else None
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
        limit = _int_arg(
            sys.argv[4],
            "Usage: memory-hook.py list [type] [project] [limit]\n"
            f"limit must be an integer from 1 to {LIST_LIMIT_MAX}",
            1, LIST_LIMIT_MAX,
        ) if len(sys.argv) > 4 else 20
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
