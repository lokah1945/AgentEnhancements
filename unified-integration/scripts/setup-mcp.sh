#!/usr/bin/env bash
# Prepare isolated dependencies and install MCP in native CLI configuration.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-install}"
log() { printf '[setup-mcp] %s\n' "$*" >&2; }
if [ "$#" -gt 1 ]; then
    log 'Usage: setup-mcp.sh [--prepare|--check|install]'
    exit 2
fi
case "$MODE" in
    --prepare|--check|install) ;;
    *) log "Unknown option: $MODE"; exit 2 ;;
esac

DATA_DIR="$(python3 "$SCRIPT_DIR/project_paths.py" runtime)"
PYTHON_BIN="$DATA_DIR/venv/bin/python"
if [ "$MODE" = --check ] && [ ! -x "$PYTHON_BIN" ]; then
    log 'Runtime missing. Run unified-integration/setup.sh or setup-mcp.sh --prepare first.'
    exit 1
fi
state_environment="$(python3 "$SCRIPT_DIR/project_paths.py" shell)"
eval "$state_environment"
case "$MODE" in
    --prepare) exec python3 "$SCRIPT_DIR/runtime_dependencies.py" ;;
    --check) exec python3 "$SCRIPT_DIR/runtime_dependencies.py" --check ;;
    install)
        PYTHON_BIN="$(python3 "$SCRIPT_DIR/runtime_dependencies.py")"
        exec "$PYTHON_BIN" "$SCRIPT_DIR/native-integration.py" --mcp-only
        ;;
esac
