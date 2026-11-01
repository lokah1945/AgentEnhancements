---
title: Architecture
version: 1.1
last_updated: 2026-11-01
audience: maintainers, contributors
---

# Architecture

## Overview

AgentEnhancements is an **aggregation platform**: it vendors seven open-source
projects and wires them together through a single integration layer so that
AI coding assistants (Claude Code, Codex, OpenCode, Cursor, Gemini CLI,
Windsurf, Copilot, Kiro) can share one skills registry, one memory system and
one compression layer.

```
AgentEnhancements/
├── unified-integration/     # OWNED integration layer (this repo's code)
│   ├── setup.sh             # single entry point / installer
│   ├── update-skills.sh     # refresh vendored sources (where they are git repos)
│   ├── launch-agent.sh      # universal launcher (env-aware, self-locating)
│   ├── config/              # machine state (detected-agents.sh, auto-generated)
│   ├── prompts/             # per-agent system prompts + universal prompt
│   ├── skills/              # unified registry
│   │   ├── all-skills.json  # UNIFIED INDEX (schema below)
│   │   ├── by-category/     # populated by setup.sh (10 canonical buckets)
│   │   └── by-agent/        # populated by setup.sh (8 canonical agents)
│   ├── memory/              # hooks + config for the memory system
│   ├── compression/         # headroom wrapper + config
│   ├── scripts/             # load-skills.py, memory.py, compress.py
│   └── tests/               # regression suite (python3 tests/run-tests.py)
├── agentic-awesome-skills/  # vendored (2,884 skills)
├── claude-mem/              # vendored
├── ECC/                     # vendored
├── headroom/                # vendored (Rust)
├── ponytail/                # vendored
├── superpowers/             # vendored
└── system-prompts-and-models-of-ai-tools/  # vendored (prompt sources)
```

## Setup pipeline (`setup.sh`)

1. **detect_agents** - probes PATH for known agent CLIs; writes
   `config/detected-agents.sh` (machine-specific, never hand-edited).
2. **setup_prompts** - copies per-agent prompt files from
   `system-prompts-and-models-of-ai-tools/` into `prompts/` (bash globstar
   is required for the recursive globs) and writes the universal prompt.
3. **aggregate_skills** - walks `skills/` of the four skill sources, parses
   SKILL.md frontmatter, copies each skill directory into `by-category/`
   and `by-agent/` (idempotently: targets are removed before copy), and
   rebuilds `all-skills.json` in a single pass. Skill metadata is passed to
   the index builder through a record file - never interpolated into code.
4. **setup_memory** - writes `memory/config.yaml`, `init-memory.sh` and the
   per-agent memory hooks (Python, parameterized SQL + thin bash wrappers).
5. **setup_compression** - locates or builds headroom (cargo optional;
   degrades to a native fallback), writes `compression/config.yaml` and the
   stream-safe `compress.sh` wrapper.
6. **create_agent_configs** - merges hooks/prompts into each detected
   agent's own config (`~/.claude/settings.json`, `~/.codex/config.yaml`,
   ...). Existing keys are preserved; only the `hooks` key is replaced.
   Backups are written next to each modified file.
7. **create_launcher / create_skills_loader / create_memory_util /
   create_compression_util** - (re)generate the utility scripts.

Every generated artifact is committed alongside the generator: the heredoc
templates inside `setup.sh` and the committed files must stay byte-identical
(enforced by `tests/test_sync.py`).

## Unified index schema (`all-skills.json`)

```json
{
  "version": "1.0",
  "sources": ["agentic-awesome-skills", "ECC", "Ponytail", "Superpowers"],
  "skills": [
    {
      "name": "example-skill",
      "category": "security",
      "description": "...",
      "risk": "safe",
      "source": "ECC",
      "tags": ["..."],
      "tools": ["claude-code"],
      "when_to_use": "..."
    }
  ],
  "total_skills": 3116,
  "categories": {"security": 268, "...": 0},
  "agents_supported": ["claude-code", "codex", "cursor", "gemini-cli",
                        "opencode", "copilot", "windsurf", "kiro"],
  "agent_skill_counts": {"claude-code": 93},
  "last_updated": "2026-11-01T18:19:54.468953Z"
}
```

Schema changes require human approval (CONTRACT §4.2).

## Invariants

- One setup script, one index, one memory system, one compression system
  (CONTRACT §2.1).
- Agent-specific config is *generated from* shared sources, never
  maintained by hand (§2.2).
- Skills are aggregated only through `aggregate_skills` (R004).
- All hooks use parameterized SQL in Python (R101).
- Bash utilities run under `set -euo pipefail` (R102) and resolve their
  installation root from their own location, with env-var overrides (R003).
