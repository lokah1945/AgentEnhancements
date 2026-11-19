# AgentEnhancements

A unified integration platform that aggregates essential AI agent skills, tools, and configurations from multiple open-source projects into a single, cohesive developer experience. This project eliminates the need to install and configure each component individually.

## Overview

AgentEnhancements brings together 9 complementary projects (plus a plugin catalog and three vendored skill suites) that enhance AI coding agents (Claude Code, Codex, OpenCode, Hermes, Cursor, Gemini CLI, Copilot, Windsurf, Kiro) with:

- **3,378 specialized skills/agents** in the unified index (see `unified-integration/skills/all-skills.json` for the live count), including the **19 official Anthropic skills** (docx, pdf, pptx, xlsx, skill-creator, mcp-builder, webapp-testing, claude-api, ...) and **283 AI personas from The Agency** (agency-agents), plus the pinned **task-observer** meta-skill (ambient skill-usage observation, [docs/TASK_OBSERVER.md](docs/TASK_OBSERVER.md))
- **Capability registry** mapping every skill, catalog plugin and MCP server in one queryable index (`registry.py map "<task>"`)
- **Native runtime activation**: one install links a curated skill set (task-observer + 15 Superpowers workflow skills) into `~/.claude/skills/`, `~/.codex/skills/`, `~/.config/opencode/skills/`, and `~/.agents/skills/`, so Agent Skills compatible harnesses discover them automatically
- **Full agent parity**: Claude Code, Codex, and OpenCode all receive equivalent integration — lifecycle hooks, native skill discovery, MCP gateway, memory persistence, and compression
- **Flexible skill discovery**: returns up to 8 relevant skill cards per prompt (configurable via `AE_MAX_SKILL_CARDS`); agents choose which to read/use from suggestions
- **Plugin catalog** with 40 curated external plugin entries from 22 unique upstream repositories (code, research, tokens, design, multimedia, and 19 The Agency division packs)
- **Context compression & memory management** for long-running sessions (headroom built by default, 99%+ fallback reduction)
- **System prompts** sourced from the vendored `system-prompts-and-models-of-ai-tools` collection
- **Unified configuration** that works across all major AI coding assistants

---

## Included Projects

| Project | Description | Key Features |
|---------|-------------|--------------|
| **[agentic-awesome-skills](./agentic-awesome-skills)** | Massive curated collection of AI agent skills | 2,781 skills, categorized by domain, auto-installable plugins |
| **[anthropic-skills](./anthropic-skills)** | Official Anthropic skills (vendored, Apache-2.0) | 19 skills: docx, pdf, pptx, xlsx, skill-creator, mcp-builder, webapp-testing, claude-api, design & comms |
| **[claude-mem](./claude-mem)** | Persistent memory layer for AI agents | Cross-session memory, automatic summarization, multi-agent support |
| **[ECC](./ECC)** | Enhanced Claude Code configuration | 314 skills, custom commands, hooks, MCP servers, dashboards |
| **[headroom](./headroom)** | Context compression & token budget management | Rust-based, 75% trigger, 200k budget, proxy server |
| **[ponytail](./ponytail)** | Skills framework & plugin system | Cross-platform skills, hook integration, multiple AI tool support |
| **[superpowers](./superpowers)** | Developer productivity skills collection | 15 skill categories, automated workflows, team sharing |
| **[system-prompts-and-models-of-ai-tools](./system-prompts-and-models-of-ai-tools)** | Reference system prompts from 25+ AI tools | Anthropic, Cursor, Windsurf, Copilot, Devin, and more |
| **[replica-skill](./replica-skill)** | 11 Claude skills that clone any app (clean-room) | recon, architect, design, build, backend, test, diff, entrepreneur, brand, launch, deploy |
| **[agency-agents](./agency-agents)** | The Agency: 283 AI specialist personas across 18 divisions (vendored, MIT) | engineering, design, security, testing, marketing, sales, finance, GIS, game-dev + NEXUS orchestration playbooks |

### Plugin Catalog (40 external sources)

The `plugin-catalog/` directory documents 40 curated external plugin sources with manifests, integration guides (SKILL.md), and an MCP server roadmap. See `docs/QUICKSTART.md` for a 5-minute tour.

| Category | Plugins |
|----------|---------|
| **code** (4) | [Matt Pocock Skills](https://github.com/mattpocock/skills), [Karpathy Skills](https://github.com/multica-ai/andrej-karpathy-skills), [Agent Skills (Addy Osmani)](https://github.com/addyosmani/agent-skills), Replica Skill |
| **research** (5) | [Graphify](https://github.com/Graphify-Labs/graphify), [Agent-Reach](https://github.com/Panniantong/Agent-Reach), [Understand Anything](https://github.com/Egonex-AI/Understand-Anything), [Last 30 Days](https://github.com/mvanhorn/last30days-skill), [REA](https://github.com/morluto/rea) |
| **tokens-optimization** (4) | [GStack](https://github.com/garrytan/gstack), [Caveman](https://github.com/JuliusBrussee/Caveman), [GSD (Get Shit Done)](https://github.com/gsd-build/get-shit-done), [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) |
| **design** (4) | [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill), [Impeccable](https://github.com/pbakaus/impeccable), [PPT Master](https://github.com/hugohe3/ppt-master), [Diagram Design](https://github.com/cathrynlavery/diagram-design) |
| **multimedia-writing** (4) | [Anthropic Skills](https://github.com/anthropics/skills), [OpenMontage](https://github.com/calesthio/OpenMontage), [Hyperframes](https://github.com/heygen-com/hyperframes), [Humanizer](https://github.com/blader/humanizer) |
| **agency** (19) | [The Agency](https://github.com/msitarzewski/agency-agents) division packs (vendored): academic, design, engineering, finance, game-development, gis, healthcare, marketing, paid-media, product, project-management, research, sales, security, spatial-computing, specialized, support, testing + NEXUS orchestration playbooks |

Catalog tooling: `catalog-validate.py` (validate), `catalog-wire.sh` (wire to registry), `catalog-test.sh` (smoke test), `dispatch.sh` (orchestrator routing), `mcp-test.sh` (MCP checks), `consent-gate.sh` + `audit-trail.sh` (safety). All in `unified-integration/scripts/`.

---

## Quick Start

### One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/lokah1945/AgentEnhancements/master/unified-integration/setup.sh | bash
```

> The one-liner runs `setup.sh` directly. For a reviewable install, use the manual method below.

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/lokah1945/AgentEnhancements.git
cd AgentEnhancements

# Run the unified setup
./unified-integration/setup.sh
```

The setup script will:
1. Detect your installed AI coding assistants (Claude Code, Codex, OpenCode, Hermes, Cursor, Gemini CLI, Windsurf, Copilot, Kiro), honoring a saved host selection
2. Aggregate skills from all sources into the unified registry (3,378 skills from 8 sources, official Anthropic copies winning name collisions) and regenerate `all-skills.json`
3. Build the capability registry (`agent-registry.json`: skills + 40 plugins + 38 MCP servers + built-ins)
4. Copy reference system-prompt files into `unified-integration/prompts/` (reference material — no agent is forced to load them; the written instruction files tell agents how to use the catalog)
5. Set up memory persistence (parameterized-SQL Python hooks, `memory_type="session_context"` enforced)
6. Enable context compression (headroom binary built by default; pure-Python fallback with 99%+ reduction for code/generic)
7. Configure **native lifecycle hooks for all detected agents** (Claude Code, Codex, OpenCode) — automatic memory save, skill card injection, session recall
8. Link **task-observer + 15 Superpowers workflow skills** into `~/.claude/skills/`, `~/.codex/skills/`, `~/.config/opencode/skills/`, and `~/.agents/skills/` for native discovery; search the full catalog on demand with flexible `max_results` (default 8, configurable via `AE_MAX_SKILL_CARDS`)

Re-run `setup.sh` any time; it is idempotent (non-destructive config merges, marker-guarded instruction files).

---

## Agent Activation Matrix

What gets configured per agent when `setup.sh` detects it:

| Agent | Activation file(s) written by setup | What activates |
|-------|--------------------------------------|----------------|
| **Claude Code** | `~/.claude/settings.json` (merged, credentials preserved) + `~/.claude/CLAUDE.md` + links in `~/.claude/skills/` | Hooks fire automatically on every tool use / session stop; 16 curated skills natively auto-discovered; flexible skill cards (default 8) |
| **Codex** | `~/.codex/AGENTS.md`, `hooks.json`, `config.toml` + `~/.codex/skills/` | Native lifecycle hooks (5/5 events), shared MCP gateway, bounded skill discovery; 16 curated skills natively auto-discovered |
| **OpenCode 2** | Existing `~/.config/opencode/opencode.jsonc` or `opencode.json`, plus `AGENTS.md` + `~/.config/opencode/skills/` | Native lifecycle plugin, shared MCP gateway, bounded skill discovery; 16 curated skills natively auto-discovered |
| **Hermes** | Selected profile `config.yaml`, `SOUL.md`, and native plugin link | Profile lifecycle hooks, shared MCP gateway and bounded skill discovery |
| **Cursor** | `~/.cursor/rules/agent-enhancements.mdc` | Global rule (frontmatter-scoped) with catalog, memory and compression usage |
| **Gemini CLI** | `~/.gemini/GEMINI.md` + `~/.gemini/config.yaml` (reference) | Global hierarchical context file loaded at session start |
| **Windsurf** | `~/.codeium/windsurf/rules/agent-enhancements.md` | Global rule with catalog, memory and compression usage |
| **GitHub Copilot** | `~/.config/github-copilot/config.yaml` (reference) | Reference configuration; use via the launcher |
| **Kiro** | `~/.kiro/config.yaml` (reference) | Reference configuration; use via the launcher |
| **All Agent Skills harnesses** | links in `~/.agents/skills/` (cross-agent standard) | Default workflow set: task-observer + 15 Superpowers skills |

Notes:
- Marker-guarded files (`<!-- agent-enhancements:begin/end -->`) preserve your personal instructions across re-runs.
- **Claude Code, Codex, and OpenCode 2 have full native lifecycle integration** — hooks, native skills, MCP gateway, memory, and compression. See [Agent guides](docs/AGENTS.md) for supported versions and verification.
- Extend the linked set with `link-skills.sh --set curated` or specific names. Use `registry.py search` for the full catalog; `--set all` exposes its metadata at every session start.
- Skill discovery is flexible: default 8 cards per prompt, configurable via `AE_MAX_SKILL_CARDS` env var; agents decide which skills to actually read/use.

### Launching an enhanced agent

```bash
./unified-integration/launch-agent.sh <agent> [args...]
# or, when /usr/local/bin is writable:
agent-enhanced <agent> [args...]
```

The launcher validates the agent against the last detection run, initializes memory, exports the standard environment variables and execs the agent.

---

## Architecture

```
AgentEnhancements/
├── README_INTEGRATION.md           # Integration & architecture guide (the merger narrative)
├── .cursorrules                    # Centralized system prompt (Karpathy + Anthropic best practices)
├── unified-integration/           # Main integration layer
│   ├── setup.sh                   # One-line installer (single source of truth)
│   ├── update-skills.sh           # Skill refresh from upstream sources
│   ├── launch-agent.sh            # Agent launcher with env config
│   ├── config/                    # Shared configurations
│   ├── prompts/                   # System prompts per AI tool
│   ├── skills/                    # Aggregated skills registry
│   │   ├── by-category/           # Skills organized by domain (generated at setup)
│   │   ├── by-agent/              # Skills organized by agent type (generated at setup)
│   │   ├── all-skills.json        # Complete skills catalog (committed index)
│   │   └── agent-registry.json    # Capability registry: skills + plugins + MCP + built-ins
│   ├── memory/                    # Memory integration (parameterized-SQL hooks)
│   ├── compression/               # Context compression (headroom + fallback)
│   ├── scripts/                   # Utility scripts (loader, memory, registry.py,
│   │                              # link-skills.sh, dispatch, setup-mcp.sh)
│   ├── mcp-servers/               # 9 in-house MCP servers (embeddings, task-router,
│   │                              # ffmpeg, vision, graphrag, arxiv, google-news,
│   │                              # video, style) + smoke_test + mcp.json template
│   └── tests/                     # Regression test suite (236 tests)
│
├── skills/                        # Modular plugin tree (6 categories, 40 plugins)
│   ├── manifest.json              # Aggregator index (committed)
│   ├── README.md                  # Tree architecture + coverage
│   ├── code/                      # 4 plugins: TS rigor, minimal ML, perf, replica
│   ├── research/                  # 5 plugins: graph, deep research, explain, trends, reasoning
│   ├── tokens-optimization/       # 4 plugins: budget, compress, atomic exec, personas
│   ├── design/                    # 4 plugins: tokens, polish, slides, diagrams
│   └── multimedia-writing/        # 4 plugins: docs, video, avatars, humanize
│                                  # (per-plugin dirs are generated: bash scripts/scaffold_modular_skills.sh)
├── plugin-catalog/                # 40 curated external plugin sources (canonical manifests)
├── scripts/                       # Repo-level generators (scaffold_modular_skills.sh,
│                                  #  generate_skills_index.py)
├── docs/MCP_INTEGRATION_CHECKLIST.md  # Step-by-step MCP server build plan (38 servers)
├── docs/ENV_VARS.md              # Every API key / env var: source + rotation policy
├── anthropic-skills/              # 19 official Anthropic skills (vendored, Apache-2.0)
├── replica-skill/                 # 11 vendored app-cloning sub-skills
├── task-observer/                 # vendored ambient skill-observation meta-skill (CC-BY-4.0, pinned; docs/TASK_OBSERVER.md)
├── agency-agents/                 # 283 The Agency personas (vendored, MIT) + NEXUS playbooks
├── agentic-awesome-skills/        # 2,781 vendored skills
├── claude-mem/                    # Memory persistence layer (vendored)
├── ECC/                           # Enhanced Claude Code config (vendored)
├── headroom/                      # Context compression (Rust, vendored)
├── ponytail/                      # Skills framework (vendored)
├── superpowers/                   # Productivity skills (vendored)
└── system-prompts-and-models-of-ai-tools/  # Reference prompts (vendored)
```

---

## Skills Catalog

The unified index (`unified-integration/skills/all-skills.json`) currently contains **3,378 unique skills** aggregated from 8 sources (the index is keyed by name; the official anthropic-skills version wins collisions with third-party copies):

| Source | Skills |
|--------|--------|
| agentic-awesome-skills | 2,729 |
| ECC | 314 |
| Superpowers | 15 |
| replica-skill | 11 |
| anthropic-skills (official) | 19 |
| Ponytail | 6 |
| agency-agents (The Agency personas) | 283 |

The on-disk registry (`skills/by-category/`, `skills/by-agent/`) is generated when you run `setup.sh`.

### Modular plugin tree (`skills/`)

The 40 cataloged plugins are exposed as a self-contained modular tree at `skills/<category>/<slug>/` (each dir holds `SKILL.md` + `manifest.json`). The per-plugin directories are **generated at install time** (symlinks into `plugin-catalog/`, gitignored); only `skills/manifest.json` and the READMEs are committed. The tree is generated from `plugin-catalog/catalog.json` - never edited by hand:

```bash
bash scripts/scaffold_modular_skills.sh     # build/rebuild the tree
python3 scripts/generate_skills_index.py    # refresh skills/manifest.json + READMEs
```

See `skills/README.md` for the tree architecture and `README_INTEGRATION.md` for the full integration narrative.

### Capability Registry (all-in-one mapping)

`unified-integration/scripts/registry.py` maps ANY task to everything the project ships - skills, catalog plugins, MCP servers and built-in capabilities - in one query:

```bash
# Activation plan for a task: matching skills (with paths), plugins,
# MCP servers, always-available capabilities and usage hints
python3 unified-integration/scripts/registry.py map "clean this excel spreadsheet"

# Focused search / details / stats
python3 unified-integration/scripts/registry.py search "pdf" --type skill
python3 unified-integration/scripts/registry.py show docx
python3 unified-integration/scripts/registry.py stats
```

Scoring understands format families ("word" -> docx, "excel" -> xlsx, "powerpoint" -> pptx) and stop words in English and Indonesian, so `map "buat dokumen word laporan keuangan"` returns the official `docx` skill first. The registry (`skills/agent-registry.json`) is rebuilt by `setup.sh` and covers 3,378 skills + 40 plugins + 38 MCP servers + 8 built-in capabilities.

### Using Skills

Find and load skills on demand (works from any agent):

```bash
# Map a task to skills + plugins + MCP servers (recommended first step)
python3 unified-integration/scripts/registry.py map "security audit"

# Find skills matching a task
python3 unified-integration/scripts/load-skills.py claude-code "security audit"

# Read a specific skill
cat unified-integration/skills/by-category/security/<skill-name>/SKILL.md
```

Agents configured above are instructed to do exactly this: search the catalog for the task at hand, then load and follow the matching SKILL.md.

Plugin catalog routing (natural-language dispatch to a catalog plugin):

```bash
bash unified-integration/scripts/dispatch.sh --dry-run "clone this app"
# Skill match : replica-skill
```

---

## Memory System

Persistent, cross-session memory backed by SQLite with parameterized queries:

```bash
# Save / load / list (any agent)
python3 unified-integration/scripts/memory.py claude-code save "prefers_typescript_strict" "yes" "user_preferences"
python3 unified-integration/scripts/memory.py claude-code load "prefers_typescript_strict"
python3 unified-integration/scripts/memory.py claude-code list

# All agents with native hooks (Claude Code, Codex, OpenCode): automatic
# Hooks save tool events and session summaries with `memory_type="session_context"`
# without any manual action.
```

Memory is stored in `~/.agent-memory/memory.db` (override with `AGENT_MEMORY_ROOT`). TTL-based cleanup runs on every save. All entries have valid `memory_type` (corrupt empty-type entries cleaned up automatically on setup).

---

## Context Compression (headroom)

**Headroom is now built by default** during `setup.sh` (opt-out with `AGENT_ENHANCEMENTS_BUILD_HEADROOM=0`).

- **Agents keep their native context management.** The instruction files written by setup tell each agent to use its CLI's built-in automatic context compaction.
- **Manual utility**: `unified-integration/compression/compress.sh` processes an individual transcript file on demand (mode selection, 50k-character truncation safety), with the vendored Rust `headroom` binary used when available and a pure-Python fallback otherwise.
- **Fallback compression improved**: 99%+ reduction for code and generic text (deduplication + whitespace normalization); JSON minification; log timestamp/ID normalization.
- `unified-integration/compression/config.yaml` (budget 200k, trigger 75%) is a **reference template** — no shipped code consumes it automatically today.
- **Proxy Mode**: if you build headroom from source you can run it as a transparent proxy for any AI API; AgentEnhancements does not enable or configure this for you.

```bash
# Compress a transcript manually
unified-integration/compression/compress.sh session.log auto

# Build headroom from source (optional, now default)
cd headroom && cargo build --release

# Start headroom proxy (manual, not configured by setup)
headroom proxy --port 8080 --target https://api.anthropic.com
```

---

## System Prompts

Prompt files in `unified-integration/prompts/` are **reference copies** refreshed from the vendored collection at setup time when a source exists. They are not injected into any agent automatically — the per-agent activation files (see the [Agent Activation Matrix](#agent-activation-matrix)) tell each agent how to discover skills, memory and compression on demand:

| Tool | Prompt File |
|------|-------------|
| Claude Code | `unified-integration/prompts/claude-code-system-prompt.txt` |
| Cursor | `unified-integration/prompts/cursor-system-prompt.txt` |
| Windsurf | `unified-integration/prompts/windsurf-system-prompt.txt` |
| GitHub Copilot | `unified-integration/prompts/copilot-system-prompt.txt` |
| Codex | `unified-integration/prompts/codex-system-prompt.txt` |
| Gemini CLI | `unified-integration/prompts/gemini-cli-system-prompt.txt` |
| Kiro | `unified-integration/prompts/kiro-system-prompt.txt` |
| OpenCode | `unified-integration/prompts/opencode-system-prompt.txt` |
| Universal | `unified-integration/prompts/universal-system-prompt.txt` |
| Consolidated (Karpathy + Anthropic + GSD) | `unified-integration/prompts/consolidated-system-prompt.txt` |

---

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AGENT_ENHANCEMENTS_BASE_DIR` | Project root | auto-detected from setup.sh location |
| `AGENT_MEMORY_ROOT` | Memory storage | `~/.agent-memory` |
| `AGENT_SKILLS_DIR` | Skills registry | `$BASE_DIR/unified-integration/skills` |
| `HEADROOM_BIN` | Compression binary | auto-detect (repo build, then PATH) |
| `AE_MAX_SKILL_CARDS` | Max skill cards per prompt | `8` (configurable, was 3) |
| `AGENT_ENHANCEMENTS_BUILD_HEADROOM` | Build headroom by default | `1` (set to `0` to skip) |

### Runtime Hooks (merged into each agent's native config)

All three primary agents (Claude Code, Codex, OpenCode) receive equivalent lifecycle hooks via `unified-integration/scripts/runtime.py`:

| Hook Event | Purpose |
|------------|---------|
| `SessionStart` | Task Observer bootstrap + session memory recall (7-day TTL) |
| `UserPromptSubmit` | Skill discovery — returns up to 8 relevant skill cards (configurable via `AE_MAX_SKILL_CARDS`) |
| `PreToolUse` | Record tool name for session memory |
| `PostToolUse` | Record tool name for session memory |
| `Stop` | Save session summary + Task Observer flush |

Hooks save with `memory_type="session_context"` — no corrupt entries.

All agent configurations are written in each tool's native format — see the [Agent Activation Matrix](#agent-activation-matrix) above and `docs/CONFIGURATION.md`.

---

## MCP Servers

`plugin-catalog/mcp-servers.json` is a **roadmap** of 40 candidate MCP servers (P0-P2), not a pre-wired configuration. To enable a server, add it to your tool's MCP config (e.g. `.claude/mcp.json` for Claude Code) using the command documented in the roadmap entry, then verify with:

```bash
bash unified-integration/scripts/mcp-test.sh --priority P0
```

---

## Testing & Validation

```bash
# Integration-layer regression suite (236 tests)
python3 unified-integration/tests/run-tests.py

# Plugin catalog validation (40 manifests)
python3 unified-integration/scripts/catalog-validate.py --root .

# Vendored ECC suite (contract-mandated)
cd ECC && node tests/run-all.js
```

CI runs all of the above on every push (`.github/workflows/ci.yml`).

---

## Contributing

This is an aggregation project. To contribute:

1. **Upstream projects**: Contribute to the original repositories
2. **Integration layer**: Improve `unified-integration/` scripts and configs
3. **Documentation**: Enhance this README and guides in `docs/`

All agents working on this repository must follow `CONTRACT.md` (conventional commits, agent traceability metadata, single source of truth rules).

### Referenced Projects (Upstream)

Vendored copies keep their own upstream licenses (see the root `LICENSE` notice and `docs/LICENSE_AUDIT.md`); the MIT grant covers only the integration layer authored in this repository.

| Project | Upstream repository | License |
|---------|---------------------|---------|
| agentic-awesome-skills | [sickn33/agentic-awesome-skills](https://github.com/sickn33/agentic-awesome-skills) | MIT (code) + CC-BY-4.0 (content, `LICENSE-CONTENT`) |
| anthropic-skills | [anthropics/skills](https://github.com/anthropics/skills) | Apache-2.0 (per-skill LICENSE.txt) |
| claude-mem | [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) | Apache-2.0 (+ NOTICE) |
| ECC | [affaan-m/ECC](https://github.com/affaan-m/ECC) | MIT |
| headroom | [headroomlabs-ai/headroom](https://github.com/headroomlabs-ai/headroom) | Apache-2.0 (+ NOTICE) |
| ponytail | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | MIT |
| superpowers | [obra/superpowers](https://github.com/obra/superpowers) | MIT |
| system-prompts-and-models-of-ai-tools | [x1xhlol/system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) | GPL-3.0 |
| replica-skill | [Jakeschincariol/replica-skill](https://github.com/Jakeschincariol/replica-skill) | MIT |
| agency-agents | [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) | MIT |
| task-observer | [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) | CC-BY-4.0 (pinned: `task-observer/VENDORED.json`) |

> **Note**: This repository contains vendored copies of the above projects for unified distribution. They are **not forks** — they are vendored dependencies. For changes to individual projects, please contribute upstream.

---

## License

The **integration layer authored in this repository** (unified-integration/, plugin-catalog/, scripts/, docs/) is released under the **MIT License** (see `LICENSE`). The vendored project directories keep their own upstream licenses — including Apache-2.0 (claude-mem, headroom, anthropic-skills), GPL-3.0 (system-prompts-and-models-of-ai-tools), and CC-BY-4.0 (task-observer, agentic-awesome-skills content) — which take precedence inside those directories. The full per-directory matrix lives in `docs/LICENSE_AUDIT.md`.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/lokah1945/AgentEnhancements/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lokah1945/AgentEnhancements/discussions)
- **Documentation**: See `docs/` folder and individual project READMEs

---

## Acknowledgments

Built on the incredible work of the open-source AI tooling community. Special thanks to the maintainers of all integrated projects for making their work available for composition.
