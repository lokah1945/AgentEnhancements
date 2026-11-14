#!/bin/bash
# Universal AI Agent Launcher with Enhancements

AGENT="${1:-claude-code}"
shift

UNIFIED_DIR="/root/agent-enhancements/unified-integration"
BASE_DIR="/root/agent-enhancements"

# Allow override via environment
UNIFIED_DIR="${AGENT_ENHANCEMENTS_UNIFIED_DIR:-$UNIFIED_DIR}"
BASE_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-$BASE_DIR}"

# Load detected agents
source "$UNIFIED_DIR/config/detected-agents.sh" 2>/dev/null || true

# Validate agent
if [[ ! " ${AGENTS[@]} " =~ " ${AGENT} " ]]; then
    echo "Agent '$AGENT' not detected. Available: ${AGENTS[@]}"
    echo "Usage: $0 <agent> [args...]"
    exit 1
fi

# Initialize memory
"$UNIFIED_DIR/memory/init-memory.sh"

# Set environment variables
export AGENT_MEMORY_ROOT="$HOME/.agent-memory"
export AGENT_SKILLS_DIR="$UNIFIED_DIR/skills"
export AGENT_COMPRESSION_CONFIG="$UNIFIED_DIR/compression/config.yaml"
export AGENT_PROMPTS_DIR="$UNIFIED_DIR/prompts"
export AGENT_ENHANCEMENTS_BASE_DIR="$BASE_DIR"
export AGENT_ENHANCEMENTS_UNIFIED_DIR="$UNIFIED_DIR"

# Launch agent with enhancements
case "$AGENT" in
    claude-code)
        exec claude "$@"
        ;;
    codex)
        exec codex "$@"
        ;;
    opencode)
        exec opencode "$@"
        ;;
    cursor)
        exec cursor "$@"
        ;;
    gemini-cli)
        exec gemini "$@"
        ;;
    windsurf)
        exec windsurf "$@"
        ;;
    copilot)
        exec gh copilot "$@"
        ;;
    kiro)
        exec kiro "$@"
        ;;
    *)
        echo "Unknown agent: $AGENT"
        exit 1
        ;;
esac
