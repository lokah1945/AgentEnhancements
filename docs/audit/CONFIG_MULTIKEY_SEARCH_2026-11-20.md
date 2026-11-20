---
title: ui.api.json consolidation, multi-key pool and search adapters
version: 1.1
last_updated: 2026-11-20
audience: maintainers
---

## ui.api.json consolidation, multi-key pool and search adapters (2026-11-20)

Agent: Claude Code (Claude Opus 5.5) | Session:
`19d3065f-e968-406c-84e3-86a49942413d` | Branch:
`feat/ui-api-v2-credential-pool` | Base: `master@6c36fd2e`.

**Status: implementation, tests and documentation complete. CONTRACT
amendment approved by the maintainer on 2026-11-20 and applied (v2.4).
Live-verified: You.com, Tavily, Exa, Serper. Not live-verified (no key):
Firecrawl, NewsAPI.**

### Outcome

- `ui.api.json` schema version 2 is the single AE-managed configuration
  source: `api_keys` arrays (multi-key), `connections`, `preflight`, `mcp`.
- Credential pool in `unified-integration/scripts/api_config.py`:
  per-request round-robin (`request_keys` / `select_key_for_request`), pure
  readiness probes (`has_usable_key`, `keys`, `value`), bounded cooldown
  (`report_key_failure`), value-free `key_health`, `all_keys_for_redaction`.
- One-time `api_config.py migrate` (also run by `setup.sh`): v1 → v2, private
  backup, atomic replace, unknown fields preserved, legacy preflight
  `model.json` / owner-only `preflight.key` imported once and left in place.
- Adaptive preflight reads only `ui.api.json` (`preflight` +
  `api_keys[api_key_ref]`). `model.json`, `AGENT_ENHANCEMENTS_MODEL_FILE`,
  `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY`, keyring and `preflight.key` are no
  longer runtime sources. Mode 0/1/2 semantics and every fallback are
  unchanged; Mode 1 remains Claude Code/Codex only and is not certified.
- New built-in `search-mcp` (gateway tool `search_web`): You.com, Tavily,
  Exa, Firecrawl, NewsAPI adapters per official docs; Serper adapter per the
  contract observed in authorized live calls (no public API reference).
- `any_of` credential requirements (`mcp.<server>.any_of`, built-in
  `BUILTIN_ANY_OF`, catalog `env_any_of`).
- The personal `search_providers.json` is fully decoupled: no runtime,
  redaction, gateway, status or test path refers to it. The file was not
  opened, read, copied, modified or deleted (metadata only:
  `mtime=2026-11-18 00:52`, untracked and ignored by `.gitignore:52`).

### Findings (as-is at `6c36fd2e`)

| ID | Prio | Evidence | Finding | Resolution |
| --- | --- | --- | --- | --- |
| F1 | P0 | `api_config.py:24,159,220-277`; `gateway.py:37,161-169` | Runtime, redaction and status read the personal root `search_providers.json`; gateway injected its keys into subprocess env | Removed; keys come from `ui.api.json` arrays only |
| F2 | P0 | `ui.api.example.json` `serper-mcp`/`you-mcp` `command` | Template suggested `npx -y serper-mcp` / `npx -y you-mcp`; `you-mcp` does not exist on npm, `serper-mcp` is unpublished (supply-chain squat risk) | Commands removed, note added |
| F3 | P0 | `gateway.py:161-169` | "Round-robin" happened once per subprocess start, not per request | External servers get the stable first key; real per-request rotation only in first-party `search-mcp` |
| F4 | P1 | `api_config.py:94-105` | One string per reference; no multi-key | Schema v2 arrays + pool |
| F5 | P1 | `adaptive_preflight.py:209-310,769-819` | Preflight settings in `model.json`, key from env/keyring/key file (second config path) | Moved to `ui.api.json`; one-time migration |
| F6 | P1 | `plugin-catalog/mcp-servers.json` | No callable search provider existed (all `to-install`, `install: null`) | `search-mcp` built; roadmap entries unchanged |
| F7 | P2 | `api_config.server_state` | No `any_of` semantics | Added for MCP entries and built-ins |
| F8 | P3 | `project_paths.py:52,71`; native env | `AGENT_ENHANCEMENTS_MODEL_FILE` written into host gateway env | No longer written; refresh retires the stale value |

### Contract amendment (approved 2026-11-20, CONTRACT v2.4)

CONTRACT §4.2 ("Modify environment variable contracts") and §9.2 require
human approval; the maintainer approved it on 2026-11-20. Applied changes:

- §8.2: remove `AGENT_ENHANCEMENTS_MODEL_FILE` and
  `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY`; add `AGENT_ENHANCEMENTS_API_FILE`
  (already used by code/tests, never listed).
- §8.5 "Configuration": replace with "The `preflight` section of the
  checkout-root `ui.api.json` (schema v2). `mode` is the exact integer 0, 1
  or 2 … Mode 2 additionally requires HTTPS `endpoint`, `sdk` ∈ {openai,
  anthropic}, non-empty `model` and a valid `api_key_ref`."
- §8.5 "Secrets": replace with "The Mode 2 key is `api_keys[api_key_ref]` of
  `ui.api.json`; no environment variable, keyring, key file or `model.json`
  is consulted. Missing key → Mode 0 before any network attempt."
- §8.6: `config/model.json` / `preflight.key` become legacy, imported once.

Applied to `CONTRACT.md` (v2.4 change-log entry). Impact: anyone
exporting `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY` or relying on the keyring
loses Mode 2 until the key is copied into `api_keys.PREFLIGHT_API_KEY`
(Mode 0 fallback, documented diagnosis `api_key_unavailable`).

### Provider matrix

| Provider | Catalogued | Adapter | Local mock tests | Gateway-observed (stdio MCP client) | Live verified |
| --- | --- | --- | --- | --- | --- |
| You.com | yes (`you-mcp`, to-install) | yes | yes | live stdio call; listed with key, hidden/rejected without | **yes** |
| Tavily | yes (`tavily-mcp`, to-install) | yes | yes | live stdio call | **yes** |
| Exa | yes (`exa-mcp`, to-install) | yes | yes | live stdio call | **yes** |
| Firecrawl | yes (`firecrawl-mcp`, to-install) | yes (`/v2/search`) | yes | in-process gateway enum + calls (mocked wire) | no |
| NewsAPI | yes (`newsapi-mcp`, to-install) | yes (`/v2/everything`) | yes | in-process gateway enum + calls (mocked wire) | no |
| Serper | yes (`serper-mcp`, to-install) | yes (empirical contract) | yes | live stdio call incl. failover `[invalid, valid]` → `attempts: 2` | **yes** |
| arXiv / Google News RSS (keyless) | built | existing | existing | existing | existing opt-in |

Evidence ledger with official URLs: [SEARCH_PROVIDER_APIS.md](../SEARCH_PROVIDER_APIS.md).

### Verification

Isolated environment mirroring `.github/workflows/ci.yml` (private
temporary `HOME`/XDG, `-u CODEX_HOME -u CLAUDE_CONFIG_DIR -u HERMES_HOME
-u XDG_CACHE_HOME -u TASK_OBSERVER_WORKSPACE`), runtime interpreter from
`setup-mcp.sh --prepare`.

| Command | Baseline `6c36fd2e` | Branch |
| --- | --- | --- |
| `run-tests.py` | 411 run, OK (3 skipped), exit 0 | 449 run, OK (3 skipped), exit 0 |
| `discovery_benchmark.py --check` | — | exit 0 |
| `mcp-servers/check-protocol.py` | — | 11/11 (10 built + gateway), exit 0 |
| `mcp-servers/smoke_test.py` | — | 10/10 healthy, exit 0 |
| `generate_capability_counts.py --check` | — | exit 0 (after `--write`) |
| `catalog-validate.py` | — | 0 errors, 0 warnings |
| `bash -n` / `py_compile` / JSON on tracked files | — | pass (3 failures only in ignored, generated `skills/by-category/general/*` vendor files, absent in CI) |
| `cd ECC && node tests/run-all.js` | 8288/8289; `lib/powershell-destructive-command.test.js` timing case failed under parallel load | ECC untouched; that file passes 61/61 three times in isolation |
| `smoke-adaptive-preflight.py` (OpenCode 2.3.2) | fails: `native_descriptions_all=4293 > 2500` | identical failure and identical values for every AE channel (`library_map_read` 491, `prompt_slot` 183, `ae_tool_catalog_and_shared_execute` 917) |

The OpenCode smoke failure is environmental: the host advertises 32 Claude
Code plugin skills installed on this machine even with an isolated `HOME`.
It reproduces on `master` and is not caused by this branch.

New coverage (`tests/test_credential_pool.py`, 34 tests): template
initialization, blank/whitespace/absent keys, de-duplication, invalid shapes
fail closed, no environment fallback, value-free status; v1 migration with
backup, idempotence, legacy `model.json`/`preflight.key` import, refusal of
group-readable/symlinked/malformed inputs, rollback on failed replace; 6
requests rotate 3 keys; readiness never rotates; cooldown expiry;
revocation; 90 concurrent requests split 30/30/30; documented request
contract per provider (URL, method, auth header, body/query); 429 failover;
bounded all-keys failure; no failover on 4xx/5xx non-key errors; network
errors and outputs never echo keys; redirect refusal; `any_of`/`required`/
`optional`/missing-runtime/missing-binary readiness; explicit disable wins;
registry hides `search-mcp` without keys; gateway enum and stale-call
rejection; real stdio session (no credentialed call). A mutation that froze
the rotation pointer failed 5 tests. `test_security_regressions.py` now
asserts that a sentinel root `search_providers.json` is never opened.

### Live verification (2026-11-20, maintainer-authorized keys)

One key per provider, copied into a private 0600 temporary `ui.api.json`
(values never printed or committed). `LiveSearchTests` (opt-in
`AE_SEARCH_LIVE=1`): OK. Per provider, 2-result queries with and without
`freshness=month`: You.com, Tavily, Exa, Serper all returned results on the
first attempt. Real stdio gateway: `search_web` enum = keyed providers, one
call per provider OK, Serper failover OK, `ae_health` OK, revocation hides the
tool and rejects the stale call, no key in any output or gateway stderr.

### Residual limitations and maintainer decisions

- `docs/repository-description.txt` now says 41 MCP catalog entries; the CI
  step comparing it with the GitHub repository description fails until the
  maintainer updates the GitHub description (outward-facing, not done here).
- Firecrawl and NewsAPI adapters are mock-tested only (no key); the external
  `*-mcp` roadmap servers remain `to-install` and unverified. Serper's
  contract is empirical (no public reference) and should be re-checked if
  Serper publishes documentation. Tool-schema budget: default profile unchanged (1,658 tokens);
  all search keys 1,763; search keys plus `OPENAI_API_KEY` 1,889, above the
  1,800 default-profile allocation (OpenAI alone was already 1,784).
- Keyring-stored preflight keys are not migrated automatically.
- The real checkout `ui.api.json` on the audit machine is still version 1
  (all keys empty); it was not migrated during this session. `setup.sh` or
  `api_config.py migrate` upgrades it.
- `mcp-test.sh --priority P0` reports `search-mcp` as not ready without keys,
  like the other credentialed P0 entries (expected, exit 1 on this machine).
- Codex keeps its tool catalog per turn: a newly keyed `search_web` may need
  a new session; revoked keys are rejected at call time on every host.
- Rotation/cooldown state is per gateway process (not distributed).
