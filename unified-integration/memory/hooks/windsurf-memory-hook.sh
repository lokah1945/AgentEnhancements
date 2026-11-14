#!/bin/bash
# Bash wrapper for memory hook - delegates to Python script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT="windsurf"
exec python3 "$SCRIPT_DIR/${AGENT}-memory-hook.py" "$@"
