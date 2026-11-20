#!/usr/bin/env python3
"""
AgentEnhancements Context Compression — headroom integration + Python fallback.
Provides context window optimization for long-running sessions.
"""

import json
import os
import subprocess
import sys
import shutil
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class CompressionMode(Enum):
    AUTO = "auto"           # Use headroom if available, else Python
    HEADROOM = "headroom"   # Force headroom binary
    PYTHON = "python"       # Force Python fallback
    NONE = "none"           # No compression


@dataclass
class CompressionConfig:
    """Compression configuration."""
    mode: CompressionMode = CompressionMode.AUTO
    budget: int = 200000          # Token budget
    trigger: float = 0.75         # Trigger at 75% of budget
    headroom_binary: str = ""     # Path to headroom binary
    max_input_chars: int = 50000  # Max chars for Python fallback
    preserve_recent: int = 10     # Preserve last N messages
    strip_thinking: bool = True   # Strip thinking/analysis blocks


class ContextCompressor:
    """
    Context compressor with headroom binary and Python fallback.
    """

    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        self._headroom_path = self._find_headroom_binary()

    def _find_headroom_binary(self) -> Optional[str]:
        """Find headroom binary."""
        # Explicit config
        if self.config.headroom_binary and Path(self.config.headroom_binary).exists():
            return self.config.headroom_binary

        # Environment variable
        if os.getenv("HEADROOM_BIN"):
            path = Path(os.getenv("HEADROOM_BIN"))
            if path.exists():
                return str(path)

        # Built in repo
        repo_binary = Path(__file__).parent.parent.parent / "headroom" / "target" / "release" / "headroom"
        if repo_binary.exists():
            return str(repo_binary)

        # PATH
        return shutil.which("headroom")

    def compress(
        self,
        text: str,
        mode: Optional[CompressionMode] = None,
        budget: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Compress text to fit within token budget.
        Returns compressed text and metadata.
        """
        mode = mode or self.config.mode
        budget = budget or self.config.budget

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_tokens = len(text) // 4

        if estimated_tokens <= budget:
            return {
                "compressed": text,
                "original_tokens": estimated_tokens,
                "compressed_tokens": estimated_tokens,
                "ratio": 1.0,
                "method": "none",
                "truncated": False,
            }

        # Try headroom first if available and mode permits
        if mode in (CompressionMode.AUTO, CompressionMode.HEADROOM) and self._headroom_path:
            result = self._compress_headroom(text, budget)
            if result:
                return result

        # Fallback to Python
        if mode in (CompressionMode.AUTO, CompressionMode.PYTHON):
            return self._compress_python(text, budget)

        return {
            "compressed": text[:budget * 4],
            "original_tokens": estimated_tokens,
            "compressed_tokens": budget,
            "ratio": budget / estimated_tokens,
            "method": "truncate",
            "truncated": True,
        }

    def _compress_headroom(self, text: str, budget: int) -> Optional[Dict]:
        """Compress using headroom binary."""
        try:
            # Write input to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(text)
                input_file = f.name

            output_file = input_file + ".out"

            # Run headroom
            cmd = [
                self._headroom_path,
                "compress",
                "--input", input_file,
                "--output", output_file,
                "--budget", str(budget),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # Cleanup
            os.unlink(input_file)
            if os.path.exists(output_file):
                compressed = Path(output_file).read_text()
                os.unlink(output_file)
            else:
                return None

            if result.returncode == 0 and compressed:
                return {
                    "compressed": compressed,
                    "original_tokens": len(text) // 4,
                    "compressed_tokens": len(compressed) // 4,
                    "ratio": len(compressed) / len(text),
                    "method": "headroom",
                    "truncated": len(compressed) < len(text),
                }

        except Exception as e:
            print(f"Headroom compression failed: {e}", file=sys.stderr)

        return None

    def _compress_python(self, text: str, budget: int) -> Dict:
        """Python fallback compression."""
        target_chars = budget * 4
        max_chars = min(self.config.max_input_chars, target_chars)

        if len(text) <= max_chars:
            return {
                "compressed": text,
                "original_tokens": len(text) // 4,
                "compressed_tokens": len(text) // 4,
                "ratio": 1.0,
                "method": "python",
                "truncated": False,
            }

        # Strategy: preserve recent messages, strip thinking, minify JSON
        lines = text.split("\n")

        # Try to parse as conversation (JSON lines or structured)
        compressed = self._smart_truncate(lines, max_chars)

        return {
            "compressed": compressed,
            "original_tokens": len(text) // 4,
            "compressed_tokens": len(compressed) // 4,
            "ratio": len(compressed) / len(text),
            "method": "python",
            "truncated": True,
        }

    def _smart_truncate(self, lines: List[str], max_chars: int) -> str:
        """Smart truncation preserving structure."""
        # Preserve last N messages
        preserve = self.config.preserve_recent

        # Split into messages (heuristic: lines starting with role markers)
        messages = []
        current = []
        for line in lines:
            if line.strip().startswith(("User:", "Assistant:", "Human:", "AI:", "{", "[")):
                if current:
                    messages.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            messages.append("\n".join(current))

        # Keep last N messages fully
        if len(messages) <= preserve:
            return "\n".join(messages)

        preserved = messages[-preserve:]
        preserved_text = "\n".join(preserved)

        # If still too long, truncate earlier messages
        if len(preserved_text) > max_chars:
            # Truncate each preserved message
            truncated = []
            per_msg = max_chars // preserve
            for msg in preserved:
                if len(msg) > per_msg:
                    msg = msg[:per_msg] + "... [truncated]"
                truncated.append(msg)
            return "\n".join(truncated)

        # Add summary of earlier messages
        earlier = messages[:-preserve]
        if earlier:
            summary = f"\n[... {len(earlier)} earlier messages summarized ...]\n"
            # Try to extract key info from earlier
            key_points = self._extract_key_points(earlier)
            if key_points:
                summary += "Key points: " + "; ".join(key_points[:5]) + "\n"

            result = summary + preserved_text
            if len(result) > max_chars:
                return result[:max_chars] + "... [truncated]"
            return result

        return preserved_text

    def _extract_key_points(self, messages: List[str]) -> List[str]:
        """Extract key points from messages."""
        points = []
        for msg in messages:
            # Look for tool calls, errors, decisions
            if any(kw in msg.lower() for kw in ["tool", "error", "decided", "conclusion", "result"]):
                # Extract first meaningful line
                for line in msg.split("\n"):
                    line = line.strip()
                    if len(line) > 20 and not line.startswith(("[", "{", "#")):
                        points.append(line[:100])
                        break
        return points

    def compress_transcript(
        self,
        transcript_path: Path,
        output_path: Optional[Path] = None,
        mode: Optional[CompressionMode] = None
    ) -> Dict:
        """Compress a transcript file."""
        text = transcript_path.read_text(encoding="utf-8")
        result = self.compress(text, mode)

        if output_path:
            output_path.write_text(result["compressed"], encoding="utf-8")

        return result

    def build_headroom(self, headroom_dir: Optional[Path] = None) -> bool:
        """Build headroom from source."""
        if headroom_dir is None:
            headroom_dir = self.base_dir / "headroom"

        if not headroom_dir.exists():
            print("Headroom source not found", file=sys.stderr)
            return False

        try:
            result = subprocess.run(
                ["cargo", "build", "--release"],
                cwd=headroom_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                binary = headroom_dir / "target" / "release" / "headroom"
                if binary.exists():
                    self._headroom_path = str(binary)
                    return True
        except Exception as e:
            print(f"Headroom build failed: {e}", file=sys.stderr)

        return False


# =========================================================================
# CONFIGURATION
# =========================================================================
def load_config(config_path: Path) -> CompressionConfig:
    """Load compression config from YAML."""
    if not config_path.exists():
        return CompressionConfig()

    try:
        with config_path.open() as f:
            data = yaml.safe_load(f) or {}

        config = CompressionConfig(
            mode=CompressionMode(data.get("mode", "auto")),
            budget=data.get("budget", 200000),
            trigger=data.get("trigger", 0.75),
            headroom_binary=data.get("headroom_binary", ""),
            max_input_chars=data.get("max_input_chars", 50000),
            preserve_recent=data.get("preserve_recent", 10),
            strip_thinking=data.get("strip_thinking", True),
        )
        return config
    except Exception:
        return CompressionConfig()


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Context Compression CLI")
    parser.add_argument("command", choices=["compress", "build-headroom", "config"])
    parser.add_argument("input", nargs="?", help="Input file or text")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--mode", choices=["auto", "headroom", "python", "none"], default="auto")
    parser.add_argument("--budget", type=int, default=200000)
    parser.add_argument("--config", help="Config file path")

    args = parser.parse_args()

    config = CompressionConfig()
    if args.config:
        config = load_config(Path(args.config))

    config.mode = CompressionMode(args.mode)
    config.budget = args.budget

    compressor = ContextCompressor(config)

    if args.command == "compress":
        if not args.input:
            parser.error("Input required")

        input_path = Path(args.input)
        if input_path.exists():
            text = input_path.read_text(encoding="utf-8")
        else:
            text = args.input

        result = compressor.compress(text)

        output_text = result["compressed"]
        if args.output:
            Path(args.output).write_text(output_text, encoding="utf-8")
            print(f"Compressed: {result['original_tokens']} -> {result['compressed_tokens']} tokens ({result['method']})")
        else:
            print(output_text)

    elif args.command == "build-headroom":
        headroom_dir = Path(args.input) if args.input else None
        if compressor.build_headroom(headroom_dir):
            print("Headroom built successfully")
        else:
            print("Headroom build failed")
            sys.exit(1)

    elif args.command == "config":
        print(json.dumps({
            "mode": config.mode.value,
            "budget": config.budget,
            "trigger": config.trigger,
            "headroom_binary": config.headroom_binary,
            "headroom_found": compressor._headroom_path is not None,
        }, indent=2))


if __name__ == "__main__":
    # Need to add yaml import
    try:
        import yaml
    except ImportError:
        pass
    main()