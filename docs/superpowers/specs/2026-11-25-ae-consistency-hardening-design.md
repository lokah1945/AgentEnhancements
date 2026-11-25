---
title: AE Consistency Hardening Design
version: 1.0
last_updated: 2026-11-25
audience: maintainers, contributors
---

# AE Consistency Hardening — Design

## Intent and why

AgentEnhancements (AE) targets a **single, honest, fail-closed capability
library**: bounded context, deterministic discovery, runtime-readiness truth,
full auditability, and zero silent drift between what the code does and what
the documentation/configuration claims. A read-only audit on 2026-11-25 found
concrete places where that target is missed: a broken observer-link guard, a
no-op XML escaper, a non-idempotent staging ledger, a stubbed Windows status,
stale preflight mode documentation, and a secret-redaction gap in manual memory
hooks. The user explicitly opted out of brainstorming questions and asked for
the inconsistencies to be fixed and the result to be production/enterprise
grade. This design records the decisions taken without further questions.

## Goals

1. Remove every **validated** drift between code, tests, generated artifacts,
   and user-facing documentation without changing protected interfaces.
2. Make each fix regression-proof with a test that is watched failing first.
3. Keep cold-start budgets, fail-closed behavior, and advisory hook semantics
   unchanged.
4. Leave an auditable record (plan ledger + commit metadata) for every change.

## Non-goals

- Altering `CONTRACT.md` binding text (§End requires maintainer approval).
- Altering the memory DB schema, skills index schema, env-var contracts, agent
  support list, compression interface, or canonical file names (CONTRACT §4.2).
- Rewriting git history or pushing to a shared branch (CONTRACT R204).
- Re-enabling the removed host-native preflight mode; Windows-only behavior
  that cannot be validated in this Linux checkout is documented, not guessed.

## Anti-goals (what would make this a failure)

- A "fix" that silently widens a capability claim (e.g. presenting a guide-only
  plugin as callable, or a removed preflight mode as available).
- A fix that adds a new schema column or changes a public CLI positional
  contract without an explicit approval gate.
- A green test suite obtained by weakening tests instead of fixing code.

## Constraints (verbatim from the project)

- One setup script, one skills index, one memory system, one compression system
  (CONTRACT §2.1).
- Skills aggregated only through `aggregate_skills()` (R004); no manual copies.
- Generated artifacts must stay byte-identical to `setup.sh` heredocs
  (`tests/test_sync.py`).
- Hook errors are advisory and must never block an agent (`runtime.py:306-310`).
- Context budgets: L0 ≤1000, cold start ≤4000, memory recall ≤600, observer
  ambient ≤250, search page ≤800/5 cards, detail ≤1200 (CONTRACT §8.4).
- Every commit carries R201/R205/R206/§12.3 agent metadata.
- Schema changes and security-related changes need human review (§9.2); only
  fixes explicitly allowed by §4.1 are made here.

## Approaches considered

| Approach | Trade-off | Decision |
|---|---|---|
| A. Align code to stale docs (restore 3-mode preflight, add `embedding` to `memory.py`) | Large behavioral/schema change; reintroduces a deliberately removed mode; violates §4.2/§9.2 | Rejected |
| B. Align derived docs/config/schema to code; fix real code defects; document intentional differences | Documentation and tests converge on shipped behavior; no protected interface changes; smallest blast radius | **Chosen** |
| C. Leave drift and add warnings only | Cheap, but leaves production traps (malformed Windows XML, leaked secrets, duplicate ledger) | Rejected |

## Decisions (builder's calls, all evidence-backed)

1. **Preflight mode numbering.** Code is authoritative: `MODE_DISABLED=0`,
   `MODE_CUSTOM=1`, `VALID_MODES=(0,1)` (`adaptive_preflight.py:73-76,264-267`),
   native mode deliberately removed by commit `a6cf8720` and verified by tests.
   Align `ui.api.schema.json`, `ui.api.example.json`, `docs/ADAPTIVE_PREFLIGHT.md`,
   `docs/API.md`, README, module docstring, and the opt-in live test to
   **0 = off, 1 = custom**; numeric 2 becomes invalid and falls back to Mode 0.
   `CONTRACT.md §8.5` is **not edited**; an evidence-backed deviation note goes
   in `docs/ADAPTIVE_PREFLIGHT.md` and `docs/audit/` instead.

2. **Memory `embedding BLOB`.** The column is dead, always NULL, never read or
   written by AE, and an ADR explicitly forbids embeddings. Both DDL variants
   are runtime-compatible. No schema change; document the compatibility rule
   and the "which writer creates the DB first" nuance in `docs/API.md`.

3. **Observer native-link guard.** Root cause is a wrong attribute name:
   `runtime.py:159` reads `loader.index`, but `SkillsLoader` exposes
   `skills_index`. The broad `except` hides the `AttributeError` on every
   session, so bootstrap always runs and double-injects context. Fix by
   detecting the **actual managed symlink** in the native skill targets
   (`AGENT_SKILLS_NATIVE_TARGETS` or the four default host dirs), falling back
   to the catalog `source` proxy only when targets cannot be determined. Use
   `loader.skills_index` at the fallback site. Keep `observer_is_natively_linked()`
   for the fallback and existing tests.

4. **Task Observer.** Add the missing `is_disabled()` gate to `rollback()`;
   dedupe `PENDING.md` writes in `stage_candidate()` by a date-independent body
   key while still refreshing the staged tree/PROPOSAL/diff. Ledger line format
   unchanged; `staged:` prefix preserved for `ae.py`.

5. **ae CLI.** Fix `_xml_escape()` with order-safe entity escaping; embed the
   normalized cron expression in `<RegistrationInfo><Description>` and parse it
   back for honest Windows status; correct `@yearly` to a `MonthlyTrigger` on
   Jan 1 and allow Sunday/`7` in the specific-DOW branch; split `<Command>` and
   `<Arguments>` and quote paths; make a corrupt learning lock self-heal;
   refresh the stale report generator. Bare `StartBoundary` and exotic cron
   fields (`1-5/2`, `*/60`) are documented as Windows-validation caveats, not
   silently changed.

6. **Memory hook redaction.** Manual `*-memory-hook.py list` can print secrets
   that `memory.py list` redacts. Reuse `api_config.redact` in all nine hooks,
   mirrored in the `setup.sh` heredoc, redacting **before** truncation.

7. **Commit metadata.** Do not edit CONTRACT or rewrite history. All new
   commits use `Co-Authored-By: <agent-name> <session-id>` (the one format both
   R205 and §12.3 agree on) plus `Agent:`/`Session:`/`Task:`/`Context:` lines.
   Record the R206-vs-§12.3 body-format conflict in an audit note for maintainers.

## What is left to the builder

Execute the linked plan task-by-task under TDD. Where the plan and this design
disagree, this design is the authority. Every deviation must be ledgered as a
Ruling with its cost if wrong.

## Verification target

- Full regression suite green (baseline before changes: 791 tests, OK, 4 skipped).
- New targeted unittest modules green, including RED→GREEN evidence.
- `test_sync.py` green after any generated-artifact edit.
- No new schema, no new env var, no CONTRACT amendment, no force-push.
