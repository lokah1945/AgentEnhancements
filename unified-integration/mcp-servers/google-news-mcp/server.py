#!/usr/bin/env python3
"""google-news-mcp — AgentEnhancements in-house MCP server.

RSS fallback for NewsAPI outages, feeding the last-30-days skill
(plugin-catalog/mcp-servers.json → google-news-mcp, P2, news).
No API key required. 10-minute response cache in /tmp/ae-news-cache.
"""
from __future__ import annotations

import hashlib
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable

from mcp.server.fastmcp import FastMCP

VERSION = "1.0.0"
BASE = "https://news.google.com/rss"
LANGS = {"en": "en", "id": "id", "jp": "jp", "kr": "kr", "de": "de",
         "fr": "fr", "es": "es", "pt": "pt-BR", "zh": "zh-Hans"}
CACHE_DIR = Path(tempfile.gettempdir()) / "ae-news-cache"
CACHE_TTL = 600
TIMEOUT = 30
MAX_LIMIT = 50

mcp = FastMCP("google-news-mcp")

TOOLS: dict[str, Callable] = {}


def _tool(fn):
    TOOLS[fn.__name__] = fn
    return mcp.tool()(fn)


def _cache_get(key: str) -> str | None:
    path = CACHE_DIR / f"{key}.xml"
    if path.is_file() and time.time() - path.stat().st_mtime < CACHE_TTL:
        return path.read_text()
    return None


def _cache_put(key: str, body: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.xml").write_text(body)


def _fetch(url: str) -> str | dict:
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "AgentEnhancements-google-news-mcp/1.0"})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return {"error": f"Google News RSS returned HTTP {exc.code}",
                "hint": "retry shortly or fall back to newsapi-mcp"}
    except urllib.error.URLError as exc:
        return {"error": f"cannot reach Google News RSS: {exc.reason}",
                "hint": "check network connectivity"}
    _cache_put(key, body)
    return body


def _parse_items(body: str, limit: int) -> list[dict]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        source = item.find("source")
        items.append({
            "title": title,
            "link": link,
            "published": pub,
            "source": source.text.strip() if source is not None and source.text else "",
        })
        if len(items) >= limit:
            break
    return items


@_tool
def health() -> dict:
    """Liveness probe + supported languages + cache stats."""
    entries = list(CACHE_DIR.glob("*.xml")) if CACHE_DIR.is_dir() else []
    return {
        "status": "ok",
        "server": "google-news-mcp",
        "version": VERSION,
        "base": BASE,
        "auth_required": False,
        "languages": sorted(LANGS),
        "cache_dir": str(CACHE_DIR),
        "cache_entries": len(entries),
    }


@_tool
def top(topic: str | None = None, lang: str = "en", limit: int = 10) -> dict:
    """Top headlines, optionally filtered by topic / search term.

    Args:
        topic: optional search topic (e.g. 'AI agents'); omit for the
            language's front-page headlines.
        lang: one of en, id, jp, kr, de, fr, es, pt, zh.
        limit: 1..50 (default 10).
    """
    lang_key = lang.lower()
    if lang_key not in LANGS:
        return {"error": f"unsupported lang {lang!r}",
                "hint": f"choose one of {sorted(LANGS)}"}
    limit = min(max(limit, 1), MAX_LIMIT)
    hl = LANGS[lang_key]
    if topic and topic.strip():
        url = (f"{BASE}/search?hl={hl}&q={urllib.parse.quote(topic.strip())}")
    else:
        url = f"{BASE}?hl={hl}&gl=US&ceid=US:{hl}"
    body = _fetch(url)
    if isinstance(body, dict):
        return body
    items = _parse_items(body, limit)
    if not items:
        return {"error": "RSS returned no parseable items",
                "hint": "the feed may have changed; verify in a browser"}
    return {
        "lang": lang_key,
        "topic": topic or None,
        "count": len(items),
        "items": items,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
