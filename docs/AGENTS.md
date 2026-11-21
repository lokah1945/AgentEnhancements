---
title: Agents
version: 1.7
last_updated: 2026-11-21
audience: users
---

## Agent Setup Guides

`setup.sh` auto-detects installed agents by probing `PATH` and activates the
enhancements through each tool's **native configuration format**. Backups are
written next to every modified file, and marker-guarded instruction files
preserve your personal content across re-runs.

### Integration Level Summary

| Agent | Integration Level | Lifecycle Hooks | Skill Injection | MCP Gateway | Memory |
|-------|------------------|-----------------|-----------------|-------------|--------|
| **Claude Code** | **Native — Full** | ✅ 5/5 | ✅ Auto | ✅ | ✅ |
| **Codex** | **Native — Full** | ✅ 5/5 | ✅ Auto | ✅ | ✅ |
| **OpenCode 2** | **Native — Full** | ✅ 4/5* | ✅ Auto | ✅ | ✅ |
| **Hermes** | **Native — Full** | ✅ 3/3** | ✅ Auto | ✅ | ✅ |
| **Cursor** | Reference Config | ❌ | Manual | ❌ | Manual |
| **Gemini CLI** | Reference Config | ❌ | Manual | ❌ | Manual |
| **Windsurf** | Reference Config | ❌ | Manual | ❌ | Manual |
| **Copilot** | Reference Config | ❌ | Manual | ❌ | Manual |
| **Kiro** | Reference Config | ❌ | Manual | ❌ | Manual |

* OpenCode uses `prompt`/`context`/`idle` mapping (no explicit SessionStart)
** Hermes uses `pre_llm_call`/`post_llm_call`/`post_tool_call` mapping

> **Adaptive Preflight Mode 1 (Native) is currently unsupported** — no host exposes a pre-inference selection surface. Mode 0 (heuristic cards) and Mode 2 (custom endpoint) are available. See [ADAPTIVE_PREFLIGHT.md](ADAPTIVE_PREFLIGHT.md).

### Detection

| Agent | Detected via |
| ------- | -------------- |
| claude-code | `command -v claude` |
| codex | `command -v codex` |
| opencode | `command -v opencode` |
| hermes | `command -v hermes` |
| cursor | `command -v cursor` |
| gemini-cli | `command -v gemini` |
| windsurf | `command -v windsurf` |
| copilot | `gh extension list` contains `copilot` |
| kiro | `command -v kiro` |

The result is written to `unified-integration/config/detected-agents.sh`
(machine-local, do not commit).

An explicit native-agent selection survives subsequent setup runs. For example:

```bash
runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
"$runtime_python" unified-integration/scripts/native-integration.py \
  --select-agents claude-code,codex,opencode,hermes \
  --profile ilma --profile master-chief
bash unified-integration/setup.sh
```

The selection is stored outside git at
`.agentenhancements/config/host-selection.json`.
Only existing Hermes profiles are selected; sibling profiles remain untouched.

### Native skill activation (all agents)

Regardless of which agent is detected, `setup.sh` symlinks a curated skill
set into the directories that Agent Skills compatible harnesses read
automatically at runtime:

| Target | Read by |
| -------- | --------- |
| `~/.claude/skills/` | Claude Code (personal skills, auto-discovered) |
| `~/.codex/skills/` | Codex (native skills directory) |
| `~/.config/opencode/skills/` | OpenCode (native skills directory) |
| `~/.agents/skills/` | cross-agent Agent Skills standard (agentskills.io) |

The default links **task-observer** and the 15 **Superpowers** workflow skills
(16 total).
Other capabilities are discovered on demand through the library map and
registry.
`link-skills.sh --set curated` explicitly selects the 31-skill collection
(anthropic-skills, replica-skill and task-observer). Extend or remove links with
`unified-integration/scripts/link-skills.sh` (see [SKILLS.md](SKILLS.md)).

Claude Code can additionally consume the upstream marketplace:
`/plugin marketplace add anthropics/skills` (vendored at `anthropic-skills/`).

**Skill discovery is flexible**: default 8 skill cards per prompt, configurable
via `AE_MAX_SKILL_CARDS` env var. Agents decide which skills to actually
read/use from the suggestions.

### Per-agent notes

#### Claude Code 2.1.202 (verified)

Setup preserves user hooks while installing `SessionStart`, `UserPromptSubmit`,
`PostToolUse` and `Stop` handlers in `~/.claude/settings.json`. Events are read
from JSON on stdin, not fictional `TOOL_NAME` environment variables. Relevant
skill paths and prior session notes are supplied automatically. User-scope MCP
servers belong in `~/.claude.json`; the gateway loads all nine bundled backends.
`CLAUDE.md` is marker-merged, preserving personal instructions.
Custom gateway authentication remains entirely in Claude's native settings.
AgentEnhancements does not import its tokens, endpoints or helper into the
project. The shared [MCP configuration](CONFIGURATION.md) is independent of
the host agent's model-provider authentication.

#### Codex CLI 0.167.2 (verified)

Setup merges MCP servers into `~/.codex/config.toml`, lifecycle hooks into
`~/.codex/hooks.json`, instructions into `~/.codex/AGENTS.md`, and **native
skills** into `~/.codex/skills/`. `CODEX_HOME` is respected. Current Codex
supports lifecycle hooks. New or changed hooks require review through `/hooks`;
after trust is recorded, ordinary `codex` startup activates them automatically.
Setup never bypasses hook trust or tool permissions. A disabled hooks feature
or managed policy can prevent activation. Older Codex versions are not covered
by this check. Codex 0.169.0 was also tested in an isolated installation. Both
versions retain the MCP tool catalog within a turn; credential revocation is
enforced by the gateway even when the client still displays a cached name.
Newly added tools may require a fresh session. See
[configuration](CONFIGURATION.md).

**Full native integration**: 5/5 lifecycle hooks (SessionStart,
UserPromptSubmit, PreToolUse, PostToolUse, Stop), 16 native skills, MCP gateway,
memory persistence, and compression — equivalent to Claude Code.

#### OpenCode 2.3.0 (verified; 2.2.5 also tested)

Setup edits the existing `~/.config/opencode/opencode.jsonc`, or creates
`opencode.json` if JSONC is absent. Personal instructions, plugins, providers
and MCP entries are preserved. JSONC comments remain in the timestamped backup;
the merged document is serialized as JSON. `XDG_CONFIG_HOME` is respected.
**Native skills** are linked into `~/.config/opencode/skills/`.

The local `unified-integration/opencode-plugin` server plugin handles prompt
routing, context injection and session notes through OpenCode 2 lifecycle
hooks. It has no runtime npm dependencies. OpenCode loads plugins
asynchronously; a fresh `/api/plugin` response can be empty until location
initialization completes. Confirm the `agentenhancements` plugin reaches
`state.status: active` before treating an empty list as an installation failure.
The gateway is registered under `mcp.servers`, with `disabled: false` and
`codemode: false` to expose its available tools directly. Legacy flat entries,
`enabled` and `env` fields are migrated. The prompt hook waits for the managed
connection to settle so the first model request includes its tools.
OpenCode 1 plugin APIs differ and
are not supported by this adapter.
Setup checks the installed version before changing the OpenCode configuration.

**Full native integration**: lifecycle hooks, 16 native skills, MCP gateway,
memory persistence, and compression — equivalent to Claude Code.

#### Hermes Agent (native profiles)

Setup installs the shared MCP gateway in each selected profile's `config.yaml`,
adds a bounded library pointer to `SOUL.md`, and links the local
`unified-integration/hermes-plugin` as `plugins/agent-enhancements`.
The named plugin is enabled through Hermes's native `plugins.enabled` setting.
An explicitly disabled plugin or a conflicting user plugin causes an error.

The plugin uses `pre_llm_call`, `post_llm_call` and `post_tool_call` to discover
skills, recall notes and persist short task/session summaries. Conversation
history and tool payloads are never forwarded to AE. Model providers, persona
content and host approvals are preserved. `--mcp-only` installs only the
gateway.
`HERMES_HOME` is respected, including setup from a terminal whose environment
points at `<root>/profiles/<name>`. If `active_profile` points to a missing
profile, setup repairs it using the saved explicit profile selection.

Use `hermes -p ilma` or `hermes -p master-chief` normally. The installed Hermes
build reporting v0.17.0, upstream `f1345290`, passed native CLI tests for both
profiles. Compatibility requires its public plugin hook API; the test command
below verifies actual installation behavior rather than a version label alone.

#### Cursor (reference config only — no native hook integration)

Setup writes `~/.cursor/rules/agent-enhancements.mdc` (frontmatter-scoped
global rule). Cursor's real `~/.cursor/settings.json` is no longer
polluted with integration keys; fictional keys from older versions are
cleaned up (signature-checked).

**No automatic lifecycle hooks, skill injection, or MCP gateway registration.**
Use `registry.py search "<task>"` and `memory.py` CLI manually.

#### Gemini CLI (reference config only — no native hook integration)

Setup writes a marker-guarded section into `~/.gemini/GEMINI.md` (the
hierarchical global context file Gemini CLI loads at session start) and
keeps `~/.gemini/config.yaml` as a reference summary.

**No automatic lifecycle hooks, skill injection, or MCP gateway registration.**
Use `registry.py search "<task>"` and `memory.py` CLI manually.

#### Windsurf (reference config only — no native hook integration)

Setup writes `~/.codeium/windsurf/rules/agent-enhancements.md`. The
legacy `~/.windsurf/config.yaml` (never read by Windsurf) is removed
(signature-checked) when found.

**No automatic lifecycle hooks, skill injection, or MCP gateway registration.**
Use `registry.py search "<task>"` and `memory.py` CLI manually.

#### GitHub Copilot / Kiro (reference config only — no native hook integration)

`~/.config/github-copilot/config.yaml` and `~/.kiro/config.yaml` carry a
reference summary of the integration settings. Use these agents through
the launcher to get the full environment.

**No automatic lifecycle hooks, skill injection, or MCP gateway registration.**
Use `registry.py search "<task>"` and `memory.py` CLI manually.

### Native verification

```bash
runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
"$runtime_python" unified-integration/scripts/doctor.py
"$runtime_python" unified-integration/tests/smoke-native-clis.py --exercise-tools
"$runtime_python" unified-integration/tests/smoke-hermes.py
```

Doctor reads the selected hosts' actual configurations, starts their configured
MCP command, checks health and calls a local tool. It retains failed targets in
its report and exits nonzero on failure. These commands use local tools and
isolated model fixtures; provider account authentication must also be verified
through the native CLI. See [RUNBOOK.md](RUNBOOK.md).

### Marker-guarded files

Instruction files written by setup are wrapped in:

```text
<!-- agent-enhancements:begin -->
... integration content ...
<!-- agent-enhancements:end -->
```

Everything outside the markers is preserved verbatim, so personal
instructions survive every re-run of `setup.sh`.

### Launching agents

```bash
unified-integration/launch-agent.sh <agent> [args...]
# or, when /usr/local/bin is writable:
agent-enhanced <agent> [args...]
```

The launcher validates the agent against the last detection run, initializes
memory, exports the standard environment variables and execs the agent.

### Customization

- Override any path: see the environment variables in
  [CONFIGURATION.md](CONFIGURATION.md).
- Re-run `setup.sh` after installing a new agent CLI; only detected agents
  are configured.
- Manage natively linked skills (auto-discovered at runtime) with
  `unified-integration/scripts/link-skills.sh` (`--set <source>|all`,
  specific names, `--status`, `--unlink`).
- Map any task to skills, plugins and MCP servers with
  `python3 unified-integration/scripts/registry.py map "<task>"`.
