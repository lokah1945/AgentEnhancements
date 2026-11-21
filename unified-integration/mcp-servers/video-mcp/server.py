#!/usr/bin/env python3
"""video-mcp — AgentEnhancements in-house MCP server.

Shot-list / timeline semantics layered on ffmpeg for openmontage and
hyperframes (plugin-catalog/mcp-servers.json → video-mcp, P2, media).

Timelines are JSON documents (clips with in/out points, optional text
overlays) persisted in /tmp/ae-video-mcp/timelines.json. render()
compiles a timeline into a single ffmpeg invocation (concat filter +
drawtext overlays). Rendering needs the ffmpeg binary; timeline
construction and EDL export are fully offline.
"""
from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from mcp.server.fastmcp import FastMCP
from filelock import FileLock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from project_paths import memory_root

VERSION = "1.0.0"
STATE_ROOT = memory_root()
PROJECT_KEY = hashlib.sha256(str(Path.cwd().resolve()).encode()).hexdigest()[:24]
STORE_DIR = STATE_ROOT / "mcp" / "video" / PROJECT_KEY
TIMELINES = STORE_DIR / "timelines.json"
MAX_CLIPS = 64
FFMPEG = "ffmpeg"

mcp = FastMCP("video-mcp")

TOOLS: dict[str, Callable] = {}


def _tool(fn):
    TOOLS[fn.__name__] = fn
    return mcp.tool()(fn)


def _load_all() -> dict:
    if TIMELINES.is_file():
        return json.loads(TIMELINES.read_text())
    return {}


def _save_all(data: dict) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    STORE_DIR.chmod(0o700)
    fd, temporary = tempfile.mkstemp(dir=STORE_DIR, prefix=".timelines-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, TIMELINES)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _safe_name(name: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_-]{1,48}$", name))


def _validate_clip(clip: dict, index: int) -> str | None:
    if not isinstance(clip, dict):
        return f"clips[{index}] must be an object"
    path = clip.get("path")
    if not path or not isinstance(path, str):
        return f"clips[{index}].path is required"
    _, problem = _validate_media_path(path, must_exist=True)
    if problem:
        return f"clips[{index}].{problem}"
    for field in ("start", "end"):
        value = clip.get(field, 0.0)
        try:
            float(value)
        except (TypeError, ValueError):
            return f"clips[{index}].{field} must be a number of seconds"
    try:
        if float(clip.get("end", 0)) <= float(clip.get("start", 0)):
            return f"clips[{index}] needs end > start"
    except (TypeError, ValueError):
        return f"clips[{index}] start/end must be numbers"
    text = clip.get("text")
    if text is not None and (not isinstance(text, str) or len(text) > 120):
        return f"clips[{index}].text must be a string of <= 120 chars"
    return None


def _allowed_roots() -> list[Path]:
    """Media roots shared with ffmpeg-mcp: cwd, /tmp, AE_FFMPEG_ALLOWED_ROOTS."""
    roots = [Path.cwd().resolve(), Path("/tmp")]
    extra = os.environ.get("AE_FFMPEG_ALLOWED_ROOTS", "")
    for item in extra.split(os.pathsep):
        if item.strip():
            roots.append(Path(item.strip()).resolve())
    return roots


def _validate_media_path(raw: str, must_exist: bool) -> tuple[Path | None, str | None]:
    """Resolve a clip/output path and keep it inside the media allowed roots."""
    path = Path(raw).expanduser().resolve()
    if must_exist and not path.is_file():
        return None, f"path not found: {raw}"
    allowed = _allowed_roots()
    if not any(path.is_relative_to(root) for root in allowed):
        return None, (f"path {raw} is outside the allowed roots "
                      f"({', '.join(str(r) for r in allowed)}); extend via "
                      f"AE_FFMPEG_ALLOWED_ROOTS")
    return path, None


# drawtext reads overlay text from a private file with expansion disabled,
# so user text never becomes filtergraph or option syntax. Only the file
# path itself is embedded, and it must be made of inert characters.
_INERT_PATH = re.compile(r"^[A-Za-z0-9/._-]+$")


@_tool
def health() -> dict:
    """Liveness probe: ffmpeg availability + timeline store."""
    return {
        "status": "ok",
        "server": "video-mcp",
        "version": VERSION,
        "ffmpeg": bool(shutil.which(FFMPEG)),
        "store": str(TIMELINES),
        "timelines": len(_load_all()),
    }


@_tool
def timeline(name: str, clips: list[dict]) -> dict:
    """Create or replace a named timeline.

    Args:
        name: timeline id (letters/digits/-/_, <= 48 chars).
        clips: list of {path, start, end, text?, position?} where start/end
            are seconds, text is an optional overlay (<= 120 chars) and
            position is one of top|center|bottom.
    """
    if not _safe_name(name):
        return {"error": "name must match ^[a-zA-Z0-9_-]{1,48}$"}
    if not isinstance(clips, list) or not clips:
        return {"error": "clips must be a non-empty list"}
    if len(clips) > MAX_CLIPS:
        return {"error": f"too many clips (max {MAX_CLIPS})"}
    for index, clip in enumerate(clips):
        problem = _validate_clip(clip, index)
        if problem:
            return {"error": problem}
        if clip.get("position") not in (None, "top", "center", "bottom"):
            return {"error": f"clips[{index}].position must be top|center|bottom"}
    total = round(sum(float(c["end"]) - float(c["start"]) for c in clips), 3)
    doc = {"name": name, "clips": clips, "total_s": total}
    STORE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    STORE_DIR.chmod(0o700)
    # Read/update/replace is a transaction across simultaneous CLI processes.
    with FileLock(str(STORE_DIR / ".timelines.lock"), mode=0o600, timeout=10):
        store = _load_all()
        store[name] = doc
        _save_all(store)
    return {
        "ok": True, "timeline": name, "clips": len(clips), "total_s": total,
        "hint": f"call render('{name}', '<out.mp4>') to produce the video",
    }


@_tool
def edl(name: str) -> dict:
    """Export a timeline as an edit-decision-list (JSON + human-readable)."""
    store = _load_all()
    doc = store.get(name)
    if doc is None:
        return {"error": f"unknown timeline {name!r}",
                "hint": "create it with timeline() first"}
    lines = [f"EDL {name}  total={doc['total_s']}s"]
    for i, clip in enumerate(doc["clips"], start=1):
        overlay = f"  text='{clip['text']}'" if clip.get("text") else ""
        lines.append(
            f"{i:03d}  {clip['path']}  "
            f"in={clip['start']}s out={clip['end']}s{overlay}")
    return {"timeline": name, "total_s": doc["total_s"],
            "clips": doc["clips"], "edl": "\n".join(lines)}


@_tool
def render(name: str, out: str) -> dict:
    """Compile a timeline to a single .mp4 via one ffmpeg invocation
    (trim each clip, concat, apply drawtext overlays)."""
    store = _load_all()
    doc = store.get(name)
    if doc is None:
        return {"error": f"unknown timeline {name!r}"}
    if not shutil.which(FFMPEG):
        return {"error": "ffmpeg binary not found on PATH",
                "hint": "install ffmpeg to render; timeline()/edl() work offline"}
    if not isinstance(out, str) or not out:
        return {"error": "out must be a non-empty .mp4 path"}
    out_path, problem = _validate_media_path(out, must_exist=False)
    if problem:
        return {"error": f"out {problem}"}
    if out_path.suffix.lower() != ".mp4":
        return {"error": "out must end with .mp4"}
    clips = doc["clips"]
    # Re-check stored clips: the store may predate the roots policy.
    sources: list[Path] = []
    for index, clip in enumerate(clips):
        source, problem = _validate_media_path(clip["path"], must_exist=True)
        if problem:
            return {"error": f"clips[{index}].{problem}"}
        sources.append(source)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="ae-video-text-"))
    try:
        if not _INERT_PATH.match(str(work)):
            return {"error": "temporary directory path is not usable by drawtext",
                    "hint": "set TMPDIR to a path made of letters, digits, '/', '.', '_' or '-'"}
        return _render(name, doc, clips, sources, out_path, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _render(name: str, doc: dict, clips: list[dict], sources: list[Path],
            out_path: Path, work: Path) -> dict:
    """Build and run the single ffmpeg invocation for render()."""
    inputs: list[str] = []
    filters: list[str] = []
    for i, clip in enumerate(clips):
        inputs += ["-ss", str(clip["start"]), "-t",
                   str(float(clip["end"]) - float(clip["start"])),
                   "-i", str(sources[i])]
        parts = [f"[{i}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                 f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1"]
        if clip.get("text"):
            y = {"top": "40", "center": "(h-text_h)/2", "bottom": "h-text_h-40"}[
                clip.get("position", "bottom")]
            text_file = work / f"overlay-{i}.txt"
            text_file.write_text(clip["text"], encoding="utf-8")
            parts.append(
                f"drawtext=textfile={text_file}:expansion=none:"
                f"fontcolor=white:fontsize=36:box=1:boxcolor=black@0.5:"
                f"x=(w-text_w)/2:y={y}")
        filters.append(",".join(parts) + f"[v{i}]")
    concat_in = "".join(f"[v{i}]" for i in range(len(clips)))
    filters.append(f"{concat_in}concat=n={len(clips)}:v=1:a=0[vout]")
    cmd = [FFMPEG, "-y", *inputs,
           "-filter_complex", ";".join(filters),
           "-map", "[vout]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           str(out_path)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return {"error": "render timed out after 600s"}
    if proc.returncode != 0:
        return {"error": f"ffmpeg exited with code {proc.returncode}",
                "hint": proc.stderr[-1500:]}
    return {"ok": True, "timeline": name, "out": str(out_path),
            "clips": len(clips), "total_s": doc["total_s"]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
