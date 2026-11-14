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
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from mcp.server.fastmcp import FastMCP

VERSION = "1.0.0"
STORE_DIR = Path(tempfile.gettempdir()) / "ae-video-mcp"
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
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    TIMELINES.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _safe_name(name: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_-]{1,48}$", name))


def _validate_clip(clip: dict, index: int) -> str | None:
    if not isinstance(clip, dict):
        return f"clips[{index}] must be an object"
    path = clip.get("path")
    if not path or not isinstance(path, str):
        return f"clips[{index}].path is required"
    if not Path(path).is_file():
        return f"clips[{index}].path not found: {path}"
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


def _escape_drawtext(text: str) -> str:
    """Escape a literal for ffmpeg drawtext."""
    escaped = (text.replace("\\", "\\\\").replace(":", "\\:")
               .replace("'", "\\'").replace("%", "\\%"))
    return escaped


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
    out_path = Path(out).expanduser().resolve()
    if out_path.suffix.lower() != ".mp4":
        return {"error": "out must end with .mp4"}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clips = doc["clips"]
    inputs: list[str] = []
    filters: list[str] = []
    for i, clip in enumerate(clips):
        inputs += ["-ss", str(clip["start"]), "-t",
                   str(float(clip["end"]) - float(clip["start"])),
                   "-i", clip["path"]]
        parts = [f"[{i}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                 f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1"]
        if clip.get("text"):
            y = {"top": "40", "center": "(h-text_h)/2", "bottom": "h-text_h-40"}[
                clip.get("position", "bottom")]
            parts.append(
                f"drawtext=text='{_escape_drawtext(clip['text'])}':"
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
