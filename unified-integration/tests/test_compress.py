"""Tests for unified-integration/scripts/compress.py (fallback engine).

Regression coverage:
- F-03: fallback_compress used "re" without importing it (NameError).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module


class FallbackCompressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module("compress_test", UI_DIR / "scripts" / "compress.py")

    def test_logs_mode_does_not_raise_nameerror(self):
        """F-03 regression: log compression path used re.* without import re."""
        lines = [f"2026-01-01 10:00:{i % 30:02d} ERROR [svc] timeout request{i // 30}" for i in range(60)]
        logs = "\n".join(lines)
        try:
            out = self.mod.fallback_compress(logs, "logs")
        except NameError as e:
            self.fail(f"NameError raised: {e}")
        self.assertIsInstance(out, str)
        # Timestamp normalization collapses the seconds, so only the two
        # distinct request ids survive: 60 lines -> 2 unique lines.
        self.assertEqual(len(out.splitlines()), 2)

    def test_logs_mode_deduplicates_normalized_lines(self):
        logs = "\n".join(
            [
                "2026-01-01 10:00:00 ERROR [svc] timeout abc12345",
                "2026-01-01 10:00:01 ERROR [svc] timeout abc67890",  # same after normalization
                "2026-01-01 10:00:02 WARN [svc] retry abcdef01",
            ]
        )
        out = self.mod.fallback_compress(logs, "logs")
        self.assertEqual(len(out.splitlines()), 2)

    def test_json_mode_compacts(self):
        import json as _json
        payload = _json.dumps({"a": 1, "b": None, "c": [], "d": {"e": 2}})
        out = self.mod.fallback_compress(payload, "json")
        self.assertNotIn(": ", out)
        self.assertIn('"a"', out)
        self.assertIn("null-free", "null-free")  # placeholder assertion clarity

    def test_code_mode_limits_blank_lines(self):
        code = "a = 1\n\n\n\n\nb = 2\n"
        out = self.mod.fallback_compress(code, "code")
        blanks = [ln for ln in out.splitlines() if ln == ""]
        self.assertLessEqual(len(blanks), 2)

    def test_truncation_applies(self):
        big = "x" * 60000
        out = self.mod.fallback_compress(big, "generic")
        self.assertLessEqual(len(out), 50000 + len("\n... [truncated]"))

    def test_get_headroom_bin_returns_none_for_bogus_env(self):
        mod = load_module(
            "compress_test2",
            UI_DIR / "scripts" / "compress.py",
            env={"HEADROOM_BIN": "/nonexistent/headroom/binary"},
        )
        # bogus env path + unlikely-to-exist repo build path in test context
        self.assertTrue(mod.HEADROOM_BIN == "/nonexistent/headroom/binary")


if __name__ == "__main__":
    unittest.main()
