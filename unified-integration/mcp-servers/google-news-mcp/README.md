# google-news-mcp

RSS fallback (no key) when NewsAPI is unavailable, feeding the
last-30-days skill. Catalog entry: `plugin-catalog/mcp-servers.json` →
`google-news-mcp` (P2, news).

## Tools

| Tool | Args | Returns |
|------|------|---------|
| `health` | — | supported languages + cache stats |
| `top` | `topic?`, `lang?=en`, `limit?=10` | headlines: title / link / published / source |

Languages: en, id, jp, kr, de, fr, es, pt, zh. Cache TTL 10 min in a
private (mode 0700) directory, `$AGENT_MEMORY_ROOT/mcp/news-cache` (default
`.agentenhancements/memory/mcp/news-cache` in this checkout); `health` reports
the exact `cache_dir`.

## Env vars

None required.

## Run

```bash
python3 unified-integration/mcp-servers/google-news-mcp/server.py   # stdio
```

## Test

Covered by `unified-integration/tests/test_mcp_servers.py`
(lang validation, limit clamping; live fetch only with the network
marker env, else skipped in CI).
