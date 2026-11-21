# AgentEnhancements Architecture Falsification Memo

**Target Concept**: AE = capability integration layer (not a coding agent)  
**User**: Layperson who doesn't know capability names/activation  
**Goal**: Automatic selection/delivery at prompt start AND mid-task when needs emerge  
**Analogy**: Agent = diner, AE preflight = chef, Registry = pantry  
**Date**: 2026-11-21  
**Evidence Base**: runtime.py, adaptive_preflight.py, gateway.py, catalog.json, ADAPTIVE_PREFLIGHT.md, opencode-plugin/index.js, CONTRACT.md, registry.py, context_budget.py, api_config.py

---

## Executive Summary

AgentEnhancements implements a **static suggestion layer**, not the automatic capability integration layer described in the master prompt. The system registers and suggests capabilities via bounded cards, but the main agent must explicitly choose, read, and invoke everything. No mid-task discovery exists. Mode 1 (native auto) is explicitly uncertified. Plugin delivery is guide-only. MCP readiness for non-OpenCode hosts is unproven. The context budget is enforced but not achieved by default. The two-dimension status contract is correctly implemented in code but not surfaced to users.

---

## Concept Falsification

### Claim 1: AE automatically selects and delivers capabilities at prompt start
**Status: FALSIFIED** | **Severity: Critical**

**Actual Behavior**: AE renders **candidate cards** (L1 pointers) into the UserPromptSubmit hook injection slot. The main agent receives a list of skill names with one-line summaries. The agent must then explicitly choose a candidate, read its `.md` file, and follow its guidance. For MCP tools, the agent must invoke them by exact gateway name. No capability is automatically loaded, executed, or made available without the agent's deliberate action.

**Evidence**:
- `runtime.py:36-72` `skill_context()`: Returns "AgentEnhancements local skill candidates for this task (read the SKILL.md of one you choose...)" -- max_results=8 cards, each: "- name: summary"
- `adaptive_preflight.py:694-751` `render_package()`: delivery="direct_read": "read before related work: {path}"; delivery="callable": "use: {ref}" (exact tool names); delivery="loaded": "already active (natively linked)" -- but ADAPTIVE_PREFLIGHT.md line 179: "No current adapter supplies enough proof to emit loaded"
- `adaptive_preflight.py:540-558` `_resolve_entry(type=skill)`: Returns delivery="direct_read" with note="read the SKILL.md before the related work"; delivery="unavailable" if file missing
- CONTRACT.md §8.5: "The selector never executes anything. It returns typed registry IDs; AgentEnhancements resolves each ID to its canonical source, checks live readiness, and renders a bounded package for the main agent. The main agent keeps every decision and every permission: preflight only prepares guidance and names; execution stays with the host."

**Gap**: The master prompt promises "automatic selection/delivery at prompt start" and the chef/pantry analogy implies the agent (diner) receives prepared capabilities. Reality: the agent receives a menu (cards) and must fetch/cook each dish itself. **No automatic loading, no automatic tool enablement, no capability activation without explicit agent action.**

---

### Claim 2: Mid-task capability discovery when needs emerge
**Status: FALSIFIED** | **Severity: Critical**

**Actual Behavior**: Only static preflight at `UserPromptSubmit`. The `PreToolUse`/`PostToolUse` hooks only save the tool name to session memory (`runtime.py:166-176`). OpenCode's `context` hook (`opencode-plugin/index.js:202-240`) validates the snapshot and falls back to Mode 0 if the registry or tool inventory changed -- it does **not** trigger new capability discovery. There is no agent-triggered, on-demand discovery path mid-task.

**Evidence**:
- `runtime.py:166-176` `handle()`: Only saves tool name to memory on PreToolUse/PostToolUse
- `opencode-plugin/index.js:202-240` context hook: Checks registryStamp() and sameInventory(); if changed, falls back to Mode 0 cards; no new registry search, no adaptive_preflight re-run
- `adaptive_preflight.py:1065-1167` `preflight_context()`: Only called from runtime.py on UserPromptSubmit; no hook for mid-task invocation

**Gap**: The master prompt requires "mid-task when needs emerge." Reality: one shot at prompt start; mid-task only saves tool names for memory recall. **No mechanism for the agent to request new capabilities during a task.**

---

### Claim 3: Mode 1 (Native Auto) certified for Claude Code/Codex
**Status: FALSIFIED** | **Severity: Critical**

**Actual Behavior**: Mode 1 requires the host adapter to supply `ae_native_selection` on the hook event (`adaptive_preflight.py:1096-1107`). The ADAPTIVE_PREFLIGHT.md explicitly states: **"Neither installed hook currently produces a certified native handoff: both use Mode 0 when the payload is absent."** Certification gates (native authentication, resolvable lightweight model, tool restrictions, recursion prevention, adapter deadline, delivery before first main request) are documented as unmet. No demonstration exists.

**Evidence**:
- `adaptive_preflight.py:1096-1107`: Requires agent in ("claude-code", "codex"), checks for `ae_native_selection` dict, rejects `lookup` decision
- ADAPTIVE_PREFLIGHT.md:145-159 (§Mode 1 contract): "Auto is targeted only at Claude Code and Codex. Neither installed hook currently produces a certified native handoff: both use Mode 0 when the payload is absent. A handoff must contain the final decision; a native lookup payload falls back. OpenCode rejects Auto even if supplied a test payload, and uses Custom for preflight inference. Native authentication, a resolvable lightweight model, tool restrictions, recursion prevention, an adapter deadline starting before inference, and delivery before the first main request remain certification gates. A fixture payload does not satisfy them. Claude's documented agent hook is a verifier with tools and a verification response schema; no arbitrary selection handoff was demonstrated. No headless wrapper or subscription inference was attempted in the local-fixture-only implementation scope. Installed versions inspected: Claude Code 2.1.327 and Codex CLI 0.167.2."

**Gap**: Mode 1 is a **specification without implementation** for the target hosts. The code accepts a native payload but no hook produces one. The documentation admits this honestly. **Mode 1 is vaporware for Claude Code/Codex.**

---

### Claim 4: Plugin catalog entries are callable runtimes
**Status: FALSIFIED** | **Severity: Critical**

**Actual Behavior**: `catalog.json` lists 39 "integrated-ready" and 1 "integrated" (anthropic-skills). But `adaptive_preflight.py:560-581` `_resolve_entry` for plugins: **required → delivery="unavailable"**, **optional → delivery="direct_read" (guide only)**. The ADAPTIVE_PREFLIGHT.md (§Output contract) states: "Plugin delivery is guidance. Reading an integration guide is not activating a plugin runtime; the package says so explicitly." No plugin runtime entry point is proven or wired.

**Evidence**:
- `catalog.json:13-37` (sample entry): "status": "integrated-ready", "guide_path": "plugin-catalog/code/agent-skills-addyosmani/SKILL.md", "mcp_servers": ["browser-tools-mcp", "lighthouse-mcp", "pa11y-mcp"]
- `adaptive_preflight.py:560-581` `_resolve_entry(type=plugin)`: If required, returns delivery="unavailable" with note="required plugin runtime entry point is not proven in this host session"; if optional and guide exists, returns delivery="direct_read" with note="guide only ({status}); runtime entry points follow the guide and host permissions"
- ADAPTIVE_PREFLIGHT.md:181-187: "Type: plugin - Proof before the main request: the optional guide file exists - Delivery: optional direct_read guidance only. Required plugin IDs conservatively fall back because a catalog-plugin runtime entry point is not proven... Nothing is installed or enabled from a selector result."
- ADAPTIVE_PREFLIGHT.md:344-345: "Plugin delivery is guidance. Reading an integration guide is not activating a plugin runtime; the package says so explicitly."

**Gap**: The catalog's "integrated-ready" status means "guide + routing shipped; upstream not vendored -- user installs it" (CONTRACT.md §8.1). But users and agents see "integrated-ready" and assume callable capability. **Zero plugins are callable runtimes; all are guide-only.**

---

### Claim 5: MCP server_state() visibility = callable tools for all hosts
**Status: PARTIALLY FALSIFIED** | **Severity: High**

**Actual Behavior**: `gateway.py:307-371 tools()` filters by `server_state()` visibility. `opencode-plugin/index.js:45-63 hostInventory()` provides **session-bound, exact tool inventory** via `ctx.tool.list()` + `ctx.mcp.list()` -- this works for OpenCode. **Claude Code and Codex have NO session tool inventory proof.** `adaptive_preflight.py:460-490 _host_tools()` only accepts OpenCode's inventory; other hosts "fail closed for MCP delivery until their own session tool observation is demonstrated."

**Evidence**:
- `gateway.py:322-324 tools()`: Filters sources by `server_state(name, config)["visible"]`
- `api_config.py:312-351 server_state()`: Returns visible=True for built-ins if "local_tools_available" or "configured"; for externals checks command exists, required keys present; **NO actual connection test, NO tool listing from live server**
- `opencode-plugin/index.js:45-63 hostInventory()`: Calls `ctx.tool.list()` and `ctx.mcp.list()` (OpenCode 2 plugin APIs); validates gateway="agent-enhancements", session_id match, api_revision match; returns exact tool names, schemas, codemode flags
- `adaptive_preflight.py:460-490 _host_tools()`: "OpenCode's supported tool.list surface is currently the only adapter supplying this private metadata. Other hosts fail closed for MCP delivery until their own session tool observation is demonstrated." Raises PreflightError for non-OpenCode.

**Gap**: `server_state()` visibility is a **static config check**, not a live connectivity/tool proof. Only OpenCode has a session-bound inventory. For Claude Code/Codex, MCP tools are **advertised but not proven callable** in the current session. The gateway's `tools/list` returns schemas, but the main agent has no proof those tools will succeed.

---

### Claim 6: Cold start ≤4000 tokens achieved by default
**Status: UNVERIFIED / UNLIKELY** | **Severity: Medium**

**Actual Behavior**: The budget constants exist in `context_budget.py` and `clamp_to_budget()` is used at every injection point. But `setup.sh` does not enable headroom proxy/native compaction by default (line 1394: `HEADROOM_CMD=""` unless binary found or built). The L0 map (`skills/library-map.json`), native skill descriptions, tool schemas, observer, memory, and prompt slot all add up. The ADAPTIVE_PREFLIGHT.md verification table shows Mode 0 cold start at 3,943 tokens (paired baseline) -- barely under 4,000, with no headroom. No evidence the default install achieves the budget with margin.

**Evidence**:
- `context_budget.py:22-33`: MAX_COLD_START_TOTAL = 4,000; MAX_NATIVE_DESCRIPTION_TOTAL = 2,500; MAX_TOOL_SCHEMA_TOTAL = 1,800; MAX_MEMORY_RECALL = 600; MAX_OBSERVER_AMBIENT = 250; MAX_SKILL_CARDS = 400; Sum of allocations = 4,000+ (native_desc + tool_schema alone = 4,300)
- `setup.sh:1369-1396 setup_compression()`: HEADROOM_CMD="" unless binary exists or AGENT_ENHANCEMENTS_BUILD_HEADROOM=1; "headroom not found, using fallback" is the common path
- ADAPTIVE_PREFLIGHT.md:294-311 verification table: Mode 0 cold start 3,943 tokens = 98.6% of budget, zero headroom
- CONTRACT.md §8.4: "Rules: --set all is never default (audited via link-skills.sh --audit)..."

**Gap**: The budget is **enforced by clamping**, not **achieved by design**. The default installation (no headroom binary, --set all disabled) runs at the edge of the limit. Any addition (more native skills, more MCP tools, longer memory recall) exceeds budget silently via truncation notes. The "context-frugal default profile" is a clamp, not a fit.

---

### Claim 7: Two-dimension status contract (implementation vs runtime) correctly separated
**Status: IMPLEMENTED IN CODE, NOT SURFACED** | **Severity: Low**

**Actual Behavior**: The code correctly separates the two dimensions: **Implementation status** in manifests (`catalog.json status`, `mcp-servers.json status`) and **Runtime readiness** computed via `api_config.server_state()` and `registry.py _skill_readiness()`/`_mcp_readiness()`. `usable_entries()` filters MCP by visibility. Parent status never implies child status. However, this separation is **not surfaced to users or agents** -- the registry cards show a single "ready" field blending both dimensions, and the catalog's "integrated-ready" label conflates implementation with usability.

**Evidence**:
- CONTRACT.md §8.1 (lines 291-329): "Every capability carries TWO independent status dimensions. One must never be inherited from the other, nor from a parent entry: - Dimension: Implementation status -- Where it lives: Manifest field status... - Dimension: Runtime readiness -- Where it lives: Computed at runtime per host/provider -- never stored in manifests"
- `registry.py:390-398 usable_entries()`: Filters MCP by `api.server_state(entry["name"], config)["visible"]`
- `registry.py:689-729 _skill_readiness()`: Checks file existence under allowed roots; checks native linking (~/.claude/skills, ~/.agents/skills); returns {"ready": "yes", "how": "natively linked"} or "on-demand read"
- `registry.py:732-746 _mcp_readiness()`: Calls `api_config.server_state()`; returns visibility reason
- `registry.py:757-775 _card()`: Single "ready" field merges both dimensions; "blocker" shows runtime reason only

**Gap**: Code enforces the contract; UI/reporting violates it. Agents see "ready: yes" or "ready: no" without knowing which dimension failed. The catalog's "integrated-ready" status is an implementation-status label that users interpret as runtime-ready.

---

## Architectural Blockers (Require Maintainer Approval)

### Blocker 1: Mode 1 Native Auto is Spec-Only
No hook adapter (Claude Code, Codex) produces `ae_native_selection`. The certification gates (native auth, lightweight model, tool restrictions, recursion prevention, adapter deadline, pre-first-request delivery) are undemonstrated. Decision required: invest in hook-side selector implementations, or deprecate Mode 1 and document Mode 2 (custom model) as the only automatic path.

### Blocker 2: No Mid-Task Discovery Architecture
The hook system only supports `UserPromptSubmit` (prompt start). Adding mid-task discovery requires either: (a) a new hook event type that agents support, (b) a background capability that agents can call on demand, or (c) the agent explicitly invoking `registry.py search/map` via tool use. Current design has none.

### Blocker 3: Plugin Runtime Gap
40 plugins in catalog, 0 callable. The "integrated-ready" label promises more than "guide only." Options: (a) build plugin runtime loader (like skills loader), (b) re-label catalog status to "guide-available," (c) wire plugin-suggested MCP servers as the actual capability surface.

### Blocker 4: MCP Session Proof for Non-OpenCode Hosts
Claude Code and Codex lack a session-bound tool inventory API. Without it, `_host_tools()` fails closed, MCP delivery is unproven, and adaptive preflight falls back to Mode 0. Requires either host-side inventory APIs or a gateway-side session registry that all hosts can query.

### Blocker 5: Context Budget Headroom
Default install runs at 98.6% of cold-start budget (3,943/4,000). Headroom binary not built by default. No compaction proxy. Options: (a) make headroom build mandatory in setup.sh, (b) reduce default native skill linking, (c) increase budget contract (breaking change), (d) accept truncation as normal.

---

## Minimal Alternatives (If Concept Cannot Be Met)

### Alternative 1: Honest "Capability Menu" Layer (Current Reality)
Accept that AE is a **discovery and suggestion layer**, not an integration layer. Rename "preflight" to "capability-menu". Document: "AE suggests capabilities; you choose, read, and invoke." Remove chef/pantry analogy. This matches current behavior exactly.

### Alternative 2: Mode 2 (Custom Model) as Primary Automatic Path
Deprecate Mode 1. Invest in Mode 2 (user-configured endpoint) as the only automatic selector. The selector already works (ADAPTIVE_PREFLIGHT.md verification table shows Mode 2 cold start 3,483 tokens). Document clearly: "Automatic capability selection requires your own model endpoint (OpenRouter, etc.)."

### Alternative 3: On-Demand Capability Tools
Expose `registry.py search/map/show` as callable MCP tools (via gateway) so the main agent can discover capabilities mid-task by invoking tools. This provides mid-task discovery without new hook events. The agent calls `ae_registry_search` → gets cards → calls `ae_registry_show` → reads SKILL.md.

### Alternative 4: Plugin → MCP Mapping as Runtime
Since plugins are guide-only but each declares `mcp_servers`, make the **MCP servers the actual callable runtime**. The plugin guide becomes "which MCP tools to use for this task." The selector selects MCP tools directly (already supported via `tool:<server>/<name>` IDs). Plugins become routing metadata, not capabilities.

### Alternative 5: Session-Bootstrap Capability Set
At `SessionStart`, pre-resolve a broad capability package (all MCP tools, native skills, built-ins) and inject it once. The agent has everything available from turn 1. No mid-task discovery, but also no prompt-start latency. Trades cold-start budget for availability. Requires raising budget or aggressive compaction.

---

## Summary Table

| Claim | Status | Severity | Key Evidence Location |
|-------|--------|----------|----------------------|
| Auto selection/delivery at prompt start | FALSIFIED | Critical | runtime.py:36-72, adaptive_preflight.py:694-751 |
| Mid-task capability discovery | FALSIFIED | Critical | runtime.py:166-176, opencode-plugin/index.js:202-240 |
| Mode 1 certified for Claude/Codex | FALSIFIED | Critical | adaptive_preflight.py:1096-1107, ADAPTIVE_PREFLIGHT.md:145-159 |
| Plugins are callable runtimes | FALSIFIED | Critical | catalog.json, adaptive_preflight.py:560-581, ADAPTIVE_PREFLIGHT.md:181-187 |
| MCP server_state = callable for all hosts | PARTIAL | High | gateway.py:307-371, opencode-plugin/index.js:45-63, adaptive_preflight.py:460-490 |
| Cold start ≤4000 tokens by default | UNVERIFIED | Medium | context_budget.py, setup.sh:1369-1396, ADAPTIVE_PREFLIGHT.md:294-311 |
| Two-dimension status correctly separated | CODE ONLY | Low | CONTRACT.md §8.1, registry.py:390-775 |

---

*This memo is evidence-based. All claims reference specific file paths and line numbers in the AgentEnhancements codebase as of 2026-11-21. No opinions -- only traced behavior.*