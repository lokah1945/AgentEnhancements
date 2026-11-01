# Changelog

All notable changes to the owned integration layer of this repository.
Vendored projects change upstream; see their own histories.

## [2.1.1] - 2026-11-01 - Audit remediation

### Fixed
- **setup.sh aborts on the first aggregated skill** - bash arithmetic
  post-increment from zero returns exit status 1 under `set -e`, so
  skills aggregation could never complete (audit F-25).
- **setup.sh only worked from `/root/agent-enhancements`** - the install
  root is now derived from the script location; `AGENT_ENHANCEMENTS_BASE_DIR`
  still overrides it (F-24). `update-skills.sh` behaves the same.
- **setup.sh aborts when `cargo` is missing** - headroom build failures now
  degrade to the fallback compression instead of killing the script (F-27).
- **Per-agent prompts were never found** - prompt globs require
  `shopt -s globstar` (now enabled with `nullglob`); added the missing Kiro
  prompt case (F-05).
- **Skills aggregation duplicated/nested directories on every re-run** -
  targets are now removed before copying; re-running `setup.sh` is
  idempotent (F-04).
- **Code injection via SKILL.md metadata** - frontmatter values were spliced
  into `python3 -c` source; they now travel through a record file, and the
  index is built in a single pass (F-02, F-19).
- **SQL injection in memory hooks** - all eight bash hooks built SQL by
  string interpolation (R101 violation). They are now thin wrappers over
  the Python hooks (parameterized SQL); Python hooks added for the agents
  that lacked them (F-01).
- **Wrong argument mapping in Claude Code hook commands** - tool input was
  stored as the memory *type*; commands now pass key/value/type correctly
  and produce valid JSON (no invalid `\$` escapes) (F-10).
- **`compress.py` NameError** - `re` was used but never imported (F-03).
- **`compress.sh` consumed stdin during content detection** - stdin is
  captured once into a temp file; script is self-locating and honors
  `AGENT_ENHANCEMENTS_BASE_DIR` (F-08).
- **`launch-agent.sh` ignored environment overrides** - stale committed
  copy replaced with the generator version: `set -euo pipefail`, self-locating
  paths, env overrides (F-06).
- **`load-skills.py` hardcoded the skills directory** - honors
  `AGENT_SKILLS_DIR`, defaults inside the repo, and loads both directory
  and flat skill layouts; missing PyYAML degrades gracefully (F-09, F-21).
- **`memory.py` exited 0 for missing memories on load** - now exits 1,
  matching the hooks (F-12).
- **Expired memories were cleaned up ~a day late** - `expires_at` now uses
  the SQLite timestamp format so comparisons against `datetime('now')`
  work (F-26).
- **`update-skills.sh` always reported "Already up to date"** - compares
  against `FETCH_HEAD` instead of the usually-unset `origin/HEAD`; one
  failing source no longer aborts the whole update (F-15, F-16).
- **Corrupted glyph in the generated skills README** (F-11).
- **README install instructions** - one-line installer pointed at the wrong
  repository name and branch (`agent-enhancements/main`); `cd` path fixed;
  skill counts aligned with the index (F-13).

### Changed
- `all-skills.json` regenerated with the fixed pipeline (2,884 → 3,116
  skills; schema now includes `agent_skill_counts`).
- `by-agent/` is populated only for the eight canonical agents; unknown
  `tools:` values remain in the index but no longer create directories.
- `memory/config.yaml` plugin paths use `${AGENT_ENHANCEMENTS_BASE_DIR}`
  references instead of hardcoded `/root` paths (R003).
- `merge_json_config`/`merge_yaml_config` pass payloads via environment
  variables instead of Python string literals (escapes and paths with
  quotes now survive).

### Added
- Regression test suite: `unified-integration/tests/` (49 tests) covering
  compression, memory, the loader, hooks, index invariants, generator/artifact
  sync and setup policy checks.
- CI workflow (`.github/workflows/ci.yml`) implementing CONTRACT §9.1:
  syntax checks, JSON validity, filename policy, commit policy (advisory),
  both test suites and advisory markdownlint.
- Documentation set completed per CONTRACT §7.2: ARCHITECTURE, API,
  CONFIGURATION, SKILLS, AGENTS, TROUBLESHOOTING, CONTRIBUTING, CHANGELOG.
- `.gitignore` for machine-local state and temp artifacts.

### Removed
- Committed temp file `.claude/settings.local.json.tmp.898491.d5c14c07c983`.

## [2.1.0] - 2026-11-01

- Agent traceability rules R205-R208 added to the contract; project renamed
  to AgentEnhancements.

## [2.0.0] - 2026-11-01

- Initial contract, replaces ad-hoc rules.

## [1.0.0] - 2026-10-15

- Implicit conventions, later formalized.
