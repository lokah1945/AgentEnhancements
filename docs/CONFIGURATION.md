---
title: Configuration
version: 1.8
last_updated: 2026-11-20
audience: users, maintainers
---

## Configuration

### Central credentials — `ui.api.json`

This file is exclusively for **AgentEnhancements MCP service credentials**.
For example, `TAVILY_API_KEY` belongs here. Agent login tokens, model-provider
credentials, custom endpoints, `apiKeyHelper` and settings files remain owned
by Claude Code, Codex, OpenCode or any other host agent. The MCP credential
loader never reads, imports or changes that host configuration.

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

Nine bundled servers expose enabled local tools with all keys empty.
GraphRAG is local and requires no API key. Embeddings default to local vectors;
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

The template contains MCP secret slots and mappings for the catalog
entries. The template and schema define the current names. `OPENAI_API_KEY` and
its model/endpoint fields apply only to the
embeddings/vision MCP implementations; they do not configure the host agent.
The same MCP configuration works for any compatible client, independently
of how that client authenticates to its own model provider.

With an explicit `CLAUDE_CONFIG_DIR`, Claude stores user MCP configuration in
`<CLAUDE_CONFIG_DIR>/.claude.json`; without that override it uses
`~/.claude.json`. This distinction is verified using the installed CLI.

MCP startup and discovery are handled by the host's native integration. The
shared MCP gateway does not inspect CLI process ancestry or maintain per-CLI
readiness files.

**Codex client limitation:** versions 0.167.2 and 0.169.0 retain their tool
catalog during a turn. The gateway still rechecks every call and immediately
rejects revoked credentials, but a newly available tool can require a fresh
session to appear. Claude/OpenCode passed live empty → populated → empty
catalog tests without a reconnect command. No CLI permissions are bypassed.

### Adaptive preflight — `.agentenhancements/config/model.json`

The optional capability-selection preflight (CONTRACT §8.5) is configured in
a user-scope file that never carries secrets and never lives inside a
project checkout:

```text
.agentenhancements/config/model.json   # fallback
# .agentenhancements/config/model.json
```

```json
{"adaptive_preflight_mode": 0}
```

`0` (or a missing file) keeps the default discovery cards. `1` lets a host
adapter supply a native selection; adapters without that integration simply
stay on the default path. `2` adds `endpoint` (HTTPS base URL), `sdk`
(`openai` or `anthropic`) and `model`, and calls that endpoint from the
existing prompt hook - no adapter change required. The Mode 2 key resolves
from `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY`, the OS keyring (service
`agentenhancements.preflight`), or a 0600 `<config dir>/preflight.key` -
never from model.json or ui.api.json. Every failure falls back to the
default cards for that turn with one stderr diagnosis line.
See [ADAPTIVE_PREFLIGHT.md](ADAPTIVE_PREFLIGHT.md) for the full contract,
protocols, deadlines and verification.

### Environment variables (immutable interface, CONTRACT §8.2)

- **Variable:** `AGENT_ENHANCEMENTS_BASE_DIR`
  - **Purpose:** Project root
  - **Default:** repository root detected from the running script's location

- **Variable:** `AGENT_ENHANCEMENTS_UNIFIED_DIR`
  - **Purpose:** Integration directory (launcher only)
  - **Default:** `<BASE_DIR>/unified-integration`

- **Variable:** `AGENT_MEMORY_ROOT`
  - **Purpose:** Memory storage
  - **Default:** `.agentenhancements/memory`

- **Variable:** `TASK_OBSERVER_WORKSPACE`
  - **Purpose:** Task Observer observation workspace root (absolute path;
    default `$AGENT_MEMORY_ROOT/task-observer`). See
    [TASK_OBSERVER.md](TASK_OBSERVER.md)
  - **Default:** `$AGENT_MEMORY_ROOT/task-observer`

- **Variable:** `AGENT_SKILLS_DIR`
  - **Purpose:** Skills registry
  - **Default:** `<BASE_DIR>/unified-integration/skills`

- **Variable:** `HEADROOM_BIN`
  - **Purpose:** Standalone compression binary
  - **Default:** auto-detect: repo build, then `PATH`

- **Variable:** `AGENT_ENHANCEMENTS_BUILD_HEADROOM`
  - **Purpose:** Optional Rust build during setup/update
  - **Default:** `1`; set `0` to skip the build

- **Variable:** `AGENT_ENHANCEMENTS_API_FILE`
  - **Purpose:** Optional private API file override for isolated
    tests/installations
  - **Default:** `<repository>/ui.api.json`

- **Variable:** `CODEX_HOME`
  - **Purpose:** Native Codex configuration directory
  - **Default:** `~/.codex`

- **Variable:** `CLAUDE_CONFIG_DIR`
  - **Purpose:** Native Claude configuration directory
  - **Default:** `~/.claude`

- **Variable:** `XDG_CONFIG_HOME`
  - **Purpose:** OpenCode configuration parent
  - **Default:** `~/.config`

- **Variable:** `XDG_DATA_HOME`
  - **Purpose:** Isolated Python environment parent
  - **Default:** `~/.local/share`

- **Variable:** `HERMES_HOME`
  - **Purpose:** Hermes data root; selected profiles live below `profiles/`
  - **Default:** `~/.hermes`

- **Variable:** `AGENT_COMPRESSION_CONFIG`
  - **Purpose:** Compression config path
  - **Default:** `<UNIFIED_DIR>/compression/config.yaml`

- **Variable:** `AGENT_PROMPTS_DIR`
  - **Purpose:** Prompts directory
  - **Default:** `<UNIFIED_DIR>/prompts`

- **Variable:** `AGENT_SKILLS_NATIVE_TARGETS`
  - **Purpose:** Colon-separated native skill link targets (link-skills.sh)
  - **Default:**
    `~/.claude/skills:~/.agents/skills:~/.codex/skills:~/.config/opencode/skills`

- **Variable:** `AGENT_ENHANCEMENTS_MODEL_FILE`
  - **Purpose:** Optional adaptive-preflight model.json override for isolated
    tests
  - **Default:** `.agentenhancements/config/model.json`

- **Variable:** `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY`
  - **Purpose:** Adaptive preflight Mode 2 key (overrides keyring and
    preflight.key)
  - **Default:** unset

- **Variable:** `AE_PREFLIGHT_DEADLINE_MS`
  - **Purpose:** Adaptive preflight total phase deadline (pilot knob)
  - **Default:** `2000`

All shipped scripts resolve their installation root from their own file
location first and let the environment override it - nothing requires the
checkout to live at a specific path (R003).

### Files written on your machine

`setup.sh` merges hooks/instructions into each **selected, detected** agent's
own
native config and creates a timestamped backup next to it:

- **Agent:** Claude Code
  - **File (native format):** `~/.claude/settings.json`, `~/.claude/CLAUDE.md`,
    `~/.claude.json` (MCP), native skills

- **Agent:** Codex
  - **File (native format):** `~/.codex/AGENTS.md`, `config.toml` (MCP),
    `hooks.json`

- **Agent:** OpenCode 2
  - **File (native format):** Existing `~/.config/opencode/opencode.jsonc` or
    `opencode.json`, plus `AGENTS.md`

- **Agent:** Hermes
  - **File (native format):** Selected `~/.hermes/profiles/<name>/config.yaml`,
    `SOUL.md`, and `plugins/agent-enhancements` symlink

- **Agent:** Cursor
  - **File (native format):** `~/.cursor/rules/agent-enhancements.mdc`

- **Agent:** Gemini CLI
  - **File (native format):** `~/.gemini/GEMINI.md` + `~/.gemini/config.yaml`
    (reference)

- **Agent:** Windsurf
  - **File (native format):** `~/.codeium/windsurf/rules/agent-enhancements.md`

- **Agent:** Copilot
  - **File (native format):** `~/.config/github-copilot/config.yaml` (reference)

- **Agent:** Kiro
  - **File (native format):** `~/.kiro/config.yaml` (reference)

- **Agent:** All agents
  - **File (native format):** links in `~/.claude/skills/` and
    `~/.agents/skills/` (curated set)

The four native adapters preserve user hook handlers, MCP servers and array
entries. Managed handlers are replaced idempotently. Existing same-name user
MCP servers are preserved. Native config writes are atomic and private, with
backups on changes. Marker-guarded markdown preserves personal instructions.
Managed gateway updates retain per-tool approvals, timeouts and custom
environment entries, including OpenCode's disabled/codemode choices.
Python aliases within the prepared venv produce the same
hook and gateway commands, avoiding redundant backups and hook trust changes.
An OpenCode 1 installation is refused before its native
configuration is rewritten.
Dependencies are installed in
`.agentenhancements/runtime/venv`;
no global pip environment is modified. `requirements.txt` defines dependencies.
Malformed native config aborts setup with an error instead of reporting success.
Codex hook trust and CLI authentication remain the application's own controls.

### Memory configuration - `unified-integration/memory/config.yaml`

Declares the SQLite backend, memory types with their TTLs and scopes,
per-agent plugin paths (as `${AGENT_ENHANCEMENTS_BASE_DIR}` references) and
auto-save triggers. The runtime honors `AGENT_MEMORY_ROOT`. Automatic notes use
seven-day retention and full canonical project paths, preventing same-basename
project collisions. Old basename-keyed notes are not automatically migrated.
This integration uses its shared SQLite utility, not a running claude-mem
daemon.

### Private MCP state

GraphRAG evidence and video timelines use `AGENT_MEMORY_ROOT/mcp/`, with
private directories/files and a hash of the server working directory as the
namespace. Writes replace files atomically. GraphRAG rereads current snapshots;
video timeline updates also take a process lock to avoid lost concurrent edits.
Old shared `/tmp` caches are not
imported automatically. This is process-cwd scoping, not MCP client-root
sandboxing.

### Compression configuration - `unified-integration/compression/config.yaml`

The standalone compressor supports `code`, `logs`, `json`, `markdown`, `generic`
and `auto`. JSON compaction preserves null/empty values; code whitespace and
repeated lines are retained. Log deduplication is explicit and lossy. The
standalone fallback has a 50,000-character cap. It does not intercept model
requests. Session compaction is handled by each CLI's native implementation;
values in the reference YAML do not configure the CLI's compaction thresholds.

### Skills registry - `unified-integration/skills/`

- `all-skills.json` - unified skills index (see
  [ARCHITECTURE.md](ARCHITECTURE.md)).
- `agent-registry.json` - capability registry across skills, plugins, MCP
  servers and built-ins (see [API.md](API.md) for the query surface).
- `by-category/<category>/<skill>/` and `by-agent/<agent>/<skill>/` are
  (re)populated by `setup.sh`; copies are idempotent.

### Native skill linking

`AGENT_SKILLS_NATIVE_TARGETS` (colon-separated) controls where
`link-skills.sh` creates its symlinks. Only symlinks owned by the registry
are managed; user data is never touched. The default links task-observer and
15 Superpowers workflow skills, with native metadata inside its token budget.
`--set curated` explicitly links anthropic-skills (19), replica-skill (11) and
task-observer (1). The full library remains available through registry search.

### Machine-local state

`unified-integration/config/detected-agents.sh` is **auto-generated** per
machine by `setup.sh`; do not commit local modifications.
`.claude/settings.local.json`
and aggregation temp files are gitignored (see `.gitignore`).

`.agentenhancements/config/host-selection.json` stores
an optional `agents` array and `hermes_profiles` array. Set them with
`native-integration.py --select-agents claude-code,codex,opencode,hermes
--profile ilma --profile master-chief`, using the prepared runtime.
Setup filters detected agents through this saved selection; explicit
`--agent` invocations still target the named adapter. Profile selection never
recreates missing personas or imports credentials from another host.

### Dependency refresh and privacy hardening

Setup records a SHA-256 digest of `requirements.txt` beside the isolated
venv. A changed requirements file or missing import triggers installation;
unchanged requirements preserve the environment. Filelock requires at least
4.2.1 (Python 3.11 or later).

Memory initialization creates private storage before SQLite opens it and
refuses a database symlink. Runtime/observer notes and audit text redact
recognized authentication fields and configured credentials. Authenticated
embeddings/vision requests refuse redirects. Public arXiv/news response
caches also use private storage below `AGENT_MEMORY_ROOT`.

Preflight Mode 2 transmits the bounded, redacted user prompt and public
capability metadata to the configured endpoint. Redaction protects known
credential values and recognizable authentication patterns; it does not
classify every possible private source snippet. Mode 0 stays local.

## Checkout-local AE storage

AE-owned dependencies and state live under the active checkout's ignored
`.agentenhancements/` directory. Paths resolve from the installed source,
independently of the current working directory or global XDG settings:

- `runtime/venv/`: the Python interpreter and MCP dependencies.
- `config/model.json`, `config/preflight.key`: optional adaptive selector.
- `config/host-selection.json`: native host/profile preferences.
- `memory/`: SQLite session notes and the task-observer workspace.
- `cache/`: Python/uv/pip/npm/Cargo/model caches and temporary task workspaces.

The directory is private (0700); credentials and memory files remain0600.
`ui.api.json` and `search_providers.json` stay ignored at the checkout root.
They are never copied from another checkout automatically.

Native agent configuration is owned by the host application. Setup merges
only the AE bridge into that configuration: commands, hooks and symlinks
point at the active checkout and its local runtime. Moving a checkout
requires rerunning setup; old managed paths are refreshed while personal
plugins, credentials and approvals are preserved.

`AGENT_ENHANCEMENTS_STATE_DIR` is an optional absolute override for isolated
fixtures. Existing explicit memory/API/model-file overrides remain
supported. The normal setup command rejects state, memory, API/model or headroom
overrides outside the checkout. Isolated low-level fixture utilities keep
their explicit override support.
No global AE memory or model file is imported implicitly. Back up and
review old state before a deliberate migration; setup does not move or
remove user data. System Python, Node, Rust and agent CLIs are prerequisites,
not copies of AE plugin code.

Cargo build outputs resolve to `headroom/target` inside the checkout,
including when a caller has a global CARGO_TARGET_DIR. A normal install
rejects target/binary symlinks that leave the checkout. Audit/consent helper
logs retain their documented private `unified-integration/memory/audit/`
location; those logs also stay inside the checkout.
