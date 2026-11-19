# AgentEnhancements (AE) / ECC — Deep Engineering Audit

**Audit Date:** 2026-11-19  
**Scope:** Full codebase — `unified-integration/`, `ECC/`, `plugin-catalog/`, `agentic-awesome-skills/`, `superpowers/`, `ponytail/`, `headroom/`  
**Auditor:** Internal (AgentEnhancements self-audit)

---

## TL;DR

| Dimension | Rating | Summary |
|-----------|--------|---------|
| **Architecture** | ✅ **Strong** | Unified registry as single source of truth; fail-closed contracts; gateway MCP pattern; three-mode preflight with bounded fallbacks |
| **Code Quality** | ✅ **High** | Typed Python (dataclasses, protocols); comprehensive error handling; secret redaction; deadline-bounded async; no silent failures |
| **Security** | ✅ **Production-Grade** | No secrets in config; keyring/env/file for Mode 2; redaction before persist; DEFAULT_DISABLED for dangerous MCPs; path traversal guards |
| **Production Readiness** | ⚠️ **Mixed** | Core runtime solid; native workflow coverage thin (1 of 6 phases); skill auto-loading absent by design; three-layer catalog adds cognitive load |
| **Testing** | ❌ **Critical Gap** | No unit/integration test suite visible; `catalog-test.sh` only validates JSON schema; no CI pipeline evident |
| **Documentation** | ✅ **Comprehensive** | CONTRACT.md, SOUL.md, per-component docs, architecture guides — but scattered across ECC/docs/ and unified-integration/ |

---

## Key Findings

### ✅ What Works Well

1. **Unified Registry (`registry.py`)** — 1,144 lines of well-structured capability discovery with:
   - Multi-source aggregation (skills, plugins, MCPs, built-in capabilities)
   - Intent-aware scoring (EN/ID synonyms, format aliases, generic-action suppression)
   - Honest abstention on low-confidence queries (CARD_MIN_SCORE=5)
   - Budget-aware token clamping (`context_budget.py`)
   - Live readiness checks per entry type

2. **Adaptive Preflight (`adaptive_preflight.py`)** — CONTRACT 8.5 implementation:
   - Three modes (0=disabled, 1=host-native, 2=custom model) with explicit fallbacks
   - Mode 1 never auto-falls to Mode 2 (user choice respected)
   - Deadline-bounded (2s default, 8s max), max 2 inference rounds
   - Secret-safe: keys from env/keyring/0600 file only — never `model.json`
   - Structured output validation with exhaustive error codes

3. **Runtime (`runtime.py`)** — Shared lifecycle across Claude/Codex/OpenCode/Hermes:
   - SessionStart: observer bootstrap + memory recall (bounded)
   - UserPromptSubmit: preflight Modes 0/1/2 + memory save (redacted)
   - Pre/PostToolUse: bounded tool-name only, never raw bodies
   - Stop: summary save + observer backstop
   - All failures advisory — never block agent work

4. **MCP Gateway Pattern** — Single stable gateway (`agent-enhancements`) that:
   - Validates server visibility via `api_config.server_state()`
   - Injects env vars at runtime
   - Preserves user tool approvals/timeouts
   - Retires old direct entries on update

5. **Task Observer (`task-observer.py`)** — Vendored upstream skill with:
   - Redaction before persist (regex for GH tokens, AWS keys, generic secrets)
   - Workspace isolated from checkout (`~/.agent-memory/task-observer/`)
   - Staging/promotion for skill updates (never auto-applies)
   - Degraded non-blocking diagnostics

6. **Security-First Defaults**:
   - `DEFAULT_DISABLED = {"task-router-mcp"}` — dangerous servers opt-in only
   - Path traversal guards in `_file_under_roots()`
   - Duplicate key rejection in JSON parsing
   - Config size limits (1MB for ui.api.json, 64KB for model.json)
   - Redirect refusal in Mode 2 HTTP client

### ⚠️ Architectural Tensions

| Tension | Impact | Mitigation |
|---------|--------|------------|
| **Two orchestration layers** | ECC's hand-rolled `orch-pipeline` (main thread) + native `Workflow` tool (background) coexist; only `orch-review` ported | Documented as pilot; incremental migration planned |
| **Skill loading is opt-in** | Hooks only *suggest* skills; `Skill` tool must be called explicitly — no auto-load | Intentional (user control) but increases friction |
| **Three-layer catalog** | ECC agents + unified skills + plugin-catalog merged at registry build | Works but adds cognitive load; `library-map.json` helps |
| **ECC ≠ AE** | AE is the integration layer wrapping ECC (the product) | Clearer naming/boundaries needed |

### ❌ Critical Gaps

1. **No Test Suite** — Only `catalog-test.sh` (JSON schema validation). No unit tests for:
   - Registry scoring algorithm
   - Preflight mode transitions
   - Memory CRUD + TTL expiry
   - MCP gateway visibility logic
   - Task observer staging/promotion

2. **No CI Pipeline** — No GitHub Actions visible for lint/test/build

3. **Native Workflow Coverage** — 1 of ~6 orch-pipeline phases ported to native `Workflow` tool

4. **Observability** — Structured logs to stderr only; no metrics export (Prometheus/OTel)

---

## Recommendations Priority

| Priority | Action |
|----------|--------|
| **P0** | Add pytest suite covering registry, preflight, memory, api_config, runtime |
| **P0** | Add GitHub Actions CI (lint + test + typecheck) |
| **P1** | Port remaining orch-pipeline phases to native Workflow (Research → Plan → Implement → Gate 1 → Review → Gate 2) |
| **P1** | Add metrics export (cold-start tokens, preflight latency, fallback rates) |
| **P2** | Unify ECC/docs + unified-integration docs into single `/docs` tree |
| **P2** | Add `skill:auto-load` opt-in capability for reduced friction |
| **P3** | Consider merging plugin-catalog into unified registry build (single source) |

---

## File Index

| Audit File | Scope |
|------------|-------|
| `UNIFIED_INTEGRATION_AUDIT.md` | `unified-integration/scripts/*.py`, `*.sh` |
| `ECC_CORE_AUDIT.md` | `ECC/agents/`, `ECC/skills/`, `ECC/commands/`, `ECC/workflows/`, `ECC/docs/` |
| `PLUGIN_CATALOG_AUDIT.md` | `plugin-catalog/catalog.json`, `mcp-servers.json`, plugin guides |
| `SKILLS_ECOSYSTEM_AUDIT.md` | `agentic-awesome-skills/`, skill loading/linking |
| `SECURITY_AUDIT.md` | Secret handling, path guards, MCP gating, redaction |
| `TESTING_GAPS.md` | Missing test coverage, CI absence |
| `ARCHITECTURAL_DECISIONS.md` | Key design choices with rationale |
| `RECOMMENDATIONS.md` | Prioritized action items with effort estimates |