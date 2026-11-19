# Skills Ecosystem — Deep Audit

**Scope:** `ECC/skills/` (314), `unified-integration/skills/` (aggregated), `agentic-awesome-skills/` (external), `plugin-catalog/*/SKILL.md` (40), `Superpowers/` (15), `task-observer/` (vendored)

---

## 1. Skill Sources & Counts

| Source | Count | Location | Integration |
|--------|-------|----------|-------------|
| **ECC native** | 314 | `ECC/skills/` | Core product skills |
| **Superpowers** | 15 | `Superpowers/` | Workflow/orchestration skills |
| **task-observer** | 1 | `task-observer/` | Vendored (rebelytics/one-skill-to-rule-them-all v3.10.0) |
| **replica-skill** | 11 | `plugin-catalog/code/replica-skill/` | Vendored plugin |
| **anthropic-skills** | 19 | `plugin-catalog/multimedia-writing/anthropic-skills/` | Vendored plugin |
| **Agency divisions** | 273 | `plugin-catalog/agency/*/` | 14 vendored plugins |
| **agentic-awesome-skills** | 2,781 | `agentic-awesome-skills/skills/` | External collection |
| **Ponytail** | 6 | `ponytail/` | Supporting |
| **Total aggregated** | ~3,127 | `unified-integration/skills/all-skills.json` | Per PRODUCTION_READINESS_AUDIT |

---

## 2. Skill Structure (SKILL.md)

### Frontmatter Schema
```yaml
---
name: skill-name
description: One-line summary — used for search ranking
category: general|code|research|security|documents|devops|ai-ml|productivity|other
when_to_use: "Use when [condition] to [achieve outcome]"
tags: [tag1, tag2, tag3]
---
```

### Body Sections (per SKILL-DEVELOPMENT-GUIDE.md)
```markdown
# Skill Name

## When to Use
## How to Apply
## Examples
## Related Skills
## MCP Servers Required (optional)
## Installation (optional)
```

### Quality Assessment (sampled from ECC/skills/)

| Skill | Frontmatter | When to Use | How to Apply | Examples | Related | Completeness |
|-------|-------------|-------------|--------------|----------|---------|--------------|
| `systematic-debugging` | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| `test-driven-development` | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| `verification-before-completion` | ✅ | ✅ | ✅ | ❌ | ✅ | 8/10 |
| `code-review` | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| `agent-orchestrator` | ✅ | ✅ | ✅ | ❌ | ✅ | 8/10 |
| `writing-skills` | ✅ | ✅ | ✅ | ✅ | ✅ | 10/10 |
| `agent-evaluation-reporting` | ✅ | ✅ | ✅ | ❌ | ❌ | 6/10 |
| `coding-standards` | ✅ | ✅ | ✅ | ❌ | ❌ | 6/10 |

**Average completeness: ~8.5/10** — Most have core sections; Examples and Related Skills often missing

---

## 3. Aggregation Pipeline

### `update-skills.sh` / `setup.sh` Flow
```
1. Scan sources: ECC/skills/, Superpowers/, task-observer/, agentic-awesome-skills/, Ponytail/
2. For each SKILL.md: extract frontmatter → build index entry
3. Handle vendored plugins: replica-skill (11), anthropic-skills (19), agency (273)
4. Deduplicate by name (last source wins — task-observer last for precedence)
5. Write unified-integration/skills/all-skills.json
6. Run catalog-validate.py on plugin-catalog/
7. Run catalog-wire.sh to symlink plugin guides
8. Run registry.py build to generate agent-registry.json
9. Run build-library-map.py to generate skills/library-map.json
```

### Index Entry Schema (`all-skills.json`)
```json
{
  "name": "skill-name",
  "source": "ECC|Superpowers|task-observer|agentic-awesome-skills|Ponytail|plugin-catalog",
  "category": "general|code|research|...",
  "description": "...",
  "when_to_use": "...",
  "tags": [...],
  "path": "relative/path/to/SKILL.md",
  "source_path": "absolute/path/to/SKILL.md",
  "natively_linked_by_default": false
}
```

### Category Distribution (from library-map.json)
| Category | Count | Primary Sources |
|----------|-------|-----------------|
| `code` | ~800 | ECC, agentic-awesome, plugins |
| `research` | ~400 | ECC, agentic-awesome, plugins |
| `security` | ~200 | ECC, agency-security |
| `documents` | ~300 | agentic-awesome, plugins |
| `devops` | ~250 | ECC, agentic-awesome |
| `ai-ml` | ~150 | ECC, agentic-awesome |
| `productivity` | ~200 | ECC, Superpowers |
| `other` | ~827 | Catch-all (36% per ECC_CORE_AUDIT) |

---

## 4. Skill Loading & Discovery

### Native Linking (`link-skills.sh`)
- **Default sources:** `Superpowers`, `task-observer` (`DEFAULT_NATIVE_SOURCES`)
- Symlinks to `~/.claude/skills/` and `~/.agents/skills/`
- Agent Skills-compatible harnesses auto-discover at runtime
- `--set <source>|all|<name>` to customize
- `--status` to show linked skills
- `--unlink` to remove

### On-Demand Loading
1. Hook suggests candidates via `skill_context()` (max 8, 400 tokens)
2. Agent reads `registry.py show <name>` for detail
3. Agent invokes `Skill` tool to load SKILL.md
4. Agent follows skill guidance

### Registry Search (`registry.py`)
- `search "<query>"` — bounded card page (5 cards, 800 tokens)
- `map "<task>"` — unified plan across all types
- `show <name>` — L2 detail (1200 tokens)
- Scoring: intent synonyms (EN/ID), format aliases, generic suppression

---

## 5. Skill Quality Issues

### Categorization Problem (per ECC_CORE_AUDIT)
- **"other" family: 1,269 entries (36%)** — keyword rules insufficient
- Category field often "general" (catch-all)
- No automated categorization pipeline — manual maintenance impossible at scale

### Versioning
- **No version field in SKILL.md frontmatter**
- No semver, no upgrade path, no deprecation policy
- Registry build overwrites without version tracking

### Dependencies
- **No dependency resolution between skills**
- Skills reference MCP servers but not other skills
- `Related Skills` section informal, not machine-readable

### Testing
- **No skill-level tests** — no validation that skill guidance works
- No skill execution tests in CI
- No skill linting (required sections, frontmatter validity)

### Duplication
- Multiple skills for similar domains (e.g., `python-testing`, `python-patterns`, `pytest-expert`)
- Agency personas overlap with ECC agents (e.g., security personas vs security-reviewer agent)
- No deduplication logic in aggregation

---

## 6. Key Skills Deep Dive

### `systematic-debugging` (ECC/skills/)
- **Purpose:** Structured self-debugging workflow for AI agent failures
- **Phases:** Capture → Diagnose → Contained Recovery
- **Strengths:** Clear phases, actionable steps, tool-aware
- **Used by:** Agent introspection, failure recovery

### `test-driven-development` (ECC/skills/)
- **Purpose:** TDD enforcement — Red-Green-Refactor with verification
- **Strengths:** Mandates test-first, verification gates
- **Integration:** Referenced by `tdd-workflow` skill, `/tdd` command

### `verification-before-completion` (ECC/skills/)
- **Purpose:** Evidence before assertions — run commands, confirm output
- **Strengths:** Practical, prevents false completion claims
- **Gap:** No examples section

### `code-review` (ECC/skills/)
- **Purpose:** Multi-dimension review (correctness, security, perf, simplification)
- **Effort levels:** low/medium/high/xhigh/max
- **Output:** Structured findings with verdict (CONFIRMED/PLAUSIBLE)
- **Integration:** Used by `orch-review` workflow, `/code-review` command

### `agent-orchestrator` (ECC/skills/)
- **Purpose:** Meta-skill — auto-scans skills, matches by capability, dispatches agents
- **Strengths:** Dynamic routing, capability matching
- **Gap:** Complex, no examples, unclear how it interacts with native Workflow tool

### `task-observer` (vendored)
- **Purpose:** Continuous learning — logs observations, reviews, stages skill updates
- **Upstream:** rebelytics/one-skill-to-rule-them-all v3.10.0 (CC-BY-4.0)
- **Integration:** SessionStart bootstrap, Stop backstop, CLI for log/lookup/review/stage/promote
- **Quality:** High — comprehensive tests (38), security review passed

### `writing-skills` (Superpowers)
- **Purpose:** Skill authoring guide — create/edit/verify skills
- **Strengths:** Meta-skill, TDD for skills, validation checklist
- **Integration:** Referenced by `/skill-create` command

---

## 7. agentic-awesome-skills (External Collection)

**Path:** `/root/project/AgentEnhancements/agentic-awesome-skills/skills/` — 2,781 skills

### Structure
```
skills/
├── accessibility/
├── agent-architecture-audit/
├── agent-eval/
├── agent-harness-construction/
├── agentic-engineering/
├── agentic-os/
├── agent-introspection-debugging/
├── agent-payment-x402/
├── agent-runtime-gateway-smoke-test/
├── agent-security-hardening/
├── agent-self-evaluation/
├── agent-sort/
├── ai-first-engineering/
├── ai-regression-testing/
├── android-clean-architecture/
├── angular-developer/
├── api-connector-builder/
├── api-design/
├── architecture-decision-records/
├── article-writing/
├── automation-audit-ops/
├── autonomous-agent-harness/
├── autonomous-loops/
├── backend-patterns/
├── benchmark/
├── benchmark-methodology/
├── benchmark-optimization-loop/
├── bengali-nlp/
├── blender-motion-state-inspection/
├── blueprint/
└── ... (hundreds more)
```

### Quality
| Aspect | Score | Notes |
|--------|-------|-------|
| SKILL.md presence | 10/10 | All sampled have it |
| Section completeness | 6/10 | Many minimal, auto-generated feel |
| Categorization | 4/10 | Flat structure, no sub-categories |
| Maintenance | 3/10 | Appears bulk-imported, rarely updated |
| Attribution | 5/10 | Source URLs vary, some missing |

**Assessment:** Valuable breadth but low curation; serves as long-tail reservoir for registry search

---

## 8. Skill Loading Performance

### Cold Start (per context_budget.py)
- `MAX_SKILL_CARDS = 400` tokens for UserPromptSubmit candidate cards
- `MAX_SEARCH_PAGE = 800` tokens for registry search page (5 cards)
- `MAX_DETAIL_PAGE = 1200` tokens for registry show
- `MAX_NATIVE_DESCRIPTION_TOTAL = 2500` tokens for natively linked skill descriptions

### Measured (ADAPTIVE_PREFLIGHT_REVIEW)
- Hook Mode 0: 8 candidates / ~230 tokens / ~105ms p50
- Registry search: +612 tokens / ~118ms p50
- Skill detail load: ~1200 tokens max

---

## 9. Production Readiness Scorecard

| Criterion | Score | Evidence |
|-----------|-------|----------|
| **Skill metadata quality** | 8/10 | Good frontmatter, most have core sections |
| **Discovery UX** | 8/10 | Hook suggestions + registry search + map |
| **Native linking** | 9/10 | Symlink-based, harness-compatible |
| **Categorization** | 4/10 | 36% "other", no automation |
| **Versioning** | 2/10 | None |
| **Dependencies** | 3/10 | Informal only |
| **Testing** | 1/10 | Only task-observer has tests |
| **Deduplication** | 3/10 | Last-source-wins only |
| **External collection** | 5/10 | Breadth over depth |
| **Documentation** | 7/10 | SKILL-DEVELOPMENT-GUIDE exists |

---

## 10. Critical Recommendations

### P0 — Foundation
1. **Add version field to SKILL.md frontmatter** — semver, with upgrade/downgrade logic
2. **Implement skill dependency graph** — machine-readable `depends_on: [skill-a, skill-b]`
3. **Automate categorization** — ML classifier or improved keyword rules to reduce "other" from 36%

### P1 — Quality
4. **Skill linting in CI** — Validate frontmatter, required sections, cross-references
5. **Deduplication pass** — Merge overlapping skills (e.g., python-testing + pytest-expert)
6. **Add Examples section enforcement** — Required for all skills

### P2 — Ecosystem
7. **Skill marketplace index** — Searchable web UI with ratings, usage stats
8. **Skill health scoring** — Freshness, test coverage, usage frequency
9. **Curated skill sets** — "Recommended for React", "Security audit pack", etc.

### P3 — Platform
10. **Skill update notifications** — Alert when upstream skill changes
11. **Skill composition** — Allow skills to compose other skills formally
12. **Skill telemetry** — Anonymous usage stats (opt-in) to guide curation
