# Cross-Platform Compatibility — AgentEnhancements Windows/Linux Architecture

**Target:** Agent integrator untuk merge `Windows` branch ke `master` di masa depan  
**Prinsip:** Single source of truth, adapter tipis per platform, no divergence

---

## 1. Arsitektur Single Source of Truth

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED PYTHON CORE                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │ installer.py│ │  memory_v2  │ │ compression │ │  registry │ │
│  │ native_v2   │ │  preflight  │ │  gateway    │ │  hooks    │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
       │  Linux/macOS│ │   Windows   │ │   Git Bash  │
       │  (WSL)      │ │  PowerShell │ │   (MSYS2)   │
       └─────────────┘ └─────────────┘ └─────────────┘
              │               │               │
       ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
       │  setup.sh   │ │  setup.ps1  │ │  setup.sh   │
       │  (entry)    │ │  (entry)    │ │  (entry)    │
       └─────────────┘ └─────────────┘ └─────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    ┌─────────────────────┐
                    │   python -m installer│
                    │   install (core)    │
                    └─────────────────────┘
```

**Key Principle:** Entry points (`setup.sh`, `setup.ps1`) are **thin wrappers** yang mendelegasikan ke `python -m installer install`. Logic inti **hanya di Python**.

---

## 2. Platform-Specific Adaptations

### 2.1 Path Handling

| Aspek | Linux/macOS | Windows | Implementation |
|-------|-------------|---------|----------------|
| Home dir | `$HOME` / `~` | `%USERPROFILE%` | `Path.home()` (cross-platform) |
| Config dir | `~/.claude` | `%USERPROFILE%\.claude` | `os.path.expanduser()` + env override |
| Path separator | `/` | `\` | `pathlib.Path` (auto) |
| Case sensitivity | Case-sensitive | Case-insensitive | Registry normalizes to lowercase |
| Long paths | Native | >260 butuh enable | `\\?\` prefix / Group Policy |
| Symlinks | Native | Butuh Admin / Developer Mode | Fallback ke copy |

**Code Pattern:**
```python
# ✅ GOOD - cross-platform
from pathlib import Path
config_dir = Path.home() / ".claude"
config_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR", config_dir))

# ❌ BAD - Windows-only
config_dir = Path("C:/Users/...")  # Hardcoded

# ❌ BAD - Unix-only  
config_dir = Path("~/.claude").expanduser()  # ~ not expanded on Windows without shell
```

### 2.2 Shell & Process Execution

| Aspek | Linux/macOS | Windows | Implementation |
|-------|-------------|---------|----------------|
| Default shell | `/bin/bash` | `powershell.exe` / `cmd.exe` | `sys.executable` untuk Python |
| Command joining | `shlex.join()` | `shlex.join()` (works) | Always use `shlex.join()` |
| Env var passing | `VAR=val cmd` | `$env:VAR="val"; cmd` | `env` prefix via `shlex.join` |
| PATH lookup | `which` / `command -v` | `where` / `shutil.which` | `shutil.which()` |
| PATHEXT | N/A | `.exe;.bat;.cmd;.ps1` | `shutil.which` handles |
| Python launcher | `python3` | `py -3` / `python` | `sys.executable` |

**Code Pattern:**
```python
# ✅ GOOD - cross-platform hook command
import shlex, sys
cmd = shlex.join([
    'env',
    f'AGENT_ENHANCEMENTS_BASE_DIR={base_dir}',
    f'AGENT_MEMORY_ROOT={memory_root}',
    sys.executable,  # Respects venv, py launcher
    str(runtime_script),
    event_name
])

# ❌ BAD - shell injection risk
cmd = f'python {runtime_script} {event_name}'  # No quoting!

# ❌ BAD - Unix-only
cmd = f'PYTHONPATH=/foo python3 {script}'  # Unix env syntax
```

### 2.3 File System & Permissions

| Aspek | Linux/macOS | Windows | Implementation |
|-------|-------------|---------|----------------|
| Permissions | `chmod 700/600` | ACL / `icacls` | `chmod` works on Git Bash, no-op on native |
| Symlinks | `ln -s` | `mklink` / junctions | Try `symlink_to()`, fallback `copytree()` |
| Temp files | `/tmp` | `%TEMP%` | `tempfile.gettempdir()` |
| Lock files | `fcntl` / `flock` | `msvcrt.locking` | SQLite WAL mode (cross-process) |
| Atomic writes | `rename()` | `ReplaceFile` / `rename` | `pathlib.Path.write_text()` atomic enough |

**Code Pattern:**
```python
# ✅ GOOD - symlink with fallback
try:
    target.symlink_to(source)
except (OSError, NotImplementedError):
    # Windows without Admin/Developer Mode
    shutil.copytree(source, target, dirs_exist_ok=True)

# ✅ GOOD - secure DB file (ASUS hardening)
import os, stat
fd = os.open(db_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        raise OSError("DB must be regular file")
finally:
    os.close(fd)
os.chmod(db_path, 0o600)  # Best effort on Windows
```

---

## 3. Entry Point Contract (CONTRACT §2.1)

### 3.1 `setup.sh` — Canonical Linux/macOS/Git Bash Entry
```bash
# Responsibilities:
# 1. One-liner install support (clone/fetch to persistent dir)
# 2. Skill aggregation from vendor tree (Bash-specific, complex)
# 3. Delegate to: python3 -m installer install "$@"
```

### 3.2 `setup.ps1` — Windows PowerShell Entry
```powershell
# Responsibilities:
# 1. Find Python (python, python3, py -3)
# 2. Delegate to: python -m installer install [args]
# 3. No skill aggregation (done by setup.sh if needed)
```

### 3.3 `python -m installer` — Shared Core
```python
# Responsibilities (ALL platforms):
# 1. Directory preparation
# 2. Agent detection (cross-platform)
# 3. Skill catalog build (via registry.cmd_build)
# 4. Native integration (hooks, MCP, skills linking)
# 5. Memory system init
# 6. Compression config
# 6. MCP gateway setup
# 7. Launcher generation
# 8. Runtime config save
```

---

## 4. CI/CD Cross-Platform Matrix

### 4.1 GitHub Actions Workflow (`.github/workflows/ci.yml`)

```yaml
jobs:
  integration-tests:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      # Linux steps
      - if: runner.os == 'Linux'
        run: |
          bash unified-integration/scripts/setup-mcp.sh --prepare
          runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
          env -u CODEX_HOME ... "$runtime_python" unified-integration/tests/run-tests.py
      
      # Windows steps  
      - if: runner.os == 'Windows'
        shell: pwsh
        run: |
          $runtime_python = & bash unified-integration/scripts/setup-mcp.sh --prepare
          $env:CODEX_HOME = $null
          ...
          & $runtime_python unified-integration/tests/run-tests.py
```

### 4.2 Key Differences Per OS

| Step | Ubuntu | Windows |
|------|--------|---------|
| Shell | `bash` | `pwsh` (PowerShell) |
| Path separator | `/` | `\` (handled by Pathlib) |
| Env var unset | `env -u VAR` | `$env:VAR = $null` |
| Chmod | `chmod 700` | No-op / ACL |
| Symlink | Native | Admin required |
| Python | `python3` | `python` / `py -3` |

---

## 5. Testing Strategy

### 5.1 Test Categories

| Category | Linux | Windows | Both |
|----------|-------|---------|------|
| Unit tests (pytest) | ✅ | ✅ | ✅ |
| Integration tests | ✅ | ✅ | ✅ |
| Hook E2E tests | ✅ | ✅ | ✅ |
| Bash script tests | ✅ | ❌ (Git Bash only) | |
| PowerShell tests | ❌ | ✅ | |
| Symlink tests | ✅ | ⚠️ (Admin) | |
| Long path tests | ✅ | ✅ (if enabled) | |

### 5.2 Test Isolation

```python
# ✅ GOOD - isolated temp dirs
import tempfile
from pathlib import Path

def test_something():
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir).resolve()
        # Test with clean state
        ...

# ✅ GOOD - fake home for agent detection
fake_home = base_dir / "fake_home"
fake_home.mkdir()
installer._detect_agents(override_home=fake_home)

# ❌ BAD - uses real home
installer._detect_agents()  # Pollutes user config!
```

---

## 6. Merge Strategy: Windows → Master

### 6.1 Conflict Areas (Predicted)

| Area | Windows Branch | Master Branch | Resolution |
|------|----------------|---------------|------------|
| `setup.sh` | Delegates to installer.py | Full Bash logic | Keep Windows version (thin wrapper) |
| `installer.py` | New shared core | Not exist | Add to master |
| `native_integration_v2.py` | 9 agents, dataclasses | `native-integration.py` (4 agents) | Replace with v2 |
| `memory_v2.py` | Thread-safe, multi-type | `memory.py` (basic) | Replace with v2 |
| `context_compression.py` | CompressionMode enum | `compress.py` + headroom | Replace |
| `adaptive_preflight_v2.py` | Structured, Mode 1 honest | `adaptive_preflight.py` | Merge best of both |
| `gateway.py` | FastMCP pattern | `mcp-servers/gateway.py` | Replace |
| CI workflow | Cross-platform matrix | Ubuntu only | Extend master CI |
| Tests | 63 new tests | Existing tests | Merge test suites |

### 6.2 Required Validation Before Merge

- [ ] All 63 Windows tests pass on Ubuntu + Windows
- [ ] Existing ASUS tests still pass
- [ ] Skill aggregation (`setup.sh aggregate-skills`) works
- [ ] Hook installation preserves user config (merge strategy)
- [ ] MCP gateway starts and health checks pass
- [ ] Memory v2 backward compatible with existing DB
- [ ] Compression works with/without headroom binary
- [ ] Preflight Mode 0 produces identical output
- [ ] No hardcoded paths, Unix-only commands, or secrets
- [ ] Documentation updated (README, CONTRACT if needed)

---

## 7. Compatibility Checklist (Per Component)

### 7.1 Installer
- [ ] `setup.sh` one-liner install works
- [ ] `setup.ps1` works on PowerShell 5.1+
- [ ] `python -m installer` works on both
- [ ] Dry-run mode works
- [ ] Agent detection cross-platform
- [ ] Skill aggregation (Bash) unchanged

### 7.2 Native Integration
- [ ] Hook merge preserves user hooks (ASUS strategy)
- [ ] MCP merge preserves user servers (ASUS strategy)
- [ ] 9 agents supported (4 native + 5 reference)
- [ ] Skill linking works (symlink + copy fallback)
- [ ] Settings backup before modify

### 7.3 Registry & Discovery
- [ ] `cmd_build` reads `all-skills.json` + catalog
- [ ] `cmd_map` returns relevant results
- [ ] Readiness levels (READY/GUIDE_ONLY/MISSING_CREDS)
- [ ] Framework conflict detection
- [ ] Token budget enforcement

### 7.4 Memory
- [ ] SQLite WAL mode on both OS
- [ ] Thread-safe (RLock)
- [ ] TTL policies work
- [ ] Parameterized queries (no injection)
- [ ] Secure file perms (chmod 600 + O_NOFOLLOW)

### 7.5 Compression
- [ ] Python fallback works
- [ ] Headroom binary auto-detected
- [ ] Config via YAML
- [ ] Budget/trigger respected

### 7.6 Preflight
- [ ] Mode 0 identical to ASUS
- [ ] Mode 1 honest fallback + warning
- [ ] Mode 2 works with fake endpoint
- [ ] Config from `ui.api.json` + env override

---

## 8. Future-Proofing Guidelines

1. **No new Bash logic in shared core** — Python only
2. **Entry points stay thin** — `setup.sh`/`setup.ps1` only delegate
3. **Pathlib everywhere** — No `os.path.join`, no string paths
4. **shlex.join for commands** — Never f-string commands
5. **sys.executable for Python** — Respects venv, py launcher
6. **Environment variable config** — Overrideable, documented
7. **Test on both OS** — CI matrix mandatory
8. **Document platform quirks** — In this file and code comments