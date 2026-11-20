#!/usr/bin/env python3
"""Tests for compression.py"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from context_compression import ContextCompressor, CompressionConfig, CompressionMode


def test_compress_no_op():
    """Test compression when text fits in budget."""
    config = CompressionConfig(budget=10000)
    compressor = ContextCompressor(config)

    text = "Short text that fits"
    result = compressor.compress(text)

    assert result["compressed"] == text
    assert result["method"] == "none"
    assert not result["truncated"]
    print("✓ No-op compression works")


def test_compress_truncate():
    """Test Python fallback truncation."""
    config = CompressionConfig(budget=10, mode=CompressionMode.PYTHON)
    compressor = ContextCompressor(config)

    # Use conversation format to trigger smart truncation
    text = "\n".join([f"User: Message {i}" for i in range(100)])  # ~1000 chars
    result = compressor.compress(text)

    assert result["method"] == "python"
    assert result["truncated"]
    assert len(result["compressed"]) < len(text)
    print("✓ Python truncation works")


def test_smart_truncate():
    """Test smart truncation preserves recent messages."""
    config = CompressionConfig(budget=100, mode=CompressionMode.PYTHON)
    compressor = ContextCompressor(config)

    # Create conversation-like text
    text = "\n".join([
        "User: First message",
        "Assistant: First response",
        "User: Second message",
        "Assistant: Second response",
        "User: Third message",
        "Assistant: Third response",
    ])

    result = compressor.compress(text)
    compressed = result["compressed"]

    # Should preserve recent messages
    assert "Third message" in compressed
    assert "Third response" in compressed
    print("✓ Smart truncation preserves recent")


def test_compress_transcript():
    """Test compressing a transcript file."""
    config = CompressionConfig(budget=100, mode=CompressionMode.PYTHON)
    compressor = ContextCompressor(config)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write("User: Hello\nAssistant: Hi there!\n" * 50)
        input_path = Path(f.name)

    with tempfile.NamedTemporaryFile(suffix='.out', delete=False) as f:
        output_path = Path(f.name)

    try:
        result = compressor.compress_transcript(input_path, output_path)
        assert result["method"] == "python"
        assert output_path.exists()
        compressed_text = output_path.read_text()
        assert len(compressed_text) < input_path.stat().st_size
    finally:
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)

    print("✓ Transcript compression works")


def test_config_loading():
    """Test loading config from YAML."""
    from context_compression import load_config
    import yaml

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            "mode": "python",
            "budget": 50000,
            "trigger": 0.8,
            "max_input_chars": 10000,
            "preserve_recent": 5,
        }, f)
        config_path = Path(f.name)

    try:
        config = load_config(config_path)
        assert config.mode == CompressionMode.PYTHON
        assert config.budget == 50000
        assert config.trigger == 0.8
        assert config.max_input_chars == 10000
        assert config.preserve_recent == 5
    finally:
        config_path.unlink()

    print("✓ Config loading works")


def test_headroom_not_found():
    """Test behavior when headroom not found."""
    config = CompressionConfig(mode=CompressionMode.AUTO, headroom_binary="/nonexistent/headroom")
    compressor = ContextCompressor(config)

    # Should fall back to Python
    assert compressor._headroom_path is None
    result = compressor.compress("x" * 10000, budget=100)
    assert result["method"] == "python"
    print("✓ Headroom fallback works")


if __name__ == "__main__":
    test_compress_no_op()
    test_compress_truncate()
    test_smart_truncate()
    test_compress_transcript()
    test_config_loading()
    test_headroom_not_found()
    print("\n✅ All compression tests passed!")