#!/bin/bash
# Universal context compression wrapper

set -euo pipefail

# Resolve the installation root from this script's location; the
# AGENT_ENHANCEMENTS_BASE_DIR environment variable overrides it.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(dirname "$SCRIPT_DIR")"
BASE_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-$(dirname "$UNIFIED_DIR")}"
CONFIG_FILE="$UNIFIED_DIR/compression/config.yaml"

INPUT="${1:-/dev/stdin}"
MODE="${2:-auto}"
AGENT="${3:-claude-code}"

# Find headroom binary: env override first, then repo build, then PATH
HEADROOM_BIN="${HEADROOM_BIN:-}"
if [ -z "$HEADROOM_BIN" ]; then
    if [ -x "$BASE_DIR/headroom/target/release/headroom" ]; then
        HEADROOM_BIN="$BASE_DIR/headroom/target/release/headroom"
    elif command -v headroom &> /dev/null; then
        HEADROOM_BIN="headroom"
    fi
fi

# Read stdin once into a temp file so content detection and compression
# both see the full stream. Previously the detection pass consumed stdin
# and the compression pass received nothing.
TMP_INPUT="$(mktemp "${TMPDIR:-/tmp}/compress-input.XXXXXX")"
trap 'rm -f "$TMP_INPUT"' EXIT
if [ "$INPUT" = "-" ] || [ "$INPUT" = "/dev/stdin" ]; then
    cat > "$TMP_INPUT"
    INPUT="$TMP_INPUT"
fi

if [ -n "$HEADROOM_BIN" ]; then
    case "$MODE" in
        code|logs|json|markdown|generic)
            "$HEADROOM_BIN" compress --mode "$MODE" < "$INPUT"
            ;;
        auto)
            # Detect content type from the first 100 lines
            if head -100 "$INPUT" | grep -q '^{' && head -100 "$INPUT" | grep -q '}'; then
                "$HEADROOM_BIN" compress --mode json < "$INPUT"
            elif head -100 "$INPUT" | grep -q '^```'; then
                "$HEADROOM_BIN" compress --mode code < "$INPUT"
            elif head -100 "$INPUT" | grep -qE '(ERROR|WARN|INFO|DEBUG).*\['; then
                "$HEADROOM_BIN" compress --mode logs < "$INPUT"
            else
                "$HEADROOM_BIN" compress --mode generic < "$INPUT"
            fi
            ;;
        *)
            echo "Unknown mode: $MODE (use auto, code, logs, json, markdown or generic)" >&2
            exit 1
            ;;
    esac
else
    # Fallback: basic compression without headroom.
    # "|| true" because head closing the pipe early (truncation at 5000
    # lines) raises SIGPIPE for upstream stages under "set -o pipefail",
    # which is expected behaviour here, not an error.
    cat "$INPUT" | \
        # Remove trailing whitespace
        sed 's/[[:space:]]\+$//' | \
        # Compress repeated lines (keep first occurrence)
        awk '!seen[$0]++' | \
        # Limit output
        head -5000 || true
fi
