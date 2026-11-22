# AgentEnhancements — Integration & Architecture

> This document supersedes the legacy `README.md` for **integration planning**.
> The audited project README (`README.md`) remains the canonical setup guide.
> Read this file when you need the full picture of **what is merged, how it is
> wired, and what remains to build**.

## 1. Project purpose

<!-- ae:counts:summary:begin -->

- **3,378 specialized skills/agents** from **8 skill sources**; 3,430 source
  records before name collisions are resolved.
- **40 catalog plugins** from **22 unique upstream repositories**
  (`integrated`: 1, `integrated-ready`: 39); 21 entries have vendored source.
- **41 MCP servers** (`built`: 11, `to-install`: 30); **10 bundled Python
  backends**, 9 enabled by default before host configuration.
- **8 built-in capabilities**; **16 default native skills**; 31 skills in the
  optional curated set.
- **3,467 registry entries** in total; **11 vendored projects** listed in the
  root license notice.

<!-- ae:counts:summary:end -->

Detailed source counts and status meanings: [generated
inventory](docs/CAPABILITY_COUNTS.md).

`AgentEnhancements` is a **single integration layer that catalogs plugin entries
and aggregates vendored skill sources** plus a setup pipeline that provisions
9 AI-agent CLIs (Claude Code, Codex CLI, Cursor, Gemini CLI,
GitHub Copilot CLI, Kiro, OpenCode, Windsurf, Hermes) from one source of truth.

The repo does **not** reinvent skills — it catalogs, normalizes, and installs
them.

## 2. Coverage check — were all the requested plugins included?

YES. **17 / 17** plugins from the merger request are present in
`plugin-catalog/catalog.json`, plus **4 additional** plugins discovered and
integrated during the audit, plus **19 agency packs** vendored from
`github.com/msitarzewski/agency-agents` (18 divisions + NEXUS orchestration
playbooks). Total: **40 plugins** across 6 categories (5 requested + `agency`).

- **#:** 1
  - **Category:** code
  - **Requested plugin:** Matt Pocock skills
  - **Catalog ID:** `code-mattpocock-skills`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/mattpocock/skills`

- **#:** 2
  - **Category:** code
  - **Requested plugin:** Karpathy skills
  - **Catalog ID:** `code-karpathy-skills`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/multica-ai/andrej-karpathy-skills`

- **#:** 3
  - **Category:** code
  - **Requested plugin:** Agent Skills (Addy Osmani)
  - **Catalog ID:** `code-agent-skills-addyosmani`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/addyosmani/agent-skills`

- **#:**
  - **Category:** code
  - **Requested plugin:** _+ Replica Skill (bonus)_
  - **Catalog ID:** `code-replica-skill`
  - **Availability notes:** **vendored**
  - **Source:** `github.com/Jakeschincariol/replica-skill`

- **#:** 4
  - **Category:** research
  - **Requested plugin:** Graphify
  - **Catalog ID:** `research-graphify`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/Graphify-Labs/graphify`

- **#:** 5
  - **Category:** research
  - **Requested plugin:** Agent-Reach
  - **Catalog ID:** `research-agent-reach`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/Panniantong/Agent-Reach`

- **#:** 6
  - **Category:** research
  - **Requested plugin:** Understand Anything
  - **Catalog ID:** `research-understand-anything`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/Egonex-AI/Understand-Anything`

- **#:** 7
  - **Category:** research
  - **Requested plugin:** Last 30 Days
  - **Catalog ID:** `research-last-30-days`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/mvanhorn/last30days-skill`

- **#:** 8
  - **Category:** research
  - **Requested plugin:** REA
  - **Catalog ID:** `research-rea`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/morluto/rea`

- **#:** 9
  - **Category:** tokens
  - **Requested plugin:** GStack
  - **Catalog ID:** `tokens-gstack`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/garrytan/gstack`

- **#:** 10
  - **Category:** tokens
  - **Requested plugin:** Caveman
  - **Catalog ID:** `tokens-caveman`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/JuliusBrussee/Caveman`

- **#:** 11
  - **Category:** tokens
  - **Requested plugin:** GSD
  - **Catalog ID:** `tokens-gsd`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/gsd-build/get-shit-done`

- **#:** 12
  - **Category:** tokens
  - **Requested plugin:** BMAD Method
  - **Catalog ID:** `tokens-bmad-method`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/bmad-code-org/BMAD-METHOD`

- **#:** 13
  - **Category:** design
  - **Requested plugin:** UI UX Pro Max
  - **Catalog ID:** `design-ui-ux-pro-max`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/nextlevelbuilder/ui-ux-pro-max-skill`

- **#:** 14
  - **Category:** design
  - **Requested plugin:** Impeccable
  - **Catalog ID:** `design-impeccable`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/pbakaus/impeccable`

- **#:** 15
  - **Category:** design
  - **Requested plugin:** PPT Master
  - **Catalog ID:** `design-ppt-master`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/hugohe3/ppt-master`

- **#:** 16
  - **Category:** design
  - **Requested plugin:** Diagram Design
  - **Catalog ID:** `design-diagram-design`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/cathrynlavery/diagram-design`

- **#:** 17
  - **Category:** multimedia
  - **Requested plugin:** Skills by Anthropic
  - **Catalog ID:** `multimedia-anthropic-skills`
  - **Availability notes:** **vendored** (19 sub-skills)
  - **Source:** `github.com/anthropics/skills`

- **#:** 18
  - **Category:** multimedia
  - **Requested plugin:** OpenMontage
  - **Catalog ID:** `multimedia-openmontage`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/calesthio/OpenMontage`

- **#:** 19
  - **Category:** multimedia
  - **Requested plugin:** Hyperframes
  - **Catalog ID:** `multimedia-hyperframes`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/heygen-com/hyperframes`

- **#:** 20
  - **Category:** multimedia
  - **Requested plugin:** Humanizer
  - **Catalog ID:** `multimedia-humanizer`
  - **Availability notes:** integrated-ready
  - **Source:** `github.com/blader/humanizer`

- **#:** 21
  - **Category:** agency
  - **Requested plugin:** The Agency division packs (18)
  - **Catalog ID:** `agency-<division>`
  - **Availability notes:** **vendored**
  - **Source:** `github.com/msitarzewski/agency-agents`

- **#:** 22
  - **Category:** agency
  - **Requested plugin:** NEXUS orchestration playbooks
  - **Catalog ID:** `agency-nexus`
  - **Availability notes:** **vendored**
  - **Source:** `github.com/msitarzewski/agency-agents`

### Status legend

- `vendored` — upstream source code copied into the repo (works offline, frozen
  at vendored commit).
- `integrated-ready` — `manifest.json` + `SKILL.md` guide exist; the upstream
  runtime and dependencies must be installed separately by the user. Setup does
  not fetch these upstreams.

> Source-URL divergences from the original request (typo or upstream rename)
> were normalized during the audit; canonical URLs are stored in
> `plugin-catalog/catalog.json` → `source_url`.

## 3. Repository architecture

```text
AgentEnhancements/
├── README.md                           # audited setup guide (canonical)
├── README_INTEGRATION.md               # this file (integration narrative)
├── .cursorrules                        # centralized system prompt (Karpathy +
# Anthropic best practices)
├── CONTRACT.md                         # contribution contract (§12.3 commit
# format)
│
├── skills/                             # ← modular tree (NEW)
│   ├── manifest.json                   # aggregator index (40 plugins)
│   ├── README.md                       # tree architecture
│   ├── code/{4 plugins}/               # each has SKILL.md + manifest.json
│   ├── research/{5 plugins}/
│   ├── tokens-optimization/{4 plugins}/
│   ├── design/{4 plugins}/
│   ├── multimedia-writing/{4 plugins}/
│   └── agency/{19 packs}/
│
├── plugin-catalog/                     # canonical catalog + per-plugin
# manifests
│   ├── catalog.json                    # 40 plugins, 6 categories, upstream
│ # URLs
│   ├── mcp-servers.json                # 41 MCP servers, P0/P1/P2 priority
│   ├── code/, research/, ...           # original SKILL.md + manifest sources
│   └── README.md
│
├── unified-integration/                # installation pipeline
│   ├── setup.sh                        # installer (9 agent CLIs)
│   ├── update-skills.sh                # registry re-builder
│   ├── mcp-servers/                    # 10 in-house MCP servers + installer
│ # template
│   ├── scripts/setup-mcp.sh            # shared native MCP configuration
│ # installer
│   ├── skills/
│   │   ├── all-skills.json             # 3,378 skills aggregated registry
│   │   ├── agent-registry.json         # capability registry (skills +
│   │   │                               # plugins + MCP + built-ins)
│   │   ├── by-category/                # 10 functional categories
│   │   └── by-agent/                   # per-agent file lists
│   ├── prompts/                        # 10 system-prompt variants
│   │   ├── universal-system-prompt.txt
│   │   ├── claude-code-system-prompt.txt
│   │   ├── codex-system-prompt.txt
│   │   └── ... (7 more)
│   ├── memory/hooks/                   # per-agent memory hooks (9 agents
│   │                                   # × .py + .sh)
│   ├── memory/, compression/           # cross-session state
│   ├── scripts/                        # shared utility scripts
│   └── tests/                          # integration regression modules
│
├── vendored upstream projects (frozen)
│   ├── anthropic-skills/               # github.com/anthropics/skills (19
│ # sub-skills)
│   ├── replica-skill/                  # github.com/Jakeschincariol/replica-skill
│ # (11 sub-skills)
│   ├── agency-agents/                  # github.com/msitarzewski/agency-agents
│ # (283 personas)
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
│   └── generate_skills_index.py        # regenerate skills/manifest.json +
│ # READMEs
│
└── .github/workflows/                  # CI (tests + skill-index freshness)
```

### 3.1 The three layers

The catalog and vendored skill bundles are parallel sources:

1. **Catalog layer** (`plugin-catalog/`) describes plugin guides, upstream
   locations and candidate MCP servers. `scaffold_modular_skills.sh` and
   `generate_skills_index.py` derive the modular guide tree in `skills/`.
2. **Skill aggregation** scans vendored bundles through
   `setup.sh aggregate_skills()` and derives `all-skills.json` plus the
   installed `by-category/` and `by-agent/` copies.
3. **Capability registry** combines that skills index with the catalog,
   MCP manifest and built-in descriptors. The L0 map and native agent
   instructions point to this registry for bounded discovery.

The modular guide tree is not a source for skill aggregation. Edit canonical
vendor/catalog inputs, then regenerate their dependent artifacts.

### 3.2 The 40 plugins, by category

#### Code (`skills/code/`)

- **Plugin:** `mattpocock-skills`
  - **Purpose:** TypeScript rigor: type narrowing, generics, Zod schema-first,
    refactor patterns
  - **MCP servers needed:** typescript-language-server, eslint-mcp

- **Plugin:** `karpathy-skills`
  - **Purpose:** Minimal-first ML / numerical: first-principles derivation,
    ≤30-line implementations, no-over-engineering review
  - **MCP servers needed:** jupyter-mcp, python-repl-mcp

- **Plugin:** `agent-skills-addyosmani`
  - **Purpose:** Frontend performance: Core Web Vitals, Lighthouse automation,
    a11y audits
  - **MCP servers needed:** browser-tools-mcp, lighthouse-mcp, pa11y-mcp

- **Plugin:** `replica-skill`
  - **Purpose:** Reverse-engineer / clone a web app into a fresh codebase (11
    sub-skills, vendored)
  - **MCP servers needed:** browser-tools-mcp, vision-mcp

#### Research (`skills/research/`)

- **Plugin:** `graphify`
  - **Purpose:** Extract entities + relations from unstructured text → knowledge
    graph
  - **MCP servers needed:** neo4j-mcp, graphrag-mcp, embeddings-mcp

- **Plugin:** `agent-reach`
  - **Purpose:** Deep multi-source research with citation tracking
  - **MCP servers needed:** tavily-mcp, exa-mcp, firecrawl-mcp

- **Plugin:** `understand-anything`
  - **Purpose:** Feynman-style concept explanation for onboarding
  - **MCP servers needed:** wikipedia-mcp, arxiv-mcp, embeddings-mcp

- **Plugin:** `last-30-days`
  - **Purpose:** Fresh-trend monitoring (last 30 days of news / releases)
  - **MCP servers needed:** exa-mcp, newsapi-mcp, google-news-mcp

- **Plugin:** `rea`
  - **Purpose:** Reverse Engineer Anything — analyze how apps/binaries work
    (upstream `morluto/rea` MCP server, install separately)
  - **MCP servers needed:** rea MCP server (upstream)

#### Tokens / Optimization (`skills/tokens-optimization/`)

- **Plugin:** `gstack`
  - **Purpose:** Token budgeting, cache strategy, context compression
  - **MCP servers needed:** —

- **Plugin:** `caveman`
  - **Purpose:** Aggressive shorthand compression for token reduction
  - **MCP servers needed:** —

- **Plugin:** `gsd`
  - **Purpose:** Atomic parallel checklist execution (Get Shit Done)
  - **MCP servers needed:** task-router-mcp, memory-mcp

- **Plugin:** `bmad-method`
  - **Purpose:** Multi-persona agile (PM/SM/Dev/Architect) build orchestrator
  - **MCP servers needed:** linear-mcp, github-issues-mcp, memory-mcp

#### Design (`skills/design/`)

- **Plugin:** `ui-ux-pro-max`
  - **Purpose:** Design-token extraction, color/spacing systems, component audit
  - **MCP servers needed:** figma-mcp, browser-tools-mcp, storybook-mcp

- **Plugin:** `impeccable`
  - **Purpose:** Visual polish: alignment, contrast, hierarchy, anti-AI-ism
    design
  - **MCP servers needed:** browser-tools-mcp, figma-mcp

- **Plugin:** `ppt-master`
  - **Purpose:** Slide narrative + structure for technical decks
  - **MCP servers needed:** google-slides-mcp, office-mcp, image-search-mcp

- **Plugin:** `diagram-design`
  - **Purpose:** Mermaid / D2 / Excalidraw diagram authoring
  - **MCP servers needed:** mermaid-mcp, excalidraw-mcp

#### Multimedia / Writing (`skills/multimedia-writing/`)

- **Plugin:** `anthropic-skills`
  - **Purpose:** Office docs (.docx/.pdf/.pptx/.xlsx), MCP server authoring,
    skill creator, webapp testing — **19 sub-skills vendored**
  - **MCP servers needed:** filesystem-mcp, pdf-mcp, vision-mcp

- **Plugin:** `openmontage`
  - **Purpose:** Non-linear video editing via ffmpeg for shorts / montages
  - **MCP servers needed:** ffmpeg-mcp, video-mcp

- **Plugin:** `hyperframes`
  - **Purpose:** Personalized talking-head video (consent-gated)
  - **MCP servers needed:** heygen-mcp, elevenlabs-mcp

- **Plugin:** `humanizer`
  - **Purpose:** Remove AI-isms from generated text, naturalize tone
  - **MCP servers needed:** style-mcp, grammar-mcp

#### Agency Personas (`skills/agency/`)

Vendored from `github.com/msitarzewski/agency-agents` (MIT). The 19 packs are
`academic`, `design`, `engineering`, `finance`, `game-development`, `gis`,
`healthcare`, `marketing`, `paid-media`, `product`, `project-management`,
`research`, `sales`, `security`, `spatial-computing`, `specialized`,
`support`, `testing`, and `nexus`. 283 personas are
converted to Agent Skills format (`agency-agents/skills/<division>/<slug>/`)
by `scripts/convert_agency_agents.py` and aggregated into the unified index
under the `agency-agents` source (skill names prefixed `agency-`). Persona
packs need no MCP servers — they are behavioral guidance, not tooling.

| Pack | Personas | Pack | Personas |
| ------ | ---------- | ------ | ---------- |
| engineering | 66 | specialized | 59 |
| marketing | 37 | game-development | 21 |
| security | 12 | gis | 13 |
| design | 10 | sales | 9 |
| testing | 9 | paid-media | 7 |
| project-management | 7 | product | 6 |
| academic | 6 | spatial-computing | 6 |
| support | 6 | finance | 5 |
| healthcare | 3 | research | 1 |
| nexus (playbooks) | 12 docs | | |

### 3.3 Orchestrators

Three plugins double as **cross-cutting orchestrators** (declared in
`catalog.json:orchestrators`):

| Slug | Role | Best for |
| ------ | ------ | ---------- |
| `bmad-method` | build | greenfield multi-persona projects |
| `gsd` | execute | atomic checklist, parallel sub-agents |
| `rea` | research | hypothesis-driven multi-step investigation |

### 3.4 Vendored upstream projects (frozen copies)

In addition to the 40 cataloged plugins, the upstream projects listed in the
root license notice are
vendored into the repo root (their source code, not just manifests):

- **Project:** `anthropic-skills/`
  - **Origin:** github.com/anthropics/skills
  - **Why vendored:** Multi-skill bundle, 19 sub-skills

- **Project:** `replica-skill/`
  - **Origin:** github.com/Jakeschincariol/replica-skill
  - **Why vendored:** Multi-skill bundle, 11 sub-skills

- **Project:** `agency-agents/`
  - **Origin:** github.com/msitarzewski/agency-agents
  - **Why vendored:** 283 persona skills + NEXUS playbooks

- **Project:** `agentic-awesome-skills/`
  - **Origin:** awesome-list fork
  - **Why vendored:** Curated skill index, used as discovery source

- **Project:** `claude-mem/`
  - **Origin:** github.com/thedotmack/claude-mem
  - **Why vendored:** Cross-session memory hooks

- **Project:** `headroom/`
  - **Origin:** github.com/headroomlabs-ai/headroom
  - **Why vendored:** Context-window optimization primitives

- **Project:** `ponytail/`
  - **Origin:** github.com/DietrichGebert/ponytail
  - **Why vendored:** Skills framework + hooks (MIT)

- **Project:** `superpowers/`
  - **Origin:** github.com/obra/superpowers
  - **Why vendored:** Developer productivity skills (MIT)

- **Project:** `system-prompts-and-models-of-ai-tools/`
  - **Origin:** github.com/x1xhlol/system-prompts-and-models-of-ai-tools
  - **Why vendored:** Reference prompts (GPL-3.0)

- **Project:** `ECC/`
  - **Origin:** github.com/affaan-m/ECC
  - **Why vendored:** Enhanced Claude Code configuration (MIT)

- **Project:** `task-observer/`
  - **Origin:** github.com/rebelytics/one-skill-to-rule-them-all
  - **Why vendored:** Ambient skill observation (CC-BY-4.0, pinned)

The [generated source table](docs/CAPABILITY_COUNTS.md) distinguishes raw
records from unique indexed skills. Skill sources feed `setup.sh` directly;
plugin guides form a separate catalog surface.

## 4. The setup pipeline

```text
┌────────────────────────────────────────────────────────────────────┐
│ plugin-catalog/catalog.json                                        │
│   ↓ (scripts/scaffold_modular_skills.sh + generate_skills_index.py)│
│ skills/<cat>/<slug>/SKILL.md + manifest.json  (guide tree; not     │
│                                                aggregated)         │
│                                                                    │
│ vendored upstream skill bundles                                    │
│   ↓ (setup.sh aggregate_skills(); update-skills.sh pulls the       │
│      vendored repos, then runs setup.sh)                           │
│ unified-integration/skills/all-skills.json  (3,378 skills)         │
│   ↓ (registry.py build: + catalog, MCP manifest, built-ins)        │
│ unified-integration/skills/agent-registry.json                     │
│   ↓ (setup.sh, per-agent dispatch)                                 │
│ ~/.claude/CLAUDE.md      ~/.codex/AGENTS.md      ~/.cursor/...     │
│ ~/.config/opencode/...  ~/.gemini/...           ~/.kiro/...       │
│ selected Hermes profiles and reference/rule files                │
└────────────────────────────────────────────────────────────────────┘
```

`setup.sh` is **idempotent** (verified end-to-end in the audit) — re-running
it merges rather than overwrites user customizations (post-H-1 audit fix).

## 5. Quality posture

- The integration regression suite includes opt-in network/model tests and
  native CLI fixtures. Totals change with the suite; consult the dated
  [verification report](docs/audit/NATIVE_HOSTS_E2E_2026-11-16.md).
- **Adaptive preflight** (capability selection before the main agent's first
  inference): dedicated regression tests cover the `ui.api.json` preflight
  contract,
  Mode 0 byte-parity, zero-egress proofs, exact-ID resolution and a full
  Mode 2 round against a local TLS fixture — see
  [docs/ADAPTIVE_PREFLIGHT.md](docs/ADAPTIVE_PREFLIGHT.md).
- **Static checks**: `bash -n`, `py_compile`, JSON schema validation —
  enforced in CI.
- **End-to-end setup** verified against 8 stub agent CLIs in an isolated
  HOME (42-second cold run, exit 0).
- Secret-scan evidence is scoped to the dated audit and revision that produced
  it.
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
ls ~/.codex/ ~/.cursor/ ~/.config/opencode/ 2>/dev/null
```

For setup and native host selection, see [README.md](README.md) and [the agent
guide](docs/AGENTS.md). `setup.sh` has no dry-run or no-vendored CLI options.

## 7. What's next — the merger backlog

See **`docs/MCP_INTEGRATION_CHECKLIST.md`** for the step-by-step plan to
finish the merger. Summary:

- The generated inventory distinguishes MCP implementation status, bundled
  backends and default enablement. Runtime readiness is checked separately.
- External MCPs need installed executables, account authorization and central
  credential references. Suggested package commands remain roadmap data.
- `setup-mcp.sh --check` and the offline MCP regression module verify bundled
  protocol behavior; optional live tests require deliberate opt-in.

## 8. Related documents

- **Document:** `README.md`
  - **Audience:** Setup & daily users

- **Document:** `README_INTEGRATION.md` (this file)
  - **Audience:** Architects & integrators

- **Document:** `.cursorrules`
  - **Audience:** Cursor / Claude Code / any agent reading system prompts

- **Document:** `skills/README.md`
  - **Audience:** Plugin authors

- **Document:** `docs/MCP_INTEGRATION_CHECKLIST.md`
  - **Audience:** Platform engineers building MCP servers

- **Document:** `docs/ADAPTIVE_PREFLIGHT.md`
  - **Audience:** Architects wiring capability-selection preflight

- **Document:** `docs/CONFIGURATION.md`
  - **Audience:** Operators managing credentials and env vars

- **Document:** `docs/audit/E2E_AUDIT_2026-11.md`
  - **Audience:** Security / QA reviewers

- **Document:** `CONTRACT.md`
  - **Audience:** Contributors
