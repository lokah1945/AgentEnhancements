# search-mcp

First-party web search adapters. Catalog entry:
`plugin-catalog/mcp-servers.json` → `search-mcp` (P0, search, status `built`).

Direct HTTPS adapters (Python stdlib, no SDK) for providers whose request
contract was checked against the provider's official documentation; the
evidence ledger is in [docs/SEARCH_PROVIDER_APIS.md](../../../docs/SEARCH_PROVIDER_APIS.md).

| Provider | Key reference in `ui.api.json` | Endpoint |
|----------|-------------------------------|----------|
| `you` | `YOU_API_KEY` | `POST https://ydc-index.io/v1/search` |
| `tavily` | `TAVILY_API_KEY` | `POST https://api.tavily.com/search` |
| `exa` | `EXA_API_KEY` | `POST https://api.exa.ai/search` |
| `firecrawl` | `FIRECRAWL_API_KEY` | `POST https://api.firecrawl.dev/v2/search` |
| `newsapi` | `NEWSAPI_KEY` | `GET https://newsapi.org/v2/everything` |
| `serper` | `SERPER_API_KEY` | `POST https://google.serper.dev/search` (contract observed live; no public API reference) |

## Tools

| Tool | Args | Returns |
|------|------|---------|
| `health` | — | server status, `available` providers, key counts per provider |
| `web` | `query`, `provider`, `count` (1-20), `freshness` (day/week/month/year) | normalized `results[]`: `provider`, `title`, `url`, `snippet`, `published_at` when present |

Through the gateway the tool is `search_web`; its `provider` enum lists only
providers that currently have a usable key, and the server is hidden when
none has one.

## Keys and rotation

Each reference in `ui.api.json` `api_keys` is an array. Every HTTP request
asks the credential pool for its key, so `["k1", "k2", "k3"]` is used
round-robin per request. A 401/402/403/429 (and Tavily 432/433) cools that
key down and retries the same query on the next key, at most 3 requests in
total. Other errors return immediately. Redirects are refused so a key
header cannot be replayed to another origin. Errors never contain keys.

## Run

```bash
python3 unified-integration/mcp-servers/search-mcp/server.py   # stdio
```

Normally it is loaded in-process by the gateway (`mcp-servers/gateway.py`).
