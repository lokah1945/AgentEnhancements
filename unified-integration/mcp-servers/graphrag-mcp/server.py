#!/usr/bin/env python3
"""graphrag-mcp — AgentEnhancements in-house MCP server.

Lexical GraphRAG for graphify / agent-reach (plugin-catalog/
mcp-servers.json → graphrag-mcp, P2, graph).

Honest scope: entity extraction and relation scoring are lexical
(capitalized-phrase heuristics + co-occurrence with PMI-style weighting),
not LLM-driven. This keeps the server fully offline, deterministic and
testable; an LLM extractor can be layered later behind the same API.

- index(corpus_id, documents): build an in-memory entity graph, persisted
  to private per-user, working-directory-scoped storage.
- query(corpus_id, question, k): extract question entities, expand 1-hop
  neighbors, rank evidence sentences by graph + lexical overlap.
- status(corpus_id): corpus stats.
"""
from __future__ import annotations

import json
import hashlib
import os
import math
import re
import tempfile
import time
from pathlib import Path
from typing import Callable

from mcp.server.fastmcp import FastMCP

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from project_paths import memory_root

VERSION = "1.0.0"
# Corpus evidence may contain private source text. Do not store it in a
# world-readable shared /tmp namespace or collide across working directories.
STATE_ROOT = memory_root()
PROJECT_KEY = hashlib.sha256(str(Path.cwd().resolve()).encode()).hexdigest()[:24]
STORE_DIR = STATE_ROOT / "mcp" / "graphrag" / PROJECT_KEY
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "of", "to", "in",
    "on", "for", "with", "by", "at", "from", "as", "is", "are", "was",
    "were", "be", "been", "it", "its", "this", "that", "these", "those",
    "he", "she", "they", "we", "you", "i", "not", "no", "yes", "can",
    "will", "would", "should", "could", "may", "might", "must", "have",
    "has", "had", "do", "does", "did", "which", "who", "whom", "what",
}
MAX_ENTITIES = 2000
# One corpus id maps to exactly one store file: ids are never cleaned or
# truncated, so two distinct ids cannot share (and overwrite) a corpus.
_CORPUS_ID_RE = re.compile(r"[a-zA-Z0-9_-]{1,64}")
_CORPUS_ID_ERROR = "corpus_id must match ^[a-zA-Z0-9_-]{1,64}$"

mcp = FastMCP("graphrag-mcp")

TOOLS: dict[str, Callable] = {}


def _tool(fn):
    TOOLS[fn.__name__] = fn
    return mcp.tool()(fn)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 15]


def _entities(sentence: str) -> list[str]:
    """Capitalized multi-word/inner-word phrases, filtered by stopwords."""
    found = []
    for match in re.finditer(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\b", sentence):
        phrase = match.group(1)
        words = phrase.split()
        if all(w.lower() in STOPWORDS for w in words):
            continue
        if phrase.lower() in STOPWORDS:
            continue
        found.append(phrase)
    # dedupe, keep order
    seen, ordered = set(), []
    for item in found:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _normalize(entity: str) -> str:
    return re.sub(r"\s+", " ", entity.strip()).lower()


_CORPORA: dict[str, dict] = {}


def _valid_corpus_id(corpus_id: object) -> bool:
    return isinstance(corpus_id, str) and _CORPUS_ID_RE.fullmatch(corpus_id) is not None


def _corpus_path(corpus_id: str) -> Path:
    if not _valid_corpus_id(corpus_id):
        raise ValueError(_CORPUS_ID_ERROR)
    return STORE_DIR / f"{corpus_id}.json"


def _load_corpus(corpus_id: str) -> dict | None:
    # Another CLI process may have replaced the corpus. Atomic disk snapshots
    # are authoritative; process-local caches must not hide other clients' edits.
    path = _corpus_path(corpus_id)
    if path.is_file():
        data = json.loads(path.read_text())
        _CORPORA[corpus_id] = data
        return data
    return None


def _save_corpus(corpus_id: str, data: dict) -> None:
    _CORPORA[corpus_id] = data
    STORE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    STORE_DIR.chmod(0o700)
    fd, temporary = tempfile.mkstemp(dir=STORE_DIR, prefix=".corpus-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, ensure_ascii=False)
        os.replace(temporary, _corpus_path(corpus_id))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _build_graph(documents: list[dict]) -> dict:
    nodes: dict[str, dict] = {}
    edge_weight: dict[tuple[str, str], int] = {}
    sentence_count = 0
    evidence: list[dict] = []
    for doc in documents:
        doc_id = doc.get("id") or f"doc-{len(evidence)}"
        for sentence in _sentences(doc.get("text", "")):
            sentence_count += 1
            ents = _entities(sentence)[:8]
            norm = [_normalize(e) for e in ents]
            for raw, key in zip(ents, norm):
                if key not in nodes and len(nodes) < MAX_ENTITIES:
                    nodes[key] = {"label": raw, "mentions": 0, "doc_ids": set()}
                if key in nodes:
                    nodes[key]["mentions"] += 1
                    nodes[key]["doc_ids"].add(doc_id)
            for i in range(len(norm)):
                for j in range(i + 1, len(norm)):
                    if norm[i] in nodes and norm[j] in nodes:
                        pair = tuple(sorted((norm[i], norm[j])))
                        edge_weight[pair] = edge_weight.get(pair, 0) + 1
            if norm:
                evidence.append({
                    "doc_id": doc_id, "sentence": sentence, "entities": norm,
                })
    edges = [
        {"source": a, "target": b, "weight": w}
        for (a, b), w in sorted(edge_weight.items(), key=lambda kv: -kv[1])
    ]
    for node in nodes.values():
        node["doc_ids"] = sorted(node["doc_ids"])
    return {
        "nodes": nodes, "edges": edges, "evidence": evidence,
        "stats": {
            "documents": len(documents), "sentences": sentence_count,
            "entities": len(nodes), "relations": len(edges),
        },
    }


@_tool
def health() -> dict:
    """Liveness probe + store location."""
    return {
        "status": "ok",
        "server": "graphrag-mcp",
        "version": VERSION,
        "mode": "lexical (LLM-optional, offline)",
        "store": str(STORE_DIR),
        "corpora_cached": len(_CORPORA),
    }


@_tool
def index(corpus_id: str, documents: list[dict]) -> dict:
    """Build the entity graph for a corpus.

    Args:
        corpus_id: stable id for the corpus (1-64 letters/digits/-/_).
        documents: list of {id?, text} dicts.
    """
    if not _valid_corpus_id(corpus_id):
        return {"error": _CORPUS_ID_ERROR}
    if not isinstance(documents, list) or not documents:
        return {"error": "documents must be a non-empty list of {id?, text}"}
    for doc in documents:
        if not isinstance(doc, dict) or not str(doc.get("text", "")).strip():
            return {"error": "every document needs a non-empty 'text' field"}
    graph = _build_graph(documents)
    _save_corpus(corpus_id, {
        "corpus_id": corpus_id, "built_at": time.time(), **graph,
    })
    return {"ok": True, "corpus_id": corpus_id, **graph["stats"]}


@_tool
def query(corpus_id: str, question: str, k: int = 5) -> dict:
    """Graph-enhanced retrieval: rank evidence sentences for a question."""
    if not _valid_corpus_id(corpus_id):
        return {"error": _CORPUS_ID_ERROR}
    corpus = _load_corpus(corpus_id)
    if corpus is None:
        return {"error": f"unknown corpus_id {corpus_id!r}",
                "hint": "call index() first"}
    if not question or not question.strip():
        return {"error": "question must be a non-empty string"}
    k = min(max(k, 1), 20)
    q_tokens = {t for t in re.findall(r"[a-z0-9]+", question.lower())
                if t not in STOPWORDS}
    q_entities = {_normalize(e) for e in _entities(question)}
    # 1-hop neighborhood expansion
    neighborhood = set(q_entities)
    for edge in corpus["edges"]:
        if edge["source"] in q_entities:
            neighborhood.add(edge["target"])
        if edge["target"] in q_entities:
            neighborhood.add(edge["source"])
    ranked = []
    for idx, ev in enumerate(corpus["evidence"]):
        s_tokens = set(re.findall(r"[a-z0-9]+", ev["sentence"].lower()))
        lexical = len(q_tokens & s_tokens)
        graph_hit = len(neighborhood & set(ev["entities"]))
        score = 2.0 * graph_hit + 1.0 * lexical
        if score > 0:
            ranked.append({
                "score": round(score, 3),
                "doc_id": ev["doc_id"],
                "entities": ev["entities"],
                "sentence": ev["sentence"],
            })
    ranked.sort(key=lambda item: (-item["score"], item["sentence"]))
    return {
        "corpus_id": corpus_id,
        "question_entities": sorted(q_entities),
        "expanded_entities": sorted(neighborhood - q_entities),
        "answers": ranked[:k],
    }


@_tool
def status(corpus_id: str) -> dict:
    """Stats for an indexed corpus (or an error when unknown)."""
    if not _valid_corpus_id(corpus_id):
        return {"error": _CORPUS_ID_ERROR}
    corpus = _load_corpus(corpus_id)
    if corpus is None:
        return {"error": f"unknown corpus_id {corpus_id!r}"}
    top = sorted(corpus["nodes"].items(),
                 key=lambda kv: -kv[1]["mentions"])[:10]
    return {
        "corpus_id": corpus_id,
        "built_at": corpus["built_at"],
        **corpus["stats"],
        "top_entities": [
            {"entity": key, **{k2: v for k2, v in node.items() if k2 != "doc_ids"}}
            for key, node in top
        ],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
