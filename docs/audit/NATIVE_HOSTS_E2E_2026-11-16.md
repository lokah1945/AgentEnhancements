---
title: Native host verification
version: 1.0
last_updated: 2026-11-16
audience: maintainers, users
---

# Native host verification — 2026-11-16

## Scope

The machine was updated from GitHub to `ca06eb39`, then repaired on
`fix/native-agents-e2e`. The user selected Claude Code, Codex, OpenCode and
Hermes, with only the `ilma` and `master-chief` Hermes profiles. AGY and other
Hermes profiles are outside this verification.

## Installed host results

| Target | Installed CLI | Configured MCP + local tool | Native model response |
| --- | --- | --- | --- |
| Claude Code | 2.1.202 | PASS | PASS |
| Codex | 0.167.2 | PASS | PASS |
| OpenCode | 2.3.0 | PASS | PASS |
| Hermes / ilma | v0.17.0, upstream f1345290 | PASS | PASS |
| Hermes / master-chief | v0.17.0, upstream f1345290 | PASS | PASS |

Each configured MCP command completed initialization, listed 28 tools under
this machine's enabled-server settings, returned healthy status and executed
local embeddings. Model probes independently requested a short acknowledgment
through each host's real configured provider.

`master-chief` initially selected Nous without an access token; its StepFun
free model was also unavailable when checked through OpenRouter. With explicit
user approval, its default was moved to the working NVIDIA Nemotron connection
used by `ilma`. The credential stays in the private native profile environment.
The installer itself preserves provider selection and authentication.

## Repairs

- Hermes uses a native profile plugin for prompt/startup context and session
  summaries, plus the same MCP gateway as the other three hosts. Explicit
  profile selection preserves sibling personas and repairs a missing active
  default using an existing selected profile.
- Machine-local host selection persists across setup runs. Configuration
  writes are atomic, with private backups only when content changes. Managed
  gateway refreshes retain user timeouts, tool approvals and environment values.
- OpenCode 1 is rejected before a V2 configuration is written. The installed
  OpenCode was upgraded from 1.17.14 to 2.3.0 with prior state backed up.
- Interpreter aliases inside the prepared venv produce identical commands,
  preserving hook trust and avoiding repeated configuration changes.
- The library map retains its bytes and timestamp when only generation time
  or the available tokenizer's estimate differs. The live token budget is
  still enforced before deciding whether to write.
- Observation targets and proposed skill names now serialize as real YAML
  lists. Paths and spaces survive a write/read round trip.
- Native CLI fixtures handle the clients' actual MCP result envelopes and
  tool-name prefixes. An absent optional `rea` server is no longer synthesized
  by a Codex override. Health is annotated as read-only; the fixture's explicit
  approval for that tool is confined to the test subprocess.

## Verification

| Check | Result |
| --- | --- |
| Integration regressions | 262 unique tests passed: 260 in the standard run and 2 opt-in network tests |
| ECC | 8,289 passed, 0 failed, across 456 files |
| MCP protocol | 10/10 passed |
| Installed native targets | 5/5 passed |
| Real provider acknowledgment | 5/5 passed |
| Claude / Codex / OpenCode fixtures | 3/3 passed, including actual MCP health calls and automatic notes |
| Hermes fixtures | Both profiles passed; 2 task notes and 2 summaries persisted; MCP discovered |
| Repeated full setup | 14 configuration/registry files byte-identical |
| Native link audit | No heavy exposure or stale links |
| Task Observer vendor pin | 25/25 checksums unchanged |
| Python runtime | 34 installed packages compatible |

The two network tests exercised live arXiv search and Google News. The standard
suite intentionally skips them unless `AE_MCP_NETWORK_TESTS=1` is set.

ECC was run in a private mount namespace with a clean temporary directory
and isolated dependency ancestry. The shared machine has an invalid `/tmp/.git`
and a root `/node_modules`, which contaminate ECC's filesystem fixtures. The
overlay's mutable OpenCode build directory was materialized before tests that
rename it. Shared directories and production services were preserved. The final
full suite passed with every test file enabled and CI's four-worker/serial
scheduling policy.

Claude and OpenCode observed empty → populated → empty cloud tool catalogs
during a session. Codex retained its within-turn catalog snapshot; its actual
health calls still observed credential changes, and the gateway enforces
revocation on every invocation. A fresh Codex session exposes newly added tools.

Review covered correctness, readability, architecture, security and performance
using the review skill's inline criteria. Configuration failure paths retain
failed targets, explicit host permissions are preserved, plugin callbacks omit
conversation histories/tool payloads, and subprocess timeouts/concurrency are
bounded. The source changes stay in the owned integration layer. Generated
artifacts match their setup templates. Changed documentation passes lint with
the repository's YAML-title and compact-table conventions; new content was
checked for credential patterns.

## Reproduction

Run from the repository root:

```bash
runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
"$runtime_python" unified-integration/tests/run-tests.py
bash unified-integration/scripts/setup-mcp.sh --check
"$runtime_python" unified-integration/scripts/doctor.py --json
"$runtime_python" unified-integration/tests/smoke-native-clis.py --exercise-tools
"$runtime_python" unified-integration/tests/smoke-hermes.py
```

The CLI fixtures use a localhost model and temporary state. Doctor reads actual
installed configurations and calls local MCP tools. Native model-account probes
were run separately. Machine-local evidence and private backups are under
`~/.local/state/agentenhancements/e2e-current/`; credentials and raw provider
transcripts are excluded from this report.
