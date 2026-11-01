#!/bin/bash
# Universal context compression wrapper

CONFIG_FILE="/root/agent-enhancements/unified-integration/compression/config.yaml"
INPUT="${1:-/dev/stdin}"
MODE="${2:-auto}"
AGENT="${3:-claude-code}"

# Try headroom first
if command -v headroom &> /dev/null || [ -f "/root/agent-enhancements/headroom/target/release/headroom" ]; then
    HEADROOM_BIN="${HEADROOM_BIN:-headroom}"
    if [ ! -f "$HEADROOM_BIN" ]; then
        HEADROOM_BIN="/root/agent-enhancements/headroom/target/release/headroom"
    fi

    case "$MODE" in
        code|logs|json|markdown|generic)
            "$HEADROOM_BIN" compress --mode "$MODE" < "$INPUT"
            ;;
        auto)
            # Detect content type
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
    esac
else
    # Fallback: basic compression
    cat "$INPUT" | \
        # Remove excessive whitespace
        sed 's/[[:space:]]\+$//' | \
        # Compress repeated lines
        awk '!seen[$0]++' | \
        # Limit output
        head -5000
fi
