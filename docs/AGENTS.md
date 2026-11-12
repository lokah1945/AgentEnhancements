---
title: Agents
version: 1.2
last_updated: 2026-11-13
audience: users
---

# Agent Setup Guides

`setup.sh` auto-detects installed agents by probing `PATH` and activates the
enhancements through each tool's **native configuration format**. Backups are
written next to every modified file, and marker-guarded instruction files
preserve your personal content across re-runs.

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

### Claude Code (full automatic activation)
Hooks are merged into `~/.claude/settings.json`:
`PreToolUse`/`PostToolUse` save tool events, `Stop` saves the session
summary. `~/.claude/CLAUDE.md` is (re)written by setup - keep personal
instructions out of that file or re-add them afterwards.

### Codex (instructions-based activation)
Codex reads `~/.codex/AGENTS.md` for global instructions and
`~/.codex/config.toml` (TOML) for settings. Setup writes a
marker-guarded integration section into `AGENTS.md` covering the skills
catalog, memory and compression commands. Codex has no hook system, so
memory is invoked explicitly per the instructions. Older setup versions
wrote `~/.codex/config.yaml`, which Codex never reads; setup removes it
(signature-checked) when found.

### OpenCode (native config + instructions)
Setup merges into `~/.config/opencode/opencode.json` using the official
schema (`$schema: https://opencode.ai/config.json`): the `instructions`
array points at the OpenCode system prompt and the `skills` array points
at `unified-integration/skills/by-category` (OpenCode scans grouping
directories up to six levels). A marker-guarded `AGENTS.md` in the same
directory documents the memory and compression commands. Older setup
versions wrote `config.json` with fictional keys; setup removes it
(signature-checked) when found.

### Cursor (global rule)
Setup writes `~/.cursor/rules/agent-enhancements.mdc` (frontmatter-scoped
global rule). Cursor's real `~/.cursor/settings.json` is no longer
polluted with integration keys; fictional keys from older versions are
cleaned up (signature-checked).

### Gemini CLI (global context file)
Setup writes a marker-guarded section into `~/.gemini/GEMINI.md` (the
hierarchical global context file Gemini CLI loads at session start) and
keeps `~/.gemini/config.yaml` as a reference summary.

### Windsurf (global rule)
Setup writes `~/.codeium/windsurf/rules/agent-enhancements.md`. The
legacy `~/.windsurf/config.yaml` (never read by Windsurf) is removed
(signature-checked) when found.

### GitHub Copilot / Kiro (reference config)
`~/.config/github-copilot/config.yaml` and `~/.kiro/config.yaml` carry a
reference summary of the integration settings. Use these agents through
the launcher to get the full environment.

## Marker-guarded files

Instruction files written by setup are wrapped in:

```
<!-- agent-enhancements:begin -->
... integration content ...
<!-- agent-enhancements:end -->
```

Everything outside the markers is preserved verbatim, so personal
instructions survive every re-run of `setup.sh`.

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
- To make individual skills natively auto-discoverable in any
  Agent Skills-compatible harness, symlink the skill folder into
  `~/.agents/skills/`.
