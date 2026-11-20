#!/usr/bin/env python3
"""Tests for memory.py"""

import json
import tempfile
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from memory import MemoryManager


def test_save_load():
    """Test basic save and load."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        # Save
        mgr.save("test_key", {"value": "test_data"}, "session_context", "session1", "claude-code")

        # Load
        result = mgr.load("test_key", "session_context", "session1")
        assert result == {"value": "test_data"}
        print("✓ Save/load works")


def test_save_load_different_types():
    """Test save/load with different memory types."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("key1", {"data": 1}, "session_context", "s1", "agent1")
        mgr.save("key2", {"data": 2}, "persistent", "", "")
        mgr.save("key3", {"data": 3}, "user_preference", "s1", "agent1")

        assert mgr.load("key1", "session_context", "s1") == {"data": 1}
        assert mgr.load("key2", "persistent") == {"data": 2}
        assert mgr.load("key3", "user_preference", "s1") == {"data": 3}
        print("✓ Different memory types work")


def test_delete():
    """Test delete operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("del_key", {"data": "delete"}, "session_context", "s1")
        assert mgr.load("del_key", "session_context", "s1") == {"data": "delete"}

        mgr.delete("del_key", "session_context", "s1")
        assert mgr.load("del_key", "session_context", "s1") is None
        print("✓ Delete works")


def test_query():
    """Test query with filters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("key_a", {"v": 1}, "session_context", "s1", tags=["tag1"])
        mgr.save("key_b", {"v": 2}, "session_context", "s1", tags=["tag2"])
        mgr.save("key_c", {"v": 3}, "session_context", "s2", tags=["tag1"])

        # Query by session
        results = mgr.query("session_context", session_id="s1")
        assert len(results) == 2

        # Query by tag
        results = mgr.query("session_context", session_id="s1", tags=["tag1"])
        assert len(results) == 1
        assert results[0]["key"] == "key_a"

        # Query by prefix
        results = mgr.query("session_context", session_id="s1", key_prefix="key_")
        assert len(results) == 2
        print("✓ Query works")


def test_list_keys():
    """Test list keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("key1", {}, "session_context", "s1")
        mgr.save("key2", {}, "session_context", "s1")
        mgr.save("key3", {}, "session_context", "s2")

        keys = mgr.list_keys("session_context", "s1")
        assert len(keys) == 2
        assert "key1" in keys and "key2" in keys
        print("✓ List keys works")


def test_idempotent_save():
    """Test idempotent save (merge semantics)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("merge_key", {"a": 1}, "session_context", "s1")
        mgr.save("merge_key", {"b": 2}, "session_context", "s1")

        result = mgr.load("merge_key", "session_context", "s1")
        # Should merge dicts
        assert result == {"a": 1, "b": 2}
        print("✓ Idempotent save with merge works")


def test_session_recall():
    """Test session recall."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("k1", {"v": 1}, "session_context", "sess1")
        mgr.save("k2", {"v": 2}, "session_context", "sess1")
        mgr.save("k3", {"v": 3}, "session_context", "sess2")

        recalled = mgr.recall_session("sess1", max_age_days=7)
        assert len(recalled) == 2
        print("✓ Session recall works")


def test_cleanup_expired():
    """Test cleanup of expired entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        # Save with very short TTL override
        mgr.save("expire_key", {"v": 1}, "session_context", "s1", ttl_override=1)
        time.sleep(1.1)

        mgr.save("keep_key", {"v": 2}, "persistent", "")

        cleaned = mgr.cleanup_expired()
        assert cleaned >= 1

        assert mgr.load("expire_key", "session_context", "s1") is None
        assert mgr.load("keep_key", "persistent") == {"v": 2}
        print("✓ Cleanup expired works")


def test_stats():
    """Test stats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)

        mgr.save("k1", {}, "session_context", "s1")
        mgr.save("k2", {}, "persistent")

        stats = mgr.stats()
        assert stats["total_entries"] == 2
        assert "session_context" in stats["by_type"]
        assert "persistent" in stats["by_type"]
        print("✓ Stats work")


def test_vacuum():
    """Test vacuum."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = MemoryManager(tmpdir)
        mgr.save("k1", {}, "session_context", "s1")
        mgr.delete("k1", "session_context", "s1")
        mgr.vacuum()  # Should not error
        print("✓ Vacuum works")


if __name__ == "__main__":
    test_save_load()
    test_save_load_different_types()
    test_delete()
    test_query()
    test_list_keys()
    test_idempotent_save()
    test_session_recall()
    test_cleanup_expired()
    test_stats()
    test_vacuum()
    print("\n✅ All memory tests passed!")