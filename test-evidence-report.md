# Test Evidence Report - AgentEnhancements

**Generated:** 2026-11-21 03:28:07 SEAST  
**Branch:** master  
**SHA:** fc893cf47f05cddc74a28b77f20b3ae2379628cb  
**OS:** MINGW64_NT-10.0-19044 (Windows 10 Enterprise LTSC 2021)  
**Python:** 3.12.10  
**Node:** v24.22.1  
**npm:** 11.19.1  
**Rust:** Not installed  

---

## Baseline Reproducible Information

### Git Status
- **Branch:** master (up to date with origin/master)
- **Modified files:** 14 files in unified-integration/, skills/
- **Untracked files:** AuditReport/, C/, falsification-memo.md, link_superpowers.sh, process_all_sources.py, process_superpowers.py, reconnaissance_report.json, setup.log

### Config State (no secrets)
- AgentEnhancements unified-integration config present
- ECC config present
- ui.api.json present

---

## 1. Integration Tests (unified-integration/tests/run-tests.py)

### Summary
- **Total tests collected:** ~500+
- **Passed:** ~180
- **Failed:** ~100+
- **Errors:** ~50+
- **Skipped:** ~10+

### Key Failure Categories

#### A. Missing `mcp` Module (Critical - 30+ tests)
**Root Cause:** The `mcp` Python package is not installed in the environment.
**Affected Tests:**
- test_mcp_servers (all MCP server tests)
- test_adaptive_preflight (PackageResolutionTests, Mode2EndToEndTests)
- test_native_hosts (DoctorTests)
- test_api_config (ConfigurationTests, GatewayTests)
- test_security_regressions (CredentialRedirectTests, FfmpegSecurityTests, GatewayHealthSecurityTests)
- test_audit_remediation (TaskRouterHardeningTests)
- test_credential_pool (GatewayStdioTests, AdapterTests)

#### B. Windows-Specific `os.fchmod` Errors (15+ tests)
**Root Cause:** `os.fchmod` is not available on Windows (MSYS2/Git Bash).
**Affected Files:**
- unified-integration/scripts/memory.py (line 41)
- unified-integration/scripts/api_config.py (line 395)
**Affected Tests:**
- test_memory (all AgentMemoryTests)
- test_adaptive_preflight (Mode0ParityTests, Mode2EndToEndTests)
- test_security_regressions (MemorySecurityTests, PreflightSecurityTests, CredentialRedactionTests)
- test_credential_pool (MigrationTests)
- test_setup_safety (SetupSafetyTests)

#### C. Unicode Decode Errors (3 tests)
**Root Cause:** CP1252 encoding issue reading .cursorrules file.
**Affected Tests:**
- test_modular_tree.TestCursorrulesCoverage.test_every_slug_routed
- test_modular_tree.TestIntegrationReadmeCoverage.test_declares_accurate_totals
- test_modular_tree.TestIntegrationReadmeCoverage.test_every_slug_documented

#### D. Test Logic Failures (40+ tests)
**Notable Failures:**
- test_adaptive_preflight.Mode0ParityTests: Legacy card rendering issues
- test_adaptive_preflight.Mode2EndToEndTests: HTTP error fallback, key missing, abstain rendering
- test_adaptive_preflight.AnthropicProtocolTests: Hook skipped (AttributeError)
- test_native_automation: Runtime tests (stdin events, credential redaction, prompt routing)
- test_native_hosts: Checkout move, codex gateway, opencode v1 refusal
- test_security_regressions: Audit log privacy, consent redaction, observer security
- test_credential_pool: Key rotation, failover, migration, schema validation

---

## 2. ECC Tests (ECC/tests/run-all.js)

### Summary
- **Partial run** (timeout at 60s)
- **Passed:** 13 tests (agent-instruction-safety, agent-security-hardening-skill, agent-yaml-surface)
- **Failed:** 2 tests (agent-payment-x402-doc, agent-payment-x402-seller-guard) - Missing `typescript` module
- **Remaining:** Multiple test suites not reached due to timeout

### Key Issues
- Missing `typescript` npm package
- Test suite execution time exceeds reasonable limits

---

## 3. Specific Test Modules

### test_adaptive_preflight.py (73 tests per ADAPTIVE_PREFLIGHT.md)
- **Passed:** 49
- **Failed:** 28
- **Skipped:** 1 (live model test requires AE_PREFLIGHT_LIVE=1)
- **Errors:** 2 (sqlite3 table missing, temp file cleanup)

### test_native_hosts.py + test_native_automation.py
- **Passed:** 18
- **Failed:** 19
- **Skipped:** 1 (python aliases skipped - requires integration venv)
- **Subtests passed:** 10

### test_security_regressions.py + test_credential_pool.py
- **Passed:** 27
- **Failed:** 35
- **Skipped:** 1 (live search requires AE_SEARCH_LIVE=1)
- **Errors:** 7
- **Subtests passed:** 10

### smoke-native-clis.py
- **Status:** ERROR - FileNotFoundError on Windows path (`\\tmp\\agentenhancements-fixture-codex.log`)

### smoke-adaptive-preflight.py --mode 0 / --mode 2
- **Status:** ERROR - Path resolution bug (AssertionError on skill path)

### test-opencode-plugin.mjs
- **Status:** FAILED - AssertionError: Expected "local skill candidates" pattern, got empty output

---

## 4. Scenario E2E Traceability (Per Master Prompt §7)

| Scenario | Status | Evidence |
|----------|--------|----------|
| 1. Programming task without AE mention | NOT TESTED | No automated test covers this |
| 2. Database migration/performance | NOT TESTED | No domain skill test executed |
| 3. Document/image/audio/video fixture | NOT TESTED | Fixture tests blocked by missing mcp |
| 4. Search multi-provider | NOT TESTED | Requires AE_SEARCH_LIVE=1 and keys |
| 5. Task without capability | NOT TESTED | No abstention test executed |
| 6. Multi-turn task A then B | NOT TESTED | No multi-turn test executed |
| 7. Mode 0 parity | FAILED | Multiple Mode0ParityTests failed |
| 8. Mode 1 Claude/Codex | PARTIAL | Mode1Tests mostly pass (fallback to mode 0) |
| 9. Mode 2 OpenCode | FAILED | Mode2EndToEndTests mostly failed |
| 10. Fault injection | PARTIAL | Some HTTP error tests run but fail |
| 11. Install lifecycle | PARTIAL | Some native host tests cover but fail |
| 12. Threat tests | PARTIAL | Security regression tests run but fail |
| 13. Mid-task emerging need (P0/P1) | NOT TESTED | No autonomous capability discovery test |
| 14. Lifecycle across tool results | NOT TESTED | No error-driven re-evaluation test |
| 15. Black-box novice UX | NOT TESTED | No clean install UX test |
| 16. Paired outcome benchmark | NOT TESTED | No AE off vs Mode 0 vs Mode 2 comparison |

---

## 5. Benchmark & Quality Gates

| Gate | Status | Notes |
|------|--------|-------|
| Discovery semantic benchmark | NOT RUN | discovery_benchmark.py fails (hook skipped: AttributeError) |
| Top-1/Top-3 precision | NOT MEASURED | No benchmark executed |
| Acceptance oracle defined | UNKNOWN | Not verified |
| E2E latency p50/p95/p99 | NOT MEASURED | No valid sample sizes |
| Cold-start context tokens | NOT MEASURED | Not measured |
| 100% tool delivery accuracy | FAILED | Multiple tool delivery tests fail |
| Exact-schema safety | PARTIAL | Some schema tests pass |
| Credential gating | PARTIAL | Some credential tests fail |
| No secret leakage | PARTIAL | Some redaction tests fail |
| CI clean at final commit | FAILED | Multiple test failures |

---

## 6. Root Cause Analysis (Systematic Debugging)

### Primary Root Causes

1. **Missing `mcp` Python Package** (Critical)
   - **Impact:** 30+ tests cannot import MCP server modules
   - **Fix:** `pip install mcp` or add to requirements.txt

2. **Windows `os.fchmod` Incompatibility** (Critical)
   - **Impact:** 15+ tests fail on database initialization
   - **Fix:** Use `os.chmod` after file close, or platform-specific handling

3. **Unicode/Encoding Issues** (Medium)
   - **Impact:** 3 tests fail reading .cursorrules
   - **Fix:** Specify encoding='utf-8' when reading files

4. **Path Resolution Bugs** (Medium)
   - **Impact:** smoke-adaptive-preflight, smoke-native-clis
   - **Fix:** Fix path resolution logic for Windows

5. **Missing `typescript` npm Package** (Medium)
   - **Impact:** 2 ECC test suites fail
   - **Fix:** `npm install typescript`

6. **Hook "AttributeError" Skip** (Critical)
   - **Impact:** discovery_benchmark, adaptive preflight anthropic tests
   - **Fix:** Investigate hook initialization error

---

## 7. Recommendations

### Immediate (Blocking)
1. Install `mcp` Python package: `pip install mcp`
2. Fix `os.fchmod` in memory.py and api_config.py for Windows compatibility
3. Install `typescript` npm package in ECC

### Short-term
1. Fix encoding specification for .cursorrules file reading
2. Fix path resolution in smoke test scripts
3. Investigate and fix "hook skipped: AttributeError" issue
4. Add Windows CI runner to catch platform-specific issues

### Medium-term
1. Implement Scenario E2E tests (1-16 from master prompt)
2. Add discovery semantic benchmark execution
3. Implement paired outcome benchmark (AE off vs Mode 0 vs Mode 2)
4. Add test result aggregation and reporting to CI

---

## 8. Redacted Evidence Samples

### Sample Error: Missing mcp Module
```
ModuleNotFoundError: No module named 'mcp'
  File ".../unified-integration/mcp-servers/gateway.py", line 25
    from mcp import ClientSession, StdioServerParameters, types
```

### Sample Error: os.fchmod on Windows
```
AttributeError: module 'os' has no attribute 'fchmod'. Did you mean: 'chmod'?
  File ".../unified-integration/scripts/memory.py", line 41
    os.fchmod(descriptor, 0o600)
```

### Sample Error: Unicode Decode
```
UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position 8528
  File ".../unified-integration/tests/test_modular_tree.py", line 249
    rules = CURSORRULES.read_text()
```

### Sample Error: Hook Skipped
```
[AgentEnhancements] hook skipped: AttributeError
```

---

## Summary

**Overall Status: CRITICAL FAILURES**

The test suite has **systemic infrastructure issues** preventing most tests from executing properly:
- 30+ tests blocked by missing `mcp` package
- 15+ tests blocked by Windows-incompatible `os.fchmod`
- Multiple path/encoding issues on Windows
- Core adaptive preflight Mode 2 tests failing
- Security regression tests failing due to infrastructure

**Minimum viable test execution requires:**
1. `pip install mcp`
2. Windows-compatible file permission handling
3. `npm install typescript` in ECC
4. Encoding fixes for file reading

Once infrastructure is fixed, re-run full test suite to establish true baseline.