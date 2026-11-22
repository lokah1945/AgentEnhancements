# Future Master Merge Handoff — Windows → Master Integration Guide

**Target Audience:** Agent yang akan mengintegrasikan branch `Windows` ke `master`  
**Branch Sumber:** `Windows` (consolidated ASUS + DELL)  
**Branch Target:** `master` (default branch)  
**Catatan:** **JANGAN LAKUKAN MERGE INI SEKARANG** — Dokumen ini hanya instruksi untuk masa depan.

---

## 1. Persiapan Pre-Merge

### 1.1 Verifikasi Branch Windows
```bash
# Pastikan branch Windows up-to-date
git fetch origin
git checkout Windows
git pull origin Windows

# Verifikasi SHA
git log --oneline -5
# Catat SHA HEAD Windows untuk referensi
```

### 1.2 Verifikasi Master Baseline
```bash
git checkout master
git pull origin master
git log --oneline -5
# Catat SHA HEAD master
```

### 1.3 Buat Merge Branch
```bash
git checkout -b merge-windows-to-master master
```

---

## 2. Area Konflik yang Diprediksi

### 2.1 File-File yang Akan Conflict

| File | Windows Version | Master Version | Strategi Resolusi |
|------|-----------------|----------------|-------------------|
| `unified-integration/setup.sh` | Thin wrapper → installer.py | Full Bash logic | **Keep Windows** (thin wrapper per CONTRACT §2.1) |
| `unified-integration/scripts/native-integration.py` | **DEPRECATED** (v2 exists) | Current canonical | **Remove/Archive**, use `native_integration_v2.py` |
| `unified-integration/scripts/memory.py` | **DEPRECATED** (v2 exists) | Current canonical | **Remove/Archive**, use `memory_v2.py` |
| `unified-integration/scripts/compress.py` | **DEPRECATED** (v2 exists) | Current canonical | **Remove/Archive**, use `context_compression.py` |
| `unified-integration/scripts/adaptive_preflight.py` | **DEPRECATED** (v2 exists) | Current canonical | **Merge best of both** → `adaptive_preflight_v2.py` |
| `unified-integration/scripts/registry.py` | ASUS version (cmd_build from all-skills.json) | Same | **Keep ASUS**, add v2 features incrementally |
| `.github/workflows/ci.yml` | Cross-platform matrix | Ubuntu only | **Merge Windows CI** into master |
| `README.md` | Updated counts + Windows guide | ASUS version | **Merge docs**, keep vendor counts |
| `CONTRACT.md` | ASUS binding + DELL appendix | ASUS binding | **Keep ASUS**, add DELL standards as appendix |

### 2.2 File Baru di Windows (Harus Di-Add ke Master)

```
unified-integration/
├── setup.ps1                           # Windows entry point
├── scripts/
│   ├── installer.py                    # Shared installer core
│   ├── native_integration_v2.py        # 9-agent native integration
│   ├── memory_v2.py                    # Thread-safe memory manager
│   ├── context_compression.py          # CompressionMode enum + headroom
│   ├── adaptive_preflight_v2.py        # Structured preflight v2
│   ├── gateway.py                      # FastMCP gateway
│   ├── native_config.py                # (existing, used by v2)
│   └── project_paths.py                # (existing, used by v2)
├── tests/
│   ├── test_installer.py
│   ├── test_memory_v2.py
│   ├── test_context_compression.py
│   ├── test_native_integration_v2.py
│   └── test_adaptive_preflight_v2.py
└── config/
    ├── compression.yaml                # Compression config
    ├── ui.api.example.json             # Config template
    └── ui.api.schema.json              # Config schema
```

### 2.3 File yang Bisa Di-Archive/Remove dari Master

```
unified-integration/scripts/
├── native-integration.py        → ARCHIVE (replaced by v2)
├── memory.py                    → ARCHIVE (replaced by v2)
├── compress.py                  → ARCHIVE (replaced by context_compression.py)
├── adaptive_preflight.py        → ARCHIVE (replaced by v2)
└── load-skills.py               → KEEP (used by runtime.py)
```

---

## 3. Langkah-Langkah Merge

### 3.1 Phase 1: Core Infrastructure (No Functional Changes)
```bash
# 1. Add new files
git add unified-integration/setup.ps1
git add unified-integration/scripts/installer.py
git add unified-integration/scripts/native_integration_v2.py
git add unified-integration/scripts/memory_v2.py
git add unified-integration/scripts/context_compression.py
git add unified-integration/scripts/adaptive_preflight_v2.py
git add unified-integration/scripts/gateway.py
git add unified-integration/tests/test_*.py
git add unified-integration/config/*.yaml unified-integration/config/*.json

# 2. Update setup.sh to thin wrapper (if not already)
# 3. Update CI workflow
git add .github/workflows/ci.yml

git commit -m "feat(windows): add cross-platform installer core and v2 modules

- Add installer.py as shared core for setup.sh/setup.ps1
- Add native_integration_v2.py (9 agents, dataclass config)
- Add memory_v2.py (thread-safe, multi-type, TTL policies)
- Add context_compression.py (CompressionMode enum, headroom)
- Add adaptive_preflight_v2.py (structured Mode 0/1/2)
- Add gateway.py (FastMCP pattern)
- Add comprehensive test suite (63 tests)
- Extend CI to cross-platform matrix (ubuntu-latest + windows-latest)

Co-Authored-By: Claude Code <noreply@anthropic.com>
Agent: Claude Code | Session: <session-id> | Task: Windows consolidation Phase 1"
```

### 3.2 Phase 2: Migration & Deprecation
```bash
# 1. Update runtime.py to use v2 modules
# 2. Update setup.sh to delegate skill aggregation only
# 3. Archive old modules (move to _archive/ or delete)
# 4. Update imports in all files

git commit -m "refactor(windows): migrate to v2 modules, archive legacy

- Migrate runtime.py hooks to use memory_v2, context_compression, adaptive_preflight_v2
- Archive native-integration.py, memory.py, compress.py, adaptive_preflight.py
- Update skill aggregation in setup.sh to be standalone
- Fix all imports to use v2 modules

Co-Authored-By: Claude Code <noreply@anthropic.com>
Agent: Claude Code | Session: <session-id> | Task: Windows consolidation Phase 2"
```

### 3.3 Phase 3: Documentation & Polish
```bash
# 1. Update README.md with Windows install guide
# 2. Update CONTRACT.md with DELL standards appendix
# 3. Sync capability counts
# 4. Update docs/

git commit -m "docs(windows): update README, CONTRACT, and capability counts

- Add Windows PowerShell install instructions to README
- Add DELL quality standards as CONTRACT appendix
- Regenerate capability counts from vendor tree
- Update cross-platform compatibility notes

Co-Authored-By: Claude Code <noreply@anthropic.com>
Agent: Claude Code | Session: <session-id> | Task: Windows consolidation Phase 3"
```

---

## 4. Validasi Wajib Post-Merge

### 4.1 Test Suite Lengkap
```bash
# Linux (Ubuntu CI equivalent)
bash unified-integration/setup.sh --dry-run
python -m pytest unified-integration/tests/ -v
bash unified-integration/tests/run-tests.py
python unified-integration/tests/discovery_benchmark.py --check

# Windows (PowerShell)
.\unified-integration\setup.ps1 --dry-run
python -m pytest unified-integration/tests/ -v
```

### 4.2 Real Agent Validation
```bash
# Test dengan agent asli (manual)
# 1. Fresh install di Windows bersih
# 2. Verifikasi hook di Claude Code (/hooks)
# 3. Verifikasi skill injection di UserPromptSubmit
# 4. Verifikasi memory persist
# 5. Verifikasi MCP gateway
```

### 4.3 Regression Check
```bash
# Bandingkan output registry
git stash
git checkout master  # pre-merge
python unified-integration/scripts/registry.py map "typescript refactor" > /tmp/master_registry.txt
git checkout merge-windows-to-master
python unified-integration/scripts/registry.py map "typescript refactor" > /tmp/windows_registry.txt
diff -u /tmp/master_registry.txt /tmp/windows_registry.txt
# Harus minimal diff (hanya urutan/format, bukan konten)
```

---

## 5. Modul Sensitif yang Butuh Perhatian Khusus

### 5.1 `runtime.py` — Hook Handler Utama
**Risiko:** Perubahan di sini mempengaruhi SEMUA agent.
**Validasi:** 
- [ ] SessionStart injects observer + memory
- [ ] UserPromptSubmit injects skill cards (Mode 0)
- [ ] PreToolUse/PostToolUse/Stop work
- [ ] Error handling non-blocking (advisory only)

### 5.2 `native_integration_v2.py` — Hook Installation
**Risiko:** Merge strategy harus preserve user config.
**Validasi:**
- [ ] `merge_hooks` preserves user hooks
- [ ] `merge_servers` preserves user MCP servers
- [ ] Settings backup before write
- [ ] 9 agents install correctly

### 5.3 `adaptive_preflight_v2.py` — Capability Selection
**Risiko:** Mode 1 fallback behavior.
**Validasi:**
- [ ] Mode 0 output identical to ASUS
- [ ] Mode 1 shows warning + fallback
- [ ] Mode 2 works with fake endpoint
- [ ] Config from `ui.api.json` + env override

### 5.4 `memory_v2.py` — SQLite Database
**Risiko:** Schema migration, concurrent access.
**Validasi:**
- [ ] Existing DB readable (backward compat)
- [ ] WAL mode works on Windows
- [ ] Thread-safe (RLock)
- [ ] TTL cleanup works
- [ ] Secure perms (chmod 600 + O_NOFOLLOW)

---

## 6. Rollback Plan

Jika merge menyebabkan regresi kritis:

```bash
# 1. Revert merge commit
git revert <merge-commit-sha>

# 2. Atau reset branch (jika belum push)
git reset --hard origin/master

# 3. Hotfix di branch Windows terpisah
git checkout Windows
# Fix issues
git push origin Windows

# 4. Retry merge dengan fix
```

---

## 7. Checklist Final Handoff

### 7.1 Dokumentasi (Sudah Ada di `docs/windows-consolidation/`)
- [x] `01_BRANCH_AND_HISTORY_AUDIT.md` — SHA, ancestry, strategi
- [x] `02_FEATURE_RECONCILIATION.md` — Matriks fitur + keputusan
- [x] `03_WINDOWS_INSTALL_AND_RUNTIME.md` — User guide Windows
- [x] `04_CROSS_PLATFORM_COMPATIBILITY.md` — Arsitektur + CI
- [x] `05_TEST_EVIDENCE_AND_RELEASE_GATE.md` — Test evidence + gates
- [x] `06_FUTURE_MASTER_MERGE_HANDOFF.md` — (This file)

### 7.2 Kode & Test
- [x] 63 unit tests baru (100% pass)
- [x] Installer core (`installer.py`) + entry points (`setup.sh`, `setup.ps1`)
- [x] 5 v2 modules (native, memory, compression, preflight, gateway)
- [x] CI cross-platform (Ubuntu + Windows)
- [x] Security scan clean

### 7.3 Blocker Saat Ini
- [ ] **Real agent E2E validation** (Gate G6) — Butuh manual test
- [ ] **ASUS regression baseline** — Butuh compare run

---

## 8. Kontak & Referensi

**Branch Windows SHA:** (catat saat push)  
**Master SHA Baseline:** (catat saat merge)  
**Dokumen Konsolidasi:** `docs/windows-consolidation/*.md`  
**Test Results:** `unified-integration/tests/` (63 tests)  
**CI Config:** `.github/workflows/ci.yml`

**Catatan Penting:** 
- Branch `Windows` adalah **single source of truth** untuk Windows native
- Jangan modifikasi `origin/claude-code-laptop-asus` atau `origin/claude-code-laptop-dell`
- Semua perubahan di `Windows` branch sudah terdokumentasi di 6 dokumen di atas
- Merge ke `master` adalah tugas terpisah oleh agent Linux di masa depan

---

**Prepared by:** Claude Code (nvidia/nemotron-3-ultra-550b-a55b)  
**Date:** 2026-11-22  
**Status:** Ready for future master integration (pending Gate G6 validation)