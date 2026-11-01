#!/usr/bin/env python3
"""
Universal Context Compression Utility
Uses headroom or native fallback for token optimization
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from typing import Optional

HEADROOM_BIN = os.environ.get("HEADROOM_BIN", "headroom")
FALLBACK_BIN = "/root/agent-enhancements/headroom/target/release/headroom"

def get_headroom_bin() -> Optional[str]:
    """Find headroom binary"""
    for bin_path in [HEADROOM_BIN, FALLBACK_BIN]:
        if bin_path and os.path.exists(bin_path):
            return bin_path
        try:
            result = subprocess.run(["which", bin_path], capture_output=True)
            if result.returncode == 0:
                return result.stdout.decode().strip()
        except:
            pass
    return None

def compress_content(content: str, mode: str = "auto", agent: str = "claude-code") -> str:
    """Compress content using headroom or fallback"""

    headroom = get_headroom_bin()

    if headroom:
        try:
            result = subprocess.run(
                [headroom, "compress", "--mode", mode],
                input=content.encode(),
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.decode()
        except Exception as e:
            print(f"Headroom error: {e}", file=sys.stderr)

    # Fallback compression
    return fallback_compress(content, mode)

def fallback_compress(content: str, mode: str) -> str:
    """Native Python fallback compression"""
    lines = content.split('\n')

    if mode in ("json", "auto"):
        # Try to detect and compress JSON
        if content.strip().startswith(('{', '[')):
            try:
                data = json.loads(content)
                # Remove null values, empty arrays/objects
                def clean(obj):
                    if isinstance(obj, dict):
                        return {k: clean(v) for k, v in obj.items() if v is not None and v != [] and v != {}}
                    elif isinstance(obj, list):
                        return [clean(v) for v in obj if v is not None and v != [] and v != {}]
                    return obj
                cleaned = clean(data)
                return json.dumps(cleaned, separators=(',', ':'))
            except:
                pass

    if mode in ("logs", "auto"):
        # Detect log format
        if any(re.search(r'\b(ERROR|WARN|INFO|DEBUG|TRACE)\b', line) for line in lines[:50]):
            # Keep only unique log lines, preserve first occurrence
            seen = set()
            unique = []
            for line in lines:
                # Normalize timestamps/IDs
                normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', 'TIMESTAMP', line)
                normalized = re.sub(r'\b[0-9a-f]{8,}\b', 'ID', normalized)
                if normalized not in seen:
                    seen.add(normalized)
                    unique.append(line)
            lines = unique

    if mode in ("code", "auto"):
        # Preserve code structure, trim comments/whitespace
        # Simple heuristic: keep lines with code, trim excessive blank lines
        compressed = []
        blank_count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_count += 1
                if blank_count <= 2:  # Max 2 blank lines
                    compressed.append(line)
            else:
                blank_count = 0
                compressed.append(line)
        lines = compressed

    # Limit total size
    result = '\n'.join(lines)
    if len(result) > 50000:  # ~12k tokens
        result = result[:50000] + "\n... [truncated]"

    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: compress.py <mode> [agent] < input.txt")
        print("Modes: auto, code, logs, json, markdown, generic")
        sys.exit(1)

    mode = sys.argv[1]
    agent = sys.argv[2] if len(sys.argv) > 2 else "claude-code"

    content = sys.stdin.read()
    compressed = compress_content(content, mode, agent)
    print(compressed)

if __name__ == "__main__":
    main()
