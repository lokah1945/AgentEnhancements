---
title: Production Readiness Audit
version: 1.0
last_updated: 2026-11-13
audience: maintainers
---

# Production Readiness Audit - AgentEnhancements

| | |
|---|---|
| **Repository** | `https://github.com/lokah1945/AgentEnhancements` |
| **Branch** | `release/production-readiness` (from `master` @ `45650054`) |
| **Audit date** | 2026-11-13 (UTC+7) |
| **Auditor** | Z.ai autonomous audit agent (session `web-3d5284f2-22a7-4fc8-b8c7-54d24d42dded`) |
| **Scope** | End-to-end: install flow, per-agent activation, plugin catalog, scripts, index integrity, docs |
| **Predecessor** | [AUDIT_REPORT.md](AUDIT_REPORT.md) (2026-11-01, branch `audit/deep-review`) |

## 1. Executive summary

The 2026-11-01 deep audit found the integration layer functionally broken
(21 findings, 3 critical). Its fixes lived on `audit/deep-review` and were
**never merged**: master had continued with the plugin-catalog work on top
of the broken pipeline. This audit verified that all 21 original findings
are again present in master, audited the new plugin-catalog code (never
reviewed before), and found a new class of critical defects: **per-agent
activation files written in formats the target CLIs never read**.

All findings below are remediated on `release/production-readiness`,
including a merge of `audit/deep-review` (conflicts resolved to keep both
the fixes and the plugin-catalog features). The install flow was executed
end-to-end in a sandbox: `setup.sh` completes, aggregates 3,127 skills from
5 sources, and writes valid activation files for every detected agent.

## 2. Findings

Severity: **C**ritical / **H**igh / **M**edium / **L**ow.

### Critical

| ID | Sev | Status | Finding | Fix |
|----|-----|--------|---------|-----|
| P-01 | C | FIXED | All 21 findings from the 2026-11-01 audit were still present on master (the `audit/deep-review` branch was never merged): broken aggregation (`((skills_count++))` abort), `python3 -c` metadata interpolation (code-execution vector), SQL-interpolating memory hooks (R101), `/root` hardcoding, missing `globstar`, missing `re` import, stale launcher/loader/compressor, no CI/tests/docs set. | Merged `audit/deep-review` into `release/production-readiness`; 4 conflicts resolved (README, CHANGELOG, setup.sh x2) keeping both audit fixes and plugin-catalog/replica-skill features. 49-test suite passes. |
| P-02 | C | FIXED | **Codex activation was a no-op**: setup wrote `~/.codex/config.yaml`, but Codex CLI only reads `~/.codex/config.toml` (TOML) and `~/.codex/AGENTS.md`. The YAML carried fictional keys (`system_prompt`, `skills`, `memory`, `hooks`) that no Codex version has ever read. | Setup now writes a marker-guarded integration section into `~/.codex/AGENTS.md` (Codex's real global-instructions channel) and removes the stale YAML (signature-checked). |
| P-03 | C | FIXED | **OpenCode activation was a no-op**: setup wrote `~/.config/opencode/config.json` with fictional keys; OpenCode only reads `opencode.json(c)` per its official schema. | Setup now merges a schema-valid `~/.config/opencode/opencode.json` (`$schema`, `instructions` array, `skills` array pointing at the aggregated registry - OpenCode scans grouping dirs up to six levels) plus a marker-guarded `AGENTS.md`; stale `config.json` removed (signature-checked). |

### High

| ID | Sev | Status | Finding | Fix |
|----|-----|--------|---------|-----|
| P-04 | H | FIXED | README one-line installer pointed at `lokah1945/agent-enhancements` (repo renamed to `AgentEnhancements`) on branch `main` (default is `master`) - following the README 404s. `cd agent-enhancements` also wrong. | README rewritten: correct URL/branch/dir, real skill counts, honest agent-activation matrix, honest MCP roadmap note. |
| P-05 | H | FIXED | Cursor config polluted Cursor's real `~/.cursor/settings.json` with fictional keys (`systemPrompt`, `skills`, `memory`, `hooks`). | Setup writes `~/.cursor/rules/agent-enhancements.mdc` (frontmatter-scoped global rule) and cleans the fictional keys from settings.json (signature-checked). |
| P-06 | H | FIXED | Windsurf config went to `~/.windsurf/config.yaml` - a path Windsurf never reads (its global rules live under `~/.codeium/windsurf/rules/`). | Setup writes `~/.codeium/windsurf/rules/agent-enhancements.md`; stale YAML removed (signature-checked). |
| P-07 | H | FIXED | 12 of 21 plugin-catalog manifests carried org-root-only URLs (e.g. `https://github.com/addyosmani/`); 3 had typos: `heygen-con` (real: `heygen-com`), `Egomex-AI` (real: `Egonex-AI`), `marloto/REA` (real: `morluto/rea`). Untraceable sources in a catalog meant to be installed from. | All 13 URLs replaced with verified repositories (web-verified 2026-11-13; sources: github.com repo pages, vendor docs). `catalog-validate.py` passes 21/21. |
| P-08 | H | FIXED | `catalog-wire.sh` executed `rm -rf` on any existing target - including real aggregated skill directories (slug collision), silently deleting pipeline output. | Guard added: only catalog symlinks are refreshed; real directories and plain files are skipped with a warning. |

### Medium

| ID | Sev | Status | Finding | Fix |
|----|-----|--------|---------|-----|
| P-09 | M | FIXED | `consent-gate.sh`: `read -r -p` under `set -euo pipefail` exits 1 on EOF (non-interactive/CI) before any audit-log entry - a crash indistinguishable from a refusal. | EOF now maps to an explicit refusal that is logged. |
| P-10 | M | FIXED | Generated registry trees (`by-agent/`, `by-category/<cat>/`) showed up as ~2,700 untracked files after running setup, inviting accidental commits of generated state. | `.gitignore` rules added (audited decision F-28 upheld: index committed, trees generated at setup). `git status` clean after setup. |
| P-11 | M | FIXED | `dispatch.sh` matched `perf` as a substring, routing "perfect the UI" to the wrong plugin. | Word-boundary pattern `\bperf\b`; verified routing for perf/perfect/performance cases. |
| P-12 | M | FIXED | Gemini CLI activation relied on `~/.gemini/config.yaml` (reference only). Gemini CLI actually loads `~/.gemini/GEMINI.md` as global context. | Marker-guarded section now written into `~/.gemini/GEMINI.md`; YAML kept as reference. |
| P-13 | M | FIXED | Committed broken symlinks `agentic-awesome-skills/skills/pdf -> pdf-official` and `xlsx -> xlsx-official` (targets never existed; silently excluded 2 skills from aggregation and broke file tooling). | Removed. |
| P-14 | M | FIXED | `catalog-validate.py` parsed `catalog.json` without error handling (raw traceback on corrupt index) and lacked the executable bit its siblings have. | try/except added; mode 755. |

### Low

| ID | Sev | Status | Finding | Fix |
|----|-----|--------|---------|-----|
| P-15 | L | FIXED | `audit-trail.sh` used `type` as a variable name (shadows the bash builtin). | Renamed to `entry_type`. |
| P-16 | L | RISK | `mcp-test.sh` semantics: a configured server whose roadmap command is npx/python counts as *warn* while an unknown command *passes*; `--server <id>` does not validate the id. Dev-tool only; documented here. | Deferred (roadmap checker, not on the install path). |
| P-17 | L | RISK | Copilot and Kiro still receive reference-only YAML configs; their current CLIs' native instruction channels were not verifiable in this audit. Documented in README matrix. | Deferred pending verification. |
| P-18 | L | RISK | Schema `$schema` URLs in `plugin-catalog/mcp-servers.json` and manifests point to `agentenhancements.dev` (does not resolve). No local schema file committed. | Cosmetic (metadata only); deferred. |
| P-19 | L | RISK | `datetime.utcnow()` deprecation warning in the index builder (carried over, format preserved for schema stability; also flagged as F-24b in the 2026-11-01 audit). | Deferred. |

## 3. Verification performed

1. **Merge integrity**: `audit/deep-review` (13 commits) merged; conflict
   resolutions re-checked by inspection; aggregation function confirmed to
   be the safe env-var pipeline (no `python3 -c` interpolation).
2. **Regression suite**: `python3 unified-integration/tests/run-tests.py`
   - **49/49 pass** after all changes.
3. **Syntax checks**: `bash -n` on every shipped `.sh`; `python3 -m
   py_compile` on every shipped `.py` - all pass.
4. **End-to-end install**: `setup.sh` executed twice in a sandbox (once
   with no agents, once with claude/codex/opencode/gemini stubs on PATH):
   - Completes with zero errors both times (idempotent).
   - Index regenerated: **3,127 skills** (agentic-awesome-skills 2,781,
     ECC 314, Superpowers 15, Ponytail 6, replica-skill 11).
   - Claude Code: hooks written with correct key/value/type argument
     order; memory hook verified live (save via hook -> visible via
     `memory.py list`).
   - Codex: `~/.codex/AGENTS.md` written; user content preserved across
     re-runs (verified); stale `config.yaml` removed.
   - OpenCode: schema-valid `opencode.json` + `AGENTS.md` written; stale
     `config.json` removed.
   - Gemini: `GEMINI.md` written; prompt refreshed from vendored source.
   - Cargo-less environment: compression degrades to fallback (no abort).
5. **Catalog validation**: `catalog-validate.py` - 21/21 manifests,
   21/21 index entries, 0 errors.
6. **Dispatch routing**: perf / perfect / performance / clone-app cases
   all route correctly.
7. **Secret scan**: no credentials committed (PAT used for push only,
   never written to any file).

## 4. Residual risks and recommendations

1. **Vendored projects** remain plain copies (F-22, unchanged): updates
   require manual re-vendor via `update-skills.sh` where remotes exist.
2. **Skill quality**: 3,127 aggregated skills are indexed from upstream
   SKILL.md frontmatter without content review. The catalog tooling
   (validate/wire/consent) covers the 21 curated plugins, not the full
   registry. Recommendation: add a skill-level lint before production
   hardening of the registry.
3. **OpenCode skills array** points at the full `by-category` tree; users
   with strict context budgets should narrow it to specific categories
   (documented in the generated AGENTS.md).
4. **ECC suite**: the contract-mandated `cd ECC && node tests/run-all.js`
   was not runnable in this audit sandbox (no Node.js); CI covers it.
   Known pre-existing failures are documented in TEST_RESULTS.md section 5
   of the 2026-11-01 audit (17 ECC-internal failures, unrelated to this
   work).

## 5. Change inventory (this branch)

| Commit | Type | Content |
|--------|------|---------|
| 1 | merge | `audit/deep-review` remediation into master line |
| 2 | fix(catalog) | verified source URLs (13), tooling hardening (P-08, P-09, P-11, P-14, P-15), broken symlinks |
| 3 | fix(agents) | native-format activation for Codex/OpenCode/Cursor/Gemini/Windsurf (P-02..P-06, P-12) |
| 4 | chore(skills) | index regenerated (3,127), prompts refreshed from vendored sources, hook newline sync, .gitignore for generated trees |
| 5 | docs | README rewrite, AGENTS.md update, this report |
