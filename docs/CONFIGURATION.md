---
title: Configuration
version: 2.0
last_updated: 2026-11-25
audience: users, maintainers
---

## Configuration

### Central credentials — `ui.api.json`

This file is the **only AE-managed configuration file** for AgentEnhancements
service credentials, connections, adaptive-preflight settings and MCP
overrides. For example, `TAVILY_API_KEY` belongs here. Agent login tokens, model-provider
credentials, custom endpoints, `apiKeyHelper` and settings files remain owned
by Claude Code, Codex, OpenCode or any other host agent. The MCP credential
loader never reads, imports or changes that host configuration.

Setup creates **one private file at the repository root**, using
[the empty template](../unified-integration/config/ui.api.example.json).
Edit its `api_keys` arrays and `connections` endpoints/client IDs.
The file is ignored by git and created with mode `0600`.

Schema version 2 stores every credential reference as an **array of keys**,
so one provider can hold several keys:

```json
{
  "version": 2,
  "api_keys": {
    "TAVILY_API_KEY": ["key-a", "key-b", "key-c"],
    "YOU_API_KEY": ["key-d"],
    "EXA_API_KEY": []
  },
  "connections": {},
  "preflight": {"mode": 0, "sdk": "", "endpoint": "", "model": "",
                "api_key_ref": "PREFLIGHT_API_KEY"},
  "mcp": {}
}
```

`[]`, a missing reference, `""` and whitespace-only entries are not
credentials. Entries are trimmed and identical keys are de-duplicated; at
most 32 keys per reference. A version 2 file with a plain string value is
rejected (fail closed). First-party adapters (`search-mcp`) choose a key per
HTTP request, round-robin, and pause a key for a bounded time after a
401/402/403/429-style answer; external stdio MCP servers receive the first
usable key when they start, so they are not described as rotating. Rotation
and cooldown state lives in the gateway process memory only. Several keys
are not a promise of a higher provider quota.

**Migration.** Version 1 files (string credentials) keep working and
`api_config.py status` reports `"migration_pending": true`. Setup runs the
one-time, idempotent upgrade; it can also be run by hand:

```bash
python3 unified-integration/scripts/api_config.py migrate
```

It writes a private `ui.api.json.backup.<timestamp>` first, replaces the file
atomically (the original stays untouched on any failure), converts strings to
arrays (`""` becomes `[]`) and preserves unknown fields. When `ui.api.json`
has no `preflight` section yet, it also imports a legacy adaptive-preflight
`.agentenhancements/config/model.json` and an owner-only `preflight.key` from
the same directory; those legacy files are left in place and are no longer
read. The import happens once: afterwards a non-secret owner-only
`legacy-preflight.imported` marker beside them prevents a later setup from
re-importing a section or key the user removed. Restore by copying the
backup over `ui.api.json`. A personal `search_providers.json` is not an AE
file: AE never reads, imports, migrates
or deletes it. Native CLI configs
contain the gateway command, not copies of its secrets. The JSON schema
provides editor validation. Setup preserves populated values.

`mcp.<server>.required` maps each server to central value names; every
listed reference must hold a usable value. `mcp.<server>.any_of` needs at
least one of its references; `optional` never gates visibility.
An empty/whitespace key disables its dependent cloud tools, even when the
parent shell has a populated API environment variable. Invalid or missing
JSON also disables cloud access. Local tools remain available. The gateway
watches edits every 0.5 seconds and emits MCP tool-list notifications;
every call rechecks credentials to reject stale cached tools immediately.
Calls already sent to a provider cannot be withdrawn by clearing a key.

Nine bundled servers expose enabled local tools with all keys empty. The
tenth, `search-mcp`, has only credentialed tools and stays hidden until at
least one of `YOU_API_KEY`, `TAVILY_API_KEY`, `EXA_API_KEY`,
`FIRECRAWL_API_KEY`, `NEWSAPI_KEY` or `SERPER_API_KEY` holds a key; keyless
arXiv and Google
News RSS remain available ([search providers](SEARCH_PROVIDER_APIS.md)).
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
status` prints per-reference key counts and hidden reasons, never secret values.
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

### Adaptive preflight — `ui.api.json` `preflight`

The optional capability-selection preflight (CONTRACT §8.5) is configured in
the `preflight` section of the same private `ui.api.json`:

```json
"preflight": {"mode": 0, "sdk": "", "endpoint": "", "model": "",
              "api_key_ref": "PREFLIGHT_API_KEY"}
```

`0` (or a missing section) keeps the default discovery cards. `1` uses
`endpoint` (HTTPS base URL), `sdk` (`openai` or `anthropic`), `model` and the
key held in `api_keys[api_key_ref]` of this file. Custom fields are kept but
unused on mode 0. The former host-native selection mode was removed in AE-003;
`2` is rejected with `preflight_invalid:mode_not_0_or_1` and falls back to
mode 0. No environment variable, keyring, key file or `model.json` is a
runtime key or settings source. Every failure falls back to the default cards
for that turn with one stderr diagnosis line.
See [ADAPTIVE_PREFLIGHT.md](ADAPTIVE_PREFLIGHT.md) for the full contract,
protocols, deadlines, verification and the CONTRACT §8.5 deviation note.

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

- **Variable:** `INSTALL_SYSTEM_LAUNCHER`
  - **Purpose:** Setup-time only. `1` makes `setup.sh` symlink
    `/usr/local/bin/agent-enhanced` to `unified-integration/launch-agent.sh`.
    If that directory is not writable, setup warns and you use the
    repo-local launcher instead.
  - **Default:** `0` (no system-wide link)

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

The Python runtime lives at `<state dir>/runtime/venv`: by default
`<checkout>/.agentenhancements/runtime/venv`, or under
`AGENT_ENHANCEMENTS_STATE_DIR` when it is set (normal setup requires that
directory to be inside the checkout). XDG data settings do not move it.

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

- **Variable:** `AGENT_ENHANCEMENTS_API_FILE`
  - **Purpose:** Optional `ui.api.json` override for isolated tests (inside
    the checkout for normal installs)
  - **Default:** `<checkout>/ui.api.json`

- **Retired (CONTRACT v2.4 §8.2):**
  `AGENT_ENHANCEMENTS_MODEL_FILE` and `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY`
  are no longer read. Preflight settings and its key moved into
  `ui.api.json`; `api_config.py migrate` imports a legacy `model.json` /
  `preflight.key` once. Isolated tests use `AGENT_ENHANCEMENTS_API_FILE`.

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
Dependencies are installed into a checkout-local environment. Host bridges
use the stable `.agentenhancements/runtime/venv` path.
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

Setup prepares Python 3.11+ dependencies from a SHA-256 wheel lock. Each
verified environment records the lock digest, Python version, platform,
absolute path and installed package versions in its own `ae-runtime.json`.
Matching environments are reused. Newly prepared environments pass the
bundled stdio smoke test before the interpreter path changes.

In `api_config.py status`, a configured external command is eligible to
connect. Check the gateway and the host's live tool list for confirmed
availability. For a blocked package launcher, install the verified release
separately and set its local entry point in `mcp.<id>.command`.

Memory initialization creates private storage before SQLite opens it and
refuses a database symlink. Runtime/observer notes and audit text redact
recognized authentication fields and configured credentials. Authenticated
embeddings/vision requests refuse redirects. Public arXiv/news response
caches also use private storage below `AGENT_MEMORY_ROOT`.

Preflight Mode 1 (custom selector; historically Mode 2) transmits the bounded,
redacted user prompt and public capability metadata to the configured endpoint.
Redaction protects known
credential values and recognizable authentication patterns; it does not
classify every possible private source snippet. Mode 0 stays local.

## Checkout-local AE storage

AE-owned dependencies and state live under the active checkout's ignored
`.agentenhancements/` directory. Paths resolve from the installed source,
independently of the current working directory or global XDG settings:

- `runtime/venv/`: stable path to the active Python environment.
- `runtime/environments/`: verified environments and version records.
- `config/model.json`, `config/preflight.key`: legacy adaptive-selector
  files, imported once by `api_config.py migrate` and no longer read.
- `config/host-selection.json`: native host/profile preferences.
- `memory/`: SQLite session notes and the task-observer workspace.
- `cache/`: Python/uv/pip/npm/Cargo/model caches and temporary task workspaces.

The directory is private (0700); credentials and memory files remain0600.
`ui.api.json` (and its backups) stays ignored at the checkout root. It is
never copied from another checkout automatically. The `.gitignore` rule for a
personal `search_providers.json` remains only to protect that private file;
AE does not use it.

Native agent configuration is owned by the host application. Setup merges
only the AE bridge into that configuration: commands, hooks and symlinks
point at the active checkout and its local runtime. Moving a checkout
requires rerunning setup; old managed paths are refreshed while personal
plugins, credentials and approvals are preserved.

`AGENT_ENHANCEMENTS_STATE_DIR` is an optional absolute override for isolated
fixtures. Existing explicit memory/API overrides remain supported
(`AGENT_ENHANCEMENTS_MODEL_FILE` is retired, CONTRACT §8.2). The normal setup
command rejects state, memory, API or headroom overrides outside the
checkout. Isolated low-level fixture utilities keep their explicit override
support.
No global AE memory or model file is imported implicitly. Back up and
review old state before a deliberate migration; setup does not move or
remove user data. System Python, Node, Rust and agent CLIs are prerequisites,
not copies of AE plugin code.

Cargo build outputs resolve to `headroom/target` inside the checkout,
including when a caller has a global CARGO_TARGET_DIR. A normal install
rejects target/binary symlinks that leave the checkout. Audit/consent helper
logs retain their documented private `unified-integration/memory/audit/`
location; those logs also stay inside the checkout.

Repeated YAML merges preserve the original bytes, comments and quoting
when managed values already match. Backups are created for actual value
changes; normal CLI diagnostic logs may still grow on each invocation.
