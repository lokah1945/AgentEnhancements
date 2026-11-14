# Architecture Overview

**Version**: 2.0  
**Last Updated**: 2026-11-01  
**Audience**: All agents, maintainers

---

## 1. System Context

This project provides a **unified enhancement layer** for AI coding agents. It aggregates skills, memory, compression, and system prompts from multiple upstream sources into a single, agent-neutral interface.

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED INTEGRATION LAYER                    │
├─────────────────────────────────────────────────────────────────┤
│  Skills Registry     │  Memory System      │  Compression      │
│  (all-skills.json)   │  (SQLite + hooks)   │  (headroom)       │
├─────────────────────────────────────────────────────────────────┤
│                    AGENT CONFIG GENERATORS                      │
│  Claude Code | Codex | OpenCode | Cursor | Gemini | Windsurf  │
│  Copilot     | Kiro                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│agentic-awesome│    │     ECC       │    │  Superpowers  │
│   -skills     │    │  (314 skills) │    │  (15 skills)  │
│  (2,791)      │    │               │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGGREGATION PIPELINE                         │
│  1. Parse SKILL.md frontmatter from ALL sources                │
│  2. Normalize categories, tags, tools                          │
│  3. Copy entire skill directories (recursive)                  │
│  4. Generate unified all-skills.json with full metadata        │
│  5. Populate by-category/ and by-agent/ directories            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Skills Registry (`unified-integration/skills/`)

**Source of Truth**: `all-skills.json` - single unified index with:
- All skills from all sources (3,127+)
- Normalized metadata: name, category, description, risk, source, tags, tools, when_to_use
- Category counts, agent skill counts
- ISO 8601 timestamp

**Directory Structure**:
```
skills/
├── all-skills.json              # Canonical index
├── by-category/                 # Category-organized (for browsing)
│   ├── security/
│   ├── architecture/
│   ├── testing/
│   ├── refactoring/
│   ├── code-review/
│   ├── documentation/
│   ├── devops/
│   ├── ai-ml/
│   ├── productivity/
│   └── general/
└── by-agent/                    # Agent-organized (for auto-loading)
    ├── claude-code/
    ├── codex/
    ├── cursor/
    ├── gemini-cli/
    ├── opencode/
    ├── copilot/
    ├── windsurf/
    └── kiro/
```

**Key Invariant**: Every skill directory contains the COMPLETE skill (SKILL.md + references/ + scripts/ + any supporting files).

### 2.2 Memory System (`unified-integration/memory/`)

**Backend**: SQLite (`~/.agent-memory/memory.db`)
**Schema**:
```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    project TEXT,
    memory_type TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata TEXT,
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(agent, project, memory_type, key)
);
```

**Memory Types**:
| Type | TTL | Scope | Purpose |
|------|-----|-------|---------|
| project_context | 365d | project | Architecture decisions, conventions |
| user_preferences | 730d | global | Coding style, patterns |
| code_patterns | 365d | project | Discovered patterns, anti-patterns |
| session_context | 7d | session | Active tasks, recent decisions |
| skill_knowledge | 180d | global | Skill usage effectiveness |

**Hook Interface** (Python canonical, Bash wrapper):
```python
# Save
memory.save(key, value, memory_type="session_context", ttl_days=30)

# Load
value = memory.load(key, memory_type="session_context")

# List
memories = memory.list(memory_type="project_context", limit=20)
```

### 2.3 Compression System (`unified-integration/compression/`)

**Primary Engine**: headroom (Rust, built from source)
**Fallback**: Native Python algorithms

**Modes**:
| Mode | Use Case | Ratio |
|------|----------|-------|
| smart | Code (preserve structure) | ~20% |
| aggressive | Logs | 60-95% |
| schema | JSON (schema-aware) | 50-80% |
| semantic | Markdown | 30-50% |
| balanced | Generic | 40-60% |

**Agent Budgets**:
| Agent | Budget | Trigger |
|-------|--------|---------|
| claude-code | 200,000 | 75% |
| gemini-cli | 1,000,000 | 75% |
| codex/cursor/windsurf/kiro | 128,000 | 75% |
| opencode | 100,000 | 75% |
| copilot | 32,000 | 75% |

### 2.4 System Prompts (`unified-integration/prompts/`)

**Universal Prompt**: `universal-system-prompt.txt` - works for all agents
**Agent-Specific**: `*-system-prompt.txt` - optimized per agent
**Discovery**: Flexible glob patterns from `system-prompts-and-models-of-ai-tools/`

---

## 3. Data Flow

### 3.1 Initial Setup
```
setup.sh
    │
    ├─► detect_agents() → config/detected-agents.sh
    │
    ├─► setup_prompts() → prompts/*-system-prompt.txt
    │
    ├─► aggregate_skills() → skills/all-skills.json + by-category/ + by-agent/
    │       │
    │       ├─► Parse agentic-awesome-skills/skills/
    │       ├─► Parse ECC/skills/
    │       ├─► Parse ponytail/skills/
    │       └─► Parse superpowers/skills/
    │
    ├─► setup_memory() → memory/config.yaml + hooks/*.py + init-memory.sh
    │
    ├─► setup_compression() → compression/config.yaml + compress.sh
    │
    ├─► create_agent_configs() → ~/.claude/, ~/.codex/, etc.
    │
    ├─► create_launcher() → launch-agent.sh
    │
    ├─► create_skills_loader() → scripts/load-skills.py
    │
    ├─► create_memory_util() → scripts/memory.py
    │
    └─► create_compression_util() → scripts/compress.py
```

### 3.2 Runtime (Agent Launch)
```
launch-agent.sh <agent>
    │
    ├─► Load detected-agents.sh
    │
    ├─► Run init-memory.sh
    │
    ├─► Export env vars:
    │       AGENT_MEMORY_ROOT
    │       AGENT_SKILLS_DIR
    │       AGENT_COMPRESSION_CONFIG
    │       AGENT_PROMPTS_DIR
    │
    └─► exec <agent> [args...]
```

### 3.3 Skill Loading (During Agent Session)
```
Agent encounters task
    │
    ├─► Match keywords to skill "when_to_use" / tags / description
    │
    ├─► Filter by agent compatibility (tools array)
    │
    ├─► Load SKILL.md from by-agent/<agent>/ or by-category/
    │
    └─► Apply skill patterns/procedures
```

### 3.4 Memory Persistence (Hooks)
```
PreToolUse / PostToolUse / Stop
    │
    ├─► Hook script called with tool name + input/result
    │
    ├─► Python hook: parameterized SQL → SQLite
    │
    └─► Next session: load relevant memories at start
```

---

## 4. Extension Points

### 4.1 Adding New Skill Source
1. Add source directory to `BASE_DIR` (git clone or submodule)
2. Update `aggregate_skills()` in `setup.sh`:
   ```bash
   process_skills_source "NewSource" "$BASE_DIR/new-source/skills"
   ```
3. Add to `sources` array in unified index generation
4. Run `update-skills.sh` → `setup.sh`

### 4.2 Adding New Agent
1. Add to `AGENT_LIST` in `setup.sh`
2. Add detection in `detect_agents()`
3. Add config generator `create_<agent>_config()`
4. Add to launcher `case` statement
5. Add to memory hook generation loop
6. Add budget in compression config
7. Update `docs/AGENTS.md`

### 4.3 Adding Memory Type
1. Add to `memory/config.yaml` types list
2. Update Python hook if special handling needed
3. Update `docs/CONFIGURATION.md`

### 4.4 Adding Compression Mode
1. Add to `compression/config.yaml` headroom.modes
2. Update `compress.sh` detection logic
3. Update Python fallback in `scripts/compress.py`
4. Update `docs/CONFIGURATION.md`

---

## 5. Security Boundaries

### 5.1 Memory Isolation
- Each agent has separate namespace in SQLite (agent column)
- Project-scoped memories isolated by project column
- No cross-agent memory access without explicit sharing

### 5.2 Hook Safety
- All SQL uses parameterized queries (no injection)
- Input validation on all hook parameters
- Size limits on stored values (prevent DoS)
- TTL enforcement (automatic cleanup)

### 5.3 Skill Execution
- Skills are documentation + patterns, not executable code
- No code execution from skill content
- Agent interprets and applies skill guidance

### 5.4 Compression Safety
- headroom runs in separate process
- Input size limits (50KB fallback)
- Timeout on compression (30s)
- No network access in compression

---

## 6. Deployment Topology

### 6.1 Single-User (Default)
```
/root/agent-enhancements/           # Project root (read-only after setup)
~/.agent-memory/                    # User memory (per-user)
~/.claude/, ~/.codex/, etc.         # Agent configs (per-agent)
```

### 6.2 Multi-User (Team)
```
/opt/agent-enhancements/            # Shared project (read-only)
/home/user/.agent-memory/           # Per-user memory
/home/user/.claude/, etc.           # Per-user agent configs
```

### 6.3 CI/CD (Automated)
- `update-skills.sh` runs on schedule
- `setup.sh` runs in container
- Agent configs generated as artifacts
- Skills index published as JSON artifact

---

## 7. Versioning & Compatibility

### 7.1 Version Scheme
- **Major**: Breaking schema changes (skills index, memory DB, compression config)
- **Minor**: New features, new agents, new skill sources
- **Patch**: Bug fixes, documentation, internal refactoring

### 7.2 Compatibility Matrix
| Component | Backward Compatible | Forward Compatible |
|-----------|---------------------|-------------------|
| all-skills.json schema | ✅ (additive only) | ⚠️ (may need migration) |
| Memory DB schema | ✅ (additive columns) | ❌ |
| Compression config | ✅ | ✅ |
| Agent config format | ✅ | ✅ |
| Hook interface | ✅ | ❌ |

### 7.3 Migration Strategy
- Schema migrations in `memory/init-memory.sh` (IF NOT EXISTS)
- Skills index: always regenerated from source (no migration needed)
- Agent configs: always regenerated (no migration needed)

---

## 8. Observability

### 8.1 Logs
- Setup: stdout/stderr (colored)
- Hooks: stderr only (structured)
- Compression: stderr on error

### 8.2 Metrics (Future)
- Skill load latency
- Memory hit/miss ratio
- Compression ratio achieved
- Hook execution time

### 8.3 Health Checks
- `memory/init-memory.sh` validates DB
- `compression/compress.sh --test` validates headroom
- `scripts/load-skills.py` validates index

---

**End of Architecture Document**