# AE Consistency Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove every validated drift between AE code, generated artifacts, configuration schema and documentation, with regression tests and no protected-interface changes.

**Architecture:** Fix at the root cause in the owning module, mirror generated artifacts through their `setup.sh` heredocs, and pin each behavior with a unittest that is watched failing before the fix. Documentation is aligned to shipped code; the binding CONTRACT is not amended.

**Tech Stack:** Python 3.11 unittest, SQLite, bash generated artifacts, OpenCode plugin (JS), Markdown docs, JSON schema.

**Spec:** `docs/superpowers/specs/2026-11-25-ae-consistency-hardening-design.md`

## Global Constraints

- CONTRACT.md v2.4 §2.1/§4.1/§4.2/§8.4/§9.2/§12.3 are binding; no schema, env-var, agent-support, compression-interface, canonical-file or CONTRACT-text change.
- Test command for the whole suite: `python3 unified-integration/tests/run-tests.py` (baseline 791 tests, OK, 4 skipped). Use the prepared runtime at `.agentenhancements/runtime/venv/bin/python` when available.
- Generated artifacts must stay byte-identical to `setup.sh` heredocs (`tests/test_sync.py`).
- Every commit: conventional subject + `Agent:`/`Session:`/`Task:`/`Context:` body + `Co-Authored-By: <agent-name> <session-id>`.
- Hook failures stay advisory; context budgets stay within CONTRACT §8.4.
- No force-push, no push to shared branch, no history rewrite.

## Review Focus

1. **Native skill unlinked after `link-skills.sh --unlink`** — expected: observer bootstrap context is still injected; fallback must not infer "linked" from a stale catalog `source`. Test: `test_unlinked_native_skill_bootstraps`.
2. **Host with special characters in user/path on Windows** — expected: Task Scheduler XML is well-formed and values round-trip. Test: `test_windows_task_xml_well_formed_with_special_chars`.
3. **Repeated `ae --learning` runs** — expected: stage tree refreshed but `PENDING.md` gets exactly one line per distinct record. Test: `test_stage_candidate_ledger_dedupe`.
4. **Manual `*-memory-hook.py list` with a configured secret** — expected: same redaction as `memory.py list`, applied before truncation. Test: `test_hook_list_redacts_before_truncation`.
5. **Configured preflight mode 2 by a user following stale docs** — expected: fail closed to Mode 0 with a stderr diagnosis, and user-facing docs/schema say 1 is custom. Tests: existing `test_invalid_mode_falls_back_to_mode0` plus new schema assertion.

---

### Task 1: Observer native-link detection

**Files:**
- Modify: `unified-integration/scripts/runtime.py:123-186`
- Test: `unified-integration/tests/test_runtime_coverage.py` (class `ObserverContextTests`)

**Interfaces:**
- Consumes: `SkillsLoader.skills_index` (`load-skills.py:35-46`), `AGENT_SKILLS_NATIVE_TARGETS` (`link-skills.sh:377`), `AGENT_SKILLS_DIR`.
- Produces: `observer_linked_in_host() -> Optional[bool]`; `observer_context(agent) -> str` unchanged signature.

- [ ] **Step 1: Write failing tests** — add to `ObserverContextTests`:
  - `test_native_link_skips_bootstrap`: temp target dir with a managed symlink `task-observer` pointing under a temp skills dir; set `AGENT_SKILLS_NATIVE_TARGETS` and `AGENT_SKILLS_DIR`; `fake_observer("SHOULD_NOT_APPEAR")`; assert `observer_context(self.agent) == ""` and `self.calls(self.observer_log) == []`.
  - `test_unlinked_native_skill_bootstraps`: same temp roots but no symlink; assert fake observer text is returned.
  - `test_real_loader_uses_skills_index`: with real loader (no redirect) and a temp index containing `{"name":"task-observer","source":"task-observer"}`, assert `observer_is_natively_linked(loader.skills_index)` is True.
- [ ] **Step 2: Run tests to verify RED** — `python3 unified-integration/tests/run-tests.py 2>&1 | grep -E 'ObserverContextTests|FAIL|ERROR'` with a small runner selecting the module; expected failures on the three new tests (`AttributeError`/assertion), not on imports.
- [ ] **Step 3: Implement** — add `native_skill_targets()` and `observer_linked_in_host()` in `runtime.py`; in `observer_context()`, skip bootstrap when `observer_linked_in_host() is True`, use `loader.skills_index` only as the indeterminate fallback, narrow the broad exception to expected load failures while keeping advisory stderr. Keep `observer_is_natively_linked(index)` unchanged for the fallback and existing tests.
- [ ] **Step 4: Run tests to verify GREEN** — full suite; expected OK with 4 skipped.
- [ ] **Step 5: Commit** — `fix(observer): detect real native link before bootstrapping`.

---

### Task 2: Task Observer disabled gate and idempotent ledger

**Files:**
- Modify: `unified-integration/scripts/task-observer.py:604-711,909-921`
- Test: `unified-integration/tests/test_task_observer.py` (`test_maintenance_gated_while_disabled`, new dedupe tests)

**Interfaces:**
- Consumes: `is_disabled(root)`, `updates_dir(root)`, `stage_candidate(...)` unchanged signature, `rollback(...)` unchanged signature.
- Produces: `PENDING.md` line format unchanged; `stage_candidate` return string keeps `staged:` prefix and appends `; ledger unchanged (duplicate)` when deduped.

- [ ] **Step 1: Write failing tests** — (a) extend `test_maintenance_gated_while_disabled` to call `self.cli("rollback", "replica-diff")` and assert `"disabled"`; (b) add `test_stage_candidate_ledger_dedupe`: call `stage_candidate` three times with identical arguments in a temp workspace, assert `PENDING.md` has exactly one line and each return starts with `staged:`; (c) add `test_ledger_keeps_distinct_records`: two different skills/observation sets yield two lines.
- [ ] **Step 2: Run to verify RED** — new rollback/dedupe assertions fail.
- [ ] **Step 3: Implement** — add `is_disabled(root)` refusal at the top of `rollback()`; in `stage_candidate()`, build the ledger entry, compute a date-independent body key, parse existing lines, append only when no line contains that body, and report duplicate status in the return string.
- [ ] **Step 4: Run to verify GREEN** — targeted module + full suite green.
- [ ] **Step 5: Commit** — `fix(observer): gate rollback when disabled and dedupe staging ledger`.

---

### Task 3: ae CLI correctness and Windows XML

**Files:**
- Modify: `unified-integration/scripts/ae.py:161-197,474-513,515-700,707-740,822-840`
- Create: `unified-integration/tests/test_ae_regressions.py`
- Modify: `unified-integration/tests/run-tests.py` (register the new module), `tests/test_ae_schedule.py` (refresh stale report text)
- Test: new unittest module.

**Interfaces:**
- Consumes: `parse_cron_expression()`, `parsed["normalized"]`, `ae.run_cmd`, `tests/fixtures/schtasks_fixture.py`.
- Produces: `_xml_escape(text: str) -> str`; `_windows_task_xml(command, trigger_xml, cron_expr="") -> str`; `_get_windows_task_status()` reads `Description` for `AE cron: <expr>`; `_acquire_learning_lock()` self-heals corrupt lock files.

- [ ] **Step 1: Write failing tests** in `test_ae_regressions.py`:
  - `test_xml_escape_escapes_five_entities`: exact output for `&<>"'` and for an already-escaped string.
  - `test_windows_task_xml_well_formed_with_special_chars`: patch `_windows_current_user` to a value with `&\<>"'`; `ET.fromstring` the result; assert UserId and Command text round-trip.
  - `test_windows_status_reports_cron_expression`: patch `run_cmd` with an XML containing `AE cron: 15 2 * * 1`; assert `cron_expression == "15 2 * * 1"`; also assert `"unknown"` without Description.
  - `test_yearly_uses_monthly_january_trigger`: assert `_cron_to_windows_trigger("0 0 1 1 *")` contains `MonthlyTrigger`, `<January/>`, `<Day>1</Day>`, and no `MonthlyDOWTrigger`.
  - `test_sunday_time_has_windows_trigger`: `15 2 * * 0` and `15 2 * * 7` return non-None trigger with `T02:15:00`.
  - `test_windows_xml_splits_command_and_arguments`: assert `<Command>` and `<Arguments>` are separate elements.
  - `test_corrupt_lock_self_heals`: write `12345\n(not-a-date)\n` into the isolated lock file; first `_acquire_learning_lock()` succeeds after healing, second returns None.
- [ ] **Step 2: Run to verify RED** — each new test fails for the intended reason.
- [ ] **Step 3: Implement** — order-safe `_xml_escape`; `RegistrationInfo/Description` carrying the cron expression; parse-back in status; `@yearly` → `MonthlyTrigger` Jan 1; allow Sunday/`7` in DOW branch; split Command/Arguments and quote paths; corrupt-lock healing; refresh `tests/test_ae_schedule.py` documentation-only stubs to report the implemented state.
- [ ] **Step 4: Run to verify GREEN** — new module and full suite green; `python3 tests/test_ae_schedule.py` in an isolated HOME still exits 0.
- [ ] **Step 5: Commit** — `fix(ae): harden scheduler XML and make learning staging idempotent`.

*Rulings to ledger:* bare `StartBoundary` and exotic cron fields need real Windows validation; document, do not change.

---

### Task 4: Memory hook redaction parity

**Files:**
- Modify: all nine `unified-integration/memory/hooks/*-memory-hook.py` (same block at line ~21 and ~123-132), `unified-integration/setup.sh` hook heredoc (~1180-1197), `docs/API.md:187-191`.
- Create/Modify: `unified-integration/tests/test_memory_coverage.py` (new test).

**Interfaces:**
- Consumes: `api_config.read_config()` / `api_config.redact(value, config)` (`api_config.py:245-257,339-356`).
- Produces: `_redact(value: str) -> str` and `_display(value: str) -> str` in each hook; `list_memories()` values redacted before truncation.

- [ ] **Step 1: Write failing test** — `test_hook_list_redacts_before_truncation`: isolated memory root and private `ui.api.json` with one known secret; write a value containing that secret; assert hook `list_memories()` output does not contain the secret and that a long secret is not partially leaked by truncation.
- [ ] **Step 2: Run to verify RED** — test fails with the secret visible.
- [ ] **Step 3: Implement** — add lazy `_redact()`/`_display()` helpers to all nine hooks and the `setup.sh` template; use `_display(row[2])` in `list_memories`; document the compatibility rule and declared-vs-enforced TTL nuance in `docs/API.md`. No schema edits.
- [ ] **Step 4: Run to verify GREEN** — `test_sync.py` plus full suite green; verify all nine hooks remain byte-identical apart from `AGENT` identity.
- [ ] **Step 5: Commit** — `fix(memory): redact manual hook listings before truncation`.

---

### Task 5: Preflight mode documentation and schema alignment

**Files:**
- Modify: `unified-integration/config/ui.api.schema.json:89-113`, `unified-integration/config/ui.api.example.json:7,43-57`, `docs/ADAPTIVE_PREFLIGHT.md`, `docs/API.md:196-198`, `README.md:630-642`, `unified-integration/scripts/adaptive_preflight.py:7-42`, `unified-integration/tests/test_adaptive_preflight.py:1196-1206`.
- Create: `docs/audit/2026-11-25-preflight-mode-deviation.md`.

**Interfaces:**
- Consumes: `MODE_DISABLED=0`, `MODE_CUSTOM=1`, `VALID_MODES=(0,1)` (`adaptive_preflight.py:73-76`); commit `a6cf8720`.
- Produces: user-facing docs/schema that name 0=off and 1=custom; numeric 2 documented as invalid → Mode 0 fallback.

- [ ] **Step 1: Write failing test** — add a test asserting `ui.api.schema.json` `preflight.mode.enum == [0,1]` and that `docs/ADAPTIVE_PREFLIGHT.md` does not contain `Mode 2` as a configurable mode (allow the quoted historical note in the deviation audit file).
- [ ] **Step 2: Run to verify RED** — assertion fails on the current schema/docs.
- [ ] **Step 3: Implement** — align schema enum/descriptions, example config help and examples, docs, README, module docstring and the opt-in live test; add deviation audit note with commit evidence; leave `CONTRACT.md` untouched.
- [ ] **Step 4: Run to verify GREEN** — new test, `test_adaptive_preflight`, `test_docs_regressions`, `test_sync`, full suite green.
- [ ] **Step 5: Commit** — `docs(preflight): align mode numbering with shipped implementation`.

---

### Task 6: Final comprehensive audit and one fix pass

**Files:**
- Create: `docs/audit/2026-11-25-consistency-audit-report.md`; any fix files discovered by the audit.

**Interfaces:**
- Consumes: all tasks above; full branch diff from `git merge-base master HEAD`; `code-reviewer.md`.
- Produces: severity-graded findings, one RED→GREEN fix pass for Critical/Important, ledgered rulings/deferred minors.

- [ ] **Step 1: Dispatch parallel audit subagents** over (a) runtime/hooks/plugin, (b) observer/memory/ae CLI, (c) docs/config/schema/contract/CI, each read-only and required to cite `file:line` and mark VALIDATED / BY DESIGN.
- [ ] **Step 2: Synthesize report** with severity by user impact, not by spec silence.
- [ ] **Step 3: For each Critical/Important finding, write a failing test, watch it fail, fix, run full suite** — one pass only; no second re-review.
- [ ] **Step 4: Ledger minors as deferred** with cost if wrong.
- [ ] **Step 5: Commit** — `test(audit): add regression coverage from consistency audit` (or `fix(audit): ...` if fixes were needed).

---

### Task 7: Verification and completion

- [ ] Full suite under the prepared runtime; expected OK.
- [ ] `python3 unified-integration/scripts/doctor.py` (advisory; report failures honestly).
- [ ] `bash -n` on every changed shell file; `python3 -m py_compile` on every changed Python file.
- [ ] `git diff --check` and `git status --short` reviewed.
- [ ] Final whole-branch review with a fresh reviewer subagent using `code-reviewer.md` and this plan's Review Focus verbatim; re-grade and do one fix pass for Critical/Important.
- [ ] Use `finishing-a-development-branch` (no push/merge without explicit user request).
