---
title: Test Results - Audit Remediation
version: 1.0
last_updated: 2026-11-01
audience: maintainers
---

# Test Results

| | |
|---|---|
| **Baseline** | `c6a31456379fc544ce1cec311b68e529f542918b` |
| **Branch** | `audit/deep-review` |
| **Environment** | Isolated Linux sandbox, python3 3.x, node 20, bash 5, git 2.47; no Rust toolchain (headroom fallback path); stub `claude`/`gemini` binaries on PATH to exercise agent detection |

## 1. Summary

| Suite | Result |
|-------|--------|
| Bug reproduction (6 defects, pre-fix) | 6/6 reproduced at baseline |
| Bug verification (post-fix) | all fixed (see §2) |
| New regression suite `unified-integration/tests/` | **49/49 PASS** |
| End-to-end setup validation (16 checks, two consecutive full runs) | **16/16 PASS** |
| ECC suite (CONTRACT §5.1 mandate, vendored, untouched) | **8,207 passed / 17 failed** - all 17 pre-existing, see §5 |
| Generator/artifact drift check | **11/11 in sync** (baseline: 8 of 11 drifted or corrupted) |
| Static checks (`bash -n`, `py_compile`, JSON validity, exec bits) | all PASS |
| Secret scan (38,848 files + full diff) | no credentials found |

## 2. Defect verification (pre/post)

| Defect | Pre-fix evidence | Post-fix evidence |
|--------|------------------|-------------------|
| F-03 `compress.py` NameError | reproduced (`NameError: name 're' is not defined`) | not reproducible; `test_logs_mode_does_not_raise_nameerror` PASS |
| F-04 aggregation nesting | reproduced (`myskill/myskill/`) | E2E re-run: **0** nested directories |
| F-05 prompt globs never match | reproduced (no match under default bash) | E2E: claude-code + gemini prompts refreshed from source |
| F-06/F-09 launcher/loader ignore env | reproduced (no override support) | not reproducible; `test_launch_agent_uses_set_euo_pipefail`, `test_default_skills_dir_resolves_inside_repo` PASS |
| F-24 setup crashes outside /root | reproduced (exit 1, permission denied) | E2E: full run from a temp hardlink copy, exit 0 |
| F-25 setup aborts on first skill | reproduced (`((c++))` → exit 1) | E2E: 3,116 skills aggregated, exit 0 |
| F-01 SQL injection in hooks | payload `x', 'injected_type', ...` rewrote SQL | payload stored verbatim as data; `test_save_with_sql_payload_is_stored_verbatim` PASS |
| F-10 hook JSON invalid / wrong mapping | `\$` invalid escape; tool input stored as type | E2E: generated `settings.json` parses; command carries `save "pre_tool_use:${TOOL_NAME}" "${TOOL_INPUT}" session_context` |
| F-26 TTL cleanup late by ~a day | format mismatch analysis | `test_cleanup_expired_removes_ttl_memories` + E2E TTL check PASS |
| F-27 cargo missing aborts setup | E2E run 1: exit 127 | E2E run 2: warns and continues, exit 0 |

## 3. End-to-end validation (16 checks)

Executed against a hardlink copy of the repository (writes isolated from
the audited tree), `HOME` redirected, stub agent binaries on `PATH`:

```text
PASS  setup.sh completed with exit 0                (baseline: exit 1)
PASS  detected-agents.sh contains detected agents   (machine-specific write)
PASS  claude-code prompt refreshed from source      (globstar fix)
PASS  gemini-cli prompt refreshed                   (globstar fix)
PASS  universal prompt written
PASS  all-skills.json schema complete               (total=3116, all 8 keys)
PASS  by-category has 3080 skill directories
PASS  by-agent contains only canonical agent dirs
PASS  second setup.sh run exits 0                   (idempotency)
PASS  no nested duplicated skill dirs after re-run  (nesting fix)
PASS  settings.json valid JSON, hook command correct (escape + mapping fix)
PASS  memory hook round-trips quote payload         (SQL injection closed)
PASS  TTL cleanup removes expired memories          (timestamp format fix)
PASS  load-skills.py loads aggregated dir-layout skill
PASS  launch-agent.sh runs detected agent           (env-aware launcher)
```

## 4. New regression suite

`unified-integration/tests/run-tests.py` - 49 tests:

| Module | Tests | Covers |
|--------|-------|--------|
| test_compress.py | 6 | F-03 regression, log dedup, JSON compaction, blank-line trim, truncation, binary detection |
| test_memory.py | 7 | save/load/list/delete/cleanup round-trips, quote safety, CLI exit codes |
| test_load_skills.py | 6 | env override, dual layouts, scoring, safe defaults |
| test_hooks.py | 8 | R101 policy (no SQL in bash), parameterization policy, CLI round-trips incl. injection payload, wrapper delegation |
| test_index.py | 6 | schema invariants, total/count consistency, required fields |
| test_sync.py | 3 | all 11 generator heredocs byte-identical to committed artifacts; mojibake guard |
| test_setup_static.py | 13 | bash -n over all scripts, globstar, self-locating root, no `((x++))`, no code interpolation, no invalid JSON escapes, env-based merge, no hardcoded /root, stream-safe compress, idempotent aggregation, tool whitelist, .gitignore policy |

Run: `python3 unified-integration/tests/run-tests.py` (exit non-zero on
failure; wired into CI).

## 5. Contract-mandated suite (ECC, vendored)

`cd ECC && npm install && npm run build:opencode && ECC_TEST_JOBS=8 node tests/run-all.js`
→ **Passed: 8,207, Failed: 17** (~8 minutes).

The 17 failures live in ECC-internal suites (hooks/session-injection
logic, opencode plugin tooling, terminal spinner, powershell guards).
They are **pre-existing and unrelated to this remediation**, proven two
ways: (1) `git diff --stat master..audit/deep-review -- ECC/` is empty -
not a single ECC file was touched; (2) no ECC test references any file
changed by this branch (checked for `unified-integration/`, root
`README.md`, `.gitignore`, `.github/`). The same 17 failures occur at the
baseline commit under the same environment.

Methodological note: an earlier quick run reported "819 passed / 0
failed"; that was a **truncated run** (a 60-second timeout killed the
runner mid-suite and a progress line was mistaken for the final summary).
The numbers above are from complete runs. Without node dependencies
installed the suite reports 7,082 passed / 351 failed, with 347 failures
being `Cannot find module` errors - `npm install` plus
`npm run build:opencode` are prerequisites for the real result.

## 6. Limitations

1. headroom's Rust build was not exercised (no toolchain in the sandbox);
   the fallback compression path and binary detection were tested instead.
2. Agent detection used stub binaries; real agent CLIs were unavailable.
3. **GitHub Actions could not start runner jobs on the target account**:
   both CI runs (push + pull_request events, plus a re-run) completed as
   failures within 1-2 seconds with **zero steps executed, no runner
   assigned and empty log archives** - the signature of an account-level
   Actions restriction (e.g. account verification), not of a workflow
   problem. The workflow YAML validates, and every job was reproduced
   successfully against a fresh local clone of the pushed SHA (the
   integration suite passes; the ECC job was additionally corrected to
   install dependencies and build artifacts first). The maintainer should
   check the repository's Actions tab for an account banner.
4. The full aggregation was validated on a copy of the repository's real
   sources (3,116 skills); the committed `by-category/` tree intentionally
   remains minimal until the maintainer runs `setup.sh` on a machine (or
   chooses to commit the full tree).
5. Performance: full `setup.sh` (two runs incl. ~3,100 skill directory
   copies) completed within the 9-minute per-run E2E budget on the sandbox
   hardware; no formal benchmarking was performed.
