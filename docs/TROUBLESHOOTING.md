---
title: Troubleshooting
version: 1.1
last_updated: 2026-11-01
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

## Memory

**Memories not saved**
Check `AGENT_MEMORY_ROOT` (default `~/.agent-memory`). The SQLite database
is `memory.db` inside that directory; verify with
`python3 unified-integration/scripts/memory.py <agent> list`.

**`load` exits with code 1**
That is the documented behaviour for a missing key, not an error.

**Expired memories linger**
`cleanup` only removes rows whose `expires_at` is in the past. If you have
data written by a pre-fix version with ISO `T` timestamps, run cleanup
twice after 24h or re-save those memories.

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
Check `HEADROOM_BIN`, or build it: `cd headroom && cargo build --release`.
The fallback compression is always available.

## Tests

Run the regression suite with:

```bash
python3 unified-integration/tests/run-tests.py
```

and the ECC suite (required before commits, CONTRACT §5.1) with:

```bash
cd ECC && node tests/run-all.js
```
