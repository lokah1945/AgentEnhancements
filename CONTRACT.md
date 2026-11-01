# AgentEnhancements Development Contract

**Project**: AgentEnhancements  
**Version**: 2.1  
**Effective Date**: 2026-11-01  
**Status**: BINDING - All agents MUST comply

---

## 1. Purpose & Scope

This contract establishes mandatory rules for ALL AI agents (Claude Code, Codex, Cursor, Gemini CLI, Copilot, Windsurf, Kiro, OpenCode, and any future agents) operating on this repository. It ensures unified direction, prevents conflicting changes, and maintains project integrity across all contributors.

**Applies to**: Every commit, edit, script, configuration, and documentation change in this repository.

---

## 2. Core Principles

### 2.1 Single Source of Truth
- **One setup script**: `unified-integration/setup.sh` (no variants, no "fixed" suffixes)
- **One skills index**: `unified-integration/skills/all-skills.json`
- **One memory system**: `unified-integration/memory/` with Python hooks
- **One compression system**: `unified-integration/compression/`

### 2.2 Agent Neutrality
- No agent-specific logic in shared infrastructure
- Agent-specific configs generated FROM shared source, not maintained separately
- All agents consume the same unified skills registry

### 2.3 Updateability First
- All external sources tracked as git submodules or documented remotes
- Update script (`unified-integration/update-skills.sh`) is the ONLY way to refresh skills
- No manual copying of skill files - always through aggregation pipeline

### 2.4 Full Auditability & Change Tracking (MANDATORY)
- **Every modification MUST be traceable to a specific agent and session**
- **All agents MUST use git for ALL changes** - no direct file writes bypassing version control
- **Commit metadata MUST include**: agent identity, session ID, task context, timestamp
- **No anonymous or untracked changes permitted** - enables full correction analysis

---

## 3. Mandatory Rules

### 3.1 File Operations

| Rule | Requirement |
|------|-------------|
| **R001** | Never create `*-fixed.*`, `*-new.*`, `*-v2.*` files. Edit the canonical file directly. |
| **R002** | All documentation changes go to `docs/` directory, never in root or scripts. |
| **R003** | Configuration templates in `unified-integration/` use environment variables, never hardcoded paths. |
| **R004** | Skills aggregated ONLY via `aggregate_skills()` function in setup.sh. No manual copies. |
| **R005** | ALL changes committed via git with agent-identifying metadata. |

### 3.2 Code Standards

| Rule | Requirement |
|------|-------------|
| **R101** | All hooks use parameterized queries (Python) - no SQL string interpolation. |
| **R102** | Bash scripts: `set -euo pipefail`, functions for logging, no global state mutation. |
| **R103** | Python scripts: type hints, docstrings, `if __name__ == "__main__":` entry point. |
| **R104** | No agent-specific imports in shared utilities (load-skills.py, memory.py, compress.py). |

### 3.3 Git Discipline & Agent Traceability

| Rule | Requirement |
|------|-------------|
| **R201** | Commit message format: `type(scope): subject` (conventional commits). |
| **R202** | One logical change per commit. No "fix + refactor + docs" in single commit. |
| **R203** | Push only after: tests pass, lint passes, docs updated in `docs/`. |
| **R204** | No force-push to main. PR required for structural changes. |
| **R205** | **Every commit MUST include agent signature**: `Co-Authored-By: <agent-name> <session-id>` |
| **R206** | **Agent identity MUST be declared** in commit body: `Agent: <agent-name> | Session: <id> | Task: <description>` |
| **R207** | **No direct filesystem writes** - all edits via git-tracked operations |
| **R208** | **Change log auto-generated** from commits for audit trail |

### 3.4 Skill Management

| Rule | Requirement |
|------|-------------|
| **R301** | New skill sources added via `setup.sh` aggregation function only. |
| **R302** | Skill metadata (category, tags, tools) MUST come from SKILL.md frontmatter. |
| **R303** | Entire skill directory copied (recursive), not just SKILL.md. |
| **R304** | Unified index regenerated from scratch on every aggregation run. |

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
|-------|---------------------------|
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
```
1. Read CONTRACT.md (this file) and docs/ARCHITECTURE.md
2. Create feature branch: git checkout -b type/short-description
3. Make minimal, focused changes
4. Run tests: cd ECC && node tests/run-all.js
5. Update docs/ if interfaces changed
6. Commit with conventional message + agent metadata
7. Push branch, create PR
```

### 5.2 Skill Update Flow (Monthly / On Demand)
```
1. Run: ./unified-integration/update-skills.sh
2. Review changes in unified-integration/skills/
3. Run: ./unified-integration/setup.sh
4. Verify all agent configs regenerated correctly
5. Commit: chore(skills): update from upstream sources
6. Push
```

### 5.3 Emergency Hotfix Flow
```
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
- **After skill updates**: Verify skill count in all-skills.json matches expectation

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
```
docs/
├── ARCHITECTURE.md          # System architecture
├── API.md                   # Internal APIs (skills loader, memory, compression)
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

### 8.1 Environment Variables (Immutable Interface)
| Variable | Purpose | Default |
|----------|---------|---------|
| `AGENT_ENHANCEMENTS_BASE_DIR` | Project root | `/root/agent-enhancements` |
| `AGENT_MEMORY_ROOT` | Memory storage | `~/.agent-memory` |
| `HEADROOM_BIN` | Compression binary | auto-detect |
| `AGENT_SKILLS_DIR` | Skills registry | `$BASE_DIR/unified-integration/skills` |

**Agents MUST NOT** introduce new required env vars without updating `docs/CONFIGURATION.md` and this contract.

### 8.2 File Paths (Canonical)
```
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
| Severity | Action |
|----------|--------|
| **Minor** (naming, style) | Auto-fix in CI, warning in PR |
| **Major** (hardcoded paths, SQL injection risk) | Block merge, require fix |
| **Critical** (schema change without approval, untracked changes) | Revert immediately, incident review |
| **Audit Failure** (missing agent identity) | Block push, require re-commit with metadata |

---

## 10. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.1 | 2026-11-01 | System | Added mandatory agent traceability (R205-R208), renamed project to AgentEnhancements |
| 2.0 | 2026-11-01 | System | Initial contract - replaces ad-hoc rules |
| 1.0 | 2026-10-15 | System | Implicit conventions (now formalized) |

---

## 11. Acknowledgment

**By operating on this repository, every agent acknowledges:**

> "I have read and understood CONTRACT.md. I will comply with all rules herein. I will not take actions outside my defined boundaries. I will document changes in `docs/` and follow the defined workflows. **I will ensure every change is traceable via git with my agent identity and session context.** I understand violations may result in reverted changes and loss of write access."

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
1. **Identify** - `git log --all --oneline --grep="<issue>"` to find related commits
2. **Trace** - `git show <commit> --format=fuller` to extract agent/session metadata
3. **Analyze** - Cross-reference session context with change impact
4. **Correct** - Apply fix with full audit trail
5. **Verify** - Regression test + update documentation

### 12.3 Mandatory Commit Metadata Format
```
type(scope): subject

Agent: <agent-name>
Session: <session-id>
Task: <task-description>
Context: <brief-context>

Co-Authored-By: <agent-name> <session-id>
```

---

**End of Contract**  
*This document is the supreme governing rule for this repository. No agent, human, or process may override it without explicit written approval from the project maintainers.*