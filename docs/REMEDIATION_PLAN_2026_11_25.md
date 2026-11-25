# AgentEnhancements — Prioritized Remediation Plan

**Audit Date:** 2026-11-25
**Auditor:** Claude Code
**Session:** 999e17e6-1be1-4b6e-b2dc-9d427b9ccb3e

This plan is executable by another agent. Each item includes: problem, root
cause, files affected, recommended change, dependencies, acceptance criteria,
regression tests, and verification procedure.

---

## Phase 1: Release Blockers (Must Fix Before Production)

### AE-001: Fix Karpathy Skills Dispatch Routing

**Problem:** Karpathy Skills only activates for ML/prototyping tasks
(`prototype|sketch|numpy|torch|first principle`). Upstream principles (Think
Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution) are
for **ALL coding tasks**.

**Root Cause:** `dispatch.sh` line 47 heuristic too narrow; upstream intent not
fully understood during integration.

**Files Affected:**

- `unified-integration/scripts/dispatch.sh` (line 47)

**Recommended Change:**

<!-- markdownlint-disable MD013 -->
```bash
# Current (line 47):
if echo "$lc" | grep -qE '(prototype|sketch|numpy|torch|first principle)'; then echo "karpathy-skills"; return; fi

# Replace with:
if echo "$lc" | grep -qE '(prototype|sketch|numpy|torch|first principle|fix|bug|refactor|review|debug|write code|implement|simplif|clean code|over.?engineer)'; then echo "karpathy-skills"; return; fi
```
<!-- markdownlint-enable MD013 -->

**Dependencies:** None (independent fix)

**Acceptance Criteria:**

- [ ] `bash dispatch.sh "fix a bug in authentication"` → karpathy-skills
- [ ] `bash dispatch.sh "refactor this function"` → karpathy-skills
- [ ] `bash dispatch.sh "review this code for simplicity"` → karpathy-skills
- [ ] `bash dispatch.sh "debug this issue"` → karpathy-skills
- [ ] `bash dispatch.sh "simplify this code"` → karpathy-skills
- [ ] `bash dispatch.sh "prototype ML model"` → karpathy-skills (existing)

**Regression Tests:**

- Run all existing dispatch tests (if any)
- Test negative cases: `bash dispatch.sh "write a poem"` → none (not coding)
- Verify no false positives on non-coding tasks

**Verification Procedure:**

```bash
cd /root/project/AgentEnhancements
bash unified-integration/scripts/dispatch.sh "fix a bug in auth"
bash unified-integration/scripts/dispatch.sh "refactor this function"
bash unified-integration/scripts/dispatch.sh "review code for simplicity"
bash unified-integration/scripts/dispatch.sh "debug issue"
bash unified-integration/scripts/dispatch.sh "simplify code"
bash unified-integration/scripts/dispatch.sh "prototype neural network"
# All should output: Skill match : karpathy-skills
```

---

### AE-002: Update filelock Minimum Version

**Problem:** Runtime dependency test fails: `filelock 3.32.0 < 4.2.1` required
for security fixes.

**Root Cause:** Minimum version check in `test_runtime_dependencies.py` line 55
expects >=4.2.1 but installed version is 3.32.0.

**Files Affected:**

- `unified-integration/tests/test_runtime_dependencies.py` (line 55)
- Runtime dependency manifests (pip requirements, pyproject.toml, etc.)

**Recommended Change:**

1. Update the minimum version check to match actual installed version OR
2. Update vendored/runtime filelock to >=4.2.1

```python
# Option 1: Update test to match reality (if 3.32.0 is acceptable)
# test_runtime_dependencies.py line 55:
# self.assertGreaterEqual(installed, (4, 2, 1))
# Change to:
# self.assertGreaterEqual(installed, (3, 32, 0))

# Option 2 (PREFERRED): Update filelock dependency to >=4.2.1
# Find and update filelock in requirements.txt, pyproject.toml, or vendored deps
```

**Dependencies:** None

**Acceptance Criteria:**

<!-- markdownlint-disable MD013 -->
- [ ] `python3 -c "import filelock; print(filelock.__version__)"` >= 4.2.1
- [ ] `python3 -m pytest unified-integration/tests/test_runtime_dependencies.py::RuntimeDependencyRefreshTests::test_filelock_runtime_includes_published_security_fixes -v` PASSES
<!-- markdownlint-enable MD013 -->

**Regression Tests:**

- Run full integration test suite: `python3 unified-integration/tests/run-tests.py`
- Verify no other version checks break

**Verification Procedure:**

<!-- markdownlint-disable MD013 -->
```bash
cd /root/project/AgentEnhancements
python3 -c "import filelock; print(filelock.__version__)"
python3 -m pytest unified-integration/tests/test_runtime_dependencies.py::RuntimeDependencyRefreshTests::test_filelock_runtime_includes_published_security_fixes -v
python3 unified-integration/tests/run-tests.py 2>&1 | grep -E "(PASS|FAIL|test_filelock)"
```
<!-- markdownlint-enable MD013 -->

---

### AE-003: Fix or Remove Preflight Mode 1

**Problem:** Preflight Mode 1 (host-native selector) configured but no adapter
supplies `ae_native_selection`. Every Mode 1 prompt falls back to Mode 0.

**Root Cause:** Mode 1 specified in CONTRACT 8.5 and implemented in
`adaptive_preflight.py` but no host adapter (Claude Code, Codex) implements the
pre-inference selection surface.

**Files Affected:**

- `unified-integration/scripts/adaptive_preflight.py` (lines 1143-1154, 1228-1231)
- Host adapters (if implementing Option A)
- `unified-integration/config/ui.api.schema.json` (if Option B)

**Recommended Change:** Choose ONE option:

**Option A (Implement):** Add `ae_native_selection` to Claude Code and Codex
host adapters

- Requires hook integration that runs pre-inference
- Complex; may not be feasible for all hosts

**Option B (Remove - RECOMMENDED):** Remove Mode 1 from valid modes

```python
# adaptive_preflight.py line 73-76:
MODE_DISABLED = 0
MODE_NATIVE = 1      # REMOVE
MODE_CUSTOM = 2
VALID_MODES = (MODE_DISABLED, MODE_CUSTOM)  # Remove MODE_NATIVE

# Line 1143-1154: Remove Mode 1 handling block
# Line 1228-1231: Remove Mode 1 status report logic
# Update ui.api.schema.json to only allow 0 or 2
```

**Dependencies:** None (but Option A requires host adapter changes)

**Acceptance Criteria:**

- [ ] Option A: Mode 1 works with claude-code and codex (ae_native_selection
      supplied and validated)
- [ ] Option B: Mode 1 removed from VALID_MODES, config schema, docs; Mode 0 and
      2 only

**Regression Tests:**

- Test Mode 0: `preflight_context` with mode=0 → skill_context fallback
- Test Mode 2: `preflight_context` with mode=2 + valid key → selection or fallback
- Test invalid mode: mode=1 → rejection with diagnosis (Option B) or works
  (Option A)

**Verification Procedure:**

```bash
cd /root/project/AgentEnhancements
# Test current behavior (should show fallback)
python3 -c "
from unified_integration.scripts.adaptive_preflight import preflight_context, load_model_config
config = load_model_config({'preflight': {'mode': 1}})
print('Mode 1 config:', config.mode, config.diagnosis)
"
# After fix: should either work or cleanly reject
```

---

## Phase 2: CI Blockers (Fix Soon)

### AE-004: Fix JSONC Reference File

**Problem:** `tsconfig-strict.json` contains comments (JSONC), fails
`python3 -m json.tool` CI check.

**Root Cause:** Reference file uses JSONC format but CI validates as strict JSON.

**Files Affected:**

- `unified-integration/skills/by-category/general/typescript-expert/references/tsconfig-strict.json`

**Recommended Change:** Remove comments OR rename to `.jsonc` and add CI exception.

<!-- markdownlint-disable MD013 -->
```json
// Option 1: Remove all // comments from file
// Option 2: Rename to tsconfig-strict.jsonc and update CI check to skip .jsonc files
```
<!-- markdownlint-enable MD013 -->

**Dependencies:** None

**Acceptance Criteria:**

- [ ] `python3 -m json.tool` passes on all owned .json files
- [ ] File retains reference value

**Verification Procedure:**

```bash
cd /root/project/AgentEnhancements
python3 -m json.tool unified-integration/skills/by-category/general/typescript-expert/references/tsconfig-strict.json
# Should pass without error
```

---

### AE-005: Fix Jinja2 Template File

**Problem:** `template.py` contains Jinja2 syntax (`{{resource_name}}`), fails
`python3 -m py_compile`.

**Root Cause:** Template file named `.py` but contains Jinja2 template syntax.

**Files Affected:**

- `unified-integration/skills/by-category/general/fastapi-router-py/assets/template.py`

**Recommended Change:** Rename to `.j2` or `.template` extension; exclude from
py_compile check.

<!-- markdownlint-disable MD013 -->
```bash
# Rename file
mv unified-integration/skills/by-category/general/fastapi-router-py/assets/template.py \
   unified-integration/skills/by-category/general/fastapi-router-py/assets/template.j2

# Update CI py_compile check to skip .j2 files (or use find -name '*.py' only)
```
<!-- markdownlint-enable MD013 -->

**Dependencies:** None

**Acceptance Criteria:**

- [ ] `python3 -m py_compile` passes on all owned .py files
- [ ] Template file retains its purpose

**Verification Procedure:**

```bash
cd /root/project/AgentEnhancements
find unified-integration scripts -name '*.py' -print0 | xargs -0 python3 -m py_compile
# Should pass without error
```

---

### AE-006: Enforce Karpathy/Superpowers Priority Rules

**Problem:** Priority rules for overlapping clean-code principles documented but
not enforced.

**Root Cause:** Rules in SKILL.md line 88-89 but no runtime enforcement in dispatch/runtime.

**Files Affected:**

- `unified-integration/scripts/dispatch.sh`
- `unified-integration/scripts/runtime.py`
- `plugin-catalog/code/karpathy-skills/SKILL.md` (documentation)

**Recommended Change:** Add priority logic in dispatch.sh:

```bash
# In classify() function, after all skill matches, apply priority:
# 1. Karpathy (general coding principles) - highest for general coding
# 2. Superpowers (workflow discipline) - for task decomposition/execution
# 3. ECC (config generation) - for agent config tasks
# 4. Ponytail (linting) - for code quality tasks

# Or in runtime.py skill selection: deduplicate overlapping principles
```

**Dependencies:** AE-001 (Karpathy dispatch fix) should be done first

**Acceptance Criteria:**

- [ ] General coding task → Karpathy selected, Superpowers/ECC/Ponytail
      clean-code suppressed
- [ ] Workflow/task decomposition task → Superpowers selected
- [ ] Agent config generation → ECC selected
- [ ] Linting/code quality task → Ponytail selected

**Verification Procedure:**

```bash
cd /root/project/AgentEnhancements
bash unified-integration/scripts/dispatch.sh "fix a bug"          # → karpathy-skills
bash unified-integration/scripts/dispatch.sh "plan this project"  # → bmad-method/gsd
bash unified-integration/scripts/dispatch.sh "generate agent config"  # → ecc
bash unified-integration/scripts/dispatch.sh "lint this code"     # → ponytail
```

---

### AE-007: Document/Enable Preflight Mode 2

**Problem:** Mode 2 requires external API key not configured by default;
untested in CI.

**Root Cause:** Mode 2 designed for custom endpoints but no default
configuration or test setup.

**Files Affected:**

- `docs/CONFIGURATION.md`
- `unified-integration/config/ui.api.example.json`

**Recommended Change:** Add documented example and test with mock endpoint.

```json
// ui.api.example.json - add preflight section:
{
  "preflight": {
    "mode": 2,
    "endpoint": "https://openrouter.ai/api/v1",
    "sdk": "openai",
    "model": "openai/gpt-4o-mini",
    "api_key_ref": "PREFLIGHT_API_KEY"
  },
  "api_keys": {
    "PREFLIGHT_API_KEY": ["sk-..."]
  }
}
```

**Dependencies:** AE-003 (Mode 1 resolution)

**Acceptance Criteria:**

- [ ] Mode 2 documented with working example in CONFIGURATION.md
- [ ] Example ui.api.json with Mode 2 config committed
- [ ] Testable with mock endpoint in CI (optional)

**Verification Procedure:**

```bash
cd /root/project/AgentEnhancements
# Configure ui.api.json with Mode 2 + valid key
# Run prompt through runtime.py
# Verify Mode 2 selection or graceful fallback
```

---

## Phase 3: Medium Priority (Next Sprint)

### AE-008: Audit All Reference Files

**Problem:** Multiple reference files in skills/ use non-standard formats.

**Root Cause:** Reference files copied from upstream without format normalization.

**Files Affected:** Multiple files in `unified-integration/skills/by-category/*/references/`

**Recommended Change:** Full audit; normalize formats or add CI exceptions with
documentation.

**Dependencies:** AE-004, AE-005

**Acceptance Criteria:**

- [ ] All reference files documented with format
- [ ] CI passes with configured exceptions

---

### AE-009: Verify Registry Search Ranking

**Problem:** Karpathy not ranked high for general coding terms in registry.py search.

**Root Cause:** Scoring algorithm may not weight general coding terms for Karpathy.

**Files Affected:** `unified-integration/scripts/registry.py` (scoring functions)

**Recommended Change:** Verify and adjust skill scoring for general coding terms.

**Dependencies:** AE-001

**Acceptance Criteria:**

- [ ] `registry.py map "fix a bug"` includes karpathy-skills in top 5
- [ ] `registry.py map "refactor code"` includes karpathy-skills in top 5

---

### AE-010: Add Karpathy to Curated Native Set

**Problem:** Default native links only task-observer + Superpowers; Karpathy not
natively discoverable.

**Root Cause:** Context-frugal default limits to 2 sources.

**Files Affected:** `unified-integration/scripts/link-skills.sh` (line 49)

**Recommended Change:** Add karpathy-skills to CURATED_SOURCES.

```bash
# link-skills.sh line 49:
CURATED_SOURCES="anthropic-skills replica-skill task-observer karpathy-skills"
```

**Dependencies:** AE-001, AE-006

**Acceptance Criteria:**

- [ ] `link-skills.sh --set curated` includes karpathy-skills
- [ ] Context budget still within limits (~3.5k tokens)

---

## Phase 4: Optional Improvements

### AE-011: Increase ECC Test Timeout

**Problem:** ECC tests ~45min, CI timeout 45min (no margin).

**Files Affected:** `.github/workflows/ci.yml` line 187

**Recommended Change:** Increase timeout to 60min.

```yaml
# .github/workflows/ci.yml
ecc-tests:
  timeout-minutes: 60  # was 45
```

---

### AE-012: Fix Markdownlint in CI

**Problem:** npm registry blocked in sandbox; markdownlint cannot install.

**Files Affected:** `.github/workflows/ci.yml` markdownlint step

**Recommended Change:** Use cached npx or pre-install in CI image.

```yaml
# Option: Use actions/setup-node with cache
- uses: actions/setup-node@v4
  with:
    node-version: "22"
    cache: 'npm'
- run: npm ci --prefer-offline --no-audit  # or use local install
```

---

## Execution Order Summary

| Order | Finding | Phase | Estimated Effort |
| ------- | --------- | ------- | ------------------ |
| 1 | AE-001 | 1 | 30 min |
| 2 | AE-002 | 1 | 30 min |
| 3 | AE-003 | 1 | 1-2 hrs (Option B) / 1 day (Option A) |
| 4 | AE-004 | 2 | 15 min |
| 5 | AE-005 | 2 | 15 min |
| 6 | AE-006 | 2 | 1 hr |
| 7 | AE-007 | 2 | 1 hr |
| 8 | AE-008 | 3 | 2 hrs |
| 9 | AE-009 | 3 | 1 hr |
| 10 | AE-010 | 3 | 15 min |
| 11 | AE-011 | 4 | 5 min |
| 12 | AE-012 | 4 | 30 min |

**Total Estimated Effort:** ~6-8 hours for all fixes

---

## Verification Checklist (Post-Remediation)

After all fixes applied, run:

<!-- markdownlint-disable MD013 -->
```bash
# 1. Full CI suite
cd /root/project/AgentEnhancements
gh workflow run ci.yml --ref master

# 2. Karpathy dispatch fix
bash unified-integration/scripts/dispatch.sh "fix a bug in authentication"
bash unified-integration/scripts/dispatch.sh "refactor this function"
bash unified-integration/scripts/dispatch.sh "review this code for simplicity"
bash unified-integration/scripts/dispatch.sh "debug this issue"
bash unified-integration/scripts/dispatch.sh "simplify this code"
bash unified-integration/scripts/dispatch.sh "prototype ML model"

# 3. Filelock version
python3 -c "import filelock; print(filelock.__version__)"
python3 -m pytest unified-integration/tests/test_runtime_dependencies.py::RuntimeDependencyRefreshTests::test_filelock_runtime_includes_published_security_fixes -v

# 4. Preflight Mode 1 resolution
# Verify Mode 1 either works or cleanly removed

# 5. JSON/Python validation
find unified-integration scripts plugin-catalog -name '*.json' -not -path '*/node_modules/*' | xargs python3 -m json.tool
find unified-integration scripts -name '*.py' | xargs python3 -m py_compile

# 6. Priority rules
bash unified-integration/scripts/dispatch.sh "fix a bug"          # → karpathy-skills
bash unified-integration/scripts/dispatch.sh "plan this project"  # → bmad-method/gsd
bash unified-integration/scripts/dispatch.sh "generate agent config"  # → ecc
bash unified-integration/scripts/dispatch.sh "lint this code"     # → ponytail

# 7. Full test suite
python3 unified-integration/tests/run-tests.py
cd ECC && node tests/run-all.js
cd headroom && cargo test --locked -p headroom-cli
bash unified-integration/scripts/setup-mcp.sh --check

# 8. Registry search
python3 unified-integration/scripts/registry.py map "fix a bug"
python3 unified-integration/scripts/registry.py map "refactor code"

# 9. Curated native links
bash unified-integration/scripts/link-skills.sh --set curated
# Verify karpathy-skills linked
```
<!-- markdownlint-enable MD013 -->

---

## End of Remediation Plan

This plan is specific enough for another agent to execute. Each item has clear
acceptance criteria and verification procedures. Prioritize Phase 1 (release
blockers) first, then Phase 2 (CI blockers), then Phase 3/4.
