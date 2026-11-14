# Environment Variables Reference

Every secret / config knob the MCP roadmap and the in-house servers use,
with where to obtain it and how it is consumed. Keys are **read at call
time** from the environment; they are never written to the repo, never
logged, and `health()` probes report only booleans.

Rotation policy: treat every key here as rotate-on-suspicion, review
quarterly. Revoke keys that have appeared in chat, screenshots, or shell
history immediately.

## In-house servers (`unified-integration/mcp-servers/`)

| Var | Server | Required | Purpose |
|-----|--------|----------|---------|
| `OPENAI_API_KEY` | embeddings-mcp, vision-mcp | for openai/semantic modes | text-embedding-3-small; gpt-4o-mini vision. Without it: deterministic `local` embedder and honest `basic_metadata` describe mode. |
| `AE_FFMPEG_ALLOWED_ROOTS` | ffmpeg-mcp | no | extra allowed path roots for inputs/outputs (`:`-separated). Defaults: cwd + /tmp. |

The remaining in-house servers (task-router, graphrag, arxiv,
google-news, video, style) need **no** environment variables.

## Upstream to-install servers (see `plugin-catalog/mcp-servers.json`)

### Search (P0/P1)

| Var | Server | Obtain from |
|-----|--------|-------------|
| `BRAVE_API_KEY` | brave-search-mcp (P0) | <https://api.search.brave.com/app/dashboard> |
| `TAVILY_API_KEY` | tavily-mcp (P0) | <https://app.tavily.com> |
| `EXA_API_KEY` | exa-mcp (P1) | <https://exa.ai> |
| `FIRECRAWL_API_KEY` | firecrawl-mcp (P1) | <https://firecrawl.dev> |

### Graph / ML (P1)

| Var | Server | Obtain from |
|-----|--------|-------------|
| `NEO4J_URI` | neo4j-mcp | Aura Free tier <https://neo4j.com/cloud/aura/> or self-hosted |
| `NEO4J_USER` | neo4j-mcp | instance credential |
| `NEO4J_PASSWORD` | neo4j-mcp | instance credential |
| `OPENAI_API_KEY` | graphrag upstream, embeddings | <https://platform.openai.com/api-keys> |

### Browser / frontend (P1)

| Var | Server | Obtain from |
|-----|--------|-------------|
| `FIGMA_TOKEN` | figma-mcp | Figma → Settings → Personal access tokens |

### Office / media (P1)

| Var | Server | Obtain from |
|-----|--------|-------------|
| `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` | google-slides-mcp | Google Cloud Console → enable Slides API → OAuth client |
| `MICROSOFT_CLIENT_ID` / `_SECRET` | office-mcp | Entra ID → App registration → PowerPoint (Graph) scope |
| `BING_IMAGE_API_KEY` | image-search-mcp | Azure Portal → Bing Search v7 resource |
| `HEYGEN_API_KEY` | heygen-mcp | <https://app.heygen.com> — **consent gate: ask before cloning any real person** |
| `ELEVENLABS_API_KEY` | elevenlabs-mcp | <https://elevenlabs.io> — **consent gate: ask before voice cloning** |

### Task / reference / news (P1/P2)

| Var | Server | Obtain from |
|-----|--------|-------------|
| `GITHUB_TOKEN` | github-issues-mcp | GitHub → Settings → Developer settings → PAT (repo scope, fine-grained preferred) |
| `LINEAR_API_KEY` | linear-mcp (P2) | <https://linear.app/settings/api> |
| `NEWSAPI_KEY` | newsapi-mcp (P2) | <https://newsapi.org> |
| `LANGUAGE_TOOL_URL` | grammar-mcp (P2) | self-host: `docker run -p 8010:8010 languagetool/languagetool` → `http://localhost:8010` |

## Recommended provisioning

```bash
# direnv per-project (never commit .envrc with real values)
echo 'export OPENAI_API_KEY="$(op read "op://Personal/openai/api-key")"' >> .envrc
direnv allow

# or pass per-invocation only
OPENAI_API_KEY="$(op read 'op://Personal/openai/api-key')" \
  python3 unified-integration/mcp-servers/embeddings-mcp/server.py
```

Rule of thumb: **env > vault lookup > prompt**. Never put keys in
`mcp.json` (it is a plain file that tools sync and back up).
