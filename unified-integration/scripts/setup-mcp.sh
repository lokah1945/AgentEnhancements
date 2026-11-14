#!/usr/bin/env bash
# setup-mcp.sh — install the 9 in-house MCP servers into agent CLI configs.
#
# Usage:
#   bash unified-integration/scripts/setup-mcp.sh             # install/refresh
#   bash unified-integration/scripts/setup-mcp.sh --check     # health-check only
#
# What it does:
#   1. Resolves the absolute repo root.
#   2. Verifies the mcp Python SDK (fastmcp) is importable; prints an
#      actionable install hint when missing.
#   3. Renders mcp.json blocks from mcp.json.example with real paths.
#   4. Merges (never overwrites) the servers into:
#        ~/.claude/mcp.json (Claude Code)      ~/.cursor/mcp.json (Cursor)
#        ~/.continue/mcp.json (Continue)       ~/.windsurf/mcp.json (Windsurf)
#        ~/.codex/mcp.json   (Codex CLI)       ~/.agents/mcp.json (generic)
#      Existing user servers are preserved; ours are refreshed in place.
#
# The 29 to-install upstream servers are intentionally NOT touched here
# (they need API keys + consent — see docs/MCP_INTEGRATION_CHECKLIST.md).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVERS_DIR="$REPO_ROOT/unified-integration/mcp-servers"
TEMPLATE="$SERVERS_DIR/mcp.json.example"
MODE="${1:-install}"

BUILT_SERVERS=(
  embeddings-mcp task-router-mcp ffmpeg-mcp vision-mcp
  graphrag-mcp arxiv-mcp google-news-mcp video-mcp style-mcp
)

TARGETS=(
  "$HOME/.claude/mcp.json"
  "$HOME/.cursor/mcp.json"
  "$HOME/.continue/mcp.json"
  "$HOME/.codex/mcp.json"
  "$HOME/.windsurf/mcp.json"
  "$HOME/.agents/mcp.json"
)

log() { printf '[setup-mcp] %s\n' "$*"; }
die() { printf '[setup-mcp] ERROR: %s\n' "$*" >&2; exit 1; }

# --- 1. sanity ------------------------------------------------------------
[[ -f "$TEMPLATE" ]] || die "template missing: $TEMPLATE"
for slug in "${BUILT_SERVERS[@]}"; do
  [[ -f "$SERVERS_DIR/$slug/server.py" ]] || die "server missing: $slug/server.py"
done

if ! python3 -c "import mcp" 2>/dev/null; then
  die "the 'mcp' Python SDK is not importable.
  Install it first:  pip install 'mcp>=1.0'
  (or: pip install -r unified-integration/mcp-servers/*/requirements.txt)"
fi

# --- 2. health check (per server) -----------------------------------------
check_one() {
  local slug="$1"
  if python3 - "$SERVERS_DIR/$slug/server.py" <<'PY' >/dev/null 2>&1
import importlib.util, sys
spec = importlib.util.spec_from_file_location("srv", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
health = mod.TOOLS["health"]()
sys.exit(0 if health.get("status") == "ok" else 1)
PY
  then
    printf '  [ok]   %s\n' "$slug"
    return 0
  else
    printf '  [FAIL] %s (see python3 %s/server.py + import mcp)\n' "$slug" "$SERVERS_DIR/$slug"
    return 1
  fi
}

if [[ "$MODE" == "--check" ]]; then
  log "health check: ${#BUILT_SERVERS[@]} built servers"
  failed=0
  for slug in "${BUILT_SERVERS[@]}"; do
    check_one "$slug" || failed=1
  done
  if [[ $failed -ne 0 ]]; then die "health check failed"; fi
  log "all servers healthy"
  exit 0
fi

# --- 3. render the block for our servers ----------------------------------
render_block() {
  python3 - "$TEMPLATE" "$REPO_ROOT" <<'PY'
import json, sys
template = json.load(open(sys.argv[1]))
root = sys.argv[2]
block = {}
for name, cfg in template["mcpServers"].items():
    cfg = dict(cfg)
    cfg["args"] = [a.replace("PLACEHOLDER_REPO_ROOT", root) for a in cfg["args"]]
    block[name] = cfg
print(json.dumps(block, indent=2))
PY
}

BLOCK="$(render_block)"

# --- 4. merge into each target (existing user servers preserved) ----------
merge_target() {
  local target="$1"
  mkdir -p "$(dirname "$target")"
  if [[ ! -f "$target" ]]; then
    printf '{"mcpServers": %s}\n' "$BLOCK" > "$target"
    printf '  [new]  %s\n' "$target"
    return
  fi
  if ! python3 -m json.tool "$target" >/dev/null 2>&1; then
    printf '  [skip] %s (invalid JSON — not touching it)\n' "$target"
    return
  fi
  python3 - "$target" "$BLOCK" <<'PY'
import json, sys
target, block = sys.argv[1], json.loads(sys.argv[2])
doc = json.load(open(target))
servers = doc.setdefault("mcpServers", {})
if not isinstance(servers, dict):
    print(f"  [skip] {target} (mcpServers is not an object)")
    raise SystemExit(0)
servers.update(block)
doc["mcpServers"] = dict(sorted(servers.items()))
with open(target, "w") as fh:
    json.dump(doc, fh, indent=2)
    fh.write("\n")
print(f"  [merge] {target}")
PY
}

log "installing ${#BUILT_SERVERS[@]} built servers into agent configs"
for target in "${TARGETS[@]}"; do
  merge_target "$target"
done

log "done. verify with: bash unified-integration/scripts/setup-mcp.sh --check"
log "note: the 29 to-install upstream servers need API keys — see"
log "      docs/MCP_INTEGRATION_CHECKLIST.md (Phase 1: P0 servers first)."
