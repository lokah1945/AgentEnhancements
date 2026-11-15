---
title: task-observer vendored source
version: 1.0
last_updated: 2026-11-15
audience: maintainers
---

# task-observer (vendored)

Canonical source of the `task-observer` skill integrated by AgentEnhancements.
Do not edit files here as the only copy of a change: this tree is refreshed
from upstream (see "Updating" below); downstream adaptation lives in the
integration layer, not in this bundle.

| Field | Value |
|-------|-------|
| Upstream | <https://github.com/rebelytics/one-skill-to-rule-them-all> |
| Pinned commit | `d61bc31f7857948710a947673c0e373bef4ed3d0` |
| Skill version | 3.10.0 |
| License | CC-BY-4.0 (LICENSE in this directory) |
| Author | Eoghan Henn and contributors |
| Vendored | 2026-11-15 |

## Attribution

The bundle is © Eoghan Henn and contributors, licensed CC-BY-4.0. Keep the
LICENSE file and this manifest with any copy.

## What is vendored

The runtime skill bundle only: `SKILL.md`, `references/`, `scripts/`, the
license and the user-facing guides.

Excluded on purpose (host integration supplies its own activation channels):
`plugins/task-observer-flush/` (Claude Code plugin, experimental upstream;
the shared runtime Stop hook covers the backstop), `.claude-plugin/`
marketplace metadata, `.github/`, `README.md` (repo-level README; the skill
docs live in SKILL.md + USER-GUIDE.md), `OPEN-SKILL-LIBRARY.md`, and
`.gitattributes`.


## Updating

Re-vendor deliberately (never silently move to a new HEAD):

1. Clone upstream at the commit you reviewed.
2. Re-run the vendoring step (see `docs/UPDATING.md`).
3. Diff the new tree against this one; record the new pin in this file and
   in the manifest checksums.
4. Downstream adaptation (aggregation, linking, runtime bootstrap) lives in
   `unified-integration/`; verify it still applies after the refresh.

## Checksums

File checksums for this vendoring are recorded in `VENDORED.json` (machine
readable); the file list and reasons above are the human-readable contract.
