#!/usr/bin/env python3
"""Regression tests for the video-mcp / ffmpeg-mcp / smoke_test.py fixes.

- video render with text and ``position: null`` no longer raises KeyError.
- video timeline rejects NaN/Infinity/negative/bool times and stores floats.
- ffmpeg cut/thumbnail past the end of the media report an error, a stale
  output is never mistaken for a new result, and in-place edits are refused.
- a failed or timed-out ffmpeg run leaves an existing ``out`` untouched (the
  result is staged and moved into place only on success), and a directory
  or unwritable ``out`` returns a structured error instead of raising.
- the built-in /tmp media root is resolved like candidates are (macOS
  /tmp -> /private/tmp).
- smoke_test.py leaves the caller's state, memory and temp dir untouched.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import REPO_DIR

SERVERS_DIR = REPO_DIR / "unified-integration" / "mcp-servers"


def setUpModule():
    """Keep credentials and generated MCP state away from the user's data."""
    global _directory, _environment
    _directory = tempfile.TemporaryDirectory(prefix="ae-test-mcp-b-")
    root = Path(_directory.name)
    _environment = patch.dict(os.environ, {
        "AGENT_ENHANCEMENTS_API_FILE": str(root / "no-credentials.json"),
        "AGENT_MEMORY_ROOT": str(root / "memory"),
        "AE_FFMPEG_ALLOWED_ROOTS": "",
    })
    _environment.start()


def tearDownModule():
    _environment.stop()
    _directory.cleanup()


def load_server(slug: str):
    spec = importlib.util.spec_from_file_location(
        f"mcp_b_{slug.replace('-', '_')}", SERVERS_DIR / slug / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def has_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class _Completed:
    returncode = 0
    stderr = ""
    stdout = ""


class TestVideoTimelineRegressions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("video-mcp")
        cls.tmp = Path(tempfile.mkdtemp(prefix="ae-test-mcp-b-video-"))
        cls.clip = cls.tmp / "clip.mp4"
        cls.clip.write_bytes(b"not really a video")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _render_command(self, name: str) -> list[str]:
        captured: list[list[str]] = []

        def fake_run(cmd, **_kwargs):
            captured.append(cmd)
            return _Completed()

        with patch.object(self.mod.shutil, "which", return_value="/usr/bin/ffmpeg"), \
                patch.object(self.mod.subprocess, "run", side_effect=fake_run):
            result = self.mod.TOOLS["render"](name, str(self.tmp / "out.mp4"))
        self.assertTrue(result.get("ok"), result)
        self.assertEqual(len(captured), 1)
        return captured[0]

    def test_null_position_with_text_renders_at_bottom(self):
        made = self.mod.TOOLS["timeline"]("nullpos", [{
            "path": str(self.clip), "start": 0, "end": 1,
            "text": "hi", "position": None}])
        self.assertTrue(made.get("ok"), made)
        cmd = self._render_command("nullpos")
        graph = cmd[cmd.index("-filter_complex") + 1]
        self.assertIn("drawtext=", graph)
        self.assertIn("y=h-text_h-40", graph)

    def test_stored_null_position_from_older_store_renders(self):
        # A timeline persisted before the fix may still hold position: null.
        store = self.mod._load_all()
        store["legacy"] = {"name": "legacy", "total_s": 1.0, "clips": [{
            "path": str(self.clip), "start": 0.0, "end": 1.0,
            "text": "old", "position": None}]}
        self.mod._save_all(store)
        cmd = self._render_command("legacy")
        self.assertIn("y=h-text_h-40", cmd[cmd.index("-filter_complex") + 1])

    def test_non_finite_negative_and_bool_times_rejected(self):
        for start, end in (("nan", "nan"), (0, "inf"), ("-inf", 1),
                           (-1, 1), (True, 2), (0, float("nan"))):
            with self.subTest(start=start, end=end):
                result = self.mod.TOOLS["timeline"]("bad", [{
                    "path": str(self.clip), "start": start, "end": end}])
                self.assertIn("error", result)

    def test_times_are_normalized_to_floats_and_result_is_valid_json(self):
        result = self.mod.TOOLS["timeline"]("strs", [{
            "path": str(self.clip), "start": "0.5", "end": "2"}])
        self.assertTrue(result.get("ok"), result)
        self.assertTrue(math.isfinite(result["total_s"]))
        json.loads(json.dumps(result, allow_nan=False))
        clip = self.mod.TOOLS["edl"]("strs")["clips"][0]
        self.assertEqual((clip["start"], clip["end"]), (0.5, 2.0))


class TestTmpRootIsResolved(unittest.TestCase):
    """A symlinked /tmp (macOS) must still admit media below it."""

    def _check(self, slug: str, validate: str):
        mod = load_server(slug)
        with tempfile.TemporaryDirectory(prefix="ae-test-mcp-b-root-") as raw:
            base = Path(raw).resolve()
            real = base / "private-tmp"
            real.mkdir()
            link = base / "tmp-link"
            link.symlink_to(real, target_is_directory=True)
            media = link / "clip.mp4"
            media.write_bytes(b"x")
            real_path = Path

            def fake_path(*parts):
                if parts == ("/tmp",):
                    return real_path(link)
                return real_path(*parts)

            fake_path.cwd = real_path.cwd
            with patch.object(mod, "Path", fake_path):
                resolved, problem = getattr(mod, validate)(str(media), True)
            self.assertIsNone(problem, problem)
            self.assertEqual(resolved, (real / "clip.mp4"))

    def test_ffmpeg_tmp_root_resolved(self):
        self._check("ffmpeg-mcp", "_validate_path")

    def test_video_tmp_root_resolved(self):
        self._check("video-mcp", "_validate_media_path")


@unittest.skipUnless(has_ffmpeg(), "ffmpeg/ffprobe binaries not installed")
class TestFfmpegOutputChecks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("ffmpeg-mcp")
        cls.tmp = Path(tempfile.mkdtemp(prefix="ae-test-mcp-b-ffmpeg-"))
        cls.clip = cls.tmp / "src.mp4"
        made = cls.mod._run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            "testsrc=duration=2:size=160x120:rate=10",
            "-pix_fmt", "yuv420p", str(cls.clip)])
        assert made.get("ok"), made

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_thumbnail_past_end_is_error(self):
        out = self.tmp / "late.jpg"
        result = self.mod.TOOLS["thumbnail"](str(self.clip), 50.0, str(out))
        self.assertIn("error", result)
        self.assertFalse(out.exists())

    def test_cut_past_end_is_error(self):
        out = self.tmp / "late.mp4"
        result = self.mod.TOOLS["cut"](str(self.clip), 50.0, 60.0, str(out))
        self.assertIn("error", result)
        self.assertFalse(out.exists())

    def test_cut_end_is_clamped_to_duration(self):
        out = self.tmp / "tail.mp4"
        result = self.mod.TOOLS["cut"](str(self.clip), 1.0, 60.0, str(out))
        self.assertTrue(result.get("ok"), result)
        self.assertLessEqual(result["segment_s"], 1.0 + 1e-6)

    def test_stale_output_is_not_reported_as_success(self):
        out = self.tmp / "stale.jpg"
        out.write_bytes(b"stale thumbnail from an earlier run")
        with patch.object(self.mod, "_media_duration", return_value=None):
            result = self.mod.TOOLS["thumbnail"](str(self.clip), 50.0, str(out))
        self.assertIn("error", result)
        # The earlier file is kept (never deleted on failure) but is not
        # reported as the new result.
        self.assertEqual(out.read_bytes(), b"stale thumbnail from an earlier run")

    def test_in_place_output_is_refused_and_input_kept(self):
        size = self.clip.stat().st_size
        result = self.mod.TOOLS["transcode"](str(self.clip), "libx264",
                                             str(self.clip))
        self.assertIn("error", result)
        self.assertEqual(self.clip.stat().st_size, size)

    def test_thumbnail_in_range_still_ok(self):
        out = self.tmp / "ok.jpg"
        result = self.mod.TOOLS["thumbnail"](str(self.clip), 0.5, str(out))
        self.assertTrue(result.get("ok"), result)
        self.assertGreater(out.stat().st_size, 0)

    def _staging_leftovers(self, directory: Path) -> list[Path]:
        return [item for item in directory.iterdir()
                if item.name.startswith(".ffmpeg-")]

    def test_failed_run_keeps_existing_output(self):
        # extract_audio on a video-only clip makes ffmpeg exit non-zero; the
        # earlier good file at out must survive, and no staging dir remains.
        work = Path(tempfile.mkdtemp(dir=self.tmp))
        out = work / "keep.m4a"
        out.write_bytes(b"earlier good render")
        result = self.mod.TOOLS["extract_audio"](str(self.clip), str(out))
        self.assertIn("error", result)
        self.assertEqual(out.read_bytes(), b"earlier good render")
        self.assertEqual(self._staging_leftovers(work), [])

    def test_bad_codec_keeps_existing_output(self):
        work = Path(tempfile.mkdtemp(dir=self.tmp))
        out = work / "keep.mp4"
        out.write_bytes(b"earlier good render")
        result = self.mod.TOOLS["transcode"](str(self.clip), "nosuchcodec",
                                             str(out))
        self.assertIn("error", result)
        self.assertEqual(out.read_bytes(), b"earlier good render")
        self.assertEqual(self._staging_leftovers(work), [])

    def test_timeout_keeps_existing_output_and_cleans_staging(self):
        work = Path(tempfile.mkdtemp(dir=self.tmp))
        out = work / "keep.jpg"
        out.write_bytes(b"earlier good render")

        def timed_out(cmd, **_kwargs):
            # ffmpeg had started writing the staged file when it was killed.
            Path(cmd[-1]).write_bytes(b"partial")
            raise subprocess.TimeoutExpired(cmd, 300)

        with patch.object(self.mod.subprocess, "run", side_effect=timed_out), \
                patch.object(self.mod, "_media_duration", return_value=None):
            result = self.mod.TOOLS["thumbnail"](str(self.clip), 0.5, str(out))
        self.assertIn("error", result)
        self.assertEqual(out.read_bytes(), b"earlier good render")
        self.assertEqual(self._staging_leftovers(work), [])

    def test_success_replaces_existing_output(self):
        work = Path(tempfile.mkdtemp(dir=self.tmp))
        out = work / "frame.jpg"
        out.write_bytes(b"old")
        result = self.mod.TOOLS["thumbnail"](str(self.clip), 0.5, str(out))
        self.assertTrue(result.get("ok"), result)
        self.assertNotEqual(out.read_bytes(), b"old")
        self.assertGreater(out.stat().st_size, 0)
        self.assertEqual(self._staging_leftovers(work), [])

    def test_concat_still_works_and_cleans_staging(self):
        work = Path(tempfile.mkdtemp(dir=self.tmp))
        out = work / "joined.mp4"
        result = self.mod.TOOLS["concat"]([str(self.clip), str(self.clip)],
                                          str(out))
        self.assertTrue(result.get("ok"), result)
        self.assertGreater(out.stat().st_size, 0)
        self.assertEqual(sorted(item.name for item in work.iterdir()),
                         ["joined.mp4"])

    def test_directory_out_is_structured_error(self):
        target = Path(tempfile.mkdtemp(dir=self.tmp))
        calls = {
            "cut": lambda: self.mod.TOOLS["cut"](str(self.clip), 0.0, 1.0, str(target)),
            "concat": lambda: self.mod.TOOLS["concat"](
                [str(self.clip), str(self.clip)], str(target)),
            "transcode": lambda: self.mod.TOOLS["transcode"](
                str(self.clip), "libx264", str(target)),
            "extract_audio": lambda: self.mod.TOOLS["extract_audio"](
                str(self.clip), str(target)),
            "thumbnail": lambda: self.mod.TOOLS["thumbnail"](
                str(self.clip), 0.5, str(target)),
        }
        for name, call in calls.items():
            with self.subTest(tool=name):
                result = call()
                self.assertIsInstance(result, dict)
                self.assertIn("error", result)
                self.assertIn("not a directory", result["error"])
                self.assertTrue(target.is_dir())

    def test_unwritable_parent_is_structured_error(self):
        blocker = self.tmp / "blocker-file"
        blocker.write_bytes(b"x")
        result = self.mod.TOOLS["thumbnail"](
            str(self.clip), 0.5, str(blocker / "sub" / "frame.jpg"))
        self.assertIsInstance(result, dict)
        self.assertIn("cannot prepare output", result.get("error", ""))


@unittest.skipUnless(has_ffmpeg(), "ffmpeg/ffprobe binaries not installed")
class TestSmokeTestIsolation(unittest.TestCase):

    def test_smoke_test_leaves_caller_state_and_tmp_untouched(self):
        with tempfile.TemporaryDirectory(prefix="ae-test-mcp-b-smoke-") as raw:
            root = Path(raw)
            sentinel, tmpdir, home = root / "sentinel", root / "tmp", root / "home"
            for item in (sentinel, tmpdir, home):
                item.mkdir()
            env = dict(os.environ)
            env.update({
                "HOME": str(home), "TMPDIR": str(tmpdir),
                "AGENT_MEMORY_ROOT": str(sentinel / "memory"),
                "AGENT_ENHANCEMENTS_STATE_DIR": str(sentinel / "state"),
                "AGENT_ENHANCEMENTS_API_FILE": str(sentinel / "api.json"),
            })
            proc = subprocess.run(
                [sys.executable, "smoke_test.py"], cwd=SERVERS_DIR, env=env,
                capture_output=True, text=True, timeout=300)
            self.assertEqual(proc.returncode, 0, proc.stdout[-2000:] + proc.stderr[-2000:])
            self.assertEqual(list(sentinel.iterdir()), [])
            self.assertEqual(list(tmpdir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
