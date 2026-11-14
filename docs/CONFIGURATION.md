---
title: Configuration
version: 1.4
last_updated: 2026-11-15
audience: users, maintainers
---

# Configuration

## Central credentials — `ui.api.json`

Setup creates **one private file at the repository root**, using
[the empty template](../unified-integration/config/ui.api.example.json).
Edit its `api_keys` string values and `connections` endpoints/client IDs.
The file is ignored by git and created with mode `0600`. Native CLI configs
contain the gateway command, not copies of its secrets. The JSON schema
provides editor validation. Setup preserves populated values.

`mcp.<server>.required` maps each server to central value names.
An empty/whitespace key disables its dependent cloud tools, even when the
parent shell has a populated API environment variable. Invalid or missing
JSON also disables cloud access. Local tools remain available. The gateway
watches edits every 0.5 seconds and emits MCP tool-list notifications;
every call rechecks credentials to reject stale cached tools immediately.
Calls already sent to a provider cannot be withdrawn by clearing a key.

Nine bundled servers provide 36 tools with all keys empty. GraphRAG is local
and requires no API key. Embeddings default to deterministic local vectors;
the `openai` backend is permitted only with `OPENAI_API_KEY`. Semantic
`vision_describe` is hidden without that key; image comparison and OCR stay
available. `OPENAI_BASE_URL` includes `/v1`; model names have separate fields.

External catalog entries are hidden until required references and an
installed `command` array are configured in this same file. `env` maps
subprocess environment names to central reference names, never literal
secrets. Arguments accept `{python}` and `{repo}`; no shell expansion is
performed. Configuring a working command activates it automatically. Clearing
a required key terminates that backend; key rotation reconnects it. A catalog
entry is not proof that its suggested npm package exists or has completed
OAuth authorization. Google/Microsoft client IDs and secrets alone do not
constitute a completed OAuth login.

For optional diagnostics, `python3 unified-integration/scripts/api_config.py
status` prints key-presence booleans and hidden reasons, never secret values.
Agents do not need to run it. Runtime session notes redact configured secrets.

Claude Code's existing custom endpoint/model configuration is preserved. A custom
gateway authenticates using its own credentials; this integration does not
require a claude.ai login. `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`,
`ANTHROPIC_BASE_URL` and `ANTHROPIC_MODEL` slots are included for central
mapping. When existing settings contain custom auth environment values and
no user-owned helper, setup moves those values to the central file and installs
the native `apiKeyHelper` automatically. `api_config.py claude-key` prints the
credential directly to Claude and must not be used as a diagnostic. The helper
refreshes at a one-second TTL; external environment credentials can still take
precedence. Existing custom helpers are preserved. Endpoint/model fields stay
in Claude's native settings; the integration does not guess provider choices.

With an explicit `CLAUDE_CONFIG_DIR`, Claude stores user MCP configuration in
`<CLAUDE_CONFIG_DIR>/.claude.json`; without that override it uses
`~/.claude.json`. This distinction is verified using the installed CLI.

Claude's Linux prompt hook waits for its own native MCP tools to be listed;
coordination markers contain process IDs only in the private user state
directory. OpenCode uses its public MCP status API. This prevents cold-start
model requests from racing MCP initialization.

**Codex client limitation:** versions 0.167.2 and 0.169.0 retain their tool
catalog during a turn. The gateway still rechecks every call and immediately
rejects revoked credentials, but a newly available tool can require a fresh
session to appear. Claude/OpenCode passed live empty → populated → empty
catalog tests without a reconnect command. No CLI permissions are bypassed.

## Environment variables (immutable interface, CONTRACT §8.1)

| Variable | Purpose | Default |
|----------|---------|---------|
| `AGENT_ENHANCEMENTS_BASE_DIR` | Project root | repository root detected from the running script's location |
| `AGENT_ENHANCEMENTS_UNIFIED_DIR` | Integration directory (launcher only) | `<BASE_DIR>/unified-integration` |
| `AGENT_MEMORY_ROOT` | Memory storage | `~/.agent-memory` |
| `AGENT_SKILLS_DIR` | Skills registry | `<BASE_DIR>/unified-integration/skills` |
| `HEADROOM_BIN` | Standalone compression binary | auto-detect: repo build, then `PATH` |
| `AGENT_ENHANCEMENTS_BUILD_HEADROOM` | Optional Rust build during setup/update | `0`; set `1` to build |
| `AGENT_ENHANCEMENTS_API_FILE` | Optional private API file override for isolated tests/installations | `<repository>/ui.api.json` |
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
namespace. Writes replace files atomically. GraphRAG rereads current snapshots;
video timeline updates also take a process lock to avoid lost concurrent edits.
Old shared `/tmp` caches are not
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
