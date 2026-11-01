---
title: Audit Report - AgentEnhancements
version: 1.0
last_updated: 2026-11-01
audience: maintainers
---

# Deep Audit Report - AgentEnhancements

| | |
|---|---|
| **Audited repository** | `https://github.com/lokah1945/AgentEnhancements` |
| **Default branch** | `master` |
| **Baseline commit** | `c6a31456379fc544ce1cec311b68e529f542918b` |
| **Audit branch** | `audit/deep-review` |
| **Audit date** | 2026-11-01 (UTC+7) |
| **Auditor** | Z.ai autonomous audit agent (session `web-ae895731-02db-4e8b-9859-40eddd164136`) |
| **Scope** | Owned integration layer + root files (full depth); vendored projects scanned for secrets/security hotspots only |

## 1. Scope and methodology

**In scope (full review):** `unified-integration/**` (73 files), `README.md`,
`CONTRACT.md`, `docs/**`, `.claude/**`, root-level policy; repository-wide
secret pattern scan; empirical reproduction of every suspected runtime
defect in an isolated sandbox; the contract-mandated ECC test suite.

**Out of scope (documented limitation):** line-by-line review of the seven
vendored projects (`agentic-awesome-skills`, `claude-mem`, `ECC`, `headroom`,
`ponytail`, `superpowers`, `system-prompts-and-models-of-ai-tools`; ~38,000
files). They are upstream code copied for distribution; changes belong
upstream. They received an automated scan for committed credentials and
dangerous patterns, not a manual review.

**Method:** static reading of every owned file → systematic diff between
`setup.sh` heredoc generators and committed artifacts (drift analysis) →
empirical reproduction of suspected bugs in a throwaway sandbox →
schema/consistency validation of `all-skills.json` against its generator →
policy checks against the repository's own CONTRACT.md.

**Environment:** isolated Linux sandbox; no credentials were requested,
extracted or transmitted; nothing was pushed to any remote during the
audit; no network calls other than the initial `git clone`.

## 2. Executive summary

The owned integration layer was **functionally broken and carried two
injection-class security defects**:

1. `setup.sh` could not complete a single run: it aborted on the first
   aggregated skill (`((skills_count++))` under `set -e`), aborted when
   `cargo` was missing, and required the checkout to live at
   `/root/agent-enhancements`. Every committed "generated" artifact was
   therefore a stale copy from an older code generation - confirmed by
   systematic drift analysis.
2. All eight memory hooks built SQL by bash string interpolation (direct
   violation of the repository's own R101), and skill metadata from
   third-party SKILL.md files was spliced into `python3 -c` source text
   (code execution vector in the project's core workflow).

21 findings were recorded: 3 critical, 8 high, 7 medium, 3 low. All
fixable findings were remediated on the audit branch; every fix is covered
by a 49-test regression suite, a 16-check end-to-end validation and the
contract-mandated ECC suite (8,207 passed; 17 pre-existing failures in
ECC-internal suites, unaffected by this work - see
[TEST_RESULTS.md](TEST_RESULTS.md) §5).

## 3. Findings

Severity: **C**ritical / **H**igh / **M**edium / **L**ow / **I**nfo.
Status: FIXED on `audit/deep-review` (see [REMEDIATION_REPORT.md](REMEDIATION_REPORT.md)) or RISK (documented residual risk).

### Critical

| ID | Sev | Status | Finding | Evidence |
|----|-----|--------|---------|----------|
| F-25 | C | FIXED | `aggregate_skills` aborts on the **first** processed skill: `((skills_count++))` post-increments from 0, evaluates to 0, returns exit status 1, and `set -euo pipefail` terminates the script. The current setup.sh has never completed a run. | Reproduced: `bash -ec 'set -euo pipefail; c=0; ((c++))'` → exit 1 |
| F-02 | C | FIXED | Third-party SKILL.md frontmatter (`name`, `description`, `tags`, `tools`) interpolated into `python3 -c '''...'''` source. A malicious upstream skill can execute arbitrary Python as the user. The project's core purpose is aggregating third-party skills, so this is a realistic supply-chain vector. | setup.sh L458-495 (baseline) |
| F-01 | C/H | FIXED | All 8 `<agent>-memory-hook.sh` build SQL via string interpolation of `key`/`value`/`project`. Quote-bearing input breaks the query; crafted input rewrites SQL (stored `memory_type` = attacker-controlled). Violates CONTRACT R101. 4 of 8 agents had no safe Python hook at all. | `claude-code-memory-hook.sh` (baseline): `VALUES ('$AGENT', '$project', '$type', '$key', '$value', ...)` |

### High

| ID | Sev | Status | Finding | Evidence |
|----|-----|--------|---------|----------|
| F-24 | H | FIXED | `setup.sh` only works when installed at `/root/agent-enhancements`; README Quick Start (`git clone` + run) crashes at the first file write. | Reproduced: exit 1, `/root/.../detected-agents.sh: Permission denied` |
| F-05 | H | FIXED | `setup_prompts` globs use `**` without `shopt -s globstar`; with default bash `**` == `*`, so the depth-3 patterns never match the actual depth-2 layout (`Anthropic/Claude Code/Prompt.txt`). Per-agent prompts were silently never configured. | Reproduced: glob matches nothing under default bash |
| F-03 | H | FIXED | `scripts/compress.py` uses `re.search`/`re.sub` in `fallback_compress` but never imports `re` → `NameError` on the logs/auto fallback path. | Reproduced: `NameError: name 're' is not defined` |
| F-04 | H | FIXED | `cp -r "$skill_dir" "$target_dir"` nests the source inside an existing target: every re-run of setup duplicated the entire skill tree into itself. | Reproduced: `by-category/security/myskill/myskill/` after re-copy |
| F-10 | H | FIXED | Claude Code hook commands passed positional args in the wrong order: `save pre_tool_use "${TOOL_NAME}" "${TOOL_INPUT}"` stored the tool name as *value* and the entire tool input as *memory_type*; combined with `UNIQUE(agent, project, memory_type, key)` the memory system stored effectively nothing. Additionally `\$` is an invalid JSON escape and the merge path stripped `\"` through a Python string literal, producing invalid JSON in `~/.claude/settings.json`. | Code trace + JSON escape analysis |
| F-27 | H | FIXED | `cargo build ... | tail -20` under `pipefail` aborts setup when cargo is missing, contradicting the code's own intent to fall back to native compression. | E2E run 1: exit 127 `cargo: command not found` |

### Medium

| ID | Sev | Status | Finding | Evidence |
|----|-----|--------|---------|----------|
| F-06 | M | FIXED | Committed `launch-agent.sh` is a stale generation: no env overrides, hardcoded `/root`, no `set -euo pipefail` (violates R102). Drift vs generator confirmed. | Drift diff |
| F-08 | M | FIXED | Committed `compress.sh` re-reads stdin up to 5 times in auto mode (stream consumed by detection) and hardcodes `/root` paths (violates R003). Generator version wrote a predictable `/tmp/compress_input_$$` file without cleanup guarantees. | Code inspection |
| F-09 | M | FIXED | Committed `load-skills.py` hardcodes `SKILLS_DIR = Path("/root/agent-enhancements/...")` (violates R003) and only understands the flat `.md` layout while the current generator produces `<name>/SKILL.md` directories. | Drift diff |
| F-17 | M | FIXED | `merge_json_config`/`merge_yaml_config` interpolate `$target_file` and the payload into Python source; paths containing quotes break, JSON escapes are mangled (root cause of the F-10 invalid-JSON path). | Code inspection |
| F-13 | M | FIXED | `.claude/settings.local.json.tmp.898491.d5c14c07c983` committed to the repository - a machine-local temp artifact that violates the repository's own §9.1 filename policy. | File present in tree |
| F-14 | M | FIXED | No CI at all, despite CONTRACT §9.1 mandating automated checks (bash -n, py_compile, markdownlint, filename policy, commit validation). | No `.github/` directory |
| F-15 | M | FIXED | README one-line installer points to `lokah1945/agent-enhancements` (wrong repo name) on branch `main` (wrong branch; default is `master`); manual install says `cd agent-enhancements` (wrong directory). Following the README fails. | README L35/L43 |
| F-16 | M | FIXED | `docs/` ships only 2 of the 9 files CONTRACT §7.2 requires (missing ARCHITECTURE, API, CONFIGURATION, SKILLS, AGENTS, TROUBLESHOOTING, CONTRIBUTING, CHANGELOG). | `ls docs/` |
| F-19 | M | FIXED | Index builder rewrote the entire `all-skills.json` once per skill (O(n²): 2,884 full-file rewrites). | Code inspection |
| F-26 | M | FIXED | `expires_at` stored as Python ISO (`T` separator) but compared with SQLite `datetime('now')` (space separator); string comparison is wrong, so TTL cleanup fires ~a day late. | Unit test + format analysis |

### Low / Info

| ID | Sev | Status | Finding | Evidence |
|----|-----|--------|---------|----------|
| F-07 | L | FIXED | Drift: committed `compress.sh` differs from generator (both broken in different ways). | Drift diff |
| F-11 | L | FIXED | Generator heredoc for `skills/README.md` contains a corrupted glyph (`└─<U+FFFD>`), corrupting the regenerated file. | Drift diff |
| F-12 | L | FIXED | `memory.py` CLI exits 0 for `load` of a missing key (generator version exits 1); inconsistent CLI contract. | Drift diff |
| F-15b | L | FIXED | `update-skills.sh` compares `HEAD..origin/HEAD`, which is unset in plain clones → always "Already up to date"; a single failing source aborts the whole update under `set -e`. | Code inspection |
| F-20 | L | FIXED | `echo "AGENTS=(${AGENTS[@]})"` breaks on bash 3.2 (macOS default) with an empty array under `set -u`. | Bash semantics |
| F-21 | L | FIXED | `load-skills.py` imports PyYAML unconditionally in `_parse_skill` with no graceful degradation. | Code inspection |
| F-22 | I | RISK | Vendored projects are plain copies, not submodules/remotes (CONTRACT §2.3 wants submodules or documented remotes). `update-skills.sh` is a no-op for them. Documented; structural decision reserved for the maintainer. | No `.git` in vendored dirs |
| F-23 | I | RISK | `config/detected-agents.sh` is committed machine-specific state (by design auto-generated; harmless but misleading in a fresh clone). | File content |
| F-24b | I | RISK | `datetime.utcnow()` deprecation warning in the index builder (cosmetic; format preserved for schema stability). | E2E log |
| F-28 | I | RISK | Committed `by-category/` ships only 38 flat `.md` files in one category while the index lists 3,116 skills; the on-disk registry is only populated by running `setup.sh`. Documented in README/docs rather than committing ~3,000 directories. | `git ls-files` counts |

## 4. Documentation vs implementation consistency

| Claim (docs/README) | Reality at baseline | Action |
|---|---|---|
| One-line install from `main` of `agent-enhancements` | Wrong repo name and branch; URL 404s | FIXED (URL, plus a pipe-to-shell caution) |
| `cd agent-enhancements` | Directory is `AgentEnhancements` | FIXED |
| "2788+ skills, 10 categories" | Index had 2,884 skills across 100+ raw categories; on-disk registry ~empty | FIXED (index regenerated: 3,116 skills; claims aligned; categories explained) |
| CONTRACT §7.2 documentation set | 2 of 9 files present | FIXED (8 added/updated + this audit set) |
| CONTRACT §9.1 CI checks | None existed | FIXED (workflow added) |
| CONTRACT R101 "hooks use parameterized queries" | 8/8 bash hooks interpolated SQL | FIXED (Python hooks + wrappers) |
| CONTRACT R003 "no hardcoded paths" | `/root/agent-enhancements` hardcoded in launcher, compressor, loader, config | FIXED (self-locating defaults + env overrides) |
| CONTRACT R102 "`set -euo pipefail`" | `launch-agent.sh` and `compress.sh` lacked it | FIXED |

## 5. Security scan summary

- **Secrets**: no credentials, tokens or private keys committed anywhere in
  the repository (38,848 files scanned; all `.env*` hits are `.example`
  templates).
- **Dangerous patterns**: the README `curl | bash` installer is the only
  remote-code-execution-by-design surface (retained, now with an explicit
  caution note); no `eval`, no `chmod 777`, no destructive `rm -rf` in the
  owned layer.
- **Injection surfaces**: F-01 (SQL) and F-02 (Python code) - both FIXED.

## 6. Audit limitations

1. Vendored projects were not manually reviewed (see scope).
2. Runtime validation used stub agent binaries (`claude`, `gemini`) for
   detection; real agent CLIs were unavailable in the sandbox.
3. headroom could not be built in the sandbox (no Rust toolchain), so the
  headroom compression path was validated only through its fallback and the
  binary-detection logic.
4. GitHub Actions workflows were validated locally (syntax + step logic)
   but not executed on GitHub runners.
