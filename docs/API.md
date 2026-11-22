---
title: Internal APIs
version: 1.6
last_updated: 2026-11-16
audience: maintainers, contributors
---

## Internal APIs

### Capability registry - `unified-integration/scripts/registry.py`

The all-in-one mapping surface across skills, catalog plugins, MCP
servers and built-in capabilities. Reads `all-skills.json`,
`plugin-catalog/catalog.json` and `plugin-catalog/mcp-servers.json`.

- **Command:** `build [--out PATH] [--quiet]`
  - **Description:** Regenerate `skills/agent-registry.json` (skills + plugins +
    MCP + capabilities). Run automatically by `setup.sh` after aggregation.

- **Command:** `map "<task>" [--limit N] [--json]`
  - **Description:** Activation plan for a natural-language task: top skills
    (with paths and native-link status), matching plugins, relevant MCP servers,
    always-available capabilities and usage hints.

- **Command:** `search "<query>" [--type T] [--limit N] [--catalog] [--json]`
  - **Description:** Scored search across every entry type (or one type:
    `skill`, `plugin`, `mcp`, `capability`). Includes unavailable candidates
    and their blockers when `--catalog` is supplied. Text and JSON results
    carry at most five complete cards within the search-page token budget.

- **Command:** `show <name-or-id> [--json]`
  - **Description:** One entry by id (`skill:docx`) or name (`docx`), including
    `path`, `source_path` and `activation`.

- **Command:** `stats [--json]`
  - **Description:** Entry counts by type and source.

- **Command:** `list [--type T] [--source S] [--json]`
  - **Description:** Enumerate entries.

Scoring uses the shared registry ranker: English/Indonesian intent terms,
weighted synonyms, format aliases, name/phrase matches and an abstention
floor. Host compatibility filters candidates without adding relevance.
Readiness checks the actual source file and native link target.

Importable functions: `load_skill_entries()`, `load_plugin_entries()`,
`load_mcp_entries()`, `load_capability_entries()`, `load_all_entries()` and
`rank_entries(entries, query, limit)`.

`search`, `map` and `list` hide unavailable MCP servers according to the live
`ui.api.json`. `show`, `stats` and the generated snapshot retain catalog
information for maintainers; they are not runtime connectivity probes.

### Credential configuration and native MCP gateway

`scripts/api_config.py init` creates the private root `ui.api.json` once;
`migrate` upgrades it to schema version 2 once (idempotent, private backup,
atomic replace, value-free JSON report; exit code 1 when refused).
`status` returns per-reference key counts, readiness reasons and the presence
of `ffmpeg`, `ffprobe` and `tesseract` on `PATH`.
Importable functions:

- `read_config()`: validated snapshot; `api_keys` is normalized to
  `{reference: [usable keys]}` for version 1 and 2 files.
- `keys(name, config=None)`, `value(name, config=None)` (first usable key,
  stable) and `has_usable_key(name, config=None)`: pure lookups that never
  move the rotation pointer.
- `request_keys(name, config=None)` / `select_key_for_request(name,
  config=None)`: key candidates for one outgoing request; the per-reference
  pointer advances exactly once per call. `report_key_failure(name, key,
  seconds)` pauses one key (1-300 s); `key_health(name, config=None)`
  returns counts only.
- `all_keys_for_redaction(config=None)` and `redact(text, config=None)`.
- `server_state(name, config=None)` (honours `required`, `any_of`,
  `enabled`, built-in `BUILTIN_ANY_OF`), `cloud_available(server, key,
  config=None)` and `migrate(legacy_dir=None)`.

Missing/invalid config never falls back to shell API credentials.
`AGENT_ENHANCEMENTS_API_FILE` is an optional override. This API covers AE
services and the adaptive-preflight selector key only. It has no host-auth
migration or
credential-output command, and never reads agent settings/provider credentials.

`mcp-servers/gateway.py` speaks MCP stdio and advertises `tools.listChanged`.
Bundled tools are namespaced, for example `embeddings_embed`, `vision_compare`
and `graphrag_query`. The cloud-only `vision_describe` disappears with an
empty `OPENAI_API_KEY`; embeddings restrict the backend enum to `local`.
Current schema validation and credential checks run on every call. Failures
use `isError: true`. Polling discovers edits without a manual tool invocation.

External servers use `mcp.<name>.command` arrays and `env` reference mappings
in the same file. AE launches installed entry points directly. Configuration
diagnostics report `host_handshake_required` for commands eligible to connect.
A package runner reports `package_launcher_requires_provisioning`. The
gateway proxies tool schemas and results. OAuth and account permissions are
managed by the provider or the host.

### Native linking - `unified-integration/scripts/link-skills.sh`

Symlinks registry skills into the directories agents read automatically
at runtime (`~/.claude/skills`, `~/.agents/skills`, `~/.codex/skills`,
`~/.config/opencode/skills`; override with
`AGENT_SKILLS_NATIVE_TARGETS`). Ownership-safe: only symlinks pointing into
the unified registry are created, refreshed or removed.

- **Invocation:** `link-skills.sh [--quiet]`
  - **Effect:** Link task-observer and 15 Superpowers workflow skills into every
    target.

- **Invocation:** `link-skills.sh --set <source>`
  - **Effect:** Link every skill of one source.

- **Invocation:** `link-skills.sh --set all` / `--all`
  - **Effect:** Link the entire catalog (heavy per-session metadata; warned).

- **Invocation:** `link-skills.sh <name> [...]`
  - **Effect:** Link specific skills by name.

- **Invocation:** `link-skills.sh --status`
  - **Effect:** Per-target listing with ownership counts.

- **Invocation:** `link-skills.sh --unlink [names ...]`
  - **Effect:** Remove registry-owned links (all, or only the named ones).

### Task Observer status - `unified-integration/scripts/task-observer.py`

`status` returns JSON describing the vendored bundle and observation workspace.
An installed, enabled bundle reports `state: "ready"` before the first session
as well as after bootstrap. `workspace_exists` separately indicates whether
bootstrap has created the workspace; reading status never creates it.
Missing bundles report `state: "not installed"`, and disabled workspaces report
`state: "disabled"`. Diagnostic states retain the `degraded` prefix.

### Skills loader - `unified-integration/scripts/load-skills.py`

`SkillsLoader(agent)` reads `all-skills.json` from `AGENT_SKILLS_DIR`
(default: `<repo>/unified-integration/skills`).

- **Method:** `find_skills(task_description, max_results=5) -> list[dict]`
  - **Description:** Shared registry ranking after host compatibility filtering;
    host aliases are normalized. Unrelated requests return no candidates.

- **Method:** `load_skill(skill_name) -> dict`
  - **Description:** Loads a skill from disk. Supports both layouts:
    `by-category/<cat>/<name>/SKILL.md` (directory) and
    `by-category/<cat>/<name>.md` (flat), plus the equivalent
    `by-agent/<agent>/` paths. Returns `{frontmatter, body, file}` or `{raw,
    file}` when no frontmatter exists.

CLI: `load-skills.py <agent> <task_description>`.

### Memory - `unified-integration/scripts/memory.py`

`AgentMemory(agent, project=None)` stores rows in SQLite at
`$AGENT_MEMORY_ROOT/memory.db` (default `.agentenhancements/memory`).

- **Method:** `save(key, value, memory_type="session_context", metadata=None,
  ttl_days=None)`
  - **Description:** Upsert (`INSERT OR REPLACE`). `expires_at` uses the SQLite
    format `YYYY-MM-DD HH:MM:SS` so expiry comparisons work.

- **Method:** `load(key, memory_type="session_context") -> str or None`
  - **Description:** Latest unexpired value for the key.

- **Method:** `list(memory_type=None, limit=20) -> list[dict]`
  - **Description:** Recent memories, values truncated to 200 chars for display.

- **Method:** `delete(key, memory_type="session_context") -> bool`
  - **Description:** Delete one memory.

- **Method:** `cleanup_expired() -> int`
  - **Description:** Deletes rows whose `expires_at < datetime('now')`.

CLI: `memory.py <agent> save|load|list|delete|cleanup ...` - `load` of a
missing key exits `1`.

#### Memory hooks - `unified-integration/memory/hooks/`

`<agent>-memory-hook.py` exposes the same commands as `memory.py` scoped to
one agent. `<agent>-memory-hook.sh` is a thin bash wrapper that `exec`s the
Python hook; **no SQL is executed from bash** (CONTRACT R101).

#### Automatic lifecycle runtime - `scripts/runtime.py`

`runtime.py <claude-code|codex|opencode|hermes> [--text]` reads one native
JSON event from stdin. Default Mode 0 performs no model/network inference;
optional preflight Mode 2 sends a bounded, redacted prompt to the explicitly
configured endpoint. See [adaptive preflight](ADAPTIVE_PREFLIGHT.md).

- **Event:** `SessionStart`
  - **Action:** Restore recent unexpired notes for this agent and canonical
    project path

- **Event:** `UserPromptSubmit`
  - **Action:** Save a bounded task note and suggest relevant local skill cards
    (default 8, bounded by the context budget)

- **Event:** `PreToolUse` / `PostToolUse`
  - **Action:** Save only the tool name; raw inputs/outputs are never stored

- **Event:** `Stop`
  - **Action:** Save bounded `last_assistant_message` when provided

Claude/Codex context uses `hookSpecificOutput.additionalContext`. OpenCode's
plugin requests plain text with `--text`. Empty `Stop` output is `{}`. Input
is capped at 2 MB, injected context at 12,000 characters, saved task/summary
notes at 600 characters. Recognizable credentials are redacted; notes expire
after seven days. Invalid input/storage failures are advisory and never block
the CLI. Memory lookup still enforces agent/project isolation and expiry.

`native-integration.py --agent <agent|all> [--mcp-only]` installs native
configuration. Run it using the interpreter returned by
`bash scripts/setup-mcp.sh --prepare`. `setup.sh` invokes it automatically.
`setup-mcp.sh --check` tests the actual stdio protocol of all ten built
servers.

### Compression - `unified-integration/scripts/compress.py`

`compress_content(content, mode="auto", agent="claude-code")` pipes through
the headroom binary (`HEADROOM_BIN`, repo build fallback) and falls back to
`fallback_compress(content, mode)` which implements log de-duplication
(timestamp/ID normalization, explicit `logs` mode), data-preserving JSON
compaction and unchanged code content, with a 50,000-character output cap.

CLI: `compress.py <mode> [agent] < input` (modes: `auto`, `code`, `logs`,
`json`, `markdown`, `generic`).

`compression/compress.sh` delegates to that utility and consumes stdin once.
A failed external headroom executable falls back to Python.

### Launcher - `unified-integration/launch-agent.sh`

`launch-agent.sh <agent> [args...]` validates the agent against
`config/detected-agents.sh`, initializes memory, exports the standard
environment (`AGENT_MEMORY_ROOT`, `AGENT_SKILLS_DIR`,
`AGENT_COMPRESSION_CONFIG`, `AGENT_PROMPTS_DIR`,
`AGENT_ENHANCEMENTS_BASE_DIR`, `AGENT_ENHANCEMENTS_UNIFIED_DIR`) and `exec`s
the agent binary.

### Config merge - `merge_yaml_config` (setup.sh)

The internal `merge_yaml_config <target_file> <enhancement_payload>` helper
merges reference YAML configuration and backs up only changed files.
Payloads and paths are data passed through environment variables. Native
JSON/TOML configuration and user hook preservation belong to
`native-integration.py` and `native_config.py`; there is no shared
`merge_json_config` function.

### Dispatcher - `unified-integration/scripts/dispatch.sh`

`dispatch.sh [--dry-run] "<prompt>"` classifies a natural-language prompt
per [ROUTER_POLICY.md](ROUTER_POLICY.md) and resolves the matching guide:
catalog plugins via `plugin-catalog/<category>/<slug>/SKILL.md`, and the
vendored Anthropic skills via `anthropic-skills/skills/<slug>/SKILL.md`.
An explicit `[skill:<slug>]` prefix bypasses the heuristics.
