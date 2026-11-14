# In-house MCP Servers

Nine MCP servers built inside AgentEnhancements (the `to-build` entries of
`plugin-catalog/mcp-servers.json`). Each directory is a self-contained
stdio server following the
`anthropic-skills/skills/mcp-builder` house pattern: schema'd tools,
deterministic outputs where possible, actionable error envelopes, a
`health` probe, and no secret logging.

| Server | Priority | Category | Feeds plugins | Offline |
|--------|----------|----------|---------------|---------|
| [`embeddings-mcp`](./embeddings-mcp/) | P1 | ml | graphify, understand-anything, agent-reach | local backend |
| [`task-router-mcp`](./task-router-mcp/) | P1 | task | gsd, bmad-method, rea | yes |
| [`ffmpeg-mcp`](./ffmpeg-mcp/) | P1 | media | openmontage | yes (needs ffmpeg binary) |
| [`vision-mcp`](./vision-mcp/) | P1 | core | anthropic-skills, impeccable, replica-skill | compare/ocr/metadata |
| [`graphrag-mcp`](./graphrag-mcp/) | P2 | graph | graphify, agent-reach | yes (lexical mode) |
| [`arxiv-mcp`](./arxiv-mcp/) | P2 | reference | understand-anything, agent-reach | no (open API, no key) |
| [`google-news-mcp`](./google-news-mcp/) | P2 | news | last-30-days | no (open RSS, no key) |
| [`video-mcp`](./video-mcp/) | P2 | media | openmontage, hyperframes | timeline/edl yes |
| [`style-mcp`](./style-mcp/) | P2 | writing | humanizer | yes |

## Common conventions

- **Run**: `python3 unified-integration/mcp-servers/<slug>/server.py`
  (stdio transport, MCP SDK `FastMCP`).
- **Health**: every server exposes `health()` returning
  `{"status": "ok", ...}` — used by CI and `setup-mcp.sh --check`.
- **Errors**: `{"error": ..., "hint": ...}` envelopes, never tracebacks.
- **Secrets**: keys are read from the environment at call time; health
  reports only booleans.
- **Tests**: `python3 unified-integration/tests/run-tests.py` includes
  `test_mcp_servers.py`; a quick manual pass is
  `python3 unified-integration/mcp-servers/smoke_test.py`.

## Install / wire into agent CLIs

```bash
bash unified-integration/scripts/setup-mcp.sh            # all built servers
bash unified-integration/scripts/setup-mcp.sh --check    # health-check mode
```

The script renders `mcp.json` blocks (see `mcp.json.example`) for Claude
Code, Cursor, Continue, Windsurf, Codex and the generic
`~/.agents/mcp.json` convention, using absolute paths resolved from this
repo clone.

The 29 remaining `to-install` servers (P0/P1 upstream packages such as
brave-search or filesystem) are **not** installed by this script — they
need API keys and per-user consent. Follow
`docs/MCP_INTEGRATION_CHECKLIST.md` Phase 1/2 for those.
