#!/usr/bin/env python3
"""Central context budget contract for AgentEnhancements (CONTRACT.md §8.4).

Every channel that injects AgentEnhancements text into a model context
MUST take its bound from this module. The values are the acceptance
criteria of the context-frugal default profile; they are implementation
limits enforced by code and tests, not marketing claims.

Measurement rules (docs/benchmark/README.md):
- "Cold start" counts every AE-added token that reaches the model from a
  new session until initial bootstrap/discovery completes, BEFORE any
  task-specific detail is selected. Host prompt, user prompt, task repo
  content and work transcripts are not AE overhead.
- All channels count: instructions sections, hook additionalContext,
  native skill descriptions for AE-linked skills, tool schemas, memory
  recall, observer ambient context, and duplication across channels.
- Prompt cache reduces cost, not context size; cached content still
  occupies the window and is therefore still counted.

Bounds (tokens, tokenizer measured with the pinned proxy unless a host
usage report says otherwise):

  BOOTSTRAP (L0 map, always read)              <= 1000
  COLD_START_TOTAL (all channels combined)     <= 4000
  MEMORY_RECALL (session-start recall)         <=  600   (inside the total)
  OBSERVER_AMBIENT (task-observer bootstrap)   <=  250   (inside the total)
  SEARCH_PAGE (one discovery result page)      <=  800, max 5 cards
  DETAIL_PAGE (one requested detail/schema)    <= 1200, larger uses paging
  NATIVE_DESCRIPTION_TOTAL (linked skills)     <=  2500   (inside the total)
  TOOL_SCHEMA_TOTAL (AE tool schemas)          <= 1800   (inside the total)

The last two are allocations inside COLD_START_TOTAL, chosen so the
default profile fits with headroom for memory recall and observer text.
TOOL_SCHEMA_TOTAL is measured on the model-visible surface (tool name +
description + inputSchema per tool, null/none fields excluded), which is
what a host passes to the model from the MCP tools/list payload; the
raw JSON-RPC envelope carries additional SDK-forced null fields that no
host model surface includes.
"""

from __future__ import annotations

MAX_BOOTSTRAP = 1_000
MAX_COLD_START_TOTAL = 4_000
MAX_MEMORY_RECALL = 600
MAX_OBSERVER_AMBIENT = 250
MAX_SKILL_CARDS = 250  # UserPromptSubmit candidate cards (CONTRACT §8.4)
MAX_SEARCH_PAGE = 800
MAX_DETAIL_PAGE = 1_200
MAX_NATIVE_DESCRIPTION_TOTAL = 2_500
MAX_TOOL_SCHEMA_TOTAL = 1_800
MAX_SEARCH_CARDS = 5

# Compatibility aliases for the legacy per-channel caps the runtime used
# to define inline; the runtime now imports them from here so every
# channel takes its bound from one module.
MAX_MEMORY = MAX_MEMORY_RECALL
MAX_OBSERVER_CONTEXT = MAX_OBSERVER_AMBIENT

# Character fallback when no tokenizer is importable: the o200k ratio on
# English/Indonesian prose in this repository measures ~4.0 chars/token.
CHARS_PER_TOKEN_FALLBACK = 4.0

#: Channels counted toward COLD_START_TOTAL, used by the budget ledger
#: tool and CI fixtures (docs/benchmark). Anything new that injects text
#: must register here so it cannot silently bypass the total.
COLD_START_CHANNELS = (
    "instructions",       # marker sections in CLAUDE.md/AGENTS.md/etc.
    "hook_session_start",  # runtime.py SessionStart additionalContext
    "hook_prompt_submit",  # runtime.py UserPromptSubmit additionalContext
    "native_descriptions",  # AE-linked native skill descriptions
    "tool_schemas",       # AE MCP tool schemas (tools/list payload)
    "memory_recall",      # included in hook_session_start, split out
    "observer_ambient",   # included in hook_session_start, split out
)


def approx_tokens(text: str) -> int:
    """Tokenizer-measured count when tiktoken is importable, else the
    documented character ratio. Callers that need exact numbers should
    import tiktoken themselves; this is for runtime guards where the
    deterministic fallback is acceptable and must stay dependency-free."""
    if not text:
        return 0
    try:  # pragma: no cover - environment dependent
        import tiktoken

        enc = tiktoken.get_encoding("o200k_base")
        return len(enc.encode(text))
    except Exception:  # noqa: BLE001 - fallback by design
        return int(len(text) / CHARS_PER_TOKEN_FALLBACK) + 1


def clamp_to_budget(text: str, max_tokens: int, *, label: str = "") -> str:
    """Trim ``text`` to at most ``max_tokens`` tokens, cutting on a line
    boundary when possible so a guard never emits a half-sentence as if it
    were complete. A trimmed result gains an explicit truncation note.

    Used by every injection channel; the note keeps the model informed
    instead of silently losing tail content (mandate §4 rule 6: detail
    needed for work is fetched on request, never silently cut).
    """
    if not text:
        return text
    if approx_tokens(text) <= max_tokens:
        return text
    lines = text.splitlines(keepends=True)
    kept: list[str] = []
    used = 0
    note = f"\n[{label or 'context'} trimmed to the {max_tokens}-token budget; request the remainder explicitly]"
    note_cost = approx_tokens(note)
    for line in lines:
        cost = approx_tokens(line)
        if used + cost > max_tokens - note_cost:
            break
        kept.append(line)
        used += cost
    if not kept:  # single very long line
        kept = [text[: int(max_tokens * CHARS_PER_TOKEN_FALLBACK)]]
    return "".join(kept).rstrip() + note


def budget_report(channels: dict[str, int]) -> dict:
    """Ledger summary for a set of measured channel token counts."""
    total = sum(channels.values())
    return {
        "channels": channels,
        "cold_start_total": total,
        "within_budget": total <= MAX_COLD_START_TOTAL,
        "limits": {
            "bootstrap": MAX_BOOTSTRAP,
            "cold_start_total": MAX_COLD_START_TOTAL,
            "memory_recall": MAX_MEMORY_RECALL,
            "observer_ambient": MAX_OBSERVER_AMBIENT,
            "search_page": MAX_SEARCH_PAGE,
            "detail_page": MAX_DETAIL_PAGE,
            "native_description_total": MAX_NATIVE_DESCRIPTION_TOTAL,
            "tool_schema_total": MAX_TOOL_SCHEMA_TOTAL,
        },
    }


if __name__ == "__main__":  # pragma: no cover - manual inspection
    import json
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "limits":
        print(json.dumps(budget_report({})["limits"], indent=2))
