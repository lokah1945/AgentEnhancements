#!/usr/bin/env python3
"""
Universal Context Compression Utility
Uses headroom or native fallback for token optimization
"""

import subprocess
import sys
import os
import json
import re
from pathlib import Path
from typing import Optional

HEADROOM_BIN = os.environ.get("HEADROOM_BIN", "headroom")


def _default_fallback_bin() -> str:
    """Locate the repo-built headroom binary without hardcoding paths."""
    base = os.environ.get("AGENT_ENHANCEMENTS_BASE_DIR")
    if base:
        return os.path.join(base, "headroom", "target", "release", "headroom")
    # Repo layout: <base>/unified-integration/scripts/compress.py
    return str(Path(__file__).resolve().parent.parent.parent / "headroom" / "target" / "release" / "headroom")


FALLBACK_BIN = _default_fallback_bin()

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
                return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            except:
                pass

    if mode == "logs":
        # Detect log format
        if any(re.search(r'\b(ERROR|WARN|INFO|DEBUG|TRACE)\b', line) for line in lines[:50]):
            seen = set()
            unique = []
            for line in lines:
                normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', 'TIMESTAMP', line)
                normalized = re.sub(r'\b[0-9a-f]{8,}\b', 'ID', normalized)
                if normalized not in seen:
                    seen.add(normalized)
                    unique.append(line)
            lines = unique

    if mode == "code":
        # Remove excessive blank lines (keep max 1 consecutive)
        result = []
        blank_count = 0
        for line in lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 1:
                    result.append(line)
            else:
                blank_count = 0
                result.append(line)
        # Deduplicate consecutive identical non-blank lines
        deduped = []
        prev = None
        for line in result:
            if line != prev or line.strip() == "":
                deduped.append(line)
            prev = line
        # Global deduplication of non-blank lines for repeating blocks
        seen = set()
        final = []
        for line in deduped:
            if not line.strip():
                final.append(line)
            elif line not in seen:
                seen.add(line)
                final.append(line)
        lines = final

    elif mode == "generic":
        # Strategy 1: Line-based deduplication
        if len(lines) > 1:
            seen = set()
            unique = []
            for line in lines:
                normalized = ' '.join(line.split())
                if normalized not in seen and normalized:
                    seen.add(normalized)
                    unique.append(line)
            result = '\n'.join(unique)
            if len(result) < len(content) * 0.9:
                lines = unique
                # Good reduction, use it
            else:
                # Line dedup didn't help enough, try other strategies
                lines = unique  # Still use deduped lines as base

        # Strategy 2: Sentence-based deduplication (if not already reduced enough)
        result = '\n'.join(lines)
        if len(result) >= len(content) * 0.9:
            sentences = re.split(r'(?<=[.!?])\s+', content)
            if len(sentences) > 1:
                seen = set()
                unique = []
                for s in sentences:
                    normalized = ' '.join(s.split())
                    if normalized not in seen and normalized:
                        seen.add(normalized)
                        unique.append(s)
                result = ' '.join(unique)
                if len(result) < len(content) * 0.9:
                    return result

        # Strategy 3: Find exact repeating pattern
        result = '\n'.join(lines)
        if len(result) >= len(content) * 0.9:
            n = len(content)
            for i in range(1, min(n // 2 + 1, 1000)):
                if n % i == 0:
                    unit = content[:i]
                    if unit * (n // i) == content:
                        return unit + " ... [repeated " + str(n // i) + " times]"

        # Strategy 4: Fallback - use line-deduped result
        lines = result.split('\n') if isinstance(result, str) else lines

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
