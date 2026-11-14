# AgentEnhancements

A unified integration platform that aggregates essential AI agent skills, tools, and configurations from multiple open-source projects into a single, cohesive developer experience. This project eliminates the need to install and configure each component individually.

## Overview

AgentEnhancements brings together 8 complementary projects (plus a plugin catalog and two vendored skill suites) that enhance AI coding agents (Claude Code, Codex, OpenCode, Cursor, Gemini CLI, Copilot, Windsurf, Kiro) with:

- **3,094 specialized skills/agents** in the unified index (see `unified-integration/skills/all-skills.json` for the live count), including the **19 official Anthropic skills** (docx, pdf, pptx, xlsx, skill-creator, mcp-builder, webapp-testing, claude-api, ...)
- **Capability registry** mapping every skill, catalog plugin and MCP server in one queryable index (`registry.py map "<task>"`)
- **Native runtime activation**: one install links a curated skill set into `~/.claude/skills/` and `~/.agents/skills/`, so Agent Skills compatible harnesses discover them automatically
- **Plugin catalog** with 21 curated external plugin sources (code, research, tokens, design, multimedia)
- **Context compression & memory management** for long-running sessions
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

### Plugin Catalog (21 external sources)

The `plugin-catalog/` directory documents 21 curated external plugin sources with manifests, integration guides (SKILL.md), and an MCP server roadmap. See `docs/QUICKSTART.md` for a 5-minute tour.

| Category | Plugins |
|----------|---------|
| **code** (4) | [Matt Pocock Skills](https://github.com/mattpocock/skills), [Karpathy Skills](https://github.com/multica-ai/andrej-karpathy-skills), [Agent Skills (Addy Osmani)](https://github.com/addyosmani/agent-skills), Replica Skill |
| **research** (5) | [Graphify](https://github.com/Graphify-Labs/graphify), [Agent-Reach](https://github.com/Panniantong/Agent-Reach), [Understand Anything](https://github.com/Egonex-AI/Understand-Anything), [Last 30 Days](https://github.com/mvanhorn/last30days-skill), [REA](https://github.com/morluto/rea) |
| **tokens-optimization** (4) | [GStack](https://github.com/garrytan/gstack), [Caveman](https://github.com/JuliusBrussee/Caveman), [GSD (Get Shit Done)](https://github.com/gsd-build/get-shit-done), [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) |
| **design** (4) | [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill), [Impeccable](https://github.com/pbakaus/impeccable), [PPT Master](https://github.com/hugohe3/ppt-master), [Diagram Design](https://github.com/cathrynlavery/diagram-design) |
| **multimedia-writing** (4) | [Anthropic Skills](https://github.com/anthropics/skills), [OpenMontage](https://github.com/calesthio/OpenMontage), [Hyperframes](https://github.com/heygen-com/hyperframes), [Humanizer](https://github.com/blader/humanizer) |

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
1. Detect your installed AI coding assistants (Claude Code, Codex, OpenCode, Cursor, Gemini CLI, Windsurf, Copilot, Kiro)
2. Aggregate skills from all sources into the unified registry (3,094 skills from 6 sources, official Anthropic copies winning name collisions) and regenerate `all-skills.json`
3. Build the capability registry (`agent-registry.json`: skills + 21 plugins + 38 MCP servers + built-ins)
4. Configure system prompts for each detected tool from the vendored prompt collection
5. Set up memory persistence (parameterized-SQL Python hooks)
6. Enable context compression (headroom binary if available, pure-Python fallback otherwise)
7. Configure Claude Code hooks for automatic memory save, and write activation files for every other agent
8. Link the curated skill set (anthropic-skills + replica-skill) into `~/.claude/skills/` and `~/.agents/skills/` for native runtime auto-discovery

Re-run `setup.sh` any time; it is idempotent (non-destructive config merges, marker-guarded instruction files).

---

## Agent Activation Matrix

What gets configured per agent when `setup.sh` detects it:

| Agent | Activation file(s) written by setup | What activates |
|-------|--------------------------------------|----------------|
| **Claude Code** | `~/.claude/settings.json` (merged, credentials preserved) + `~/.claude/CLAUDE.md` + links in `~/.claude/skills/` | Hooks fire automatically on every tool use / session stop; curated skills natively auto-discovered |
| **Codex** | `~/.codex/AGENTS.md` | Global instructions: skills catalog usage, memory and compression commands. Codex reads AGENTS.md at session start |
| **OpenCode** | `~/.config/opencode/opencode.json` (schema-valid) + `~/.config/opencode/AGENTS.md` | Native skills discovery via the `skills` array (points at the aggregated registry) + instruction files via `instructions` |
| **Cursor** | `~/.cursor/rules/agent-enhancements.mdc` | Global rule (frontmatter-scoped) with catalog, memory and compression usage |
| **Gemini CLI** | `~/.gemini/GEMINI.md` + `~/.gemini/config.yaml` (reference) | Global hierarchical context file loaded at session start |
| **Windsurf** | `~/.codeium/windsurf/rules/agent-enhancements.md` | Global rule with catalog, memory and compression usage |
| **GitHub Copilot** | `~/.config/github-copilot/config.yaml` (reference) | Reference configuration; use via the launcher |
| **Kiro** | `~/.kiro/config.yaml` (reference) | Reference configuration; use via the launcher |
| **All Agent Skills harnesses** | links in `~/.agents/skills/` (cross-agent standard) | Curated set (anthropic-skills 19 + replica-skill 11) auto-discovered at runtime |

Notes:
- Marker-guarded files (`<!-- agent-enhancements:begin/end -->`) preserve your personal instructions across re-runs.
- Claude Code is the only agent with an automatic hook system; for all others, the written instructions tell the agent how to invoke memory/compression explicitly.
- Extend the natively linked set any time: `bash unified-integration/scripts/link-skills.sh --set superpowers`, `link-skills.sh <skill-name>`, or `--set all` for the entire catalog (`--status` / `--unlink` to inspect or remove; user-owned entries are never touched).

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
│   └── tests/                     # Regression test suite (149 tests)
│
├── skills/                        # Modular plugin tree (5 categories, 21 plugins)
│   ├── manifest.json              # Aggregator index (committed)
│   ├── README.md                  # Tree architecture + coverage
│   ├── code/                      # 4 plugins: TS rigor, minimal ML, perf, replica
│   ├── research/                  # 5 plugins: graph, deep research, explain, trends, reasoning
│   ├── tokens-optimization/       # 4 plugins: budget, compress, atomic exec, personas
│   ├── design/                    # 4 plugins: tokens, polish, slides, diagrams
│   └── multimedia-writing/        # 4 plugins: docs, video, avatars, humanize
│                                  # (per-plugin dirs are generated: bash scripts/scaffold_modular_skills.sh)
├── plugin-catalog/                # 21 curated external plugin sources (canonical manifests)
├── scripts/                       # Repo-level generators (scaffold_modular_skills.sh,
│                                  #  generate_skills_index.py)
├── docs/MCP_INTEGRATION_CHECKLIST.md  # Step-by-step MCP server build plan (38 servers)
├── docs/ENV_VARS.md              # Every API key / env var: source + rotation policy
├── anthropic-skills/              # 19 official Anthropic skills (vendored, Apache-2.0)
├── replica-skill/                 # 11 vendored app-cloning sub-skills
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

The unified index (`unified-integration/skills/all-skills.json`) currently contains **3,094 unique skills** aggregated from 6 sources (the index is keyed by name; the official anthropic-skills version wins collisions with third-party copies):

| Source | Skills |
|--------|--------|
| agentic-awesome-skills | 2,729 |
| ECC | 314 |
| Superpowers | 15 |
| replica-skill | 11 |
| anthropic-skills (official) | 19 |
| Ponytail | 6 |

The on-disk registry (`skills/by-category/`, `skills/by-agent/`) is generated when you run `setup.sh`.

### Modular plugin tree (`skills/`)

The 21 cataloged plugins are exposed as a self-contained modular tree at `skills/<category>/<slug>/` (each dir holds `SKILL.md` + `manifest.json`). The tree is generated from `plugin-catalog/catalog.json` - never edited by hand:

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

Scoring understands format families ("word" -> docx, "excel" -> xlsx, "powerpoint" -> pptx) and stop words in English and Indonesian, so `map "buat dokumen word laporan keuangan"` returns the official `docx` skill first. The registry (`skills/agent-registry.json`) is rebuilt by `setup.sh` and covers 3,094 skills + 21 plugins + 38 MCP servers + 7 built-in capabilities.

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

# Claude Code: automatic
# Hooks in ~/.claude/settings.json save tool events and session summaries
# without any manual action.
```

Memory is stored in `~/.agent-memory/memory.db` (override with `AGENT_MEMORY_ROOT`). TTL-based cleanup runs on every save.

---

## Context Compression (headroom)

Automatic token budget management for long conversations:

- **Budget**: 200,000 tokens
- **Trigger**: 75% utilization (150k tokens)
- **Compression**: Summarizes old context, preserves recent + critical info
- **Fallback**: pure-Python/stream compression when the Rust binary is not built
- **Proxy Mode**: Works as transparent proxy for any AI API

```bash
# Compress a transcript
unified-integration/compression/compress.sh session.log auto

# Build headroom from source (optional; setup falls back gracefully)
cd headroom && cargo build --release

# Start headroom proxy
headroom proxy --port 8080 --target https://api.anthropic.com

# Use with any client
export ANTHROPIC_BASE_URL=http://localhost:8080
```

---

## System Prompts

Prompt files in `unified-integration/prompts/` are refreshed from the vendored collection at setup time when a source exists:

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

### Claude Code hooks (merged into `~/.claude/settings.json`)

```json
{
  "hooks": {
    "PreToolUse":  [{ "matcher": "*", "hooks": [{ "type": "command", "command": "<repo>/unified-integration/memory/hooks/claude-code-memory-hook.py save \"pre_tool_use:${TOOL_NAME}\" \"${TOOL_INPUT}\" session_context" }] }],
    "PostToolUse": [{ "matcher": "*", "hooks": [{ "type": "command", "command": "<repo>/unified-integration/memory/hooks/claude-code-memory-hook.py save \"post_tool_use:${TOOL_NAME}\" \"${TOOL_RESULT}\" session_context" }] }],
    "Stop":        [{ "hooks": [{ "type": "command", "command": "<repo>/unified-integration/memory/hooks/claude-code-memory-hook.py save \"session_summary\" \"${SESSION_SUMMARY}\" session_context" }] }]
  }
}
```

All other agent configurations are written in each tool's native format — see the [Agent Activation Matrix](#agent-activation-matrix) above and `docs/CONFIGURATION.md`.

---

## MCP Servers

`plugin-catalog/mcp-servers.json` is a **roadmap** of 38 candidate MCP servers (P0-P2), not a pre-wired configuration. To enable a server, add it to your tool's MCP config (e.g. `.claude/mcp.json` for Claude Code) using the command documented in the roadmap entry, then verify with:

```bash
bash unified-integration/scripts/mcp-test.sh --priority P0
```

---

## Testing & Validation

```bash
# Integration-layer regression suite (149 tests)
python3 unified-integration/tests/run-tests.py

# Plugin catalog validation (21 manifests)
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

| Project | Repository | License |
|---------|------------|---------|
| agentic-awesome-skills | [Original Repo](https://github.com/agentic-awesome/agentic-awesome-skills) | MIT |
| anthropic-skills | [Original Repo](https://github.com/anthropics/skills) | Apache-2.0 (per-skill LICENSE.txt) |
| claude-mem | [Original Repo](https://github.com/claude-mem/claude-mem) | MIT |
| ECC | [Original Repo](https://github.com/ecc-project/ecc) | MIT |
| headroom | [Original Repo](https://github.com/headroom/headroom) | MIT/Apache-2.0 |
| ponytail | [Original Repo](https://github.com/ponytail/ponytail) | MIT |
| superpowers | [Original Repo](https://github.com/superpowers/superpowers) | MIT |
| system-prompts-and-models-of-ai-tools | [Original Repo](https://github.com/system-prompts/system-prompts-and-models-of-ai-tools) | CC-BY-4.0 |
| replica-skill | [Original Repo](https://github.com/Jakeschincariol/replica-skill) | MIT |

> **Note**: This repository contains copies of the above projects for unified distribution. They are **not forks** — they are vendored dependencies. For changes to individual projects, please contribute upstream.

---

## License

This aggregation is released under **MIT License**. Individual projects retain their original licenses (see table above and `docs/LICENSE_AUDIT.md`).

---

## Support

- **Issues**: [GitHub Issues](https://github.com/lokah1945/AgentEnhancements/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lokah1945/AgentEnhancements/discussions)
- **Documentation**: See `docs/` folder and individual project READMEs

---

## Acknowledgments

Built on the incredible work of the open-source AI tooling community. Special thanks to the maintainers of all integrated projects for making their work available for composition.
