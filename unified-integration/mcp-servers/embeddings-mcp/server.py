#!/usr/bin/env python3
"""embeddings-mcp — AgentEnhancements in-house MCP server.

Uniform embedding service for every skill that needs vectors (graphify,
understand-anything, agent-reach per plugin-catalog/mcp-servers.json).

Backends:
- "openai": text-embedding-3-small via the OpenAI REST API (needs
  OPENAI_API_KEY). Called with stdlib urllib; no SDK dependency.
- "local": deterministic hashed bag-of-words embedder (256-dim,
  L2-normalized). Zero deps, offline, stable across runs - good for
  tests, clustering, and cosine workflows that do not need semantic nuance.

House pattern: anthropic-skills/skills/mcp-builder - schema'd tools,
deterministic outputs, actionable errors, health probe, no secret logging.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

VERSION = "1.0.0"
LOCAL_DIM = 256
OPENAI_URL = "https://api.openai.com/v1/embeddings"
OPENAI_MODEL = "text-embedding-3-small"
OPENAI_TIMEOUT = 30

mcp = FastMCP("embeddings-mcp")

TOOLS: dict[str, Callable] = {}


def _tool(fn):
    """Register in FastMCP and in the module-level TOOLS registry (tests)."""
    TOOLS[fn.__name__] = fn
    return mcp.tool()(fn)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _local_embed(text: str) -> list[float]:
    """Deterministic hashed bag-of-words vector, L2-normalized."""
    vec = [0.0] * LOCAL_DIM
    for token in _tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % LOCAL_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 8) for v in vec]


def _openai_embed(texts: list[str]) -> list[list[float]] | dict:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {
            "error": "OPENAI_API_KEY is not set",
            "hint": "export OPENAI_API_KEY=... or pass backend='local' "
                    "for the deterministic offline embedder",
        }
    payload = json.dumps({"model": OPENAI_MODEL, "input": texts}).encode()
    request = urllib.request.Request(
        OPENAI_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    request.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(request, timeout=OPENAI_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        return {
            "error": f"OpenAI API returned HTTP {exc.code}",
            "hint": "check key validity / quota; response tail: " + detail,
        }
    except urllib.error.URLError as exc:
        return {
            "error": f"cannot reach OpenAI API: {exc.reason}",
            "hint": "check network / proxy settings, or use backend='local'",
        }
    return [item["embedding"] for item in body["data"]]


def _resolve_backend(requested: str | None) -> str:
    if requested:
        return requested
    return "openai" if os.environ.get("OPENAI_API_KEY") else "local"


@_tool
def health() -> dict:
    """Liveness + capability probe. Never exposes the API key itself."""
    return {
        "status": "ok",
        "server": "embeddings-mcp",
        "version": VERSION,
        "backends": {
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
            "local": True,
        },
        "local_dim": LOCAL_DIM,
        "openai_model": OPENAI_MODEL,
    }


@_tool
def embed(text: str, backend: str | None = None) -> dict:
    """Embed one text.

    Args:
        text: the string to embed.
        backend: "openai" (needs OPENAI_API_KEY) or "local" (deterministic,
            offline). Defaults to openai when the key is present, else local.
    """
    if not isinstance(text, str) or not text.strip():
        return {"error": "text must be a non-empty string"}
    chosen = _resolve_backend(backend)
    if chosen == "local":
        return {"backend": "local", "dim": LOCAL_DIM, "embedding": _local_embed(text)}
    result = _openai_embed([text])
    if isinstance(result, dict):  # error envelope
        return result
    return {"backend": "openai", "dim": len(result[0]), "embedding": result[0]}


@_tool
def embed_batch(texts: list[str], backend: str | None = None) -> dict:
    """Embed a batch of texts (same backend rules as embed)."""
    if not isinstance(texts, list) or not texts:
        return {"error": "texts must be a non-empty list of strings"}
    if not all(isinstance(t, str) and t.strip() for t in texts):
        return {"error": "every item in texts must be a non-empty string"}
    chosen = _resolve_backend(backend)
    if chosen == "local":
        return {
            "backend": "local",
            "dim": LOCAL_DIM,
            "embeddings": [_local_embed(t) for t in texts],
        }
    result = _openai_embed(texts)
    if isinstance(result, dict):
        return result
    return {"backend": "openai", "dim": len(result[0]), "embeddings": result}


@_tool
def cosine(a: list[float], b: list[float]) -> dict:
    """Cosine similarity between two vectors (any backend, same length)."""
    if not a or not b or len(a) != len(b):
        return {"error": "a and b must be non-empty vectors of equal length"}
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return {"similarity": round(dot / (na * nb), 8)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
