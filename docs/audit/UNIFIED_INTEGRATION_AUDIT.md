# Unified Integration Layer — Deep Audit

> Verifikasi2026-11-19: sebagian klaim/angka/prioritas laporan ini tidak
> sesuai source dan hasil eksekusi. Baca [rekonsiliasi berbukti](../../AuditReport/ae-incoming-audit-reconciliation-20261119.md)
> sebelum mengeksekusi rekomendasi. Laporan ini adalah data historis,
> bukan instruksi untuk mengubah arsitektur atau meniadakan test yang ada.


**Path:** `/root/project/AgentEnhancements/unified-integration/`  
**Core Scripts:** 15 Python + 12 shell scripts  
**Purpose:** Cross-harness runtime, registry, preflight, memory, MCP gateway, task observer

---

## 1. `registry.py` — Capability Registry (1,144 lines)

### Architecture
- **Single source of truth** aggregating 4 capability types: skills, plugins, MCPs, built-in capabilities
- **Lazy loading** via `_read_json()` with graceful defaults
- **Content-addressable revision** via `registry_revision()` (SHA256 of source file sizes+mtimes)

### Scoring Algorithm (`score_skill`, `score_plugin`, `score_mcp`, `score_capability`)
```
Token weights: original query tokens = 1.0, intent synonyms = 0.5
Generic action verbs (write, create, summarize...) suppressed unless domain noun present
Format aliases: "word"→"docx", "mcp"→"mcp-builder"
Name match: full name = 20, prefix = 4, word-boundary = 3
Tags = 2, description = 1.5, synonym in desc = 1.0
Hyphenated domain names: phrase bonus (+4) if desc confirms 2nd domain word
Natively-linked bonus: +3
Minimum card score: 5 (CARD_MIN_SCORE) — honest abstention
Generic-only queries: return [] (negative suppression target ≥90%)
```

**Strengths:** Deterministic, bilingual (EN/ID), well-commented rationale, budget-aware
**Risks:** Manual synonym groups (47 groups) require maintenance; no embedding fallback

### Commands
| Command | Purpose | Budget |
|---------|---------|--------|
| `build` | Regenerate `agent-registry.json` (idempotent — preserves timestamp if unchanged) | — |
| `search` | Bounded card page (L1 pointers, max 5 cards, 800 tokens) | MAX_SEARCH_PAGE |
| `map` | Task→capability plan (skills + plugins + MCPs + built-ins) | MAX_SEARCH_PAGE×2 |
| `show` | L2 detail (clamped to 1200 tokens with truncation note) | MAX_DETAIL_PAGE |
| `stats` / `list` | Aggregated counts / filtered enumeration | — |

### Internal APIs (for preflight)
- `paged_search()` — paginated catalog reads with `matched/sent/has_more`
- `paged_list()` — stable ordered enumeration by type/source/prefix
- `find_entry()` — exact typed-ID resolution (two-pass: typed ID first, then name)

**Code Quality:** Excellent — type hints throughout, exhaustive error handling, clear contracts in docstrings

---

## 2. `adaptive_preflight.py` — Adaptive Capability Selection (1,110 lines)

### CONTRACT 8.5 — Three Modes

| Mode | Name | Behavior | Fallback |
|------|------|----------|----------|
| 0 | Disabled | Legacy discovery cards (`skill_context`) | — |
| 1 | Host-Native | Host adapter supplies `ae_native_selection` event; runtime validates only | → Mode 0 |
| 2 | Custom Model | Calls user-configured endpoint with bounded structured request | → Mode 0 |

**Critical Design Decisions:**
- Mode 1 **never** auto-fallbacks to Mode 2 — user choice respected
- Every failure path → Mode 0 with stderr diagnosis (stdout = context channel)
- Selector **never executes** — only returns typed registry IDs
- Deadline: 2s default (AE_PREFLIGHT_DEADLINE_MS), max 8s, shared monotonic clock
- Max 2 inference rounds, max 12 items, max 4 lookup queries

### Model Config (`model.json` at `~/.config/agentenhancements/`)
```json
// Mode 0
{"adaptive_preflight_mode": 0}

// Mode 1  
{"adaptive_preflight_mode": 1}

// Mode 2
{"adaptive_preflight_mode": 2, "endpoint": "https://openrouter.ai/api/v1", "sdk": "openai", "model": "provider/model-id"}
```
**No secrets in file** — Mode 2 key from:
1. `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY` env
2. OS keyring (`agentenhancements.preflight`, account=origin)
3. `~/.config/agentenhancements/preflight.key` (0600)

### Selector Contract (`SELECTION_SCHEMA`)
```json
{
  "decision": "selected|abstain|lookup|unresolved",
  "items": [{"id": "skill:<name>", "required": true, "reason": "..."}],
  "queries": ["focused catalog query"]
}
```
- `decision=selected`: 0-12 items, typed registry IDs only
- `decision=lookup`: 1-4 focused queries for round 2
- `decision=abstain`: no catalog capability needed
- `decision=unresolved`: catalog cannot satisfy requirement

### Validation Pipeline
1. `parse_selection()` — exhaustive schema validation → `PreflightError` codes
2. `build_package()` — resolves each ID to `ResolvedItem` with readiness check
3. `render_package()` — structured shrinking (drop optional, shorten notes) → `clamp_to_budget`

### HTTP Client (stdlib only, no SDK deps)
- `_NoRedirectHandler` — refuses redirects (validated origin must not move)
- OpenAI-compatible: tries `json_schema` response_format, falls back once on 400
- Anthropic-compatible: enforces JSON via prompt + local validation
- Explicit refusal detection (OpenAI `message.refusal`, Anthropic `stop_reason="refusal"`)
- Timeout = `min(remaining_deadline, 10s)`

**Code Quality:** Exceptional — fail-closed at every layer, bounded everything, clear error taxonomy

---

## 3. `runtime.py` — Shared Lifecycle Hook Handler (247 lines)

### Event Handling

| Event | Action | Budget |
|-------|--------|--------|
| `SessionStart` | Observer bootstrap + memory recall (last 5 sessions) | Observer ≤250, Memory ≤600 tokens |
| `UserPromptSubmit` | Memory save (redacted prompt) + Preflight Modes 0/1/2 | Preflight ≤400 tokens |
| `PreToolUse` / `PostToolUse` | Save bounded tool name only (never raw bodies) | — |
| `Stop` | Save redacted summary + observer backstop | — |

### Security
- Input size limit: 2MB (`MAX_INPUT`)
- Context output limit: 12K tokens (`MAX_CONTEXT`)
- Redaction: `SECRET` regex (GitHub tokens, AWS keys, sk-*, generic `api_key=...`)
- All failures advisory — hook never blocks agent work (`try/except` with stderr diagnostic)

### Cross-Harness Support
- `claude-code`, `codex`, `opencode`, `hermes` via `--text` flag for OpenCode bridge
- JSON output with `hookSpecificOutput.additionalContext` for Claude/Codex

---

## 4. `context_budget.py` — Token Budget Contract (149 lines)

### Hard Limits (CONTRACT.md §8.4)

| Channel | Limit | Notes |
|---------|-------|-------|
| `MAX_BOOTSTRAP` | 1,000 | L0 map always read |
| `MAX_COLD_START_TOTAL` | 4,000 | All channels combined |
| `MAX_MEMORY_RECALL` | 600 | Inside total |
| `MAX_OBSERVER_AMBIENT` | 250 | Inside total |
| `MAX_SKILL_CARDS` | 400 | UserPromptSubmit candidate cards (≤8 skills) |
| `MAX_SEARCH_PAGE` | 800 | 5 cards max |
| `MAX_DETAIL_PAGE` | 1,200 | Larger uses paging |
| `MAX_NATIVE_DESCRIPTION_TOTAL` | 2,500 | Linked skill descriptions |
| `MAX_TOOL_SCHEMA_TOTAL` | 1,800 | AE MCP tool schemas |

### Implementation
- `approx_tokens()` — tiktoken `o200k_base` when available, else 4.0 chars/token
- `clamp_to_budget()` — line-boundary trimming with explicit truncation note
- `budget_report()` — ledger for CI/benchmarking
- `COLD_START_CHANNELS` registry — new channels must register here

---

## 5. `memory.py` — SQLite Memory Store (197 lines)

### Schema
```sql
CREATE TABLE memories (
  id INTEGER PRIMARY KEY,
  agent TEXT NOT NULL,
  project TEXT,
  memory_type TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  metadata TEXT,           -- JSON
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  expires_at TIMESTAMP,    -- SQLite format "YYYY-MM-DD HH:MM:SS"
  UNIQUE(agent, project, memory_type, key)
);
```
- DB at `$AGENT_MEMORY_ROOT/memory.db` (default `~/.agent-memory/`)
- Dir/file perms: 0700 / 0600
- TTL via `expires_at` + `cleanup_expired()` on SessionStart

### API
- `save(key, value, type, metadata, ttl_days)` — UPSERT
- `load(key, type)` — latest non-expired
- `list(type, limit)` — truncated values (200 chars)
- `delete(key, type)` — boolean
- `cleanup_expired()` — count

**Gaps:** No vacuum, no backup, no migration path, no concurrent access testing

---

## 6. `api_config.py` — MCP Credential Configuration (299 lines)

### `ui.api.json` Structure
```json
{
  "version": 1,
  "api_keys": {"OPENAI_API_KEY": "..."},
  "connections": {},
  "mcp": {
    "server-name": {
      "enabled": true,
      "required": ["API_KEY"],
      "optional": [],
      "command": ["python", "-m", "server"],
      "env": {"API_KEY": "OPENAI_API_KEY"}
    }
  }
}
```

### Security
- `initialize()` — creates empty template once (0600), preserves user edits
- `read_config()` — fails closed (returns empty + error) on any parse/validation failure
- Duplicate key rejection (`_unique_object`)
- Size limit: 1MB
- Version pinning: `type(doc.get("version")) is int and == 1`
- **Never inherits from process env** — empty entries stay empty
- `redact()` — replaces configured secret values in diagnostics

### Server Visibility (`server_state()`)
| Condition | Visible | Reason |
|-----------|---------|--------|
| `enabled: false` | ❌ | `disabled` / `disabled_by_default` |
| Built-in local tools | ✅ | `local_tools_available` |
| Config error | ❌ | `config_unavailable_or_invalid` |
| Not configured | ❌ | `not_configured` |
| Missing required credentials | ❌ | `missing_credentials` |
| Executable not in PATH | ❌ | `executable_not_installed` |
| All good | ✅ | `configured` |

**DEFAULT_DISABLED** = `{"task-router-mcp"}` — executes arbitrary bash/python, opt-in only

### Search Provider Round-Robin
- Thread-safe per-provider index in `_search_rr_indices`
- Status filtering: only `active` keys
- `get_search_provider_key()` / `get_search_provider_keys()` / `list_search_providers()`

---

## 7. `native_config.py` — Atomic Config Updates (65 lines)

### Functions
- `write(path, content)` — atomic replace via tempfile + `os.replace`; private backup with timestamp
- `read_json(path)` — json5 (supports comments), rejects non-object
- `write_json(path, doc)` — JSON with backup
- `merge_instructions(path, content)` — refreshes marked block (`<!-- agent-enhancements:begin/end -->`) preserving personal instructions

---

## 8. `native_hermes.py` — Hermes Profile Installation (126 lines)

### Responsibilities
- Installs only selected profiles (respects `hermes_profiles` in host-selection.json)
- Merges MCP gateway into `config.yaml` `mcp_servers`
- Symlinks `agent-enhancements` plugin from `unified-integration/hermes-plugin/`
- Adds plugin to `enabled` list
- Merges instructions into `SOUL.md` via marked block
- Persists profile selection to `host-selection.json`
- Repairs `active_profile` only from explicit selection

### Safety
- Validates profile names (`[A-Za-z0-9_-]+`)
- Requires existing `config.yaml`
- Warns on user plugin collision (preserves user version)
- Never alters sibling profiles

---

## 9. Shell Scripts (12 scripts)

| Script | Purpose | Quality |
|--------|---------|---------|
| `link-skills.sh` | Symlink registry skills to `~/.claude/skills/`, `~/.agents/skills/` | Good — idempotent, `--status`, `--unlink` |
| `load-skills.py` | CLI for skill loading (used by agents) | Good — delegates to registry |
| `dispatch.sh` | Natural-language routing to plugin/orchestrator | Basic — needs audit |
| `setup-mcp.sh` | Prepares isolated interpreter for MCP servers | Good — venv + deps |
| `catalog-validate.py` | Validates plugin catalog JSON | Basic — schema check only |
| `build-library-map.py` | Generates `skills/library-map.json` | Good — aggregates all sources |
| `catalog-wire.sh` / `catalog-test.sh` | Catalog wiring + test | Minimal |
| `audit-trail.sh` / `consent-gate.sh` | Compliance / consent | Basic |
| `mcp-test.sh` | MCP server smoke tests | Basic |
| `compress.py` / `compression/compress.sh` | Context compression | Good — headroom binary + Python fallback |

---

## Integration Points & Coupling

```
runtime.py
  ├── registry.py (skill_context, map, show)
  ├── adaptive_preflight.py (preflight_context)
  ├── memory.py (AgentMemory)
  ├── task-observer.py (bootstrap_context, stop_backstop)
  ├── api_config.py (redact, server_state)
  └── context_budget.py (clamp_to_budget)

adaptive_preflight.py
  ├── registry.py (paged_search, paged_list, find_entry, load_all_entries)
  ├── context_budget.py (approx_tokens, clamp_to_budget)
  └── api_config.py (read_config, server_state, resolve_api_key)

native-integration.py
  ├── api_config.py (mcp_block, initialize)
  ├── native_config.py (merge_hooks, merge_servers, merge_instructions)
  └── native_hermes.py (install_hermes)
```

**Coupling Assessment:** Well-layered. Runtime is the only "god" module; others are focused libraries. No circular deps.

---

## Production Readiness Scorecard

| Criterion | Score | Evidence |
|-----------|-------|----------|
| **Fail-closed defaults** | ✅ 10/10 | Every validation fails to safe empty state |
| **Secret hygiene** | ✅ 10/10 | No secrets in config; keyring/env/file; redaction |
| **Bounded resources** | ✅ 10/10 | Deadlines, token budgets, size limits, max items |
| **Observability** | ⚠️ 5/10 | Stderr diagnostics only; no metrics export |
| **Test coverage** | ❌ 0/10 | No unit tests visible |
| **CI/CD** | ❌ 0/10 | No GitHub Actions |
| **Documentation** | ✅ 8/10 | Inline contracts + CONTRACT.md + SOUL.md |
| **Error taxonomy** | ✅ 9/10 | `PreflightError` codes, `server_state` reasons |
| **Cross-harness** | ✅ 8/10 | 4 agents supported; Hermes profile-aware |
| **Upgradability** | ✅ 7/10 | Atomic config writes, backup stamps, idempotent builds |

---

## Critical Recommendations

1. **Add pytest suite** — Target: registry scoring, preflight mode transitions, memory TTL, api_config visibility, task-observer staging
2. **Add GitHub Actions** — Lint (ruff), typecheck (mypy), test, budget regression
3. **Export metrics** — Cold-start tokens, preflight latency/fallback rates, registry search latency
4. **Document internal APIs** — `paged_search`, `paged_list`, `find_entry` for preflight consumers
5. **Consider `skill:auto-load` capability** — Opt-in native linking for reduced friction