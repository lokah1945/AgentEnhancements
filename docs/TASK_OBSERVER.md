---
title: Task Observer
version: 1.1
last_updated: 2026-11-25
audience: users, maintainers
---

## Task Observer (vendored skill: ambient skill-usage observation)

Task Observer turns the corrections, repeated workflows and methodology
evidence of a work session into small, reviewed skill updates. Every change
comes with its evidence and a written reason, and nothing touches a skill
until it is staged, validated and explicitly promoted.

The skill is vendored from
[rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all)
("One Skill to Rule Them All", © Eoghan Henn and contributors,
**CC-BY-4.0**), pinned at commit `d61bc31f7857948710a947673c0e373bef4ed3d0`
(skill version 3.10.0). See `task-observer/VENDORED.md` and
`task-observer/VENDORED.json` for the pin, the file manifest and checksums.

### What it does — and what it deliberately does not

- **Does**: observes sessions for skill-improvement evidence (user
  corrections, a rule the agent violated, a better workflow than a skill
  recommends, repeating work that argues for a new skill); writes each
  finding as one Markdown file with YAML frontmatter to a persistent
  workspace; surfaces open findings at the next session start; reviews the
  backlog; stages skill updates for human approval.
- **Does not**: record raw tool inputs/outputs or transcripts (the shared
  runtime already refuses these); call any LLM provider or network service
  (normal operation is fully offline); auto-apply skill changes (staging
  only; promotion is always an explicit step); run commands found inside
  observation text (observations are data, never instructions).

### Scope: global workspace, per-project memories

The observation workspace is **one user-scope root**, shared across
projects, tools and agents on the same install:

```text
$AGENT_MEMORY_ROOT/task-observer/          (default .agentenhancements/memory/task-observer)
├── skill-observations/                    # upstream "skill-observations/"
# layout
│   ├── observation-log/                   # the log IS this directory
│   │   ├── NNNN-slug.md                   # one file per observation
│   │   └── archive/                       # resolved entries (grace period
│ # applies)
│   │       └── .id-floor                  # highest id ever issued
│   ├── cross-cutting-principles.md
│   ├── last-review-date.txt
│   └── checkpoints.log
└── skill-updates/                         # staging root (beside, never inside)
    ├── YYYY-MM-DD/<skill>/                # staged copy + PROPOSAL.md
    ├── YYYY-MM-DD/<skill>.diff
    ├── PENDING.md                         # staging ledger
    └── rollback/                          # pre-promotion backups
```

Override the root with `TASK_OBSERVER_WORKSPACE` (absolute path). Global
skills (the normal case: the unified registry) share this one root, so an
observation logged in one project is found by sessions in another — the
upstream "one user-scope root" rule. The shared session memory
(`memory.py`) stays per-project as before; the two systems do not mix.

### Activation (how a session gets it)

1. **Lifecycle bootstrap (primary).** The shared runtime
   (`scripts/runtime.py`) runs on every `SessionStart` event for Claude
   Code, Codex and OpenCode. It always bootstraps the workspace if missing
   (the Stop backstop needs it) and, when task-observer is **not** linked
   into a native skill directory, injects a bounded context (status,
   workspace path, up to 5 open observations). The card is suppressed when
   a registry-owned `task-observer` symlink exists, because the native skill
   already supplies it; a catalog `source` alone is not proof of a link.
   This is NOT keyword-matched: a session that never mentions Task Observer
   still gets the bootstrap and, when unlinked, the card.
2. **Native discovery.** `link-skills.sh` links the bundle into
   `~/.claude/skills/` and `~/.agents/skills/` as part of the default
   curated set, so every Agent Skills compatible harness can load
   `SKILL.md` and its `references/` on demand.
3. **Instruction channels.** The `CLAUDE.md` / `AGENTS.md` /
   `GEMINI.md` marker sections mention the observer through the shared
   integration block; Cursor/Windsurf rules and the launcher environment
   work the same way as for every other capability.

Agents without lifecycle hooks (Cursor, Gemini CLI, Copilot, Windsurf,
Kiro) get discovery (2) and instruction (3) only: the observer must be
invoked manually or via its CLI. See the capability matrix below for the
evidence level per agent.

### Usage (verified commands)

```bash
# status (state, counts, last review) - honest, never optimistic
python3 unified-integration/scripts/task-observer.py status

# log an observation (agent calls this when evidence exists)
python3 unified-integration/scripts/task-observer.py log \
  --title "replica-diff ignores pixel threshold" \
  --issue "user asked 0.05, tool ran with default" \
  --principle "user parameters must reach the tool call" \
  --skill replica-diff --session-context "fixture demo"

# what is open for one skill (the per-skill check)
python3 unified-integration/scripts/task-observer.py lookup replica-diff

# read-only review: open entries grouped by skill + staged candidates
python3 unified-integration/scripts/task-observer.py review

# stage a proposed change (never installs anything)
python3 unified-integration/scripts/task-observer.py stage replica-diff \
  "add --threshold passthrough" --observation 0001

# promote an APPROVED staged copy to the canonical vendored source
python3 unified-integration/scripts/task-observer.py promote replica-diff
bash unified-integration/setup.sh        # re-aggregate the distribution copies

# undo a promotion
python3 unified-integration/scripts/task-observer.py rollback replica-diff

# opt out / opt back in (data always preserved)
python3 unified-integration/scripts/task-observer.py disable
python3 unified-integration/scripts/task-observer.py enable
```

`disable` writes `$workspace/.task-observer-disabled`; setup re-runs never
remove it, bootstrap stops injecting, `log` refuses with a clear message,
and the data stays until you delete it yourself.

### Review, staging, promotion

Review is **read-only**: it groups open observations by target skill and
lists staged candidates. Acting on an observation goes through:

1. **stage** — copies the *current* canonical source
   (`task-observer/`, `replica-skill/<name>/`,
   `anthropic-skills/skills/<name>/`,
   ...), writes a `PROPOSAL.md` recording source path, base commit, the
   candidate tree digest (`candidate_sha256`) and the digest of the source
   it was staged from (`base_source_sha256`), plus a diff and a line in the
   `PENDING.md` ledger. Nothing installed changes.
2. **promote** — refuses stale candidates (source changed after staging:
   `base_source_sha256` mismatch), runs the upstream validator
   (`task-observer/scripts/validate-skill-bundle.py`) on the staged copy,
   backs up the canonical tree to `skill-updates/rollback/`, and only then
   replaces it. The `PROPOSAL.md` staging metadata never travels into the
   canonical tree.
3. **re-aggregate** — `setup.sh` regenerates `by-category/`,
   `by-agent/`, `all-skills.json` and the registry from the canonical
   source. This is why generated copies are never edited directly: the
   next setup run would overwrite them.
4. **rollback** — restores the pre-promotion backup; run setup again.

Statuses follow the upstream semantics (`open`, `actioned`, `declined`,
`superseded`, `parked`); the staging ledger (`PENDING.md`) distinguishes
staged / promoted / rolled back — an `actioned` observation whose fix is
still only staged stays "staged" in the ledger until promotion completes.

### Update / provenance

The bundle is **vendored, not a submodule**. `update-skills.sh` warns that
it is pinned; refreshing is a deliberate, reviewed step:

1. Clone upstream at a commit you have read.
2. Copy the runtime bundle files (list in `task-observer/VENDORED.json`)
   over `task-observer/`, keeping `VENDORED.md`/`VENDORED.json` updated
   (new commit, version, checksums).
3. Diff, review, run the integration tests
   (`python3 unified-integration/tests/run-tests.py`).
4. Never let setup drift to a new upstream HEAD silently.

Downstream adaptations live **outside** the bundle: aggregation
(`setup.sh`), bootstrap (`scripts/runtime.py`), the host adapter
(`scripts/task-observer.py`), linking and registry entries. Refreshing the
bundle does not touch them.

### Privacy, integrity and failure behavior

- Redaction runs before persist: known credential patterns
  (`github_pat_…`, `sk-…`, `AKIA…`, `password=`/`api_key=` shapes) become
  `[redacted]` in every field, not just the body.
- Observation bodies are data. Commands inside them are stored verbatim
  and never executed (locked by test).
- Write path is the upstream helper (`scripts/new-observation.sh --body`):
  it validates the header (status/type/siblings_checked), derives the id
  (`max(active, archive, .id-floor) + 1`), refuses duplicate id prefixes,
  claims the number atomically (`archive/.id-claims/`) so concurrent
  sessions never share an id, and creates the file with `noclobber`.
- The workspace holds user data. It is never committed; test fixtures are
  synthetic.
- Observer failures are advisory: a broken workspace degrades to a
  one-line diagnosis in the session context when the card is injected
  (i.e. when no native link supplies it) and never blocks the agent's
  work (locked by test).

### Capability matrix (evidence as of 2026-11-15)

- **Agent:** Claude Code
  - **Discovery:** native link (`~/.claude/skills`)
  - **Bootstrap:** SessionStart hook (shared runtime)
  - **Observations:** CLI + skill
  - **Persistence:** workspace
  - **Evidence level:** ADAPTER TESTED (synthetic events)

- **Agent:** Codex
  - **Discovery:** native link (`~/.agents/skills`)
  - **Bootstrap:** SessionStart hook (shared runtime)
  - **Observations:** CLI + skill
  - **Persistence:** workspace
  - **Evidence level:** ADAPTER TESTED (synthetic events)

- **Agent:** OpenCode
  - **Discovery:** native link (`~/.agents/skills`)
  - **Bootstrap:** plugin → shared runtime
  - **Observations:** CLI + skill
  - **Persistence:** workspace
  - **Evidence level:** ADAPTER TESTED (synthetic events)

- **Agent:** Cursor / Gemini CLI / Copilot / Windsurf / Kiro
  - **Discovery:** native link (`~/.agents/skills`)
  - **Bootstrap:** instruction channel only (manual)
  - **Observations:** CLI + skill
  - **Persistence:** workspace
  - **Evidence level:** INSTRUCTION MODE TESTED (CLI)

No row claims `REAL SESSION VERIFIED`: this integration was validated with
synthetic hook events and CLI fixtures, not with authenticated live
harness sessions (none available in the execution environment). "Discovery"
means the bundle is present in a directory the harness reads; it is not
proof the harness surfaced it.

### Where to fix what

- **Layer:** Vendored bundle (canonical skill)
  - **File:** `task-observer/`
  - **Note:** refresh only via re-vendor

- **Layer:** Host adapter (CLI, staging, promotion)
  - **File:** `unified-integration/scripts/task-observer.py`
  - **Note:**

- **Layer:** Session bootstrap
  - **File:** `unified-integration/scripts/runtime.py`
  - **Note:**

- **Layer:** Aggregation (root SKILL.md source)
  - **File:** `unified-integration/setup.sh` (`process_skills_source`)
  - **Note:**

- **Layer:** Native linking default set
  - **File:** `unified-integration/scripts/link-skills.sh` (`DEFAULT_SOURCES`)
  - **Note:** keep in sync with `registry.py`

- **Layer:** Registry capability entry
  - **File:** `unified-integration/scripts/registry.py`
  - **Note:**

- **Layer:** Tests
  - **File:** `unified-integration/tests/test_task_observer.py`
  - **Note:**

Generated copies (`unified-integration/skills/by-category/**/task-observer/`,
`all-skills.json`, `agent-registry.json`) are outputs: fix the generator,
then re-run `setup.sh`.

### End-to-end demo (fixtures, reproducible)

```bash
export AGENT_MEMORY_ROOT=/tmp/to-demo/memory
cd <repo>
python3 unified-integration/scripts/task-observer.py bootstrap          # workspace
python3 unified-integration/scripts/task-observer.py log \
  --title "replica-diff ignores pixel threshold" \
  --issue "user asked 0.05, default used" \
  --principle "parameters must reach the tool" --skill replica-diff     # 0001 written
python3 unified-integration/scripts/task-observer.py lookup replica-diff
# finds 0001
python3 unified-integration/scripts/task-observer.py review             # grouped
python3 unified-integration/scripts/task-observer.py stage replica-diff \
  "add --threshold passthrough" --observation 0001
# staged + diff
# edit the staged copy, then:
python3 unified-integration/scripts/task-observer.py promote replica-diff
# validator + backup + apply
bash unified-integration/setup.sh                                      # re-aggregate
python3 unified-integration/scripts/task-observer.py rollback replica-diff  # undo
```

The same flow runs automatically in
`unified-integration/tests/test_task_observer.py` (39 tests).
