---
title: Troubleshooting
version: 1.4
last_updated: 2026-11-15
audience: users
---

# Troubleshooting

## Setup

**`setup.sh` fails with "Permission denied" or "No such file or directory"
mentioning `/root/agent-enhancements`**
You are running an old revision. Current `setup.sh` derives the install
root from its own location. Update the repo (`git pull`) and re-run
`./unified-integration/setup.sh`. You can still force a location with
`AGENT_ENHANCEMENTS_BASE_DIR=/path/to/repo ./unified-integration/setup.sh`.

**No agents detected**
Every agent CLI must be on `PATH`. Install the agent first, then re-run
`setup.sh`; check `unified-integration/config/detected-agents.sh`.

**Per-agent prompts "not found" warnings**
Prompt files are copied from `system-prompts-and-models-of-ai-tools/`.
Some agents (e.g. Copilot) have no prompt source in that collection - the
warning is expected and the universal prompt is still written.

**`cargo: command not found` during setup**
Optional. headroom needs a Rust toolchain to build; without it the setup
logs `cargo not found, will use fallback compression` and continues with
the built-in Python/shell compression.

## Native activation and accounts

**Codex warns that hooks need review**
Open `/hooks` and review the AgentEnhancements commands. Once trusted, they run
on ordinary startup. Changing hook definitions requires another review. Do not
use a sandbox/approval bypass to solve this.

**OpenCode plugin list is initially empty**
Plugins initialize asynchronously. Wait for the location to finish warming and
verify `agentenhancements` has `state.status: active` through `/api/plugin`.
The adapter targets OpenCode 2.2.5; OpenCode 1 uses a different plugin API.

**Model calls fail with authentication errors**
Enhancement setup does not create provider accounts. Claude Code requires its
own login; an expired OpenCode Console/provider key must be replaced through
that provider's account flow. Native hooks and local MCP health can be tested
without making paid model calls. Run `bash unified-integration/scripts/setup-mcp.sh --check`
for the nine built servers' actual protocol tests.

**Existing JSONC comments disappeared**
Merged JSONC is serialized as JSON to preserve its values safely. The original
file, including comments, remains in a private timestamped backup beside it.

## Memory

**Memories not saved**
Check `AGENT_MEMORY_ROOT` (default `~/.agent-memory`). The SQLite database
is `memory.db` inside that directory; verify with
`python3 unified-integration/scripts/memory.py <agent> list`.

**`load` exits with code 1**
That is the documented behaviour for a missing key, not an error.

**Expired memories linger**
`cleanup` only removes rows whose `expires_at` is in the past. If you have
data written by a pre-fix version with ISO `T` timestamps, re-save it with the
current utility. New notes use UTC SQLite timestamps; reads filter expired
values even before cleanup. Automatic notes expire after seven days.

## Skills

**`by-category/` looks almost empty in a fresh clone**
Expected: only the `general` flat files are committed. Run `setup.sh` to
aggregate all sources (3,000+ skills) into `by-category/` and `by-agent/`.

**Duplicate or nested skill directories after multiple runs**
Fixed in this revision - aggregation removes each target before copying.
If you still see nesting, you are on an old revision; delete
`unified-integration/skills/by-category` and `by-agent`, then re-run
`setup.sh`.

**`update-skills.sh` says "Not a git repository (vendored copy), skipping"**
The bundled projects are vendored copies, not submodules. Refresh them by
re-copying from upstream (see [UPDATING.md](UPDATING.md)).

## Compression

**`compress.sh` produces empty output for piped input**
Fixed in this revision (stdin is captured once before detection). Update
your checkout.

**headroom not used**
Check `HEADROOM_BIN`. Building Rust is optional and disabled by default; set
`AGENT_ENHANCEMENTS_BUILD_HEADROOM=1` during setup to opt in. Python fallback
is always available. This utility is separate from native CLI compaction.

## Tests

After merging a new skill source, run `bash unified-integration/setup.sh` to
rebuild the generated registry directories. The committed index alone does
not populate `by-category/`; an older local registry can therefore miss a
new default native link even when the index lists it.

Run the regression suite with the prepared runtime so the MCP dependencies
are available:

```bash
runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
"$runtime_python" unified-integration/tests/run-tests.py
```

and the ECC suite (required before commits, CONTRACT §5.1) with:

```bash
cd ECC && node tests/run-all.js
```

For parallel ECC runs, use the configuration in the root CI workflow: four
workers, with suites that modify shared build directories or assert timing
budgets scheduled serially after the worker pool. This follows ECC's own
workflow and keeps every suite enabled.
The workflow also installs jq and ripgrep, and verifies PCRE2 support before
running ECC's scanner tests.

## GitHub Actions

**Jobs fail before any step starts, with no downloadable logs**
Read the check-run annotations. An account billing lock can reject every job
before a runner is assigned, including jobs in a public repository. The account
owner must resolve the lock in GitHub Settings, Billing and licensing, or
contact GitHub Support if the billing page shows no problem to resolve.
After the lock is cleared, rerun the workflow and inspect the actual step
results. Local test results do not establish that GitHub Actions is green.
