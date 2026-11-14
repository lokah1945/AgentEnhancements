#!/bin/bash
# Universal context compression wrapper; consumes stdin exactly once.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(dirname "$SCRIPT_DIR")"
INPUT="${1:-/dev/stdin}"
MODE="${2:-auto}"
AGENT="${3:-claude-code}"
case "$MODE" in
    auto|code|logs|json|markdown|generic) ;;
    *) printf 'Unknown mode: %s\n' "$MODE" >&2; exit 2 ;;
esac
if [ "$INPUT" = "-" ]; then INPUT=/dev/stdin; fi
exec python3 "$UNIFIED_DIR/scripts/compress.py" "$MODE" "$AGENT" < "$INPUT"
