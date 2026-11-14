#!/usr/bin/env bash
# Smoke test MCP server configuration for the plugin catalog.
# Usage:
#   bash mcp-test.sh --priority P0|P1|P2
#   bash mcp-test.sh --for-plugin <slug>
#   bash mcp-test.sh --server <id>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="$(cd "$UNIFIED_DIR/.." && pwd)"
SERVERS_JSON="$BASE_DIR/plugin-catalog/mcp-servers.json"
PYTHON_BIN="$(bash "$SCRIPT_DIR/setup-mcp.sh" --prepare)"

pass() { echo -e "\033[0;32m[PASS]\033[0m $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $*"; }
fail() { echo -e "\033[0;31m[FAIL]\033[0m $*"; }

get_servers() {
    local filter="$1"
    local value="${2:-}"
    case "$filter" in
        --priority)
            jq -r --arg p "$value" '.servers[] | select(.priority == $p) | .id' "$SERVERS_JSON"
            ;;
        --for-plugin)
            jq -r --arg p "$value" '.servers[] | select((.for_plugins // []) | index($p)) | .id' "$SERVERS_JSON"
            ;;
        --server)
            echo "$value"
            ;;
        *)
            jq -r '.servers[].id' "$SERVERS_JSON"
            ;;
    esac
}

is_configured() {
    "$PYTHON_BIN" - "$1" "$BASE_DIR" <<'PYCONFIG'
import os
import sys
from pathlib import Path
import json5
import tomllib

name = sys.argv[1]
home = Path.home()
claude = Path(os.environ.get('CLAUDE_CONFIG_DIR', home / '.claude'))
codex = Path(os.environ.get('CODEX_HOME', home / '.codex'))
opencode = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'opencode'
configs = [Path(str(claude) + '.json'), Path(sys.argv[2]) / '.mcp.json',
           codex / 'config.toml', opencode / 'opencode.json', opencode / 'opencode.jsonc']
for path in configs:
    if not path.is_file():
        continue
    try:
        doc = tomllib.loads(path.read_text()) if path.suffix == '.toml' else json5.loads(path.read_text())
        for key in ['mcpServers', 'mcp_servers', 'mcp']:
            servers = doc.get(key, {})
            if key == 'mcp':
                servers = servers.get('servers', servers)
            if name in servers and servers[name].get('enabled', True) and not servers[name].get('disabled', False):
                raise SystemExit(0)
    except (ValueError, OSError):
        continue
raise SystemExit(1)
PYCONFIG
}

check_installable() {
    local id="$1"
    # Built servers use the isolated runtime already prepared above.
    if jq -e --arg id "$id" '.servers[] | select(.id == $id and .status == "built")' "$SERVERS_JSON" >/dev/null; then
        return 1
    fi
    local cmd
    cmd="$(jq -r --arg id "$id" '.servers[] | select(.id == $id) | .command' "$SERVERS_JSON")"
    case "$cmd" in
        npx)   warn "$id - npm package (auto-install via npx -y)"; return 0 ;;
        python) warn "$id - python module (perlu pip install)"; return 0 ;;
        *)     return 1 ;;
    esac
}

main() {
    local filter="${1:-}"
    local value="${2:-}"

    if [ -z "$filter" ] || [ ! -f "$SERVERS_JSON" ]; then
        echo "Usage: $0 --priority P0|P1|P2 | --for-plugin <slug> | --server <id>"
        [ -f "$SERVERS_JSON" ] || fail "roadmap tidak ditemukan: $SERVERS_JSON"
        exit 2
    fi

    local servers
    servers=$(get_servers "$filter" "$value")
    if [ -z "$servers" ]; then
        fail "Tidak ada server untuk filter: $filter $value"
        exit 1
    fi

    echo "=== Test MCP servers (filter: $filter $value) ==="
    local total=0 passed=0 warned=0 failed=0
    while IFS= read -r srv; do
        [ -z "$srv" ] && continue
        total=$((total + 1))
        if is_configured "$srv"; then
            if check_installable "$srv"; then
                warned=$((warned + 1))
            else
                pass "$srv (configured)"
                passed=$((passed + 1))
            fi
        else
            fail "$srv (not configured in native agent settings)"
            failed=$((failed + 1))
        fi
    done <<< "$servers"

    echo ""
    echo "=== Summary: total=$total pass=$passed warn=$warned fail=$failed ==="
    [ "$failed" -eq 0 ]
}

main "$@"
