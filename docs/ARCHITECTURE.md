---
title: Architecture
version: 1.5
last_updated: 2026-11-15
audience: maintainers, contributors
---

# Architecture

## Overview

AgentEnhancements is an **aggregation platform**: it vendors eight open-source
projects and wires them together through a single integration layer so that
AI coding assistants (Claude Code, Codex, OpenCode, Cursor, Gemini CLI,
Windsurf, Copilot, Kiro) can share one skills registry, one capability
registry, one memory system and one compression layer. ONE install provides
everything; a curated skill set is additionally activated natively so
compatible harnesses discover it automatically at runtime.

```
AgentEnhancements/
├── unified-integration/     # OWNED integration layer (this repo's code)
│   ├── setup.sh             # single entry point / installer
│   ├── update-skills.sh     # refresh vendored sources (where they are git repos)
│   ├── launch-agent.sh      # universal launcher (env-aware, self-locating)
│   ├── config/              # machine state (detected-agents.sh, auto-generated)
│   ├── prompts/             # per-agent system prompts + universal prompt
│   ├── skills/              # unified registry
│   │   ├── all-skills.json  # UNIFIED SKILLS INDEX (schema below)
│   │   ├── agent-registry.json  # CAPABILITY REGISTRY (skills+plugins+MCP+capabilities)
│   │   ├── by-category/     # populated by setup.sh (10 canonical buckets)
│   │   └── by-agent/        # populated by setup.sh (8 canonical agents)
│   ├── memory/              # hooks + config for the memory system
│   ├── compression/         # headroom wrapper + config
│   ├── scripts/             # load-skills.py, memory.py, compress.py,
│   │                        # registry.py, link-skills.sh, dispatch.sh,
│   │                        # task-observer.py (observer host adapter),
│   │                        # catalog tooling (validate/wire/test/consent/audit)
│   └── tests/               # regression suite (python3 tests/run-tests.py)
├── agentic-awesome-skills/  # vendored (skills, primary source)
├── anthropic-skills/        # vendored (19 official Anthropic skills, Apache-2.0)
├── claude-mem/              # vendored
├── ECC/                     # vendored
├── headroom/                # vendored (Rust)
├── agency-agents/           # vendored (283 The Agency personas + NEXUS playbooks)
├── plugin-catalog/          # curated external plugin sources (40) + MCP roadmap
├── ponytail/                # vendored
├── replica-skill/           # vendored (11 app-cloning sub-skills)
├── task-observer/           # vendored (ambient skill-observation meta-skill, CC-BY-4.0, pinned)
├── superpowers/             # vendored
└── system-prompts-and-models-of-ai-tools/  # vendored (prompt sources)
```

## Automatic runtime

Claude Code and Codex pass native JSON events to `scripts/runtime.py`.
OpenCode 2 loads `opencode-plugin/index.js` and bridges its prompt/context/idle
hooks to the same runtime. Startup recalls notes, bootstraps the Task
Observer workspace and injects a bounded observer context (status, open
observations); prompt events suggest relevant skills; stop/idle events
persist summaries. No launcher or manual skill command
is needed. Native compaction remains under each CLI's control. The memory DB
and skill-index schemas are unchanged.

## Setup pipeline (`setup.sh`)

0. **prepare runtime** - create an isolated Python environment and install
   declared dependencies; no global pip installation.
1. **detect_agents** - probes PATH for known agent CLIs; writes
   `config/detected-agents.sh` (machine-specific, never hand-edited).
2. **setup_prompts** - copies per-agent prompt files from
   `system-prompts-and-models-of-ai-tools/` into `prompts/` (bash globstar
   is required for the recursive globs) and writes the universal prompt.
3. **aggregate_skills** - walks `skills/` of the eight skill sources (agency-agents is division-nested, so each division directory is scanned in turn; task-observer is a root-layout source whose SKILL.md sits at the source root and is aggregated as a single skill), parses
   SKILL.md frontmatter (re-parsed from file so YAML block scalars become
   real descriptions), copies each skill directory into `by-category/`
   and `by-agent/` (idempotently: targets are removed before copy), and
   rebuilds `all-skills.json` in a single pass, keyed by skill name (later
   sources win collisions; anthropic-skills runs last). Skill metadata is
   passed to the index builder through a record file - never interpolated
   into code.
3b. **build_registry** - regenerates `skills/agent-registry.json` from the
   fresh index plus `plugin-catalog/` (21 plugins) and the MCP roadmap
   (38 servers) and the built-in capabilities. Non-fatal on failure; the
   committed registry remains a fallback.
4. **setup_memory** - writes `memory/config.yaml`, `init-memory.sh` and the
   per-agent memory hooks (Python, parameterized SQL + thin bash wrappers).
5. **setup_compression** - locates headroom, optionally builds it when
   `AGENT_ENHANCEMENTS_BUILD_HEADROOM=1`, and writes the standalone wrapper.
   The default uses an existing binary or the Python fallback.
6. **create_agent_configs** - merges hooks/prompts into each detected
   agent's own config (`~/.claude/settings.json`, `~/.codex/AGENTS.md`,
   ...). The three native adapters preserve user hooks, MCP servers, providers
   and instruction/plugin arrays. Backups are written next to changed files.
   One native `agent-enhancements` gateway loads the nine built MCP servers.
   OpenCode 2 uses `mcp.servers`, `disabled` and `environment`; the adapter
   migrates legacy flat entries. Its prompt hook waits for the managed MCP
   connection before the first model request captures available tools.
6b. **link_native_skills** - runs `scripts/link-skills.sh` to symlink the
   curated set (anthropic-skills + replica-skill + task-observer) into `~/.claude/skills/`
   and `~/.agents/skills/`, making those skills auto-discoverable at
   runtime by every Agent Skills compatible harness. Ownership-safe and
   non-fatal.
7. **create_launcher / create_skills_loader / create_memory_util /
   create_compression_util** - (re)generate the utility scripts.

Every generated artifact is committed alongside the generator: the heredoc
templates inside `setup.sh` and the committed files must stay byte-identical
(enforced by `tests/test_sync.py`).

## Unified index schema (`all-skills.json`)

```json
{
  "version": "1.1",
  "sources": ["agentic-awesome-skills", "ECC", "Ponytail", "Superpowers",
               "replica-skill", "anthropic-skills", "agency-agents",
               "task-observer"],
  "skills": [
    {
      "name": "example-skill",
      "category": "security",
      "description": "...",
      "risk": "safe",
      "source": "ECC",
      "tags": ["..."],
      "tools": ["claude-code"],
      "when_to_use": "...",
      "path": "unified-integration/skills/by-category/security/example-skill/SKILL.md",
      "source_path": "ECC/skills/example-skill/SKILL.md"
    }
  ],
  "total_skills": 3378,
  "categories": {"security": 268, "...": 0},
  "agents_supported": ["claude-code", "codex", "cursor", "gemini-cli",
                        "opencode", "copilot", "windsurf", "kiro"],
  "agent_skill_counts": {"claude-code": 93},
  "last_updated": "2026-11-13T00:00:00Z"
}
```

Schema changes require human approval (CONTRACT §4.2). v1.1 added the
additive `path` / `source_path` fields for capability mapping.

## Capability registry (`agent-registry.json`)

Built by `scripts/registry.py` from three inputs plus static descriptors:
the skills index, `plugin-catalog/catalog.json` (40 plugins) and
`plugin-catalog/mcp-servers.json` (38 MCP servers), plus 7 built-in
capabilities (memory, compression, loader, dispatcher, native linking,
launcher, the registry itself). Every entry carries `id`, `type`, `name`,
`description`, `path` and `activation`. Query surface:

```bash
python3 unified-integration/scripts/registry.py map "<task>"   # activation plan
python3 unified-integration/scripts/registry.py search "pdf"
python3 unified-integration/scripts/registry.py show docx
```

Scoring uses stop-word filtering (EN + ID), format-family aliases
(word->docx, excel->xlsx, powerpoint->pptx), name-match priority and a
zero-friction boost for natively linked skills.

## Invariants

The private root `ui.api.json` is the credential source for project MCPs.
It is not an agent credential store: native authentication, provider settings
and login helpers are outside its scope. The loader and gateway have no
agent-specific authentication or process-coordination logic.
`scripts/api_config.py` reads and validates snapshots; the gateway watches
configuration and sends `notifications/tools/list_changed`. Calls revalidate
the current schema and credential state, including previously cached names.
Offline tool subsets remain available with empty keys. External subprocesses
start only with configured requirements and commands, receive only their
mapped credentials, and are replaced on key rotation. The registry snapshot
retains the full catalog; agent-facing search/map/list filters unavailable
MCPs using the live API configuration.

- One setup script, one index, one memory system, one compression system
  (CONTRACT §2.1).
- Agent-specific config is *generated from* shared sources, never
  maintained by hand (§2.2).
- Skills are aggregated only through `aggregate_skills` (R004).
- All hooks use parameterized SQL in Python (R101).
- Bash utilities run under `set -euo pipefail` (R102) and resolve their
  installation root from their own location, with env-var overrides (R003).
