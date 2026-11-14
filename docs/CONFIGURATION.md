---
title: Configuration
version: 1.3
last_updated: 2026-11-14
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
| `HEADROOM_BIN` | Standalone compression binary | auto-detect: repo build, then `PATH` |
| `AGENT_ENHANCEMENTS_BUILD_HEADROOM` | Optional Rust build during setup/update | `0`; set `1` to build |
| `CODEX_HOME` | Native Codex configuration directory | `~/.codex` |
| `CLAUDE_CONFIG_DIR` | Native Claude configuration directory | `~/.claude` |
| `XDG_CONFIG_HOME` | OpenCode configuration parent | `~/.config` |
| `XDG_DATA_HOME` | Isolated Python environment parent | `~/.local/share` |
| `AGENT_COMPRESSION_CONFIG` | Compression config path | `<UNIFIED_DIR>/compression/config.yaml` |
| `AGENT_PROMPTS_DIR` | Prompts directory | `<UNIFIED_DIR>/prompts` |
| `AGENT_SKILLS_NATIVE_TARGETS` | Colon-separated native skill link targets (link-skills.sh) | `~/.claude/skills:$HOME/.agents/skills` |

All shipped scripts resolve their installation root from their own file
location first and let the environment override it - nothing requires the
checkout to live at a specific path (R003).

## Files written on your machine

`setup.sh` merges hooks/instructions into each **detected** agent's own
native config and creates a timestamped backup next to it:

| Agent | File (native format) |
|-------|------|
| Claude Code | `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, `~/.claude.json` (MCP), native skills |
| Codex | `~/.codex/AGENTS.md`, `config.toml` (MCP), `hooks.json` |
| OpenCode 2 | Existing `~/.config/opencode/opencode.jsonc` or `opencode.json`, plus `AGENTS.md` |
| Cursor | `~/.cursor/rules/agent-enhancements.mdc` |
| Gemini CLI | `~/.gemini/GEMINI.md` + `~/.gemini/config.yaml` (reference) |
| Windsurf | `~/.codeium/windsurf/rules/agent-enhancements.md` |
| Copilot | `~/.config/github-copilot/config.yaml` (reference) |
| Kiro | `~/.kiro/config.yaml` (reference) |
| All agents | links in `~/.claude/skills/` and `~/.agents/skills/` (curated set) |

The three native adapters preserve user hook handlers, MCP servers and array
entries. Managed handlers are replaced idempotently. Existing same-name user
MCP servers are preserved. Native config writes are atomic and private, with
backups on changes. Marker-guarded markdown preserves personal instructions.
Dependencies are installed in `${XDG_DATA_HOME:-~/.local/share}/agentenhancements/venv`;
no global pip environment is modified. `requirements.txt` defines dependencies.
Malformed native config aborts setup with an error instead of reporting success.
Codex hook trust and CLI authentication remain the application's own controls.

## Memory configuration - `unified-integration/memory/config.yaml`

Declares the SQLite backend, memory types with their TTLs and scopes,
per-agent plugin paths (as `${AGENT_ENHANCEMENTS_BASE_DIR}` references) and
auto-save triggers. The runtime honors `AGENT_MEMORY_ROOT`. Automatic notes use
seven-day retention and full canonical project paths, preventing same-basename
project collisions. Old basename-keyed notes are not automatically migrated.
This integration uses its shared SQLite utility, not a running claude-mem daemon.

## Private MCP state

GraphRAG evidence and video timelines use `AGENT_MEMORY_ROOT/mcp/`, with
private directories/files and a hash of the server working directory as the
namespace. Writes replace files atomically. Old shared `/tmp` caches are not
imported automatically. This is process-cwd scoping, not MCP client-root
sandboxing.

## Compression configuration - `unified-integration/compression/config.yaml`

The standalone compressor supports `code`, `logs`, `json`, `markdown`, `generic`
and `auto`. JSON compaction preserves null/empty values; code whitespace and
repeated lines are retained. Log deduplication is explicit and lossy. The
standalone fallback has a 50,000-character cap. It does not intercept model
requests. Session compaction is handled by each CLI's native implementation;
values in the reference YAML do not configure the CLI's compaction thresholds.

## Skills registry - `unified-integration/skills/`

- `all-skills.json` - unified skills index (see [ARCHITECTURE.md](ARCHITECTURE.md)).
- `agent-registry.json` - capability registry across skills, plugins, MCP
  servers and built-ins (see [API.md](API.md) for the query surface).
- `by-category/<category>/<skill>/` and `by-agent/<agent>/<skill>/` are
  (re)populated by `setup.sh`; copies are idempotent.

## Native skill linking

`AGENT_SKILLS_NATIVE_TARGETS` (colon-separated) controls where
`link-skills.sh` creates its symlinks. Only symlinks owned by the registry
are managed; user data is never touched. The default curated set is
anthropic-skills (19) + replica-skill (11).

## Machine-local state

`unified-integration/config/detected-agents.sh` is **auto-generated** per
machine by `setup.sh`; do not commit local modifications. `.claude/settings.local.json`
and aggregation temp files are gitignored (see `.gitignore`).
