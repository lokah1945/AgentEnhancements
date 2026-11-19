# AgentEnhancements Development Contract

**Project**: AgentEnhancements  
**Version**: 2.3\
**Effective Date**: 2026-11-20\
**Status**: BINDING - All agents MUST comply

---

## 1. Purpose & Scope

This contract establishes mandatory rules for ALL AI agents (Claude Code, Codex,
Cursor, Gemini CLI, Copilot, Windsurf, Kiro, OpenCode, and any future agents)
operating on this repository. It ensures unified direction, prevents conflicting
changes, and maintains project integrity across all contributors.

**Applies to**: Every commit, edit, script, configuration, and documentation
change in this repository.

---

## 2. Core Principles

### 2.1 Single Source of Truth

- **One setup script**: `unified-integration/setup.sh` (no variants, no "fixed"
  suffixes)
- **One skills index**: `unified-integration/skills/all-skills.json`
- **One memory system**: `unified-integration/memory/` with Python hooks
- **One compression system**: `unified-integration/compression/`

### 2.2 Agent Neutrality

- No agent-specific logic in shared infrastructure
- Agent-specific configs generated FROM shared source, not maintained separately
- All agents consume the same unified skills registry

### 2.3 Updateability First

- All external sources are **vendored full copies** (no submodules) with the
  upstream repository and license documented per directory (root `LICENSE`
  notice, `docs/LICENSE_AUDIT.md`)
- Update script (`unified-integration/update-skills.sh`) refreshes the
  aggregation/registry from the on-disk tree; moving a vendored source to a new
  upstream version is a deliberate **re-vendor procedure** (review, commit,
  re-run setup) — see `docs/UPDATING.md` §2.2
- No manual copying of skill files into the registry - always through the
  aggregation pipeline

### 2.4 Full Auditability & Change Tracking (MANDATORY)

- **Every modification MUST be traceable to a specific agent and session**
- **All agents MUST use git for ALL changes** - no direct file writes bypassing
  version control
- **Commit metadata MUST include**: agent identity, session ID, task context,
  timestamp
- **No anonymous or untracked changes permitted** - enables full correction
  analysis

---

## 3. Mandatory Rules

### 3.1 File Operations

- **Rule:** **R001**
  - **Requirement:** Never create `*-fixed.*`, `*-new.*`, `*-v2.*` files. Edit
    the canonical file directly.

- **Rule:** **R002**
  - **Requirement:** All documentation changes go to `docs/` directory, never in
    root or scripts.

- **Rule:** **R003**
  - **Requirement:** Configuration templates in `unified-integration/` use
    environment variables, never hardcoded paths.

- **Rule:** **R004**
  - **Requirement:** Skills aggregated ONLY via `aggregate_skills()` function in
    setup.sh. No manual copies.

- **Rule:** **R005**
  - **Requirement:** ALL changes committed via git with agent-identifying
    metadata.

### 3.2 Code Standards

- **Rule:** **R101**
  - **Requirement:** All hooks use parameterized queries (Python) - no SQL
    string interpolation.

- **Rule:** **R102**
  - **Requirement:** Bash scripts: `set -euo pipefail`, functions for logging,
    no global state mutation.

- **Rule:** **R103**
  - **Requirement:** Python scripts: type hints, docstrings, `if __name__ ==
    "__main__":` entry point.

- **Rule:** **R104**
  - **Requirement:** No agent-specific imports in shared utilities
    (load-skills.py, memory.py, compress.py).

### 3.3 Git Discipline & Agent Traceability

- **Rule:** **R201**
  - **Requirement:** Commit message format: `type(scope): subject` (conventional
    commits).

- **Rule:** **R202**
  - **Requirement:** One logical change per commit. No "fix + refactor + docs"
    in single commit.

- **Rule:** **R203**
  - **Requirement:** Push only after: tests pass, lint passes, docs updated in
    `docs/`.

- **Rule:** **R204**
  - **Requirement:** No force-push to main. PR required for structural changes.

- **Rule:** **R205**
  - **Requirement:** **Every commit MUST include agent signature**:
    `Co-Authored-By: <agent-name> <session-id>`

- **Rule:** **R206**
  - **Requirement:** **Agent identity MUST be declared** in commit body: `Agent:
    <agent-name> | Session: <id> | Task: <description>`

- **Rule:** **R207**
  - **Requirement:** **No direct filesystem writes** - all edits via git-tracked
    operations

- **Rule:** **R208**
  - **Requirement:** **Change log auto-generated** from commits for audit trail

### 3.4 Skill Management

- **Rule:** **R301**
  - **Requirement:** New skill sources added via `setup.sh` aggregation function
    only.

- **Rule:** **R302**
  - **Requirement:** Skill metadata (category, tags, tools) MUST come from
    SKILL.md frontmatter.

- **Rule:** **R303**
  - **Requirement:** Entire skill directory copied (recursive), not just
    SKILL.md.

- **Rule:** **R304**
  - **Requirement:** Unified index regenerated from scratch on every aggregation
    run.

---

## 4. Agent Boundaries

### 4.1 What ANY Agent May Do

- Fix bugs in existing functionality
- Add tests for uncovered code paths
- Update documentation in `docs/`
- Improve error messages / logging
- Optimize performance without changing interfaces
- Update `update-skills.sh` when source repos change structure

### 4.2 What NO Agent May Do (Without Explicit Human Approval)

- Change the skills aggregation architecture
- Modify the unified skills index schema
- Add/remove agent support (changes AGENTS array)
- Alter memory database schema
- Change compression engine interface
- Modify environment variable contracts
- Rename/move canonical files (setup.sh, all-skills.json, etc.)
- **Bypass git tracking or commit without agent identity**

### 4.3 Agent-Specific Permissions

| Agent | Permitted Specializations |
| ------- | --------------------------- |
| **Claude Code** | Hook integration, CLAUDE.md generation, settings.json |
| **Codex** | Codex config.yaml, multi-agent workflows |
| **Cursor** | Cursor settings.json, prompt optimization |
| **Gemini CLI** | Large context budget tuning |
| **Copilot** | VS Code integration patterns |
| **Windsurf** | Cascade workflow integration |
| **Kiro** | Steering file generation |
| **OpenCode** | Native hook system integration |

---

## 5. Development Workflow

### 5.1 Standard Flow

```text
1. Read CONTRACT.md (this file) and docs/ARCHITECTURE.md
2. Create feature branch: git checkout -b type/short-description
3. Make minimal, focused changes
4. Run tests: cd ECC && node tests/run-all.js
5. Update docs/ if interfaces changed
6. Commit with conventional message + agent metadata
7. Push branch, create PR
```

### 5.2 Skill Update Flow (On Demand)

```text
1. Run: ./unified-integration/update-skills.sh   (re-aggregates from the
   vendored tree)
2. To move to a NEW upstream version: follow the re-vendor procedure in
   docs/UPDATING.md §2.2
3. Review changes in unified-integration/skills/
4. Run: ./unified-integration/setup.sh
5. Verify all agent configs regenerated correctly
6. Commit: chore(skills): update from upstream sources
7. Push
```

### 5.3 Emergency Hotfix Flow

```text
1. Branch from main: git checkout -b hotfix/critical-description
2. Minimal fix only - no refactoring
3. Test affected component only
4. Commit: fix(scope): critical one-line description
5. Push, PR, merge immediately
6. Backport to release branches if needed
```

---

## 6. Testing Requirements

### 6.1 Mandatory Test Runs

- **Before commit**: `cd ECC && node tests/run-all.js` (must pass)
- **Before PR**: Full test suite + lint (if configured)
- **After skill updates**: Verify skill count in all-skills.json matches
  expectation

### 6.2 Test Coverage Targets

- Hooks: 100% (security critical)
- Skills loader: 90%+
- Memory system: 95%+
- Compression: 80%+

---

## 7. Documentation Standards

### 7.1 Required Documentation

Every change that affects:

- **Interfaces** → Update `docs/API.md`
- **Configuration** → Update `docs/CONFIGURATION.md`
- **Architecture** → Update `docs/ARCHITECTURE.md`
- **Skills** → Update `docs/SKILLS.md`
- **Troubleshooting** → Update `docs/TROUBLESHOOTING.md`

### 7.2 Documentation Location

```text
docs/
├── ARCHITECTURE.md          # System architecture
├── API.md                   # Internal APIs (skills loader, memory,
# compression)
├── CONFIGURATION.md         # All config options, env vars
├── SKILLS.md                # Skill format, aggregation, categories
├── AGENTS.md                # Agent-specific setup guides
├── TROUBLESHOOTING.md       # Common issues & solutions
├── CONTRIBUTING.md          # How to contribute (this contract summarized)
├── CHANGELOG.md             # Version history
└── UPDATING.md              # How to update skills, deps, tools
```

### 7.3 Documentation Style

- Markdown with frontmatter: `title`, `version`, `last_updated`, `audience`
- Code blocks with language tags
- No inline HTML
- Relative links only

---

## 8. Configuration Contract

### 8.1 Capability status contract (two dimensions)

Every capability in the ecosystem (skill, plugin, MCP server, built-in) carries
TWO independent status dimensions. One must never be inherited from the other,
nor from a parent entry:

- **Dimension:** **Implementation status**
  - **Where it lives:** Manifest field `status` (plugin-catalog,
    mcp-servers.json) — static, hand-maintained, validated by
    `catalog-validate.py`
  - **Values:** `to-integrate`, `integrated` (vendored + wired + tested),
    `integrated-ready` (guide + routing shipped; upstream not vendored — user
    installs it), `deprecated`; MCP roadmap: `built`, `to-install`
  - **Meaning:** How far the AE-side artifact is implemented

- **Dimension:** **Runtime readiness**
  - **Where it lives:** Computed at runtime per host/provider — never stored in
    manifests
  - **Values:** visible/hidden via `api_config.server_state()` reasons:
    `local_tools_available`, `configured`, `not_configured`,
    `missing_credentials`, `runtime_not_configured`, `executable_not_installed`,
    `disabled`, `disabled_by_default`; skills: linked via `link-skills.sh
    --status`
  - **Meaning:** Whether the capability can actually be invoked right now, by
    this user, on this host

Rules:

- Readiness is recomputed from live state (files, credentials, config) — it is
  never cached across an auth/permission revocation, and never claimed from a
  manifest. `registry.py usable_entries` and the MCP gateway both filter on it.
- A parent's status (e.g. a plugin family or plugin catalog entry) never
  implies the status of its children (e.g. sub-skills, suggested MCP servers).
- Capabilities that are not ready may be listed WITH their diagnosis
  (`api_config.status()`, `registry.py map`) but must not be offered as
  healthy callable tools.
- Documentation may not present reference config files as native activation,
  nor a `to-install` roadmap entry as an installed server.

### 8.2 Environment Variables (Immutable Interface)

- **Variable:** `AGENT_ENHANCEMENTS_BASE_DIR`
  - **Purpose:** Project root
  - **Default:** Checkout root inferred from the installed setup script

- **Variable:** `AGENT_MEMORY_ROOT`
  - **Purpose:** Memory storage
  - **Default:** `.agentenhancements/memory`

- **Variable:** `HEADROOM_BIN`
  - **Purpose:** Compression binary
  - **Default:** auto-detect

- **Variable:** `AGENT_SKILLS_DIR`
  - **Purpose:** Skills registry
  - **Default:** `$BASE_DIR/unified-integration/skills`

- **Variable:** `AGENT_ENHANCEMENTS_MODEL_FILE`
  - **Purpose:** Adaptive preflight model.json override (isolated tests)
  - **Default:** `.agentenhancements/config/model.json`

- **Variable:** `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY`
  - **Purpose:** Adaptive preflight Mode 2 key
  - **Default:** unset

- **Variable:** `AE_PREFLIGHT_DEADLINE_MS`
  - **Purpose:** Adaptive preflight phase deadline
  - **Default:** `2000`

**Agents MUST NOT** introduce new required env vars without updating
`docs/CONFIGURATION.md` and this contract.

### 8.3 File Paths (Canonical)

```text
unified-integration/
├── setup.sh                    # MAIN ENTRY POINT
├── update-skills.sh            # Skill refresh
├── launch-agent.sh             # Universal launcher
├── config/
│   └── detected-agents.sh      # Auto-generated
├── prompts/
│   ├── universal-system-prompt.txt
│   └── *-system-prompt.txt     # Per-agent
├── skills/
│   ├── all-skills.json         # UNIFIED INDEX
│   ├── by-category/
│   └── by-agent/
├── memory/
│   ├── config.yaml
│   ├── init-memory.sh
│   └── hooks/
│       ├── *-memory-hook.py    # Python (canonical)
│       └── *-memory-hook.sh    # Bash wrapper
├── compression/
│   ├── config.yaml
│   └── compress.sh
└── scripts/
    ├── load-skills.py
    ├── memory.py
    └── compress.py
```

---

## 9. Enforcement & Consequences

### 9.1 Automated Checks (Pre-commit / CI)

- `bash -n` on all `.sh` files
- `python3 -m py_compile` on all `.py` files
- `markdownlint` on all `.md` files
- Conventional commit message validation
- No `fixed|new|v\d+|temp|backup` in filenames
- **Agent identity validation in commit metadata**

### 9.2 Human Review Required For

- Schema changes (skills index, memory DB, compression config)
- New agent support
- Architecture modifications
- Security-related changes
- **Changes without valid agent traceability**

### 9.3 Violation Handling

- **Severity:** **Minor** (naming, style)
  - **Action:** Auto-fix in CI, warning in PR

- **Severity:** **Major** (hardcoded paths, SQL injection risk)
  - **Action:** Block merge, require fix

- **Severity:** **Critical** (schema change without approval, untracked changes)
  - **Action:** Revert immediately, incident review

- **Severity:** **Audit Failure** (missing agent identity)
  - **Action:** Block push, require re-commit with metadata

---

## 10. Change Log

- **Version:**2.3
  - **Date:**2026-11-20
  - **Author:**Codex, session ae-audit-20261119
  - **Changes:** Maintainer-approved checkout-local runtime/state defaults;
    optional isolation override and native relocation behavior in section 8.6.

- **Version:** 2.2
  - **Date:** 2026-11-15
  - **Author:** ZCode (audit remediation session)
  - **Changes:** §2.3/§5.2 rewritten to match the vendoring reality (re-vendor
    procedure, no submodule pulls); new §8.1 capability status contract
    (implementation vs runtime readiness dimensions)

- **Version:** 2.1
  - **Date:** 2026-11-01
  - **Author:** System
  - **Changes:** Added mandatory agent traceability (R205-R208), renamed project
    to AgentEnhancements

- **Version:** 2.0
  - **Date:** 2026-11-01
  - **Author:** System
  - **Changes:** Initial contract - replaces ad-hoc rules

- **Version:** 1.0
  - **Date:** 2026-10-15
  - **Author:** System
  - **Changes:** Implicit conventions (now formalized)

---

## 11. Acknowledgment

**By operating on this repository, every agent acknowledges:**

> "I have read and understood CONTRACT.md. I will comply with all rules herein.
> I will not take actions outside my defined boundaries. I will document changes
> in `docs/` and follow the defined workflows. **I will ensure every change is
> traceable via git with my agent identity and session context.** I understand
> violations may result in reverted changes and loss of write access."

---

## 12. Audit & Correction Analysis Framework

### 12.1 Traceability Requirements

Every change in this repository MUST enable:

- **Who**: Which agent (Claude Code, Codex, Cursor, etc.) made the change
- **When**: Exact timestamp with timezone
- **Why**: Task/context description linking to issue/PR
- **What**: Precise diff with file/line granularity
- **How**: Session ID for correlation across multiple commits

### 12.2 Correction Analysis Workflow

When issues are detected:

1. **Identify** - `git log --all --oneline --grep="<issue>"` to find related
   commits
2. **Trace** - `git show <commit> --format=fuller` to extract agent/session
   metadata
3. **Analyze** - Cross-reference session context with change impact
4. **Correct** - Apply fix with full audit trail
5. **Verify** - Regression test + update documentation

### 12.3 Mandatory Commit Metadata Format

```text
type(scope): subject

Agent: <agent-name>
Session: <session-id>
Task: <task-description>
Context: <brief-context>

Co-Authored-By: <agent-name> <session-id>
```

---

**End of Contract**  
*This document is the supreme governing rule for this repository. No agent,
human, or process may override it without explicit written approval from the
project maintainers.*

### 8.4 Context budget contract (library model)

The default profile is context-frugal. Budgets are implementation limits
enforced by `unified-integration/scripts/context_budget.py` and tested by
CI fixtures — not claims:

| Surface | Limit (tokens) |
| --- | ---: |
| L0 bootstrap map (skills/library-map.json) | ≤ 1,000 |
| Cold start total (all AE channels, model-visible) | ≤ 4,000 |
| Memory recall (inside total) | ≤ 600 |
| Observer ambient (inside total) | ≤ 250 |
| One search result page | ≤ 800, max 5 cards |
| One detail page | ≤ 1,200 |
| Native description allocation | ≤ 2,500 |
| Tool schema allocation (model-visible) | ≤ 1,800 |

Rules: `--set all` is never default (audited via `link-skills.sh --audit`,
migrated via `--migrate`); the catalog stays fully reachable through
`registry.py search/map/show` cards and lifecycle-hook suggestions;
scale fixture (1×/5×/10×) must keep L0 growth ≤ 200 tokens. Measurement:
tiktoken o200k_base proxy unless host usage telemetry is available.

### 8.5 Adaptive preflight contract (capability selection)

Optional pre-inference capability selection (docs/ADAPTIVE_PREFLIGHT.md).
Defaults are context-frugal and fail-closed; every rule below is enforced
by `unified-integration/scripts/adaptive_preflight.py` and tested by
`tests/test_adaptive_preflight.py`.

- **Aspect:** Configuration
  - **Contract:** One checkout-local `model.json` at
    `<checkout>/.agentenhancements/config/model.json`, inside ignored
    checkout state.
    `adaptive_preflight_mode` is the exact integer 0, 1 or 2; anything else
    (bool, numeric string, float, duplicate field, malformed JSON) runs Mode 0
    with a stderr diagnosis. Mode 2 additionally requires a HTTPS `endpoint`,
    `sdk` ∈ {openai, anthropic} and a non-empty `model`; on Modes 0/1 those
    fields are ignored.

- **Aspect:** Secrets
  - **Contract:** model.json and ui.api.json never carry the Mode 2 key.
    Resolution: `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY` → OS keyring
    (`agentenhancements.preflight`, account = endpoint origin) → 0600 `<config
    dir>/preflight.key`. Missing key → Mode 0 before any network attempt.

- **Aspect:** Mode 0 parity
  - **Contract:** Missing file, explicit 0 and every failure path render the
    legacy discovery cards byte-identically; memory effects run exactly once per
    prompt; zero egress (asserted by tests).

- **Aspect:** Selector
  - **Contract:** Never executes, never sees history/tool
    payloads/memory/credentials. Input: bounded intent + compact catalog cards +
    locally served lookup pages. Output: `selected` (1-12 typed registry IDs),
    `abstain` (inject nothing), `lookup` (1-4 queries, one extra round) or
    `unresolved`. At most two inference rounds.

- **Aspect:** Validation
  - **Contract:** Typed IDs resolve exactly (no name-surface aliasing); skill
    delivery requires an existing file under allowed roots (`loaded` only when
    natively linked); MCP requires `api_config.server_state` visibility; one
    unavailable required item → Mode 0 fallback with diagnosis; optional items
    are dropped.

- **Aspect:** Package
  - **Contract:** One render inside the UserPromptSubmit slot (MAX_SKILL_CARDS,
    400 tokens): purpose, minimum instruction, exact tool names/references,
    `direct_read` vs `loaded` vs `callable` distinguished, registry revision
    digest included. Structured shrinking before any clamp; never a
    post-serialization cut.

- **Aspect:** Deadline
  - **Contract:** One monotonic deadline per prompt (default 2 s,
    `AE_PREFLIGHT_DEADLINE_MS`), socket timeouts derived from the remainder, no
    automatic retries (HTTP 429/5xx/timeout/refusal/invalid JSON → Mode 0 for
    the turn); redirects refused.

- **Aspect:** Mode 1
  - **Contract:** Adapter supplies `ae_native_selection` on the hook event,
    validated by the same handler. No native payload → Mode 0 for the turn. Mode
    1 never switches to Mode 2 automatically.

- **Aspect:** Diagnostics
  - **Contract:** One bounded stderr line per fallback (requested mode,
    effective mode, reason code); stdout stays the context channel. `doctor.py`
    reports an advisory summary; secrets never appear.

### 8.6 Checkout-local runtime and state

Maintainer authorization: on2026-11-19 the user explicitly selected that
all AE-owned venv/cache/memory must reside inside the checkout. This
supersedes previous user-scope defaults; schemas and selection modes stay
compatible. Canonical defaults are resolved from the installed source:

- `.agentenhancements/runtime/venv`: managed Python dependencies.
- `.agentenhancements/config`: model/key file and host/profile selection.
- `.agentenhancements/memory`: shared notes and observer data.
- `.agentenhancements/cache`: all AE-managed caches and temporary work.

The state directory is ignored by git and private0700. The optional
`AGENT_ENHANCEMENTS_STATE_DIR` provides an absolute isolation override;
existing explicit memory/API/model overrides remain available for tests.
Project-local deployments keep overrides under the checkout. Native host
configuration is a bridge to project code, not storage for AE dependencies.
Setup refreshes owned paths after relocation and preserves unrelated
user configuration. No automatic import/deletion of global state occurs.
