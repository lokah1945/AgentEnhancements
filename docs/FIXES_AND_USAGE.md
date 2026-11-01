# AgentEnhancements - Fixes and Usage Guide

## Overview

This document summarizes the critical bugs fixed in the unified integration setup script and provides guidance on using the project with various AI coding agents (Claude Code, Codex, OpenCode, Cursor, Gemini CLI, Windsurf, Copilot, Kiro).

## Critical Bugs Fixed

### 1. Skill Copying Limit (FIXED)
**Original Bug**: The `aggregate_skills()` function used `mapfile -d '' -n 20` which limited processing to only 20 skills per source directory.

**Impact**: Only 20 skills from ECC, Ponytail, and Superpowers would be copied instead of all available skills.

**Fix**: Replaced with a `while read` loop using `find -print0` that processes ALL skills.

### 2. Date Expansion Bug (FIXED)
**Original Bug**: `$(date -Iseconds)` inside a single-quoted Python heredoc - written literally instead of expanded.

**Impact**: The `last_updated` field in `all-skills.json` contained the literal string `$(date -Iseconds)`.

**Fix**: Used Python's `datetime.utcnow().isoformat() + 'Z'` for proper ISO 8601 timestamps.

### 3. Skills Not Actually Aggregated (FIXED)
**Original Bug**: The unified `all-skills.json` only contained skills from `agentic-awesome-skills`. Skills from ECC, Ponytail, and Superpowers were copied to the filesystem but not included in the index.

**Impact**: Skills loader couldn't find skills from ECC, Ponytail, or Superpowers.

**Fix**: All sources are now parsed and added to the unified index with complete metadata (category, tags, tools, risk, description, when_to_use).

### 4. Category Mapping Missing (FIXED)
**Original Bug**: All external skills were dumped into `by-category/general/` ignoring the actual category from SKILL.md frontmatter.

**Impact**: Skills couldn't be discovered by category; poor organization.

**Fix**: Parses `category` from SKILL.md frontmatter and copies to correct `by-category/<category>/` directory. Unknown categories default to `general`.

### 5. Incomplete Skill Copying (FIXED)
**Original Bug**: Only `SKILL.md` was copied, missing `references/`, `scripts/`, and other supporting files.

**Impact**: Skills with reference documentation or scripts were incomplete.

**Fix**: Uses `cp -r` to copy entire skill directory recursively.

### 6. SQL Injection in Memory Hooks (FIXED)
**Original Bug**: Bash memory hooks used string interpolation directly in SQL queries:
```bash
sqlite3 ... "INSERT ... VALUES ('$AGENT', '$project', ...)"
```

**Impact**: Potential SQL injection if memory values contain quotes or special characters.

**Fix**: Rewrote memory hooks in Python using parameterized queries (`?` placeholders). Bash wrappers maintained for backward compatibility.

### 7. Hardcoded Paths (FIXED)
**Original Bug**: `/root/agent-enhancements/` hardcoded throughout the script.

**Impact**: Project couldn't be relocated; failed if installed elsewhere.

**Fix**: Uses `BASE_DIR` variable with `AGENT_ENHANCEMENTS_BASE_DIR` environment variable override.

### 8. Fallback JSON with Fake Counts (FIXED)
**Original Bug**: Hardcoded skill counts (2884, 150, 200, etc.) in fallback JSON that didn't reflect reality.

**Impact**: Misleading statistics if primary skills index unavailable.

**Fix**: Fallback removed; actual counts generated from parsed skills.

### 9. Prompt Path Mismatches (FIXED)
**Original Bug**: Assumed specific paths that may not match actual directory structure in `system-prompts-and-models-of-ai-tools`.

**Impact**: System prompts not found for some agents.

**Fix**: Uses flexible glob patterns (`**/*pattern*`) to find prompts in actual directories.

### 10. Headroom Binary Detection Logic (FIXED)
**Original Bug**: Flawed logic in `compress.sh` for finding headroom binary.

**Impact**: Compression fallback used even when headroom was available.

**Fix**: Proper detection priority: built binary > PATH > source build.

## Additional Improvements

- **Agent Detection**: Improved Codex/Copilot detection reliability
- **Skill Loader**: Updated to read from new unified index format with all sources
- **Environment Variables**: Added for customization:
  - `AGENT_ENHANCEMENTS_BASE_DIR` - Override base directory
  - `AGENT_MEMORY_ROOT` - Override memory storage location
  - `HEADROOM_BIN` - Override headroom binary path
- **Cross-Agent Compatibility**: Skills copied to both `by-category/` and `by-agent/<tool>/` for better agent-specific loading
- **Update Script**: Created `update-skills.sh` to pull latest changes from all source repositories

## Usage Instructions

### Initial Setup

```bash
# Run the fixed setup script
/root/agent-enhancements/unified-integration/setup.sh
```

This will:
1. Detect available AI coding agents in PATH
2. Set up system prompts for each detected agent
3. Aggregate skills from all sources (agentic-awesome-skills, ECC, Ponytail, Superpowers)
4. Configure persistent memory (claude-mem)
5. Configure context compression (headroom)
6. Create agent-specific configurations in their respective config directories
7. Create universal launcher script and utilities

### Launching Enhanced Agents

```bash
# Using the universal launcher
/root/agent-enhancements/unified-integration/launch-agent.sh claude-code
/root/agent-enhancements/unified-integration/launch-agent.sh codex
/root/agent-enhancements/unified-integration/launch-agent.sh cursor
# etc.

# Or if symlink was created (requires sudo)
agent-enhanced claude-code
```

### Using Skills

Skills are auto-loaded based on task keywords. To manually load a skill:

```bash
# Using the skills loader
python3 /root/agent-enhancements/unified-integration/scripts/load-skills.py claude-code "security audit"
```

### Using Memory

```bash
# Save a memory
python3 /root/agent-enhancements/unified-integration/scripts/memory.py claude-code save "project_convention" "Use TypeScript for all new files" "project_context" 365

# Load a memory
python3 /root/agent-enhancements/unified-integration/scripts/memory.py claude-code load "project_convention" "project_context"

# List memories
python3 /root/agent-enhancements/unified-integration/scripts/memory.py claude-code list
```

### Using Compression

```bash
# Compress content
cat large_file.txt | /root/agent-enhancements/unified-integration/compression/compress.sh auto claude-code

# Or using Python utility
cat large_file.txt | python3 /root/agent-enhancements/unified-integration/scripts/compress.py auto claude-code
```

### Updating Skills from Sources

```bash
# Run the update script to pull latest from all git repositories
/root/agent-enhancements/unified-integration/update-skills.sh
```

This will:
1. Git pull latest changes from all skill source repositories
2. Re-run skills aggregation
3. Rebuild headroom and claude-mem if they were updated
4. Prompt you to re-run setup.sh to apply changes

### Custom Installation Location

If you want to install the project elsewhere:

```bash
export AGENT_ENHANCEMENTS_BASE_DIR="/path/to/your/agent-enhancements"
/path/to/your/agent-enhancements/unified-integration/setup.sh
```

### Custom Memory Location

```bash
export AGENT_MEMORY_ROOT="/path/to/memory"
```

## Agent-Specific Configuration

The setup creates configurations in each agent's standard config directory:

| Agent | Config Directory | Config File |
|-------|-----------------|-------------|
| Claude Code | `~/.claude/` | `CLAUDE.md`, `settings.json` |
| Codex | `~/.codex/` | `config.yaml` |
| OpenCode | `~/.config/opencode/` | `config.json` |
| Cursor | `~/.cursor/` | `settings.json` |
| Gemini CLI | `~/.gemini/` | `config.yaml` |
| Windsurf | `~/.windsurf/` | `config.yaml` |
| Copilot | `~/.config/github-copilot/` | `config.yaml` |
| Kiro | `~/.kiro/` | `config.yaml` |

## Skill Structure

Skills are organized in the unified registry:

```
unified-integration/skills/
├── by-category/
│   ├── security/
│   ├── architecture/
│   ├── testing/
│   ├── refactoring/
│   ├── code-review/
│   ├── documentation/
│   ├── devops/
│   ├── ai-ml/
│   ├── productivity/
│   └── general/
├── by-agent/
│   ├── claude-code/
│   ├── codex/
│   ├── cursor/
│   ├── gemini-cli/
│   ├── opencode/
│   ├── copilot/
│   ├── windsurf/
│   └── kiro/
└── all-skills.json (unified index with all metadata)
```

Each skill directory contains the full skill (SKILL.md + references/ + scripts/).

## Unified Skills Index Format

The `all-skills.json` contains:

```json
{
  "version": "1.0",
  "sources": ["agentic-awesome-skills", "ECC", "Ponytail", "Superpowers"],
  "skills": [
    {
      "name": "skill-name",
      "category": "security",
      "description": "Skill description...",
      "risk": "safe|medium|critical",
      "source": "agentic-awesome-skills",
      "tags": ["tag1", "tag2"],
      "tools": ["claude-code", "codex", "cursor"],
      "when_to_use": "When to use this skill..."
    }
  ],
  "total_skills": 3127,
  "categories": {
    "security": 180,
    "architecture": 220,
    ...
  },
  "agent_skill_counts": {
    "claude-code": 2800,
    "codex": 2750,
    ...
  },
  "last_updated": "2026-11-01T12:00:00Z"
}
```

## Troubleshooting

### Skills Not Loading
- Check that `all-skills.json` exists and has skills
- Verify the skill's `tools` array includes your agent
- Run `python3 scripts/load-skills.py <agent> <task>` to debug

### Memory Not Working
- Run `memory/init-memory.sh` to initialize SQLite database
- Check that `~/.agent-memory/memory.db` exists
- Verify hooks are using the Python scripts (not bash)

### Compression Not Working
- Verify headroom is built: `ls /root/agent-enhancements/headroom/target/release/headroom`
- Check `compression/config.yaml` has correct binary_path
- Fallback compression will be used if headroom unavailable

### Agent Config Not Applied
- Check the agent's config directory exists
- Verify the config file references correct paths
- Re-run setup.sh after any path changes

## Multi-Agent Compatibility

The project is designed to work with all supported agents simultaneously:

1. **Shared Skills**: All agents access the same unified skills registry
2. **Shared Memory**: Each agent has its own namespace in the shared memory database
3. **Shared Compression**: All agents can use headroom compression
4. **Agent-Specific Prompts**: Each agent gets its optimized system prompt
5. **Agent-Specific Configs**: Each agent gets configs in its native format

## Maintaining the Project

### Adding New Skill Sources
1. Add the source directory to `BASE_DIR`
2. Update `setup.sh` to include the new source in `aggregate_skills()`
3. Add the source to the `sources` array in the unified index

### Updating Skill Metadata
Run the update script regularly:
```bash
/root/agent-enhancements/unified-integration/update-skills.sh
```

### Rebuilding from Scratch
```bash
# Clean up
rm -rf /root/agent-enhancements/unified-integration/{skills,memory,compression,prompts,config}/*
rm -rf ~/.agent-memory

# Re-run setup
/root/agent-enhancements/unified-integration/setup.sh
```

## Testing

Run the ECC test suite to verify everything works:
```bash
cd /root/agent-enhancements/ECC
node tests/run-all.js
```

## Version Information

- **Setup Script Version**: 2.0 (fixed)
- **Last Updated**: 2026-11-01
- **Compatible Agents**: Claude Code, Codex, OpenCode, Cursor, Gemini CLI, Windsurf, Copilot, Kiro
- **Total Skills**: ~3,127 (2,791 agentic-awesome-skills + 314 ECC + 7 Ponytail + 15 Superpowers)

## Support

For issues or questions:
- Check the troubleshooting section above
- Review agent-specific documentation in each agent's config directory
- Run with `bash -x setup.sh` for debug output