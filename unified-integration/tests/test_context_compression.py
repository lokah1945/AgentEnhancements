#!/usr/bin/env python3
"""
Tests for ContextCompressor.
"""

import tempfile
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from context_compression import ContextCompressor, CompressionConfig, CompressionMode, load_config


def test_compression_config_defaults():
    """Test CompressionConfig defaults."""
    config = CompressionConfig()
    assert config.mode == CompressionMode.AUTO
    assert config.budget == 200000
    assert config.trigger == 0.75
    assert config.max_input_chars == 50000
    assert config.preserve_recent == 10
    assert config.strip_thinking == True


def test_compression_mode_enum():
    """Test CompressionMode enum values."""
    assert CompressionMode.PYTHON.value == "python"
    assert CompressionMode.HEADROOM.value == "headroom"
    assert CompressionMode.AUTO.value == "auto"


def test_context_compressor_init():
    """Test ContextCompressor initialization."""
    config = CompressionConfig(mode=CompressionMode.PYTHON)
    compressor = ContextCompressor(config)
    assert compressor.config.mode == CompressionMode.PYTHON


def test_estimate_tokens():
    """Test token estimation."""
    config = CompressionConfig()
    compressor = ContextCompressor(config)

    # Roughly 4 chars per token
    text = "x" * 100
    tokens = compressor._estimate_tokens(text)
    assert tokens == 25


def test_should_compress():
    """Test compression trigger logic."""
    config = CompressionConfig(budget=1000, trigger=0.5)
    compressor = ContextCompressor(config)

    # Under trigger
    short_text = "x" * 100  # ~25 tokens
    assert not compressor._should_compress(short_text)

    # Over trigger
    long_text = "x" * 3000  # ~750 tokens, over 500 trigger
    assert compressor._should_compress(long_text)


def test_compress_under_budget():
    """Test text under budget returns unchanged."""
    config = CompressionConfig(budget=10000, mode=CompressionMode.PYTHON)
    compressor = ContextCompressor(config)

    text = "short text"
    result = compressor.compress(text)

    assert result["compressed"] == text
    assert result["compression_ratio"] == 1.0
    assert result["truncated"] == False


def test_compress_over_budget_python():
    """Test Python compression over budget."""
    config = CompressionConfig(budget=100, mode=CompressionMode.PYTHON)
    compressor = ContextCompressor(config)

    text = "x" * 1000  # ~250 tokens, over budget
    result = compressor.compress(text)

    assert result["compressed_tokens"] < result["original_tokens"]
    assert result["truncated"] == True
    assert result["mode"] == "python"


def test_compress_strips_thinking():
    """Test thinking block stripping."""
    config = CompressionConfig(budget=10, mode=CompressionMode.PYTHON, strip_thinking=True)
    compressor = ContextCompressor(config)

    text = "before <thinking>secret thoughts</thinking> after"
    result = compressor.compress(text)

    assert "<thinking>" not in result["compressed"]
    assert "secret thoughts" not in result["compressed"]
    assert "before" in result["compressed"]
    assert "after" in result["compressed"]


def test_compress_preserves_recent():
    """Test recent content preservation."""
    config = CompressionConfig(budget=50, mode=CompressionMode.PYTHON, preserve_recent=2)
    compressor = ContextCompressor(config)

    # Create text with many lines
    lines = [f"line {i}" for i in range(20)]
    text = "\n".join(lines)

    result = compressor.compress(text)

    # Should preserve last 2 lines
    assert "line 18" in result["compressed"]
    assert "line 19" in result["compressed"]


def test_compress_max_input_chars():
    """Test max_input_chars truncation."""
    config = CompressionConfig(budget=50, mode=CompressionMode.PYTHON, max_input_chars=100)
    compressor = ContextCompressor(config)

    text = "x" * 500
    result = compressor.compress(text)

    assert len(result["compressed"]) <= 100 + 50  # 100 + truncation marker


def test_load_config_from_yaml():
    """Test loading config from YAML."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
mode: python
budget: 150000
trigger: 0.8
headroom_binary: ""
max_input_chars: 30000
preserve_recent: 5
strip_thinking: false
""")
        config_path = Path(f.name)

    try:
        config = load_config(config_path)
        assert config.mode == CompressionMode.PYTHON
        assert config.budget == 150000
        assert config.trigger == 0.8
        assert config.max_input_chars == 30000
        assert config.preserve_recent == 5
        assert config.strip_thinking == False
    finally:
        config_path.unlink()


def test_load_config_missing_file():
    """Test loading config from missing file returns defaults."""
    config = load_config(Path("/nonexistent/path.yaml"))
    assert config.mode == CompressionMode.AUTO
    assert config.budget == 200000


def test_compression_result_structure():
    """Test compression result has all required fields."""
    config = CompressionConfig(mode=CompressionMode.PYTHON, budget=100)
    compressor = ContextCompressor(config)

    result = compressor.compress("x" * 1000)

    required_fields = ["compressed", "original_tokens", "compressed_tokens",
                       "compression_ratio", "mode", "truncated"]
    for field in required_fields:
        assert field in result


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])