---
title: Internal APIs
version: 1.2
last_updated: 2026-11-13
audience: maintainers, contributors
---

# Internal APIs

## Capability registry - `unified-integration/scripts/registry.py`

The all-in-one mapping surface across skills, catalog plugins, MCP
servers and built-in capabilities. Reads `all-skills.json`,
`plugin-catalog/catalog.json` and `plugin-catalog/mcp-servers.json`.

| Command | Description |
|---------|-------------|
| `build [--out PATH] [--quiet]` | Regenerate `skills/agent-registry.json` (skills + plugins + MCP + capabilities). Run automatically by `setup.sh` after aggregation. |
| `map "<task>" [--limit N] [--json]` | Activation plan for a natural-language task: top skills (with paths and native-link status), matching plugins, relevant MCP servers, always-available capabilities and usage hints. |
| `search "<query>" [--type T] [--limit N] [--json]` | Scored search across every entry type (or one type: `skill`, `plugin`, `mcp`, `capability`). |
| `show <name-or-id> [--json]` | One entry by id (`skill:docx`) or name (`docx`), including `path`, `source_path` and `activation`. |
| `stats [--json]` | Entry counts by type and source. |
| `list [--type T] [--source S] [--json]` | Enumerate entries. |

Scoring: stop-word filtering (EN + ID), format-family aliases (`word`->docx,
`excel`->xlsx, `powerpoint`->pptx, ...), name-match priority (+8) and a
zero-friction boost (+3) for natively linked skills.

Importable functions: `load_skill_entries()`, `load_plugin_entries()`,
`load_mcp_entries()`, `load_capability_entries()`, `load_all_entries()` and
`rank_entries(entries, query, limit)`.

## Native linking - `unified-integration/scripts/link-skills.sh`

Symlinks registry skills into the directories agents read automatically
at runtime (`~/.claude/skills`, `~/.agents/skills`; override with
`AGENT_SKILLS_NATIVE_TARGETS`). Ownership-safe: only symlinks pointing into
the unified registry are created, refreshed or removed.

| Invocation | Effect |
|-----------|--------|
| `link-skills.sh [--quiet]` | Link the default curated set (anthropic-skills 19 + replica-skill 11) into every target. |
| `link-skills.sh --set <source>` | Link every skill of one source. |
| `link-skills.sh --set all` / `--all` | Link the entire catalog (heavy per-session metadata; warned). |
| `link-skills.sh <name> [...]` | Link specific skills by name. |
| `link-skills.sh --status` | Per-target listing with ownership counts. |
| `link-skills.sh --unlink [names ...]` | Remove registry-owned links (all, or only the named ones). |

## Skills loader - `unified-integration/scripts/load-skills.py`

`SkillsLoader(agent)` reads `all-skills.json` from `AGENT_SKILLS_DIR`
(default: `<repo>/unified-integration/skills`).

| Method | Description |
|--------|-------------|
| `find_skills(task_description, max_results=5) -> list[dict]` | Keyword-scored matching over `when_to_use` (+2), `tags` (+3), `description` (+1) and agent compatibility (+5). Returns the top entries from the index. |
| `load_skill(skill_name) -> dict` | Loads a skill from disk. Supports both layouts: `by-category/<cat>/<name>/SKILL.md` (directory) and `by-category/<cat>/<name>.md` (flat), plus the equivalent `by-agent/<agent>/` paths. Returns `{frontmatter, body, file}` or `{raw, file}` when no frontmatter exists. |

CLI: `load-skills.py <agent> <task_description>`.

## Memory - `unified-integration/scripts/memory.py`

`AgentMemory(agent, project=None)` stores rows in SQLite at
`$AGENT_MEMORY_ROOT/memory.db` (default `~/.agent-memory`).

| Method | Description |
|--------|-------------|
| `save(key, value, memory_type="session_context", metadata=None, ttl_days=None)` | Upsert (`INSERT OR REPLACE`). `expires_at` uses the SQLite format `YYYY-MM-DD HH:MM:SS` so expiry comparisons work. |
| `load(key, memory_type="session_context") -> str or None` | Latest value for the key. |
| `list(memory_type=None, limit=20) -> list[dict]` | Recent memories, values truncated to 200 chars for display. |
| `delete(key, memory_type="session_context") -> bool` | Delete one memory. |
| `cleanup_expired() -> int` | Deletes rows whose `expires_at < datetime('now')`. |

CLI: `memory.py <agent> save|load|list|delete|cleanup ...` - `load` of a
missing key exits `1`.

### Memory hooks - `unified-integration/memory/hooks/`

`<agent>-memory-hook.py` exposes the same commands as `memory.py` scoped to
one agent. `<agent>-memory-hook.sh` is a thin bash wrapper that `exec`s the
Python hook; **no SQL is executed from bash** (CONTRACT R101).

Claude Code hook events map to the CLI as:

```text
PreToolUse  -> save "pre_tool_use:${TOOL_NAME}"    "${TOOL_INPUT}"  session_context
PostToolUse -> save "post_tool_use:${TOOL_NAME}"   "${TOOL_RESULT}" session_context
Stop        -> save "session_summary"              "${SESSION_SUMMARY}" session_context
```

## Compression - `unified-integration/scripts/compress.py`

`compress_content(content, mode="auto", agent="claude-code")` pipes through
the headroom binary (`HEADROOM_BIN`, repo build fallback) and falls back to
`fallback_compress(content, mode)` which implements log de-duplication
(timestamp/ID normalization), JSON compaction and blank-line trimming, with
a 50,000-character output cap.

CLI: `compress.py <mode> [agent] < input` (modes: `auto`, `code`, `logs`,
`json`, `markdown`, `generic`).

`compression/compress.sh` is the shell equivalent; it reads stdin once into
a temp file (stream-safe) and honours `AGENT_ENHANCEMENTS_BASE_DIR`.

## Launcher - `unified-integration/launch-agent.sh`

`launch-agent.sh <agent> [args...]` validates the agent against
`config/detected-agents.sh`, initializes memory, exports the standard
environment (`AGENT_MEMORY_ROOT`, `AGENT_SKILLS_DIR`,
`AGENT_COMPRESSION_CONFIG`, `AGENT_PROMPTS_DIR`,
`AGENT_ENHANCEMENTS_BASE_DIR`, `AGENT_ENHANCEMENTS_UNIFIED_DIR`) and `exec`s
the agent binary.

## Config merge - `merge_json_config` / `merge_yaml_config` (setup.sh)

`merge_<format>_config <target_file> <enhancement_payload>` deep-merges the
payload into an existing config: the `hooks` key is replaced wholesale,
every other key is merged recursively. Payloads and paths are passed to the
Python merger via environment variables. A timestamped backup is written
next to the target before merging.

## Dispatcher - `unified-integration/scripts/dispatch.sh`

`dispatch.sh [--dry-run] "<prompt>"` classifies a natural-language prompt
per [ROUTER_POLICY.md](ROUTER_POLICY.md) and resolves the matching guide:
catalog plugins via `plugin-catalog/<category>/<slug>/SKILL.md`, and the
vendored Anthropic skills via `anthropic-skills/skills/<slug>/SKILL.md`.
An explicit `[skill:<slug>]` prefix bypasses the heuristics.
