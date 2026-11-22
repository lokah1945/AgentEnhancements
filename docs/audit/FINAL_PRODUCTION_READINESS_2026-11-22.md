---
title: Final production readiness audit and remediation
version: 1.0
last_updated: 2026-11-22
audience: maintainers
---

## Final production readiness audit and remediation (2026-11-20 to 2026-11-22)

> Historical record, superseded by [docs/audit/ENTERPRISE_RELEASE_2026-11-23.md](ENTERPRISE_RELEASE_2026-11-23.md). Readiness claims here are not current.

Agent: Claude Code (Claude Opus 5.5) | Session:
`fdc7d37d-642e-4ec9-96f6-a1ab893d503a` | Branch:
`fix/final-audit-remediation` | Base: `master@fc893cf4`.

### Verdict

**Not release-ready on `master@fc893cf4`; release-ready for Claude Code,
Codex and OpenCode on this branch once it is merged, with the open items
below accepted or scheduled.** `master` contains two P0 defects (video-mcp
filtergraph injection, Hermes cross-user note leak) and eight P1 defects.
All of them are fixed on this branch, each with a regression test that
fails on `fc893cf4`. Hermes messaging gateways must not serve more than one
person on `master`.

### Method

- Twelve read-only audit dimensions ran in sandbox clones at `fc893cf4`
  with isolated HOME, state, memory and API files. Every P0/P1 finding was
  checked by two independent adversarial verifiers (reproduce, then scope).
- Two dimensions (baseline CI reproduction, setup lifecycle) were stopped
  by an account usage limit. Their scope was covered directly: the
  CI-equivalent run below and the setup-related findings of the other
  dimensions (prompt rewrite, Codex hook order, OpenCode hooks, Hermes
  collision, smoke isolation).
- Real-host pilots on `master` (real HOME, installed hooks, fixture repo
  with a PostgreSQL need that appears only after reading code): OpenCode
  2.3.2 and Codex 0.167.2 found the need mid-task through the L0 registry
  path and produced correct fixes; Hermes 0.17.0 never consulted AE and
  wrote invalid SQL. One run per host: indicative, not statistical.
- Fixes were developed test-first in a separate worktree so the hooks
  installed on the maintainer's hosts kept running `master`.

### Findings fixed on this branch

| Sev | Finding | Commit |
| --- | --- | --- |
| P0 | video-mcp overlay text escaped into the ffmpeg filtergraph (file truncation, SSRF, apostrophes broke renders) | `50e4baf0` |
| P0 | Hermes gateway: one chat user's notes recalled into another user's turn | `d0e1835d` |
| P1 | video-mcp ignored media allowed roots (read/write anywhere) | `50e4baf0` |
| P1 | Hermes profiles recalled each other's notes | `d0e1835d` |
| P1 | Hermes smoke wrote the checkout's live host selection | `1673de21` |
| P1 | OpenCode L0 registry command relative to the checkout | `4e4fdbed` |
| P1 | Selector IDs aliased across types and case | `d89b9a28` |
| P1 | Legacy preflight files re-imported after the user revoked them | `4a4c2da6` |
| P1 | Setup re-run untrusted the user's Codex hooks | `58cbef21` |
| P1 | Mode 2 selector received pasted provider credentials | `26377cbd` |
| P1 | Unverified, unpinned `npx -y` roadmap packages shown as run commands | `c342a457` |
| P2 | Redaction corrupted words such as `task-observer-…` | `3678d008` |
| P2 | OpenCode Stop ran on every tool-loop continuation | `4e4fdbed` |
| P2 | Plugins reported `ready: yes (built-in)`; cards printed `ready: yes ()` | `4f435445` |
| P2 | doctor passed OpenCode without the AE plugin | `292024cc` |
| P2 | doctor passed Claude Code/Codex without AE hooks | `e307622d` |
| P2 | Setup rewrote tracked prompt files on every run | `fdb778d1` |
| P2 | vision-mcp read/uploaded arbitrary files | `271d85bf` |
| P2 | Offensive-risk skills offered without a label | `90dc9624` |
| P2 | Consent/audit logs committable | `667dcd06` |
| P2 | External MCP could shadow a built-in tool name | `03498c92` |
| P2 | One JSON-RPC error tore down an external MCP worker | `03498c92` |
| P2 | Mode 1 reported as effective | `c7946490` |
| P2 | Hermes setup enabled a user's same-name plugin | `f7fb39ab` |
| P2 | `registry.py show` relative paths; L0 "never hidden" claim | `d38bfeff` |
| P3 | Inert command hooks written into `opencode.json` | `c657b149` |
| P3 | Fake `python -m` run lines for built-in servers | `c342a457` |

Documentation was updated in `61260fd2` (markdownlint clean). The
documented real-CLI smoke was repaired in `dff1016f`.

### Open items

Needs a maintainer decision (contract or product change):

- **Mid-task capability hints** (P2): no hook re-evaluates capabilities after
  the first prompt, although Claude Code and Codex accept PostToolUse
  `additionalContext`. Pilots show agents can self-serve through L0; an
  automatic hint changes the context contract.
- **Preflight deadline knob** (P2): `AE_PREFLIGHT_DEADLINE_MS` allows up to
  8,000 ms, above the 8 s Hermes adapter timeout and close to the 10 s
  Claude/Codex hook timeout, so a slow selector can lose the Mode 0
  fallback; lookups and the fallback render are not inside the deadline.
- **Tool schema budget** (P2, known): enabling OpenAI or task-router pushes
  model-visible AE schemas above the 1,800-token allocation.
- **CONTRACT text** (P3): §8.4–§8.6 sit after "End of Contract"; Hermes is
  missing from the §1/§4.3 agent list; hook card default 8 vs page cap 5.
- **Catalog packages** (P1 residual): pin each roadmap `npx` entry to a
  verified vendor package or mark it guide-only; `newsapi-mcp` names a
  different vendor's package. Needs vendor verification.
- **Licensing** (known AE26-R01): GPL-3.0 prompt archive and
  `anthropic-skills` without a root LICENSE are redistributed.

Engineering backlog, no decision needed:

- PREFLIGHT_API_KEY round-robin restarts per hook process (never rotates);
  failed keys are not cooled down across prompts.
- task-router tasks outlive the gateway and their hard timeout; finished
  workspaces are not cleaned. search-mcp has no total deadline and a
  cancelled call keeps its backend thread.
- Hermes: background memory-review fork overwrites the parent session's
  notes; `post_tool_call` and Claude/Codex Pre/PostToolUse spawn a blocking
  Python process per tool call only to record its name; Hermes gets none
  of the 16 default native skills.
- OpenCode: first prompt runs SessionStart and UserPromptSubmit serially
  (up to 8 s each) before the model; tests do not cover the installed
  `codemode: false` configuration.
- Discovery quality: Mode 0 precision is low and it rarely abstains on an
  independent probe set; short tokens graze skill names; the L0 budget gate
  measures only the `rendered` field although agents read the whole file.
- Redaction is pattern-based: unrecognised credential shapes in prompts can
  still reach memory notes (7-day TTL) and the Mode 2 selector.
- Legacy preflight import is skipped when `ui.api.json` did not exist yet;
  an all-unavailable optional selection injects nothing silently.
- Secondary hosts (Cursor, Windsurf, Copilot) still use undocumented or
  retired channels (known P-05, P-06, P-17); a saved native selection drops
  secondary hosts.
- `smoke-native-clis.py`: update the tool-discovery assertion for deferred
  MCP tool loading (Claude Code ToolSearch, Codex).
- Known and accepted: consent gate can be approved from piped stdin
  (AE26-R05); no lockfile/SBOM/releases (AE26-R06); third-party SKILL.md
  prose is not screened (AE26-R08); task-router denylist is advisory.

### Verification

All runs on 2026-11-22, sandboxed HOME, CI-equivalent steps from
`.github/workflows/ci.yml` (setup.sh, run-tests.py, frozen discovery
benchmark, capability counts), branch head vs `fc893cf4`:

| Check | `fc893cf4` | This branch |
| --- | --- | --- |
| `setup.sh` | exit 1 (see below) | exit 0 |
| `run-tests.py` | 450 OK, 4 skipped | 471 OK, 4 skipped |
| Discovery benchmark top-1 / top-3 / negatives abstained | 25/40, 30/40, 6/6 | 25/40, 30/40, 6/6 |
| Capability counts check | pass | pass |
| Checkout clean after setup | no (`codex-system-prompt.txt` rewritten) | yes |
| markdownlint (owned docs) | not run | pass |

The baseline `setup.sh` failed with `Hermes profile does not exist: ilma`
because the baseline Hermes smoke run earlier had written its fixture
profile selection into that checkout's state: an end-to-end reproduction
of the P1 smoke-isolation defect.

Real installed CLIs against localhost fixture models, fix-branch native
integration installed into a sandboxed HOME (the maintainer's own host
configurations were not modified):

- Hermes 0.17.0, profiles `ilma` and `master-chief`: pass (task and
  summary notes, native MCP discovery).
- OpenCode 2.3.2: pass on two consecutive runs (AE events stored, gateway
  tools delivered to the model). The first run in a fresh HOME missed the
  tools: cold-start timing, related to the open OpenCode latency item.
- Claude Code 2.1.329 and Codex 0.167.2: the fixture turn completes, but
  the smoke's "gateway tools in the first model request" assertion fails
  on `fc893cf4` and on this branch alike. Claude Code now sends
  `ToolSearch` plus a deferred-tool placeholder instead of MCP schemas;
  Codex sends none to a custom provider. The assertion predates deferred
  tool loading and needs updating (open item). Codex hooks also start
  untrusted in a fresh HOME by design.
- The smoke itself could not start on any current install (stale venv
  path); fixed in `dff1016f`.

Pilots of real models on the maintainer's hosts were run on `master` only;
they were not repeated on this branch.
