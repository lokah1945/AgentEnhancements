#!/bin/bash
# Initialize agent memory system

MEMORY_ROOT="${AGENT_MEMORY_ROOT:-$HOME/.agent-memory}"
mkdir -p "$MEMORY_ROOT"/{projects,global,sessions,skills}

# Create SQLite database for structured memory
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
fi

echo "Memory system initialized at $MEMORY_ROOT"
