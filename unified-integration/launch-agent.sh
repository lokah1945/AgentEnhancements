#!/bin/bash
# Universal AI Agent Launcher with Enhancements

set -euo pipefail

AGENT="${1:-claude-code}"
if [ $# -gt 0 ]; then
    shift
fi

# Resolve installation paths from this script's location; environment
# variables take precedence.
UNIFIED_DIR="${AGENT_ENHANCEMENTS_UNIFIED_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
BASE_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-$(dirname "$UNIFIED_DIR")}"

# Detected agents (written by setup.sh); pre-declared so the script also
# works when the file is missing.
AGENTS=()
# shellcheck source=/dev/null
source "$UNIFIED_DIR/config/detected-agents.sh" 2>/dev/null || true

# Validate agent
if [[ ! " ${AGENTS[*]:-} " =~ " ${AGENT} " ]]; then
    echo "Agent '$AGENT' not detected. Available: ${AGENTS[*]:-none}"
    echo "Run $UNIFIED_DIR/setup.sh to (re)detect installed agents."
    echo "Usage: $0 <agent> [args...]"
    exit 1
fi

# Initialize memory
if [ -x "$UNIFIED_DIR/memory/init-memory.sh" ]; then
    "$UNIFIED_DIR/memory/init-memory.sh"
else
    echo "Warning: memory initializer not found at $UNIFIED_DIR/memory/init-memory.sh" >&2
fi

# Set environment variables
export AGENT_MEMORY_ROOT="${AGENT_MEMORY_ROOT:-$HOME/.agent-memory}"
export AGENT_SKILLS_DIR="$UNIFIED_DIR/skills"
export AGENT_COMPRESSION_CONFIG="$UNIFIED_DIR/compression/config.yaml"
export AGENT_PROMPTS_DIR="$UNIFIED_DIR/prompts"
export AGENT_ENHANCEMENTS_BASE_DIR="$BASE_DIR"
export AGENT_ENHANCEMENTS_UNIFIED_DIR="$UNIFIED_DIR"

# Launch agent with enhancements
case "$AGENT" in
    claude-code) exec claude "$@" ;;
    codex)       exec codex "$@" ;;
    opencode)    exec opencode "$@" ;;
    cursor)      exec cursor "$@" ;;
    gemini-cli)  exec gemini "$@" ;;
    windsurf)    exec windsurf "$@" ;;
    copilot)     exec gh copilot "$@" ;;
    kiro)        exec kiro "$@" ;;
    *)
        echo "Unknown agent: $AGENT"
        exit 1
        ;;
esac
