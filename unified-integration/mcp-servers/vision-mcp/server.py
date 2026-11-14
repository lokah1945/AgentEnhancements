#!/usr/bin/env python3
"""vision-mcp — AgentEnhancements in-house MCP server.

Multimodal image understanding for anthropic-skills, impeccable and
replica-skill (plugin-catalog/mcp-servers.json → vision-mcp, P1, core).

- compare: fully offline (PIL histogram + normalized pixel diff).
- ocr: tesseract binary when installed; actionable error otherwise.
- describe: gpt-4o vision when OPENAI_API_KEY is set; honest
  basic-metadata fallback (size, format, dominant colors) when not.
  The active mode is always reported in the response - never faked.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

VERSION = "1.0.0"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"
MAX_BYTES = 8 * 1024 * 1024

mcp = FastMCP("vision-mcp")

TOOLS: dict[str, Callable] = {}


def _tool(fn):
    TOOLS[fn.__name__] = fn
    return mcp.tool()(fn)


def _load_image(raw: str) -> tuple[Path | None, bytes | None, str | None]:
    if not raw or not isinstance(raw, str):
        return None, None, "image_path must be a non-empty string"
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        return None, None, f"file not found: {raw}"
    if path.stat().st_size > MAX_BYTES:
        return None, None, (f"file larger than {MAX_BYTES // (1024 * 1024)} MB; "
                            f"downscale first")
    data = path.read_bytes()
    # Pillow import is deferred: health() must work without PIL installed.
    return path, data, None


@_tool
def health() -> dict:
    """Liveness probe: PIL / tesseract / OpenAI-key availability (booleans)."""
    try:
        import PIL  # noqa: F401
        pil = True
    except ImportError:
        pil = False
    return {
        "status": "ok",
        "server": "vision-mcp",
        "version": VERSION,
        "pil": pil,
        "tesseract": bool(shutil.which("tesseract")),
        "openai_key": bool(os.environ.get("OPENAI_API_KEY")),
    }


@_tool
def compare(a: str, b: str) -> dict:
    """Similarity of two images (0..1): histogram intersection blended with
    a normalized mean pixel difference. Fully offline via PIL."""
    try:
        from PIL import Image
    except ImportError:
        return {"error": "Pillow is not installed",
                "hint": "pip install pillow"}
    path_a, data_a, err = _load_image(a)
    if err:
        return {"error": err}
    path_b, data_b, err = _load_image(b)
    if err:
        return {"error": err}
    try:
        img_a = Image.open(path_a).convert("RGB")
        img_b = Image.open(path_b).convert("RGB")
    except Exception as exc:
        return {"error": f"cannot decode images: {exc}"}
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size)
    hist_a = img_a.histogram()
    hist_b = img_b.histogram()
    intersections = []
    for channel in range(3):
        ha = hist_a[channel * 256:(channel + 1) * 256]
        hb = hist_b[channel * 256:(channel + 1) * 256]
        total = sum(max(x, y) for x, y in zip(ha, hb)) or 1
        intersections.append(sum(min(x, y) for x, y in zip(ha, hb)) / total)
    hist_sim = sum(intersections) / 3
    from PIL import ImageChops
    diff = ImageChops.difference(img_a, img_b)
    stat = sum(diff.convert("L").getdata()) / (img_a.size[0] * img_a.size[1])
    pixel_sim = 1.0 - min(stat / 255.0, 1.0)
    similarity = round(0.5 * hist_sim + 0.5 * pixel_sim, 6)
    return {"similarity": similarity, "same_size": img_a.size == img_b.size,
            "histogram_similarity": round(hist_sim, 6),
            "pixel_similarity": round(pixel_sim, 6)}


@_tool
def ocr(image_path: str, lang: str = "eng") -> dict:
    """OCR via the tesseract binary (installable separately)."""
    path, _data, err = _load_image(image_path)
    if err:
        return {"error": err}
    if not shutil.which("tesseract"):
        return {"error": "tesseract binary not found on PATH",
                "hint": "apt install tesseract-ocr (or brew install tesseract)"}
    if not lang or not lang.replace("-", "").replace("_", "").isalnum():
        return {"error": "lang must be a tesseract language code, e.g. 'eng'"}
    try:
        proc = subprocess.run(
            ["tesseract", str(path), "stdout", "-l", lang],
            capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {"error": "tesseract timed out after 120s"}
    if proc.returncode != 0:
        return {"error": "tesseract failed",
                "hint": proc.stderr[-600:]}
    return {"text": proc.stdout.strip(), "lang": lang}


@_tool
def describe(image_path: str, detail: str = "auto") -> dict:
    """Describe an image. Uses gpt-4o vision when OPENAI_API_KEY is set
    (mode "openai"); otherwise returns honest basic metadata (mode
    "basic_metadata": size, format, dominant colors). The mode field in
    the response always states which path was taken."""
    path, data, err = _load_image(image_path)
    if err:
        return {"error": err}
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        b64 = base64.b64encode(data).decode("ascii")
        suffix = path.suffix.lstrip(".").lower() or "png"
        media = {"jpeg": "image/jpeg", "jpg": "image/jpeg"}.get(suffix, "image/png")
        body = json.dumps({
            "model": OPENAI_MODEL,
            "max_tokens": 400,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text",
                     "text": "Describe this image precisely and concisely."},
                    {"type": "image_url",
                     "image_url": {"url": f"data:{media};base64,{b64}"}},
                ],
            }],
        }).encode()
        request = urllib.request.Request(
            OPENAI_URL, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        request.add_header("Authorization", f"Bearer {api_key}")
        try:
            with urllib.request.urlopen(request, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return {"mode": "openai", "model": OPENAI_MODEL,
                    "description": payload["choices"][0]["message"]["content"]}
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as exc:
            return {"error": f"OpenAI vision call failed: {exc}",
                    "hint": "falling back is explicit - re-run with the key "
                            "unset to get basic_metadata mode"}
    # Honest offline fallback: real metadata, no fabricated description.
    try:
        from PIL import Image
        img = Image.open(path).convert("RGB")
    except ImportError:
        return {"error": "no OPENAI_API_KEY and Pillow is not installed",
                "hint": "either set OPENAI_API_KEY or pip install pillow"}
    small = img.resize((64, 64))
    colors = sorted(small.getcolors(64 * 64) or [], reverse=True)[:5]
    total = 64 * 64
    return {
        "mode": "basic_metadata",
        "note": "set OPENAI_API_KEY for a semantic description",
        "size": list(img.size),
        "format": img.format or path.suffix.lstrip("."),
        "dominant_colors": [
            {"rgb": list(color), "share": round(count / total, 4)}
            for count, color in colors
        ],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
