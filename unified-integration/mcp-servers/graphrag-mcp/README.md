# graphrag-mcp

Lexical GraphRAG for graphify / agent-reach. Catalog entry:
`plugin-catalog/mcp-servers.json` → `graphrag-mcp` (P2, graph).

**Honest scope:** entity extraction and relation scoring are *lexical*
(capitalized-phrase heuristics + co-occurrence with PMI-style weighting),
not LLM-driven. Fully offline, deterministic, testable. An LLM extractor
can be layered later behind the same tool API.

## Tools

| Tool | Args | Returns |
|------|------|---------|
| `health` | — | mode + store location |
| `index` | `corpus_id`, `documents[] {id?, text}` | stats: entities, relations, sentences |
| `query` | `corpus_id`, `question`, `k?=5` | question entities, 1-hop expansion, ranked evidence |
| `status` | `corpus_id` | stats + top entities |

## Persistence

Corpora are cached in memory and mirrored to `/tmp/ae-graphrag/<corpus>.json`.

## Env vars

None required.

## Run

```bash
python3 unified-integration/mcp-servers/graphrag-mcp/server.py   # stdio
```

## Test

Covered by `unified-integration/tests/test_mcp_servers.py`
(index 2 docs → query with entity overlap → ranked answer; unknown
corpus error; bad corpus_id rejection).
