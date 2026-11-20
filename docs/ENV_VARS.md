---
title: Environment Variables Reference
version: 1.2
last_updated: 2026-11-20
audience: users, maintainers
---

## Environment Variables Reference

Every secret / config knob the MCP roadmap and the in-house servers use,
with where to obtain it and how it is consumed. MCP keys are resolved from the
private root `ui.api.json` and configured
search-provider key slots. Empty central values never inherit API credentials
from the shell. Subprocesses receive only mapped references. Status/health
probes report presence and readiness, never key values.

Rotation policy: treat every key here as rotate-on-suspicion, review
quarterly. Revoke keys that have appeared in chat, screenshots, or shell
history immediately.

### In-house servers (`unified-integration/mcp-servers/`)

- **Var:** `OPENAI_API_KEY`
  - **Server:** embeddings-mcp, vision-mcp
  - **Required:** for openai/semantic modes
  - **Purpose:** text-embedding-3-small; gpt-4o-mini vision. **Privacy:** with
    the key set, `vision-mcp describe` uploads the image (base64) to
    `api.openai.com` / `OPENAI_BASE_URL` — see docs/SAFETY.md §3. Without it:
    deterministic `local` embedder and honest `basic_metadata` describe mode.

- **Var:** `AE_FFMPEG_ALLOWED_ROOTS`
  - **Server:** ffmpeg-mcp
  - **Required:** no
  - **Purpose:** extra allowed path roots for inputs/outputs (`:`-separated).
    Defaults: cwd + /tmp.

The remaining in-house servers (task-router, graphrag, arxiv,
google-news, video, style) need **no** environment variables.

**task-router-mcp** runs arbitrary bash/python payloads with your user
privileges. It is **hidden by default** and must be enabled explicitly in
`ui.api.json` (`"task-router-mcp": {"enabled": true}`) — see docs/SAFETY.md §0.

### Upstream to-install servers (see `plugin-catalog/mcp-servers.json`)

#### Search (P0/P1)

| Var | Server | Obtain from |
| ----- | -------- | ------------- |
| `YOU_API_KEY` | you-mcp (P0) | Provider account dashboard |
| `SERPER_API_KEY` | serper-mcp (P0) | Provider account dashboard |
| `TAVILY_API_KEY` | tavily-mcp (P0) | <https://app.tavily.com> |
| `EXA_API_KEY` | exa-mcp (P1) | <https://exa.ai> |
| `FIRECRAWL_API_KEY` | firecrawl-mcp (P1) | <https://firecrawl.dev> |

#### Graph / ML (P1)

- **Var:** `NEO4J_URI`
  - **Server:** neo4j-mcp
  - **Obtain from:** Aura Free tier <https://neo4j.com/cloud/aura/> or
    self-hosted

- **Var:** `NEO4J_USER`
  - **Server:** neo4j-mcp
  - **Obtain from:** instance credential

- **Var:** `NEO4J_PASSWORD`
  - **Server:** neo4j-mcp
  - **Obtain from:** instance credential

- **Var:** `OPENAI_API_KEY`
  - **Server:** graphrag upstream, embeddings
  - **Obtain from:** <https://platform.openai.com/api-keys>

#### Browser / frontend (P1)

| Var | Server | Obtain from |
| ----- | -------- | ------------- |
| `FIGMA_TOKEN` | figma-mcp | Figma → Settings → Personal access tokens |

#### Office / media (P1)

- **Var:** `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET`
  - **Server:** google-slides-mcp
  - **Obtain from:** Google Cloud Console → enable Slides API → OAuth client

- **Var:** `MICROSOFT_CLIENT_ID` / `_SECRET`
  - **Server:** office-mcp
  - **Obtain from:** Entra ID → App registration → PowerPoint (Graph) scope

- **Var:** `BING_IMAGE_API_KEY`
  - **Server:** image-search-mcp
  - **Obtain from:** Azure Portal → Bing Search v7 resource

- **Var:** `HEYGEN_API_KEY`
  - **Server:** heygen-mcp
  - **Obtain from:** <https://app.heygen.com> — **consent gate: ask before
    cloning any real person**

- **Var:** `ELEVENLABS_API_KEY`
  - **Server:** elevenlabs-mcp
  - **Obtain from:** <https://elevenlabs.io> — **consent gate: ask before voice
    cloning**

#### Task / reference / news (P1/P2)

- **Var:** `GITHUB_TOKEN`
  - **Server:** github-issues-mcp
  - **Obtain from:** GitHub → Settings → Developer settings → PAT (repo scope,
    fine-grained preferred)

- **Var:** `LINEAR_API_KEY`
  - **Server:** linear-mcp (P2)
  - **Obtain from:** <https://linear.app/settings/api>

- **Var:** `NEWSAPI_KEY`
  - **Server:** newsapi-mcp (P2)
  - **Obtain from:** <https://newsapi.org>

- **Var:** `LANGUAGE_TOOL_URL`
  - **Server:** grammar-mcp (P2)
  - **Obtain from:** self-host: `docker run -p 8010:8010
    languagetool/languagetool` → `http://localhost:8010`

### AgentEnhancements Integration Variables

- **Variable:** `AGENT_ENHANCEMENTS_BASE_DIR`
  - **Purpose:** Project root
  - **Default:** auto-detected from setup.sh location

- **Variable:** `AGENT_MEMORY_ROOT`
  - **Purpose:** Memory storage
  - **Default:** `.agentenhancements/memory`

- **Variable:** `AGENT_SKILLS_DIR`
  - **Purpose:** Skills registry
  - **Default:** `$BASE_DIR/unified-integration/skills`

- **Variable:** `HEADROOM_BIN`
  - **Purpose:** Compression binary
  - **Default:** auto-detect (repo build, then PATH)

- **Variable:** `AE_MAX_SKILL_CARDS`
  - **Purpose:** Max skill cards per prompt
  - **Default:** `8` (configurable)

- **Variable:** `AGENT_ENHANCEMENTS_BUILD_HEADROOM`
  - **Purpose:** Build headroom by default
  - **Default:** `1` (set to `0` to skip)

- **Variable:** `AGENT_SKILLS_NATIVE_TARGETS`
  - **Purpose:** Skill link targets (colon-separated)
  - **Default:**
    `~/.claude/skills:~/.agents/skills:~/.codex/skills:~/.config/opencode/skills`

### Recommended provisioning

Run setup to create the ignored, private `ui.api.json`, then edit the
credential arrays (one or more keys per reference) and connection fields
locally. Keep secrets out of host-native MCP command arguments and tracked
files. Provider and preflight keys are never read from the shell environment:
an exported `TAVILY_API_KEY` or `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY` has no
effect. See [configuration](CONFIGURATION.md) for the version 2 schema,
multi-key rotation and the one-time `api_config.py migrate` upgrade.

Use `python3 unified-integration/scripts/api_config.py status` for safe
key-count/readiness diagnostics. Never print raw keys to test rotation.
