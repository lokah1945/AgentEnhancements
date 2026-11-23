#!/usr/bin/env python3
"""ffmpeg-mcp — AgentEnhancements in-house MCP server.

Non-linear video editing via ffmpeg for the openmontage skill
(plugin-catalog/mcp-servers.json → ffmpeg-mcp, P1, media).

All path arguments must resolve inside an allowed root (cwd or /tmp by
default; extend with AE_FFMPEG_ALLOWED_ROOTS="/pathA:/pathB"). ffmpeg/ffprobe
are invoked with -y (idempotent overwrite) and captured stderr tails on
failure.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

VERSION = "1.0.0"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"
STDERR_TAIL = 1200

mcp = FastMCP("ffmpeg-mcp")

TOOLS: dict[str, Callable] = {}


def _tool(fn):
    TOOLS[fn.__name__] = fn
    return mcp.tool()(fn)


def _allowed_roots() -> list[Path]:
    # Resolve /tmp like candidates are resolved (macOS: /tmp -> /private/tmp).
    roots = [Path.cwd().resolve(), Path("/tmp").resolve()]
    extra = os.environ.get("AE_FFMPEG_ALLOWED_ROOTS", "")
    for item in extra.split(os.pathsep):
        if item.strip():
            roots.append(Path(item.strip()).resolve())
    return roots


def _validate_path(raw: str, must_exist: bool) -> tuple[Path | None, str | None]:
    if not raw or not isinstance(raw, str):
        return None, "path must be a non-empty string"
    path = Path(raw).expanduser().resolve()
    if must_exist and not path.is_file():
        return None, f"input file not found: {raw}"
    allowed = _allowed_roots()
    if not any(path.is_relative_to(root) for root in allowed):
        return None, (f"path {raw} is outside the allowed roots "
                      f"({', '.join(str(r) for r in allowed)}); extend via "
                      f"AE_FFMPEG_ALLOWED_ROOTS")
    return path, None


def _run(cmd: list[str]) -> dict:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        return {"error": f"{cmd[0]} binary not found on PATH",
                "hint": "install ffmpeg (apt install ffmpeg / brew install ffmpeg)"}
    except subprocess.TimeoutExpired:
        return {"error": "ffmpeg timed out after 300s"}
    if proc.returncode != 0:
        return {"error": f"{cmd[0]} exited with code {proc.returncode}",
                "hint": proc.stderr[-STDERR_TAIL:]}
    return {"ok": True, "stderr_tail": proc.stderr[-400:]}


def _media_duration(path: Path) -> float | None:
    """Container duration in seconds, or None when ffprobe cannot tell."""
    try:
        proc = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    try:
        value = float(proc.stdout.strip())
    except ValueError:
        return None
    return value if value >= 0 else None


def _prepare_output(output: Path, *inputs: Path) -> str | None:
    """Validate the output target before any ffmpeg work starts.

    Refuses in-place edits, a target that exists but is not a regular file
    (a directory, for example) and a parent directory that cannot be
    created. Nothing at ``output`` is changed here: ffmpeg writes into a
    private staging directory and ``_render`` only moves a fresh, non-empty
    result onto ``output``, so a failed run never destroys an earlier file.
    """
    if output in inputs:
        return "out must differ from the input file(s)"
    if output.exists() and not output.is_file():
        return "out must be a file path, not a directory"
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return f"cannot prepare output {output}: {exc.strerror or exc}"
    return None


def _check_output(output: Path, result: dict) -> dict:
    """Turn a zero exit code without a non-empty output file into an error."""
    if "error" in result:
        return result
    if not output.is_file() or output.stat().st_size == 0:
        return {"error": "ffmpeg produced no output",
                "hint": result.get("stderr_tail", "")}
    return result


def _render(output: Path, inputs: tuple[Path, ...],
            run: Callable[[Path, Path], dict]) -> dict:
    """Run ``run(staged_output, staging_dir)`` and publish its result atomically.

    ffmpeg writes to a file with the same extension (so the same muxer)
    inside a private ``mkdtemp`` directory next to ``output``. Only a
    successful run that produced a non-empty file is moved onto ``output``
    with ``os.replace``; on any failure, including a timeout, the staging
    directory is removed and an existing ``output`` is left untouched. A
    stale ``output`` is therefore never reported as the new result.
    """
    problem = _prepare_output(output, *inputs)
    if problem:
        return {"error": problem}
    try:
        staging = Path(tempfile.mkdtemp(prefix=".ffmpeg-", dir=output.parent))
    except OSError as exc:
        return {"error": f"cannot prepare output {output}: {exc.strerror or exc}"}
    try:
        staged = staging / f"output{output.suffix}"
        result = _check_output(staged, run(staged, staging))
        if "error" in result:
            return result
        try:
            os.replace(staged, output)
        except OSError as exc:
            return {"error": f"cannot write output {output}: {exc.strerror or exc}"}
        return result
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _duration_seconds(raw: str | int | float) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value


@_tool
def health() -> dict:
    """Liveness probe: ffmpeg/ffprobe availability + allowed roots."""
    return {
        "status": "ok",
        "server": "ffmpeg-mcp",
        "version": VERSION,
        "ffmpeg": bool(shutil.which(FFMPEG)),
        "ffprobe": bool(shutil.which(FFPROBE)),
        "allowed_roots": [str(r) for r in _allowed_roots()],
    }


@_tool
def probe(path: str) -> dict:
    """Media metadata for a file (duration, streams, codec, resolution)."""
    target, err = _validate_path(path, must_exist=True)
    if err:
        return {"error": err}
    proc = subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(target)],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        return {"error": "ffprobe failed",
                "hint": proc.stderr[-STDERR_TAIL:]}
    info = json.loads(proc.stdout)
    fmt = info.get("format", {})
    video = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    audio = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    return {
        "path": str(target),
        "duration_s": round(float(fmt.get("duration", 0)), 3),
        "size_bytes": int(fmt.get("size", 0)),
        "video_streams": [{
            "codec": s.get("codec_name"),
            "width": s.get("width"),
            "height": s.get("height"),
            "fps": s.get("r_frame_rate"),
        } for s in video],
        "audio_streams": [{
            "codec": s.get("codec_name"),
            "sample_rate": s.get("sample_rate"),
            "channels": s.get("channels"),
        } for s in audio],
    }


@_tool
def cut(path: str, start: float, end: float, out: str) -> dict:
    """Cut a segment [start, end) seconds. Idempotent: re-runs overwrite out."""
    target, err = _validate_path(path, must_exist=True)
    if err:
        return {"error": err}
    output, err = _validate_path(out, must_exist=False)
    if err:
        return {"error": err}
    start_s = _duration_seconds(start)
    end_s = _duration_seconds(end)
    if start_s is None or end_s is None or end_s <= start_s:
        return {"error": "start/end must be seconds with 0 <= start < end"}
    duration = _media_duration(target)
    if duration is not None:
        if start_s >= duration:
            return {"error": f"start={start_s}s is at or beyond the media "
                             f"duration ({duration:.3f}s)"}
        end_s = min(end_s, duration)
    result = _render(output, (target,), lambda staged, _dir: _run([
        FFMPEG, "-y", "-ss", str(start_s), "-to", str(end_s),
        "-i", str(target), "-c", "copy", str(staged)]))
    if "error" in result:
        return result
    return {"ok": True, "out": str(output),
            "segment_s": round(end_s - start_s, 3)}


@_tool
def concat(paths: list[str], out: str) -> dict:
    """Concatenate clips (same codec/resolution) via the concat demuxer."""
    if not isinstance(paths, list) or len(paths) < 2:
        return {"error": "paths must be a list of at least 2 files"}
    resolved = []
    for raw in paths:
        target, err = _validate_path(raw, must_exist=True)
        if err:
            return {"error": err}
        if any(character in str(target) for character in ("\r", "\n", "\0")):
            return {"error": "concat input paths cannot contain line breaks or NUL"}
        resolved.append(target)
    output, err = _validate_path(out, must_exist=False)
    if err:
        return {"error": err}

    def run(staged: Path, staging: Path) -> dict:
        # The list file lives in the private staging directory (mkdtemp, 0700),
        # so no predictable sibling path can be a symlink to user data. Quote
        # paths for ffconcat's parser, whose single-quoted tokens otherwise
        # allow directive injection.
        list_file = staging / "concat-list.txt"
        with open(list_file, "x", encoding="utf-8") as stream:
            for path in resolved:
                escaped = str(path).replace("'", "'\\''")
                stream.write(f"file '{escaped}'\n")
        return _run([FFMPEG, "-y", "-f", "concat", "-safe", "0",
                     "-i", str(list_file), "-c", "copy", str(staged)])

    result = _render(output, tuple(resolved), run)
    if "error" in result:
        return result
    return {"ok": True, "out": str(output), "clips": len(resolved)}


@_tool
def transcode(path: str, codec: str = "libx264", out: str | None = None) -> dict:
    """Re-encode a file (default H.264). Audio copied when possible."""
    target, err = _validate_path(path, must_exist=True)
    if err:
        return {"error": err}
    if not codec or not codec.replace("-", "").replace("_", "").isalnum():
        return {"error": "codec must be a plain codec name, e.g. libx264"}
    output, err = _validate_path(out or str(target.with_suffix(".conv.mp4")),
                                 must_exist=False)
    if err:
        return {"error": err}
    result = _render(output, (target,), lambda staged, _dir: _run([
        FFMPEG, "-y", "-i", str(target),
        "-c:v", codec, "-c:a", "copy", str(staged)]))
    if "error" in result:
        return result
    return {"ok": True, "out": str(output), "codec": codec}


@_tool
def extract_audio(path: str, out: str) -> dict:
    """Extract the audio track to .m4a (AAC copy when possible)."""
    target, err = _validate_path(path, must_exist=True)
    if err:
        return {"error": err}
    output, err = _validate_path(out, must_exist=False)
    if err:
        return {"error": err}
    result = _render(output, (target,), lambda staged, _dir: _run([
        FFMPEG, "-y", "-i", str(target), "-vn",
        "-c:a", "aac", str(staged)]))
    if "error" in result:
        return result
    return {"ok": True, "out": str(output)}


@_tool
def thumbnail(path: str, t: float = 0.0, out: str | None = None) -> dict:
    """Grab a single frame at time t (seconds) as a .jpg."""
    target, err = _validate_path(path, must_exist=True)
    if err:
        return {"error": err}
    at = _duration_seconds(t)
    if at is None:
        return {"error": "t must be a non-negative second offset"}
    duration = _media_duration(target)
    if duration is not None and at >= duration:
        return {"error": f"t={at}s is at or beyond the media duration "
                         f"({duration:.3f}s)"}
    output, err = _validate_path(out or str(target.with_suffix(".jpg")),
                                 must_exist=False)
    if err:
        return {"error": err}
    result = _render(output, (target,), lambda staged, _dir: _run([
        FFMPEG, "-y", "-ss", str(at), "-i", str(target),
        "-frames:v", "1", "-q:v", "2", str(staged)]))
    if "error" in result:
        return result
    return {"ok": True, "out": str(output), "at_s": at}


if __name__ == "__main__":
    mcp.run(transport="stdio")
