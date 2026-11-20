---
title: Adaptive Preflight Capability Selection
version: 1.2
last_updated: 2026-11-20
audience: users, maintainers
---

## Adaptive Preflight Capability Selection

Implementation of the 2026-11-19 architecture review
("Audit Arsitektur Pemilihan Capability", roadmap stage 1: one shared
handler with fixtures). The runtime hook can now delegate capability
selection to an isolated selector before the main agent's first
inference, instead of only listing heuristic candidates.

### Model

One selector role, three modes, one validated package:

- **Mode:** 0 - disabled (default)
  - **Who assigns:** The hook uses the existing loader.
  - **Model used by the selector:** None: the main agent decides from the
    candidate cards.

- **Mode:** 1 - native
  - **Who assigns:** The host adapter supplies the selection through its own
    sanctioned inference surface.
  - **Model used by the selector:** The host's configured model.

- **Mode:** 2 - custom
  - **Who assigns:** The AE hook calls the user-configured endpoint.
  - **Model used by the selector:** The endpoint/sdk/model triple in the
    `ui.api.json` `preflight` section.

The selector never executes anything and never sees history, tool
payloads, memory, observations or credentials. Its input is the task
intent (bounded), a compact catalog view, and - on request - focused
lookup pages served by the local registry. Its output is a small JSON
document that names typed registry IDs. AgentEnhancements then:

1. resolves every ID to its canonical entry (exact typed-ID match),
2. proves delivery (readable skill references, exact tools observed in the
   current host session, built-ins),
3. renders one bounded package for the main agent, inside the same
   UserPromptSubmit slot the legacy cards occupied (400 tokens).

The main agent keeps every decision and every permission: preflight
only prepares guidance and names; execution stays with the host.

### Configuration

The `preflight` section of the private, ignored `<checkout>/ui.api.json`
(the single AE configuration file, see [configuration](CONFIGURATION.md)):

```json
"preflight": {"mode": 0}
```

```json
"preflight": {"mode": 1}
```

```json
"preflight": {
  "mode": 2,
  "endpoint": "https://openrouter.ai/api/v1",
  "sdk": "openai",
  "model": "provider/model-id",
  "api_key_ref": "PREFLIGHT_API_KEY"
}
```

Rules (enforced by `scripts/adaptive_preflight.py` and its tests):

- A missing file or missing `preflight` section is Mode 0 without a
  diagnosis.
- `mode` must be the exact integer 0, 1 or 2. Booleans, numeric strings,
  floats and out-of-range values fall back to Mode 0 with a diagnosis code
  on stderr. Malformed JSON, duplicate fields or a non-object section make
  the whole `ui.api.json` invalid (`ui_api_json_invalid`), which also hides
  credentialed MCP tools: fail closed.
- Mode 2 additionally requires `endpoint` (an HTTPS base URL without
  credentials or fragments), `sdk` (`openai` or `anthropic`), a non-empty
  `model` and an `api_key_ref` naming an `api_keys` reference (default
  `PREFLIGHT_API_KEY`). On Mode 0/1 these fields are stored but ignored,
  so switching modes never loses the custom setup.
- The file is re-read once per UserPromptSubmit. Writers should use
  atomic replace; changes apply from the next prompt.
- A legacy `.agentenhancements/config/model.json` is no longer read;
  `api_config.py migrate` imports it once (see below).

#### Protocol details (Mode 2)

- `sdk: "openai"` - Chat Completions at `<endpoint>/chat/completions`
  (OpenAI-compatible; for OpenRouter use `https://openrouter.ai/api/v1`).
  The request asks for a strict `response_format` JSON schema; if the
  endpoint answers HTTP 400 (unsupported parameter), exactly one
  immediate re-issue is made without `response_format` and the JSON is
  validated locally in full. That is a protocol-compatibility
  fallback, not an automatic retry: HTTP 429/5xx, timeouts, refusals
  and invalid JSON fall back to Mode 0 for the turn with no second
  request.
- `sdk: "anthropic"` - Messages API at `<endpoint>/v1/messages` (base
  URL without `/v1`, mirroring the Anthropic SDK). JSON is enforced
  through the prompt and validated locally.
- Redirects are refused: the validated origin must not silently move.
- `temperature` is 0 and output is capped at 500 tokens.

#### Credentials (Mode 2)

The key is `api_keys[api_key_ref]` in the same `ui.api.json` (an array;
one key is chosen per prompt, round-robin when several are listed). It is
never read from the shell environment, an OS keyring, a key file or
`model.json`, and it never enters the selector prompt or the main-agent
context. The previous sources (`AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY`,
keyring service `agentenhancements.preflight`, `<config dir>/preflight.key`)
are retired; `python3 unified-integration/scripts/api_config.py migrate`
imports an owner-only `preflight.key` and the legacy `model.json` once when
`ui.api.json` has no `preflight` section. Keyring entries are not imported:
copy that key into `api_keys.PREFLIGHT_API_KEY` by hand.

A missing key falls back to Mode 0 before any network attempt.

#### Mode 1 contract

The adapter supplies its native selection on the hook event:

```json
{
  "hook_event_name": "UserPromptSubmit",
  "prompt": "...",
  "ae_native_selection": {
    "decision": "selected",
    "items": [{"id": "skill:postgresql-optimization", "required": true}]
  }
}
```

The payload follows the same output contract as the custom selector
and is validated by the same handler - a typed decision, at most 12
items, optional `required` flags. A Mode 1 failure never switches to
Mode 2; the turn falls back to Mode 0 and the model source follows the
user's explicit choice.

Auto is targeted only at Claude Code and Codex. Neither installed hook
currently produces a certified native handoff: both use Mode 0 when the
payload is absent. A handoff must contain the final decision; a native
`lookup` payload falls back. OpenCode rejects Auto even if supplied a test
payload, and uses Custom for preflight inference.

Native authentication, a resolvable lightweight model, tool restrictions,
recursion prevention, an adapter deadline starting before inference, and
delivery before the first main request remain certification gates. A
fixture payload does not satisfy them. Claude's documented agent hook is a
verifier with tools and a verification response schema; no arbitrary
selection handoff was demonstrated. No headless wrapper or subscription
inference was attempted in the local-fixture-only implementation scope.
Installed versions inspected: Claude Code 2.1.327 and Codex CLI 0.167.2.
See the official [Claude hooks](https://code.claude.com/docs/en/hooks) and
[Codex hooks](https://developers.openai.com/codex/hooks) references.

### Output contract

The selector returns one of:

- `selected` - 1 to 12 typed registry IDs, ordered by importance.
  `required` defaults to true; false marks optional contributions.
- `abstain` - ordinary tools are enough; nothing is injected.
- `lookup` - 1 to 4 focused catalog queries; AE answers from the local
  registry and a second (final) inference round follows.
- `unresolved` - the catalog cannot satisfy a stated requirement.

Validation and resolution then prove, per item:

- **Type:** skill
  - **Proof before the main request:** the SKILL.md exists under an allowed root
  - **Delivery:** `direct_read` with the exact path and a read-before-work
    instruction. Directory links do not prove the body was loaded into this
    request. No current adapter supplies enough proof to emit `loaded`.

- **Type:** plugin
  - **Proof before the main request:** the optional guide file exists
  - **Delivery:** optional `direct_read` guidance only. Required plugin IDs
    conservatively fall back because a catalog-plugin runtime entry point is
    not proven. This also limits required guide-only contributions; request
    such guidance through the existing discovery/read workflow. Nothing is
    installed or enabled from a selector result.

- **Type:** mcp
  - **Proof before the main request:** current configuration permits the
    server and exact tools from it occur in a session-bound host inventory
  - **Delivery:** `callable` references name only those observed tools

- **Type:** `tool:<server>/<name>`
  - **Proof before the main request:** the exact gateway tool name, server
    mapping, host name/namespace, schema and current availability agree
  - **Delivery:** `callable` with the host's executable reference, e.g.
    `tools["agent-enhancements"].ffmpeg_probe` in OpenCode Code Mode

- **Type:** capability
  - **Proof before the main request:** built-in descriptor
  - **Delivery:** `callable` with the documented usage line

Anything that cannot be proven is `unavailable`. One unavailable
**required** item sends the whole turn back to Mode 0 with a
`required_capability_unavailable` diagnosis; optional items are simply
dropped. Fictitious or ambiguous IDs are rejected the same way - the
selector cannot talk AgentEnhancements into loading something the
registry cannot resolve exactly (typed IDs never bind through the
name-surface alias that `registry.py show` used to allow).

The rendered package carries the local `registry_revision` digest so a
host can detect catalog changes between selection and dispatch.
The renderer keeps complete required IDs and references together. It drops
notes and optional items, then uses a compact required render. If that still
exceeds 400 tokens, the whole turn falls back with `package_budget_exceeded`;
there is no final text truncation. Twelve compact items can fit. Registry
changes during selection or rendering also discard the package.

### OpenCode 2 delivery boundary

The existing bridge obtains private evidence from supported `ctx.tool.list()`
and `ctx.mcp.list()` APIs, bound to the current session and configuration
revision. It starts no second gateway. Exact naming and cloud-tool gates reuse
the gateway implementation. A host inventory is not sent to the selector.

The prompt hook runs `UserPromptSubmit` once. A private runtime envelope
also prepares the legacy fallback without another lifecycle/memory effect;
existing native JSON and `--text` outputs are unchanged. The context hook
checks the snapshot and outgoing declaration before injecting the package.
Schema drift, missing declarations or changed snapshots use the prepared
fallback. Host reads have 750 ms bounds; MCP readiness uses a 1.5 s polling
window. The existing runtime subprocess timeout remains eight seconds.

Private inventories are capped at 64,000 characters and are omitted if they
would exceed the existing hook input limit. Large metadata cannot suppress a
normally valid Mode 0 prompt. Direct tools require matching JSON schemas.
Code Mode proof is currently limited to primitive object signatures without
unsupported constraints, as exercised by `ffmpeg_probe(path: string)`; complex
or hidden Code Mode declarations fall back. This is not certification of every
tool advertised by the gateway. See the supported
[OpenCode plugin APIs](https://opencode.ai/docs/build/plugins/server/).

### Fallbacks and deadline

The whole preflight phase shares one monotonic deadline - 2 seconds by
default (`AE_PREFLIGHT_DEADLINE_MS`), at most two inference rounds -
leaving room for the Mode 0 render inside the hosts' 8-10 second hook
budgets. Late results are discarded. Every failure path (missing or
broken preflight config, missing key, timeout, HTTP error, refusal, invalid
JSON, truncation, unprovable selection) renders the legacy candidate
cards byte-identically and prints one bounded diagnosis line to
stderr. Stdout stays reserved for the context channel (OpenCode and
Hermes read it as the injection surface). Memory effects run exactly
once per prompt regardless of mode.

Mode 0 makes no selector request and does not resolve the Custom key. The
regression suite blocks sockets on the runtime path; ordinary host MCP startup
and the existing memory redactor retain their normal behavior.

### Cost notes

Preflight replaces the existing candidate slot; abstain leaves it empty.
Custom also consumes up to two selector inference rounds, each capped at
500 output tokens. The following scripted fixtures measure wiring and actual
host actions, not semantic relevance, inference quality or provider pricing.

### Verification

- `tests/test_adaptive_preflight.py` - 73 regression tests: config
  contract, Mode 0 parity (byte-identical renders, single memory
  effect, zero egress), selection parsing, exact-ID resolution,
  package rendering inside the 400-token slot, and a full Mode 2
  end-to-end run against a local TLS fixture (structured output,
  lookup round, compatibility re-issue, no-retry, deadline, refusal,
  invalid JSON, required-vs-optional, OpenCode `--text` bridge).
- Live model check: `AE_PREFLIGHT_LIVE=1` with a real checkout-local
  ui.api.json preflight Mode 2 and key (mirrors `AE_MCP_NETWORK_TESTS`).
- `scripts/doctor.py` prints an advisory preflight summary (requested
  and effective mode, diagnosis code, key presence - never the key).

Actual host pilot: OpenCode v2.3.2, one AE gateway per standalone host, an
HTTPS selector fixture (`fixture-selector`) and a separate local main-model
fixture (`ae-fixture/fixture`, OpenAI-compatible streaming). The first main
request contains the unchanged decoded user prompt, the selected package and
the exact Code Mode declaration. The host reads the selected SKILL.md before
calling the gateway; its 32×32 synthetic video result returns to the main
endpoint. Fixture database triggers count task INSERT/UPDATE operations,
including replacements, and establish one task write per prompt.

Columns: requested/effective mode; selector/main-agent requests; main-agent
catalog searches; detail reads; prompt-slot / AE cold-start tokens.

| Mode | Scenario | Sel/main req | Searches | Reads | Slot/cold tokens |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 / 0 | Paired baseline | 0 / 4 | 1 | 1 | 269 / 3,943 |
| 2 / 2 | Same prompt and profile | 1 / 3 | 0 | 1 | 186 / 3,483 |
| 2 / 2 | Abstain | 1 / 1 | 0 | 0 | 0 / 3,296 |
| 2 / 2 | Cross-domain focused lookup | 2 / 4 | 0 | 2 | 256 / 3,552 |
| 2 / 0 | Toolset changed after selection | 1 / 4 | 1 | 1 | 269 / 3,971 |
| 2 / 0 | Nonexistent required tool | 1 / 4 | 1 | 1 | 269 / 3,945 |
| 2 / 2 | Optional plugin guide | 1 / 4 | 0 | 2 | 238 / 3,534 |

Each row has one sample. Paired time from CLI launch to the first main request
was 5.222 s (Mode 0) and 6.875 s (Mode 2), including host startup. No p50/p95 is
inferred from those single samples. Token figures use the existing documented
chars/4 counter; raw provider usage and costs are unavailable. Per-request input
and output proxies are retained separately. The cold ledger includes duplicate
bootstrap pointers, all native skill descriptions conservatively, AE Code Mode
declarations plus the shared execute schema, observer/memory, prompt slot and
actual additional catalog results. Task detail bodies arrive after selection.

The lookup case verifies that `skill:postgresql-optimization` is absent from
the first eight candidates, finds it through the same registry's focused page,
and delivers only the selected capabilities to the main agent. The guide case
reads OpenMontage's integration file; it does not prove an OpenMontage runtime.
`ctx.plugin.list()` and actual prompt/context effects prove the existing AE
OpenCode bridge entry point is active. Catalog-plugin runtime readiness is
explicitly not certified.

Reproduce with the checkout venv, a fresh output directory under ignored
checkout state, installed OpenCode 2 and ffmpeg. No user credentials are needed:

```bash
AE_PYTHON=".agentenhancements/runtime/venv/bin/python"
"$AE_PYTHON" unified-integration/tests/smoke-adaptive-preflight.py \
  --output .agentenhancements/cache/preflight-proof --mode 2
"$AE_PYTHON" unified-integration/tests/smoke-adaptive-preflight.py \
  --output .agentenhancements/cache/preflight-proof --mode 0
# Additional independent cases: --scenario abstain|lookup|stale|unavailable|guide
```

Synthetic main/selector bodies are redacted and saved privately without auth
headers. Host metadata identifies the session and active bridge. The 50-case
discovery benchmark passes with a maximum 304-token hook slot and unchanged
sources during measurement; its lexical ranking quality is not a selector
quality evaluation.

### What is deliberately not claimed

- Only the demonstrated OpenCode version/path and simple exact tool declaration
  have actual first-request proof. Other hosts need their own supported session
  inventory and delivery checks; MCP-only installation remains ordinary MCP.
- Plugin delivery is guidance. Reading an integration guide is not
  activating a plugin runtime; the package says so explicitly.
- Selector relevance, abstain precision and native Auto authentication remain
  unmeasured. No real model comparison or user-credential inference was run.
