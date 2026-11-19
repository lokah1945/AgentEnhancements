# Architectural Decisions — Deep Audit

**Purpose:** Document key design choices with rationale, trade-offs, and alternatives considered

---

## 1. Unified Registry as Single Source of Truth

### Decision
All capabilities (skills, plugins, MCPs, built-ins) aggregated into one registry (`agent-registry.json`) with unified search/map/show interface.

### Rationale
- **Discovery unity:** Agents query one tool instead of N sources
- **Scoring consistency:** Single algorithm ranks across types
- **Budget control:** Token budgets applied at registry level
- **Readiness validation:** Live checks per entry type in one place

### Trade-offs
| Pro | Con |
|-----|-----|
| Single query surface | Large aggregated JSON (2.7MB, 594K tokens) |
| Cross-type ranking | Build step required (not fully dynamic) |
| Unified budgets | Staleness between build and runtime |
| Consistent contracts | Three-layer catalog (ECC + unified + plugin-catalog) |

### Alternatives Considered
- **Per-source query tools** — Rejected: fragments agent context, duplicates budget logic
- **Embedding-based search** — Rejected: non-deterministic, harder to debug, no bilingual support
- **GraphQL federation** — Rejected: overkill for CLI-first architecture

---

## 2. Adaptive Preflight Three-Mode Design (CONTRACT 8.5)

### Decision
Three distinct modes with explicit fallback chain: Mode 0 (legacy) → Mode 1 (host-native) → Mode 2 (custom model). **Mode 1 never auto-fallbacks to Mode 2.**

### Rationale
- **User sovereignty:** Model source follows explicit choice
- **Progressive enhancement:** Mode 0 works everywhere; Modes 1/2 add value where supported
- **Fail-closed:** Every failure → Mode 0 with diagnosis
- **Latency budget:** 2s deadline shared across all phases

### Mode 1 vs Mode 2 Separation
| Aspect | Mode 1 (Native) | Mode 2 (Custom) |
|--------|-----------------|-----------------|
| Model source | Host's sanctioned inference | User-configured endpoint |
| Credentials | Host-managed | User keyring/env/file |
| Isolation | Host-enforced | AE-enforced (no SDK retries) |
| Fallback | → Mode 0 only | → Mode 0 only |

### Why Not Auto-Fallback 1→2?
- Prevents silent credential/model switching
- Host native selection may have different capabilities/privacy
- User explicitly chose Mode 1; overriding violates intent

### Alternatives Considered
- **Single mode with provider priority** — Rejected: obscures trust boundaries
- **Mode 2 as default** — Rejected: requires credentials, breaks air-gapped
- **Mode 1 → 2 fallback on timeout** — Rejected: violates explicit choice principle

---

## 3. Gateway MCP Pattern (Single Stable Gateway)

### Decision
One MCP server (`agent-enhancements`) gates all backend MCPs. Backend servers registered in `ui.api.json`; gateway validates visibility, injects env, publishes tools.

### Rationale
- **Credential isolation:** Backend credentials never exposed to model
- **Tool approval preservation:** User's per-tool approvals respected
- **Visibility gating:** `DEFAULT_DISABLED` + credential checks before publish
- **Single connection:** Host manages one stdio connection
- **Hot reload:** Gateway re-reads config on each `tools/list` / `tools/call`

### Trade-offs
| Pro | Con |
|-----|-----|
| Centralized security | Extra hop for every tool call |
| Credential rotation without restart | Gateway becomes SPOF |
| Unified tool schema namespace | Added complexity vs direct MCP |
| Host approval preservation | Gateway must stay in sync with backends |

### Why Not Direct MCP Connections?
- Model would see raw credentials in tool definitions
- No centralized visibility gating
- Each harness would need custom MCP management
- Credential rotation requires agent restart

---

## 4. Skill Loading: Opt-In Only (No Auto-Load)

### Decision
Hooks suggest skills; `Skill` tool must be explicitly invoked to load SKILL.md. No automatic skill activation.

### Rationale
- **User control:** Agent doesn't load unexpected instructions
- **Context budget:** Only loaded skills consume tokens
- **Security:** Untrusted skill content not auto-executed
- **Determinism:** Same prompt → same available skills

### Trade-offs
| Pro | Con |
|-----|-----|
| Explicit capability selection | Higher friction (extra step) |
| Predictable context usage | Discovery → load → use = 3 steps |
| Skill content sandboxed | Novice users may not know to load |

### Alternatives Considered
- **Auto-load top-N suggestions** — Rejected: context explosion, surprise behavior
- **Keyword-triggered auto-load** — Rejected: false positives, security risk
- **Harness-native skill discovery** — Partial: `link-skills.sh` enables native discovery for default sources

---

## 5. Native Workflow Tool vs Hand-Rolled Orchestration

### Decision
Two orchestration layers coexist:
- **Native `Workflow` tool** — Background, deterministic, resumable, structured output
- **Hand-rolled `orch-pipeline`** — Main conversation, interactive gates, human-in-the-loop

Only `orch-review` (Phase 5) ported to native so far.

### Rationale
- **Gates need human approval** — Native workflows can't pause for interactive consent
- **Incremental migration** — Port highest-value phase first (review = most parallelizable)
- **Background vs foreground** — Native = fire-and-forget; hand-rolled = interactive

### Trade-offs
| Native Workflow | Hand-Rolled Pipeline |
|-----------------|---------------------|
| Background execution | Main conversation |
| Deterministic, resumable | Human gates (Gate 1, Gate 2) |
| Structured output validation | Free-form agent output |
| Concurrency capped | Unbounded parallelism |
| No interactive pauses | Full interactive control |

### Migration Strategy (Documented)
1. ✅ Phase 5: Review → `orch-review` (native)
2. 🔄 Phase 1: Research → multi-modal sweep (native)
3. 🔄 Phase 2: Plan → judge panel (native)
4. 🔄 Phase 3: Implement → subagents (native)
5. ⏳ Phase 4: Gate 1 (stays in main)
6. ⏳ Phase 6: Gate 2 → commit (stays in main)

---

## 6. Context Budget Contract (CONTRACT.md §8.4)

### Decision
Hard token limits per channel, enforced by `context_budget.clamp_to_budget()` with explicit truncation notes. All channels registered in `COLD_START_CHANNELS`.

### Limits (Measured via tiktoken o200k_base)
| Channel | Limit | Enforcement |
|---------|-------|-------------|
| `MAX_BOOTSTRAP` | 1,000 | L0 map read |
| `MAX_COLD_START_TOTAL` | 4,000 | Sum of all channels |
| `MAX_MEMORY_RECALL` | 600 | SessionStart recall |
| `MAX_OBSERVER_AMBIENT` | 250 | Task observer bootstrap |
| `MAX_SKILL_CARDS` | 400 | UserPromptSubmit candidates |
| `MAX_SEARCH_PAGE` | 800 | Registry search (5 cards) |
| `MAX_DETAIL_PAGE` | 1,200 | Registry show (with paging) |
| `MAX_NATIVE_DESCRIPTION_TOTAL` | 2,500 | Linked skill descriptions |
| `MAX_TOOL_SCHEMA_TOTAL` | 1,800 | AE MCP tool schemas |

### Why Not Soft Limits?
- **Predictability:** Hard limits = guaranteed context window fit
- **Explicit truncation:** Notes inform model instead of silent loss
- **Budget allocation:** Forces architectural decisions (what to include)

### Why Character Fallback (4.0 chars/token)?
- Zero-dependency runtime (tiktoken optional)
- Deterministic across environments
- Conservative (overestimates tokens → safer)

---

## 7. Memory: SQLite + TTL (No Vector Store)

### Decision
Local SQLite per agent/project with TTL-based expiry. No embeddings, no semantic search.

### Rationale
- **Zero dependencies:** SQLite in stdlib
- **Privacy:** No data leaves machine
- **Simplicity:** CRUD + TTL = 200 lines
- **Determinism:** Exact key lookup, no approximate results

### Trade-offs
| Pro | Con |
|-----|-----|
| No external deps | No semantic recall |
| Fast exact lookup | Manual key management |
| TTL auto-cleanup | No cross-project sharing |
| 0600 perms | No encryption at rest |

### Why Not Vector Memory?
- Adds heavy deps (sentence-transformers, FAISS, etc.)
- Semantic search quality varies; exact keys more reliable for agent memories
- Privacy/latency concerns with cloud embeddings
- Can be added later as optional capability

---

## 8. Plugin Catalog: Curated External + Vendored

### Decision
Two-tier plugin system:
1. **Curated plugins (40)** — `catalog.json` with manifests, guides, MCP refs
2. **Vendored plugins (16)** — Bundled in `plugin-catalog/` (replica, anthropic, 14 agency)

### Rationale
- **Curated:** Upstream maintained, versioned, user opts in
- **Vendored:** Guaranteed availability, pinned versions, no network at install
- **Unified registry** abstracts the difference

### Vendoring Criteria (Implicit)
- Critical for core workflows (task-observer, replica-skill)
- Upstream unstable/unmaintained (anthropic-skills)
- Large persona collections (agency-agents = 273 personas)

### Trade-offs
| Curated | Vendored |
|---------|----------|
| Always fresh | Pinned version |
| Network at install | Zero network |
| User chooses version | Maintainer chooses |
| Smaller repo | Larger repo |

---

## 9. Configuration: XDG + Atomic Writes

### Decision
- User config: `$XDG_CONFIG_HOME/agentenhancements/` (fallback `~/.config/`)
- Project config: `ui.api.json` at repo root (private, 0600)
- Atomic writes via tempfile + `os.replace` + timestamped backups
- Marked blocks in instruction files (`<!-- agent-enhancements:begin/end -->`)

### Rationale
- **XDG compliance:** Standard Linux config location
- **Project isolation:** `ui.api.json` per-checkout, not global
- **Atomicity:** No partial writes, easy rollback
- **User preservation:** Marked blocks preserve personal instructions

---

## 10. Secret Resolution: Layered (Env → Keyring → File)

### Decision
Mode 2 API keys resolved in priority order:
1. `AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY` (env)
2. OS keyring (`agentenhancements.preflight`, account=origin)
3. `~/.config/agentenhancements/preflight.key` (0600)

**Never:** `ui.api.json`, `model.json`, process env inheritance

### Rationale
- **Origin binding:** Keyring account = endpoint origin (prevents cross-use)
- **No plaintext in config:** `model.json` is commit-safe
- **Defense in depth:** Multiple secure stores
- **OS integration:** Keyring uses platform secure storage (libsecret, Keychain, Credential Manager)

---

## 11. Redaction: Regex-Based (Not Semantic)

### Decision
Single regex pattern matching known secret formats + generic `key=value` patterns.

### Rationale
- **Zero dependencies:** No ML, no external service
- **Deterministic:** Same input → same output
- **Fast:** Single pass over text
- **Extensible:** Pattern list in one place

### Limitations
- ❌ Misses novel secret formats
- ❌ False positives on `api_key` in docs/examples
- ❌ No context awareness (can't distinguish "my api_key is X" vs "example: api_key=Y")

### Why Not Semantic/ML?
- Adds heavy deps
- Non-deterministic
- False sense of security (adversarial examples exist)
- Regex catches 95%+ of real leaks in practice

---

## 12. Agent Tool Privileges: Explicit Lists (Aspirational)

### Current State
~40% of ECC agents declare `tools: "*"` (all tools)

### Target Architecture
Each agent declares explicit tool list:
```yaml
tools: [Read, Write, Edit, Bash, Grep, Glob, Task, WebFetch, WebSearch]
```

### Rationale for Explicit Lists
- **Least privilege:** Compromised agent = limited blast radius
- **Auditability:** Clear what each agent can do
- **Harness enforcement:** Some harnesses respect tool lists

### Why Not Enforced Yet?
- Migration effort (71 agents × ~10 tools each)
- Some agents genuinely need dynamic tool access (orchestrators)
- Harness support varies (Claude Code respects; others may not)

---

## 13. Hook Bootstrap: Shared Module (Not Inlined)

### Current Problem
`ECC/hooks/hooks.json` duplicates 280-line Node bootstrap in 20+ hook entries

### Target Architecture
```json
"command": "node scripts/hooks/run-with-flags.js pre:bash:dispatcher scripts/hooks/pre-bash-dispatcher.js"
```

### Rationale
- **DRY:** Single bootstrap implementation
- **Security:** Integrity hash on bootstrap module
- **Performance:** Avoids re-evaluating 280 lines per hook fire
- **Maintainability:** One place to update

### Blockers
- Requires all harness installers to deploy `run-with-flags.js`
- Hermes/Codex/OpenCode hook formats differ slightly
- Legacy hook entries need migration

---

## 14. ECC2 Rust: Monolith → Modular (In Progress)

### Current State
`ECC/ecc2/src/main.rs` = 459KB (~15K lines) single file

### Target
Modular crate structure:
```
ecc2/
├── Cargo.toml (workspace)
├── crates/
│   ├── ecc-core/
│   ├── ecc-config/
│   ├── ecc-runtime/
│   ├── ecc-hooks/
│   ├── ecc-mcp/
│   └── ecc-cli/
└── src/main.rs (thin entry point)
```

### Rationale
- **Reviewability:** 15K lines unreviewable
- **Testability:** Unit tests per crate
- **Compilation:** Incremental builds
- **Team scaling:** Ownership per crate

### Blocker
- Massive refactor; risk of behavioral changes
- No tests for current monolith behavior
- Needs `ecc2/` test suite first

---

## 15. Decision Registry

| ID | Decision | Status | Owner | Revisit |
|----|----------|--------|-------|---------|
| AD-001 | Unified registry as single source | ✅ Implemented | AE Core | — |
| AD-002 | Three-mode adaptive preflight | ✅ Implemented | AE Core | — |
| AD-003 | Gateway MCP pattern | ✅ Implemented | AE Core | — |
| AD-004 | Opt-in skill loading | ✅ Implemented | AE Core | — |
| AD-005 | Native workflow for review only | 🔄 Partial | ECC Core | 2026-Q2 |
| AD-006 | Hard context budgets | ✅ Implemented | AE Core | — |
| AD-007 | SQLite memory (no vector) | ✅ Implemented | AE Core | 2026-Q3 |
| AD-008 | Curated + vendored plugins | ✅ Implemented | AE Core | — |
| AD-009 | XDG config + atomic writes | ✅ Implemented | AE Core | — |
| AD-010 | Layered secret resolution | ✅ Implemented | AE Core | — |
| AD-011 | Regex redaction | ✅ Implemented | AE Core | 2026-Q2 |
| AD-012 | Explicit agent tool lists | 🔄 Partial | ECC Core | 2026-Q1 |
| AD-013 | Shared hook bootstrap module | ❌ Pending | ECC Core | 2026-Q1 |
| AD-014 | ECC2 modular Rust | 🔄 In Progress | ECC Core | 2026-Q2 |
| AD-015 | Skill versioning | ❌ Pending | AE Core | 2026-Q2 |
| AD-016 | Skill dependency graph | ❌ Pending | AE Core | 2026-Q3 |
