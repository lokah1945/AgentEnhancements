#!/usr/bin/env python3
"""
Tests for MemoryManager v2.
"""

import json
import tempfile
import time
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from memory_v2 import MemoryManager


def test_memory_manager_init():
    """Test MemoryManager initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)
        assert mgr.memory_dir == Path(tmpdir)
        assert mgr.db_path == Path(tmpdir) / "memory.db"
        assert mgr.db_path.exists()


def test_memory_manager_save_load():
    """Test basic save and load."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        # Save a value
        mgr.save("test_key", {"foo": "bar", "count": 42}, "session_context")

        # Load it back
        value = mgr.load("test_key", "session_context")
        assert value == {"foo": "bar", "count": 42}


def test_memory_manager_save_load_string():
    """Test save/load with string value."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("string_key", "hello world", "persistent")
        value = mgr.load("string_key", "persistent")
        assert value == "hello world"


def test_memory_manager_upsert_merge():
    """Test upsert merges dict values."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("merge_key", {"a": 1, "b": 2}, "session_context")
        mgr.save("merge_key", {"b": 3, "c": 4}, "session_context")

        value = mgr.load("merge_key", "session_context")
        assert value == {"a": 1, "b": 3, "c": 4}


def test_memory_manager_multiple_types():
    """Test different memory types."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("key1", "session", "session_context")
        mgr.save("key2", "persistent", "persistent")
        mgr.save("key3", "preference", "user_preference")

        assert mgr.load("key1", "session_context") == "session"
        assert mgr.load("key2", "persistent") == "persistent"
        assert mgr.load("key3", "user_preference") == "preference"


def test_memory_manager_session_isolation():
    """Test session_id isolates memories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("key", "session1", "session_context", session_id="sess1")
        mgr.save("key", "session2", "session_context", session_id="sess2")

        assert mgr.load("key", "session_context", session_id="sess1") == "session1"
        assert mgr.load("key", "session_context", session_id="sess2") == "session2"


def test_memory_manager_global_fallback():
    """Test global (empty session_id) fallback."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("key", "global", "session_context", session_id="")
        mgr.save("key", "session", "session_context", session_id="sess1")

        # Session-specific should win
        assert mgr.load("key", "session_context", session_id="sess1") == "session"
        # Global fallback when session not found
        assert mgr.load("key", "session_context", session_id="sess2") == "global"


def test_memory_manager_list():
    """Test listing memories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("key1", "value1", "session_context")
        mgr.save("key2", "value2", "persistent")
        mgr.save("key3", "value3", "session_context")

        items = mgr.list(limit=10)
        assert len(items) == 3

        session_items = mgr.list(memory_type="session_context")
        assert len(session_items) == 2


def test_memory_manager_recall_session():
    """Test recall_session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("old", "old_value", "session_context", session_id="sess1")
        time.sleep(0.01)
        mgr.save("new", "new_value", "session_context", session_id="sess1")

        items = mgr.recall_session("sess1", max_age_days=7, limit=10)
        assert len(items) == 2
        # Should be ordered by updated_at DESC
        assert items[0]["key"] == "new"
        assert items[1]["key"] == "old"


def test_memory_manager_cleanup_expired():
    """Test cleanup_expired removes expired entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        # Save with very short TTL (1 second)
        mgr.save("expire_key", "will_expire", "session_context", ttl_override=1)
        mgr.save("keep_key", "will_keep", "persistent")

        time.sleep(1.1)

        removed = mgr.cleanup_expired()
        assert removed >= 1

        assert mgr.load("expire_key", "session_context") is None
        assert mgr.load("keep_key", "persistent") == "will_keep"


def test_memory_manager_stats():
    """Test stats method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("k1", "v1", "session_context")
        mgr.save("k2", "v2", "persistent")
        mgr.save("k3", "v3", "user_preference")

        stats = mgr.stats()
        assert stats["total_entries"] == 3
        assert stats["by_type"]["session_context"] == 1
        assert stats["by_type"]["persistent"] == 1
        assert stats["by_type"]["user_preference"] == 1
        assert stats["db_size_bytes"] > 0


def test_memory_manager_ttl_policies():
    """Test TTL policies are defined."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        assert "session_context" in mgr.TTL_POLICIES
        assert "persistent" in mgr.TTL_POLICIES
        assert "user_preference" in mgr.TTL_POLICIES
        assert "skill_usage" in mgr.TTL_POLICIES
        assert "task_observer" in mgr.TTL_POLICIES

        assert mgr.TTL_POLICIES["persistent"] is None
        assert mgr.TTL_POLICIES["session_context"] == 7 * 24 * 3600


def test_memory_manager_delete():
    """Test delete method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("key", "value", "session_context")
        assert mgr.load("key", "session_context") == "value"

        mgr.delete("key", "session_context")
        assert mgr.load("key", "session_context") is None


def test_memory_manager_invalid_type():
    """Test invalid memory_type raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        try:
            mgr.save("key", "value", "invalid_type")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unknown memory_type" in str(e)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])