# Security & Configuration Audit Report

**Date:** 2026-11-21
**Scope:** AgentEnhancements Unified Integration Layer
**Reference:** Master Prompt §5 (Threat Modeling, Supply Chain, etc.) & §4 (Contract, Configuration)

---

## Executive Summary

| Category | P0 | P1 | P2 | P3 | Total |
|----------|----|----|----|----|-------|
| Threat Modeling | 1 | 4 | 2 | 1 | 8 |
| Supply Chain | 0 | 2 | 3 | 2 | 7 |
| Checkout-Local State | 0 | 1 | 2 | 1 | 4 |
| Setup/Update Safety | 0 | 2 | 1 | 1 | 4 |
| Gateway Security | 1 | 3 | 2 | 0 | 6 |
| Memory/Observer/Compression | 0 | 1 | 3 | 2 | 6 |
| Registry/Skill Counts | 0 | 1 | 2 | 1 | 4 |
| Documentation/Drift | 0 | 2 | 2 | 2 | 6 |
| **TOTAL** | **2** | **16** | **17** | **10** | **45** |

---

## 1. THREAT MODELING

### P0: Hardcoded Preflight API Key in Committed ui.api.json
- **File:** `ui.api.json:15`
- **Root Cause:** The preflight section contained a live OpenRouter API key that was committed to the repository. The credential has been rotated.
- **Reproduction:** `cat ui.api.json | grep -A5 preflight`
- **User Impact:** API key exposed in git history; any clone or fork inherits the credential. Key rotation required immediately.
- **Severity:** P0 (secret leakage in committed config)

### P1: Secret Pattern in Preflight Configuration Leaks to Gateway Health
- **File:** `unified-integration/mcp-servers/gateway.py:464-475`
- **Root Cause:** The `_run_health()` method redacts payloads but only for known provenance fields. The preflight API key (`api_key_ref`) could leak via external MCP health responses that echo environment values.
- **Reproduction:** Configure vision-mcp with OPENAI_API_KEY, call ae_health, observe response.
- **User Impact:** Credential exposure in health check responses.

### P1: External MCP Subprocess Receives All Configured Env Refs
- **File:** `unified-integration/mcp-servers/gateway.py:165-168`
- **Root Cause:** `External.run()` iterates all `settings.env` entries and resolves each via `value(ref, config)`. A compromised or malicious external MCP receives every reference configured for it, not just required ones.
- **Reproduction:** Configure an external MCP with 5 env refs; all 5 resolved and passed.
- **User Impact:** Over-privileged credential forwarding to external processes.

### P1: No Input Sanitization on Skill Frontmatter Fields Used as Paths
- **File:** `unified-integration/setup.sh:568-576, 652-655`
- **Root Cause:** Skill `name` from frontmatter used directly in filesystem paths (`by-category/$category/$name`). Sanitization only replaces `/` with `-` and blocks `.` and `..`. No validation against path traversal via other chars (e.g., `\`, null bytes, Unicode tricks).
- **Reproduction:** Create skill with name `test\0name` or `subdir/../escape`.
- **User Impact:** Potential path escape during skill aggregation.

### P1: Tool Name/Schema Spoofing in MCP Gateway
- **File:** `unified-integration/mcp-servers/gateway.py:307-371`
- **Root Cause:** `tools()` builds catalog from `self.definitions` (bundled) and `self.externals[].tools` (fetched at startup). A malicious external MCP could advertise tool names colliding with built-ins (e.g., `search-mcp_web`). The gateway prefixes with `public_name()` but collision on prefix+hash possible.
- **Reproduction:** External MCP returns tool named `search-mcp_web`; gateway produces `search_mcp_web_<hash>` which may match legitimate tool.
- **User Impact:** Tool impersonation, credential misrouting.

### P2: Symlink Attack in link-skills.sh
- **File:** `unified-integration/scripts/link-skills.sh:124-142`
- **Root Cause:** `link_skill()` checks if existing destination is a symlink pointing to `$SKILLS_DIR/*` or previous checkout. However, a pre-existing symlink at target could point to arbitrary location. The check `case "$current" in "$SKILLS_DIR"/*)` only validates after the fact; `ln -sfn` will overwrite.
- **Reputation:** Mitigated by warning on non-symlink, but race condition exists.
- **User Impact:** Symlink overwrite could redirect skill loads.

### P2: Path Traversal in Skill Registry Resolution
- **File:** `unified-integration/scripts/load-skills.py:2082-2094`
- **Root Cause:** `skill_path()` resolves skill name against `by-category/*/$name/SKILL.md` and `by-agent/$agent/$name/SKILL.md`. Validation: `Path(skill_name).name != skill_name` blocks path separators but not Unicode normalization or case-folding attacks on case-insensitive FS.
- **Reproduction:** On Windows, skill name `NAME` vs `name` could resolve differently.
- **User Impact:** Potential skill misload on case-insensitive filesystems.

### P3: ui.api.json File Permissions Not Enforced at Read
- **File:** `unified-integration/scripts/api_config.py:102-103, 199-210`
- **Root Cause:** `initialize()` creates file with `0o600` but `read_config()` does not verify permissions on read. A world-readable ui.api.json would be read without warning.
- **Reproduction:** `chmod 644 ui.api.json && python3 -c "from api_config import read_config; print(read_config())"`
- **User Impact:** Silent credential exposure if permissions relaxed.

---

## 2. SUPPLY CHAIN

### P1: No Automated Vulnerability Scanning in CI
- **File:** `.github/workflows/` (missing), `unified-integration/setup.sh`
- **Root Cause:** No `cargo audit`, `pip-audit`, `npm audit` or equivalent in CI pipeline. Dependencies pinned in `Cargo.toml` and `requirements.txt` but no scheduled scan.
- **Reproduction:** Check CI config for vulnerability scanning steps.
- **User Impact:** Vulnerable transitive deploys undetected.

### P1: setup.sh Clones Unpinned Repository for Piped Installs
- **File:** `unified-integration/setup.sh:11-38`
- **Root Cause:** The one-liner install path clones `https://github.com/lokah1945/AgentEnhancements.git` without pinning to a specific commit/tag unless `AGENT_ENHANCEMENTS_REF` is set. The comment acknowledges this (AE-11) but the default remains unpinned.
- **Reproduction:** `curl -fsSL https://.../setup.sh | bash` on fresh machine.
- **User Impact:** Supply chain attack via compromised upstream repo.

### P2: headroom Binary Build is Optional Fallback, Not Verified
- **File:** `unified-integration/setup.sh:1369-1396`
- **Root Cause:** `setup_compression()` builds headroom from source if `Cargo.toml` exists and `AGENT_ENHANCEMENTS_BUILD_HEADROOM=1`. No checksum verification of built binary. If cargo or dependencies compromised, malicious binary installed.
- **Reproduction:** Run setup with `AGENT_ENHANCEMENTS_BUILD_HEADROOM=1` on compromised cargo registry.
- **User Impact:** Unverified native code execution.

### P2: npx -y Used in MCP Server Configurations
- **File:** `ui.api.json:140-142, 423-426`
- **Root Cause:** `neo4j-mcp` and `agent-browser-mcp` use `npx -y @alanse/mcp-neo4j-server` and `node mcp-servers/agent_browser/src/index.js` without version pinning. `npx -y` downloads and executes latest version automatically.
- **Reproduction:** Configure these MCPs, observe npx execution.
- **User Impact:** Unpinned supply chain for external MCP servers.

### P2: Malformed YAML in Config Merge Causes Silent Skip
- **File:** `unified-integration/setup.sh:1590-1647`
- **Root Cause:** `merge_yaml_config()` catches PyYAML import errors and parse errors, logs warning, and returns without merging. No failure mode; user config left unmerged.
- **Reproduction:** Create invalid YAML in target config, run setup.
- **User Impact:** Silent configuration drift.

### P3: Cargo.lock Not Committed for headroom
- **File:** `headroom/Cargo.toml` (no Cargo.lock in repo root)
- **Root Cause:** headroom workspace uses `cargo build --locked` in setup.sh but `Cargo.lock` is not committed in the repository (it's in headroom/ but not tracked by git at repo root).
- **Reproduction:** Check git status for Cargo.lock.
- **User Impact:** Non-reproducible builds across machines.

### P3: Plugin Catalog License Verification Incomplete
- **File:** `docs/LICENSE_AUDIT.md:127-240`
- **Root Cause:** 22 external plugin catalog entries have "assumed" licenses with "TODO verify" status. Only 3 are verified.
- **Reproduction:** Review LICENSE_AUDIT.md Part B.
- **User Impact:** Potential license compliance issues if plugins vendored.

---

## 3. CHECKOUT-LOCAL STATE (Section 8.6)

### P1: AGENT_ENHANCEMENTS_STATE_DIR Override Not Validated for Symlinks
- **File:** `unified-integration/scripts/project_paths.py:14-19, 35-44`
- **Root Cause:** `state_root()` expands user path but does not verify it's not a symlink before use. `prepare()` checks for symlinks on created paths but the override itself could be a symlink.
- **Reproduction:** `ln -s /tmp/evil ~/.agentenhancements && AGENT_ENHANCEMENTS_STATE_DIR=~/.agentenhancements setup.sh`
- **User Impact:** State directory escape via symlink.

### P2: Memory Database Path Not Validated Against Symlinks at Open
- **File:** `unified-integration/scripts/memory.py:35-43`
- **Root Cause:** `_init_db()` uses `O_NOFOLLOW` when opening DB file but the parent directory (`MEMORY_ROOT`) could be a symlink. The check at line 30-31 only validates the root path at creation time.
- **Reproduction:** Replace `.agentenhancements/memory` with symlink after setup.
- **User Impact:** SQLite writes redirected outside checkout.

### P2: Cache Directories Created Without O_NOFOLLOW
- **File:** `unified-integration/scripts/project_paths.py:62-90`
- **Root Cause:** `environment()` sets `XDG_CACHE_HOME`, `UV_CACHE_DIR`, etc. to subdirectories of `.agentenhancements/cache` but `prepare()` creates cache with `mkdir -p` without symlink check.
- **Reproduction:** Symlink `.agentenhancements/cache` to `/tmp`, run setup.
- **User Impact:** Cache pollution outside checkout boundary.

### P3: No Cross-Project Isolation for Concurrent Checkouts
- **File:** `unified-integration/scripts/project_paths.py:14-19`
- **Root Cause:** `AGENT_ENHANCEMENTS_STATE_DIR` defaults to `ROOT / '.agentenhancements'` where ROOT is the script's grandparent. Two checkouts in different directories get separate state, but if `AGENT_ENHANCEMENTS_BASE_DIR` is overridden to same value, they share state.
- **Reproduction:** Two projects, same `AGENT_ENHANCEMENTS_BASE_DIR`, run setup in both.
- **User Impact:** Memory/config collision between projects.

---

## 4. SETUP/UPDATE SAFETY

### P1: Idempotent Setup Not Fully Verified for Config Merge
- **File:** `unified-integration/setup.sh:1579-1647`
- **Root Cause:** `merge_yaml_config()` compares canonical YAML dump before/after but `yaml.safe_dump(existing, sort_keys=True) == before` may be false positive when only comment/formatting differs. Backup created only when merged != original, but semantic equivalence not guaranteed.
- **Reproduction:** Run setup twice, observe backup creation on second run.
- **User Impact:** Unnecessary backup accumulation; potential config drift.

### P1: Migration v1->v2 Creates Backup but No Rollback on Failure
- **File:** `unified-integration/scripts/api_config.py:485-495`
- **Root Cause:** `migrate()` writes backup then atomic replace. If `_write_private_atomic()` fails on the new file, the backup exists but no automatic rollback to original. User must manually restore.
- **Reproduction:** Make ui.api.json unwritable, run migrate.
- **User Impact:** Partial migration leaves config in inconsistent state.

### P2: YAML Serialization Idempotence Failures Noted
- **File:** `unified-integration/setup.sh:1590-1647`, `test_hooks.py` (referenced in task)
- **Root Cause:** `merge_yaml_config()` uses `yaml.dump(existing, default_flow_style=False, sort_keys=False)` which may produce different output on each run for same logical content (key order, quoting). The comparison `yaml.safe_dump(existing, sort_keys=True) == before` uses `sort_keys=True` but the actual write uses `sort_keys=False`.
- **Reproduction:** Run setup twice on same config, compare outputs.
- **User Impact:** Config file churn on every setup run.

### P3: setup.sh Does Not Validate Git State Before Pull
- **File:** `unified-integration/setup.sh:22-35`
- **Root Cause:** The piped install path does `git pull --ff-only` but does not check for uncommitted changes, staged changes, or detached HEAD before pulling. Could fail or merge unexpectedly.
- **Reproduction:** Modify file in existing checkout, run piped install.
- **User Impact:** Unexpected merge conflicts or data loss.

---

## 5. GATEWAY SECURITY (gateway.py)

### P0: Credential Rotation Does Not Invalidate In-Flight Requests
- **File:** `unified-integration/mcp-servers/gateway.py:237-242, 558-568`
- **Root Cause:** `External.stop()` cancels the worker task but in-flight requests in `self.pending` are resolved with error. However, `call_tool()` at line 558-568 checks `value(ref, config) != value(ref, worker.config)` **after** the call is queued. A request already in the queue when credentials rotate will execute with old credentials.
- **Reproduction:** Start long-running external MCP call, rotate credentials in ui.api.json, observe call completes with old key.
- **User Impact:** Credential rotation not immediate; stale credentials used.

### P1: Dynamic Tool Visibility Without Schema Revalidation on Every Call
- **File:** `unified-integration/mcp-servers/gateway.py:307-371, 501-518`
- **Root Cause:** `tools(config)` rebuilds catalog on every `list_tools()` call, but `call_tool()` calls `tools(config)` again at line 506. The schema validation at line 514 uses the freshly built schema. This is correct, but the `fingerprints` mechanism (line 296) only restarts external workers on config change, not on credential rotation for built-ins.
- **Reproduction:** Remove API key from ui.api.json, call tool immediately; gateway should reject.
- **User Impact:** Brief window where stale tool visibility persists.

### P1: Module Lock Contention on Blocking Built-in Tools
- **File:** `unified-integration/mcp-servers/gateway.py:253, 523-528`
- **Root Cause:** `module_locks` dict has one lock per built-in server. `call_tool()` acquires lock and runs `asyncio.to_thread(lambda: asyncio.run(...))` which creates a new event loop per call. High concurrency on same built-in serializes all calls.
- **Reproduction:** Concurrent calls to same built-in MCP (e.g., embeddings-mcp).
- **User Impact:** Latency under load; no connection pooling.

### P2: External Process Cleanup on Gateway Shutdown
- **File:** `unified-integration/mcp-servers/gateway.py:607-609`
- **Root Cause:** `lifespan()` cancels watcher and gathers `worker.stop()` for all externals. `External.stop()` cancels task and gathers with `return_exceptions=True`. If worker's `run()` is blocked in `session.call_tool()`, cancellation may not interrupt immediately (depends on MCP SDK).
- **Reproduction:** Kill gateway process during external MCP call.
- **User Impact:** Orphaned external MCP processes.

### P2: No Rate Limiting on External MCP Calls
- **File:** `unified-integration/mcp-servers/gateway.py:140-153, 225-235`
- **Root Cause:** `External` uses unbounded `asyncio.Queue`. No backpressure, no rate limiting, no circuit breaker. A flood of calls to a slow external MCP will queue indefinitely.
- **Reproduction:** Send 1000 concurrent calls to external MCP.
- **User Impact:** Memory exhaustion, unresponsive gateway.

### P3: Task Router MCP Enabled by Default in ui.api.json
- **File:** `ui.api.json:322-326`
- **Root Cause:** `task-router-mcp` has `"enabled": true` in the committed ui.api.json, but `DEFAULT_DISABLED` in api_config.py hides it by default. However, the explicit `"enabled": true` in user config overrides the default, making it visible. The config should not have it enabled by default.
- **Reproduction:** `python3 -c "from api_config import server_state; print(server_state('task-router-mcp'))"`
- **User Impact:** Dangerous arbitrary-code-execution MCP exposed if user doesn't understand implications.

---

## 6. MEMORY/OBSERVER/COMPRESSION

### P1: Memory Hooks Redact but Prompt Not Modified
- **File:** `unified-integration/scripts/runtime.py:31-33, 158-165`
- **Root Cause:** `redact()` uses `api_config.redact` which replaces known secrets. However, `UserPromptSubmit` handler saves `redact(prompt)` to memory but returns `prompt_context()` which may include unredacted skill descriptions from registry. The prompt itself is not modified before reaching the model.
- **Reproduction:** Include API key in prompt, observe memory saves redacted version but model sees original.
- **User Impact:** Secrets in prompt reach model; only memory is protected.

### P2: Observer Workspace Path Not Validated Against Symlinks
- **File:** `unified-integration/scripts/task-observer.py:45-65`
- **Root Cause:** `workspace_root()` uses `TASK_OBSERVER_WORKSPACE` env var or defaults to `memory_root()/task-observer`. No symlink validation on the workspace path itself.
- **Reproduction:** Symlink `.agentenhancements/memory/task-observer` to `/tmp/steal`.
- **User Impact:** Observer logs written outside checkout.

### P2: Headroom Binary Not Actually Used (Fallback Only)
- **File:** `unified-integration/setup.sh:1369-1396`, `unified-integration/scripts/compress.py:2398-2420`
- **Root Cause:** `setup_compression()` builds headroom if Cargo.toml exists and `AGENT_ENHANCEMENTS_BUILD_HEADROOM=1`. `compress.py` checks for binary at `HEADROOM_BIN` env, fallback path, and `shutil.which`. In practice, the binary is rarely built (requires Rust toolchain) so fallback compression is used. The "20% token reduction" claim in universal prompt is not achieved.
- **Reproduction:** Run setup without Rust, check `compress.py` output.
- **User Impact:** Compression effectiveness overstated; fallback is basic deduplication.

### P2: SQLite Concurrency - No WAL Mode or Connection Pooling
- **File:** `unified-integration/scripts/memory.py:44-63, 78-83`
- **Root Cause:** Each `AgentMemory` operation opens new connection with `sqlite3.connect(DB_PATH)`. No WAL mode (`PRAGMA journal_mode=WAL`), no connection pooling. Concurrent access from multiple hooks/agents causes lock contention.
- **Reproduction:** Run multiple `memory.py save` commands concurrently.
- **User Impact:** "Database is locked" errors under concurrent use.

### P3: Memory TTL Cleanup Only on Explicit Call
- **File:** `unified-integration/scripts/memory.py:137-144`
- **Root Cause:** `cleanup_expired()` only called explicitly (e.g., `runtime.py:135` on SessionStart). No background TTL cleanup. Expired rows accumulate until manual cleanup.
- **Reproduction:** Add memory with 1-day TTL, wait 2 days, query without SessionStart.
- **User Impact:** Stale data persists, storage grows unbounded.

### P3: Observer Logs Raw Tool Names Without Redaction
- **File:** `unified-integration/scripts/runtime.py:166-176`
- **Root Cause:** `PreToolUse`/`PostToolUse` save `tool_name` to memory without redaction. Tool names could contain sensitive info (e.g., file paths, command args).
- **Reproduction:** Use tool with sensitive name, check memory.
- **User Impact:** Partial data leakage in observer/memory.

---

## 7. REGISTRY/SKILL COUNTS

### P1: Generation Not Fully Deterministic - Timestamp in Output
- **File:** `unified-integration/scripts/registry.py:650-654, 680-686`
- **Root Cause:** `cmd_build()` includes `"generated_at": datetime.now(timezone.utc).isoformat()` in registry output. Comparison excludes `generated_at` (line 672-673) but the field is still written. If comparison passes, timestamp preserved; if fails, new timestamp written. This is correct per AE-14 audit, but the field exists.
- **Reproduction:** Run `registry.py build` twice, compare outputs.
- **User Impact:** Git diff noise on every regeneration if content changes.

### P2: Search Bias Not Audited for Positive/Negative Balance
- **File:** `unified-integration/scripts/registry.py:139-157, 425-505`
- **Root Cause:** `CARD_MIN_SCORE = 5` and `GENERIC_ACTION_WORDS` filter aim for 90% negative suppression. No test validates this threshold against real queries. Positive bias (showing irrelevant skills) vs negative bias (missing relevant skills) not measured.
- **Reproduction:** Run `registry.py search "write a haiku"` - should return empty (generic action only).
- **User Impact:** Search quality unverified.

### P2: Bilingual ID/EN Search Not Tested for Parity
- **File:** `unified-integration/scripts/registry.py:55-63, 283-287`
- **Root Cause:** `STOP_WORDS` and `LEXICAL_ALIASES` include Indonesian terms. `INTENT_SYNONYM_GROUPS` mix EN/ID. No test validates that Indonesian queries return equivalent results to English.
- **Reproduction:** Compare `registry.py search "debug"` vs `registry.py search "gagal"`.
- **User Impact:** Non-English users may get degraded search.

### P3: Metadata Minimal at Startup Claim Unverified
- **File:** `unified-integration/scripts/registry.py:390-398`
- **Root Cause:** `usable_entries()` filters MCPs via `api_config.server_state()` which reads full config. Skills index loaded entirely (`all-skills.json` ~3.3k entries). The "metadata minimal at startup" claim refers to lazy detail loading, but the index is fully loaded.
- **Reproduction:** Profile memory/startup time of `registry.py search`.
- **User Impact:** Startup latency higher than claimed.

---

## 8. DOCUMENTATION/DRIFT

### P1: Host Parity Claims vs Evidence Mismatch
- **File:** `README.md`, `docs/AGENTS.md`, `AuditReport/host-runtime-integration-audit.md`
- **Root Cause:** Documentation claims "Compatible with: Claude Code, Codex, Cursor, Gemini CLI, Copilot, Windsurf, Kiro, OpenCode" (README:318-320) but audit shows only 4/9 hosts have native activation (Claude Code, Codex, OpenCode, Hermes). 5 hosts are "DOCUMENTED_ONLY" with no runtime integration.
- **Reproduction:** Compare README claims with `host-runtime-integration-audit.md` table.
- **User Impact:** Misleading feature parity claims.

### P1: 'to-install' MCP Servers Misrepresented as Built
- **File:** `plugin-catalog/mcp-servers.json`, `docs/MCP_SERVERS.md`
- **Root Cause:** MCP roadmap includes servers with `"status": "to-install"` (e.g., many entries). The gateway's `server_state()` for non-built-ins returns `visible: false, reason: "not_configured"` but the catalog doesn't clearly distinguish "built and configured" from "install yourself".
- **Reproduction:** Check `registry.py map` output for MCP servers - shows all as available.
- **User Impact:** User expects working MCP but gets configuration burden.

### P2: Legacy model.json References Not Fully Removed
- **File:** `docs/CONFIGURATION.md`, `docs/ADAPTIVE_PREFLIGHT.md`
- **Root Cause:** CONTRACT §8.6 states "legacy preflight `model.json`/`preflight.key` are imported once into `ui.api.json` and no longer read". However, documentation still references these files as configuration options.
- **Reproduction:** Search docs for `model.json` references.
- **User Impact:** Confusion about active configuration paths.

### P2: Skill Counts in Documentation Drift from Canonical Sources
- **File:** `docs/CAPABILITY_COUNTS.md`, `README.md:285-286`
- **Root Cause:** README claims "3,000+ curated skills" (line 285). `docs/CAPABILITY_COUNTS.md` has specific counts. The actual `all-skills.json` count should be the source of truth. No automated verification that docs match index.
- **Reproduction:** `python3 -c "import json; print(json.load(open('unified-integration/skills/all-skills.json'))['total_skills'])"` vs docs.
- **User Impact:** Stale numbers in documentation.

### P3: CONTRACT Section Placement/Links Accuracy
- **File:** `CONTRACT.md`, `docs/ARCHITECTURE.md`, `docs/API.md`
- **Root Cause:** CONTRACT.md §8.4-8.6 added at end of file (after section 12). Cross-references from other docs may not point to correct sections. Section numbering in CONTRACT.md has gaps (§8.1, 8.2, 8.3, then 12, then 8.4, 8.5, 8.6).
- **Reproduction:** Check internal links in docs.
- **User Impact:** Navigation confusion.

### P3: Path Accuracy in Generated Agent Configs
- **File:** `unified-integration/setup.sh:1649-1676` (create_claude_code_config)
- **Root Cause:** Generated CLAUDE.md references `$BASE_DIR/skills/library-map.json` and `$UNIFIED_DIR/scripts/registry.py`. These variables are expanded at setup time but if the checkout is relocated, the paths in CLAUDE.md become stale.
- **Reproduction:** Move checkout after setup, check `~/.claude/CLAUDE.md` paths.
- **User Impact:** Broken paths in agent instructions after relocation.

---

## Summary of Critical Actions Required

| Priority | Action | Owner |
|----------|--------|-------|
| P0 | **Rotate preflight API key immediately** - committed in ui.api.json | Maintainer |
| P0 | **Fix credential rotation race** in gateway.py External.call() | Developer |
| P1 | **Remove npx -y from MCP configs** or pin versions | Developer |
| P1 | **Add symlink validation** for AGENT_ENHANCEMENTS_STATE_DIR override | Developer |
| P1 | **Document actual host parity** (4/9 native, 5/9 documented-only) | Documentation |
| P1 | **Implement vulnerability scanning** in CI | DevOps |
| P2 | **Enable SQLite WAL mode** for memory DB | Developer |
| P2 | **Fix YAML merge idempotence** in setup.sh | Developer |
| P2 | **Remove enabled: true** for task-router-mcp in committed config | Maintainer |
| P3 | **Add automated doc freshness checks** | Documentation |

---

## Verification Commands

```bash
# Verify preflight key not in git history (after rotation)
git log --all --full-history -- ui.api.json | grep -c "sk-or-v1"

# Check MCP configs for npx -y
grep -r "npx.*-y" unified-integration/config/ ui.api.json

# Verify symlink checks
ls -la .agentenhancements/

# Check host parity claims
grep -n "Compatible with" README.md
python3 unified-integration/scripts/registry.py stats --json | jq '.by_source'

# Verify skill count matches
python3 -c "import json; d=json.load(open('unified-integration/skills/all-skills.json')); print(d['total_skills'])"

# Check for legacy model.json references
grep -r "model\.json" docs/ --include="*.md"
```

---

**Report Generated:** 2026-11-21
**Auditor:** Systematic Security Audit per Master Prompt §5 & §4
**Next Review:** After P0/P1 remediation