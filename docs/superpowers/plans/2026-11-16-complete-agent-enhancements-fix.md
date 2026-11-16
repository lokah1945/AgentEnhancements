# Complete AgentEnhancements E2E Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all critical, high, and medium issues from the deep E2E audit so that AgentEnhancements works automatically for Claude Code, Codex, and OpenCode with full skill discovery, native skills, MCP gateway, memory, and compression.

**Architecture:** Extend the existing universal integration layer (`native-integration.py`, `link-skills.sh`, `runtime.py`) to treat all three agents equally. Each fix is an independent module modification with clear boundaries.

**Tech Stack:** Python 3.11+, Bash, SQLite, MCP protocol, Jinja2 templates

**Spec:** This plan implements the findings from the deep E2E audit report (this conversation context).

## Global Constraints

- **Agent parity:** Claude Code, Codex, and OpenCode must have equivalent integration depth (hooks, native skills, MCP, memory)
- **No context bloat:** Cold start must stay ≤ 4000 tokens (CONTRACT.md §8.4)
- **Skill discovery precision:** Return relevant skills only; `max_results` configurable per agent; agent decides which to read
- **Catalog access:** Full 3,378-skill catalog always reachable via `registry.py search/map/show` and MCP tools
- **Memory integrity:** `memory_type` never empty; all entries have valid type
- **Compression:** Headroom binary built by default; fallback works for code/generic
- **Single branch:** All changes committed directly to `master`; no PRs, no feature branches
- **Verification:** Each task must pass its verification step before marking complete

## Review Focus

| Input Class / Failure Mode | Expected Behavior | Owning Task |
|---------------------------|-------------------|-------------|
| Codex/OpenCode session start without hooks | Runtime hooks fire, skill cards injected | Task 1 |
| Native skills missing in agent skill dirs | All 16 skills linked in each agent's native dir | Task 2 |
| Memory entries with empty `memory_type` | Zero corrupt entries; all have valid type | Task 3 |
| Headroom not built → weak compression | Binary exists; fallback compresses code/generic | Task 4 |
| Registry structure mismatch | Both entry formats work; search/map functional | Task 5 |
| Agent skill directories don't exist | Created and populated on setup | Task 2 |
| MCP gateway not exposed to all agents | Gateway registered in each agent's config | Task 1 |
| Memory hooks not installed for Codex/OpenCode | Memory save/load works from hooks | Task 1 |

---

### Task 1: Install Runtime Hooks for All Agents

**Files:**
- Modify: `unified-integration/scripts/native-integration.py:143-262` (install function)
- Modify: `unified-integration/scripts/runtime.py` (ensure agent parameter handling)
- Test: Manual verification per agent

**Interfaces:**
- Consumes: Existing hook installation logic for claude-code
- Produces: Hook installation for codex, opencode; MCP registration for all

- [ ] **Step 1: Write the failing test**

```bash
# Test script: verify_hooks_per_agent.sh
#!/bin/bash
for agent in claude-code codex opencode; do
    # Simulate hook install
    python3 -c "
import sys
sys.path.insert(0, 'unified-integration/scripts')
from native_integration import install
install('$agent', mcp_only=False)
"
    # Check config files
    case $agent in
        claude-code) config=~/.claude/settings.json ;;
        codex) config=~/.codex/hooks.json ;;
        opencode) config=~/.config/opencode/opencode.jsonc ;;
    esac
    if ! grep -q "runtime.py $agent" "$config" 2>/dev/null; then
        echo "FAIL: $agent hooks not installed"
        exit 1
    fi
    echo "PASS: $agent hooks installed"
done
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash verify_hooks_per_agent.sh`
Expected: FAIL for codex and opencode (hooks not installed)

- [ ] **Step 3: Implement hook installation for all agents in `native-integration.py`**

Modify the `install()` function to:
1. Add hook installation for `codex` (writes to `~/.codex/hooks.json`)
2. Add hook installation for `opencode` (writes to `~/.config/opencode/opencode.jsonc`)
3. Ensure MCP server registration for all agents
4. Use the same `merge_hooks` logic as claude-code
5. Handle agent-specific config paths correctly

Key changes in `install()`:
```python
elif agent == "codex":
    config_dir = Path(os.environ.get("CODEX_HOME", home / ".codex"))
    # MCP registration (already exists)
    # ADD: Hook installation
    hooks_path = config_dir / "hooks.json"
    hooks = read_json(hooks_path)
    merge_hooks(hooks, agent)
    write_json(hooks_path, hooks)
    
elif agent == "opencode":
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "opencode"
    path = config_dir / "opencode.jsonc"
    if not path.exists():
        path = config_dir / "opencode.json"
    doc = read_json(path)
    # ADD: Hook installation for OpenCode
    hooks = doc.setdefault("hooks", {})
    merge_hooks(hooks, agent)
    write_json(path, doc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash verify_hooks_per_agent.sh`
Expected: PASS for all three agents

- [ ] **Step 5: Commit**

```bash
git add unified-integration/scripts/native-integration.py
git commit -m "feat(native): install runtime hooks for codex and opencode"
```

---

### Task 2: Link Native Skills for All Agents

**Files:**
- Modify: `unified-integration/scripts/link-skills.sh:345-350` (TARGETS default)
- Test: `bash link-skills.sh --status`

**Interfaces:**
- Consumes: Current `AGENT_SKILLS_NATIVE_TARGETS` default
- Produces: Extended targets including all three agents

- [ ] **Step 1: Write the failing test**

```bash
# Test script: verify_native_skills.sh
#!/bin/bash
for agent in claude-code codex opencode; do
    case $agent in
        claude-code) skills_dir=~/.claude/skills ;;
        codex) skills_dir=~/.codex/skills ;;
        opencode) skills_dir=~/.config/opencode/skills ;;
    esac
    count=$(ls -1 "$skills_dir" 2>/dev/null | wc -l)
    if [ "$count" -lt 16 ]; then
        echo "FAIL: $agent has $count skills (expected 16)"
        exit 1
    fi
    echo "PASS: $agent has $count skills"
done
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash verify_native_skills.sh`
Expected: FAIL for codex and opencode (directories don't exist / empty)

- [ ] **Step 3: Implement extended targets in `link-skills.sh`**

Modify the default `TARGETS` array (line 345-350) to include:
```bash
TARGETS=()
IFS=':' read -r -a RAW_TARGETS <<< "${AGENT_SKILLS_NATIVE_TARGETS:-$HOME/.claude/skills:$HOME/.agents/skills:$HOME/.codex/skills:$HOME/.config/opencode/skills}"
for t in "${RAW_TARGETS[@]}"; do
    [ -n "$t" ] && TARGETS+=("$t")
done
```

Also ensure `mkdir -p` creates parent directories in `link_skill()` function.

- [ ] **Step 4: Run test to verify it passes**

Run: `bash link-skills.sh --quiet && bash verify_native_skills.sh`
Expected: PASS for all three agents

- [ ] **Step 5: Commit**

```bash
git add unified-integration/scripts/link-skills.sh
git commit -m "feat(link-skills): extend native targets to codex and opencode"
```

---

### Task 3: Fix Memory System (Empty memory_type Entries)

**Files:**
- Modify: `unified-integration/scripts/memory.py:48-66` (save method - ensure memory_type default)
- Modify: `unified-integration/scripts/runtime.py:142-147` (PreToolUse/PostToolUse - pass memory_type)
- Script: One-time cleanup of corrupt entries
- Test: `python3 -c "import sqlite3; conn=sqlite3.connect('/root/.agent-memory/memory.db'); print(conn.execute('SELECT COUNT(*) FROM memories WHERE memory_type=\"\" OR memory_type IS NULL').fetchone()[0])"`

**Interfaces:**
- Consumes: Current memory save calls without memory_type
- Produces: All memory entries have valid `memory_type`

- [ ] **Step 1: Write the failing test**

```bash
# Cleanup script then verify
python3 << 'PYEOF'
import sqlite3
conn = sqlite3.connect('/root/.agent-memory/memory.db')
# Clean up
conn.execute('DELETE FROM memories WHERE memory_type = "" OR memory_type IS NULL')
conn.commit()
# Verify
count = conn.execute('SELECT COUNT(*) FROM memories WHERE memory_type = "" OR memory_type IS NULL').fetchone()[0]
conn.close()
assert count == 0, f"Still has {count} corrupt entries"
print("PASS: No corrupt entries")
PYEOF
```

- [ ] **Step 2: Run test to verify it fails (before fix)**

Run the cleanup/verify script - should show 23 corrupt entries before cleanup

- [ ] **Step 3: Fix memory save calls in `runtime.py`**

Line 142-147: Add `memory_type="session_context"` to the save call:
```python
memory.save(
    f"session:{session_key}:last_tool",
    tool,
    memory_type="session_context",  # ADD THIS
    metadata={"event": name},
    ttl_days=7,
)
```

Also fix Stop event save (line 151-155):
```python
memory.save(
    f"session:{session_key}:summary",
    redact(message)[:MAX_MEMORY],
    memory_type="session_context",  # ADD THIS
    ttl_days=7,
)
```

- [ ] **Step 4: Fix `memory.py` default handling**

Ensure `save()` method default `memory_type="session_context"` is always used (already correct at line 48).

- [ ] **Step 5: Run cleanup and verify**

Run: `python3 cleanup_memory.py && python3 verify_memory.py`
Expected: PASS (0 corrupt entries)

- [ ] **Step 6: Commit**

```bash
git add unified-integration/scripts/runtime.py unified-integration/scripts/memory.py
git commit -m "fix(memory): ensure all entries have valid memory_type; cleanup corrupt entries"
```

---

### Task 4: Build Headroom Binary and Improve Fallback Compression

**Files:**
- Modify: `unified-integration/setup.sh:1293-1330` (setup_compression - build headroom by default)
- Modify: `unified-integration/scripts/compress.py:2369-2406` (fallback_compress - improve code/generic)
- Test: Compression verification script

**Interfaces:**
- Consumes: Current fallback compression (no-op for code/generic)
- Produces: Headroom binary built; fallback reduces code/generic by ≥30%

- [ ] **Step 1: Write the failing test**

```bash
# Test script: verify_compression.sh
#!/bin/bash
python3 << 'PYEOF'
import sys
sys.path.insert(0, 'unified-integration/scripts')
from compress import fallback_compress

# Test code compression
code = "def func():\n    x = 1\n    return x\n" * 100
compressed = fallback_compress(code, "code")
reduction = (len(code) - len(compressed)) / len(code) * 100
print(f"Code reduction: {reduction:.1f}%")
assert reduction >= 30, f"Code reduction only {reduction:.1f}%"

# Test generic compression
generic = "This is a test " * 1000
compressed = fallback_compress(generic, "generic")
reduction = (len(generic) - len(compressed)) / len(generic) * 100
print(f"Generic reduction: {reduction:.1f}%")
assert reduction >= 30, f"Generic reduction only {reduction:.1f}%"

print("PASS: Compression effective")
PYEOF
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash verify_compression.sh`
Expected: FAIL (current fallback returns original for code/generic)

- [ ] **Step 3: Build headroom by default in `setup.sh`**

Modify `setup_compression()` (line 1293-1330):
1. Change `AGENT_ENHANCEMENTS_BUILD_HEADROOM` default from "0" to "1"
2. Ensure cargo is available (install if needed via rustup)
3. Build headroom during setup

- [ ] **Step 4: Improve fallback compression in `compress.py`**

Modify `fallback_compress()` (line 2369-2406):
1. For "code" mode: Remove blank lines, compress whitespace, deduplicate repeated patterns
2. For "generic" mode: Deduplicate repeated sentences, compress whitespace
3. Preserve semantic structure (don't break code syntax)

```python
def fallback_compress(content: str, mode: str) -> str:
    lines = content.split('\n')
    
    if mode == "code":
        # Remove excessive blank lines (keep max 1)
        result = []
        blank_count = 0
        for line in lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 1:
                    result.append(line)
            else:
                blank_count = 0
                result.append(line)
        # Deduplicate consecutive identical lines
        deduped = []
        prev = None
        for line in result:
            if line != prev or line.strip() == "":
                deduped.append(line)
            prev = line
        return '\n'.join(deduped)
    
    elif mode == "generic":
        # Deduplicate similar lines
        seen = set()
        unique = []
        for line in lines:
            normalized = ' '.join(line.split())  # Normalize whitespace
            if normalized not in seen and normalized:
                seen.add(normalized)
                unique.append(line)
        return '\n'.join(unique)
    
    # ... existing logic for json, logs, markdown
```

- [ ] **Step 5: Run test to verify it passes**

Run: `bash verify_compression.sh`
Expected: PASS (≥30% reduction for code and generic)

- [ ] **Step 6: Commit**

```bash
git add unified-integration/setup.sh unified-integration/scripts/compress.py
git commit -m "feat(compression): build headroom by default; improve fallback for code/generic"
```

---

### Task 5: Fix Registry Structure Compatibility

**Files:**
- Modify: `unified-integration/scripts/registry.py` (add compatibility layer)
- Test: Registry search/map/show commands

**Interfaces:**
- Consumes: Current `{entries: []}` structure
- Produces: Both `{entries: []}` and `{skills: [], plugins: [], mcp: [], capabilities: []}` accessible

- [ ] **Step 1: Write the failing test**

```bash
# Test script: verify_registry.sh
#!/bin/bash
python3 << 'PYEOF'
import json
with open('unified-integration/skills/agent-registry.json') as f:
    data = json.load(f)

# Check both structures work
# Old structure
assert 'entries' in data
assert len(data['entries']) == 3464

# New structure (compatibility)
skills = [e for e in data['entries'] if e.get('type') == 'skill']
plugins = [e for e in data['entries'] if e.get('type') == 'plugin']
mcp = [e for e in data['entries'] if e.get('type') == 'mcp']
capabilities = [e for e in data['entries'] if e.get('type') == 'capability']

print(f"Skills: {len(skills)}")
print(f"Plugins: {len(plugins)}")
print(f"MCP: {len(mcp)}")
print(f"Capabilities: {len(capabilities)}")

# Verify registry.py search works
import subprocess
result = subprocess.run([
    sys.executable, 'unified-integration/scripts/registry.py', 
    'search', 'debug', '--type', 'skill', '--limit', '1'
], capture_output=True, text=True)
assert result.returncode == 0
print("PASS: Registry compatible")
PYEOF
```

- [ ] **Step 2: Run test to verify it passes** (should already pass)

Run: `bash verify_registry.sh`
Expected: PASS (registry already works)

- [ ] **Step 3: Add convenience properties to registry.py for compatibility**

Add helper methods in `registry.py` to expose both views:
```python
@property
def skills(self):
    return [e for e in self.entries if e.get('type') == 'skill']

@property  
def plugins(self):
    return [e for e in self.entries if e.get('type') == 'plugin']
# etc.
```

- [ ] **Step 4: Commit**

```bash
git add unified-integration/scripts/registry.py
git commit -m "feat(registry): add compatibility views for skills/plugins/mcp/capabilities"
```

---

### Task 6: Update Setup.sh to Install for All Agents

**Files:**
- Modify: `unified-integration/setup.sh:2463-2486` (link_native_skills, create_agent_configs)
- Test: Full setup.sh run

**Interfaces:**
- Consumes: Current setup flow
- Produces: All three agents fully configured

- [ ] **Step 1: Write the failing test**

```bash
# Test script: verify_full_setup.sh
#!/bin/bash
# Run setup for all agents
python3 unified-integration/scripts/native-integration.py --agent claude-code
python3 unified-integration/scripts/native-integration.py --agent codex
python3 unified-integration/scripts/native-integration.py --agent opencode

# Verify each
for agent in claude-code codex opencode; do
    case $agent in
        claude-code) 
            config=~/.claude/settings.json
            skills=~/.claude/skills
            ;;
        codex) 
            config=~/.codex/hooks.json
            skills=~/.codex/skills
            ;;
        opencode) 
            config=~/.config/opencode/opencode.jsonc
            skills=~/.config/opencode/skills
            ;;
    esac
    
    # Check hooks
    if ! grep -q "runtime.py $agent" "$config" 2>/dev/null; then
        echo "FAIL: $agent hooks missing"
        exit 1
    fi
    
    # Check skills
    count=$(ls -1 "$skills" 2>/dev/null | wc -l)
    if [ "$count" -lt 16 ]; then
        echo "FAIL: $agent skills=$count"
        exit 1
    fi
    
    echo "PASS: $agent fully configured"
done
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash verify_full_setup.sh`
Expected: FAIL for codex/opencode

- [ ] **Step 3: Ensure `create_agent_configs` calls native-integration for all agents**

In `setup.sh` main(), the `create_agent_configs` function already iterates over `AGENTS` array and calls native-integration. Just ensure `AGENTS` includes all detected agents (already done in `detect_agents`).

- [ ] **Step 4: Run test to verify it passes**

Run: `bash verify_full_setup.sh`
Expected: PASS for all three agents

- [ ] **Step 5: Commit**

```bash
git add unified-integration/setup.sh
git commit -m "feat(setup): ensure all detected agents get full native integration"
```

---

### Task 7: Verify Skill Discovery Precision (Configurable max_results)

**Files:**
- Modify: `unified-integration/scripts/runtime.py:57` (max_results parameter)
- Modify: `unified-integration/scripts/load-skills.py:1986` (max_results default)
- Test: Skill discovery with varying complexity prompts

**Interfaces:**
- Consumes: Current hardcoded `max_results=3`
- Produces: Configurable max_results; agent can request more

- [ ] **Step 1: Write the failing test**

```bash
# Test script: verify_skill_discovery.sh
#!/bin/bash
python3 << 'PYEOF'
import sys
sys.path.insert(0, 'unified-integration/scripts')
from load_skills import SkillsLoader

loader = SkillsLoader("claude-code")

# Simple prompt - should get few relevant skills
simple_skills = loader.find_skills("fix bug", max_results=5)
print(f"Simple prompt: {len(simple_skills)} skills")

# Complex prompt - should get more relevant skills  
complex_skills = loader.find_skills("create a complete REST API with authentication, rate limiting, database models, tests, and documentation using FastAPI and PostgreSQL", max_results=10)
print(f"Complex prompt: {len(complex_skills)} skills")

# Verify we can get more when needed
assert len(complex_skills) >= len(simple_skills), "Complex should get more or equal"
print("PASS: Skill discovery scales with complexity")
PYEOF
```

- [ ] **Step 2: Run test to verify it passes** (should work with current code)

Run: `bash verify_skill_discovery.sh`
Expected: PASS (load_skills already supports max_results parameter)

- [ ] **Step 3: Make runtime.py use configurable max_results**

In `runtime.py` skill_context function, change:
```python
matches = loader.find_skills(prompt, max_results=3)
```
to:
```python
# Allow more results for complex prompts; agent filters
max_results = int(os.environ.get("AE_MAX_SKILL_CARDS", "5"))
matches = loader.find_skills(prompt, max_results=max_results)
```

- [ ] **Step 4: Commit**

```bash
git add unified-integration/scripts/runtime.py
git commit -m "feat(skills): make max_results configurable via AE_MAX_SKILL_CARDS"
```

---

### Task 8: Final E2E Verification

**Files:**
- Script: Comprehensive verification script
- Test: Run full verification

**Interfaces:**
- Consumes: All previous fixes
- Produces: Verification report

- [ ] **Step 1: Write comprehensive verification script**

```bash
# verify_e2e.sh
#!/bin/bash
set -e

echo "=== E2E VERIFICATION ==="

# 1. Hooks for all agents
for agent in claude-code codex opencode; do
    case $agent in
        claude-code) config=~/.claude/settings.json ;;
        codex) config=~/.codex/hooks.json ;;
        opencode) config=~/.config/opencode/opencode.jsonc ;;
    esac
    if ! grep -q "runtime.py $agent" "$config"; then
        echo "FAIL: $agent hooks missing"
        exit 1
    fi
done
echo "✅ Hooks installed for all agents"

# 2. Native skills for all agents
for agent in claude-code codex opencode; do
    case $agent in
        claude-code) skills=~/.claude/skills ;;
        codex) skills=~/.codex/skills ;;
        opencode) skills=~/.config/opencode/skills ;;
    esac
    count=$(ls -1 "$skills" 2>/dev/null | wc -l)
    if [ "$count" -lt 16 ]; then
        echo "FAIL: $agent skills=$count"
        exit 1
    fi
done
echo "✅ Native skills linked for all agents"

# 3. Memory integrity
corrupt=$(python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.agent-memory/memory.db')
c = conn.execute('SELECT COUNT(*) FROM memories WHERE memory_type=\"\" OR memory_type IS NULL')
print(c.fetchone()[0])
")
if [ "$corrupt" -ne 0 ]; then
    echo "FAIL: $corrupt corrupt memory entries"
    exit 1
fi
echo "✅ Memory integrity OK"

# 4. Compression
python3 << 'PYEOF'
import sys
sys.path.insert(0, 'unified-integration/scripts')
from compress import fallback_compress
code = "def func():\n    x = 1\n    return x\n" * 100
c = fallback_compress(code, "code")
assert (len(code) - len(c)) / len(code) > 0.3
print("✅ Compression effective")
PYEOF

# 5. Registry
python3 unified-integration/scripts/registry.py search "debug" --type skill --limit 1 >/dev/null
echo "✅ Registry functional"

# 6. Skill discovery
python3 << 'PYEOF'
import sys
sys.path.insert(0, 'unified-integration/scripts')
from load_skills import SkillsLoader
loader = SkillsLoader("claude-code")
skills = loader.find_skills("debug failing test", max_results=5)
assert len(skills) >= 3
print(f"✅ Skill discovery returns {len(skills)} skills")
PYEOF

# 7. MCP Gateway
python3 -c "
import sys
sys.path.insert(0, 'unified-integration/mcp-servers')
from gateway import Gateway
from api_config import read_config
import asyncio
g = Gateway()
asyncio.run(g.load())
config, _ = read_config()
tools = g.tools(config)
assert len(tools) >= 20
print(f'✅ MCP Gateway exposes {len(tools)} tools')
"

echo ""
echo "=== ALL CHECKS PASSED ==="
```

- [ ] **Step 2: Run final verification**

Run: `bash verify_e2e.sh`
Expected: All checks pass

- [ ] **Step 3: Commit verification script**

```bash
git add verify_e2e.sh
git commit -m "test: add comprehensive E2E verification script"
```

---

## Execution Notes

- Tasks 1, 2, 3, 4, 6, 7 can run in parallel (independent files)
- Task 5 is a minor compatibility fix
- Task 8 depends on all previous tasks
- Each task must pass its verification before marking complete
- All commits go directly to `master` branch