# Prioritized Recommendations — Deep Audit

**Methodology:** Impact × Effort matrix; P0=do now, P1=next sprint, P2=next quarter, P3=backlog

---

## Priority Matrix

| Priority | Criteria | Count |
|----------|----------|-------|
| **P0** | Critical security, data loss, production blocker, < 1 week | 6 |
| **P1** | High impact, medium effort, improves reliability/velocity | 10 |
| **P2** | Medium impact, architectural, enables future work | 8 |
| **P3** | Nice-to-have, polish, developer experience | 5 |

---

## P0 — Critical (Do This Week)

### P0-1: Add GitHub Actions CI Pipeline
**Impact:** 🔴 Critical | **Effort:** 2-3 days | **Owner:** Platform
**Why:** Zero CI = no regression detection, no automated validation, no confidence in merges
**What:**
- `.github/workflows/ci.yml`: lint (ruff, shellcheck), typecheck (mypy), test (pytest), security (gitleaks, pip-audit)
- `.github/workflows/registry.yml`: rebuild registry on catalog changes, validate schema
- `.github/workflows/ecc.yml`: ECC test suite (Node + Python)
- Required status checks on main branch

**Acceptance:** All PRs pass CI; main branch protected; badge in README

### P0-2: Refactor `hooks.json` Bootstrap Duplication
**Impact:** 🔴 Critical | **Effort:** 1-2 days | **Owner:** ECC Core
**Why:** 5,600+ lines duplicated; attack surface; maintenance nightmare; no integrity verification
**What:**
- Extract bootstrap to `scripts/hooks/run-with-flags.js` (already exists)
- Update all 20+ hook entries to use shared module
- Add SHA256 integrity check on bootstrap module
- Test across all 4 harness installers

**Acceptance:** `hooks.json` < 500 lines; all harnesses install correctly; `bash -n` passes

### P0-3: Least Privilege for ECC Agents
**Impact:** 🔴 Critical | **Effort:** 3-5 days | **Owner:** ECC Core
**Why:** ~40% agents use `tools: "*"` — violated least privilege; blast radius = all tools
**What:**
- Audit each of 71 agents
- Declare explicit tool lists based on actual usage
- Test each agent with restricted tools
- Document tool requirements per agent

**Acceptance:** Zero agents with `tools: "*"`; all agent tests pass

### P0-4: Test Adaptive Preflight (Zero Coverage)
**Impact:** 🔴 Critical | **Effort:** 5-7 days | **Owner:** AE Core
**Why:** 1,110 lines of critical orchestration code with **0 tests**; mode transitions, fallback, HTTP client untested
**What:**
- Unit tests for every function in `adaptive_preflight.py`
- Integration tests for Mode 0/1/2 transitions
- Mock HTTP tests for OpenAI/Anthropic clients
- Fallback diagnosis code coverage

**Acceptance:** >90% coverage on `adaptive_preflight.py`; all mode transitions tested

### P0-5: Test Registry Scoring Algorithms
**Impact:** 🔴 Critical | **Effort:** 3-4 days | **Owner:** AE Core
**Why:** Core discovery logic untested; regressions silent; scoring determines agent capability
**What:**
- Property-based tests (hypothesis) for `score_skill`, `score_plugin`, `score_mcp`, `score_capability`
- Golden master tests for known queries
- Edge cases: generic suppression, synonym expansion, hyphenated phrases, natively-linked bonus
- `CARD_MIN_SCORE` abstention behavior

**Acceptance:** >85% coverage on scoring functions; all fixtures pass

### P0-6: Add Supply Chain Scanning
**Impact:** 🔴 Critical | **Effort:** 1-2 days | **Owner:** Platform
**Why:** No SBOM, no dependency audit, no vulnerability detection
**What:**
- `pip-audit` in CI for Python deps
- `npm audit` for Node deps (ECC, agent_browser)
- `cargo deny` for Rust (ECC2) — already has deny.toml
- `gitleaks`/`trufflehog` for secret scanning
- SBOM generation (CycloneDX) for all components

**Acceptance:** CI fails on high/critical vulns; SBOM artifact on every release

---

## P1 — High Impact (Next Sprint)

### P1-1: Complete Native Workflow Migration (Phases 1-3)
**Impact:** 🟠 High | **Effort:** 2-3 weeks | **Owner:** ECC Core
**Why:** Only 1 of 6 phases ported; hand-rolled pipeline lacks determinism, resumability, structured output
**What:**
- Phase 1: Research → multi-modal sweep (parallel agents, completeness critic)
- Phase 2: Plan → judge panel (N approaches, parallel judges, synthesis)
- Phase 3: Implement → subagent dispatch (pipeline, structured output)
- Keep Gates 1/2 in main conversation

**Acceptance:** All phases runnable as native workflows; parity with hand-rolled output

### P1-2: Test Context Budget Enforcement
**Impact:** 🟠 High | **Effort:** 1 week | **Owner:** AE Core
**Why:** Budget contract central to AE; `context_budget.py` has 0 tests; clamping behavior unverified
**What:**
- Token counting accuracy (tiktoken vs fallback)
- `clamp_to_budget` line-boundary trimming + truncation note
- Channel budget ledger (`COLD_START_CHANNELS`)
- Regression tests for 4000 token cold-start limit

**Acceptance:** >90% coverage; budget regression detected in CI

### P1-3: Skill Versioning & Dependency Graph
**Impact:** 🟠 High | **Effort:** 1-2 weeks | **Owner:** AE Core
**Why:** No versioning = no upgrades, no deprecation, no reproducibility; no deps = manual composition
**What:**
- Add `version` field to SKILL.md frontmatter (semver)
- Add `depends_on: [skill-a, skill-b]` machine-readable
- Registry build validates dependencies, detects cycles
- `registry.py show` displays dependency tree
- Migration guide for existing skills

**Acceptance:** All 314 ECC skills versioned; dependency graph validated in CI

### P1-4: Automate Skill Categorization
**Impact:** 🟠 High | **Effort:** 1 week | **Owner:** AE Core
**Why:** 36% skills in "other" category; manual maintenance impossible at 3,127 skills
**What:**
- Train lightweight classifier (TF-IDF + logistic regression) on skill descriptions/tags
- Or improve keyword rules with domain-specific dictionaries
- Run categorization at registry build; flag low-confidence for review
- Target: "other" < 10%

**Acceptance:** "other" category < 10%; categorization runs in CI

### P1-5: Add MCP Health Endpoints & Install Verification
**Impact:** 🟠 High | **Effort:** 1 week | **Owner:** AE Core
**Why:** 10 built MCPs have no health checks; 60 to-install unverified post-install
**What:**
- Add `/health` endpoint to all 10 built MCP servers
- Post-install smoke test in `setup-mcp.sh` (tools/list + tools/call ping)
- Health check in gateway `tools/list` (mark unhealthy)
- CI job: verify all built MCPs respond to health check

**Acceptance:** All built MCPs have `/health`; install verifies each MCP

### P1-6: Fix `agent_browser` Path Inconsistency
**Impact:** 🟠 High | **Effort:** 1 day | **Owner:** AE Core
**Why:** Uses `mcp-servers/agent_browser/` not `unified-integration/mcp-servers/` — breaks patterns
**What:**
- Move to `unified-integration/mcp-servers/agent_browser/`
- Update `mcp-servers.json` implementation path
- Update installers/scripts referencing old path
- Test gateway loads correctly

**Acceptance:** Consistent path; all installers work; gateway publishes tools

### P1-7: Unify Documentation Tree
**Impact:** 🟠 High | **Effort:** 3-5 days | **Owner:** Docs
**Why:** Docs split across `ECC/docs/`, `unified-integration/`, root — no single source
**What:**
- Consolidate into `/docs` at repo root
- Redirect old paths
- Single `mkdocs.yml` / `docsify` config
- Automated link checking in CI
- Freshness check (warn if > 90 days unmodified)

**Acceptance:** Single doc site; all links valid; freshness CI passes

### P1-8: Add Metrics Export (Observability)
**Impact:** 🟠 High | **Effort:** 1 week | **Owner:** Platform
**Why:** No visibility into cold-start tokens, preflight latency, fallback rates, skill usage
**What:**
- Structured JSON logs to stderr (existing) + optional file/OTel
- Key metrics: `cold_start_tokens`, `preflight_latency_ms`, `fallback_rate`, `skill_load_count`, `registry_search_latency`
- `doctor.py` report includes metrics summary
- Grafana dashboard template (optional)

**Acceptance:** Metrics emitted; `doctor.py` shows summary; dashboard works

### P1-9: E2E Test with Real Agent (Claude Code in Container)
**Impact:** 🟠 High | **Effort:** 1 week | **Owner:** Platform
**Why:** No validation that full stack works end-to-end
**What:**
- Dockerfile with Claude Code + AE installed
- Test script: SessionStart → UserPromptSubmit → skill discovery → load → execute → Stop
- Verify hooks fire, memory persists, registry works, MCP gateway responds
- Run in CI (or nightly)

**Acceptance:** E2E passes in container; catches integration regressions

### P1-10: Wire Orchestrators into Runtime
**Impact:** 🟠 High | **Effort:** 3-5 days | **Owner:** AE Core
**Why:** 3 orchestrators (bmad-method, gsd, rea) listed in catalog but not invokable
**What:**
- Add orchestrator routing to `dispatch.sh` / registry
- `registry.py map` includes orchestrators when task matches
- `orchestrator` capability type in registry
- Documentation on when to use each

**Acceptance:** Orchestrators discoverable and invokable via standard flow

---

## P2 — Medium Impact (Next Quarter)

### P2-1: Skill Auto-Load Opt-In Capability
**Impact:** 🟡 Medium | **Effort:** 1-2 weeks | **Owner:** AE Core
**Why:** Opt-in loading adds friction; power users want zero-friction
**What:**
- New capability: `capability:auto-load` (opt-in via config)
- When enabled: top-3 scored skills auto-loaded via `Skill` tool
- Respects context budget (clamps to MAX_SKILL_CARDS)
- User can disable per-session

**Acceptance:** Opt-in works; budget respected; disable works

### P2-2: Plugin Marketplace UI
**Impact:** 🟡 Medium | **Effort:** 2-3 weeks | **Owner:** Platform
**Why:** 40 plugins + 70 MCPs hard to discover via CLI only
**What:**
- Static site (GitHub Pages) from `catalog.json` + `mcp-servers.json`
- Searchable, filterable, sortable
- Plugin detail pages with guide preview
- Install command copy button
- Usage stats (opt-in anonymous)

**Acceptance:** Live at `plugins.agentenhancements.dev` (or similar)

### P2-3: Curated Install Profiles
**Impact:** 🟡 Medium | **Effort:** 1 week | **Owner:** AE Core
**Why:** Users overwhelmed by 3,127 skills; need guided starting points
**What:**
- Profiles: `minimal`, `full-stack`, `research-heavy`, `security-audit`, `frontend`, `backend`
- Each profile: curated skill set + plugin set + MCP set
- `setup.sh --profile <name>` installs profile
- User can customize after

**Acceptance:** 5+ profiles; install works; profiles documented

### P2-4: SBOM Generation for All Components
**Impact:** 🟡 Medium | **Effort:** 3-5 days | **Owner:** Platform
**Why:** Supply chain transparency; compliance; vulnerability tracking
**What:**
- `cyclonedx-py` for Python (unified-integration)
- `cyclonedx-bom` for Node (ECC, agent_browser)
- `cargo cyclonedx` for Rust (ECC2)
- Merge into single SBOM per release
- Publish as release asset

**Acceptance:** SBOM attached to every GitHub release; valid CycloneDX

### P2-5: Secret Scanning in CI + Pre-commit
**Impact:** 🟡 Medium | **Effort:** 2-3 days | **Owner:** Platform
**Why:** `gitleaks`/`trufflehog` not in CI; secrets could be committed
**What:**
- `gitleaks` in CI (fail on leak)
- Pre-commit hook for local detection
- Baseline for existing false positives
- Document secret handling in CONTRIBUTING.md

**Acceptance:** CI fails on new secrets; pre-commit catches locally

### P2-6: Dependency Update Automation (Renovate/Dependabot)
**Impact:** 🟡 Medium | **Effort:** 1-2 days | **Owner:** Platform
**Why:** Manual dependency updates = stale deps = vulns
**What:**
- Renovate config for Python, Node, Rust, GitHub Actions
- Auto-PR for minor/patch; manual for major
- Group related updates
- Test on PR before merge

**Acceptance:** Weekly dependency PRs; zero high vulns > 30 days

### P2-7: Agent Registry Schema Validation
**Impact:** 🟡 Medium | **Effort:** 3-5 days | **Owner:** ECC Core
**Why:** 71 agents, no schema validation; frontmatter errors silent
**What:**
- JSON Schema for agent frontmatter (name, description, tools, model)
- Validation in CI on `ECC/agents/*.md`
- Auto-fix for common issues (tool list sorting, model normalization)
- Documentation of required fields

**Acceptance:** CI validates all agents; zero frontmatter errors

### P2-8: Formal Threat Model (STRIDE)
**Impact:** 🟡 Medium | **Effort:** 1 week | **Owner:** Security
**Why:** No documented threat model; security decisions ad-hoc
**What:**
- STRIDE analysis for: Registry, Preflight, Runtime, MCP Gateway, Memory, Hooks, Installers
- Data flow diagrams for each component
- Threat enumeration with mitigations
- Review quarterly

**Acceptance:** Threat model document; mitigations tracked; quarterly review scheduled

---

## P3 — Nice to Have (Backlog)

### P3-1: Plugin Update Notifications
**Impact:** 🟢 Low | **Effort:** 1 week | **Owner:** Platform
**What:** GitHub Actions workflow checks upstream plugin repos weekly; opens PR/issue on new release

### P3-2: Skill Composition (Formal)
**Impact:** 🟢 Low | **Effort:** 2 weeks | **Owner:** AE Core
**What:** Skills can declare `composes: [skill-a, skill-b]` → auto-loads dependencies + merges guidance

### P3-3: Skill Telemetry (Opt-In Anonymous)
**Impact:** 🟢 Low | **Effort:** 1 week | **Owner:** Platform
**What:** Anonymous usage stats (skill load count, search frequency) → guides curation

### P3-4: Visual Regression for Dashboard
**Impact:** 🟢 Low | **Effort:** 3-5 days | **Owner:** Platform
**What:** Playwright tests for `ecc_dashboard.py` UI; screenshot comparison

### P3-5: Chaos Engineering for Resilience
**Impact:** 🟢 Low | **Effort:** 2 weeks | **Owner:** Platform
**What:** Litmus/Chaos Mesh experiments: hook timeout, MCP failure, network partition, disk full

---

## Effort vs Impact Visualization

```
IMPACT
  🔴 Critical  | P0-1  P0-2  P0-3  P0-4  P0-5  P0-6
  🟠 High      | P1-1  P1-2  P1-3  P1-4  P1-5  P1-6  P1-7  P1-8  P1-9  P1-10
  🟡 Medium    | P2-1  P2-2  P2-3  P2-4  P2-5  P2-6  P2-7  P2-8
  🟢 Low       | P3-1  P3-2  P3-3  P3-4  P3-5
               +-------------------------------------------------- EFFORT
                 1d    3d    1w    2w    3w    1m
```

---

## Quick Wins (Can Start Today)

| Task | Effort | Command |
|------|--------|---------|
| Add `gitleaks` to CI | 30 min | `echo "gitleaks detect" >> .github/workflows/ci.yml` |
| Pin Python deps | 1 hour | `pip freeze > unified-integration/requirements.txt` |
| Add `cargo deny` check | 15 min | `cargo deny check` in ECC2 CI |
| Enable `shellcheck` | 15 min | `shellcheck unified-integration/scripts/*.sh` |
| Add `mypy` config | 1 hour | `mypy --config-file=mypy.ini unified-integration/scripts/` |

---

## Dependency Graph (Critical Path)

```
P0-1 (CI) ──┬──→ P0-4 (Preflight tests)
            ├──→ P0-5 (Registry tests)
            ├──→ P0-6 (Supply chain)
            ├──→ P1-2 (Budget tests)
            ├──→ P1-8 (Metrics)
            └──→ P2-5 (Secret scanning)
P0-2 (Hooks) ──→ P0-3 (Agent tools)
P1-1 (Workflows) ──→ P1-10 (Orchestrators)
P1-3 (Skill versioning) ──→ P2-1 (Auto-load) ──→ P3-2 (Composition)
P1-4 (Categorization) ──→ P2-3 (Profiles)
P1-5 (MCP health) ──→ P2-4 (SBOM)
```

---

## Resource Allocation Suggestion

| Role | Focus | Capacity |
|------|-------|----------|
| **Platform Engineer** | P0-1, P0-6, P1-8, P1-9, P2-4, P2-5, P2-6 | 1 FTE |
| **AE Core Engineer** | P0-4, P0-5, P1-2, P1-3, P1-4, P1-5, P1-6, P1-10 | 1-2 FTE |
| **ECC Core Engineer** | P0-2, P0-3, P1-1, P1-7, P2-7 | 1 FTE |
| **Security Engineer** | P2-8, P3-5 | 0.5 FTE |
| **Tech Writer** | P1-7, P3-1 | 0.5 FTE |

---

## Success Metrics (90 Days)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| CI pass rate | N/A | 100% | GitHub Actions |
| Preflight test coverage | 0% | >90% | `coverage.py` |
| Registry scoring coverage | 0% | >85% | `coverage.py` |
| Agent least privilege | 60% | 100% | Agent audit script |
| Hook bootstrap lines | 5,600+ | <500 | `wc -l hooks.json` |
| "Other" skill category | 36% | <10% | Registry stats |
| MCP health endpoints | 0/10 | 10/10 | `doctor.py` |
| E2E test pass | 0 | 1 | CI pipeline |
| Critical vulns | Unknown | 0 | `pip-audit`/`npm audit` |
| Cold-start budget regression | Undetected | Caught in CI | Benchmark job |
