# Host Runtime Integration Audit Report

**Date:** 2026-11-21  
**Scope:** Unified Integration Layer — AgentEnhancements  
**Method:** Code inspection, test analysis, contract verification against `CONTRACT.md` §8

---

## Summary Classification

| Host | Native Activation | Lifecycle Events | Capability Delivery | Preflight Mode |
|------|-------------------|------------------|---------------------|----------------|
| Claude Code | **VERIFIED_FIXTURE** | 5/5 (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop) | Via `hookSpecificOutput.additionalContext` JSON | Mode 0 verified; Mode 1 **unsupported** (no native `ae_native_selection` producer) |
| Codex | **VERIFIED_FIXTURE** | 5/5 (same events via `hooks.json`) | Via `hookSpecificOutput.additionalContext` JSON | Mode 0 verified; Mode 1 **unsupported** (no native `ae_native_selection` producer) |
| OpenCode 2 | **VERIFIED_REAL_HOST** | 4/5 (prompt=UserPromptSubmit, context=continuation, idle=Stop, experimental.idle) | Via `context` hook system message injection | Mode 0, 2 **verified**; Mode 1 N/A |
| Hermes | **VERIFIED_FIXTURE** | 3/3 (pre_llm_call, post_llm_call, post_tool_call) | Via plugin `context` return value | Mode 0 **verified**; Mode 1/2 untested |
| Cursor | **DOCUMENTED_ONLY** | None (global `.mdc` rule only) | Reference file + `registry.py` CLI | None (no hook integration) |
| Gemini CLI | **DOCUMENTED_ONLY** | None (GEMINI.md + reference config.yaml) | Reference file + `registry.py` CLI | None |
| Windsurf | **DOCUMENTED_ONLY** | None (global rule only) | Reference file + `registry.py` CLI | None |
| Copilot | **DOCUMENTED_ONLY** | None (reference config.yaml only) | Reference file only | None |
| Kiro | **DOCUMENTED_ONLY** | None (reference config.yaml only) | Reference file only | None |

---

## 1. CLAUDE CODE

### native_activation: VERIFIED_FIXTURE
- setup.sh writes `~/.claude/settings.json` (merged, preserves user hooks/env) — **CONFIRMED** (`native-integration.py:170-185`)
- Hooks installed for all 5 events: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop — **CONFIRMED** (`native-integration.py:79-90`)
- UserPromptSubmit injects `skill_context` (Mode 0) or `preflight_context` (Mode 1/2) — **CONFIRMED** (`runtime.py:158-165`)
- **Mode 1: ae_native_selection** — **NOT PRODUCED** by any installed hook. The CONTRACT §8.5 and ADAPTIVE_PREFLIGHT.md §1.5 explicitly state: *"Neither installed hook currently produces a certified native handoff: both use Mode 0 when the payload is absent. A handoff must contain the final decision... Claude's documented agent hook is a verifier with tools and a verification response schema; no arbitrary selection handoff was demonstrated."* (ADAPTIVE_PREFLIGHT.md:145-160)
- Memory: AgentMemory saves session_context notes, recalls on SessionStart — **CONFIRMED** (`runtime.py:138-157`, `memory.py`)
- MCP: Gateway registered in `~/.claude.json` (user scope), tools visible via gateway — **CONFIRMED** (`native-integration.py:177-185`)
- Native skills: `link-skills.sh` symlinks curated set (task-observer + Superpowers) to `~/.claude/skills/` — **CONFIRMED** (`link-skills.sh:43`, `setup.sh:2535`)
- Test: `smoke-native-clis.py` runs claude-code with fixture model, verifies automatic notes — **CONFIRMED** (`smoke-native-clis.py:562-572`, `784-802`)

### lifecycle_events_covered
| Event | Implementation Ref |
|-------|-------------------|
| SessionStart | `runtime.py:138-157` — observer bootstrap + memory recall |
| UserPromptSubmit | `runtime.py:158-165` — memory save + preflight_context |
| PreToolUse | `runtime.py:166-176` — bounded tool name save |
| PostToolUse | `runtime.py:166-176` — bounded tool name save |
| Stop | `runtime.py:177-197` — redacted summary save + observer backstop |

### capability_delivery_proof
- **What reaches main model:** JSON `hookSpecificOutput.additionalContext` string injected via Claude Code's hook protocol
- **How verified:** `smoke-native-clis.py` runs `claude -p` with fixture model, asserts `AGENT_ENHANCEMENTS_FIXTURE_OK` in output and memory.db contains summary row (`smoke-native-clis.py:784-802`)

### preflight_mode_support
| Mode | Status | Evidence |
|------|--------|----------|
| 0 | **VERIFIED** | Default; `skill_context` discovery cards rendered (`runtime.py:36-72`) |
| 1 | **UNSUPPORTED** | No native producer for `ae_native_selection`; ADAPTIVE_PREFLIGHT.md:145-160 confirms |
| 2 | **IMPLEMENTED_UNVERIFIED** | Code path exists (`adaptive_preflight.py:1090-1111`) but no live test with real credentials |

### gaps_and_limitations
1. **Mode 1 not implemented** — No Claude Code hook produces `ae_native_selection`; would require a pre-hook inference surface that Claude Code doesn't expose
2. **Mode 2 untested with real credentials** — Only fixture tests exist
3. **Hook timeout** — 10s hardcoded (`native-integration.py:86`); may be tight for slow preflight
4. **MCP at user scope only** — `~/.claude.json` not project-scoped (`native-integration.py:177-185`)

---

## 2. CODEX

### native_activation: VERIFIED_FIXTURE
- setup.sh writes `~/.codex/AGENTS.md`, `hooks.json`, `config.toml` — **CONFIRMED** (`native-integration.py:186-196`, `setup.sh:1678-1704`)
- Native lifecycle hooks (5/5 events per README) — **CONFIRMED** (`native-integration.py:193-196` writes `hooks.json` with all 5 events)
- Shared MCP gateway, bounded skill discovery — **CONFIRMED** (`native-integration.py:188-191` merges MCP into `config.toml`)
- **Mode 1: ae_native_selection** — **NOT PRODUCED**. Same as Claude Code: ADAPTIVE_PREFLIGHT.md:145-160 states *"Neither installed hook currently produces a certified native handoff... Codex hooks reference"* — no arbitrary selection handoff demonstrated
- Test: `smoke-native-clis.py` runs codex with fixture model, verifies automatic notes — **CONFIRMED** (`smoke-native-clis.py:544-561`, `784-802`)

### lifecycle_events_covered
| Event | Implementation Ref |
|-------|-------------------|
| SessionStart | `runtime.py:138-157` — via `hooks.json` |
| UserPromptSubmit | `runtime.py:158-165` — via `hooks.json` |
| PreToolUse | `runtime.py:166-176` — via `hooks.json` |
| PostToolUse | `runtime.py:166-176` — via `hooks.json` |
| Stop | `runtime.py:177-197` — via `hooks.json` |

### capability_delivery_proof
- **What reaches main model:** JSON `hookSpecificOutput.additionalContext` string via Codex's `hooks.json` protocol
- **How verified:** `smoke-native-clis.py` runs `codex exec` with fixture model, asserts fixture response and memory.db summary row

### preflight_mode_support
| Mode | Status | Evidence |
|------|--------|----------|
| 0 | **VERIFIED** | Default; discovery cards |
| 1 | **UNSUPPORTED** | No native producer; ADAPTIVE_PREFLIGHT.md:145-160 |
| 2 | **IMPLEMENTED_UNVERIFIED** | Code path exists but no live credential test |

### gaps_and_limitations
1. **Mode 1 not implemented** — Same as Claude Code; Codex hooks don't expose a pre-inference selection surface
2. **Mode 2 untested with real credentials**
3. **TOML comment preservation** — Verified in tests (`test_native_automation.py:257-284`) but merge replaces hooks entirely
4. **User MCP servers preserved** — Tested (`test_native_automation.py:289-294`)

---

## 3. OPENCODE 2

### native_activation: VERIFIED_REAL_HOST
- setup.sh writes `~/.config/opencode/opencode.jsonc`, `AGENTS.md`, registers plugin — **CONFIRMED** (`native-integration.py:197-265`)
- opencode-plugin/index.js loaded as native plugin — **CONFIRMED** (`native-integration.py:260-262`, `opencode-plugin/index.js:181-258`)
- prompt hook → UserPromptSubmit equivalent, context hook → model continuation — **CONFIRMED** (`opencode-plugin/index.js:190-201` for prompt, `202-239` for context)
- hostInventory() uses `ctx.tool.list()` and `ctx.mcp.list()` — session-bound — **CONFIRMED** (`opencode-plugin/index.js:45-63`)
- MCP readiness: 1.5s polling, `tool.reload()` on connection — **CONFIRMED** (`opencode-plugin/index.js:122-139`)
- **Mode 2: Custom preflight with fixture selector** — **VERIFIED** with proof table in ADAPTIVE_PREFLIGHT.md §1.5 (table rows for Mode 2 scenarios)
- Test: `smoke-native-clis.py` for opencode, verifies automatic notes — **CONFIRMED** (`smoke-native-clis.py:573-606`, `653-668`, `784-802`)
- Test: `smoke-adaptive-preflight.py --mode 2` — **CONFIRMED** (`smoke-adaptive-preflight.py:148-371`, proof table ADAPTIVE_PREFLIGHT.md:294-302)

### lifecycle_events_covered
| Event | Implementation Ref |
|-------|-------------------|
| prompt (UserPromptSubmit equiv) | `opencode-plugin/index.js:190-201` — `readyMcp` + `runtime("UserPromptSubmit")` |
| context (continuation) | `opencode-plugin/index.js:202-239` — injects skills, memory, observer |
| experimental.idle (Stop equiv) | `opencode-plugin/index.js:241-252` — captures final assistant message |
| SessionStart | Implicit via first `prompt` hook (`previous` from `runtime("SessionStart")`) |

### capability_delivery_proof
- **What reaches main model:** System message parts injected via `context` hook (`input.system.push({type: "text", text})`)
- **How verified:** 
  - `test-opencode-plugin.mjs:60-86` asserts `security-audit` skill mentioned, `registry.py search` in context
  - `smoke-native-clis.py` runs `opencode run` with fixture, asserts fixture response and memory.db
  - `smoke-adaptive-preflight.py` validates exact tool declaration (`tools["agent-enhancements"].ffmpeg_probe`) in first request context (`smoke-adaptive-preflight.py:298-311`)

### preflight_mode_support
| Mode | Status | Evidence |
|------|--------|----------|
| 0 | **VERIFIED** | Default; `skill_context` cards via `runtime.py` |
| 1 | **N/A** | OpenCode rejects Auto (`adaptive_preflight.py:1097-1098`) |
| 2 | **VERIFIED_REAL_HOST** | `smoke-adaptive-preflight.py` proof table (8 scenarios); `test_adaptive_preflight.py` 73 tests |

### gaps_and_limitations
1. **Mode 1 explicitly rejected** — `adaptive_preflight.py:1097-1098` raises `mode1_host_unsupported`
2. **hostInventory only for opencode** — `_host_tools` returns `[]` for other agents (`adaptive_preflight.py:460-490`)
3. **MCP polling 1.5s** — Hardcoded; may need adjustment for slow networks
4. **Code Mode proof limited** — Only primitive object signatures (`ffmpeg_probe(path: string)`) certified (`opencode-plugin/index.js:86-118`)
5. **8s runtime subprocess timeout** — `opencode-plugin/index.js:150`

---

## 4. HERMES

### native_activation: VERIFIED_FIXTURE
- setup.sh writes selected profile `config.yaml`, `SOUL.md`, native plugin symlink — **CONFIRMED** (`native_hermes.py:79-130`)
- hermes-plugin bridges `pre_llm_call`, `post_llm_call`, `post_tool_call` — **CONFIRMED** (`hermes-plugin/__init__.py:31-48`)
- Mode support: check `native_hermes.py` — **Mode 0 only** (no preflight config integration in plugin)
- Test: `smoke-hermes.py` runs real Hermes profiles against localhost fixture — **CONFIRMED** (`smoke-hermes.py:50-84`)

### lifecycle_events_covered
| Event | Implementation Ref |
|-------|-------------------|
| pre_llm_call (SessionStart + UserPromptSubmit) | `hermes-plugin/__init__.py:33-37` — `runtime("SessionStart")` + `runtime("UserPromptSubmit")` |
| post_llm_call (Stop) | `hermes-plugin/__init__.py:39-40` — `runtime("Stop")` |
| post_tool_call (PostToolUse) | `hermes-plugin/__init__.py:42-44` — `runtime("PostToolUse")` |

### capability_delivery_proof
- **What reaches main model:** `context` field returned from `pre_llm_call` hook (`hermes-plugin/__init__.py:36-37`)
- **How verified:** `smoke-hermes.py` asserts fixture response and memory.db contains 2 summaries + 2 tasks per profile (`smoke-hermes.py:72-84`)

### preflight_mode_support
| Mode | Status | Evidence |
|------|--------|----------|
| 0 | **VERIFIED** | `runtime.py` skill_context path works via plugin |
| 1 | **UNIMPLEMENTED** | No `ae_native_selection` producer in Hermes |
| 2 | **UNIMPLEMENTED** | No preflight config wired in `native_hermes.py` |

### gaps_and_limitations
1. **Only Mode 0 supported** — Plugin calls `runtime.py` directly; no adaptive preflight integration
2. **No preflight config in Hermes profile** — `native_hermes.py` doesn't write `preflight` section to `config.yaml`
3. **Profile selection manual** — Requires `--profile` flags; no auto-detection of active profile
4. **Plugin symlink collision warning only** — User plugin preserved but no migration path (`native_hermes.py:106-108`)

---

## 5. CURSOR / GEMINI CLI / WINDSURF / COPILOT / KIRO

### Classification: DOCUMENTED_ONLY / REFERENCE CONFIG ONLY

These hosts receive **no native automation** — only reference configuration files that document how to use the AgentEnhancements library manually.

### What setup.sh writes

| Host | Files Written | Type |
|------|---------------|------|
| Cursor | `~/.cursor/rules/agent-enhancements.mdc` | Global rule (not alwaysApply) |
| Gemini CLI | `~/.gemini/GEMINI.md` + `~/.gemini/config.yaml` | Global context + reference config |
| Windsurf | `~/.codeium/windsurf/rules/agent-enhancements.md` | Global rule |
| Copilot | `~/.config/github-copilot/config.yaml` | Reference config only |
| Kiro | `~/.kiro/config.yaml` | Reference config only |

### Are these preflight hooks or just reference files?

**Just reference files.** None of these hosts have:
- Lifecycle hook integration (no SessionStart, UserPromptSubmit, etc.)
- Automatic skill/context injection
- Memory persistence via AgentEnhancements hooks
- MCP gateway auto-registration
- Any `runtime.py` execution

The generated files contain:
- Pointers to `registry.py search "<task>"` for on-demand skill discovery
- Memory CLI commands: `python3 .../memory.py <agent> save/load`
- Compression CLI: `.../compress.sh`
- Native skill activation note: `~/.agents/skills/` symlinked by `link-skills.sh`

### native_activation: DOCUMENTED_ONLY for all five

### lifecycle_events_covered: [] (empty array)

### capability_delivery_proof
- **What reaches main model:** Nothing automatic. User must manually invoke `registry.py`, `memory.py`, `compress.sh`
- **How verified:** No tests exist for these hosts in the test suite

### preflight_mode_support: 0 (none)

### gaps_and_limitations
| Host | Specific Gaps |
|------|---------------|
| Cursor | `.mdc` rule has `alwaysApply: false` — only triggers on relevance; no hook API access |
| Gemini CLI | `GEMINI.md` is hierarchical memory, not a hook; `config.yaml` reference only |
| Windsurf | Rules directory read at startup; no runtime hook mechanism |
| Copilot | VS Code settings only; no CLI hook integration |
| Kiro | Config file only; no documented hook system |

---

## Cross-Host Verification Matrix

| Capability | Claude Code | Codex | OpenCode 2 | Hermes | Cursor | Gemini | Windsurf | Copilot | Kiro |
|------------|-------------|-------|------------|--------|--------|--------|----------|---------|------|
| Settings merge (preserve user) | ✅ | ✅ | ✅ | ✅ | N/A | ✅ | ✅ | ✅ | ✅ |
| All 5 lifecycle hooks | ✅ | ✅ | 4/5* | 3/3** | ❌ | ❌ | ❌ | ❌ | ❌ |
| SessionStart memory recall | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| UserPromptSubmit injection | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Tool use tracking | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Stop summary save | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| MCP gateway registration | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Native skill symlinks | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Mode 0 preflight | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Mode 1 preflight | ❌ | ❌ | N/A | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Mode 2 preflight | Code only | Code only | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Fixture smoke test | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

* OpenCode uses `prompt`/`context`/`idle` mapping  
** Hermes uses `pre_llm_call`/`post_llm_call`/`post_tool_call` mapping

---

## Key Findings

### 1. Mode 1 (Native Selection) is Not Implemented for Any Host
The CONTRACT §8.5 and ADAPTIVE_PREFLIGHT.md explicitly document that **neither Claude Code nor Codex hooks produce `ae_native_selection`**. The architecture requires a pre-inference selection surface that neither host exposes. Mode 1 remains a theoretical contract.

### 2. OpenCode 2 is the Only Host with Verified Mode 2
The `smoke-adaptive-preflight.py` test provides a complete proof table (8 scenarios) demonstrating Mode 2 working end-to-end with a local fixture selector and main model. No other host has this verification.

### 3. Five Hosts Have Zero Runtime Integration
Cursor, Gemini CLI, Windsurf, Copilot, and Kiro receive only documentation-style configuration files. They cannot automatically invoke skills, persist memory, or discover MCP tools through AgentEnhancements hooks.

### 4. Memory & MCP Are Shared Across Native Hosts
Claude Code, Codex, OpenCode, and Hermes all share:
- `AgentMemory` SQLite backend (`memory.py`)
- MCP gateway via `ui.api.json` (`api_config.py`)
- `runtime.py` lifecycle handler

### 5. Native Skill Activation is Opt-In and Curated
`link-skills.sh` defaults to only `task-observer` + `Superpowers` (~2 skills). The full 3,378-skill catalog is **not** natively linked by default (audited via `link-skills.sh --audit`). This is a deliberate context-budget decision (CONTRACT §8.4).

---

## Recommendations

1. **Document Mode 1 as unsupported** — Update README/AGENTS.md to clarify that "native" preflight mode requires host capabilities that don't exist
2. **Add OpenCode 2 as reference implementation** — It's the only host with full Mode 0/2 verification
3. **Consider minimal Cursor/Gemini hooks** — If these hosts add hook APIs, implement `runtime.py` bridges
4. **Add live credential test for Mode 2** — Current tests use fixtures only; `AE_PREFLIGHT_LIVE=1` documented but not in CI
5. **Audit Hermes for Mode 2 support** — Plugin architecture could support it with minimal changes