---
title: Configuration
version: 1.1
last_updated: 2026-11-01
audience: users, maintainers
---

# Configuration

## Environment variables (immutable interface, CONTRACT §8.1)

| Variable | Purpose | Default |
|----------|---------|---------|
| `AGENT_ENHANCEMENTS_BASE_DIR` | Project root | repository root detected from the running script's location |
| `AGENT_ENHANCEMENTS_UNIFIED_DIR` | Integration directory (launcher only) | `<BASE_DIR>/unified-integration` |
| `AGENT_MEMORY_ROOT` | Memory storage | `~/.agent-memory` |
| `AGENT_SKILLS_DIR` | Skills registry | `<BASE_DIR>/unified-integration/skills` |
| `HEADROOM_BIN` | Compression binary | auto-detect: repo build, then `PATH` |
| `AGENT_COMPRESSION_CONFIG` | Compression config path | `<UNIFIED_DIR>/compression/config.yaml` |
| `AGENT_PROMPTS_DIR` | Prompts directory | `<UNIFIED_DIR>/prompts` |

All shipped scripts resolve their installation root from their own file
location first and let the environment override it - nothing requires the
checkout to live at a specific path (R003).

## Files written on your machine

`setup.sh` merges hooks into each **detected** agent's own config and
creates a timestamped backup next to it:

| Agent | File |
|-------|------|
| Claude Code | `~/.claude/settings.json` (+ `~/.claude/CLAUDE.md`) |
| Codex | `~/.codex/config.yaml` |
| OpenCode | `~/.config/opencode/config.json` |
| Cursor | `~/.cursor/settings.json` |
| Gemini CLI | `~/.gemini/config.yaml` |
| Windsurf | `~/.windsurf/config.yaml` |
| Copilot | `~/.config/github-copilot/config.yaml` |
| Kiro | `~/.kiro/config.yaml` |

The merge replaces only the `hooks` key; everything else in an existing
config is preserved.

## Memory configuration - `unified-integration/memory/config.yaml`

Declares the SQLite backend, memory types with their TTLs and scopes,
per-agent plugin paths (as `${AGENT_ENHANCEMENTS_BASE_DIR}` references) and
auto-save triggers. The runtime honors `AGENT_MEMORY_ROOT`.

## Compression configuration - `unified-integration/compression/config.yaml`

Engine selection (`headroom` with a native fallback), per-content modes
(`code`, `logs`, `json`, `markdown`, `generic`), token budgets per agent and
the 75% trigger / 50% target thresholds.

## Skills registry - `unified-integration/skills/`

- `all-skills.json` - unified index (see [ARCHITECTURE.md](ARCHITECTURE.md)).
- `by-category/<category>/<skill>/` and `by-agent/<agent>/<skill>/` are
  (re)populated by `setup.sh`; copies are idempotent.

## Machine-local state

`unified-integration/config/detected-agents.sh` is **auto-generated** per
machine by `setup.sh`; do not commit local modifications. `.claude/settings.local.json`
and aggregation temp files are gitignored (see `.gitignore`).
