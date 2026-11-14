# arxiv-mcp

Paper search + metadata from the public arXiv Atom API for
understand-anything and agent-reach. Catalog entry:
`plugin-catalog/mcp-servers.json` → `arxiv-mcp` (P2, reference).

No API key required. Responses cached 1 h in `/tmp/ae-arxiv-cache`.

## Tools

| Tool | Args | Returns |
|------|------|---------|
| `health` | — | API endpoint + cache stats |
| `search` | `query`, `max_results?=5`, `sort?` (relevance \| lastUpdatedDate \| submittedDate) | papers with title/authors/abstract/pdf_url |
| `fetch` | `arxiv_id` (e.g. `2401.00001`) | one paper's full metadata |

## Env vars

None required (arXiv API is open).

## Run

```bash
python3 unified-integration/mcp-servers/arxiv-mcp/server.py   # stdio
```

## Test

Covered by `unified-integration/tests/test_mcp_servers.py`
(input validation, id format guard; live search runs only when the
network marker env is present and is otherwise skipped in CI).
