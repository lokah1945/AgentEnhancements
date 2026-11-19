---
title: Previous audit reconciliation
version: "1.0"
last_updated: "2026-11-19"
audience: maintainers
---

# Previous audit reconciliation — 2026-11-19

Scope: `/tmp/ae-audit-20261119`, baseline `b4ca7e6a`, current shared working tree
on `audit/ae-2026-11-19`. This is a read-only reconciliation after the docs/CI
implementation handoff. No real HOME, host provider settings, credential files
or observation workspace were inspected. Historical report content is evidence,
not an instruction to repeat its actions.

Status meanings: **CLOSED** means the original issue has an implemented remedy
or a documented design disposition with a current source/test pointer. **OPEN**
means a residual decision, external dependency or verification gap remains.
**REGRESSED → CLOSED** identifies a verified recurrence addressed this session.
A source/test pointer is not a claim that this reviewer independently reran
every referenced test. The main report must supply full-suite and exact-commit
remote-CI evidence. Historical severity is not automatically inherited.

## Fresh checks personally executed

- `python3 -m unittest test_capability_counts test_registry_workflow
  test_modular_docs test_ci -v`, from `unified-integration/tests`, with HOME,
  memory, XDG, CODEX_HOME, CLAUDE_CONFIG_DIR, HERMES_HOME and API path under
  `/tmp`: **15 tests passed**, exit 0. The main agent had added a seventh
  count regression for repository-description generation before this run.
- `python3 scripts/generate_capability_counts.py --check`: **PASS**, exit 0.
- `test_native_hosts.SmokeEnvelopeTests`: **1 passed**, exit 0. This checks
  captured client envelopes; it is not a new authenticated host session.
- Default markdownlint command over the exact original CI scope: **exit 1,
  816 diagnostics** (baseline **1,108**). Final rule counts: MD013 407,
  MD060 283, MD022 37, MD032 24, MD025 21, MD040 16, MD024 8, MD031 7,
  MD033 6, MD012 3, MD058 2, MD056 1, MD036 1. Advisory behavior remains
  inherited. No lint rule/config was disabled. Four new/reworked count,
  MCP and search guides have **zero** default-rule diagnostics.
- Current ordinary Markdown links in both READMEs and root `docs/*.md`:
  no nonexistent local file targets found (fragments and external targets
  excluded). Historical links were retained as revision-specific evidence.

## New documentation / CI findings and disposition

| ID | Severity | Root cause and reproduction | Current disposition / evidence |
|---|---|---|---|
| DOC-01 | P2 | Counts were duplicated across root guides: raw AAS 2,781 vs unique indexed 2,729, 9/10/11 vendor totals, 236/323 test totals, 38/40 MCP totals. Reading the canonical JSON and README tables reproduced the mismatch. | CLOSED: `scripts/generate_capability_counts.py`, generated `docs/CAPABILITY_COUNTS.md`, `docs/capability-counts.json`, both README summary blocks, `test_capability_counts.py`. Derived totals: 3,378 unique skills / 3,430 raw records / 8 sources; 40 plugin entries / 22 upstreams; 40 MCP entries / 10 built statuses / 9 bundled backends / 8 default-enabled; 8 built-ins; default native 16 / optional curated 31; 11 vendor directories. No permanent regression-test total is presented as current evidence. |
| DOC-02 | P2 | `generate_skills_index.py` replaced implementation status with `vendored` based on a different boolean and claimed remote upstreams were fetched on demand. Controlled input with `vendored: true,status: integrated-ready` generated the wrong status table. | CLOSED: `test_modular_docs.py` failed before the fix and passes now. The generator uses actual catalog status, counts status independently and describes external installation honestly; `skills/` READMEs regenerated. |
| DOC-03 | P2 | LICENSE_AUDIT claimed missing `doc-coauthoring/LICENSE.txt` was covered by a repo-wide Apache license, but the vendored Anthropic tree has no root LICENSE. | OPEN upstream coverage clarification; unsupported claim corrected. 18/19 per-skill LICENSE.txt files inspected and Apache-2.0 confirmed. Root license notice, LICENSE_AUDIT and third-party notices now identify the gap. This is file evidence, not a legal guarantee. |
| DOC-04 | P2 | Dated production report retained truncated credential previews and a command that printed returned keys. | CLOSED in working tree: `AuditReport/ae-final-production-report-20261117.md` previews redacted and command reports presence instead of values. No preview values reproduced here. Credential revocation / Git-history exposure assessment belongs to main security audit. |
| DOC-05 | P2 | Current guides mixed obsolete native config paths, Brave installation, automatic remote installation, nonexistent setup options, and unsupported provider HTTP authentication/parameter/quota assertions. `FIXES_AND_USAGE.md` also recommended deleting all integration directories and the real memory DB for rebuilds. | CLOSED for rewritten current setup/MCP/search/usage guides. `docs/SEARCH_PROVIDER_APIS.md` now documents AE's actual subprocess/credential boundary, not an unimplemented HTTP adapter. Current MCP/checklist/usage guides point to canonical configuration and prepared runtime; destructive rebuild recipe removed. Dated audit evidence retained. |
| DOC-06 | P3 | `README_INTEGRATION.md:149-166` still describes strict catalog → modular tree → unified index flow; aggregation actually consumes vendored skill sources while catalog guides are a separate registry surface. | CLOSED in final main integration: current pipeline/cookbook/API descriptions corrected; see dated end-to-end report. |
| DOC-07 | P3 | `docs/COOKBOOK.md:17,127` still presents REA as a generic research/bug orchestrator, conflicting with the corrected Reverse Engineer Anything identity. | CLOSED in final main integration: current pipeline/cookbook/API descriptions corrected; see dated end-to-end report. |
| DOC-08 | P3 | `docs/API.md` config-merge section still names removed `merge_json_config` / generic `merge_<format>` API although only `merge_yaml_config` is present. | CLOSED in final main integration: current pipeline/cookbook/API descriptions corrected; see dated end-to-end report. |
| CI-01 | P2 | Registry workflow rebuilt registry consumers without re-aggregating vendor skills. A fixture changed source.txt while index.txt remained old; actual extracted build step produced an old registry and failed the test. | CLOSED: workflow now calls canonical setup before registry/map generation, relevant source paths trigger it, isolated HOME/XDG/memory set, headroom skipped for this focused registry job. `test_registry_workflow.py` RED → GREEN. Full headroom gets its separate non-advisory CI job added by main. |
| CI-02 | P3 | Top-level workflows used mutable action major tags; checkout persisted the Git token unnecessarily. | CLOSED: all existing official actions pinned to verified current-major SHAs; checkout `persist-credentials: false`; existing `contents: read` preserved; no pull_request_target privilege expansion. See verified upstream commit sources below. |
| CI-03 | P3 | Registry workflow globally installed latest pip/PyYAML despite a canonical isolated runtime; ECC used npm install instead of lockfile installation; advisory markdownlint fetched an unconstrained latest version. | CLOSED focused changes: canonical setup prepares Python; `npm ci`; markdownlint-cli pinned 0.49.1 with Node 22 (its package engines require >=22); ECC remains Node 20. Broader Python ranges / system apt reproducibility remain the maintainer's documented tradeoff. |
| CI-04 | P3 | Existing advisory markdownlint concealed a large owned-doc style backlog. | CLOSED in final integration:1,108 baseline →816 early review →0 diagnostics under unchanged default rules. Markdownlint is now required; inherited advisory bypass removed. |

## AE-01 through AE-22 — independent audit 2026-11-15

Sources: `docs/audit/AGENTENHANCEMENTS_E2E_AUDIT_2026-11-15.md` and
`REMEDIATION_CLOSURE_2026-11-15.md`. Original findings are not new findings.

| ID | Status | Current evidence / limitation |
|---|---|---|
| AE-01 | CLOSED historical account incident; current release verification separate | Closure report records CI green 5/5 at a88efe65; native-host report later records full ECC success. Do not repeat “never green.” Main must report latest actual GitHub run for the final SHA; no inference from local tests. |
| AE-02 | CLOSED material labeling error | Root LICENSE explicitly scopes MIT to owned layer; claude-mem/headroom Apache LICENSE+NOTICE and system-prompts GPL LICENSE verified; README provenance corrected. DOC-03 tracks the narrower Anthropic gap rather than reopening original labeling issue. |
| AE-03 | OPEN documented maintainer decision | GPL prompt archive and extracted commercial prompt rights remain a redistributor/maintainer decision; source/notice retained. No legal approval or removal inferred. |
| AE-04 | CLOSED by documented vendoring policy | CONTRACT 2.3/5.2 and `docs/UPDATING.md` specify deliberate re-vendoring, not submodule pulls. `update-skills.sh` refreshes local aggregation. Do not rediscover absence of nested .git as a new bug. |
| AE-05 | REGRESSED → mostly CLOSED | DOC-01/05 fix current count and procedure drift. Remaining focused DOC-06/07/08 handed to main. Historical counts in dated reports/changelog intentionally preserved. |
| AE-06 | CLOSED original mechanism claim | Unsupported Continue paths removed from current integration guide; `.cursorrules` is not claimed to be symlinked by setup. Historical ADR-006 remains a dated decision and is not rewritten. |
| AE-07 | CLOSED | `catalog-test.sh` derives categories from catalog; `CatalogTestAgencyTests.test_agency_slug_smoke` covers nexus. Persona packs with no MCP dependency are not automatically defective. |
| AE-08 | REGRESSED → CLOSED | 2026-11-16 fallback deduplication reintroduced semantic loss / exaggerated reduction claims. Main repairs compressor path; current README/API/CONFIG describe explicit utility, native CLI compaction and cap. Test coverage in test_compress; main owns final Rust/CLI verification. |
| AE-09 | CLOSED | README explicitly labels copied system prompts reference material; no automatic system-prompt activation promised. |
| AE-10 | CLOSED mitigation, inherent execution boundary remains | `api_config.DEFAULT_DISABLED` hides task-router; opt-in still executes user-privileged commands. `TaskRouterHardeningTests` covers Python destructive payload refusal/default hiding. Denylist is not a sandbox. |
| AE-11 | OPEN residual supply-chain tradeoff; several fixes CLOSED | Installer supports AGENT_ENHANCEMENTS_REF and now refuses missing requested pins (`test_setup_safety.test_piped_installer_refuses_missing_pin`); existing copy refresh is ff-only. Action SHAs pinned; runtime dependencies now include filelock security fix/refresh. README curl master script and ranged dependencies are not fully reproducible/checksummed releases. |
| AE-12 | CLOSED historical blanket ECC-failure assertion; exact current suite belongs to main | Native-host report records 8,289/0 under isolated environment. Current job uses Node 20, dependencies and serial mutating/timing suites; `test_ci` passed. Do not relax ECC gate or inherit old 43-failure totals as current. |
| AE-13 | CLOSED | Generated-at-install modular tree explicitly documented; canonical catalog remains source; `skills/manifest.json` and generators describe generated tree. |
| AE-14 | CLOSED | Timestamp-preserving registry/map generation and deterministic index tests; regeneration workflow checks all committed consumer artifacts. New count --write preserves unchanged mtime in behavioral test. |
| AE-15 | CLOSED by documented limitation; comment-preserving writer deferred | OpenCode JSONC values/config arrays preserved; comments remain in private backup and limitation documented. Current docs do not claim comments survive serialization. |
| AE-16 | CLOSED original false success; strengthened current privacy | initializer checks real DB availability; main adds mode/symlink refusal coverage in `test_setup_safety.test_memory_initializer_creates_private_storage_and_refuses_db_symlink`. |
| AE-17 | REGRESSION then CLOSED | First reinstall still reformatted equivalent YAML and made a backup. AE26-31/`1b3951ed` preserves original bytes; two new regression tests fail before the fix and pass after it. |
| AE-18 | CLOSED | `/usr/local/bin` launcher requires `INSTALL_SYSTEM_LAUNCHER=1`; default uses repository-local launcher. |
| AE-19 | CLOSED | Catalog/roadmap reference validator and nexus path tests; catalog validation and current generated count check. Native default status mismatch independently covered by count generator. |
| AE-20 | CLOSED original dead-code set | Unused merge_json_config removed; updater's impossible daemon rebuild removed; unsupported Continue removed from current guides. DOC-08 is a stale documentation name, not revived runtime code. |
| AE-21 | CLOSED documentation mitigation | SAFETY/ENV_VARS/CONFIG document image upload and cloud gating; local comparison/OCR distinguished. Consent remains the user's decision. |
| AE-22 | CLOSED original install side effect | `mcp-test.sh` only prepares on explicit --prepare; prechecks jq/Python/json5. Residual hardcoded venv lookup ignores XDG_DATA_HOME and deserves P3 follow-up; see notes below. |

## LIBRARY_MODEL_CLOSURE residuals and review IDs

| ID | Status | Current evidence / limitation |
|---|---|---|
| S1 | CLOSED | Transactional observer rollback; `ReviewHardeningTests.test_rollback_is_transactional`; private candidate/backup swap and restore path. |
| S2 | CLOSED | `_copy_tree` preserves symlinks and refuses copy failures; `test_staged_symlink_is_copied_as_link_not_dereferenced`. |
| H1 | CLOSED | check-protocol parses actual consolidated ae_health structured/text result; degraded verdict branch exercised by hardening coverage. |
| H2 | CLOSED original fixture bug | `smoke-native-clis.py` understands ae_health tool prefixes/envelopes. `SmokeEnvelopeTests` independently rerun here 1/1 PASS. `NATIVE_HOSTS_E2E_2026-11-16.md` records actual CLI fixture success. A new authenticated session is outside this review, not proof the old bug persists. |
| H4 | CLOSED | L0 `rendered` persists in library-map.json; build-library-map CLI has actual argparse/text-output handling. |
| H6a | CLOSED | Ownership-safe migration restores parked rows without clobbering user slots; link-skills audit/migration tests. Main adds independent registry traversal and destination-symlink safety. |
| S4 | REGRESSED / incompletely mitigated → CLOSED now | Old acceptance relied on whitelisted external health fields, but configured credentials could survive truncation/other fields. Current gateway `_redact_payload` cleans complete payload recursively before truncation; `GatewayHealthSecurityTests.test_health_redacts_secrets_before_truncation_in_every_field`. Do not mark old whitelist reasoning sufficient. |
| S5 | CLOSED before this audit baseline | `gateway.py:54-103` explicitly preserves keys in a JSON-schema `properties` container, including parameter name `title`, while dropping annotation titles. The old feared disappearing title parameter is no longer present in source. No new runtime S5 proof was fabricated; schema regression gap can remain P3 if main wants a dedicated test. |
| S6 | OPEN accepted low-priority / insufficiently specified | Closure report groups S6 as LOW/recommended but does not describe an independently reproducible bug. Retain inherited disposition; do not invent a fix or claim new severity. |
| S8 | OPEN accepted bounded-content risk | Vendor/observation content remains data under host permissions; bounded observer context and no automatic execution mitigate it. Source body quality is not universally certified. |
| S9 | OPEN accepted bounded-content risk | Same historical grouping concerns control characters / untrusted observation content. Current size/security guards improve it; no claim of universal prompt-injection elimination. |
| S10 | OPEN accepted low-priority / unspecified | Only present in grouped LOW row; no standalone detail sufficient for a new verified defect. |
| S11 | OPEN accepted low-priority / unspecified | Same as S10. |
| H5 | CLOSED by accepted idempotency disposition | Duplicate OpenCode Stop backstop writes share memory keys/upsert semantics. No exactly-once callback claim is made. |
| H8 | OPEN accepted low-priority / unspecified | Grouped LOW finding without standalone reproduction in the retained closure report. |

## Original F findings — 2026-11-01

Source: `docs/audit/AUDIT_REPORT.md`; subsequent remediation, production
readiness and E2E reports verify the merge. These are tracked individually
to avoid falsely reissuing the original list.

| ID | Status | Evidence / disposition |
|---|---|---|
| F-01 | CLOSED | Python parameterized SQL hooks and injection round-trip tests; main adds private-file/symlink regression coverage. |
| F-02 | CLOSED | Third-party metadata carried through record file, not Python source interpolation; setup static guard. |
| F-03 | CLOSED | `compress.py` imports re; logs regression. |
| F-04 | CLOSED original nesting; new safety strengthened | Copy targets reset under checked boundaries; `test_setup_safety` reproduces destination symlink/data-loss and swallowed-copy failure, fixed by main. |
| F-05 | CLOSED | globstar/nullglob enabled and prompt generation refreshed. |
| F-06 | CLOSED | Self-locating launcher and env overrides; generator/artifact sync guard. |
| F-07 | CLOSED | Compressor wrapper matches setup heredoc; test_sync. |
| F-08 | CLOSED | Wrapper consumes stdin once, safe temp cleanup; tests/compress. |
| F-09 | CLOSED | Loader resolves root/env override and both layouts. |
| F-10 | CLOSED | Native JSON lifecycle bridge replaces invented tool environment arguments; session_context explicit and runtime tests. |
| F-11 | CLOSED | Generated README glyph corrected; sync/mojibake guard. |
| F-12 | CLOSED | Missing memory load exits 1; memory CLI tests. |
| F-13 | CLOSED | Committed local temp artifact removed and ignored-state policy present. |
| F-14 | CLOSED runtime checks; advisory lint debt separate | Both test suites, static syntax/JSON, filename and count guards exist in CI. CI-04 retains actual lint debt. |
| F-15 | CLOSED | README installer repository/branch/directory corrected; pinned bootstrap semantics independently strengthened now. |
| F-15b | CLOSED / superseded | Updater re-aggregates intentional vendored copies; no origin/HEAD claim. |
| F-16 | CLOSED | Required docs set exists. |
| F-17 | CLOSED | YAML merge receives data through environment rather than Python interpolation; native config has dedicated serializers. |
| F-19 | CLOSED | Index built in one pass, not per-record full-file rewrite. |
| F-20 | CLOSED | Empty detected-agent handling retained under shell strict mode. |
| F-21 | CLOSED | Loader supports graceful PyYAML fallback. |
| F-22 | CLOSED by explicit vendoring policy | No submodules is now intentional, with upstream/license documentation and reviewed update procedure. |
| F-23 | CLOSED | detected-agents.sh is ignored machine state. |
| F-24 | CLOSED | Script-derived install root; env override remains. |
| F-24b | CLOSED | Index timestamp uses timezone-aware datetime. |
| F-25 | CLOSED | Counter arithmetic no longer exits on first increment under set -e. |
| F-26 | CLOSED | SQLite-compatible UTC expiry and read-time filtering. |
| F-27 | CLOSED old absence-of-cargo crash | Build failure falls back; current real Rust compiler defect fixed separately by main and covered in new headroom job. |
| F-28 | CLOSED documented generation policy | Committed index and generated ignored registry tree are distinguished; no need to commit thousands of directories. |

## Production-readiness P findings — 2026-11-13

| ID | Status | Evidence / disposition |
|---|---|---|
| P-01 | CLOSED | Prior deep-review fixes were merged; do not repeat “all old fixes unmerged.” |
| P-02 | CLOSED | Codex instructions/config.toml/hooks.json native paths; native configuration tests. |
| P-03 | CLOSED | OpenCode 2 JSON(C), native plugin and provider-array preservation; V1 refusal regression. |
| P-04 | CLOSED | Correct README install URL/repository path. |
| P-05 | CLOSED | Cursor global .mdc rule, not invented settings keys. |
| P-06 | CLOSED | Windsurf uses .codeium/windsurf/rules. |
| P-07 | CLOSED | Canonical repository URLs validated; current README_INTEGRATION claude-mem/headroom typo recurrence corrected. |
| P-08 | CLOSED | Catalog wiring skips real user files/directories; no unconditional catalog rm of actual bundles. |
| P-09 | CLOSED | Consent EOF becomes an explicit logged refusal; privacy/redaction strengthened now. |
| P-10 | CLOSED | Generated registry trees ignored. |
| P-11 | CLOSED | perf word-boundary routing and dispatcher regressions. |
| P-12 | CLOSED | Gemini marker-merged GEMINI.md instruction channel. |
| P-13 | CLOSED | Broken AAS pdf/xlsx symlinks removed; source paths now resolve. |
| P-14 | CLOSED | Catalog parse failure handling/executable; catalog validator tests. |
| P-15 | CLOSED | Audit trail uses entry_type, not builtin-shadowing type. |
| P-16 | OPEN low-priority checker limitation | mcp-test remains a configuration smoke check, not runtime protocol certification; --server unknown ID not explicitly rejected by get_servers. A nonexistent server normally fails configuration, so original arbitrary-command-pass claim should not be repeated without fixture proof. |
| P-17 | OPEN intentional compatibility limit | Copilot/Kiro receive clearly labeled reference configs; not certified equivalent lifecycle adapters. |
| P-18 | OPEN metadata debt | External $schema metadata can point to unavailable agentenhancements.dev definitions; local schema validation remains the actual guard. No unsupported live DNS claim made here. |
| P-19 | CLOSED | timezone-aware datetime replaced utcnow. |

## E2E November audit H/M/L findings

| ID | Status | Evidence / disposition |
|---|---|---|
| H-1 | CLOSED | CLAUDE.md marker merge preserves personal text; test_hardening ClaudeMdPreservationTests. |
| H-2 | CLOSED | Sorted index and registry; deterministic tests and unchanged-write behavior. |
| M-1 | CLOSED original drift; current sync belongs to final suite | Generated prompt/hooks match templates; machine-specific detected state ignored. Main refreshes Codex prompt reference and templates. |
| M-2 | CLOSED with stronger honest-failure contract | Malformed native config preserved and setup reports failure (`test_malformed_user_config_is_untouched_and_setup_reports_failure`); do not restore old false-success behavior. |
| M-3 | REGRESSED → CLOSED | MCP count increased again after prior 36→38 fix; generated inventory and existing hardening test now track 40 canonical entries. |
| M-4 | REGRESSED → CLOSED | Setup-generated README/source counts now use dynamic/pointer output; current count guards and human guides corrected. |
| M-5 | CLOSED | CI builds source tree before integration suite; registry workflow now also re-aggregates before drift checks. |
| L-1 | CLOSED original dot/dotdot; further boundary issue fixed now | Name guard retained; main adds registry traversal/destination symlink regressions. |
| L-2 | CLOSED | timezone-aware index timestamps. |
| L-3 | CLOSED | No “FIXED VERSION” setup header. |
| L-4 | CLOSED | Test docstring invalid-escape warning corrected historically. |

## AuditReport / SDD 2026-11-16 and 2026-11-17 reconciliation

- SDD Task 1/6 native parity: CLOSED implemented adapter paths; real host
  verification remains revision/host-specific. Writing generic hooks into
  OpenCode JSON is not sole proof of activation; the V2 plugin is the bridge.
- SDD Task 2 default native targets: CLOSED; four target directories and the
  default source alignment are implemented. Sixteen workflow skills do not
  imply the whole library is natively loaded.
- SDD Task 3 empty memory type: CLOSED for new writes/session_context; legacy
  cleanup affected a prior user's local DB and is not rerun in this audit.
- SDD Task 4 compression: REGRESSED → CLOSED by main: the 99% reduction recipe
  removed repeated code semantics and the Rust CLI did not compile. Do not
  preserve “backward compatible” or “semantic structure preserved” claims from
  that old report as current evidence. Main's Rust tests/build and fallback
  round-trips supersede it.
- SDD Task 5 registry view compatibility: CLOSED as not an actual required
  schema change; registry uses the canonical entries view and typed IDs.
- SDD Task 7 candidate flexibility: CLOSED as configurable bounded hook
  candidates, not all-task relevance quality. Current discovery benchmark
  and negative fixtures belong to main's current result, not old sample claims.
- SDD Task 8 all-systems green: prior execution ledger left checkboxes open;
  its presence is not evidence today's implementation is incomplete. Use
  current fresh verification, not hand-edited historical checkbox state.
- 2026-11-17 Issue 1 DEFAULT_NATIVE_SOURCES mismatch: CLOSED; literal source
  parity checked by count generator and native linkage tests.
- 2026-11-17 Issue 2 Hermes collision: mitigation is “warn/preserve user
  plugin,” not guaranteed activation of AE's plugin. This is not permission to
  overwrite the user's plugin. Main should retain that compatibility limit.
- 2026-11-17 Issue 3 Codex prompt missing: CLOSED; source lookup includes
  Open Source prompts/Codex CLI; main refreshed the generated reference.
- 2026-11-17 Issue 4 P0 external MCPs unconfigured: OPEN deployment prerequisite,
  expected by design; installing every roadmap candidate is not audit scope.
- 2026-11-17 Issue 5 JSONC comments: CLOSED by documented backup limitation.
- Brave removal: CLOSED active catalog; obsolete references in current
  operational guides corrected. Historical removal reports retain numbers.
- Search-provider “all integrated end-to-end” claims: historical evidence
  only. Configuring key rotation/environment does not certify installed
  upstream packages, HTTP contracts, quotas or actual search availability.
- Old high “agency MCP warnings” recommendation was not a security bug: persona
  packs can work without tool dependencies; current catalog validator is the
  authority, and an empty suggestion is not proof of incomplete execution.
- Old “gateway exposes only ae_health” / “no skills/ index” claims are
  contradicted by current gateway.tools and committed manifest/README. Do not
  reopen them without reproducing the active toolset/schema.
- Old cold-start totals around 461 counted only hook outputs while omitting
  other channels. Do not repeat as total context evidence; main's measured
  all-channel budget/benchmark is authoritative for the current revision.

## Other still-open P2/P3 limitations worth keeping explicit

- **P2 external ownership/license:** Anthropic missing per-skill notice
  coverage (DOC-03) and prompt archive rights (AE-03) require upstream or
  maintainer decisions. No notice/license content removed to manufacture a
  clean result.
- **P3 lint debt:** exact advisory lint result above. Passing functional and
  static syntax checks does not convert lint exit 1 into lint passing.
- **P3 installation/readiness:** optional external MCP runtime/package/OAuth
  verification and host-version limitations remain. Built catalog entry
  `agent_browser` is outside BUILTINS; source status alone is insufficient.
- **P3 checker ergonomics:** `mcp-test.sh:32` chooses the existing runtime from
  `$HOME/.local/share/...` rather than XDG_DATA_HOME, unlike canonical setup.
  On an XDG-only installation it can fall back to a Python lacking json5 and
  fail despite a prepared runtime. This was read-only discovered after the
  implementation freeze; no patch or live-host experiment performed here.
- **P3 documentation:** DOC-06/07/08 are a focused handoff, not a reason to
  rewrite historical ADRs/audits. Main may close them before final report.
- **Verification:** parent is responsible for full ECC/integration/CLI build,
  static checks, remote Actions and Git-history/credential exposure results.
  This artifact cannot certify a future final commit not yet created.

## Official action pin evidence

Resolved through the GitHub connector against official actions repositories,
retaining existing major lines:

- checkout v4 → `11d5960a326750d5838078e36cf38b85af677262`:
  https://github.com/actions/checkout/commit/11d5960a326750d5838078e36cf38b85af677262
- setup-node v4 → `49933ea5288caeca8642d1e84afbd3f7d6820020`:
  https://github.com/actions/setup-node/commit/49933ea5288caeca8642d1e84afbd3f7d6820020
- setup-python v5 → `a26af69be951a213d495a4c3e4e4022e16d87065`:
  https://github.com/actions/setup-python/commit/a26af69be951a213d495a4c3e4e4022e16d87065
- upload-artifact v4 → `ea165f8d65b6e75b540449e92b4886f43607fa02`:
  https://github.com/actions/upload-artifact/commit/ea165f8d65b6e75b540449e92b4886f43607fa02

## Completed read coverage

Full CONTRACT.md and both README files; both top-level workflows; root
LICENSE; in-tree license/notice headers for all eleven vendors; all eighteen
Anthropic per-skill LICENSE headers and its root README/notices inventory.
Source/tool reads included current count/scaffold generators, registry,
native linking, API config, CI tests/runner, selected gateway/native/installer
paths and all new owned regressions.

All original docs read, including nested historical evidence:

```
docs/ADAPTIVE_PREFLIGHT.md
docs/ADR.md
docs/AGENTS.md
docs/API.md
docs/ARCHITECTURE.md
docs/CHANGELOG.md
docs/CONFIGURATION.md
docs/CONTRIBUTING.md
docs/COOKBOOK.md
docs/ENV_VARS.md
docs/FIXES_AND_USAGE.md
docs/INTEGRATION_CHECKLIST.md
docs/LICENSE_AUDIT.md
docs/MCP_INTEGRATION_CHECKLIST.md
docs/MCP_SERVERS.md
docs/QUICKSTART.md
docs/ROUTER_POLICY.md
docs/RUNBOOK.md
docs/SAFETY.md
docs/SEARCH_PROVIDER_APIS.md
docs/SKILLS.md
docs/TASK_OBSERVER.md
docs/TROUBLESHOOTING.md
docs/UPDATING.md
docs/audit/ADAPTIVE_PREFLIGHT_REVIEW_2026-11-19.md
docs/audit/AGENTENHANCEMENTS_E2E_AUDIT_2026-11-15.md
docs/audit/API_MCP_AUTOMATION_AUDIT_2026-11-15.md
docs/audit/AUDIT_REPORT.md
docs/audit/AuditReport1611202601.md
docs/audit/E2E_AUDIT_2026-11.md
docs/audit/LIBRARY_MODEL_CLOSURE_2026-11-15.md
docs/audit/NATIVE_AUTOMATION_AUDIT_2026-11-14.md
docs/audit/NATIVE_HOSTS_E2E_2026-11-16.md
docs/audit/PRODUCTION_READINESS_AUDIT.md
docs/audit/REMEDIATION_CLOSURE_2026-11-15.md
docs/audit/REMEDIATION_REPORT.md
docs/audit/TASK_OBSERVER_INTEGRATION_2026-11-15.md
docs/audit/TEST_RESULTS.md
docs/benchmark/REPORT_2026-11-15.md
docs/benchmark/coldstart-after.json
docs/benchmark/coldstart-baseline.json
docs/benchmark/routing-final.json
docs/superpowers/plans/2026-11-16-complete-agent-enhancements-fix.md
AuditReport/ae-benchmark-report-20261117.md
AuditReport/ae-brave-search-removal-report-20261117.md
AuditReport/ae-comprehensive-benchmark-report-20261117.md
AuditReport/ae-comprehensive-fix-validation-report-20261117.md
AuditReport/ae-final-production-report-20261117.md
AuditReport/ae-search-providers-end-to-end-report-20261117.md
.superpowers/sdd/2026-11-16-complete-agent-enhancements-fix/progress.md
.superpowers/sdd/2026-11-16-complete-agent-enhancements-fix/task-1-report.md
.superpowers/sdd/2026-11-16-complete-agent-enhancements-fix/task-2-report.md
.superpowers/sdd/2026-11-16-complete-agent-enhancements-fix/task-3-report.md
.superpowers/sdd/2026-11-16-complete-agent-enhancements-fix/task-4-report.md
```


Final integration note: main also corrected the XDG runtime lookup in
`mcp-test.sh`, with a failing-before/passing-after interpreter fixture.
The three small current-guide residuals DOC-06/07/08 are closed.

Final scope update: the user approved checkout-local state including venv,
cache and memory. The earlier XDG lookup repair is superseded by canonical
project runtime selection, retaining interpreter-selection regression
coverage. New upstream b6e1c056 reports are reconciled in
[additional audit verification](ae-incoming-audit-reconciliation-20261119.md).
