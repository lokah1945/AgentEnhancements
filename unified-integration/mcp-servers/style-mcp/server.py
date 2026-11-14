#!/usr/bin/env python3
"""style-mcp — AgentEnhancements in-house MCP server.

AI-ism detection + de-clichéing for the humanizer skill
(plugin-catalog/mcp-servers.json → style-mcp, P2, writing).

Pure Python, fully offline, deterministic. score() flags known LLM
fingerprint patterns with concrete suggestions; rewrite() applies the
safe mechanical substitutions and reports the remaining findings so the
caller knows when human judgment is still needed.
"""
from __future__ import annotations

import re
from typing import Callable

from mcp.server.fastmcp import FastMCP

VERSION = "1.0.0"

mcp = FastMCP("style-mcp")

TOOLS: dict[str, Callable] = {}


def _tool(fn):
    TOOLS[fn.__name__] = fn
    return mcp.tool()(fn)


# (name, regex, suggestion, replacement-or-None, weight)
PATTERNS: list[tuple[str, re.Pattern, str, str | None, int]] = [
    ("cliche:delve", re.compile(r"\bdelve into\b", re.I),
     "plain verb: 'examine' / 'look at'", "examine", 3),
    ("cliche:tapestry", re.compile(r"\b(rich )?tapestry\b", re.I),
     "delete the metaphor; state the fact directly", None, 3),
    ("cliche:landscape", re.compile(r"\b(navigate|in) the (ever-)?(changing |evolving )?landscape of\b", re.I),
     "name the actual domain: 'in the field of X'", None, 3),
    ("cliche:realm", re.compile(r"\bin the realm of\b", re.I),
     "'in' + the concrete subject", "in", 2),
    ("cliche:underscore", re.compile(r"\bunderscore[sd]?\b", re.I),
     "'shows' / 'highlights'", None, 2),
    ("cliche:testament", re.compile(r"\ba testament to\b", re.I),
     "'evidence that' / 'shows that'", "evidence of", 3),
    ("filler:important-note", re.compile(r"\bit is important to note that\b", re.I),
     "delete; the note itself carries the weight", "", 3),
    ("filler:worth-mentioning", re.compile(r"\bit is worth (mentioning|noting) that\b", re.I),
     "delete the preamble", "", 3),
    ("filler:needless-to-say", re.compile(r"\bneedless to say,?\b", re.I),
     "delete", "", 2),
    ("filler:in-conclusion", re.compile(r"\bin conclusion,?\b", re.I),
     "state the takeaway directly", "", 2),
    ("filler:furthermore", re.compile(r"^\s*furthermore,?\b", re.I | re.M),
     "shorter connective or none", None, 1),
    ("filler:moreover", re.compile(r"^\s*moreover,?\b", re.I | re.M),
     "shorter connective or none", None, 1),
    ("hedge:it-seems", re.compile(r"\bit seems that\b", re.I),
     "commit: state the claim or cite it", None, 2),
    ("hedge:arguably", re.compile(r"\barguably\b", re.I),
     "commit or drop the claim", None, 1),
    ("rule-of-three", re.compile(r"\b(\w+[\w-]*), (\w+[\w-]*), and (\w+[\w-]*)\b"),
     "LLMs overuse triads; keep only the items that earn their place", None, 1),
    ("em-dash-overflow", re.compile(r"[^-\s]---[^-\s]"),
     "one em dash per paragraph is plenty", None, 1),
    ("adverb-booster", re.compile(r"\b(incredibly|remarkably|significantly|substantially|notably) \w+\b", re.I),
     "cut the booster; let the fact land", None, 1),
    ("meta:as-an-ai", re.compile(r"\bas an ai\b", re.I),
     "delete; the reader knows", "", 4),
]

MAX_TEXT = 200_000


def _score_text(text: str) -> tuple[int, list[dict]]:
    findings: list[dict] = []
    penalty = 0
    for name, pattern, suggestion, _repl, weight in PATTERNS:
        matches = pattern.findall(text)
        count = len(matches)
        if count:
            penalty += weight * min(count, 3)
            findings.append({
                "pattern": name,
                "count": count,
                "weight": weight,
                "suggestion": suggestion,
            })
    score = max(0, 100 - penalty)
    return score, findings


@_tool
def health() -> dict:
    """Liveness probe: pattern count + version."""
    return {
        "status": "ok",
        "server": "style-mcp",
        "version": VERSION,
        "patterns": len(PATTERNS),
        "mode": "offline / deterministic",
    }


@_tool
def score(text: str) -> dict:
    """Score naturalness 0..100 (higher = fewer AI fingerprints) and list
    every finding with a concrete fix suggestion."""
    if not isinstance(text, str) or not text.strip():
        return {"error": "text must be a non-empty string"}
    if len(text) > MAX_TEXT:
        return {"error": f"text exceeds {MAX_TEXT} chars; chunk it first"}
    value, findings = _score_text(text)
    return {
        "score": value,
        "verdict": ("human-leaning" if value >= 85 else
                    "ai-flavored" if value >= 60 else "heavily ai-flavored"),
        "findings": findings,
        "words": len(text.split()),
    }


@_tool
def rewrite(text: str) -> dict:
    """Apply the safe mechanical substitutions (fillers, cliches with a
    defined replacement). Returns the edited text plus the BEFORE/AFTER
    scores and remaining findings - anything still flagged needs human
    judgment, not more regex."""
    if not isinstance(text, str) or not text.strip():
        return {"error": "text must be a non-empty string"}
    if len(text) > MAX_TEXT:
        return {"error": f"text exceeds {MAX_TEXT} chars; chunk it first"}
    before, findings_before = _score_text(text)
    edited = text
    for _name, pattern, _suggestion, replacement, _weight in PATTERNS:
        if replacement is not None:
            edited = pattern.sub(replacement, edited)
    edited = re.sub(r"[ \t]{2,}", " ", edited)
    edited = re.sub(r"\n{3,}", "\n\n", edited)
    after, findings_after = _score_text(edited)
    return {
        "before_score": before,
        "after_score": after,
        "text": edited.strip(),
        "remaining_findings": findings_after,
        "note": "mechanical edits only - review remaining_findings yourself",
    }


@_tool
def patterns() -> dict:
    """List every known AI-ism pattern with its weight and suggestion."""
    return {"patterns": [
        {"pattern": name, "weight": weight, "suggestion": suggestion,
         "auto_rewritable": replacement is not None}
        for name, _pat, suggestion, replacement, weight in PATTERNS
    ]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
