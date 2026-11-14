# Agent-Specific Setup Guide

**Version**: 2.0  
**Last Updated**: 2026-11-01  
**Audience**: Users, DevOps, agents

---

## 1. Supported Agents

| Agent | CLI Command | Config Dir | Config File | Status |
|-------|-------------|------------|-------------|--------|
| Claude Code | `claude` | `~/.claude/` | `CLAUDE.md`, `settings.json` | ✅ Full |
| Codex | `codex` | `~/.codex/` | `config.yaml` | ✅ Full |
| OpenCode | `opencode` | `~/.config/opencode/` | `config.json` | ✅ Full |
| Cursor | `cursor` | `~/.cursor/` | `settings.json` | ✅ Full |
| Gemini CLI | `gemini` | `~/.gemini/` | `config.yaml` | ✅ Full |
| Windsurf | `windsurf` | `~/.windsurf/` | `config.yaml` | ✅ Full |
| GitHub Copilot | `gh copilot` | `~/.config/github-copilot/` | `config.yaml` | ✅ Full |
| Kiro | `kiro` | `~/.kiro/` | `config.yaml` | ✅ Full |

---

## 2. Quick Start per Agent

### 2.1 Universal (All Agents)
```bash
# One-time setup
/root/agent-enhancements/unified-integration/setup.sh

# Launch any agent with enhancements
/root/agent-enhancements/unified-integration/launch-agent.sh <agent-name>
```

### 2.2 Claude Code
```bash
# Auto-configured by setup.sh
# Adds to ~/.claude/CLAUDE.md and ~/.claude/settings.json

# Launch
claude
# OR enhanced
/root/agent-enhancements/unified-integration/launch-agent.sh claude-code
```

**Features Enabled**:
- ✅ System prompt optimization
- ✅ Skills auto-load (all 3,127+)
- ✅ Persistent memory (SQLite + hooks)
- ✅ Context compression (headroom, 200K budget)
- ✅ Pre/Post/Stop hooks for memory

### 2.3 Codex
```bash
# Auto-configured by setup.sh
# Adds to ~/.codex/config.yaml

# Launch
codex
# OR enhanced
/root/agent-enhancements/unified-integration/launch-agent.sh codex
```

**Features Enabled**:
- ✅ System prompt optimization
- ✅ Skills auto-load
- ✅ Persistent memory
- ✅ Context compression (128K budget)

### 2.4 OpenCode
```bash
# Auto-configured by setup.sh
# Adds to ~/.config/opencode/config.json

# Launch
opencode
# OR enhanced
/root/agent-enhancements/unified-integration/launch-agent.sh opencode
```

**Features Enabled**:
- ✅ System prompt optimization
- ✅ Skills auto-load
- ✅ Persistent memory
- ✅ Context compression (100K budget)

### 2.5 Cursor
```bash
# Auto-configured by setup.sh
# Adds to ~/.cursor/settings.json

# Launch
cursor
# OR enhanced
/root/agent-enhancements/unified-integration/launch-agent.sh cursor
```

**Features Enabled**:
- ✅ System prompt optimization
- ✅ Skills auto-load
- ✅ Persistent memory
- ✅ Context compression (128K budget)

### 2.6 Gemini CLI
```bash
# Auto-configured by setup.sh
# Adds to ~/.gemini/config.yaml

# Launch
gemini
# OR enhanced
/root/agent-enhancements/unified-integration/launch-agent.sh gemini-cli
```

**Features Enabled**:
- ✅ System prompt optimization
- ✅ Skills auto-load
- ✅ Persistent memory
- ✅ Context compression (1M budget)

### 2.7 Windsurf
```bash
# Auto-configured by setup.sh
# Adds to ~/.windsurf/config.yaml

# Launch
windsurf
# OR enhanced
/root/agent-enhancements/unified-integration/launch-agent.sh windsurf
```

**Features Enabled**:
- ✅ System prompt optimization
- ✅ Skills auto-load
- ✅ Persistent memory
- ✅ Context compression (128K budget)

### 2.8 GitHub Copilot
```bash
# Auto-configured by setup.sh
# Adds to ~/.config/github-copilot/config.yaml

# Launch (via VS Code)
code .
# Copilot Chat available with enhancements
```

**Features Enabled**:
- ✅ Skills auto-load
- ✅ Context compression (32K budget)
- ⚠️ Memory via VS Code settings
- ⚠️ No native hooks (uses VS Code)

### 2.9 Kiro
```bash
# Auto-configured by setup.sh
# Adds to ~/.kiro/config.yaml

# Launch
kiro
# OR enhanced
/root/agent-enhancements/unified-integration/launch-agent.sh kiro
```

**Features Enabled**:
- ✅ System prompt optimization
- ✅ Skills auto-load
- ✅ Persistent memory
- ✅ Context compression (128K budget)

---

## 3. Agent Feature Comparison

| Feature | Claude Code | Codex | OpenCode | Cursor | Gemini | Windsurf | Copilot | Kiro |
|---------|-------------|-------|----------|--------|--------|----------|---------|------|
| System Prompt | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Skills Auto-load | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Persistent Memory | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Context Compression | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hooks (Pre/Post/Stop) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| Budget (tokens) | 200K | 128K | 100K | 128K | 1M | 128K | 32K | 128K |
| Skill Categories | All | All | All | All | All | All | All | All |

---

## 4. Per-Agent Configuration Details

### 4.1 Claude Code (`~/.claude/`)

**CLAUDE.md** - Main configuration:
```markdown
# System Prompt
@/path/to/claude-code-system-prompt.txt

# Skills
- Source: /path/to/skills
- Auto-load: true
- Categories: all

# Memory
- Enabled: true
- Plugin: /path/to/claude-mem/.claude-plugin
- Auto-save: task_complete, decision_made, session_end

# Compression
- Enabled: true
- Budget: 200000
- Trigger at: 75%

# Hooks
- PreToolUse: memory_save, context_compress
- PostToolUse: memory_save
- Stop: memory_save
```

**settings.json** - Hooks configuration:
```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": "memory-hook.py save pre_tool_use \"${TOOL_NAME}\" \"${TOOL_INPUT}\"}]}],
    "PostToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": "memory-hook.py save post_tool_use \"${TOOL_NAME}\" \"${TOOL_RESULT}\"}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "memory-hook.py save session_end \"summary\" \"${SESSION_SUMMARY}\"}]}]
  }
}
```

### 4.2 Codex (`~/.codex/config.yaml`)

```yaml
system_prompt: "@/path/to/codex-system-prompt.txt"
skills:
  directory: "/path/to/skills"
  auto_load: true
memory:
  enabled: true
  plugin: "/path/to/claude-mem/.codex-plugin"
compression:
  enabled: true
  engine: "headroom"
  budget: 128000
hooks:
  pre_tool: "memory-hook.py save"
  post_tool: "memory-hook.py save"
  stop: "memory-hook.py save session_end"
```

### 4.3 Other Agents

See `CONFIGURATION.md` for complete configuration examples for all agents.

---

## 5. Verification Checklist

After running `setup.sh`, verify each agent:

### 5.1 Config Files Exist
```bash
# Claude Code
ls ~/.claude/CLAUDE.md ~/.claude/settings.json

# Codex
ls ~/.codex/config.yaml

# OpenCode
ls ~/.config/opencode/config.json

# Cursor
ls ~/.cursor/settings.json

# Gemini
ls ~/.gemini/config.yaml

# Windsurf
ls ~/.windsurf/config.yaml

# Copilot
ls ~/.config/github-copilot/config.yaml

# Kiro
ls ~/.kiro/config.yaml
```

### 5.2 Skills Registry Accessible
```bash
python3 /root/agent-enhancements/unified-integration/scripts/load-skills.py claude-code "test"
# Should return skill matches
```

### 5.3 Memory Initialized
```bash
/root/agent-enhancements/unified-integration/memory/init-memory.sh
# Should create ~/.agent-memory/memory.db
```

### 5.4 Compression Working
```bash
echo "test content" | /root/agent-enhancements/unified-integration/compression/compress.sh auto claude-code
# Should output compressed content
```

### 5.5 Launch Agent
```bash
/root/agent-enhancements/unified-integration/launch-agent.sh claude-code --version
# Should launch agent successfully
```

---

## 6. Troubleshooting per Agent

### 6.1 Claude Code Issues

| Problem | Solution |
|---------|----------|
| Hooks not firing | Check `~/.claude/settings.json` syntax |
| Memory not saving | Run `memory/init-memory.sh` |
| Skills not loading | Verify `CLAUDE.md` skills path |
| Compression errors | Check headroom binary in PATH |

### 6.2 Codex Issues

| Problem | Solution |
|---------|----------|
| Config not applied | Restart Codex after config change |
| Memory plugin missing | Verify `.codex-plugin` exists |
| Skills not found | Check `config.yaml` skills.directory |

### 6.3 Common Issues (All Agents)

| Problem | Solution |
|---------|----------|
| "Agent not detected" | Install agent CLI, ensure in PATH |
| "Permission denied" | Run `chmod +x` on hook scripts |
| "Module not found" | Install Python dependencies: `pip install pyyaml` |
| "Headroom not found" | Build: `cd /root/agent-enhancements/headroom && cargo build --release` |

---

## 7. Advanced Configuration

### 7.1 Custom Budgets

Edit `unified-integration/compression/config.yaml`:
```yaml
agents:
  claude-code:
    budget: 300000  # Increase for larger contexts
```

### 7.2 Custom Memory Types

Edit `unified-integration/memory/config.yaml`:
```yaml
types:
  - name: "my_custom_type"
    description: "Custom memory for X"
    ttl_days: 90
    scope: "project"
```

### 7.3 Disable Features Per Agent

```yaml
# In compression config
agents:
  copilot:
    enabled: false  # Disable compression for Copilot
```

---

## 8. Updating Agent Configs

After any changes to `setup.sh` or upstream configs:

```bash
# Regenerate all agent configs
/root/agent-enhancements/unified-integration/setup.sh

# Or for specific agent, the setup.sh handles all detected agents
```

---

**End of Agent Setup Guide**