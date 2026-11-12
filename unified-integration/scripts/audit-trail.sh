#!/usr/bin/env bash
# Audit trail helper: append structured entries to the runtime audit logs.
# Logs live in unified-integration/memory/audit/*.jsonl
#
# Usage:
#   bash audit-trail.sh mcp-call <server> <tool> <args_hash> <result_summary>
#   bash audit-trail.sh video <plugin> <intent> <input_hash> <output_path> [approved_by]
#   bash audit-trail.sh decision <slug> <decision_text>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AUDIT_DIR="$UNIFIED_DIR/memory/audit"

log_info()  { echo -e "\033[0;34m[audit]\033[0m $1"; }

append_entry() {
    local log_file="$1"
    local entry="$2"
    mkdir -p "$(dirname "$log_file")"
    touch "$log_file"
    echo "$entry" >> "$log_file"
    log_info "logged to $log_file"
}

entry_type="${1:-}"
shift || true

ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

case "$entry_type" in
    mcp-call)
        [ $# -ge 4 ] || { echo "Usage: $0 mcp-call <server> <tool> <args_hash> <result_summary>"; exit 2; }
        entry=$(jq -c -n --arg ts "$ts" --arg s "$1" --arg t "$2" --arg ah "$3" --arg rs "$4" \
          '{timestamp: $ts, server: $s, tool: $t, args_hash: $ah, result_summary: $rs}')
        append_entry "$AUDIT_DIR/mcp-calls.jsonl" "$entry"
        ;;
    video)
        [ $# -ge 4 ] || { echo "Usage: $0 video <plugin> <intent> <input_hash> <output_path> [approved_by]"; exit 2; }
        approved_by="${5:-user}"
        entry=$(jq -c -n --arg ts "$ts" --arg p "$1" --arg i "$2" --arg ih "$3" --arg op "$4" --arg ab "$approved_by" \
          '{timestamp: $ts, plugin: $p, intent: $i, input_hash: $ih, output_path: $op, approved_by: $ab}')
        append_entry "$AUDIT_DIR/video.jsonl" "$entry"
        ;;
    decision)
        [ $# -ge 2 ] || { echo "Usage: $0 decision <slug> <decision_text>"; exit 2; }
        entry=$(jq -c -n --arg ts "$ts" --arg s "$1" --arg d "$2" \
          '{timestamp: $ts, slug: $s, decision: $d}')
        append_entry "$AUDIT_DIR/decisions.jsonl" "$entry"
        ;;
    *)
        echo "Usage: $0 <mcp-call|video|decision> <args...>"
        echo "  mcp-call <server> <tool> <args_hash> <result_summary>"
        echo "  video <plugin> <intent> <input_hash> <output_path> [approved_by]"
        echo "  decision <slug> <decision_text>"
        exit 2
        ;;
esac
