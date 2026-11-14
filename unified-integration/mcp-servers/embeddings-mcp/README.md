# embeddings-mcp

Uniform embedding service for vector-dependent skills (graphify,
understand-anything, agent-reach). Catalog entry:
`plugin-catalog/mcp-servers.json` → `embeddings-mcp` (P1, ml).

## Tools

| Tool | Args | Returns |
|------|------|---------|
| `health` | — | backend availability (never the key itself) |
| `embed` | `text`, `backend?` ("openai" \| "local") | `{backend, dim, embedding}` |
| `embed_batch` | `texts[]`, `backend?` | `{backend, dim, embeddings[]}` |
| `cosine` | `a[]`, `b[]` | `{similarity}` |

## Backends

- **openai** — `text-embedding-3-small` via REST (stdlib urllib, no SDK).
  Requires `OPENAI_API_KEY`. Selected by default when the key is present.
- **local** — deterministic 256-dim hashed bag-of-words, L2-normalized.
  Offline, zero deps, byte-stable across runs. Default when no key.

## Env vars

| Var | Required | Purpose |
|-----|----------|---------|
| `OPENAI_API_KEY` | for openai backend | API key (read at call time, never logged) |

## Run

```bash
python3 unified-integration/mcp-servers/embeddings-mcp/server.py   # stdio
```

## Test

Covered by `unified-integration/tests/test_mcp_servers.py` (local backend
end-to-end: embed → cosine; determinism; error envelopes).
