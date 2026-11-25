---
title: Preflight mode numbering deviation (AE-003)
version: 1.0
last_updated: 2026-11-25
audience: maintainers, contributors
---

# Preflight mode numbering deviation (AE-003)

## Finding

`CONTRACT.md §8.5` and several derived documents describe adaptive preflight
modes 0 (disabled), 1 (host-native) and 2 (custom endpoint). The shipped code
accepts only `0` and `1`; integer `2` is rejected with
`preflight_invalid:mode_not_0_or_1` and falls back to Mode 0.

## Evidence

- `unified-integration/scripts/adaptive_preflight.py:69-71` — `MODE_DISABLED = 0`,
  `MODE_CUSTOM = 1`, `VALID_MODES = (0, 1)`; no `MODE_NATIVE` symbol.
- `adaptive_preflight.py:262-263` — strict type/membership check.
- `adaptive_preflight.py:1136` — "Only MODE_CUSTOM (1) is supported;
  MODE_NATIVE was removed".
- `git show 095fc19d6e59ad22a04430108067b60f553a9fa5` — pushed commit
  (2026-11-25, git author `lokah1945`, commit body declares `Agent: Claude Code`)
  with body: "Remove non-functional Preflight Mode 1
  (AE-003): Mode 1 (native host selection) had no adapter implementation;
  collapse to Mode 0 (disabled) and Mode 1 (custom model) only."
- `git show a6cf872020d298c7c54a723d2f7d43f200b493c0` — same decision recorded;
  its example-config edit is internally contradictory and was corrected here.
- `unified-integration/tests/test_adaptive_preflight.py` — 0 and 1 are the only
  valid modes; the new regression pins integer 2 as invalid.

## Resolution applied

Code is behaviorally authoritative; the deliberately removed host-native mode
is not restored. Derived descriptors were aligned to the implementation:
`ui.api.schema.json` enum `[0, 1]`, `ui.api.example.json`, `README.md`,
`docs/API.md`, `docs/ADAPTIVE_PREFLIGHT.md`, module docstring/labels, the
opt-in smoke harness and the live test.

`CONTRACT.md` was **not** edited. Its End of Contract clause requires explicit
written maintainer approval, and no such amendment exists. A future
maintainer-approved §10 version entry should amend §8.5 to the implemented
0/1 contract; this note records the deviation until then.

## Impact and cost if wrong

- A user following the old docs sets `mode: 2`; the runtime fails closed to
  Mode 0 with a stderr diagnosis instead of silently calling a model.
- Reviewers reading only CONTRACT §8.5 will see a mismatch; this note and the
  corrected derived docs explain it.
- Cost if the maintainer instead wants the three-mode design restored: the
  now-removed native adapter must be implemented and CONTRACT §8.5 kept as-is;
  this change would need reverting.
