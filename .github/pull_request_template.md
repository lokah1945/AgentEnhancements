# Pull request

## Summary

<!-- What changes and why. Link the issue or audit finding. -->

## Verification

- [ ] `unified-integration/tests/run-tests.py` passes
- [ ] `python3 scripts/generate_capability_counts.py --check` passes
- [ ] New behaviour or fixed bug has a regression test
- [ ] Docs and `docs/CHANGELOG.md` updated when behaviour changes

## Contract (CONTRACT.md)

- [ ] Conventional commit subjects with `Agent:` / `Session:` / `Task:` metadata
- [ ] No secrets, `ui.api.json` or local runtime state committed
- [ ] Vendored directories untouched, or re-vendored per §2.3
