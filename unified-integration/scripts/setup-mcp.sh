#!/usr/bin/env bash
# Prepare isolated dependencies and install MCP in native CLI configuration.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/agentenhancements"
PYTHON_BIN="$DATA_DIR/venv/bin/python"
MODE="${1:-install}"
log() { printf '[setup-mcp] %s\n' "$*" >&2; }
if [ ! -x "$PYTHON_BIN" ]; then
    mkdir -p "$DATA_DIR"
    if command -v uv >/dev/null 2>&1; then
        uv venv --python python3 "$DATA_DIR/venv" >&2
    else
        python3 -m venv "$DATA_DIR/venv" >&2
    fi
fi
if ! "$PYTHON_BIN" -c 'import mcp, PIL, yaml, tomlkit, json5, jsonschema, filelock' 2>/dev/null; then
    log "Installing runtime dependencies into $DATA_DIR/venv"
    if command -v uv >/dev/null 2>&1; then
        uv pip install --python "$PYTHON_BIN" -r "$UNIFIED_DIR/requirements.txt" >&2
    else
        "$PYTHON_BIN" -m pip install -r "$UNIFIED_DIR/requirements.txt" >&2
    fi
fi
case "$MODE" in
    --prepare) printf '%s\n' "$PYTHON_BIN" ;;
    --check) exec "$PYTHON_BIN" "$UNIFIED_DIR/mcp-servers/check-protocol.py" ;;
    install) exec "$PYTHON_BIN" "$SCRIPT_DIR/native-integration.py" --mcp-only ;;
    *) log "Unknown option: $MODE"; exit 2 ;;
esac
