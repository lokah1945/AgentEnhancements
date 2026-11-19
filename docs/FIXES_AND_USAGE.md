---
title: Fixes and Usage Notes
version: 1.1
last_updated: 2026-11-15
audience: users, maintainers
---

## AgentEnhancements - Fixes and Usage Guide

### Overview

This document summarizes the critical bugs fixed in the unified integration
setup script and provides guidance on using the project with various AI coding
agents (Claude Code, Codex, OpenCode, Cursor, Gemini CLI, Windsurf, Copilot,
Kiro).

### Critical Bugs Fixed

#### 1. Skill Copying Limit (FIXED)

**Original Bug**: The `aggregate_skills()` function used `mapfile -d '' -n 20`
which limited processing to only 20 skills per source directory.

**Impact**: Only 20 skills from ECC, Ponytail, and Superpowers would be copied
instead of all available skills.

**Fix**: Replaced with a `while read` loop using `find -print0` that processes
ALL skills.

#### 2. Date Expansion Bug (FIXED)

**Original Bug**: `$(date -Iseconds)` inside a single-quoted Python heredoc -
written literally instead of expanded.

**Impact**: The `last_updated` field in `all-skills.json` contained the literal
string `$(date -Iseconds)`.

**Fix**: Used Python's `datetime.utcnow().isoformat() + 'Z'` for proper ISO 8601
timestamps.

#### 3. Skills Not Actually Aggregated (FIXED)

**Original Bug**: The unified `all-skills.json` only contained skills from
`agentic-awesome-skills`. Skills from ECC, Ponytail, and Superpowers were copied
to the filesystem but not included in the index.

**Impact**: Skills loader couldn't find skills from ECC, Ponytail, or
Superpowers.

**Fix**: All sources are now parsed and added to the unified index with complete
metadata (category, tags, tools, risk, description, when_to_use).

#### 4. Category Mapping Missing (FIXED)

**Original Bug**: All external skills were dumped into `by-category/general/`
ignoring the actual category from SKILL.md frontmatter.

**Impact**: Skills couldn't be discovered by category; poor organization.

**Fix**: Parses `category` from SKILL.md frontmatter and copies to correct
`by-category/<category>/` directory. Unknown categories default to `general`.

#### 5. Incomplete Skill Copying (FIXED)

**Original Bug**: Only `SKILL.md` was copied, missing `references/`, `scripts/`,
and other supporting files.

**Impact**: Skills with reference documentation or scripts were incomplete.

**Fix**: Uses `cp -r` to copy entire skill directory recursively.

#### 6. SQL Injection in Memory Hooks (FIXED)

**Original Bug**: Bash memory hooks used string interpolation directly in SQL
queries:

```bash
sqlite3 ... "INSERT ... VALUES ('$AGENT', '$project', ...)"
```

**Impact**: Potential SQL injection if memory values contain quotes or special
characters.

**Fix**: Rewrote memory hooks in Python using parameterized queries (`?`
placeholders). Bash wrappers maintained for backward compatibility.

#### 7. Hardcoded Paths (FIXED)

**Original Bug**: `/root/agent-enhancements/` hardcoded throughout the script.

**Impact**: Project couldn't be relocated; failed if installed elsewhere.

**Fix**: Uses `BASE_DIR` variable with `AGENT_ENHANCEMENTS_BASE_DIR` environment
variable override.

#### 8. Fallback JSON with Fake Counts (FIXED)

**Original Bug**: Hardcoded skill counts (2884, 150, 200, etc.) in fallback JSON
that didn't reflect reality.

**Impact**: Misleading statistics if primary skills index unavailable.

**Fix**: Fallback removed; actual counts generated from parsed skills.

#### 9. Prompt Path Mismatches (FIXED)

**Original Bug**: Assumed specific paths that may not match actual directory
structure in `system-prompts-and-models-of-ai-tools`.

**Impact**: System prompts not found for some agents.

**Fix**: Uses flexible glob patterns (`**/*pattern*`) to find prompts in actual
directories.

#### 10. Headroom Binary Detection Logic (FIXED)

**Original Bug**: Flawed logic in `compress.sh` for finding headroom binary.

**Impact**: Compression fallback used even when headroom was available.

**Fix**: Proper detection priority: built binary > PATH > source build.

### Additional Improvements

- **Agent Detection**: Improved Codex/Copilot detection reliability
- **Skill Loader**: Updated to read from new unified index format with all
  sources
- **Environment Variables**: Added for customization:
  - `AGENT_ENHANCEMENTS_BASE_DIR` - Override base directory
  - `AGENT_MEMORY_ROOT` - Override memory storage location
  - `HEADROOM_BIN` - Override headroom binary path
- **Cross-Agent Compatibility**: Skills copied to both `by-category/` and
  `by-agent/<tool>/` for better agent-specific loading
- **Update Script**: `update-skills.sh` refreshes the registry from vendored
  content; upstream updates require reviewed re-vendoring.

### Current usage

The fixes above are historical context. Current installation, native host
paths and capability counts are maintained in [AGENTS.md](AGENTS.md),
[CONFIGURATION.md](CONFIGURATION.md) and
[CAPABILITY_COUNTS.md](CAPABILITY_COUNTS.md).
Run these commands from the repository root:

```bash
bash unified-integration/setup.sh
python3 unified-integration/scripts/registry.py search "security audit"
python3 unified-integration/scripts/memory.py claude-code save convention \
  "Use TypeScript" user_preferences
python3 unified-integration/scripts/memory.py claude-code load convention user_preferences
unified-integration/compression/compress.sh session.log auto
```

The prompt hook suggests bounded candidate cards; the agent chooses which
skill instructions to read. The standalone compressor processes a file or
stdin, while session compaction belongs to the host CLI.

### Refreshing an installation

```bash
bash unified-integration/update-skills.sh
runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
"$runtime_python" unified-integration/tests/run-tests.py
```

The updater re-aggregates vendored content already on disk. Upstream refresh
uses the reviewed procedure in [UPDATING.md](UPDATING.md). Re-running setup
preserves user configuration and session data; deleting the integration
folders or the memory database is not a required rebuild step.

### Troubleshooting

Use [TROUBLESHOOTING.md](TROUBLESHOOTING.md) and the
[operations runbook](RUNBOOK.md) for the current diagnostics. Native host
configuration uses each host's supported paths; old reference files such as
Codex `config.yaml` do not activate native hooks. The generated source index
is rebuilt by setup and must never be edited manually.
