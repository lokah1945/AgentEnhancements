#!/bin/bash
# Universal context compression wrapper

CONFIG_FILE="/root/agent-enhancements/unified-integration/compression/config.yaml"
INPUT="${1:-/dev/stdin}"
MODE="${2:-auto}"
AGENT="${3:-claude-code}"

# Find headroom binary
HEADROOM_BIN=""
if [ -f "/root/agent-enhancements/headroom/target/release/headroom" ]; then
    HEADROOM_BIN="/root/agent-enhancements/headroom/target/release/headroom"
elif command -v headroom &> /dev/null; then
    HEADROOM_BIN="headroom"
fi

if [ -n "$HEADROOM_BIN" ]; then
    case "$MODE" in
        code|logs|json|markdown|generic)
            "$HEADROOM_BIN" compress --mode "$MODE" < "$INPUT"
            ;;
        auto)
            # Detect content type
            # Read first 100 lines for detection
            head -100 "$INPUT" > /tmp/compress_input_$$
            if grep -q '^{' /tmp/compress_input_$$ && grep -q '}' /tmp/compress_input_$$; then
                "$HEADROOM_BIN" compress --mode json < "$INPUT"
            elif grep -q '^```' /tmp/compress_input_$$; then
                "$HEADROOM_BIN" compress --mode code < "$INPUT"
            elif grep -qE '(ERROR|WARN|INFO|DEBUG).*\[' /tmp/compress_input_$$; then
                "$HEADROOM_BIN" compress --mode logs < "$INPUT"
            else
                "$HEADROOM_BIN" compress --mode generic < "$INPUT"
            fi
            rm -f /tmp/compress_input_$$
            ;;
    esac
else
    # Fallback: basic compression
    cat "$INPUT" | \
        # Remove trailing whitespace
        sed 's/[[:space:]]\+$//' | \
        # Compress repeated lines (keep first occurrence)
        awk '!seen[$0]++' | \
        # Limit output
        head -5000
fi
