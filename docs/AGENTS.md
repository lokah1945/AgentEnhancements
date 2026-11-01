---
title: Agents
version: 1.1
last_updated: 2026-11-01
audience: users
---

# Agent Setup Guides

`setup.sh` auto-detects installed agents by probing `PATH` and merges the
enhancements (skills path, memory hooks, compression settings) into each
agent's own config file. Backups are written next to every modified file.

## Detection

| Agent | Detected via |
|-------|--------------|
| claude-code | `command -v claude` |
| codex | `command -v codex` |
| opencode | `command -v opencode` |
| cursor | `command -v cursor` |
| gemini-cli | `command -v gemini` |
| windsurf | `command -v windsurf` |
| copilot | `gh extension list` contains `copilot` |
| kiro | `command -v kiro` |

The result is written to `unified-integration/config/detected-agents.sh`
(machine-local, do not commit).

## Per-agent notes

### Claude Code
Hooks are merged into `~/.claude/settings.json`:
`PreToolUse`/`PostToolUse` save tool events, `Stop` saves the session
summary. `~/.claude/CLAUDE.md` is (re)written by setup - keep personal
instructions out of that file or re-add them afterwards.

### Codex / Gemini CLI / Windsurf / Copilot / Kiro
Config merged into each tool's YAML config (see
[CONFIGURATION.md](CONFIGURATION.md)). Prompt files are copied from
`system-prompts-and-models-of-ai-tools/` where a source exists for the
agent (Kiro ships `Mode_Clasifier_Prompt.txt`, `Spec_Prompt.txt`,
`Vibe_Prompt.txt`; the first is used). Copilot has no prompt source in the
vendored collection and is configured for skills/memory/compression only.

### OpenCode
Merged into `~/.config/opencode/config.json` (JSON, not YAML).

## Launching agents

```bash
unified-integration/launch-agent.sh <agent> [args...]
# or, when /usr/local/bin is writable:
agent-enhanced <agent> [args...]
```

The launcher validates the agent against the last detection run, initializes
memory, exports the standard environment variables and execs the agent.

## Customization

- Override any path: see the environment variables in
  [CONFIGURATION.md](CONFIGURATION.md).
- Re-run `setup.sh` after installing a new agent CLI; only detected agents
  are configured.
