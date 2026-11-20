---
title: Search Provider Integration
version: 3.1
last_updated: 2026-11-20
audience: users, maintainers
---

## Search Provider Integration

AE ships one first-party search server, `search-mcp`
(`unified-integration/mcp-servers/search-mcp/server.py`), with direct HTTPS
adapters for providers whose request contract was checked against the
provider's own documentation. It is exposed through the existing MCP gateway
as one tool, `search_web`. Keyless alternatives stay separate: `arxiv-mcp`
(arXiv API) and `google-news-mcp` (Google News RSS).

The `you-mcp`, `serper-mcp`, `tavily-mcp`, `exa-mcp`, `firecrawl-mcp` and
`newsapi-mcp` entries in `plugin-catalog/mcp-servers.json` remain `to-install`
roadmap entries for *external* MCP servers. They are not installed servers,
and their status is unchanged by `search-mcp`.

## Keys and readiness

Keys live only in `ui.api.json` `api_keys`, one array per reference
([configuration](CONFIGURATION.md)):

| Provider (`provider` argument) | Reference |
| --- | --- |
| `you` | `YOU_API_KEY` |
| `tavily` | `TAVILY_API_KEY` |
| `exa` | `EXA_API_KEY` |
| `firecrawl` | `FIRECRAWL_API_KEY` |
| `newsapi` | `NEWSAPI_KEY` |
| `serper` | `SERPER_API_KEY` |

- `search-mcp` is visible only while at least one of these references holds
  a usable key (`any_of`). The `provider` enum of `search_web` lists only
  providers that currently have a key; every call is re-validated against a
  fresh snapshot, so a removed key rejects the next call even if the host
  still shows the tool.
- Each HTTP request takes its key from the credential pool: three keys are
  used round-robin per request. Readiness checks and `status` never move the
  rotation pointer.
- Bounded failover (read-only search only): HTTP 401/402/403/429 (Tavily also
  432/433, NewsAPI 401/429; Serper answers an invalid key with 403) pauses
  that key (429: `Retry-After` bounded to
  1-300 s, else 60 s; auth/quota: 300 s) and retries the same query on the
  next key, at most 3 requests per call. Other errors return immediately.
  Several keys do not guarantee a higher quota.
- Redirects are refused, so a key header is never replayed to another
  origin. Errors, health output and diagnostics never contain key values.
- A personal `search_providers.json` is not part of AE. Nothing in AE reads,
  imports, migrates, copies or deletes it; its `.gitignore` rule stays only to
  protect the owner's private file.

## Evidence ledger (verified 2026-11-20)

| Provider | Official source | Request contract used | Result mapping | Status |
| --- | --- | --- | --- | --- |
| You.com | [v1 search](https://you.com/docs/api-reference/search/v1-search), [authentication](https://you.com/docs/using-the-api/authentication) | `POST https://ydc-index.io/v1/search`, header `X-API-Key`, body `query`, `count`, `freshness` | `results.web[]`: `title`, `url`, `description` (else `snippets[0]`), `page_age` | adapter + mock tests |
| Tavily | [search endpoint](https://docs.tavily.com/documentation/api-reference/endpoint/search) | `POST https://api.tavily.com/search`, `Authorization: Bearer`, body `query`, `max_results`, `time_range` | `results[]`: `title`, `url`, `content`, `published_date`, `score` | adapter + mock tests |
| Exa | [search reference](https://docs.exa.ai/reference/search) | `POST https://api.exa.ai/search`, header `x-api-key`, body `query`, `numResults`, `contents.text.maxCharacters`, `startPublishedDate` | `results[]`: `title`, `url`, `text`, `publishedDate`, `author` | adapter + mock tests (docs show no example response; mapping follows the schema) |
| Firecrawl | [v2 search](https://docs.firecrawl.dev/api-reference/endpoint/search), [rate limits](https://docs.firecrawl.dev/rate-limits) | `POST https://api.firecrawl.dev/v2/search`, `Authorization: Bearer`, body `query`, `limit`, `tbs` (`qdr:d`/`qdr:w` only) | `data.web[]`: `title`, `url`, `description` (no date) | adapter + mock tests; `month`/`year` freshness rejected (not in the official examples) |
| NewsAPI | [everything](https://newsapi.org/docs/endpoints/everything), [authentication](https://newsapi.org/docs/authentication), [errors](https://newsapi.org/docs/errors) | `GET https://newsapi.org/v2/everything`, header `X-Api-Key` (never the URL), `q`, `pageSize`, `sortBy=publishedAt`, `from` | `articles[]`: `title`, `url`, `description`, `publishedAt`, `source.name` | adapter + mock tests; free tier is development-only per NewsAPI pricing |
| Serper | [serper.dev](https://serper.dev/) (no public API reference; playground needs a login) | Observed in authorized live calls 2026-11-20: `POST https://google.serper.dev/search`, header `X-API-KEY`, body `q`, `num`, `tbs` (`qdr:d`/`qdr:y` echoed in `searchParameters`); invalid key → 403 `{"message":"Unauthorized."}` | `organic[]`: `title`, `link`, `snippet`, `date` (optional), `position` | adapter + mock + live tests; contract is empirical, not documented |

Package check (2026-11-20): `you-mcp` does not exist on npm and
`serper-mcp` is unpublished (use `search-mcp` provider `serper`). The
template no longer suggests `npx -y you-mcp`
or `npx -y serper-mcp`; installing an unverified package name is a
supply-chain risk.

Status levels are kept separate: *catalogued* (roadmap entry), *adapter
implemented*, *local mock-tested* (contract fixtures in
`tests/test_credential_pool.py`), *host-observed* (a real stdio MCP session
lists `search_web` only while a key exists; no credentialed call is made in
tests) and *live verified*.

Live verification (2026-11-20, maintainer-authorized keys, one key per
provider, 2-result queries): You.com, Tavily, Exa and Serper answered through
`run_search` with and without `freshness` and through a real stdio gateway
session (`search_web`, one call per provider). Serper also proved live
failover: `[invalid, valid]` returned results with `attempts: 2`. Revoking the
keys removed `search_web` and rejected the stale call. With three keys per
provider, three consecutive live calls used each key once (HTTP 200 each),
confirming per-request round-robin against the real APIs. **Firecrawl and
NewsAPI are not live verified** (no key available). Re-run with:

```bash
AE_SEARCH_LIVE=1 AGENT_ENHANCEMENTS_API_FILE=/path/to/private/ui.api.json \
  .agentenhancements/runtime/venv/bin/python -m unittest \
  test_credential_pool.LiveSearchTests   # from unified-integration/tests
```

## Verify safely

```bash
python3 unified-integration/scripts/api_config.py status
python3 unified-integration/scripts/registry.py search "web search" --type mcp
bash unified-integration/scripts/mcp-test.sh --priority P0
```

`status` prints key counts and readiness reasons, never values. The
`search-mcp` `health` result (through `ae_health`) lists the available
providers and per-provider key/cooldown counts. Use synthetic keys and
isolated fixtures (`AGENT_ENHANCEMENTS_API_FILE`) to inspect rotation. The
gateway has no `--help` interface; starting it runs the stdio server.

## Readiness failures

- `missing_credentials` (`missing` or `missing_any_of`): add a key to the
  listed reference(s).
- `runtime_not_configured`: configure an installed `command` (external entries).
- `executable_not_installed`: verify and install the chosen executable.
- `disabled`: review the user's explicit setting.
- `search_web` call error `provider_unavailable`: the provider has no usable
  key; `all_tried_keys_failed`: every tried key was rejected or rate limited.
