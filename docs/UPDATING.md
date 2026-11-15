---
title: Updating Guide
version: 2.1
last_updated: 2026-11-15
audience: users, devops, maintainers
---

# Updating Guide

## 1. Overview

This guide covers all update procedures for the AgentEnhancements project.

> **Vendoring reality (read first).** All eleven source directories
> (`agentic-awesome-skills/`, `ECC/`, `anthropic-skills/`, `claude-mem/`,
> `headroom/`, `ponytail/`, `superpowers/`, `replica-skill/`,
> `agency-agents/`, `system-prompts-and-models-of-ai-tools/`,
> `task-observer/`) are **vendored full copies without `.git`**. There is
> nothing to `git pull` inside them. `update-skills.sh` therefore
> re-aggregates from what is on disk and prints per-source re-vendor
> instructions; refreshing upstream content is a deliberate, reviewed
> re-vendor procedure (§2.2), never an automatic pull. Upstream URLs and
> licenses per directory: root `LICENSE` notice + `docs/LICENSE_AUDIT.md`.

### Update Categories

| Category | Frequency | Command | Risk |
|----------|-----------|---------|------|
| Registry/aggregation refresh | Any time | `./unified-integration/update-skills.sh` | Low |
| Vendored source refresh (re-vendor) | Deliberate, reviewed | Manual (§2.2) | Medium |
| Project dependencies (requirements.txt) | As needed | Manual | Medium |
| Setup script | Per release | Git pull of this repo | Low |
| Agent CLIs | Per agent release | Agent-specific | Low |

---

## 2. Refreshing skills and the registry

### 2.1 Registry refresh (safe, repeatable)

```bash
cd <repo>
./unified-integration/update-skills.sh
```

What it actually does: re-runs the aggregation pipeline
(`setup.sh` → `all-skills.json` → `agent-registry.json`) from the vendored
copies on disk, and prints a per-source reminder that vendored directories
must be re-vendored to move to a new upstream version. Exit 0 means the
registry is consistent with the tree — not that upstreams were contacted.

Optional: `AGENT_ENHANCEMENTS_BUILD_HEADROOM=1 ./unified-integration/update-skills.sh`
also rebuilds the Rust headroom binary from the vendored source.

### 2.2 Re-vendor one source (the real update procedure)

```bash
# Example: agentic-awesome-skills (MIT code + CC-BY-4.0 content)
cd /tmp && git clone --depth 1 https://github.com/sickn33/agentic-awesome-skills.git fresh
diff -rq fresh "$AGENT_ENHANCEMENTS_BASE_DIR/agentic-awesome-skills" | head   # review drift
rm -rf "$AGENT_ENHANCEMENTS_BASE_DIR/agentic-awesome-skills"
mkdir -p "$AGENT_ENHANCEMENTS_BASE_DIR/agentic-awesome-skills"
cp -r fresh/. "$AGENT_ENHANCEMENTS_BASE_DIR/agentic-awesome-skills/"
rm -rf "$AGENT_ENHANCEMENTS_BASE_DIR/agentic-awesome-skills/.git"  # keep the vendor clean
```

Then: record the upstream commit you vendored in the commit message
(`chore(vendor): refresh <source> from <url>@<sha>`), re-run
`./unified-integration/setup.sh`, and run the regression suite
(`python3 unified-integration/tests/run-tests.py`). For sources with
license notices (claude-mem, headroom: Apache-2.0 + NOTICE), keep the
NOTICE files. Never silently drop or rewrite LICENSE files during a
re-vendor.

`task-observer` is **pinned** — refresh only through the checksumed
procedure in `task-observer/VENDORED.json` (details: `docs/TASK_OBSERVER.md`).

### 2.3 Verify Refresh

```bash
python3 unified-integration/scripts/registry.py stats
python3 unified-integration/scripts/load-skills.py claude-code "security audit"
bash unified-integration/scripts/link-skills.sh --status
```

---

## 3. Updating Core Dependencies

### 3.1 headroom (Rust, vendored)

```bash
cd "$AGENT_ENHANCEMENTS_BASE_DIR/headroom" && cargo build --release
# A new upstream version requires the §2.2 re-vendor procedure first.
```

### 3.2 claude-mem (Node.js, vendored)

claude-mem ships as a vendored source tree; AgentEnhancements uses its
concepts (SQLite memory, summarization) through its own parameterized-SQL
hooks and does not build or run the claude-mem daemon. Refreshing the
vendor is a §2.2 procedure; there is no per-update `npm run build` step in
this repository.

### 3.3 ECC (Node.js, vendored — test suite only)

```bash
cd ECC && npm install --no-audit --no-fund && npm run build:opencode
node tests/run-all.js
```

---

## 4. Updating This Repository

```bash
cd <repo>
git fetch origin
git log --oneline HEAD..origin/master
git pull --ff-only origin master
./unified-integration/setup.sh
```

Verify: `bash -n unified-integration/setup.sh` and
`python3 -m py_compile unified-integration/scripts/*.py`.

---

## 5. Updating Agent CLIs

Each agent updates itself (Claude Code auto-update, Cursor/Windsurf app
updates, `npm update -g` for Codex/Gemini CLI, `gh extension upgrade
copilot`, Kiro app updates). AgentEnhancements configuration survives CLI
updates because all activation files are marker-guarded or merged
non-destructively — re-run `setup.sh` only after an AE release.

---

## 6. Post-Update Verification Checklist

### 6.1 Core System
- [ ] `bash -n unified-integration/setup.sh` - Syntax OK
- [ ] `python3 -m py_compile unified-integration/scripts/*.py` - Python OK
- [ ] `python3 unified-integration/scripts/memory.py claude-code list` - Memory OK

### 6.2 Skills
- [ ] `python3 unified-integration/scripts/registry.py stats` - Registry builds
- [ ] `python3 unified-integration/scripts/load-skills.py claude-code "test"` - Skills load

### 6.3 Agent Configs (paths actually written by setup.sh)
- [ ] Claude Code: `~/.claude/settings.json` (merged) + `~/.claude/CLAUDE.md` (marker)
- [ ] Codex: `~/.codex/AGENTS.md` (marker) + `~/.codex/config.toml` (MCP)
- [ ] OpenCode: `~/.config/opencode/opencode.json[c]` + `AGENTS.md`
- [ ] Cursor: `~/.cursor/rules/agent-enhancements.mdc`
- [ ] Gemini: `~/.gemini/GEMINI.md` (reference config.yaml)
- [ ] Windsurf: `~/.codeium/windsurf/rules/agent-enhancements.md`
- [ ] Copilot/Kiro: reference configs only (`~/.config/github-copilot/config.yaml`, `~/.kiro/config.yaml`)

### 6.4 Tests
- [ ] `python3 unified-integration/tests/run-tests.py` - All pass
- [ ] `cd ECC && node tests/run-all.js` - Baseline unchanged

---

## 7. Rollback Procedures

### 7.1 Rollback a re-vendor

Vendored directories have no git history of their own — the rollback IS the
previous commit of this repository:

```bash
cd <repo>
git log --oneline -- <vendored-dir>          # find the previous vendor commit
git checkout <previous-commit> -- <vendored-dir>
./unified-integration/setup.sh
```

### 7.2 Full Rollback

```bash
# 1. Roll this repository back
git checkout <known-good-commit>

# 2. Re-run setup (marker-guarded merges converge to the old state)
./unified-integration/setup.sh

# 3. Per-file backups written during merges live next to each target as
#    <file>.backup.<timestamp> (0600) - restore them if a merge went wrong.
```

---

## 8. Troubleshooting Updates

| Issue | Solution |
|-------|----------|
| "Not a git repository ... skipping" in update-skills.sh | Expected for vendored sources — use §2.2 re-vendor |
| Cargo build fails | Update Rust: `rustup update`, check Cargo.toml |
| Tests fail after update | Compare against the baseline in `docs/audit/TEST_RESULTS.md` |
| Skill count dropped | Diff the vendored source vs upstream before/after re-vendor |
| Agent config not updated | Re-run setup.sh; check marker blocks were not hand-edited |
| Memory DB locked | Kill stale hooks: `lsof ~/.agent-memory/memory.db` |
