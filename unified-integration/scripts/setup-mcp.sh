#!/usr/bin/env bash
# Prepare isolated dependencies and install MCP in native CLI configuration.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
eval "$(python3 "$SCRIPT_DIR/project_paths.py" shell)"
DATA_DIR="$(python3 "$SCRIPT_DIR/project_paths.py" runtime)"
PYTHON_BIN="$DATA_DIR/venv/bin/python"
MODE="${1:-install}"
log() { printf '[setup-mcp] %s\n' "$*" >&2; }
REQUIREMENTS="$UNIFIED_DIR/requirements.txt"
REQUIREMENTS_STAMP="$DATA_DIR/requirements.sha256"
requirements_digest="$(python3 - "$REQUIREMENTS" <<'PY'
import hashlib
import sys
from pathlib import Path
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
if [ ! -x "$PYTHON_BIN" ]; then
    mkdir -p "$DATA_DIR"
    if command -v uv >/dev/null 2>&1; then
        uv venv --python python3 "$DATA_DIR/venv" >&2
    else
        python3 -m venv "$DATA_DIR/venv" >&2
    fi
fi
installed_digest=""
if [ -f "$REQUIREMENTS_STAMP" ]; then
    IFS= read -r installed_digest < "$REQUIREMENTS_STAMP" || true
fi
if [ "$installed_digest" != "$requirements_digest" ] || \
   ! "$PYTHON_BIN" -c 'import mcp, PIL, yaml, tomlkit, json5, jsonschema, filelock' 2>/dev/null; then
    log "Installing runtime dependencies into $DATA_DIR/venv"
    if command -v uv >/dev/null 2>&1; then
        uv pip install --python "$PYTHON_BIN" -r "$REQUIREMENTS" >&2
    else
        "$PYTHON_BIN" -m pip install -r "$REQUIREMENTS" >&2
    fi
    stamp_tmp="$(mktemp "$DATA_DIR/.requirements.XXXXXX")"
    printf '%s\n' "$requirements_digest" > "$stamp_tmp"
    mv -f "$stamp_tmp" "$REQUIREMENTS_STAMP"
fi
case "$MODE" in
    --prepare) printf '%s\n' "$PYTHON_BIN" ;;
    --check) exec "$PYTHON_BIN" "$UNIFIED_DIR/mcp-servers/check-protocol.py" ;;
    install) exec "$PYTHON_BIN" "$SCRIPT_DIR/native-integration.py" --mcp-only ;;
    *) log "Unknown option: $MODE"; exit 2 ;;
esac
