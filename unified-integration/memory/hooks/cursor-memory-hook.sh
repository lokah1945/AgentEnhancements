#!/bin/bash
# Memory hook for cursor

AGENT="cursor"
MEMORY_ROOT="${AGENT_MEMORY_ROOT:-$HOME/.agent-memory}"

case "$1" in
    save)
        key="$2"
        value="$3"
        type="${4:-session_context}"
        project="${5:-$(basename "$PWD")}"

        if command -v sqlite3 &> /dev/null; then
            sqlite3 "$MEMORY_ROOT/memory.db" \
                "INSERT OR REPLACE INTO memories (agent, project, memory_type, key, value, updated_at) VALUES ('$AGENT', '$project', '$type', '$key', '$value', datetime('now'));"
        else
            mkdir -p "$MEMORY_ROOT/projects/$project"
            echo "$value" > "$MEMORY_ROOT/projects/$project/${type}_${key}.md"
        fi
        ;;
    load)
        key="$2"
        type="${3:-session_context}"
        project="${4:-$(basename "$PWD")}"

        if command -v sqlite3 &> /dev/null; then
            sqlite3 "$MEMORY_ROOT/memory.db" \
                "SELECT value FROM memories WHERE agent='$AGENT' AND project='$project' AND memory_type='$type' AND key='$key' ORDER BY updated_at DESC LIMIT 1;"
        else
            cat "$MEMORY_ROOT/projects/$project/${type}_${key}.md" 2>/dev/null || echo ""
        fi
        ;;
    list)
        project="${2:-$(basename "$PWD")}"

        if command -v sqlite3 &> /dev/null; then
            sqlite3 "$MEMORY_ROOT/memory.db" \
                "SELECT memory_type, key, substr(value, 1, 100), updated_at FROM memories WHERE agent='$AGENT' AND project='$project' ORDER BY updated_at DESC;"
        else
            ls -la "$MEMORY_ROOT/projects/$project/" 2>/dev/null || echo "No memories found"
        fi
        ;;
    *)
        echo "Usage: $0 {save|load|list} [args...]"
        exit 1
        ;;
esac