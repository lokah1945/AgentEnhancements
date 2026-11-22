# Feature Reconciliation Matrix — ASUS vs DELL vs Windows Target

**Tanggal:** 2026-11-22  
**Basis:** Analisis kode, CONTRACT, README, CI, dan test dari kedua branch  
**Prinsip:** Retain ASUS vendor tree & CONTRACT; Port DELL modern Python architecture & cross-platform improvements; Adapt both ke single source of truth.

---

## Legend Status Keputusan

| Kode | Arti |
|------|------|
| **RETAIN-ASUS** | Pertahankan implementasi ASUS sebagai canonical |
| **PORT-DELL** | Port implementasi DELL ke arsitektur ASUS (replace) |
| **ADAPT-BOTH** | Gabungkan keduanya, buat implementasi unified yang lebih baik |
| **DEPRECATE** | Hapus/abaikan dengan alasan |
| **NEW-WINDOWS** | Implementasi baru khusus Windows target |

---

## 1. Setup & Installation

| Komponen | ASUS (SHA: df94c5c) | DELL (SHA: 5e6d25f) | Keputusan Windows | Alasan & Evidence |
|----------|---------------------|---------------------|-------------------|-------------------|
| **Installer Utama** | `setup.sh` (Bash, 500+ baris, single source of truth per CONTRACT §2.1) | `setup.py` (Python, 300+ baris, cross-platform native) | **ADAPT-BOTH** | ASUS CONTRACT wajib `setup.sh` sebagai canonical. DELL `setup.py` superior untuk Windows native (pathlib, no Bash dependency). **Solusi:** `setup.sh` tetap entrypoint Linux; `setup.ps1` tipis untuk Windows yang memanggil core Python (`setup.py` atau module baru `installer.py`). Core logic di Python shared module. |
| **Auto-detect Host** | Bash `command -v` checks di `detect_agents()` | Python `Path.home()` checks di `_detect_agents()` | **PORT-DELL** | DELL implementation lebih robust, cross-platform, testable. Port ke `installer.py` shared module. |
| **Dry-run Support** | Tidak eksplisit | Ya (`dry_run: bool` parameter di `run()`) | **PORT-DELL** | Critical untuk safe installation. Tambahkan ke shared installer. |
| **Idempotency** | Marker-guarded, merge semantics | Non-destructive config merges, marker-guarded | **RETAIN-ASUS** | ASUS approach sudah mature & tested di CI. |
| **Uninstall/Repair/Upgrade** | Tidak ada eksplisit | Tidak ada eksplisit | **NEW-WINDOWS** | Gap di keduanya. Implementasikan di shared installer: `install`, `uninstall`, `repair`, `upgrade`, `dry-run`. |
| **Saved Host Selection** | `native-integration.py --print-selection` → `detected-agents.sh` | Tidak ada | **RETAIN-ASUS** | ASUS mechanism works. Port ke Python shared. |
| **Isolated HOME/Config** | CI uses isolated `$HOME` | Tidak eksplisit di setup | **RETAIN-ASUS** | ASUS pattern sudah terbukti di CI. |

---

## 2. Registry & Capability Discovery

| Komponen | ASUS | DELL | Keputusan Windows | Alasan & Evidence |
|----------|------|------|-------------------|-------------------|
| **Registry Structure** | `registry.py` monolitik (search, map, build, stats, list, show) | `SkillRegistry` class dengan `SkillEntry`, `PluginEntry`, `RankedCapability`, `CapabilityComposition` | **PORT-DELL** | DELL arsitektur jauh superior: dataclasses, type hints, enums (`ReadinessLevel`, `CapabilityRole`), evidence-aware ranking, framework tags, capability composition. ASUS registry functional tapi kurang structured. |
| **Skill Index** | `all-skills.json` (generated dari vendor tree, 3.378 skills) | `all-skills.json` (generated dari `skills/` modular tree, 42 skills) + `plugin-catalog/catalog.json` (40 plugins) | **ADAPT-BOTH** | ASUS vendor tree = source of truth untuk skills (3.378). DELL modular `skills/` tree = curated subset (42) + external catalog. **Windows:** Pertahankan vendor tree ASUS sebagai canonical source; generate modular `skills/` tree dari vendor untuk discovery; gunakan DELL `SkillEntry` model. |
| **Plugin Catalog** | Tidak terpisah (termasuk di registry) | `plugin-catalog/catalog.json` + `mcp-servers.json` terpisah | **PORT-DELL** | DELL separation of concerns lebih bersih. Adopsi struktur catalog DELL. |
| **MCP Registry** | Embedded di `registry.py` + `mcp-servers/mcp.json.example` | `plugin-catalog/mcp-servers.json` + `gateway.py` | **PORT-DELL** | DELL MCP catalog terstruktur + gateway implementation. |
| **Search/Map Algorithm** | Keyword scoring + intent synonyms + format aliases + stop words | Keyword + semantic + readiness + compatibility + budget scoring + framework detection | **PORT-DELL** | DELL multi-factor scoring jauh lebih baik untuk relevance. Port algorithm, pertahankan ASUS synonym/alias data. |
| **Readiness Levels** | Tidak ada (binary: installed/not) | `ReadinessLevel` enum: READY, GUIDE_ONLY, NOT_INSTALLED, MISSING_CREDENTIALS, UNAVAILABLE | **PORT-DELL** | Critical untuk honest capability exposure. No-key capabilities harus `MISSING_CREDENTIALS`/`UNAVAILABLE`, tidak `READY`. |
| **Capability Composition** | Tidak ada (flat list) | `CapabilityComposition`: primary, supporting, optional, alternative, conflicts | **PORT-DELL** | DELL composition model enables better agent decision-making. |
| **Framework Tags** | Tidak ada | `framework_tags` per skill + `FRAMEWORK_PATTERNS` detection | **PORT-DELL** | Valuable untuk conflict detection (django vs flask) dan relevance. |

---

## 3. Adaptive Preflight (Mode 0/1/2)

| Komponen | ASUS | DELL | Keputusan Windows | Alasan & Evidence |
|----------|------|------|-------------------|-------------------|
| **Mode 0 (Legacy)** | `skill_context()` di `runtime.py` — heuristic cards, bounded | `PreflightMode.LEGACY` — keyword matching, bounded | **RETAIN-ASUS** | ASUS implementation sudah mature, integrated dengan `context_budget.clamp_to_budget`, tested di CI. |
| **Mode 1 (Native)** | Interface ada (`ae_native_selection` event), tapi **unsupported** per README | `PreflightMode.NATIVE_AUTO` — host-native selection via adapter | **ADAPT-BOTH** | Kedua branch agree Mode 1 **belum production-ready** (host APIs tidak expose selection surface). Windows: Pertahankan interface, implementasi honest fallback ke Mode 0, jangan klaim production ready. |
| **Mode 2 (Custom)** | `adaptive_preflight.py` — full implementation dengan SDK (openai/anthropic), deadline, fallback | `AdaptivePreflight` class — similar features, config dari `ui.api.json` | **PORT-DELL** | DELL implementation lebih clean (dataclasses, enums, structured result `PreflightResult`). Port ke ASUS `adaptive_preflight.py` structure. |
| **Config Source** | `ui.api.json` preflight section | `ui.api.json` preflight section + env overrides | **RETAIN-ASUS** | ASUS config contract sudah established. DELL env overrides useful — port as additive. |
| **Deadline/Timeout** | `AE_PREFLIGHT_DEADLINE_MS` (default 2s), max 2 inference rounds | `deadline_ms` config (default 2000), `max_rounds` (default 2) | **RETAIN-ASUS** | Same values. ASUS env var naming consistent. |
| **Fallback Behavior** | Selalu fallback ke Mode 0 (`skill_context`) | `fallback_on_error: bool` config | **RETAIN-ASUS** | ASUS fallback deterministic & non-blocking. DELL config flag useful — port. |
| **Conflict Detection** | Tidak ada | `CONFLICT_GROUPS` (django/flask/fastapi, react/vue/angular, dll.) | **PORT-DELL** | Valuable untuk preventing conflicting capability selection. |
| **Abstention Logic** | Tidak eksplisit | `abstained: bool`, `abstain_reason: str` | **PORT-DELL** | Honest signaling ketika native agent cukup. |

---

## 4. Memory System

| Komponen | ASUS | DELL | Keputusan Windows | Alasan & Evidence |
|----------|------|------|-------------------|-------------------|
| **Storage** | SQLite (`memory.db`), single table `memories` | SQLite (`memory.db`), single table `memories` dengan more columns | **PORT-DELL** | DELL schema lebih lengkap: `tags`, `session_id`, `agent_type`, multiple indexes. |
| **Memory Types** | Implicit via `memory_type` column (session_context default) | Explicit `TTL_POLICIES`: session_context (7d), persistent (∞), user_preference (1y), skill_usage (30d), task_observer (14d) | **PORT-DELL** | DELL TTL policies superior, explicit, documented. |
| **Thread Safety** | Tidak ada (single connection per op) | `threading.RLock` + connection pool pattern | **PORT-DELL** | Required untuk concurrent hook execution. |
| **Parameterized Queries** | Ya (CONTRACT R101) | Ya (context manager) | **RETAIN-ASUS** | Both compliant. |
| **WAL Mode** | Ya (explicit `PRAGMA journal_mode=WAL`) | Ya (explicit) | **RETAIN-ASUS** | Both good. |
| **File Permissions** | `os.chmod(0o600)` + `O_NOFOLLOW` anti-symlink | Tidak eksplisit | **RETAIN-ASUS** | ASUS security hardening important untuk Windows. Port ke DELL implementation. |
| **API** | `save(key, value, memory_type, metadata, ttl_days)`, `load(key, memory_type)`, `list(memory_type, limit)` | `save(key, value, memory_type, session_id, agent_type, tags, ttl_override)`, `load(key, memory_type, session_id, agent_type)`, `recall_session(session_id, max_age_days)`, `stats()` | **PORT-DELL** | DELL API lebih powerful. Port, pertahankan ASUS security hardening. |

---

## 5. Context Compression

| Komponen | ASUS | DELL | Keputusan Windows | Alasan & Evidence |
|----------|------|------|-------------------|-------------------|
| **Implementation** | `compress.py` (Python fallback) + `headroom` (Rust binary, optional) | `context_compression.py` — `ContextCompressor` dengan `CompressionMode` enum (PYTHON, HEADROOM, AUTO) | **PORT-DELL** | DELL unified interface lebih clean. ASUS headroom integration sudah tested — port logic. |
| **Config** | Hardcoded di `context_budget.py` | `compression.yaml` (mode, budget, trigger, headroom_binary, max_input_chars, preserve_recent, strip_thinking) | **PORT-DELL** | External config file superior. |
| **Budget Management** | `context_budget.py` — `MAX_MEMORY`, `MAX_SKILL_CARDS`, `MAX_OBSERVER_AMBIENT`, `clamp_to_budget()` | Integrated di `ContextCompressor` + `HookRuntime._maybe_compress()` | **ADAPT-BOTH** | ASUS `context_budget.py` constants useful untuk clamping. DELL compressor integration better. Merge: constants di shared config, compressor di DELL style. |

---

## 6. Native Integration & Hooks

| Komponen | ASUS | DELL | Keputusan Windows | Alasan & Evidence |
|----------|------|------|-------------------|-------------------|
| **Supported Agents** | 4 native: Claude Code, Codex, OpenCode, Hermes<br>5 reference: Cursor, Gemini, Copilot, Windsurf, Kiro | 9 full: Claude Code, Codex, OpenCode, Hermes, Cursor, Gemini, Copilot, Windsurf, Kiro | **PORT-DELL** | DELL supports more agents natively. Windows target butuh parity. |
| **Hook Installation** | `merge_hooks()` — merge into existing `settings.json`/`hooks.json`, preserve user hooks | `AgentConfig.hooks` — generates full hook config per agent | **ADAPT-BOTH** | ASUS merge approach **safer** (preserves user config). DELL generation approach **simpler** but risky. **Windows:** Use ASUS merge strategy dengan DELL hook definitions. |
| **MCP Config** | `merge_servers()` — refresh managed servers, preserve user servers | `AgentConfig.mcp_config` — gateway/native per agent | **ADAPT-BOTH** | ASUS merge preserves user MCP. DELL gateway pattern good. Windows: ASUS merge + DELL gateway template. |
| **Hook Events** | SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop | Same 5 + Hermes variants (pre_llm_call, post_llm_call, post_tool_call) | **RETAIN-ASUS** | Standard Claude Code/Codex/OpenCode events. Hermes variants port jika needed. |
| **Hook Command** | `env + runtime_python + runtime.py <agent>` (single entrypoint) | Per-event commands ke `runtime.py <event>` | **RETAIN-ASUS** | Single entrypoint simpler, less config drift. DELL per-event allows different timeouts — port timeout config. |
| **Runtime Python Resolution** | `runtime_python()` — checks venv, sys.prefix, sys.executable | `sys.executable` | **RETAIN-ASUS** | ASUS resolution lebih robust untuk virtual environments. |
| **Settings Preservation** | Preserves `provider choices, credentials, tool approvals, user hooks, user MCP` | Generates fresh configs | **RETAIN-ASUS** | Critical untuk user trust. ASUS approach proven. |

---

## 7. MCP Gateway

| Komponen | ASUS | DELL | Keputusan Windows | Alasan & Evidence |
|----------|------|------|-------------------|-------------------|
| **Gateway Implementation** | `mcp-servers/gateway.py` (referenced via `mcp_block()`) | `gateway.py` — FastMCP pattern, health tool mandatory | **PORT-DELL** | DELL FastMCP implementation lebih modern, testable. ASUS gateway ada tapi less structured. |
| **Built-in Servers** | 11 built, 30 to-install, 10 bundled Python backends | 5 built Python, 2 available npm, 8 planned | **RETAIN-ASUS** | ASUS memiliki lebih banyak built servers. Inventory needed. |
| **Permission Boundaries** | Via gateway env gating | Explicit di `gateway.py` | **PORT-DELL** | DELL explicit boundaries better. |
| **Health Checks** | `setup-mcp.sh --check` | `health` tool mandatory per MCP standard | **PORT-DELL** | Standard compliance. |
| **Stdio Framing** | Via gateway | Via gateway | **RETAIN-ASUS** | Both use gateway pattern. |

---

## 8. Task Observer & Correction Loop

| Komponen | ASUS | DELL | Keputusan Windows | Alasan & Evidence |
|----------|------|------|-------------------|-------------------|
| **Task Observer** | `task-observer.py` — workspace_root, bootstrap_context, log command | `task_observer.py` — similar, integrated dengan `HookRuntime` | **RETAIN-ASUS** | ASUS implementation mature, vendored skill (CC-BY-4.0). DELL integration good — port integration pattern. |
| **Correction Loop** | Tidak ada eksplisit | `correction_loop.py` — structured correction/review | **PORT-DELL** | Valuable untuk quality gates. |
| **Review Coordinator** | Tidak ada | `review_coordinator.py` — orchestration | **PORT-DELL** | Complements correction loop. |
| **Stage Detector** | Tidak ada | `stage_detector.py` — detects workflow stages | **PORT-DELL** | Useful untuk context-aware behavior. |
| **Effectiveness Tracker** | Tidak ada | `effectiveness_tracker.py` — metrics | **PORT-DELL** | Telemetry untuk improvement. |

---

## 9. Configuration & Secrets

| Komponen | ASUS | DELL | Keputusan Windows | Alasan & Evidence |
|----------|------|------|-------------------|-------------------|
| **Config File** | `ui.api.json` (private, schema v2) | `ui.api.json` + `ui.api.example.json` + `ui.api.schema.json` | **ADAPT-BOTH** | ASUS `ui.api.json` canonical. DELL example + schema valuable untuk validation & documentation. |
| **Multiple API Keys per Provider** | `api_config.py` — rotation order, first usable | Tidak eksplisit | **RETAIN-ASUS** | ASUS rotation logic implemented. |
| **Hot Reload** | Tidak eksplisit | Tidak eksplisit | **NEW-WINDOWS** | Gap di keduanya. Implementasikan file watcher untuk config changes. |
| **No-Key = Disabled** | Implicit via `redact_configured` | Explicit `ReadinessLevel.MISSING_CREDENTIALS` | **PORT-DELL** | DELL explicit readiness level better untuk UI/honest exposure. |
| **Credential Passing** | Env vars via `environment()` → gateway env | Env vars, never CLI args | **RETAIN-ASUS** | Both secure. ASUS centralized `environment()` function good. |
| **Secret Redaction** | `redact()` di `runtime.py` & `api_config.py` | Tidak eksplisit di memory/registry | **RETAIN-ASUS** | ASUS redaction comprehensive. Port ke DELL modules. |

---

## 10. Cross-Platform / Windows Correctness

| Aspek | ASUS | DELL | Keputusan Windows | Alasan & Evidence |
|-------|------|------|-------------------|-------------------|
| **Path Handling** | Bash `$HOME`, `~/.claude`, mixed `pathlib` di Python | `pathlib.Path` consistently, `Path.home()` | **PORT-DELL** | DELL consistent pathlib usage. ASUS Bash paths problematic untuk Windows native. |
| **Drive/UNC Paths** | Tidak handled | Tidak handled | **NEW-WINDOWS** | Gap. Implementasikan `project_paths.py` enhancements untuk drive-relative, UNC, long paths. |
| **Case Sensitivity** | Bash assumes case-sensitive | Python assumes case-insensitive (Windows default) | **NEW-WINDOWS** | Implementasikan case-fold collision detection di registry/skill loading. |
| **CRLF/LF** | Bash scripts LF, Python LF | Python LF, no Bash | **RETAIN-ASUS** | Keep LF untuk all scripts. `.gitattributes` untuk enforcement. |
| **Encoding** | UTF-8 implicit | UTF-8 explicit di file ops | **PORT-DELL** | Explicit encoding safer. |
| **Long Paths** | Tidak handled | Tidak handled | **NEW-WINDOWS** | Enable long path support via manifest/registry. |
| **PATHEXT / shutil.which** | Bash `command -v` | `shutil.which` | **PORT-DELL** | Python `shutil.which` respects PATHEXT on Windows. |
| **Python Launcher** | `python3` hardcoded di Bash | `sys.executable` / `python` | **PORT-DELL** | `sys.executable` correct untuk venv. |
| **Subprocess Shell Injection** | `shlex.join` di `native-integration.py` | f-string command construction | **RETAIN-ASUS** | ASUS `shlex.join` safer. Port ke DELL hook commands. |
| **Symlink/Junction** | `ln -s` di Bash scripts | Tidak used | **RETAIN-ASUS** | ASUS uses symlinks untuk skill linking. Windows needs junction fallback (may need admin). Document limitation. |
| **Git Bash vs PowerShell** | Assumes Git Bash available | Tests on both (CI matrix) | **ADAPT-BOTH** | Windows target: primary PowerShell, optional Git Bash. Setup scripts must work di both. |

---

## 11. Testing & CI

| Komponen | ASUS | DELL | Keputusan Windows | Alasan & Evidence |
|----------|------|------|-------------------|-------------------|
| **Test Suite** | `unified-integration/tests/run-tests.py` (integration tests), `discovery_benchmark.py` | `unified-integration/tests/test_*.py` (17 files, 236 tests claimed) | **ADAPT-BOTH** | ASUS integration tests valuable untuk E2E. DELL unit tests comprehensive. Merge: run both suites. |
| **CI Platform** | Ubuntu only (7 jobs) | Ubuntu + Windows matrix (8 jobs) | **PORT-DELL** | Cross-platform CI mandatory untuk Windows target. |
| **Shell Commands in CI** | Bash commands (works on Ubuntu) | Some Unix shell commands di `windows-latest` (problematic) | **NEW-WINDOWS** | Fix DELL CI: use PowerShell untuk Windows jobs, explicit shell specification. |
| **Static Checks** | bash -n, py_compile, JSON validity, filename policy, commit policy | py_compile, JSON/YAML validity, placeholder check, secret scan | **ADAPT-BOTH** | Combine: bash -n untuk .sh, py_compile, JSON/YAML, secret scan, placeholder check, filename policy. |
| **Security Scan** | pip-audit, cargo-audit, npm audit | Secret scan, hardcoded cred check, .gitignore validation | **ADAPT-BOTH** | Combine all. |
| **Smoke Tests** | Discovery benchmark freeze | Registry map, memory, compression, gateway, preflight | **ADAPT-BOTH** | Combine. |

---

## 12. Documentation

| Dokumen | ASUS | DELL | Keputusan Windows | Alasan |
|---------|------|------|-------------------|--------|
| **README** | Comprehensive, badges, counts | Comprehensive, quick start, agent matrix | **ADAPT-BOTH** | Merge: ASUS counts/vendor info + DELL quick start/activation matrix. |
| **CONTRACT** | Binding, detailed rules (R001-R304) | Contribution standards, skill/MCP specs | **RETAIN-ASUS** | ASUS CONTRACT binding untuk development. DELL standards port sebagai appendix. |
| **Architecture Docs** | `docs/ARCHITECTURE.md` (referenced), `ADAPTIVE_PREFLIGHT.md` | `docs/audit/*.md`, `MCP_INTEGRATION_CHECKLIST.md` | **ADAPT-BOTH** | Consolidate ke `docs/windows-consolidation/` + update root docs. |
| **Audit Reports** | `AuditReport/*.md` (10+ reports) | `docs/audit/*.md` (4 reports) + summary reports | **RETAIN-ASUS** | ASUS audit trail extensive. Archive DELL reports di `docs/windows-consolidation/`. |

---

## 13. Vendor Tree & Skills Inventory

| Aspek | ASUS | DELL | Keputusan Windows |
|-------|------|------|-------------------|
| **Vendored Projects** | 11 projects (ECC, anthropic-skills, agentic-awesome-skills, claude-mem, headroom, ponytail, superpowers, system-prompts, replica-skill, task-observer, agency-agents) | 0 (referenced as external) | **RETAIN-ASUS** — Vendor tree adalah asset besar. DELL approach (external refs) untuk future updates. |
| **Skill Count Claim** | 3,378 skills (dari vendor aggregation) | 42 local skills + 40 plugins | **ADAPT-BOTH** — Windows: vendor tree sebagai canonical source (3,378), curated modular subset (42) untuk native linking, plugin catalog (40) untuk external. Jangan klaim angka tanpa distinction. |
| **Skill Status Tracking** | Implicit via vendor dir existence | Explicit `status` di frontmatter (draft/stable/deprecated) | **PORT-DELL** — Add status tracking ke vendor aggregation. |

---

## 14. Ringkasan Keputusan Utama

| Area | Strategi Windows |
|------|------------------|
| **Installer** | `setup.sh` (Linux entrypoint) → calls `installer.py` (shared core) + `setup.ps1` (Windows entrypoint) → calls same `installer.py` |
| **Registry** | DELL `SkillRegistry` architecture + ASUS vendor data + DELL plugin catalog structure |
| **Preflight** | ASUS Mode 0 core + DELL Mode 2 implementation + honest Mode 1 fallback |
| **Memory** | DELL `MemoryManager` + ASUS security hardening (chmod, O_NOFOLLOW) |
| **Compression** | DELL `ContextCompressor` + ASUS headroom integration + `context_budget` constants |
| **Native Integration** | ASUS merge strategy (preserve user config) + DELL agent configs (9 agents) + DELL hook definitions |
| **MCP** | DELL `gateway.py` (FastMCP) + ASUS built servers inventory |
| **Cross-Platform** | DELL pathlib consistency + Windows-specific fixes (case-fold, long paths, PATHEXT, junctions) |
| **CI** | DELL matrix (Ubuntu + Windows) + ASUS static checks + fixed shell commands |
| **Tests** | Combined suite (ASUS integration + DELL unit) |
| **CONTRACT** | ASUS CONTRACT binding + DELL quality standards as appendix |

---

## 15. Risiko & Mitigasi

| Risiko | Sumber | Mitigasi |
|--------|--------|----------|
| Vendor tree breakage saat refactor registry | ASUS vendor size (40k files) | Incremental: pertahankan `registry.py` ASUS sebagai compatibility layer, buat `registry_v2.py` DELL-style baru, migrate secara bertahap dengan test. |
| Hook merge conflicts dengan user config | ASUS merge logic complexity | Test matrix: fresh install, existing config dengan user hooks, existing config dengan user MCP. |
| Windows symlink/junction permission | Skill linking requires symlinks | Document: run setup sebagai Admin untuk full linking, atau fallback ke copy mode. |
| Mode 1 false production claim | Kedua branch unsupported | Explicit documentation: Mode 1 = experimental, fallback ke Mode 0, no SLA. |
| Secret leakage di vendor tree | ASUS history | Pre-commit hook + CI secret scan pada delta Windows branch. |
| CI Windows shell command failures | DELL CI uses Unix commands | Rewrite CI steps untuk Windows: PowerShell native, explicit `shell: pwsh`. |

---

## 16. Evidence Checklist (Untuk Validasi Nanti)

- [ ] Installer Python core (`installer.py`) works dari `setup.sh`, `setup.ps1`, dan direct `python -m installer`
- [ ] Registry V2 loads vendor tree + modular skills + plugin catalog
- [ ] Preflight Mode 0 produces identical output ke ASUS baseline
- [ ] Preflight Mode 2 works dengan fake endpoint (no real API key)
- [ ] Memory V2 passes ASUS memory tests + DELL memory tests
- [ ] Compression works dengan headroom binary (if present) dan Python fallback
- [ ] Native integration installs hooks untuk 9 agents, preserves user settings
- [ ] MCP gateway starts, health check passes, permissions work
- [ ] Cross-platform CI passes di ubuntu-latest dan windows-latest
- [ ] Combined test suite passes (ASUS integration + DELL unit)
- [ ] Secret scan clean pada `git diff origin/claude-code-laptop-asus..Windows`
- [ ] No hardcoded paths, credentials, atau Unix-only assumptions