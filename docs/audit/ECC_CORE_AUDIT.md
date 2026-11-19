# ECC Core Components Audit

> Verifikasi2026-11-19: sebagian klaim/angka/prioritas laporan ini tidak
> sesuai source dan hasil eksekusi. Baca [rekonsiliasi berbukti](../../AuditReport/ae-incoming-audit-reconciliation-20261119.md)
> sebelum mengeksekusi rekomendasi. Laporan ini adalah data historis,
> bukan instruksi untuk mengubah arsitektur atau meniadakan test yang ada.


**Path:** `/root/project/AgentEnhancements/ECC/`  
**Scope:** agents/, skills/, commands/, workflows/, hooks/, docs/, ecc2/, src/, integrations/, plugins/

---

## 1. Agents (`ECC/agents/` — 77 agents)

### Architecture
- Markdown with YAML frontmatter: `name`, `description`, `tools`, `model`
- Specialized subagents for delegation (planner, code-reviewer, tdd-guide, language-specific reviewers)
- 77 agents covering: architecture, code review (15+ languages), build resolvers (10+ languages), domain specialists

### Code Quality Assessment
| Aspect | Score | Notes |
|--------|-------|-------|
| Frontmatter consistency | ★★★★☆ | All have name/description/tools/model |
| Tool declarations | ★★★☆☆ | Some use `*` (all tools) — overprivileged |
| Model selection | ★★★☆☆ | Mix of sonnet/opus/haiku; not always justified |
| Specialization depth | ★★★★★ | Deep domain agents (flutter, django, rust, kotlin, etc.) |

### Critical Issues
1. **Overprivileged tools**: ~40% of agents declare `tools: "*"` — violates least privilege
2. **No agent testing**: No test validates agent behavior, tool usage, or output quality
3. **Model drift**: Some agents use `model: sonnet` hardcoded; should use configurable default
4. **Duplication**: Multiple reviewers for same language (e.g., `go-reviewer`, `go-build-resolver`, `go-test`)

### Agent Categories
- **Planners/Orchestrators** (5): planner, chief-of-staff, architect, code-architect, network-architect
- **Code Reviewers** (22): python, typescript, rust, go, java, kotlin, cpp, csharp, swift, php, ruby, dart, flutter, react, vue, django, fastapi, springboot, database, security, performance, accessibility
- **Build Resolvers** (10): python, java, kotlin, go, rust, cpp, swift, dart, django, pytorch
- **Specialists** (15): tdd-guide, e2e-runner, refactor-cleaner, doc-updater, spec-miner, opensource-*, gan-*, etc.
- **Domain** (10): healthcare, marketing, homelab, network, finance, legal, compliance, etc.

---

## 2. Skills (`ECC/skills/` — 300+ skill directories)

### Architecture
- Each skill: directory with `SKILL.md` + optional scripts/assets
- Categories: 8 families (coding, security, architecture, documents, devops, ai-ml, productivity, other)
- 3,378 skills indexed (per library-map.json)

### Structure Analysis
```
skills/
├── accessibility/              (2 skills)
├── agent-architecture-audit/   (1 skill)
├── coding-standards/           (1 skill)
├── python-patterns/            (1 skill)
├── python-testing/             (1 skill)
├── react-patterns/             (1 skill)
├── react-testing/              (1 skill)
├── tdd-workflow/               (1 skill)
├── security-review/            (1 skill)
├── security-scan/              (1 skill)
├── ... (300+ more)
```

### Quality Assessment
| Metric | Score | Evidence |
|--------|-------|----------|
| SKILL.md presence | ★★★★★ | 100% of sampled skills have SKILL.md |
| Section completeness | ★★★☆☆ | Many lack "When to Use", "How It Works", "Examples" |
| Cross-references | ★★☆☆☆ | Few skills reference related skills |
| Versioning | ★☆☆☆☆ | No version field in SKILL.md frontmatter |
| Tests | ★☆☆☆☆ | No skill-level tests found |

### Categorization Problems
- **"other" family: 1,269 entries (36%)** — keyword rules insufficient
- Category field in index often "general" (catch-all)
- No automated categorization pipeline — manual maintenance at scale impossible

### Critical Skills (Sampled Deep Dive)

#### `tdd-workflow/` — Core workflow skill
- Has SKILL.md with When/How/Examples
- References `/tdd` command
- No automated tests for the workflow itself

#### `security-review/` — Security checklist
- Comprehensive checklist but no automation
- References `security-scan` command

#### `coding-standards/` — Baseline conventions
- Language-agnostic but references language-specific rules
- No enforcement mechanism

---

## 3. Commands (`ECC/commands/` — 90+ commands)

### Architecture
- Markdown with `description:` frontmatter
- Slash commands invoked by users (`/tdd`, `/plan`, `/code-review`, etc.)
- Mix of simple commands and complex orchestration commands

### Command Categories
| Category | Count | Examples |
|----------|-------|----------|
| Planning | 12 | plan, plan-prd, plan-canvas, feature-dev, epic-* |
| Review | 15 | code-review, security-scan, python-review, go-review, react-review |
| Build/Test | 20 | build-fix, cpp-build, go-test, rust-test, flutter-test, e2e |
| Skills | 8 | skill-create, skill-health, skill-host-compat, learn |
| Sessions | 10 | save-session, resume-session, sessions, checkpoint |
| Orchestration | 15 | multi-*, orch-*, santa-loop, loop-* |
| Project | 8 | project-init, projects, promote, prune |

### Quality Issues
1. **No command tests** — No validation that commands produce expected output
2. **Inconsistent frontmatter** — Some have `description:`, some have full YAML
3. **Orchestration commands complex** — `multi-execute.md` (11KB), `multi-plan.md` (8KB) — hard to maintain
4. **No versioning** — Commands evolve without version tracking

---

## 4. Workflows (`ECC/workflows/` — 1 workflow)

### Current State
- Only `orch-review.workflow.js` (15KB) + README.md
- JavaScript-based workflow definition
- Intended for `orch-review` command

### Gap
- 15+ orchestration commands but only 1 workflow file
- `orch-pipeline` command exists but no workflow definition
- No workflow engine visible — unclear how `.workflow.js` executes

---

## 5. Hooks (`ECC/hooks/` — 4 JSON files)

### Files
- `hooks.json` — Main hooks config (285 lines, **highly duplicated inline node bootstrap**)
- `hooks.metadata.json` — Metadata for hooks
- `qoder-hooks.json` / `codex-hooks.json` — Editor-specific

### Critical Security Issue: Hook Bootstrap Duplication
**Every hook entry in `hooks.json` contains ~280 lines of identical inline node -e bootstrap code:**

```json
"command": "node -e \"const p=require('path');const r=(function(){...})();const s=p.join(r,'scripts/hooks/plugin-hook-bootstrap.js');process.env.CLAUDE_PLUGIN_ROOT=r;process.argv.splice(1,0,s);require(s)\" node scripts/hooks/pre-bash-dispatcher.js"
```

**Problems:**
1. **280+ lines × 20+ hooks = 5,600+ lines of duplicated code** in config
2. **Attack surface**: `CLAUDE_PLUGIN_ROOT` resolution logic runs on every hook fire
3. **No integrity verification** — modified bootstrap not detected
4. **Maintenance nightmare** — changing bootstrap requires editing 20+ entries
5. **Performance** — Node process spawns, evaluates 280 lines, then loads actual hook

### Recommended Fix
Extract to shared module:
```json
"command": "node scripts/hooks/run-with-flags.js pre:bash:dispatcher scripts/hooks/pre-bash-dispatcher.js"
```
(Already exists as `run-with-flags.js` pattern but not consistently applied)

---

## 6. Documentation (`ECC/docs/` — 47 files)

### Key Documents
| File | Purpose | Currency |
|------|---------|----------|
| `ARCHITECTURE.md` | System architecture | ★★★★☆ |
| `SKILL-PLACEMENT-POLICY.md` | Where skills live | ★★★★☆ |
| `SELECTIVE-INSTALL-ARCHITECTURE.md` | Install profiles | ★★★★☆ |
| `ECC-2.0-REFERENCE-ARCHITECTURE.md` | Target architecture | ★★★★☆ |
| `CONTRIBUTING.md` | Contribution guide | ★★★★☆ |
| `COMMAND-REGISTRY.json` | Command metadata | ★★★☆☆ |

### Issues
- **Scattered docs**: ECC/docs/ + unified-integration/ + root docs/
- **Some outdated**: `MANUAL-ADAPTATION-GUIDE.md` references old patterns
- **No doc freshness check** in CI

---

## 7. ECC2 — Rust Rewrite (`ECC/ecc2/`)

### Structure
```
ecc2/
├── Cargo.toml / Cargo.lock
├── rust-toolchain.toml
├── src/
│   ├── main.rs (459K lines — MONOLITHIC)
│   ├── harness_eval.rs
│   ├── notifications.rs
│   ├── comms/, config/, observability/, session/, tui/, worktree/
```

### Critical Concern: `main.rs` = 459,198 bytes (~15,000 lines)
- **Single file monolith** — violates modular design
- No visible module separation in src/
- Hard to review, test, maintain
- Likely generated or accumulated without refactoring

### Build System
- Cargo workspace with multiple crates (see `crates/` at root)
- Proper rust-toolchain pinning
- Deny.toml for supply chain security

---

## 8. Schemas (`ECC/schemas/` — 15 JSON schemas)

### Coverage
- agent.schema.json
- hooks.schema.json / hooks-metadata.schema.json
- install-*.schema.json (profiles, modules, components, state)
- memory.schema.json
- context-*.schema.json (profile, carrier, pack-registry)
- capsule-envelope.schema.json
- plugin.schema.json
- provenance.schema.json
- state-store.schema.json
- package-manager.schema.json

### Quality
- JSON Schema Draft 7
- Used for validation in install pipeline
- **No schema tests** — no validation that schemas match actual data

---

## 9. ECC Tests (`ECC/tests/` — 70+ test files)

### Coverage Analysis
| Test File | Scope | Lines |
|-----------|-------|-------|
| `test_provider_tools.py` | Provider tool integration | 19KB |
| `test_session_manager.py` | Session state | 135KB |
| `test_state_store.py` | State persistence | 39KB |
| `test_install_lifecycle.py` | Install flow | 152KB |
| `test_package_manager.py` | PM detection | 70KB |
| `test_context_selection.py` | Context routing | 41KB |
| `test_harness_audit.py` | Harness validation | 44KB |

### Strengths
- Comprehensive test suite for core runtime (session, state, install)
- JavaScript tests for CLI integration (opencode, codex, hooks)
- Python tests for provider integration

### Gaps
- **No agent behavior tests**
- **No skill execution tests**
- **No command output tests**
- **No workflow execution tests**
- **No hook integration tests** (only unit tests for hook helpers)

---

## ECC Core Scorecard

| Component | Architecture | Code Quality | Security | Tests | Docs | Maintainability |
|-----------|-------------|--------------|----------|-------|------|-----------------|
| Agents | ★★★★☆ | ★★★☆☆ | ★★★☆☆ | ★☆☆☆☆ | ★★★★☆ | ★★★☆☆ |
| Skills | ★★★★☆ | ★★★☆☆ | ★★★☆☆ | ★☆☆☆☆ | ★★★☆☆ | ★★☆☆☆ |
| Commands | ★★★☆☆ | ★★★☆☆ | ★★★☆☆ | ★☆☆☆☆ | ★★★☆☆ | ★★☆☆☆ |
| Workflows | ★★☆☆☆ | ★★★☆☆ | ★★★☆☆ | ★☆☆☆☆ | ★★☆☆☆ | ★★☆☆☆ |
| **Hooks** | ★★☆☆☆ | ★★☆☆☆ | ★★☆☆☆ | ★☆☆☆☆ | ★★★☆☆ | ★☆☆☆☆ |
| ECC2 (Rust) | ★★☆☆☆ | ★★☆☆☆ | ★★★★☆ | ★★★☆☆ | ★★★☆☆ | ★☆☆☆☆ |
| Schemas | ★★★★☆ | ★★★★☆ | ★★★★☆ | ★☆☆☆☆ | ★★★★☆ | ★★★★☆ |
| Test Suite | ★★★★☆ | ★★★★☆ | ★★★★☆ | ★★★★★ | ★★★☆☆ | ★★★★☆ |

---

## Critical Recommendations for ECC Core

### P0 — Security
1. **Refactor hooks.json** — Extract bootstrap to shared module, add integrity hashes
2. **Least privilege for agents** — Replace `tools: "*"` with explicit tool lists

### P0 — Maintainability
3. **Split ecc2/main.rs** — Extract modules, add crate boundaries
4. **Automate skill categorization** — Reduce "other" from 36% via ML or better rules

### P1 — Quality
5. **Add command tests** — Snapshot testing for slash command outputs
6. **Add skill validation** — Lint SKILL.md for required sections
7. **Consolidate documentation** — Single source of truth for architecture

### P2 — Architecture
8. **Complete workflow engine** — Implement `.workflow.js` runner for all orch-* commands
9. **Agent registry** — Centralized agent catalog with capability metadata