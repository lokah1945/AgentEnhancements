---
title: Remediation Report - AgentEnhancements
version: 1.0
last_updated: 2026-11-01
audience: maintainers
---

# Remediation Report

| | |
|---|---|
| **Baseline** | `c6a31456379fc544ce1cec311b68e529f542918b` |
| **Branch** | `audit/deep-review` |
| **Remediation principle** | only verifiable, backward-compatible fixes; no interface/schema changes; CONTRACT §4.2 boundaries respected |

## 1. What was changed and why

### 1.1 setup.sh pipeline repair (F-24, F-05, F-25, F-04, F-02, F-19, F-27, F-20, F-11, F-10, F-17, F-26-template)

| Fix | Technical rationale |
|-----|---------------------|
| Install root derived from `BASH_SOURCE` (env var still wins) | Makes the documented Quick Start work from any checkout location without changing the `AGENT_ENHANCEMENTS_BASE_DIR` contract (R003). |
| `shopt -s globstar nullglob` | `**` globs now match the real prompt layout; `nullglob` removes the literal-pattern edge case. Verified: claude-code and gemini prompts are now found from source. |
| `skills_count=$((skills_count + 1))` | Post-increment from zero returns status 1 under `set -e`; arithmetic expansion has no such trap. This alone unblocked the entire aggregation. |
| `rm -rf` before `cp -r` (by-category and by-agent) | `cp -r src dst` nests when `dst` exists; pre-removing makes aggregation idempotent. Verified over two consecutive full runs: zero nested directories. |
| Skill name sanitized (`/` → `-`); `by-agent` copies restricted to the 8 canonical agents | Both values come from third-party frontmatter and are used as paths; hardening was required because the fix introduces `rm -rf` on computed targets. |
| Metadata passed via a `\x1e`/`\x1f`-separated record file; index built in one Python pass | Eliminates the code-injection vector (values never enter Python source) and the O(n²) full-index rewrite. Output schema is byte-compatible. |
| Skill tool whitelist for `by-agent/` | Matches the canonical agent list already fixed in the index schema. Unknown tools remain indexed, they just don't create directories. |
| `cargo` availability guard around the headroom build | Preserves the code's own intent (fallback compression) instead of aborting under `pipefail`. |
| Empty-array-safe `detected-agents.sh` write and summary echo | Bash 3.2 (macOS) compatibility under `set -u`. |
| Claude Code hook commands remapped to `save "<event>:${TOOL_NAME}" "${TOOL_INPUT}" session_context` and `\$` escapes removed | `\$` is not a valid JSON escape and the tool input was landing in the `memory_type` column; the new mapping stores real values with a valid type. Verified: generated `settings.json` parses and carries the intended command. |
| `merge_json_config` / `merge_yaml_config` receive paths and payloads via environment variables | Routing through a Python string literal stripped JSON escapes (invalid `settings.json`); env passing also removes path-quoting fragility. PyYAML import now fails with a clear message. |
| Hook template `expires_at` uses SQLite timestamp format | ISO `T` vs space comparison broke timely TTL cleanup. |
| Fixed the corrupted `└──` glyph in the skills README heredoc | Regenerated file was byte-corrupted. |

### 1.2 Memory hooks (F-01)

All 8 bash hooks replaced with 5-line wrappers that `exec` the Python hook
(parameterized SQL). Python hooks generated for all 8 agents from the
setup.sh template (4 agents previously had none). The committed tree is a
superset of what per-machine setup generates. Verified by a stored
quote-bearing SQL-injection payload round-tripping as plain data.

### 1.3 Compression (F-03, F-08)

- `import re` added (NameError fix).
- `compress.py` fallback binary path resolves from `AGENT_ENHANCEMENTS_BASE_DIR`
  or the script location instead of `/root`.
- `compress.sh` rewritten: `set -euo pipefail`, self-locating root, stdin
  captured **once** into a `mktemp` file with an EXIT trap (both detection
  and compression now see the full stream), explicit unknown-mode error.
  Truncating `head -5000` tolerates expected SIGPIPE.

### 1.4 Launcher (F-06)

`launch-agent.sh` synced to the generator version and improved:
`set -euo pipefail`, self-locating `UNIFIED_DIR`/`BASE_DIR` with env
overrides, pre-declared `AGENTS` array (works when detection file is
missing), guarded memory init, `AGENT_MEMORY_ROOT` no longer clobbers an
existing value.

### 1.5 Scripts (F-09, F-12, F-21, F-26)

- `load-skills.py`: honors `AGENT_SKILLS_DIR`, defaults inside the repo,
  supports **both** `by-category/<cat>/<name>/SKILL.md` and flat
  `by-category/<cat>/<name>.md` layouts (plus `by-agent`), degrades
  gracefully without PyYAML, usage check fixed.
- `memory.py`: `load` of a missing key exits 1 (consistent with hooks);
  `expires_at` in SQLite format.

### 1.6 update-skills.sh (F-15b, F-16)

Compares against `FETCH_HEAD` (always defined after `fetch`) instead of the
usually-unset `origin/HEAD`; `cd` in subshells; a failing source logs a
warning and the update continues; same self-locating root as setup.sh;
rebuild steps no longer abort on failure.

### 1.7 Index regeneration

`all-skills.json` regenerated by the repaired pipeline over the repository's
real sources: **3,116 skills** (was 2,884 from an older generation), full
schema including `agent_skill_counts`. The on-disk `by-category/` flat files
are intentionally left as committed (they remain readable via the dual-layout
loader); the full registry populates on the user's machine via `setup.sh`.

### 1.8 Hygiene (F-13)

- Removed `.claude/settings.local.json.tmp.898491.d5c14c07c983`.
- Added `.gitignore` (machine-local state, aggregation temp files, backup
  files, editor junk).

### 1.9 CI (F-14)

`.github/workflows/ci.yml` implements CONTRACT §9.1: `bash -n`, `py_compile`,
JSON validity, filename policy (scoped to the owned layer so vendored
upstream naming doesn't fail the build), conventional-commit + agent
traceability validation (advisory, because human commits legitimately lack
agent trailers), the unified-integration suite, the ECC suite and advisory
markdownlint on owned docs.

### 1.10 Documentation (F-13, F-15, F-16)

- README: correct install URL/branch/directory, honest skill counts and
  registry explanation, pipe-to-shell caution.
- Added per §7.2: ARCHITECTURE, API, CONFIGURATION, SKILLS, AGENTS,
  TROUBLESHOOTING, CONTRIBUTING, CHANGELOG (frontmatter per §7.3).

## 2. Deliberately NOT changed (CONTRACT §4.2 boundaries)

- Unified index **schema** (only regenerated data, same fields).
- The AGENTS list, memory DB schema, compression engine interface,
  environment variable names, canonical file names/locations.
- The vendored projects (upstream-owned).
- The README `curl | bash` installer (kept, with a caution note).
- `datetime.utcnow()` deprecation in the index builder (changing the
  timestamp format would alter the schema's `last_updated` rendering).

## 3. Residual risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | Vendored copies are not submodules; `update-skills.sh` cannot refresh them | Medium | Documented in UPDATING/TROUBLESHOOTING; converting to submodules is a maintainer decision (§4.2) |
| R2 | `curl \| bash` installer executes remote code by design | Medium | Caution note added; SHA-pinning or a release artifact is a maintainer decision |
| R3 | Skills aggregated from third parties are copied to disk and their SKILL.md bodies are trusted content (only metadata handling was hardened) | Medium | Inherent to the project's purpose; recommend an upstream review policy |
| R4 | `\x1e`/`\x1f` record separators could theoretically appear in a malicious description, garbling one index entry (no code execution) | Low | Record parser pads/ignores malformed fields; acceptable trade-off |
| R5 | CI workflow pushed but GitHub Actions could not start runner jobs on the account (all jobs fail in ~1s, zero steps, no runner, empty logs; YAML valid, local fresh-clone simulation passes) | Low | Maintainer should check the repo's Actions tab for an account-level banner (verification/restriction) and re-run; evidence documented in TEST_RESULTS §6.3 |
| R6 | headroom compression path validated via fallback only (no Rust toolchain in the audit sandbox) | Low | Binary detection logic covered by unit tests; build path is optional by design |
| R7 | `~/.claude/CLAUDE.md` is still overwritten by setup (pre-existing behaviour; labelled in docs/AGENTS.md) | Low | Changing merge semantics for a free-form doc is a product decision |

## 4. Applying the changes

```bash
# review
git fetch origin
git checkout audit/deep-review
git log --stat master..audit/deep-review

# verify locally
python3 unified-integration/tests/run-tests.py
(cd ECC && node tests/run-all.js)
bash unified-integration/setup.sh   # from the repo root, any location

# merge when satisfied (PR preferred)
```

## 5. Rolling back

The branch is additive over `master`; rollback is `git revert` of the
offending commits or simply not merging. No history rewriting, no force
push, no deletion of existing functionality. Individual commits are
thematically grouped (see `git log master..audit/deep-review`) so a partial
revert is straightforward. `setup.sh` merges create timestamped
`*.backup.*` files next to every user config it touches, so machine-side
rollback is a file copy.
