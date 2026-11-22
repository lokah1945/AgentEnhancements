# Windows Installation & Runtime Guide — AgentEnhancements

**Target Audience:** Windows users (PowerShell/CMD/Git Bash)  
**Branch:** `Windows` (consolidated from ASUS + DELL)  
**Last Updated:** 2026-11-22

---

## 1. Prasyarat

### 1.1 Sistem yang Didukung
- **Windows 10/11** (x64, ARM64)
- **PowerShell 5.1+** (built-in) atau **PowerShell 7+** (recommended)
- **Git Bash** (optional, untuk kompatibilitas skrip Bash)
- **Python 3.10+** (harus di PATH)

### 1.2 Python Installation
```powershell
# Via winget (recommended)
winget install Python.Python.3.12

# Atau via Chocolatey
choco install python3

# Atau download dari python.org
# Pastikan "Add Python to PATH" dicentang saat install
```

### 1.3 Verifikasi Prasyarat
```powershell
python --version    # Harus >= 3.10
git --version       # Untuk clone repo
powershell $PSVersionTable.PSVersion  # Harus >= 5.1
```

---

## 2. Instalasi

### 2.1 Metode 1: PowerShell Native (Recommended)
```powershell
# Clone repository
git clone https://github.com/lokah1945/AgentEnhancements.git
cd AgentEnhancements

# Checkout branch Windows
git checkout Windows

# Jalankan installer PowerShell
.\unified-integration\setup.ps1
```

### 2.2 Metode 2: Git Bash / WSL (Linux-compatible)
```bash
git clone https://github.com/lokah1945/AgentEnhancements.git
cd AgentEnhancements
git checkout Windows
bash unified-integration/setup.sh
```

### 2.3 Metode 3: Python Module Direct (Advanced)
```powershell
git clone https://github.com/lokah1945/AgentEnhancements.git
cd AgentEnhancements
git checkout Windows
python -m unified-integration.scripts.installer install
```

### 2.4 Opsi Installer

| Flag | Deskripsi |
|------|-----------|
| `--agents <list>` | Agent spesifik: `claude-code codex` |
| `--dry-run` | Preview tanpa apply |
| `--verbose` / `-v` | Output debug |
| `--skip-hooks` | Skip hook installation |
| `--skip-mcp` | Skip MCP gateway setup |
| `--skip-memory` | Skip memory system |
| `--skip-compression` | Skip compression setup |
| `--skip-skills` | Skip skill aggregation |
| `--force` | Force reinstall |

**Contoh:**
```powershell
# Install hanya untuk Claude Code dan Codex
.\unified-integration\setup.ps1 --agents claude-code,codex

# Dry run untuk preview
.\unified-integration\setup.ps1 --dry-run --verbose

# Skip MCP gateway
.\unified-integration\setup.ps1 --skip-mcp
```

---

## 3. Konfigurasi Pasca-Install

### 3.1 Restart Agent
Setelah install, **restart AI coding agent** Anda:
- **Claude Code**: Tutup dan buka ulang terminal/VS Code
- **Codex**: Restart Codex CLI
- **Cursor**: Reload window (Ctrl+Shift+P → "Developer: Reload Window")

### 3.2 Verifikasi Hook (Claude Code)
```bash
# Di dalam sesi Claude Code
/hooks
```
Harus menampilkan hook `agent-enhancements` untuk event: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`.

### 3.3 Test Registry
```powershell
python unified-integration/scripts/registry.py map "typescript refactor"
```
Harus mengembalikan daftar skill/plugin/MCP yang relevan.

### 3.4 Test Memory
```powershell
python unified-integration/scripts/memory_v2.py save test_key '{"project": "my-app"}' --type persistent
python unified-integration/scripts/memory_v2.py load test_key --type persistent
```

### 3.5 Test Compression
```powershell
python -c "
import sys
sys.path.insert(0, 'unified-integration/scripts')
from context_compression import ContextCompressor, CompressionConfig, CompressionMode
c = ContextCompressor(CompressionConfig(mode=CompressionMode.PYTHON))
result = c.compress('test content ' * 100, budget=1000)
print(f'Compressed: {result[\"original_tokens\"]} -> {result[\"compressed_tokens\"]} tokens')
"
```

---

## 4. Konfigurasi Lanjutan

### 4.1 File Konfigurasi Utama: `ui.api.json`
File ini berisi API keys dan konfigurasi preflight. **Jangan commit file ini.**

**Lokasi:** Root repository (atau `AGENT_ENHANCEMENTS_BASE_DIR`)

**Template:** `unified-integration/config/ui.api.example.json`

**Contoh isi:**
```json
{
  "api_keys": {
    "OPENAI_API_KEY": ["sk-..."],
    "ANTHROPIC_API_KEY": ["sk-ant-..."],
    "GITHUB_TOKEN": ["ghp_..."],
    "PREFLIGHT_API_KEY": ["sk-..."]
  },
  "preflight": {
    "mode": 0,
    "max_skill_cards": 8,
    "token_budget": 400
  }
}
```

### 4.2 Environment Variables
| Variable | Deskripsi | Default |
|----------|-----------|---------|
| `AE_PREFLIGHT_MODE` | Override preflight mode (0/1/2) | 0 |
| `AE_PREFLIGHT_DEADLINE_MS` | Timeout preflight (ms) | 2000 |
| `AE_MAX_SKILL_CARDS` | Max skill cards per prompt | 8 |
| `AGENT_ENHANCEMENTS_BASE_DIR` | Override repo root | Auto-detect |
| `AGENT_MEMORY_ROOT` | Override memory directory | `.agentenhancements/memory` |
| `CLAUDE_CONFIG_DIR` | Override Claude config dir | `~/.claude` |
| `CODEX_HOME` | Override Codex config dir | `~/.codex` |

### 4.3 Preflight Modes
| Mode | Nama | Status | Deskripsi |
|------|------|--------|-----------|
| 0 | Legacy | ✅ **Production** | Heuristic keyword matching, no external calls |
| 1 | Native Auto | ⚠️ **Unsupported** | Host-native selection (API tidak tersedia) |
| 2 | Custom Endpoint | 🧪 **Experimental** | Custom LLM endpoint untuk capability selection |

**Rekomendasi:** Gunakan **Mode 0** (default). Mode 1 tidak didukung karena host APIs tidak expose selection surface. Mode 2 butuh endpoint custom yang valid.

---

## 5. Troubleshooting

### 5.1 Hook Tidak Terpasang (Claude Code)
```powershell
# Cek settings.json
type $env:USERPROFILE\.claude\settings.json

# Harus ada entry hook dengan command berisi "unified-integration/scripts/runtime.py"
# Jika tidak ada, jalankan ulang setup:
.\unified-integration\setup.ps1 --force
```

### 5.2 Python Tidak Ditemukan
```powershell
# Pastikan Python di PATH
where python

# Jika pakai py launcher
py -3 --version

# Set PYTHON_EXE jika perlu
$env:PYTHON_EXE = "py -3"
```

### 5.3 Symlink Gagal (Windows)
Windows butuh **Admin privileges** untuk symlink. Jika gagal:
```powershell
# Jalankan PowerShell sebagai Administrator
# Atau gunakan mode copy (fallback otomatis di installer v2)
```

### 5.4 MCP Gateway Tidak Start
```powershell
# Cek log
python unified-integration/scripts/gateway.py status

# Rebuild MCP runtime
bash unified-integration/scripts/setup-mcp.sh --prepare
```

### 5.5 Headroom Binary Tidak Ditemukan
```powershell
# Build dari source (butuh Rust)
cd headroom
cargo build --release

# Atau install via cargo
cargo install headroom-cli
```

---

## 6. Uninstall / Repair / Upgrade

### 6.1 Uninstall
```powershell
# Manual cleanup (installer v2 belum punya uninstall command)
# 1. Hapus hook dari agent configs
# 2. Hapus skill links di ~/.claude/skills, ~/.codex/skills, dll.
# 3. Hapus MCP gateway dari ~/.claude.json, ~/.codex/config.toml
# 4. Hapus folder .agentenhancements di repo root
```

### 6.2 Repair
```powershell
# Re-run installer dengan force
.\unified-integration\setup.ps1 --force
```

### 6.3 Upgrade
```powershell
# Pull latest changes
git pull origin Windows

# Re-run installer
.\unified-integration\setup.ps1 --force
```

---

## 7. Git Bash Compatibility

Jika menggunakan **Git Bash** (MSYS2):
```bash
# Semua perintah di atas works di Git Bash
# Setup.sh adalah entry point canonical (CONTRACT §2.1)

# Catatan: Path Windows (C:\Users\...) works di Git Bash
# Environment variables: $HOME, $USERPROFILE
```

---

## 8. Known Limitations (Windows)

| Limitation | Workaround |
|------------|------------|
| Symlink butuh Admin | Installer fallback ke copy mode |
| Case-insensitive FS | Registry handles case-fold collision |
| Long paths (>260) | Enable via Group Policy / Registry |
| PATHEXT handling | Python `shutil.which` used |
| PowerShell execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

---

## 9. Support & Reporting Issues

- **GitHub Issues**: https://github.com/lokah1945/AgentEnhancements/issues
- **Branch**: `Windows` (target branch untuk Windows fixes)
- **Logs**: `$env:USERPROFILE\.agentenhancements\logs\` (jika enabled)

---

## 10. Quick Reference Card

```powershell
# Install cepat
git clone https://github.com/lokah1945/AgentEnhancements.git
cd AgentEnhancements
git checkout Windows
.\unified-integration\setup.ps1

# Verifikasi
python -m unified-integration.scripts.installer detect
python unified-integration/scripts/registry.py map "build mcp server"
python unified-integration/scripts/memory_v2.py stats

# Config
notepad ui.api.json  # Edit API keys
notepad unified-integration/config/compression.yaml  # Compression settings

# Update
git pull origin Windows
.\unified-integration\setup.ps1 --force
```