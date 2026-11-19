#!/bin/bash
# Initialize agent memory system

set -euo pipefail
umask 077
MEMORY_ROOT="${AGENT_MEMORY_ROOT:-$HOME/.agent-memory}"
if [ -L "$MEMORY_ROOT" ] || [ -L "$MEMORY_ROOT/memory.db" ]; then
    echo "Refusing symlinked memory storage" >&2
    exit 1
fi
mkdir -p "$MEMORY_ROOT"/{projects,global,sessions,skills}
chmod 700 "$MEMORY_ROOT"
if [ -e "$MEMORY_ROOT/memory.db" ]; then
    chmod 600 "$MEMORY_ROOT/memory.db"
fi

# Create SQLite database for structured memory when the sqlite3 CLI is
# available. Without it, the Python hooks create the same schema on first
# use - report that honestly instead of claiming initialization (AE-16).
if command -v sqlite3 &> /dev/null; then
    sqlite3 "$MEMORY_ROOT/memory.db" << 'SQL'
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
);

CREATE INDEX IF NOT EXISTS idx_agent_project ON memories(agent, project);
CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_expires ON memories(expires_at);
SQL
    chmod 600 "$MEMORY_ROOT/memory.db"
    echo "Memory system initialized at $MEMORY_ROOT (schema created)"
elif [ -f "$MEMORY_ROOT/memory.db" ]; then
    echo "Memory storage ready at $MEMORY_ROOT (database exists; schema maintained by the Python hooks)"
else
    echo "Memory directories created at $MEMORY_ROOT; the SQLite database will be created by the Python hooks on first use (sqlite3 CLI not installed)"
fi
