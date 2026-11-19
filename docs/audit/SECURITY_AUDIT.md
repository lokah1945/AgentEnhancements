# Security Audit — Deep Audit

**Scope:** All secret handling, input validation, path traversal, MCP gating, redaction, supply chain

---

## 1. Secret Management

### `api_config.py` — `ui.api.json` Credentials
```python
# NEVER inherits from process environment
def value(name: str, config: dict | None = None) -> str:
    if config is None:
        config, _ = read_config()
    for section in ("api_keys", "connections"):
        result = config.get(section, {}).get(name, "")
        if isinstance(result, str) and result.strip():
            return result.strip()
    return ""  # Empty entries stay empty — no env fallback
```

**Security Properties:**
- ✅ Empty entries deliberately do NOT inherit from env
- ✅ Config file 0600 perms (`initialize()` uses `os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600`)
- ✅ Size limit: 1MB max (`path.stat().st_size > 1024 * 1024`)
- ✅ Version pinning: `type(doc.get("version")) is int and == 1`
- ✅ Duplicate key rejection (`_unique_object` hook)
- ✅ String-only validation for all credential values
- ✅ `redact()` removes configured secrets from diagnostics

### `adaptive_preflight.py` — Mode 2 API Keys
```python
def resolve_api_key(endpoint: str) -> str:
    # 1. AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY env
    # 2. OS keyring (service="agentenhancements.preflight", account=origin)
    # 3. <config_dir>/preflight.key (0600, first non-empty line)
    # NEVER: ui.api.json, model.json
```

**Security Properties:**
- ✅ Keys bound to endpoint origin (prevents cross-origin reuse)
- ✅ Keyring integration (OS secure storage)
- ✅ File perms 0600 enforced (`st_mode & 0o077 == 0`)
- ✅ `model.json` holds NO secrets (explicitly documented)
- ✅ Separate namespace from MCP credentials

### `runtime.py` — Redaction
```python
SECRET = re.compile(
    r"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]+|sk-(?:ant-)?[A-Za-z0-9_-]{16,}"
    r"|\bAKIA[A-Z0-9]{16}\b"
    r"|(?i:(?:api[_-]?key|access[_-]?token|password|secret|authorization)"
    r"\s*[:=]\s*[\"']?[^\s\"',}]+)"
)
```

**Coverage:**
- ✅ GitHub PATs (`github_pat_`, `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`)
- ✅ OpenAI/Anthropic keys (`sk-`, `sk-ant-`)
- ✅ AWS access keys (`AKIA...`)
- ✅ Generic `api_key=`, `access_token=`, `password=`, `secret=`, `authorization=`

**Applied at:**
- `SessionStart` memory recall (redacted before display)
- `UserPromptSubmit` prompt save (redacted before SQLite)
- `Stop` summary save (redacted)
- `api_config.redact()` for diagnostics

---

## 2. Input Validation & Fail-Closed

### `api_config.read_config()` — Malformed Config
```python
try:
    # parse, validate version, structure, types
    return doc, None
except (OSError, ValueError, TypeError, UnicodeError):
    # Exception text can include source JSON and credentials. Keep it private.
    return {"api_keys": {}, "connections": {}, "mcp": {}}, "config_unavailable_or_invalid"
```
- ✅ Fails closed: returns empty config + error code
- ✅ No exception details leaked (credentials in traceback)
- ✅ Size limit prevents DoS via huge config

### `adaptive_preflight.load_model_config()` — Model Config
```python
# Validates:
# - File size ≤ 64KB
# - Valid JSON, no duplicate keys
# - Mode ∈ {0,1,2} (exact int, not bool)
# - Mode 2: HTTPS endpoint, valid SDK, non-empty model
# - On ANY failure: returns Mode 0 with diagnosis code
```

### `registry.find_entry()` — Typed ID Resolution
```python
# Two-pass resolution:
# 1. Exact typed ID match (skill:, plugin:, mcp:, capability:)
# 2. Stripped name/slug match
# Prevents: capability:task-observer → skill:task-observer alias bug
```

### `native_config.write()` — Atomic Config Updates
```python
# Tempfile + os.replace (atomic)
# Private backup with timestamp before overwrite
# Preserves unchanged files (no unnecessary mtime changes)
```

### `adaptive_preflight._NoRedirectHandler` — HTTP Redirect Refusal
```python
class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Refuse redirects — validated origin must not move
```

---

## 3. Path Traversal Guards

### `adaptive_preflight._file_under_roots()`
```python
def _file_under_roots(candidate: Path, roots: List[Path]) -> bool:
    try:
        resolved = candidate.resolve()
    except OSError:
        return False
    return any(resolved.is_relative_to(root) for root in roots)

# Used in _resolve_entry() for skill/plugin/MCP file resolution
# Roots: REPO_ROOT + optional AGENT_SKILLS_DIR override
```

### `task-observer.py` — Workspace Validation
```python
def workspace_root(explicit: Optional[str] = None) -> Path:
    if explicit:
        root = Path(explicit).expanduser()
    else:
        # AGENT_MEMORY_ROOT or ~/.agent-memory
    if not root.is_absolute():
        raise ValueError(f"workspace root must be absolute, got {root}")
    return root

# Stage/Promote: validates skill_name is single component (no ..)
# Containment check before rmtree/copytree
```

### `native_hermes.py` — Profile Name Validation
```python
if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
    raise ValueError("invalid Hermes profile name")
```

---

## 4. MCP Server Gating

### `api_config.server_state()` — Visibility Control
```python
DEFAULT_DISABLED = frozenset({"task-router-mcp"})  # Executes arbitrary bash/python

def server_state(name: str, config: dict | None = None) -> dict:
    # 1. Disabled by default? → visible=False, reason="disabled_by_default"
    # 2. Explicitly enabled=false? → visible=False, reason="disabled"
    # 3. Built-in local tools? → visible=True, reason="local_tools_available"
    # 4. Config error? → visible=False, reason="config_unavailable_or_invalid"
    # 5. Not configured? → visible=False, reason="not_configured"
    # 6. Missing required credentials? → visible=False, reason="missing_credentials"
    # 7. Executable not in PATH? → visible=False, reason="executable_not_installed"
    # 8. All good → visible=True, reason="configured"
```

**Security Properties:**
- ✅ Dangerous servers (`task-router-mcp`) opt-in only
- ✅ Credential presence validated before visibility
- ✅ Executable existence verified (no phantom servers)
- ✅ Config errors fail closed (no partial visibility)

### `native-integration.py` — Gateway Pattern
```python
def mcp_block() -> dict:
    # Single stable gateway: "agent-enhancements"
    # Injects env vars at runtime
    # Retires old direct entries on update
    # Preserves user tool approvals/timeouts
```

---

## 5. Supply Chain

### Vendored Dependencies
| Component | Source | Pin | Verification |
|-----------|--------|-----|--------------|
| `task-observer` | rebelytics/one-skill-to-rule-them-all | `d61bc31f7857948710a947673c0e373bef4ed3d0` (v3.10.0) | `VENDORED.json` with SHA256 per file |
| `replica-skill` | Jakeschincariol/replica-skill | Bundled in plugin-catalog | Manifest `vendored: true` |
| `anthropic-skills` | anthropics/skills | Bundled in plugin-catalog | Manifest `vendored: true` |
| `agency-agents` | msitarzewski/agency-agents | 14 plugins, bundled | Manifest `vendored: true` |

**Gaps:**
- ⚠️ No automated dependency update checking
- ⚠️ No SBOM generation
- ⚠️ `VENDORED.json` only for task-observer; others lack per-file checksums

### ECC2 Rust (`ECC/ecc2/`)
- ✅ `Cargo.lock` committed
- ✅ `rust-toolchain.toml` pins version
- ✅ `deny.toml` for supply chain (advisories, bans, licenses)
- ⚠️ `main.rs` 459KB monolith — hard to audit

### Python Dependencies (`unified-integration/requirements.txt`)
```
tiktoken
pyyaml
json5
keyring
```
- ⚠️ No version pinning in requirements.txt
- ⚠️ No `pip-audit` / `safety` in CI
- ⚠️ `keyring` optional but used for Mode 2 keys

---

## 6. Runtime Isolation

### Hook Execution (`runtime.py`)
```python
MAX_INPUT = 2_000_000  # 2MB stdin limit
MAX_CONTEXT = 12_000   # 12K token output limit

# All failures advisory — hook never blocks agent work
try:
    context = handle(args.agent, event)
except Exception as exc:
    print(f"[AgentEnhancements] hook skipped: {type(exc).__name__}", file=sys.stderr)
```

### Preflight Deadline (`adaptive_preflight.py`)
```python
DEFAULT_DEADLINE_SECONDS = 2.0
MIN_DEADLINE_SECONDS = 0.1
MAX_DEADLINE_SECONDS = 8.0
MAX_INFERENCE_ROUNDS = 2
HTTP_TIMEOUT_CAP_SECONDS = 10.0

# Monotonic deadline shared across catalog reads, connection, inference, validation
# Late results discarded
```

### Memory DB (`memory.py`)
```python
MEMORY_ROOT = Path(os.environ.get("AGENT_MEMORY_ROOT", Path.home() / ".agent-memory"))
DB_PATH = MEMORY_ROOT / "memory.db"

# Dir 0700, file 0600
MEMORY_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
DB_PATH.chmod(0o600)

# SQLite parameterized queries (no injection)
# TTL via expires_at + cleanup_expired() on SessionStart
```

---

## 7. Security Scorecard

| Area | Score | Evidence |
|------|-------|----------|
| **Secret isolation** | 10/10 | Separate stores for MCP vs preflight; no env inheritance |
| **Redaction coverage** | 9/10 | Regex covers GH, AWS, OpenAI, generic patterns |
| **Fail-closed configs** | 10/10 | All parsers return safe empty + error code |
| **Path traversal** | 9/10 | `is_relative_to()` guards, absolute path enforcement |
| **MCP gating** | 10/10 | DEFAULT_DISABLED, credential validation, executable check |
| **Redirect refusal** | 10/10 | Custom HTTP handler blocks redirects |
| **Atomic writes** | 9/10 | Tempfile + os.replace + timestamped backups |
| **Input size limits** | 9/10 | 2MB stdin, 1MB config, 64KB model.json |
| **Deadline enforcement** | 9/10 | Monotonic, shared, late-discard |
| **Supply chain** | 6/10 | Pinned vendors, deny.toml, but no SBOM, no auto-update |
| **Vendored verification** | 7/10 | task-observer has SHA256; others only manifest-level |
| **Least privilege agents** | 4/10 | ~40% agents use `tools: "*"` (per ECC_CORE_AUDIT) |
| **Hook bootstrap duplication** | 3/10 | 5,600+ lines duplicated inline in hooks.json (ECC_CORE_AUDIT) |

---

## 8. Critical Findings

### C-01: Hook Bootstrap Code Duplication (ECC/hooks/hooks.json)
**Severity:** HIGH  
**Issue:** 280+ lines of Node bootstrap code duplicated across 20+ hook entries  
**Risk:** Attack surface (CLAUDE_PLUGIN_ROOT resolution runs every hook), maintenance nightmare, no integrity verification  
**Fix:** Extract to shared module (`run-with-flags.js` pattern exists but not applied consistently)

### C-02: Overprivileged Agents
**Severity:** HIGH  
**Issue:** ~40% of ECC agents declare `tools: "*"`  
**Risk:** Violates least privilege; compromised agent = full tool access  
**Fix:** Audit each agent, declare explicit tool lists

### C-03: No SBOM / Dependency Scanning
**Severity:** MEDIUM  
**Issue:** No automated supply chain monitoring for Python/Node/Rust deps  
**Risk:** Vulnerable transitive dependencies undetected  
**Fix:** Add `pip-audit`, `npm audit`, `cargo deny` to CI

### C-04: Model.json Key Resolver — Keyring Optional
**Severity:** LOW  
**Issue:** `keyring` import wrapped in try/except; absence silent  
**Risk:** Falls back to file/env; not a vulnerability but reduces security posture  
**Fix:** Document keyring as recommended; consider making it required for Mode 2

---

## 9. Recommendations

### P0 — Immediate
1. **Refactor hooks.json** — Extract bootstrap to shared module, add integrity hashes
2. **Least privilege agents** — Replace `tools: "*"` with explicit lists
3. **Add supply chain scanning** — `pip-audit`, `npm audit`, `cargo deny` in CI

### P1 — Hardening
4. **SBOM generation** — CycloneDX/SPDX for all components
5. **Vendored SHA256 manifests** — Extend `VENDORED.json` pattern to all vendored plugins
6. **Pin Python dependencies** — Exact versions in requirements.txt + hash verification

### P2 — Monitoring
7. **Secret scanning in CI** — `gitleaks`/`trufflehog` on every push
8. **Dependency update bot** — Renovate/Dependabot for all ecosystems
9. **Audit log for config changes** — Track ui.api.json, model.json modifications

### P3 — Architecture
10. **Capability-based agent permissions** — Fine-grained tool access per agent
11. **Zero-trust MCP gateway** — Per-request credential validation, audit logging
12. **Formal threat model** — STRIDE analysis for the full architecture
