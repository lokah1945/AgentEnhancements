# MCP Integration Checklist — Finalizing the AgentEnhancements Merger

> Step-by-step build plan for the **38 MCP servers** required to activate all
> 21 plugins in `plugin-catalog/catalog.json`. Numbers below are computed from
> `plugin-catalog/mcp-servers.json` (run `python3 -c` snippet at the bottom to
> re-derive).
>
> **Status legend**
> - `to-install` (29 servers) — upstream package exists; install via `npx` /
>   `pip` and configure env vars.
> - `to-build` (9 servers) — no upstream package; must be implemented in-house
>   following the Anthropic `mcp-builder` skill pattern.

## 0. Pre-flight (do this before anything else)

- [ ] **0.1** Confirm `plugin-catalog/catalog.json` lists **21 plugins** and
      `plugin-catalog/mcp-servers.json` lists **38 servers**.
      ```bash
      python3 -c "import json; c=json.load(open('plugin-catalog/catalog.json')); m=json.load(open('plugin-catalog/mcp-servers.json')); print('plugins',len(c['skills']),'servers',len(m['servers']))"
      ```
      Note: `mcp-servers.json` description still says "20 plugin" — fix that
      string to "21 plugin" in a separate commit.
- [ ] **0.2** Provision a secrets vault (1Password CLI / `pass` / `direnv`).
      The catalog requires **20 distinct env vars**; never hard-code any.
- [ ] **0.3** Set up a Python 3.11+ venv for the 9 to-build servers:
      ```bash
      python3 -m venv ~/.venvs/agentenhancements-mcp
      source ~/.venvs/agentenhancements-mcp/bin/activate
      pip install mcp fastmcp pydantic
      ```
- [ ] **0.4** Set up Node 20+ for the 29 to-install servers:
      ```bash
      nvm use 20
      ```
- [ ] **0.5** Create the MCP config dir each agent CLI reads from
      (`~/.config/mcp/servers.json` is the conventional path; Cursor,
      Claude Code, Continue each have their own — `setup.sh` handles the
      symlink normalization).

---

## Phase 1 — P0 servers (blocker: skills non-functional without these)

**Goal:** install + configure the **5 P0 servers**. After Phase 1, the 4
plugins marked `P0-only-deps` (agent-reach, last-30-days, rea,
understand-anything, bmad-method, gsd, anthropic-skills, replica-skill,
agent-skills-addyosmani, impeccable, ui-ux-pro-max) become minimally usable.

### P0.1 `filesystem-mcp`  ·  core, no env vars

- [ ] Install: `npx -y @modelcontextprotocol/server-filesystem`
- [ ] Configure allowed paths: `$HOME`, project root, `/tmp/agentenhancements/`.
- [ ] Test: `mcp-call filesystem list_dir "$HOME"`
- [ ] Lock down: deny writes outside the allowlist.

### P0.2 `memory-mcp`  ·  memory, no env vars

- [ ] Install: `npx -y @modelcontextprotocol/server-memory`
- [ ] Storage path: `~/.local/share/agentenhancements/memory.json`
- [ ] Test: write a key, read it back, restart server, read again.

### P0.3 `browser-tools-mcp`  ·  browser, no env vars

- [ ] Install: `npx -y @agent-infra/browser-tools-mcp`
- [ ] Requires Playwright browsers: `npx playwright install chromium`
- [ ] Test: `mcp-call browser navigate "https://example.com" && screenshot`
- [ ] Pin to localhost / test fixtures only (see `.cursorrules` §3.3).

### P0.4 `brave-search-mcp`  ·  search, `BRAVE_API_KEY`

- [ ] Acquire key: <https://api.search.brave.com/app/dashboard>
- [ ] Store in vault: `op item create --category=api --title="brave" key=$BRAVE_API_KEY`
- [ ] Install: `npx -y @modelcontextprotocol/server-brave-search`
- [ ] Test: `mcp-call brave web_search "test query"`

### P0.5 `tavily-mcp`  ·  search, `TAVILY_API_KEY`

- [ ] Acquire key: <https://app.tavily.com/>
- [ ] Install: `npx -y tavily-mcp`
- [ ] Test: `mcp-call tavily search "test query" max_results=3`

### Phase 1 acceptance

- [ ] All 5 P0 servers respond to a `health` tool call.
- [ ] `python3 unified-integration/scripts/registry.py map "search the web"`
      routes to a plugin whose MCP deps are all P0-installed.
- [ ] End-to-end: run `agent-reach` skill against a 1-source test query and
      confirm a citation is returned.

---

## Phase 2 — P1 servers (22 servers; activate plugins fully)

### P1 batch A — Search & ingestion (4 servers)

| Server | Env var | Install / build |
|--------|---------|-----------------|
| `exa-mcp` | `EXA_API_KEY` | `npx -y exa-mcp-server` |
| `firecrawl-mcp` | `FIRECRAWL_API_KEY` | `npx -y firecrawl-mcp` |
| `newsapi-mcp` | `NEWSAPI_KEY` | `npx -y newsapi-mcp` |
| `wikipedia-mcp` | (none) | `npx -y wikipedia-mcp` |

- [ ] Acquire keys for Exa, Firecrawl, NewsAPI.
- [ ] Install all 4.
- [ ] Test each with one query.

### P1 batch B — Browser & frontend (4 servers)

| Server | Env var | Install / build |
|--------|---------|-----------------|
| `lighthouse-mcp` | (none) | `npx -y lighthouse-mcp` |
| `pa11y-mcp` | (none) | `npx -y pa11y-mcp` |
| `figma-mcp` | `FIGMA_TOKEN` | `npx -y figma-mcp-server` |
| `storybook-mcp` | (none) | `npx -y storybook-mcp` |

- [ ] Acquire Figma personal access token.
- [ ] Install all 4.
- [ ] Test lighthouse against `https://example.com` and assert a non-zero
      performance score.

### P1 batch C — Office & docs (4 servers)

| Server | Env var | Install / build |
|--------|---------|-----------------|
| `google-slides-mcp` | `GOOGLE_OAUTH_CLIENT_ID` + `SECRET` | `npx -y google-slides-mcp` |
| `office-mcp` | `MICROSOFT_CLIENT_ID` + `SECRET` | `npx -y office-mcp` |
| `image-search-mcp` | `BING_IMAGE_API_KEY` | `npx -y image-search-mcp` |
| `pdf-mcp` | (none) | `npx -y pdf-mcp` |

- [ ] Register Google OAuth client (Slides API scope).
- [ ] Register Microsoft Entra app (PowerPoint scope).
- [ ] Acquire Bing Image Search key.
- [ ] Install all 4.
- [ ] Test: generate a 3-slide deck via `ppt-master` skill.

### P1 batch D — Code & data (4 servers)

| Server | Env var | Install / build |
|--------|---------|-----------------|
| `typescript-language-server` | (none) | `npx -y typescript-language-server-mcp` |
| `eslint-mcp` | (none) | `npx -y eslint-mcp` |
| `jupyter-mcp` | (none) | `pip install jupyter-mcp` |
| `python-repl-mcp` | (none) | `pip install python-repl-mcp` |

- [ ] Install all 4.
- [ ] Test: run a 5-line numpy snippet via `python-repl-mcp`.

### P1 batch E — Task management (2 servers)

| Server | Env var | Install / build |
|--------|---------|-----------------|
| `github-issues-mcp` | `GITHUB_TOKEN` | `npx -y github-issues-mcp` |
| `task-router-mcp` | (none) | **BUILD** — see §P1 build B |

### P1 batch F — Diagrams & media (4 servers)

| Server | Env var | Install / build |
|--------|---------|-----------------|
| `mermaid-mcp` | (none) | `npx -y mermaid-mcp` |
| `heygen-mcp` | `HEYGEN_API_KEY` | `npx -y heygen-mcp` (consent-gated) |
| `elevenlabs-mcp` | `ELEVENLABS_API_KEY` | `npx -y elevenlabs-mcp` (consent-gated) |
| `embeddings-mcp` | `OPENAI_API_KEY` | **BUILD** — see §P1 build A |

### P1 build A — `embeddings-mcp`  ·  category=ml, status=to-build

- [ ] Spec: tools `embed(text, model="text-embedding-3-small")`,
      `embed_batch(texts[])`, `cosine(a, b)`.
- [ ] Backend: OpenAI by default; allow LangChain local fallback.
- [ ] Path: `unified-integration/mcp-servers/embeddings-mcp/server.py`.
- [ ] Follow `anthropic-skills/skills/mcp-builder/SKILL.md`.
- [ ] Test: embed "hello", embed "world", cosine > 0.
- [ ] Wire env var `OPENAI_API_KEY`.

### P1 build B — `task-router-mcp`  ·  category=task, status=to-build

- [ ] Spec: tools `dispatch(task_spec)`, `track(task_id)`, `cancel(task_id)`,
      `health`.
- [ ] Backend: in-process thread pool; spawn sub-agent via `setup.sh`'s
      `launch-agent.sh`.
- [ ] Path: `unified-integration/mcp-servers/task-router-mcp/server.py`.
- [ ] Test: dispatch a 2-step task, verify both complete.

### P1 build C — `ffmpeg-mcp`  ·  category=media, status=to-build

- [ ] Spec: tools `cut(path, start, end)`, `concat(paths[])`, `transcode(path,
      codec)`, `extract_audio(path)`, `thumbnail(path, t)`.
- [ ] Backend: shell out to `ffmpeg`; never expose arbitrary args.
- [ ] Path: `unified-integration/mcp-servers/ffmpeg-mcp/server.py`.
- [ ] Test: cut a 10s test clip to 5s, compare durations.

### P1 build D — `vision-mcp`  ·  category=core, status=to-build

- [ ] Spec: tools `describe(image_path)`, `ocr(image_path)`,
      `compare(img_a, img_b)`.
- [ ] Backend: OpenAI Vision (`gpt-4o`) by default; allow local LLaVA fallback.
- [ ] Path: `unified-integration/mcp-servers/vision-mcp/server.py`.
- [ ] Test: describe a screenshot, assert non-empty caption.

### Phase 2 acceptance

- [ ] All 22 P1 servers (18 install + 4 build) respond to `health`.
- [ ] At least one plugin from each of the 5 categories runs end-to-end with
      its full MCP dependency set:
      - code: `agent-skills-addyosmani` (lighthouse audit)
      - research: `graphify` (extract entities from 1 page) — note: requires
        neo4j-mcp from P1 batch (graph) below
      - tokens: `gsd` (run a 3-item checklist)
      - design: `ppt-master` (3-slide deck)
      - multimedia: `anthropic-skills` (generate a .docx)

### P1 batch G — Graph (left out of acceptance; needed by `graphify`)

- [ ] `neo4j-mcp` (P1, env: `NEO4J_URI` + `NEO4J_USER` + `NEO4J_PASSWORD`):
      install via `npx -y neo4j-mcp-server` after provisioning a Neo4j
      instance (Aura Free tier is fine for dev).

---

## Phase 3 — P2 servers (11 servers; nice-to-have / fallbacks)

### P2 install batch (7 servers)

| Server | Env var | Notes |
|--------|---------|-------|
| `linear-mcp` | `LINEAR_API_KEY` | Optional PM tool for bmad-method |
| `excalidraw-mcp` | (none) | Whiteboard-style diagrams |
| `storybook-mcp` (dup) | (none) | Already in P1; keep for QA |
| `google-news-mcp` | (none) | **BUILD** — RSS fallback for NewsAPI |
| `arxiv-mcp` | (none) | **BUILD** — paper fetcher |
| `graphrag-mcp` | `OPENAI_API_KEY` | **BUILD** — GraphRAG retrieval |
| `video-mcp` | (none) | **BUILD** — timeline wrapper |
| `style-mcp` | (none) | **BUILD** — AI-ism detector |
| `grammar-mcp` | `LANGUAGE_TOOL_URL` | Self-host LanguageTool |

### P2 build A — `graphrag-mcp`  ·  graph, to-build

- [ ] Use Microsoft GraphRAG as backend; expose `index(docs[])`,
      `query(question)`.
- [ ] Path: `unified-integration/mcp-servers/graphrag-mcp/server.py`.

### P2 build B — `arxiv-mcp`  ·  reference, to-build

- [ ] Use `arxiv` PyPI lib; expose `search(query, max=10)`,
      `fetch(arxiv_id)`.

### P2 build C — `google-news-mcp`  ·  news, to-build

- [ ] RSS scraping of `news.google.com`; expose `top(topic, lang)`.

### P2 build D — `video-mcp`  ·  media, to-build

- [ ] Wraps `ffmpeg-mcp` with shot-list + timeline semantics.

### P2 build E — `style-mcp`  ·  writing, to-build

- [ ] AI-ism detector: regex + small classifier for "delve", "in conclusion",
      "navigate the landscape", etc.
- [ ] Expose `score(text)`, `rewrite(text, target_score)`.

### Phase 3 acceptance

- [ ] All 11 P2 servers respond to `health`.
- [ ] Optional: enable `humanizer` end-to-end with `style-mcp` + `grammar-mcp`.

---

## Phase 4 — Wiring & QA

- [ ] **4.1** Update `plugin-catalog/mcp-servers.json`: flip every server's
      `status` from `to-install`/`to-build` → `installed` as it lands.
- [ ] **4.2** Regenerate the modular tree + index:
      ```bash
      bash scripts/scaffold_modular_skills.sh
      python3 scripts/generate_skills_index.py
      ```
- [ ] **4.3** Update `unified-integration/setup.sh` MCP-install section to
      auto-install all `installed` servers and refuse to start if any P0
      server is missing (fail-fast).
- [ ] **4.4** Add a CI job `test-mcp-health` that pings every `installed`
      server's `health` tool against a stub agent.
- [ ] **4.5** Update `README.md` and `README_INTEGRATION.md` "What's next"
      section to reflect completion.
- [ ] **4.6** Document the env-var setup in `docs/ENV_VARS.md` (one row per
      var: name, purpose, where to obtain, rotation policy).
- [ ] **4.7** Tag a release: `git tag v2.0.0-mcp-complete`.

---

## Quick scoreboard

| Phase | Servers delivered | Cumulative | Notes |
|-------|-------------------|------------|-------|
| 1 | 5 (P0) | 5 / 38 | Skills minimally usable |
| 2 | 22 (P1) | 27 / 38 | Skills fully usable per category |
| 3 | 11 (P2) | 38 / 38 | Complete |
| 4 | — | — | Wiring + QA + release |

## Build vs install split

| Status | Count | Servers |
|--------|-------|---------|
| `to-install` | 29 | brave-search, tavily, exa, firecrawl, neo4j, browser-tools, lighthouse, pa11y, figma, storybook, mermaid, excalidraw, google-slides, office, image-search, heygen, elevenlabs, typescript-language-server, eslint, jupyter, python-repl, memory, github-issues, linear, wikipedia, newsapi, grammar, filesystem, pdf |
| `to-build` | 9 | graphrag, embeddings, ffmpeg, video, task-router, arxiv, google-news, vision, style |

## Required API integrations (20 distinct env vars)

| Var | Server | How to obtain |
|-----|--------|---------------|
| `BRAVE_API_KEY` | brave-search-mcp | <https://api.search.brave.com> |
| `TAVILY_API_KEY` | tavily-mcp | <https://app.tavily.com> |
| `EXA_API_KEY` | exa-mcp | <https://exa.ai> |
| `FIRECRAWL_API_KEY` | firecrawl-mcp | <https://firecrawl.dev> |
| `OPENAI_API_KEY` | embeddings-mcp, graphrag-mcp, vision-mcp | <https://platform.openai.com/api-keys> |
| `NEWSAPI_KEY` | newsapi-mcp | <https://newsapi.org> |
| `FIGMA_TOKEN` | figma-mcp | Figma → Settings → Personal access tokens |
| `GOOGLE_OAUTH_CLIENT_ID` | google-slides-mcp | Google Cloud Console → APIs → Slides API |
| `GOOGLE_OAUTH_CLIENT_SECRET` | google-slides-mcp | (same as above) |
| `MICROSOFT_CLIENT_ID` | office-mcp | Entra ID → App registration → PowerPoint scope |
| `MICROSOFT_CLIENT_SECRET` | office-mcp | (same as above) |
| `BING_IMAGE_API_KEY` | image-search-mcp | Azure Portal → Bing Search v7 |
| `HEYGEN_API_KEY` | heygen-mcp | <https://app.heygen.com> (consent gate!) |
| `ELEVENLABS_API_KEY` | elevenlabs-mcp | <https://elevenlabs.io> (consent gate!) |
| `GITHUB_TOKEN` | github-issues-mcp | GitHub → Settings → Developer settings → PAT (repo scope) |
| `LINEAR_API_KEY` | linear-mcp | <https://linear.app/settings/api> |
| `NEO4J_URI` | neo4j-mcp | Aura Free tier or self-hosted |
| `NEO4J_USER` | neo4j-mcp | (instance-specific) |
| `NEO4J_PASSWORD` | neo4j-mcp | (instance-specific) |
| `LANGUAGE_TOOL_URL` | grammar-mcp | self-host `languagetool/languagetool` Docker image |

---

## Re-derivation snippet

Numbers in this document are computed from `plugin-catalog/mcp-servers.json`
on 2026-11-14. To re-derive after edits:

```bash
python3 - <<'PY'
import json, collections
m = json.load(open('plugin-catalog/mcp-servers.json'))
s = m['servers']
print(f"Total: {len(s)}")
print("By priority:", dict(collections.Counter(x['priority'] for x in s)))
print("By status:", dict(collections.Counter(x['status'] for x in s)))
print("To-build:", [x['id'] for x in s if x['status']=='to-build'])
PY
```

---

_End of MCP integration checklist._
