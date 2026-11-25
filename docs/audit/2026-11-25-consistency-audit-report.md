---
title: AE Consistency Audit Report (post-remediation)
version: 1.0
last_updated: 2026-11-25
audience: maintainers, contributors
---

# AE Consistency Audit Report — 2026-11-25

## Scope

Read-only audit of branch `fix/ae-consistency-hardening` after six commits.
Three independent subagents audited (1) runtime/hooks/OpenCode plugin,
(2) observer/memory/ae CLI, and (3) docs/config/schema/CI. A fourth,
fresh-context reviewer graded the whole branch with Review Focus pinned by
the implementation plan. No repo files were modified by the auditors.

## Severity synthesis (by user impact)

| Severity | Count | Disposition |
|---|---:|---|
| Critical | 0 | — |
| Important | 0 | — |
| Medium | 5 | All fixed in the single fix pass |
| Low / cosmetic | 9 | Fixed where cheap; otherwise documented/deferred |

## Medium findings fixed

1. **Catalog source falsely proved a native link** (`runtime.py`) — with no
   native target directory, the catalog fallback suppressed the observer card
   on fresh/partial installs. Fixed by never inferring a link from `source`;
   card is kept when link state is indeterminate. Test:
   `test_missing_native_targets_keep_observer_card`.
2. **OpenCode Stop dedupe lost its digest without a note map entry** (`:210-217`)
   — idle before the first prompt, or LRU eviction, re-ran Stop and appended
   duplicate checkpoints. Fixed with an independent bounded digest map.
   Test: new assertion in `test-opencode-plugin.mjs`.
3. **Manual hook listings leaked configured secrets in key/metadata fields**
   (all nine hooks) — fixed with one redactor closure per listing call,
   applied before truncation to key, value and metadata; mirrored in
   `setup.sh` and `memory.py`. Tests: `test_hook_list_redacts_keys_and_metadata`,
   `test_hook_list_reads_config_once_per_call`.
4. **Legacy `model.json` migration emitted invalid `mode: 2`** (`api_config.py`)
   — documented migration path produced a rejected config. Fixed by mapping
   legacy 2 → 1 and retired 1 → 0; test expectation updated and re-verified.
5. **Active docs still advertised Mode 2 / host-native Mode 1**
   (`CONFIGURATION.md`, `TROUBLESHOOTING.md`, `README_INTEGRATION.md`,
   `docs/API.md`) — aligned to 0/1 with historical labels explicit.

## Low findings fixed

- Symlink ownership prefix check now requires a path boundary and the
  `task-observer` basename.
- Broad exception paths narrowed without dropping advisory behavior.
- Sunday-at-time cron no longer raises `ValueError` for non-simple fields.
- Learning lock self-heal gated by mtime so a fresh partial lock cannot be
  stolen; recursion remains bounded.
- Stale Windows fixture/report labels, stale test names and stale code-line
  citations in the audit notes corrected.
- Frontmatter version/date bumped on substantively edited docs.

## Deferred (with cost if wrong)

- Bare `StartBoundary` values and exotic cron fields need a real Windows host;
  unit tests cannot certify `schtasks` acceptance. Cost: a Windows user may see
  a rejected trigger for those expressions; they are documented as unsupported.
- `CONTRACT.md §8.5` three-mode text is deliberately unchanged — amendment
  needs explicit maintainer approval (End of Contract clause). Cost: readers of
  the contract alone see a mismatch; `docs/ADAPTIVE_PREFLIGHT.md` and the
  deviation note explain it.
- Legacy `embedding BLOB` column left in place — schema change needs approval;
  documented in `docs/API.md` as runtime-compatible dead schema.
- Archived audit snapshots retain historical Mode 2 labels by design.
- Vendored filename-hygiene observations are outside this branch's scope.

## Verification evidence

- Full suite under the prepared runtime: **811 tests, OK (4 skipped)**.
- OpenCode plugin integration: `test-opencode-plugin.mjs` → `integration: OK`.
- Doctor: 7/7 native targets pass; adaptive preflight mode 0 (advisory).
- Static: `bash -n` on `setup.sh`, `py_compile` on all changed Python modules,
  `git diff --check` — all clean.
- Generated artifacts: `test_sync` byte-parity checks pass after every
  `setup.sh` heredoc edit.
- Final whole-branch review: **Ready to merge?** — yes; no Critical or
  Important issues, three Minor findings, all addressed or ledgered.
