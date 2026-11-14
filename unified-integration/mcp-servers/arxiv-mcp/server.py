#!/usr/bin/env python3
"""arxiv-mcp — AgentEnhancements in-house MCP server.

Paper search + metadata fetch from the public arXiv Atom API for
understand-anything and agent-reach (plugin-catalog/mcp-servers.json →
arxiv-mcp, P2, reference). No API key required. Responses are cached in
/tmp/ae-arxiv-cache with a 1-hour TTL (idempotent re-queries are free).
"""
from __future__ import annotations

import hashlib
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable

from mcp.server.fastmcp import FastMCP

VERSION = "1.0.0"
API_URL = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom",
      "arxiv": "http://arxiv.org/schemas/atom"}
CACHE_DIR = Path(tempfile.gettempdir()) / "ae-arxiv-cache"
CACHE_TTL = 3600
TIMEOUT = 30

mcp = FastMCP("arxiv-mcp")

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
    path = CACHE_DIR / f"{key}.xml"
    path.write_text(body)


def _fetch(url: str) -> str | dict:
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AgentEnhancements-arxiv-mcp/1.0"})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return {"error": f"arXiv API returned HTTP {exc.code}",
                "hint": "retry shortly; the endpoint is rate-limited"}
    except urllib.error.URLError as exc:
        return {"error": f"cannot reach arXiv API: {exc.reason}",
                "hint": "check network connectivity"}
    _cache_put(key, body)
    return body


def _parse_entry(entry) -> dict:
    atom = "{http://www.w3.org/2005/Atom}"
    arxiv = "{http://arxiv.org/schemas/atom}"
    entry_id = entry.findtext(f"{atom}id", default="")
    return {
        "arxiv_id": entry_id.rsplit("/", 1)[-1] if entry_id else "",
        "title": re.sub(r"\s+", " ", entry.findtext(f"{atom}title", default="")).strip(),
        "authors": [a.findtext(f"{atom}name", default="")
                    for a in entry.findall(f"{atom}author")][:12],
        "abstract": re.sub(r"\s+", " ",
                           entry.findtext(f"{atom}summary", default="")).strip(),
        "published": entry.findtext(f"{atom}published", default=""),
        "updated": entry.findtext(f"{atom}updated", default=""),
        "categories": [c.get("term") for c in entry.findall(f"{atom}category")],
        "pdf_url": entry.findtext(f"{arxiv}pdf", default="") or
                   (entry_id.replace("abs", "pdf") if entry_id else ""),
        "comment": entry.findtext(f"{arxiv}comment", default="") or None,
    }


@_tool
def health() -> dict:
    """Liveness probe + cache stats."""
    entries = list(CACHE_DIR.glob("*.xml")) if CACHE_DIR.is_dir() else []
    return {
        "status": "ok",
        "server": "arxiv-mcp",
        "version": VERSION,
        "api": API_URL,
        "auth_required": False,
        "cache_dir": str(CACHE_DIR),
        "cache_entries": len(entries),
    }


@_tool
def search(query: str, max_results: int = 5, sort: str = "relevance") -> dict:
    """Search arXiv papers.

    Args:
        query: free-text or field query (e.g. 'all:graph rag').
        max_results: 1..20 (default 5).
        sort: 'relevance' | 'lastUpdatedDate' | 'submittedDate'.
    """
    if not query or not query.strip():
        return {"error": "query must be a non-empty string"}
    max_results = min(max(max_results, 1), 20)
    sort_map = {
        "relevance": "relevance",
        "lastupdateddate": "lastUpdatedDate",
        "submitteddate": "submittedDate",
    }
    sort_key = sort_map.get(sort.lower())
    if sort_key is None:
        return {"error": "sort must be one of relevance|lastUpdatedDate|submittedDate"}
    url = (f"{API_URL}?search_query={urllib.parse.quote(query)}"
           f"&start=0&max_results={max_results}"
           f"&sortBy={sort_key}&sortOrder=descending")
    body = _fetch(url)
    if isinstance(body, dict):
        return body
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return {"error": "arXiv returned malformed XML; try again"}
    entries = [_parse_entry(e) for e in root.findall(f"{{{NS['atom']}}}entry")]
    return {"query": query, "count": len(entries), "papers": entries}


@_tool
def fetch(arxiv_id: str) -> dict:
    """Fetch one paper by id (e.g. '2401.00001' or '2401.00001v2')."""
    if not arxiv_id or not re.match(r"^[0-9]{4}\.[0-9]{4,5}(v[0-9]+)?$", arxiv_id):
        return {"error": "arxiv_id must look like 2401.00001 (or 2401.00001v2)"}
    url = f"{API_URL}?id_list={arxiv_id}&max_results=1"
    body = _fetch(url)
    if isinstance(body, dict):
        return body
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return {"error": "arXiv returned malformed XML; try again"}
    entries = root.findall(f"{{{NS['atom']}}}entry")
    if not entries:
        return {"error": f"no paper found for id {arxiv_id}"}
    return _parse_entry(entries[0])


if __name__ == "__main__":
    mcp.run(transport="stdio")
