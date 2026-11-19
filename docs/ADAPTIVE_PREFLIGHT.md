---
title: Adaptive Preflight Capability Selection
version: 1.0
last_updated: 2026-11-19
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
  - **Model used by the selector:** The endpoint/sdk/model triple in model.json.

The selector never executes anything and never sees history, tool
payloads, memory, observations or credentials. Its input is the task
intent (bounded), a compact catalog view, and - on request - focused
lookup pages served by the local registry. Its output is a small JSON
document that names typed registry IDs. AgentEnhancements then:

1. resolves every ID to its canonical entry (exact typed-ID match),
2. proves what is actually usable right now (skill files that exist,
   gateway-visible MCP servers, built-ins),
3. renders one bounded package for the main agent, inside the same
   UserPromptSubmit slot the legacy cards occupied (400 tokens).

The main agent keeps every decision and every permission: preflight
only prepares guidance and names; execution stays with the host.

### Configuration

Private state under the active checkout, independent of cwd and global XDG:

```text
.agentenhancements/config/model.json
```

```json
{"adaptive_preflight_mode": 0}
```

```json
{"adaptive_preflight_mode": 1}
```

```json
{
  "adaptive_preflight_mode": 2,
  "endpoint": "https://openrouter.ai/api/v1",
  "sdk": "openai",
  "model": "provider/model-id"
}
```

Rules (enforced by `scripts/adaptive_preflight.py` and its tests):

- `adaptive_preflight_mode` must be the exact integer 0, 1 or 2.
  Booleans, numeric strings, floats, out-of-range values, duplicate
  fields and malformed JSON are rejected: the run falls back to Mode 0
  and a diagnosis code is printed to stderr.
- Mode 2 additionally requires `endpoint` (an HTTPS base URL without
  credentials or fragments), `sdk` (`openai` or `anthropic`) and a
  non-empty `model`. On Mode 0/1 these fields are stored but ignored,
  so switching modes never loses the custom setup.
- The file is re-read once per UserPromptSubmit. Writers should use
  atomic replace; changes apply from the next prompt.
- The file must never contain secrets.

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

The key never lives in model.json or ui.api.json. Resolution order:

1. `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY` environment variable
2. the OS keyring, service `agentenhancements.preflight`, account =
   the endpoint's origin
3. a 0600 key file at `<config dir>/preflight.key` (first non-empty
   line; looser permissions are refused)

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

Wiring an adapter's native inference (for example OpenCode's
`ctx.experimental.generate` at the prompt hook) is the staged pilot
work: the runtime contract above is ready, and adapters that do not
supply the field simply run Mode 0 until their host-side integration
is proven. Mode 2 needs no adapter change - the runtime performs the
call inside the existing hook.

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
  - **Delivery:** `direct_read` (exact path to read before related work) or
    `loaded` when the host profile already links it natively

- **Type:** plugin
  - **Proof before the main request:** the guide file exists; status is recorded
  - **Delivery:** `direct_read` (guidance; runtime entry points follow the
    guide)

- **Type:** mcp
  - **Proof before the main request:** `api_config.server_state` reports the
    server visible
  - **Delivery:** `callable` (the gateway publishes the schema on the session
    toolset)

- **Type:** `tool:<server>/<name>`
  - **Proof before the main request:** the server is visible
  - **Delivery:** `callable` with the exact tool reference

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

### Fallbacks and deadline

The whole preflight phase shares one monotonic deadline - 2 seconds by
default (`AE_PREFLIGHT_DEADLINE_MS`), at most two inference rounds -
leaving room for the Mode 0 render inside the hosts' 8-10 second hook
budgets. Late results are discarded. Every failure path (missing or
broken model.json, missing key, timeout, HTTP error, refusal, invalid
JSON, truncation, unprovable selection) renders the legacy candidate
cards byte-identically and prints one bounded diagnosis line to
stderr. Stdout stays reserved for the context channel (OpenCode and
Hermes read it as the injection surface). Memory effects run exactly
once per prompt regardless of mode.

Mode 0 is provably egress-free: no credentials are read, no network
module is exercised, and the regression suite asserts no socket is
ever opened.

### Cost notes

Measured on the audit's fixtures, a rendered package replaces the
eight candidate cards (about 220-230 tokens) with a typically smaller,
exact pointer set (43-134 tokens for one to six items), and `abstain`
injects zero tokens. Mode 2 additionally spends its own inference
tokens (bounded: one catalog view + at most two rounds, 500 output
tokens each). Whether that trade wins depends on the task shape -
cross-domain tasks and rare capabilities benefit most; simple tasks
are better served by Mode 0, which is exactly why it stays the
default and the fallback.

### Verification

- `tests/test_adaptive_preflight.py` - 58 regression tests: config
  contract, Mode 0 parity (byte-identical renders, single memory
  effect, zero egress), selection parsing, exact-ID resolution,
  package rendering inside the 400-token slot, and a full Mode 2
  end-to-end run against a local TLS fixture (structured output,
  lookup round, compatibility re-issue, no-retry, deadline, refusal,
  invalid JSON, required-vs-optional, OpenCode `--text` bridge).
- Live model check: `AE_PREFLIGHT_LIVE=1` with a real user-scope
  model.json and key (mirrors `AE_MCP_NETWORK_TESTS`).
- `scripts/doctor.py` prints an advisory preflight summary (requested
  and effective mode, diagnosis code, key presence - never the key).

### What is deliberately not claimed

- A package item marked `callable` is proven against the gateway's
  published surface and the current configuration; the final proof
  that the host actually placed the tool schema on the request belongs
  to the live host pilot (review stage 2), not to the repository
  suite.
- Plugin delivery is guidance. Reading an integration guide is not
  activating a plugin runtime; the package says so explicitly.
- Selector quality (recall on rare capabilities, abstain precision) is
  a benchmark concern for the pilot on real hosts, not a claim of this
  implementation.
