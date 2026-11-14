# google-news-mcp

RSS fallback (no key) when NewsAPI is unavailable, feeding the
last-30-days skill. Catalog entry: `plugin-catalog/mcp-servers.json` →
`google-news-mcp` (P2, news).

## Tools

| Tool | Args | Returns |
|------|------|---------|
| `health` | — | supported languages + cache stats |
| `top` | `topic?`, `lang?=en`, `limit?=10` | headlines: title / link / published / source |

Languages: en, id, jp, kr, de, fr, es, pt, zh. Cache TTL 10 min in
`/tmp/ae-news-cache`.

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
