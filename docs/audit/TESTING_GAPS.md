# Testing Gaps — Deep Audit

> Verifikasi2026-11-19: sebagian klaim/angka/prioritas laporan ini tidak
> sesuai source dan hasil eksekusi. Baca [rekonsiliasi berbukti](../../AuditReport/ae-incoming-audit-reconciliation-20261119.md)
> sebelum mengeksekusi rekomendasi. Laporan ini adalah data historis,
> bukan instruksi untuk mengubah arsitektur atau meniadakan test yang ada.


**Scope:** Unit, integration, E2E, contract, performance, security testing across all components

---

## 1. Current Test Infrastructure

### Unified Integration Tests (`unified-integration/tests/`)
```
test_registry.py              # Registry search/map/show/list/stats
test_load_skills.py           # SkillsLoader find_skills
test_hooks.py                 # Hook event handling
test_native_automation.py     # native-integration.py install flows
test_native_hosts.py          # Multi-harness config merging
test_api_config.py            # ui.api.json read/validate/redact
test_compress.py              # Compression utilities
test_memory.py                # SQLite memory CRUD + TTL
test_index.py                 # all-skills.json aggregation
test_sync.py                  # Generator/artifact sync
test_dispatch_anthropic.py    # dispatch.sh routing
test_setup_static.py          # setup.sh static analysis
test_ci.py                    # CI pipeline validation
test_hardening.py             # Security hardening checks
test_task_observer.py         # 38 tests: Bundle, Bootstrap, Observation
test_mcp_servers.py           # MCP catalog + network (opt-in)
run-tests.py                  # Test runner (190→228 tests after task-observer)
```

### ECC Tests (`ECC/tests/`)
```
test_provider_tools.py        # Provider tool integration (19KB)
test_session_manager.py       # Session state (135KB)
test_state_store.py           # State persistence (39KB)
test_install_lifecycle.py     # Install flow (152KB)
test_package_manager.py       # PM detection (70KB)
test_context_selection.py     # Context routing (41KB)
test_harness_audit.py         # Harness validation (44KB)
```

### ECC JavaScript Tests (`ECC/`)
```
node tests/run-all.js         # 8,212 pass / 11 fail (pre-existing)
```

### Catalog Validation
```
catalog-validate.py           # Validates catalog.json + plugin manifests
catalog-test.sh               # Basic catalog wiring test
```

---

## 2. Coverage Analysis by Component

### `registry.py` (1,144 lines)
| Function | Tested? | Gap |
|----------|---------|-----|
| `load_skill_entries` | ✅ | — |
| `load_plugin_entries` | ✅ | — |
| `load_mcp_entries` | ✅ | — |
| `load_capability_entries` | ✅ | — |
| `score_skill` | ❌ | **Critical** — core ranking algorithm untested |
| `score_plugin` | ❌ | **Critical** — plugin scoring untested |
| `score_mcp` | ❌ | **Critical** — MCP scoring untested |
| `score_capability` | ❌ | **Critical** — capability scoring untested |
| `token_weights` | ❌ | Intent synonym weighting untested |
| `expand_intent` | ❌ | Synonym expansion untested |
| `rank_entries` | ❌ | Full ranking pipeline untested |
| `cmd_build` | ✅ | Via test_index.py |
| `cmd_search` | ✅ | Via test_registry.py |
| `cmd_map` | ✅ | Via test_registry.py |
| `cmd_show` | ✅ | Via test_registry.py |
| `find_entry` | ❌ | Typed ID resolution untested |
| `paged_search` | ❌ | Preflight internal API untested |
| `paged_list` | ❌ | Preflight internal API untested |

**Registry Test Coverage: ~35%** — CLI commands tested; core algorithms NOT tested

### `adaptive_preflight.py` (1,110 lines)
| Function | Tested? | Gap |
|----------|---------|-----|
| `load_model_config` | ❌ | Mode validation, diagnosis codes untested |
| `deadline_seconds` | ❌ | Env override, bounds untested |
| `Deadline` class | ❌ | Monotonic deadline logic untested |
| `parse_selection` | ❌ | **Critical** — schema validation untested |
| `registry_revision` | ❌ | Content hash untested |
| `_resolve_entry` | ❌ | **Critical** — readiness resolution untested |
| `_resolve_tool_id` | ❌ | Tool ID resolution untested |
| `build_package` | ❌ | **Critical** — package building untested |
| `render_package` | ❌ | Budget clamping, shrinking untested |
| `resolve_api_key` | ❌ | Keyring/env/file priority untested |
| `call_openai_compatible` | ❌ | **Critical** — HTTP client untested |
| `call_anthropic_compatible` | ❌ | **Critical** — HTTP client untested |
| `run_custom_selection` | ❌ | **Critical** — 2-round inference untested |
| `preflight_context` | ❌ | **Critical** — main entry point untested |
| `status_report` | ❌ | Diagnostic output untested |

**Preflight Test Coverage: ~0%** — NO TESTS for the entire adaptive preflight system

### `runtime.py` (247 lines)
| Function | Tested? | Gap |
|----------|---------|-----|
| `redact` | ✅ | Via test_hooks.py |
| `skill_context` | ✅ | Via test_hooks.py |
| `prompt_context` | ❌ | Preflight integration untested |
| `observer_context` | ✅ | Via test_task_observer.py |
| `handle` (SessionStart) | ✅ | Via test_native_automation.py |
| `handle` (UserPromptSubmit) | ❌ | Preflight modes untested |
| `handle` (Pre/PostToolUse) | ✅ | Via test_hooks.py |
| `handle` (Stop) | ❌ | Observer backstop untested |

**Runtime Test Coverage: ~50%** — Basic hooks tested; preflight integration missing

### `memory.py` (197 lines)
| Function | Tested? | Gap |
|----------|---------|-----|
| `AgentMemory.__init__` | ✅ | Via test_memory.py |
| `save` | ✅ | Via test_memory.py |
| `load` | ✅ | Via test_memory.py |
| `list` | ✅ | Via test_memory.py |
| `delete` | ✅ | Via test_memory.py |
| `cleanup_expired` | ❌ | TTL expiry untested |
| Concurrent access | ❌ | No thread-safety tests |
| Corruption recovery | ❌ | No DB corruption tests |

**Memory Test Coverage: ~70%** — CRUD tested; TTL, concurrency, recovery missing

### `api_config.py` (299 lines)
| Function | Tested? | Gap |
|----------|---------|-----|
| `initialize` | ✅ | Via test_api_config.py |
| `read_config` | ✅ | Via test_api_config.py |
| `value` | ✅ | Via test_api_config.py |
| `redact` | ✅ | Via test_api_config.py |
| `server_state` | ✅ | Via test_api_config.py |
| `cloud_available` | ✅ | Via test_api_config.py |
| Search provider round-robin | ❌ | Thread-safety, fallback untested |

**API Config Test Coverage: ~80%** — Core tested; round-robin missing

### `task-observer.py` (38 tests in test_task_observer.py)
| Area | Coverage |
|------|----------|
| Bundle integrity | ✅ |
| Workspace bootstrap | ✅ |
| Observation logging | ✅ |
| Lookup/open entries | ✅ |
| Review/staging | ✅ |
| Promotion/rollback | ✅ |
| Disable/enable | ✅ |
| Security (redaction, traversal) | ✅ |
| Concurrent writers | ✅ |
| **Task Observer Coverage: ~95%** — **Best tested component** |

### `native-integration.py` / `native_hermes.py`
| Area | Tested? | Gap |
|------|---------|-----|
| Hook merging | ✅ | Via test_native_automation.py |
| MCP block merge | ✅ | Via test_native_automation.py |
| Hermes profile install | ❌ | No Hermes binary in CI |
| Config merging | ✅ | Via test_native_hosts.py |
| Instruction merging | ❌ | Marker block logic untested |

### `context_budget.py` (149 lines)
| Function | Tested? | Gap |
|----------|---------|-----|
| `approx_tokens` | ❌ | Tiktoken vs fallback untested |
| `clamp_to_budget` | ❌ | Line-boundary trimming untested |
| `budget_report` | ❌ | Ledger untested |

**Context Budget Coverage: 0%** — Critical for token management, completely untested

### ECC Agents/Skills/Commands
| Component | Tested? |
|-----------|---------|
| Agent invocation | ❌ |
| Skill loading/execution | ❌ |
| Command output | ❌ |
| Workflow execution | ❌ |
| Hook integration | ❌ |

**ECC Test Coverage: ~0% for behavioral components** — Only infrastructure tests exist

---

## 3. Missing Test Categories

### Contract Tests
- ❌ Registry scoring contract (CARD_MIN_SCORE, generic suppression)
- ❌ Preflight mode transitions (0→1→2→0 fallback)
- ❌ MCP visibility state machine
- ❌ Skill loading activation contract
- ❌ Context budget enforcement across channels

### Integration Tests
- ❌ Full hook flow: SessionStart → UserPromptSubmit → PreToolUse → PostToolUse → Stop
- ❌ Preflight + Runtime integration (Mode 0/1/2)
- ❌ Multi-harness install verification (Claude + Codex + OpenCode + Hermes)
- ❌ MCP gateway + registry + api_config integration
- ❌ Task observer + memory + runtime integration

### E2E Tests
- ❌ Real agent session with AE installed
- ❌ Skill discovery → load → execute → observe cycle
- ❌ Preflight Mode 2 with real provider (OpenRouter/Anthropic)
- ❌ Native workflow (`orch-review`) on real PR
- ❌ Multi-agent orchestration (orch-pipeline)

### Performance Tests
- ❌ Cold-start token budget regression (4000 token limit)
- ❌ Preflight latency (2s deadline)
- ❌ Registry search latency (p50/p95)
- ❌ Memory DB performance under load
- ❌ Hook overhead per event

### Security Tests
- ❌ Secret redaction coverage (all patterns)
- ❌ Path traversal attempts (skill/plugin/MCP resolution)
- ❌ Config injection (duplicate keys, oversized)
- ❌ Redirect attacks (Mode 2 HTTP client)
- ❌ Agent tool privilege escalation

### Chaos/Resilience Tests
- ❌ Corrupted config files (ui.api.json, model.json, registry)
- ❌ Missing MCP servers (gateway degradation)
- ❌ Network failures during preflight
- ❌ Concurrent hook invocations
- ❌ Disk full / permission errors

---

## 4. CI/CD Status

### Current
- ❌ **No GitHub Actions workflow visible** in repository
- ❌ No automated test runs on push/PR
- ❌ No linting (ruff, mypy, shellcheck)
- ❌ No type checking (mypy/pyright)
- ❌ No security scanning (gitleaks, pip-audit, npm audit, cargo deny)
- ❌ No performance benchmarks

### Referenced but Missing
- `PRODUCTION_READINESS_AUDIT` mentions `.github/workflows/ci.yml` and `registry-regeneration.yml` — **not found in current tree**
- `ADAPTIVE_PREFLIGHT_REVIEW` references CI workflows — **not found**

---

## 5. Test Quality Issues

### Existing Test Problems
1. **No fixtures/factories** — Tests recreate setup inline
2. **No parameterized tests** — Scenarios hardcoded
3. **No snapshot testing** — Command output not regression-tested
4. **No property-based testing** — Scoring algorithms need hypothesis
5. **Flaky tests** — ECC JS tests: 11/8212 fail (pre-existing, fixture/race/timing)
6. **No test isolation** — Shared SQLite DB, filesystem state
7. **No coverage reporting** — No `coverage.py` / `llvm-cov`

### Test Organization
```
unified-integration/tests/          # 15 test files, 228 tests
ECC/tests/                          # 7 test files, ~500KB total
ECC/ (JS tests)                     # 8,212 tests (mostly CLI integration)
plugin-catalog/                     # 0 test files
agentic-awesome-skills/             # 0 test files
Superpowers/                        # 0 test files
task-observer/                      # 38 tests (in unified-integration/tests/)
```

---

## 6. Recommendations

### P0 — Foundation (Do First)
1. **Add GitHub Actions CI** — Lint → Typecheck → Test → Security scan
2. **Test registry scoring** — Property-based tests for `score_skill`, `score_plugin`, `score_mcp`
3. **Test adaptive preflight** — Unit tests for every function; integration test for mode transitions
4. **Test context_budget** — Token counting, clamping, budget report
5. **Fix test isolation** — Temp dirs, in-memory SQLite, mocked filesystem

### P1 — Coverage
6. **Contract tests** — Mode transitions, MCP visibility, skill activation
7. **Integration tests** — Full hook flow, multi-harness install
8. **E2E smoke tests** — Real agent session (Claude Code in container)
9. **Performance benchmarks** — Cold-start, preflight latency, registry search
10. **Security tests** — Redaction, traversal, injection, redirect

### P2 — Quality
11. **Snapshot testing** — Command outputs, registry JSON, hook configs
12. **Property-based testing** — Hypothesis for scoring, token budget
13. **Mutation testing** — Verify test quality (mutmut)
14. **Coverage reporting** — Target 80%+ for core modules (registry, preflight, runtime, memory)
15. **Flaky test quarantine** — Fix or isolate ECC JS test failures

### P3 — Platform
16. **Test matrix** — Python 3.11/3.12/3.13, Node 18/20/22, OS Linux/macOS
17. **Contract testing** — Pact/Schemathesis for MCP gateway API
18. **Chaos testing** — Litmus/Chaos Mesh for resilience
19. **Visual regression** — For dashboard/UI components
20. **Test dashboard** — Historical trends, flaky detection, coverage trends
