# AgentEnhancements — Integration & Architecture

> This document supersedes the legacy `README.md` for **integration planning**.
> The audited project README (`README.md`) remains the canonical setup guide.
> Read this file when you need the full picture of **what is merged, how it is
> wired, and what remains to build**.

## 1. Project purpose

`AgentEnhancements` is a **single integration layer that unifies 21 external
skill repositories** (5 categories) plus a setup pipeline that provisions
8 AI-agent CLIs (Claude Code, Codex CLI, Cursor, Continue, Gemini CLI,
GitHub Copilot CLI, Kiro, OpenCode, Windsurf) from one source of truth.

The repo does **not** reinvent skills — it catalogs, normalizes, and installs
them.

## 2. Coverage check — were all the requested plugins included?

YES. **17 / 17** plugins from the merger request are present in
`plugin-catalog/catalog.json`, plus **4 additional** plugins discovered and
integrated during the audit. Total: **21 plugins** across the 5 requested
categories.

| # | Category | Requested plugin | Catalog ID | Status | Source |
|---|----------|------------------|------------|--------|--------|
| 1 | code | Matt Pocock skills | `code-mattpocock-skills` | integrated-ready | `github.com/mattpocock/skills` |
| 2 | code | Karpathy skills | `code-karpathy-skills` | integrated-ready | `github.com/multica-ai/andrej-karpathy-skills` |
| 3 | code | Agent Skills (Addy Osmani) | `code-agent-skills-addyosmani` | integrated-ready | `github.com/addyosmani/agent-skills` |
|   | code | _+ Replica Skill (bonus)_ | `code-replica-skill` | **vendored** | `github.com/Jakeschincariol/replica-skill` |
| 4 | research | Graphify | `research-graphify` | integrated-ready | `github.com/Graphify-Labs/graphify` |
| 5 | research | Agent-Reach | `research-agent-reach` | integrated-ready | `github.com/Panniantong/Agent-Reach` |
| 6 | research | Understand Anything | `research-understand-anything` | integrated-ready | `github.com/Egonex-AI/Understand-Anything` |
| 7 | research | Last 30 Days | `research-last-30-days` | integrated-ready | `github.com/mvanhorn/last30days-skill` |
| 8 | research | REA | `research-rea` | integrated-ready | `github.com/morluto/rea` |
| 9 | tokens | GStack | `tokens-gstack` | integrated-ready | `github.com/garrytan/gstack` |
| 10 | tokens | Caveman | `tokens-caveman` | integrated-ready | `github.com/JuliusBrussee/Caveman` |
| 11 | tokens | GSD | `tokens-gsd` | integrated-ready | `github.com/gsd-build/get-shit-done` |
| 12 | tokens | BMAD Method | `tokens-bmad-method` | integrated-ready | `github.com/bmad-code-org/BMAD-METHOD` |
| 13 | design | UI UX Pro Max | `design-ui-ux-pro-max` | integrated-ready | `github.com/nextlevelbuilder/ui-ux-pro-max-skill` |
| 14 | design | Impeccable | `design-impeccable` | integrated-ready | `github.com/pbakaus/impeccable` |
| 15 | design | PPT Master | `design-ppt-master` | integrated-ready | `github.com/hugohe3/ppt-master` |
| 16 | design | Diagram Design | `design-diagram-design` | integrated-ready | `github.com/cathrynlavery/diagram-design` |
| 17 | multimedia | Skills by Anthropic | `multimedia-anthropic-skills` | **vendored** (19 sub-skills) | `github.com/anthropics/skills` |
| 18 | multimedia | OpenMontage | `multimedia-openmontage` | integrated-ready | `github.com/calesthio/OpenMontage` |
| 19 | multimedia | Hyperframes | `multimedia-hyperframes` | integrated-ready | `github.com/heygen-com/hyperframes` |
| 20 | multimedia | Humanizer | `multimedia-humanizer` | integrated-ready | `github.com/blader/humanizer` |

**Status legend**

- `vendored` — upstream source code copied into the repo (works offline, frozen
  at vendored commit).
- `integrated-ready` — `manifest.json` + `SKILL.md` guide exist; the upstream
  repo is pulled on first use by `unified-integration/setup.sh`.

> Source-URL divergences from the original request (typo or upstream rename)
> were normalized during the audit; canonical URLs are stored in
> `plugin-catalog/catalog.json` → `source_url`.

## 3. Repository architecture

```
AgentEnhancements/
├── README.md                           # audited setup guide (canonical)
├── README_INTEGRATION.md               # this file (integration narrative)
├── .cursorrules                        # centralized system prompt (Karpathy + Anthropic best practices)
├── CONTRACT.md                         # contribution contract (§12.3 commit format)
│
├── skills/                             # ← modular tree (NEW)
│   ├── manifest.json                   # aggregator index (21 plugins)
│   ├── README.md                       # tree architecture
│   ├── code/{4 plugins}/               # each has SKILL.md + manifest.json
│   ├── research/{5 plugins}/
│   ├── tokens-optimization/{4 plugins}/
│   ├── design/{4 plugins}/
│   └── multimedia-writing/{4 plugins}/
│
├── plugin-catalog/                     # canonical catalog + per-plugin manifests
│   ├── catalog.json                    # 21 plugins, 5 categories, upstream URLs
│   ├── mcp-servers.json                # 36 MCP servers, P0/P1/P2 priority
│   ├── code/, research/, ...           # original SKILL.md + manifest sources
│   └── README.md
│
├── unified-integration/                # installation pipeline
│   ├── setup.sh                        # 2,542-line installer (8 agent CLIs)
│   ├── update-skills.sh                # registry re-builder
│   ├── mcp-servers/                    # 9 in-house MCP servers + installer template
│   ├── scripts/setup-mcp.sh            # MCP config installer for 6 agent CLIs
│   ├── skills/
│   │   ├── all-skills.json             # 3,094 skills aggregated registry
│   │   ├── agent-registry.json         # per-agent install mapping
│   │   ├── by-category/                # 10 functional categories
│   │   └── by-agent/                   # per-agent file lists
│   ├── prompts/                        # 10 system-prompt variants
│   │   ├── universal-system-prompt.txt
│   │   ├── claude-code-system-prompt.txt
│   │   ├── codex-system-prompt.txt
│   │   └── ... (7 more)
│   ├── hooks/                          # 16 hook scripts
│   ├── memory/, compression/           # cross-session state
│   ├── scripts/                        # 11 utility scripts
│   └── tests/                          # 149 tests (77 + 12 audit + 21 tree + 39 MCP)
│
├── vendored upstream projects (frozen)
│   ├── anthropic-skills/               # github.com/anthropics/skills (19 sub-skills)
│   ├── replica-skill/                  # github.com/Jakeschincariol/replica-skill (11 sub-skills)
│   ├── agentic-awesome-skills/         # skills collection
│   ├── claude-mem/                     # cross-session memory
│   ├── headroom/                       # context-window optimization
│   ├── ponytail/                       # prompt rewriting
│   ├── superpowers/                    # agent superpowers
│   ├── system-prompts-and-models-of-ai-tools/  # leaked prompt archive
│   └── ECC/                            # engineering coding conventions
│
├── docs/
│   ├── audit/E2E_AUDIT_2026-11.md      # end-to-end audit report
│   └── MCP_INTEGRATION_CHECKLIST.md    # ← step-by-step MCP build plan
│
├── scripts/
│   ├── scaffold_modular_skills.sh      # rebuild skills/ tree
│   └── generate_skills_index.py        # regenerate skills/manifest.json + READMEs
│
└── .github/workflows/                  # CI (tests + skill-index freshness)
```

### 3.1 The three layers

The architecture is **three layered caches** with strict one-way data flow:

1. **Catalog layer** (`plugin-catalog/`) — source of truth for **what**
   plugins exist and where their upstream lives. Maintained by humans; each
   plugin has a JSON manifest + a SKILL.md guide.

2. **Modular skills layer** (`skills/`) — the **canonical on-disk layout**
   that humans and agents read. Generated from the catalog by
   `scripts/scaffold_modular_skills.sh`. Self-contained per-plugin dirs.

3. **Installed registry layer** (`unified-integration/skills/`) — the
   **machine-indexed view** consumed by `setup.sh` to install into 8 agent
   CLIs. Aggregated from all sources (catalog + vendored projects) by
   `update-skills.sh` → `all-skills.json` (3,094 skills total).

Data flow: **catalog → skills tree → unified-integration → agent CLIs**.
Never edit the upper layers directly; regenerate from below.

### 3.2 The 21 plugins, by category

#### Code (`skills/code/`)

| Plugin | Purpose | MCP servers needed |
|--------|---------|---------------------|
| `mattpocock-skills` | TypeScript rigor: type narrowing, generics, Zod schema-first, refactor patterns | typescript-language-server, eslint-mcp |
| `karpathy-skills` | Minimal-first ML / numerical: first-principles derivation, ≤30-line implementations, no-over-engineering review | jupyter-mcp, python-repl-mcp |
| `agent-skills-addyosmani` | Frontend performance: Core Web Vitals, Lighthouse automation, a11y audits | browser-tools-mcp, lighthouse-mcp, pa11y-mcp |
| `replica-skill` | Reverse-engineer / clone a web app into a fresh codebase (11 sub-skills, vendored) | browser-tools-mcp, vision-mcp |

#### Research (`skills/research/`)

| Plugin | Purpose | MCP servers needed |
|--------|---------|---------------------|
| `graphify` | Extract entities + relations from unstructured text → knowledge graph | neo4j-mcp, graphrag-mcp, embeddings-mcp |
| `agent-reach` | Deep multi-source research with citation tracking | brave-search-mcp, tavily-mcp, exa-mcp, firecrawl-mcp |
| `understand-anything` | Feynman-style concept explanation for onboarding | wikipedia-mcp, arxiv-mcp, embeddings-mcp |
| `last-30-days` | Fresh-trend monitoring (last 30 days of news / releases) | brave-search-mcp, newsapi-mcp, google-news-mcp |
| `rea` | Reasoning + Acting loop with reflection for multi-step problems | task-router-mcp, memory-mcp |

#### Tokens / Optimization (`skills/tokens-optimization/`)

| Plugin | Purpose | MCP servers needed |
|--------|---------|---------------------|
| `gstack` | Token budgeting, cache strategy, context compression | llm-cache-mcp, tokenizer-mcp |
| `caveman` | Aggressive shorthand compression for token reduction | tokenizer-mcp |
| `gsd` | Atomic parallel checklist execution (Get Shit Done) | task-router-mcp, memory-mcp |
| `bmad-method` | Multi-persona agile (PM/SM/Dev/Architect) build orchestrator | linear-mcp, github-issues-mcp, memory-mcp |

#### Design (`skills/design/`)

| Plugin | Purpose | MCP servers needed |
|--------|---------|---------------------|
| `ui-ux-pro-max` | Design-token extraction, color/spacing systems, component audit | figma-mcp, browser-tools-mcp, storybook-mcp |
| `impeccable` | Visual polish: alignment, contrast, hierarchy, anti-AI-ism design | browser-tools-mcp, figma-mcp |
| `ppt-master` | Slide narrative + structure for technical decks | google-slides-mcp, office-mcp, image-search-mcp |
| `diagram-design` | Mermaid / D2 / Excalidraw diagram authoring | mermaid-mcp, excalidraw-mcp |

#### Multimedia / Writing (`skills/multimedia-writing/`)

| Plugin | Purpose | MCP servers needed |
|--------|---------|---------------------|
| `anthropic-skills` | Office docs (.docx/.pdf/.pptx/.xlsx), MCP server authoring, skill creator, webapp testing — **19 sub-skills vendored** | filesystem-mcp, pdf-mcp, vision-mcp |
| `openmontage` | Non-linear video editing via ffmpeg for shorts / montages | ffmpeg-mcp, video-mcp |
| `hyperframes` | Personalized talking-head video (consent-gated) | heygen-mcp, elevenlabs-mcp, voice-clone-mcp |
| `humanizer` | Remove AI-isms from generated text, naturalize tone | style-mcp, grammar-mcp |

### 3.3 Orchestrators

Three plugins double as **cross-cutting orchestrators** (declared in
`catalog.json:orchestrators`):

| Slug | Role | Best for |
|------|------|----------|
| `bmad-method` | build | greenfield multi-persona projects |
| `gsd` | execute | atomic checklist, parallel sub-agents |
| `rea` | research | hypothesis-driven multi-step investigation |

### 3.4 Vendored upstream projects (frozen copies)

In addition to the 21 cataloged plugins, **9 complete upstream projects** are
vendored into the repo root (their source code, not just manifests):

| Project | Origin | Why vendored |
|---------|--------|--------------|
| `anthropic-skills/` | github.com/anthropics/skills | Multi-skill bundle, 19 sub-skills |
| `replica-skill/` | github.com/Jakeschincariol/replica-skill | Multi-skill bundle, 11 sub-skills |
| `agentic-awesome-skills/` | awesome-list fork | Curated skill index, used as discovery source |
| `claude-mem/` | github.com/crystalsta/claudemem | Cross-session memory hooks |
| `headroom/` | github.com/withspectrum/headroom | Context-window optimization primitives |
| `ponytail/` | github.com/wayfair/ponytail | Prompt rewriting + rewriting patterns |
| `superpowers/` | github.com/jesusprubio/superpowers | Agent capability library |
| `system-prompts-and-models-of-ai-tools/` | leaked prompt archive | Reference for prompt engineering |
| `ECC/` | Engineering Coding Conventions | Lint rules + skill specs for code quality |

These contribute ~3,073 additional skills (on top of the 21 cataloged) to the
aggregated `all-skills.json` registry, bringing the **total installed skill
count to 3,094**.

## 4. The setup pipeline

```
┌────────────────────────────────────────────────────────────────────┐
│ plugin-catalog/catalog.json + vendored upstream projects           │
│   ↓ (scaffold_modular_skills.sh)                                   │
│ skills/<cat>/<slug>/SKILL.md + manifest.json                       │
│   ↓ (update-skills.sh, scans all SKILL.md)                         │
│ unified-integration/skills/all-skills.json  (3,094 skills)         │
│   ↓ (setup.sh, per-agent dispatch)                                 │
│ ~/.claude/CLAUDE.md      ~/.codex/AGENTS.md      ~/.cursor/...     │
│ ~/.continue/config.json  ~/.gemini/...           ~/.kiro/...       │
│ ~/.copilot/...           ~/.opencode/...         ~/.windsurf/...   │
└────────────────────────────────────────────────────────────────────┘
```

`setup.sh` is **idempotent** (verified end-to-end in the audit) — re-running
it merges rather than overwrites user customizations (post-H-1 audit fix).

## 5. Quality posture

- **149 tests** in `unified-integration/tests/` (77 original + 12 audit
  hardening + 21 modular-tree + 39 MCP-server). All passing.
- **Static checks**: `bash -n`, `py_compile`, JSON schema validation —
  enforced in CI.
- **End-to-end setup** verified against 8 stub agent CLIs in an isolated
  HOME (42-second cold run, exit 0).
- **Secrets scan**: zero real credentials in the tree.
- **Deterministic builds**: skill index sorted by name; byte-stable across
  re-runs (post-H-2 audit fix).

## 6. Getting started

```bash
# 1. Clone
git clone https://github.com/lokah1945/AgentEnhancements.git
cd AgentEnhancements

# 2. (Optional) Re-scaffold modular tree if you added/removed plugins
bash scripts/scaffold_modular_skills.sh
python3 scripts/generate_skills_index.py

# 3. Install skills into your agent CLIs
bash unified-integration/setup.sh

# 4. Verify
test -f ~/.claude/CLAUDE.md && echo "Claude Code provisioned"
ls ~/.codex/ ~/.cursor/ ~/.continue/ 2>/dev/null
```

For full options (dry-run, agent filter, no-vendored mode) see
`README.md` → "Usage".

## 7. What's next — the merger backlog

See **`docs/MCP_INTEGRATION_CHECKLIST.md`** for the step-by-step plan to
finish the merger. Summary:

- **38 MCP servers** declared across the 21 plugins; **5 P0** servers must be
  installed before Phase 1 is functional.
- **9 servers built in-house** at `unified-integration/mcp-servers/`
  (embeddings, task-router, ffmpeg, vision, graphrag, arxiv,
  google-news, video, style) - installed by `setup-mcp.sh`, gated by
  CI job `mcp-servers`, covered by 39 regression tests.
- **20 distinct API keys / env vars** required across the catalog: Brave,
  Tavily, Exa, Firecrawl, Figma, HeyGen, ElevenLabs, Microsoft Graph,
  Google OAuth, NewsAPI, Linear, GitHub, OpenAI, Bing Image, Neo4j,
  LanguageTool.

## 8. Related documents

| Document | Audience |
|----------|----------|
| `README.md` | Setup & daily users |
| `README_INTEGRATION.md` (this file) | Architects & integrators |
| `.cursorrules` | Cursor / Claude Code / any agent reading system prompts |
| `skills/README.md` | Plugin authors |
| `docs/MCP_INTEGRATION_CHECKLIST.md` | Platform engineers building MCP servers |
| `docs/audit/E2E_AUDIT_2026-11.md` | Security / QA reviewers |
| `CONTRACT.md` | Contributors |
