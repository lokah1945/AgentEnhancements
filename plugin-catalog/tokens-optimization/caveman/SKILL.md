---
slug: caveman
category: tokens-optimization
version: 1.0.0
status: manifest-only
mcp_servers: []
trigger_keywords: [caveman, cavecrew, subagent compression]
---

# Caveman (Upstream: JuliusBrussee/caveman v4.2.0)

**THIS IS A MANIFEST-ONLY ENTRY DOCUMENTING UPSTREAM CAPABILITY. NO AE RUNTIME INTEGRATION EXISTS.**

## Upstream Reality (v4.2.0, 2026-11-22)

Caveman provides TWO distinct capabilities:

### 1. Cavecrew Subagent Presets (Primary)
Three subagent presets that answer in "ultracave voice" (compressed output):
- **cavecrew-investigator**: Locate code (`path:line — symbol — note`)
- **cavecrew-builder**: Surgical edits ≤2 files (`path:line-range — change. verified: …`)
- **cavecrew-reviewer**: Diff review (`path:line: 🔴 severity: problem. fix.`)

**Token savings**: Subagent tool results returned compressed (~1/3 tokens vs vanilla Explore/edit/review). This is the REAL win — main context shrinks per delegation.

### 2. Caveman System Prompt (Secondary)
A system prompt for LLM-based prompt compression (requires LLM call):
- Strips greetings, polite markers, hedges, narrative
- Converts to `<verb> <object> <constraint>` structure
- Uses syntax-heavy shorthand (symbols, `;` separators)

**NOT a standalone CLI tool or binary.** No `caveman` command exists upstream.

## What AE Manifest Claims Were INCORRECT

| Claim in Old Manifest | Upstream Reality |
|----------------------|------------------|
| "Radical prompt compression... hemat token hingga 70%" | Marketing claim, not measured |
| "integrated-ready" | NO runtime integration in AE |
| "MCP: tokenizer-mcp" | Does NOT exist |
| "CAVEMAN_MODE=true env toggle" | Does NOT exist |
| "similarity ≥ 0.92 threshold" | Invented |
| "prompt rewriting via skill" | Requires LLM call, not deterministic tool |

## AE's Actual Compression Engine: Headroom

AE uses **Headroom** (Rust binary at `headroom/target/release/headroom`) for deterministic compression:
- Modes: auto, code, logs, json, markdown, generic
- No LLM required
- Preserves semantic meaning (line numbers, errors, checksums, provenance)
- Fallback Python compressor when binary unavailable

## When to Use What

| Need | Use |
|------|-----|
| Deterministic compression of logs/JSON/diffs/code | Headroom (`compress.py`) |
| Subagent delegation with compressed output | Cavecrew presets (via upstream skill) |
| LLM-based prompt rewriting (opt-in) | Caveman system prompt (manual) |

## Integration Notes

- This manifest documents upstream capability for discovery
- NO auto-activation, NO pipeline integration, NO runtime hooks
- If user wants cavecrew: they invoke upstream skill manually
- Headroom remains AE's default compression for all runtime use cases