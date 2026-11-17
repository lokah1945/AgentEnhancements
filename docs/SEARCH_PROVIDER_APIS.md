# Search Provider API Documentation

Reference for implementing search provider MCP servers with correct parameters and round-robin key rotation.

---

## 1. You.com Search API

**Base URL:** `https://api.you.com`
**Authentication:** Bearer token in Authorization header
**Documentation:** https://api.you.com/

### Endpoints

#### Search
```
POST /search
Authorization: Bearer <YOU_API_KEY>
Content-Type: application/json

{
  "query": "string",
  "recency": "day|week|month|year",      // Optional: time filter
  "count": 10,                            // Optional: results per page (max 20)
  "page": 1                               // Optional: pagination
}
```

#### Response
```json
{
  "results": [
    {
      "title": "string",
      "url": "string",
      "snippet": "string",
      "source": "string",
      "published_date": "ISO8601"
    }
  ],
  "total_results": 100,
  "query": "string"
}
```

### Rate Limits
- Free tier: 100 requests/day
- Pro tier: 1000 requests/day
- Enterprise: Custom

### Implementation Notes
- Use `recency` parameter for time-filtered searches (maps to last-30-days `recency` param)
- Round-robin across 3 API keys via `get_search_provider_key('you')`
- Header: `Authorization: Bearer <key>`

---

## 2. Tavily AI Search API

**Base URL:** `https://api.tavily.com`
**Authentication:** API key in request body
**Documentation:** https://docs.tavily.com/

### Endpoints

#### Search
```
POST /search
Content-Type: application/json

{
  "api_key": "<TAVILY_API_KEY>",
  "query": "string",
  "search_depth": "basic|advanced",       // Optional: "basic" (fast) or "advanced" (comprehensive)
  "topic": "general|news|finance",        // Optional: search category
  "max_results": 10,                       // Optional: max 20
  "include_domains": [],                   // Optional: whitelist
  "exclude_domains": [],                   // Optional: blacklist
  "include_answer": true,                  // Optional: AI summary
  "include_raw_content": false,            // Optional: full page content
  "include_images": false                  // Optional: image URLs
}
```

#### Response
```json
{
  "query": "string",
  "answer": "string",                      // AI-generated summary (if include_answer=true)
  "results": [
    {
      "title": "string",
      "url": "string",
      "content": "string",
      "score": 0.95,
      "raw_content": "string",             // If include_raw_content=true
      "published_date": "ISO8601"
    }
  ],
  "response_time": 1.23
}
```

### Rate Limits
- Free tier: 1000 requests/month
- Pro tier: 10000 requests/month
- Enterprise: Custom

### Implementation Notes
- Use `search_depth` parameter for last-30-days (maps to "advanced" for comprehensive)
- Round-robin across 3 API keys via `get_search_provider_key('tavily')`
- API key in request body, not header

---

## 3. Serper (Google Search) API

**Base URL:** `https://google.serper.dev`
**Authentication:** API key in X-API-KEY header
**Documentation:** https://serper.dev/api

### Endpoints

#### Search
```
POST /search
X-API-KEY: <SERPER_API_KEY>
Content-Type: application/json

{
  "q": "string",                           // Query string
  "gl": "us",                              // Optional: country code (default "us")
  "hl": "en",                              // Optional: language code (default "en")
  "num": 10,                               // Optional: results per page (max 100)
  "page": 1,                               // Optional: pagination
  "type": "search|news|places|images",     // Optional: search type
  "time_range": "day|week|month|year"      // Optional: time filter (maps to last-30-days)
}
```

#### News Search
```
POST /news
X-API-KEY: <SERPER_API_KEY>
Content-Type: application/json

{
  "q": "string",
  "time_range": "month",                   // Maps to last-30-days
  "num": 10
}
```

#### Response
```json
{
  "searchParameters": { "q": "...", "type": "search" },
  "organic": [
    {
      "title": "string",
      "link": "string",
      "snippet": "string",
      "position": 1,
      "date": "ISO8601"
    }
  ],
  "news": [...],                            // For news type
  "relatedSearches": [...]
}
```

### Rate Limits
- Free tier: 2500 requests/month
- Pro tier: 10000 requests/month
- Enterprise: Custom

### Implementation Notes
- Use `time_range` parameter for last-30-days (maps to "month")
- Round-robin across 3 API keys via `get_search_provider_key('serper')`
- Header: `X-API-KEY: <key>`

---

## 4. Exa Neural Search API

**Base URL:** `https://api.exa.ai`
**Authentication:** Bearer token in Authorization header
**Documentation:** https://exa.ai/docs

### Endpoints

#### Search
```
POST /search
Authorization: Bearer <EXA_API_KEY>
Content-Type: application/json

{
  "query": "string",
  "type": "neural|keyword|auto",           // Optional: search mode (default "auto")
  "num_results": 10,                        // Optional: max 100
  "include_domains": [],                    // Optional: whitelist
  "exclude_domains": [],                    // Optional: blacklist
  "start_published_date": "ISO8601",        // Optional: date filter (maps to last-30-days)
  "end_published_date": "ISO8601",          // Optional: date filter
  "use_autoprompt": true,                   // Optional: query enhancement
  "category": "news|general|academic",      // Optional: content category
  "include_text": true,                     // Optional: include full text
  "text_max_length": 1000                   // Optional: max text length
}
```

#### Response
```json
{
  "results": [
    {
      "title": "string",
      "url": "string",
      "text": "string",                     // Full text if include_text=true
      "score": 0.95,
      "published_date": "ISO8601",
      "author": "string"
    }
  ],
  "request_id": "string"
}
```

### Rate Limits
- Free tier: 1000 requests/month
- Pro tier: 10000 requests/month
- Enterprise: Custom

### Implementation Notes
- Use `start_published_date`/`end_published_date` for last-30-days filtering
- Round-robin across 3 API keys via `get_search_provider_key('exa')`
- Header: `Authorization: Bearer <key>`
- Best for semantic/neural search, not just keyword matching

---

## 5. Firecrawl (Scraping + Search)

**Base URL:** `https://api.firecrawl.dev`
**Authentication:** Bearer token in Authorization header
**Documentation:** https://firecrawl.dev/api

### Endpoints

#### Search
```
POST /search
Authorization: Bearer <FIRECRAWL_API_KEY>
Content-Type: application/json

{
  "query": "string",
  "limit": 10,                              // Optional: max results
  "scrapeOptions": {                        // Optional: scrape each result
    "formats": ["markdown", "html"],
    "onlyMainContent": true,
    "includeTags": [],
    "excludeTags": []
  }
}
```

#### Scrape
```
POST /scrape
Authorization: Bearer <FIRECRAWL_API_KEY>
Content-Type: application/json

{
  "url": "string",
  "formats": ["markdown", "html", "json"],
  "onlyMainContent": true
}
```

### Rate Limits
- Free tier: 500 requests/month
- Pro tier: 5000 requests/month

### Implementation Notes
- Not a traditional search engine - scrapes and extracts content
- Best for deep content extraction after initial search
- Round-robin NOT needed (single key in search_providers.json)
- Used by: `agent-reach`, `graphify`

---

## 6. Google News MCP (Built-in)

**Implementation:** `unified-integration/mcp-servers/google-news-mcp/`
**Status:** Built-in (no API key required)
**Source:** RSS feeds from Google News

### Features
- RSS-based news aggregation
- No API key required
- Supports `when` parameter for time filtering (`1d`, `7d`, `30d`)
- Categories: World, Business, Technology, etc.

### Implementation Notes
- Built-in server, always available
- Used by: `last-30-days`
- No round-robin needed (no API keys)

---

## 7. NewsAPI

**Base URL:** `https://newsapi.org/v2`
**Authentication:** API key in query parameter or header
**Documentation:** https://newsapi.org/docs

### Endpoints

#### Everything
```
GET /everything
Authorization: Bearer <NEWSAPI_KEY>
? q=string
& from=ISO8601
& to=ISO8601
& language=en
& sortBy=publishedAt|relevancy|popularity
& pageSize=10
```

#### Top Headlines
```
GET /top-headlines
Authorization: Bearer <NEWSAPI_KEY>
? category=technology
& country=us
& pageSize=10
```

### Rate Limits
- Free tier: 100 requests/day
- Pro tier: 500 requests/day

### Implementation Notes
- Use `from`/`to` parameters for last-30-days filtering
- Round-robin NOT needed (single key in search_providers.json)
- Used by: `last-30-days`

---

## Round-Robin Implementation Summary

All four primary search providers (You.com, Tavily, Serper, Exa) use round-robin key rotation via `get_search_provider_key(provider)` in `api_config.py`.

### Gateway Integration (`gateway.py`)

```python
# In External.run()
env = {}
for name, ref in self.settings.get("env", {}).items():
    if ref in ("TAVILY_API_KEY", "EXA_API_KEY", "SERPER_API_KEY", "YOU_API_KEY"):
        provider = ref.replace("_API_KEY", "").lower()
        rr_key = get_search_provider_key(provider)  # Thread-safe round-robin
        if rr_key:
            env[name] = rr_key
        else:
            env[name] = value(ref, self.config)
    else:
        env[name] = value(ref, self.config)
```

### Key Rotation Pattern

Each provider maintains independent round-robin index:
```
Call 1: key_1
Call 2: key_2  
Call 3: key_3
Call 4: key_1 (cycles back)
...
```

Thread-safe via `threading.Lock()` in `api_config.py`.

---

## Configuration Files

| File | Purpose | Git Status |
|------|---------|------------|
| `ui.api.json` | Central config, references provider names | Tracked |
| `search_providers.json` | Actual API keys (template) | **Gitignored** |
| `/root/credential/search_providers.json` | Legacy location (removed) | N/A |

### Security
- `search_providers.json` is in `.gitignore`
- Template uses placeholder keys: `YOUR_<PROVIDER>_API_KEY_<N>_HERE`
- Users must replace with real keys before use
- Real keys never committed to GitHub

---

## Testing Commands

```bash
# Verify search providers loaded
python3 unified-integration/scripts/api_config.py status

# Test round-robin
cd unified-integration/scripts && python3 -c "
from api_config import get_search_provider_key
for p in ['you','tavily','serper','exa']:
    print(p, [get_search_provider_key(p) for _ in range(4)])
"

# Test gateway integration
python3 unified-integration/mcp-servers/gateway.py --help
```

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `visible=False, reason=missing_credentials` | API key not in ui.api.json | Add key to ui.api.json |
| `visible=False, reason=executable_not_installed` | MCP server not installed | Run `npx -y <server>` |
| `visible=False, reason=runtime_not_configured` | No command in ui.api.json | Add command array to mcp entry |
| Round-robin returns placeholder | Real keys not in search_providers.json | Replace placeholders with real keys |

---

## Migration from Legacy Location

Old location: `/root/credential/search_providers.json` → **Removed**
New location: `/root/project/AgentEnhancements/search_providers.json` → **Gitignored**

The `api_config.py` now references:
```python
SEARCH_PROVIDERS_PATH = ROOT / "search_providers.json"
```

Where `ROOT = Path(__file__).resolve().parent.parent` = AE repository root.