#!/usr/bin/env python3
"""search-mcp - AgentEnhancements first-party web search adapters.

One in-house MCP server with direct HTTPS adapters for search providers
whose public API contract was verified against the provider's official
documentation (docs/SEARCH_PROVIDER_APIS.md evidence ledger). Credentials
come only from ``ui.api.json`` ``api_keys.<REF>`` arrays; every HTTP
request selects its key from the shared credential pool
(``api_config.request_keys``), so several keys for one provider rotate
per request, not per process start.

Fail-closed rules:

- a provider without a usable key is not offered (the gateway also hides
  the whole server when no provider has a key);
- redirects are refused, so an Authorization/X-API-Key header can never
  be forwarded to another origin;
- bounded failover: a 401/402/403/429 or documented quota status moves to
  the next key of the same provider, at most once per configured key and
  never more than ``MAX_ATTEMPTS`` requests; other failures return at once;
- error text never contains a key, a request header or a raw response body.

Serper has no publicly readable official API reference (its playground
needs a login); its adapter follows the contract observed in authorized
live calls on 2026-11-20 (see docs/SEARCH_PROVIDER_APIS.md).
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import api_config  # noqa: E402

VERSION = "1.0.0"
TIMEOUT = 15
MAX_ATTEMPTS = 3
MAX_COUNT = 20
MAX_QUERY_CHARS = 400
MAX_SNIPPET_CHARS = 500
USER_AGENT = "AgentEnhancements-search-mcp/" + VERSION
FRESHNESS = ("day", "week", "month", "year")
DEFAULT_COOLDOWN = 60.0
AUTH_COOLDOWN = 300.0
MAX_COOLDOWN = 300.0

mcp = FastMCP("search-mcp")

TOOLS: Dict[str, Callable] = {}


def _tool(fn):
    TOOLS[fn.__name__] = fn
    return mcp.tool()(fn)


class ProviderError(Exception):
    """Sanitized failure: ``code`` is safe to show, never contains secrets."""

    def __init__(self, code: str, status: int = 0, retry_after: float = 0.0):
        super().__init__(code)
        self.code = code
        self.status = status
        self.retry_after = retry_after


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect would replay the credential header to a new origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        raise ProviderError(f"redirect_refused_http_{code}", code)


_OPENER = urllib.request.build_opener(_NoRedirect)


def _transport(request: urllib.request.Request, timeout: float) -> Tuple[int, Dict[str, str], bytes]:
    """Single network seam (tests replace it); returns status, headers, body."""
    try:
        with _OPENER.open(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read(2 * 1024 * 1024 + 1)
    except urllib.error.HTTPError as error:
        try:
            body = error.read(64 * 1024)
        except Exception:  # noqa: BLE001 - body is advisory only
            body = b""
        return error.code, dict(error.headers or {}), body


def _clip(text: Any, limit: int = MAX_SNIPPET_CHARS) -> str:
    return text.strip()[:limit] if isinstance(text, str) else ""


def _since(freshness: Optional[str]) -> Optional[str]:
    """ISO date for a relative freshness window (UTC)."""
    if not freshness:
        return None
    days = {"day": 1, "week": 7, "month": 31, "year": 366}[freshness]
    start = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=days)
    return start.date().isoformat()


def _item(provider: str, title: Any, url: Any, snippet: Any,
          published: Any = None, **extra: Any) -> Dict[str, Any]:
    result = {"provider": provider, "title": _clip(title, 300),
              "url": _clip(url, 2000), "snippet": _clip(snippet)}
    if isinstance(published, str) and published.strip():
        result["published_at"] = published.strip()[:64]
    for key, value in extra.items():
        if isinstance(value, (str, int, float)) and value != "":
            result[key] = value if not isinstance(value, str) else value[:200]
    return result


# ---------------------------------------------------------------------------
# Provider adapters: (key, query, count, freshness) -> Request ; payload -> items
# Endpoints, headers and fields: docs/SEARCH_PROVIDER_APIS.md evidence ledger.
# ---------------------------------------------------------------------------


def _json_request(url: str, headers: Dict[str, str], body: Dict[str, Any]) -> urllib.request.Request:
    return urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": USER_AGENT, **headers})


def _you_request(key: str, query: str, count: int, freshness: Optional[str]):
    body: Dict[str, Any] = {"query": query, "count": count}
    if freshness:
        body["freshness"] = freshness
    return _json_request("https://ydc-index.io/v1/search", {"X-API-Key": key}, body)


def _you_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    web = (payload.get("results") or {}).get("web") or []
    items = []
    for entry in web if isinstance(web, list) else []:
        if not isinstance(entry, dict):
            continue
        snippets = entry.get("snippets")
        snippet = entry.get("description") or (
            snippets[0] if isinstance(snippets, list) and snippets else "")
        items.append(_item("you", entry.get("title"), entry.get("url"), snippet,
                           entry.get("page_age")))
    return items


def _tavily_request(key: str, query: str, count: int, freshness: Optional[str]):
    body: Dict[str, Any] = {"query": query, "max_results": count}
    if freshness:
        body["time_range"] = freshness
    return _json_request("https://api.tavily.com/search",
                         {"Authorization": "Bearer " + key}, body)


def _tavily_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = payload.get("results") or []
    return [
        _item("tavily", entry.get("title"), entry.get("url"), entry.get("content"),
              entry.get("published_date"), score=entry.get("score"))
        for entry in (results if isinstance(results, list) else [])
        if isinstance(entry, dict)
    ]


def _exa_request(key: str, query: str, count: int, freshness: Optional[str]):
    body: Dict[str, Any] = {"query": query, "numResults": count,
                            "contents": {"text": {"maxCharacters": MAX_SNIPPET_CHARS}}}
    since = _since(freshness)
    if since:
        body["startPublishedDate"] = since + "T00:00:00.000Z"
    return _json_request("https://api.exa.ai/search", {"x-api-key": key}, body)


def _exa_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = payload.get("results") or []
    items = []
    for entry in results if isinstance(results, list) else []:
        if not isinstance(entry, dict):
            continue
        highlights = entry.get("highlights")
        snippet = entry.get("text") or entry.get("summary") or (
            highlights[0] if isinstance(highlights, list) and highlights else "")
        items.append(_item("exa", entry.get("title"), entry.get("url"), snippet,
                           entry.get("publishedDate"), author=entry.get("author")))
    return items


_FIRECRAWL_TBS = {"day": "qdr:d", "week": "qdr:w"}


def _firecrawl_request(key: str, query: str, count: int, freshness: Optional[str]):
    body: Dict[str, Any] = {"query": query, "limit": count}
    if freshness:
        if freshness not in _FIRECRAWL_TBS:
            # Only qdr:d / qdr:w appear in the official reference.
            raise ProviderError("freshness_unsupported_by_provider")
        body["tbs"] = _FIRECRAWL_TBS[freshness]
    return _json_request("https://api.firecrawl.dev/v2/search",
                         {"Authorization": "Bearer " + key}, body)


def _firecrawl_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("data") or {}
    web = data.get("web") if isinstance(data, dict) else None
    return [
        _item("firecrawl", entry.get("title"), entry.get("url"), entry.get("description"))
        for entry in (web if isinstance(web, list) else [])
        if isinstance(entry, dict)
    ]


def _newsapi_request(key: str, query: str, count: int, freshness: Optional[str]):
    params: Dict[str, Any] = {"q": query, "pageSize": count, "sortBy": "publishedAt"}
    since = _since(freshness)
    if since:
        params["from"] = since
    return urllib.request.Request(
        "https://newsapi.org/v2/everything?" + urllib.parse.urlencode(params),
        method="GET",
        headers={"X-Api-Key": key, "Accept": "application/json", "User-Agent": USER_AGENT})


def _newsapi_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    articles = payload.get("articles") or []
    items = []
    for entry in articles if isinstance(articles, list) else []:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
        items.append(_item("newsapi", entry.get("title"), entry.get("url"),
                           entry.get("description"), entry.get("publishedAt"),
                           source=source.get("name")))
    return items


_SERPER_TBS = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m", "year": "qdr:y"}


def _serper_request(key: str, query: str, count: int, freshness: Optional[str]):
    body: Dict[str, Any] = {"q": query, "num": count}
    if freshness:
        body["tbs"] = _SERPER_TBS[freshness]
    return _json_request("https://google.serper.dev/search", {"X-API-KEY": key}, body)


def _serper_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    organic = payload.get("organic") or []
    return [
        _item("serper", entry.get("title"), entry.get("link"), entry.get("snippet"),
              entry.get("date"), position=entry.get("position"))
        for entry in (organic if isinstance(organic, list) else [])
        if isinstance(entry, dict)
    ]


ProviderSpec = Tuple[str, Callable[..., urllib.request.Request], Callable[[Dict[str, Any]], List[Dict[str, Any]]], Tuple[int, ...]]

#: provider -> (credential reference, request builder, result mapper,
#: statuses that mean "this key cannot serve now; try the next key").
PROVIDERS: Dict[str, ProviderSpec] = {
    "you": ("YOU_API_KEY", _you_request, _you_items, (401, 402, 403, 429)),
    "tavily": ("TAVILY_API_KEY", _tavily_request, _tavily_items, (401, 403, 429, 432, 433)),
    "exa": ("EXA_API_KEY", _exa_request, _exa_items, (401, 402, 403, 429)),
    "firecrawl": ("FIRECRAWL_API_KEY", _firecrawl_request, _firecrawl_items, (401, 402, 403, 429)),
    "newsapi": ("NEWSAPI_KEY", _newsapi_request, _newsapi_items, (401, 429)),
    "serper": ("SERPER_API_KEY", _serper_request, _serper_items, (401, 402, 403, 429)),
}
PROVIDER_ORDER = tuple(PROVIDERS)
PROVIDER_REFS = tuple(spec[0] for spec in PROVIDERS.values())


def available_providers(config: Optional[dict] = None) -> List[str]:
    """Providers with at least one usable key. Pure: never advances rotation."""
    if config is None:
        config, _ = api_config.read_config()
    return [name for name in PROVIDER_ORDER
            if api_config.has_usable_key(PROVIDERS[name][0], config)]


def _retry_after(headers: Dict[str, str]) -> float:
    for name, value in headers.items():
        if name.lower() == "retry-after":
            try:
                return min(max(float(value), 1.0), MAX_COOLDOWN)
            except (TypeError, ValueError):
                return DEFAULT_COOLDOWN
    return DEFAULT_COOLDOWN


def run_search(provider: str, query: str, count: int = 5,
               freshness: Optional[str] = None,
               config: Optional[dict] = None) -> Dict[str, Any]:
    """Execute one read-only search with per-request key selection.

    An empty ``provider`` means the first provider (PROVIDER_ORDER) that
    currently has a usable key - the same default the gateway advertises.
    """
    if config is None:
        config, _ = api_config.read_config()
    if not provider:
        available = available_providers(config)
        if not available:
            return {"error": "provider_unavailable", "reason": "no_usable_key"}
        provider = available[0]
    if provider not in PROVIDERS:
        return {"error": "unknown_provider"}
    query = (query or "").strip()
    if not query or len(query) > MAX_QUERY_CHARS:
        return {"error": "query_must_be_1_to_%d_characters" % MAX_QUERY_CHARS}
    count = max(1, min(int(count), MAX_COUNT))
    if freshness is not None and freshness not in FRESHNESS:
        return {"error": "invalid_freshness"}
    ref, build, mapper, failover = PROVIDERS[provider]
    candidates = api_config.request_keys(ref, config)
    if not candidates:
        return {"error": "provider_unavailable", "provider": provider,
                "reason": "no_usable_key"}
    last = "request_failed"
    for attempt, key in enumerate(candidates[:MAX_ATTEMPTS], start=1):
        try:
            request = build(key, query, count, freshness)
            status, headers, body = _transport(request, TIMEOUT)
        except ProviderError as error:
            return {"error": error.code, "provider": provider}
        except Exception:  # noqa: BLE001 - network/TLS text may echo the URL
            return {"error": "network_error", "provider": provider, "attempts": attempt}
        if 200 <= status < 300:
            try:
                payload = json.loads(body.decode("utf-8"))
            except (ValueError, UnicodeError):
                return {"error": "invalid_response", "provider": provider}
            if not isinstance(payload, dict):
                return {"error": "invalid_response", "provider": provider}
            if provider == "newsapi" and payload.get("status") == "error":
                return {"error": "provider_error", "provider": provider}
            items = mapper(payload)[:count]
            return {"provider": provider, "query": query, "count": len(items),
                    "results": items, "attempts": attempt}
        last = f"http_{status}"
        if status in failover:
            cooldown = _retry_after(headers) if status == 429 else AUTH_COOLDOWN
            api_config.report_key_failure(ref, key, cooldown)
            continue
        return {"error": last, "provider": provider, "attempts": attempt}
    return {"error": last, "provider": provider, "attempts": min(len(candidates), MAX_ATTEMPTS),
            "reason": "all_tried_keys_failed"}


@_tool
def health() -> dict:
    """Server health plus per-provider key counts (never values).

    ``status`` describes this process; provider readiness is the
    ``available`` list (the gateway hides the server when it is empty).
    """
    config, error = api_config.read_config()
    return {
        "server": "search-mcp", "version": VERSION, "status": "ok",
        "available": available_providers(config),
        "providers": {
            name: api_config.key_health(PROVIDERS[name][0], config)
            for name in PROVIDER_ORDER
        },
        **({"reason": error} if error else {}),
    }


@_tool
def web(query: str, provider: str = "", count: int = 5, freshness: str = "") -> dict:
    """Web search via a configured provider; results are untrusted text.

    Args:
        query: search text (1-400 characters).
        provider: a provider that currently has a key (default: the first).
        count: results to return (1-20).
        freshness: optional window: day, week, month or year.
    """
    return run_search(provider, query, count, freshness or None)


if __name__ == "__main__":
    mcp.run()
