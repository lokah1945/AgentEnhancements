#!/usr/bin/env python3
"""
AgentEnhancements Context Compression — Python fallback with headroom binary support.
Ported from DELL branch with ASUS headroom integration.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class CompressionMode(Enum):
    """Compression mode."""
    PYTHON = "python"      # Pure Python implementation
    HEADROOM = "headroom"  # Rust headroom binary
    AUTO = "auto"          # Try headroom, fallback to Python


@dataclass
class CompressionConfig:
    """Configuration for context compression."""
    mode: CompressionMode = CompressionMode.AUTO
    budget: int = 200000
    trigger: float = 0.75
    headroom_binary: str = ""
    max_input_chars: int = 50000
    preserve_recent: int = 10
    strip_thinking: bool = True


@dataclass
class CompressionResult:
    """Result of compression operation."""
    original_text: str
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    mode_used: CompressionMode
    truncated: bool = False


class ContextCompressor:
    """
    Context compressor with multiple backends.
    Supports headroom binary (Rust) and Python fallback.
    """

    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        self._headroom_path = self._find_headroom()

    def _find_headroom(self) -> Optional[Path]:
        """Find headroom binary."""
        if self.config.headroom_binary:
            p = Path(self.config.headroom_binary)
            if p.exists():
                return p

        # Search common locations
        search_paths = [
            Path(__file__).resolve().parent.parent.parent / "headroom" / "target" / "release" / "headroom",
            Path(__file__).resolve().parent.parent.parent / "headroom" / "target" / "release" / "headroom.exe",
            Path(shutil.which("headroom") or ""),
        ]

        for p in search_paths:
            if p.exists():
                return p
        return None

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: 4 chars per token)."""
        return len(text) // 4

    def _should_compress(self, text: str) -> bool:
        """Check if text should be compressed based on budget and trigger."""
        tokens = self._estimate_tokens(text)
        return tokens >= self.config.budget * self.config.trigger

    def _compress_python(self, text: str, budget: int) -> CompressionResult:
        """Pure Python compression implementation."""
        original_tokens = self._estimate_tokens(text)

        if not self._should_compress(text):
            return CompressionResult(
                original_text=text,
                compressed_text=text,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                compression_ratio=1.0,
                mode_used=CompressionMode.PYTHON,
            )

        # Strategy 1: Strip thinking blocks if enabled
        compressed = text
        if self.config.strip_thinking:
            # Remove <thinking>...</thinking> blocks
            compressed = re.sub(r'<thinking>.*?</thinking>', '', compressed, flags=re.DOTALL)
            # Remove 【...】 blocks (common in some outputs)
            compressed = re.sub(r'【[^】]*】', '', compressed)

        # Strategy 2: Truncate to max_input_chars
        if len(compressed) > self.config.max_input_chars:
            compressed = compressed[:self.config.max_input_chars]
            compressed += "\n\n[... truncated due to context budget ...]"

        # Strategy 3: Preserve recent content (last N lines/paragraphs)
        lines = compressed.split('\n')
        if len(lines) > self.config.preserve_recent * 2:
            # Keep first portion and last N lines
            keep_first = len(lines) - self.config.preserve_recent
            compressed = '\n'.join(lines[:keep_first]) + '\n\n[... middle content compressed ...]\n' + '\n'.join(lines[-self.config.preserve_recent:])

        compressed_tokens = self._estimate_tokens(compressed)

        # If still over budget, aggressive truncation
        if compressed_tokens > budget:
            # Calculate target chars
            target_chars = budget * 4
            if len(compressed) > target_chars:
                compressed = compressed[:target_chars] + "\n\n[... aggressively truncated ...]"
                compressed_tokens = self._estimate_tokens(compressed)

        return CompressionResult(
            original_text=text,
            compressed_text=compressed,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compressed_tokens / original_tokens if original_tokens > 0 else 1.0,
            mode_used=CompressionMode.PYTHON,
            truncated=compressed_tokens < original_tokens,
        )

    def _compress_headroom(self, text: str, budget: int) -> CompressionResult:
        """Compress using headroom binary."""
        if not self._headroom_path:
            raise RuntimeError("headroom binary not found")

        original_tokens = self._estimate_tokens(text)

        try:
            # headroom compress --mode <mode> --budget <budget>
            mode_map = {
                "code": "code",
                "logs": "logs",
                "json": "json",
                "markdown": "markdown",
                "generic": "generic",
            }
            # Auto-detect content type
            content_mode = "generic"
            if text.strip().startswith('{') or text.strip().startswith('['):
                content_mode = "json"
            elif '```' in text or text.count('\n') > 20:
                content_mode = "code"

            cmd = [
                str(self._headroom_path),
                "compress",
                "--mode", content_mode,
                "--budget", str(budget),
            ]

            result = subprocess.run(
                cmd,
                input=text.encode('utf-8'),
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"headroom failed: {result.stderr.decode('utf-8', errors='replace')}")

            compressed = result.stdout.decode('utf-8', errors='replace')
            compressed_tokens = self._estimate_tokens(compressed)

            return CompressionResult(
                original_text=text,
                compressed_text=compressed,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                compression_ratio=compressed_tokens / original_tokens if original_tokens > 0 else 1.0,
                mode_used=CompressionMode.HEADROOM,
                truncated=compressed_tokens < original_tokens,
            )

        except Exception as e:
            raise RuntimeError(f"headroom compression failed: {e}")

    def compress(self, text: str, budget: Optional[int] = None) -> Dict[str, Any]:
        """
        Compress text using configured mode.
        Returns dict with compressed text and metadata.
        """
        budget = budget or self.config.budget
        original_tokens = self._estimate_tokens(text)

        # If text is already under budget, return as-is
        if original_tokens <= budget:
            return {
                "compressed": text,
                "original_tokens": original_tokens,
                "compressed_tokens": original_tokens,
                "compression_ratio": 1.0,
                "mode": self.config.mode.value,
                "truncated": False,
            }

        # Try configured mode
        modes_to_try = []
        if self.config.mode == CompressionMode.AUTO:
            if self._headroom_path:
                modes_to_try = [CompressionMode.HEADROOM, CompressionMode.PYTHON]
            else:
                modes_to_try = [CompressionMode.PYTHON]
        elif self.config.mode == CompressionMode.HEADROOM:
            if self._headroom_path:
                modes_to_try = [CompressionMode.HEADROOM, CompressionMode.PYTHON]
            else:
                modes_to_try = [CompressionMode.PYTHON]
        else:
            modes_to_try = [CompressionMode.PYTHON]

        last_error = None
        for mode in modes_to_try:
            try:
                if mode == CompressionMode.HEADROOM:
                    result = self._compress_headroom(text, budget)
                else:
                    result = self._compress_python(text, budget)

                return {
                    "compressed": result.compressed_text,
                    "original_tokens": result.original_tokens,
                    "compressed_tokens": result.compressed_tokens,
                    "compression_ratio": result.compression_ratio,
                    "mode": result.mode_used.value,
                    "truncated": result.truncated,
                }

            except Exception as e:
                last_error = e
                continue

        # All modes failed - return original with warning
        print(f"[ContextCompressor] All compression modes failed: {last_error}", file=sys.stderr)
        return {
            "compressed": text,
            "original_tokens": original_tokens,
            "compressed_tokens": original_tokens,
            "compression_ratio": 1.0,
            "mode": "none (failed)",
            "truncated": False,
        }


def load_config(config_path: Path) -> CompressionConfig:
    """Load compression config from YAML file."""
    if not config_path.exists():
        return CompressionConfig()

    try:
        import yaml
        data = yaml.safe_load(config_path.read_text()) or {}
    except Exception:
        return CompressionConfig()

    return CompressionConfig(
        mode=CompressionMode(data.get("mode", "auto")),
        budget=data.get("budget", 200000),
        trigger=data.get("trigger", 0.75),
        headroom_binary=data.get("headroom_binary", ""),
        max_input_chars=data.get("max_input_chars", 50000),
        preserve_recent=data.get("preserve_recent", 10),
        strip_thinking=data.get("strip_thinking", True),
    )


def main():
    """CLI for testing."""
    import argparse
    parser = argparse.ArgumentParser(description="Context Compression CLI")
    parser.add_argument("text", nargs="?", help="Text to compress (stdin if omitted)")
    parser.add_argument("--budget", type=int, default=200000, help="Token budget")
    parser.add_argument("--mode", choices=["auto", "python", "headroom"], default="auto")
    parser.add_argument("--config", type=Path, help="Config YAML path")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    args = parser.parse_args()

    if args.stdin or args.text is None:
        text = sys.stdin.read()
    else:
        text = args.text

    if args.config:
        config = load_config(args.config)
    else:
        config = CompressionConfig(mode=CompressionMode(args.mode), budget=args.budget)

    compressor = ContextCompressor(config)
    result = compressor.compress(text, budget=args.budget)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()