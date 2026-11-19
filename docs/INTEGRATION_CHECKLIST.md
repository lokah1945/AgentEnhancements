---
title: Integration Checklist
version: 2.0
last_updated: 2026-11-19
audience: all agents and contributors
---

## Integration checklist

Use this checklist against the current revision. Dated test results and
previous repair claims remain in [audit reports](audit/) and the changelog;
they do not certify a new installation. Current inventory totals are
[generated from canonical data](CAPABILITY_COUNTS.md).

### Catalog and skill sources

- [ ] Run `python3 unified-integration/scripts/catalog-validate.py --root .`.
- [ ] Regenerate the modular tree and manifest with
  `bash scripts/scaffold_modular_skills.sh` and
  `python3 scripts/generate_skills_index.py`.
- [ ] Run `bash unified-integration/setup.sh` to aggregate all skill sources.
- [ ] Verify unique skills, source counts and registry counts with
  `python3 scripts/generate_capability_counts.py --check`.
- [ ] Test representative guides, including an agency pack, with
  `bash unified-integration/scripts/catalog-test.sh nexus`.

### Native activation

- [ ] Verify the selected hosts and Hermes profiles using the
  [agent guide](AGENTS.md); preserve host authentication and approval policy.
- [ ] Inspect `bash unified-integration/scripts/link-skills.sh --status`.
- [ ] Confirm default workflow skills are discoverable and other skills can
  be found through registry search and loaded on demand.
- [ ] Exercise automatic notes in an isolated fixture home; keep raw tool
  payloads and transcripts outside the memory store.

### MCP and external dependencies

- [ ] Run the bundled protocol check:
  `bash unified-integration/scripts/setup-mcp.sh --check`.
- [ ] Enable external dependencies only after verifying the upstream package,
  authorization, executable and central credential mappings.
- [ ] Follow the [MCP checklist](MCP_INTEGRATION_CHECKLIST.md). Search
  candidates
  use You.com, Serper, Tavily and Exa; Brave is absent from the active catalog.
- [ ] Verify tool availability and revocation through the actual selected host.
  A catalog status is separate from runtime readiness.

### Release verification

- [ ] Run the complete integration suite with the prepared Python runtime.
- [ ] Run the complete ECC suite with CI's dependency and scheduling policy.
- [ ] Verify generated files and index stability across repeated setup runs.
- [ ] Review source licenses and notices before re-vendoring or redistribution.
- [ ] Confirm GitHub Actions results for the exact release commit.
- [ ] Record deferred findings and test limitations with their evidence.
