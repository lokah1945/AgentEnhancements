# Troubleshooting Guide

**Version**: 2.0  
**Last Updated**: 2026-11-01  
**Audience**: Users, agents, DevOps

---

## 1. Quick Diagnostics

Run these first to identify the issue category:

```bash
# 1. Check setup.sh syntax
bash -n /root/agent-enhancements/unified-integration/setup.sh

# 2. Check Python scripts
python3 -m py_compile /root/agent-enhancements/unified-integration/scripts/*.py
python3 -m py_compile /root/agent-enhancements/unified-integration/memory/hooks/*.py

# 3. Check config files
python3 -c "import yaml; yaml.safe_load(open('/root/agent-enhancements/unified-integration/memory/config.yaml'))"
python3 -c "import yaml; yaml.safe_load(open('/root/agent-enhancements/unified-integration/compression/config.yaml'))"
python3 -c "import json; json.load(open('/root/agent-enhancements/unified-integration/skills/all-skills.json'))"

# 4. Check agent detection
/root/agent-enhancements/unified-integration/setup.sh 2>&1 | grep -E "(Found|WARN|ERROR)"
```

---

## 2. Common Issues & Solutions

### 2.1 Setup Failures

#### "command not found: claude/codex/opencode/etc."
```
Cause: Agent CLI not installed or not in PATH
Solution:
  - Install the agent CLI
  - Add to PATH: export PATH="$PATH:/path/to/agent/bin"
  - Re-run setup.sh
```

#### "Permission denied" on hook scripts
```
Cause: Hook scripts not executable
Solution:
  chmod +x /root/agent-enhancements/unified-integration/memory/hooks/*.sh
  chmod +x /root/agent-enhancements/unified-integration/memory/hooks/*.py
  chmod +x /root/agent-enhancements/unified-integration/compression/compress.sh
  chmod +x /root/agent-enhancements/unified-integration/launch-agent.sh
```

#### "sqlite3: command not found"
```
Cause: SQLite not installed
Solution:
  Ubuntu/Debian: apt-get install sqlite3
  macOS: brew install sqlite3
  Alpine: apk add sqlite
```

#### "headroom not found" / compression fails
```
Cause: headroom binary not built or not in PATH
Solution:
  cd /root/agent-enhancements/headroom && cargo build --release
  # Verify:
  ls -la /root/agent-enhancements/headroom/target/release/headroom
  # Or set custom path:
  export HEADROOM_BIN="/root/agent-enhancements/headroom/target/release/headroom"
```

#### "ModuleNotFoundError: No module named 'yaml'"
```
Cause: PyYAML not installed
Solution:
  pip install pyyaml
  # Or: pip3 install pyyaml
```

#### "No such file or directory: /root/agent-enhancements/..."
```
Cause: Project not at default location
Solution:
  export AGENT_ENHANCEMENTS_BASE_DIR="/actual/path/to/agent-enhancements"
  /actual/path/to/agent-enhancements/unified-integration/setup.sh
```

---

### 2.2 Skills Issues

#### Skills not loading / "0 skills found"
```
Cause: all-skills.json missing or empty
Solution:
  1. Check file exists: ls -la /root/agent-enhancements/unified-integration/skills/all-skills.json
  2. Check content: cat /root/agent-enhancements/unified-integration/skills/all-skills.json | head -20
  3. Re-run aggregation: /root/agent-enhancements/unified-integration/setup.sh
  4. Verify sources exist: ls /root/agent-enhancements/agentic-awesome-skills/skills | wc -l
```

#### Skill not found for specific agent
```
Cause: Agent not in skill's tools array
Solution:
  1. Check skill frontmatter: cat skills/by-category/security/skill-name/SKILL.md | head -20
  2. Verify agent in tools list: grep -A 10 "tools:" skills/by-category/security/skill-name/SKILL.md
  3. Add agent to tools if compatible, re-run setup.sh
```

#### Skills duplicated across categories
```
Cause: Same skill name in multiple sources with different categories
Solution:
  - Check all-skills.json for duplicates: python3 -c "import json; d=json.load(open('skills/all-skills.json')); names=[s['name'] for s in d['skills']]; print([n for n in names if names.count(n)>1])"
  - Upstream fix needed - report to source repo
```

#### "SKILL.md is a directory" error
```
Cause: Corrupted skill directory structure
Solution:
  find /root/agent-enhancements/*/skills -name "SKILL.md" -type d
  # Remove corrupted entries and re-run setup.sh
```

---

### 2.3 Memory Issues

#### Memory not persisting between sessions
```
Cause: Hooks not firing or DB not initialized
Solution:
  1. Verify DB exists: ls -la ~/.agent-memory/memory.db
  2. Initialize: /root/agent-enhancements/unified-integration/memory/init-memory.sh
  3. Check hooks in agent config:
     - Claude: cat ~/.claude/settings.json | grep memory-hook
     - Codex: cat ~/.codex/config.yaml | grep memory
  4. Test manually:
     python3 /root/agent-enhancements/unified-integration/scripts/memory.py claude-code save test "value"
     python3 /root/agent-enhancements/unified-integration/scripts/memory.py claude-code load test
```

#### "database is locked" error
```
Cause: Multiple processes accessing SQLite
Solution:
  1. Check for stale processes: lsof ~/.agent-memory/memory.db
  2. Kill if needed: kill -9 <PID>
  3. Ensure hooks use short transactions (they do)
```

#### Memory hook returns empty
```
Cause: Key not found or wrong memory_type
Solution:
  1. List memories: python3 scripts/memory.py claude-code list
  2. Check memory_type matches: python3 scripts/memory.py claude-code load key project_context
  3. Verify project name: python3 scripts/memory.py claude-code list project_context
```

#### Memory growing unbounded
```
Cause: TTL not working or auto-cleanup not running
Solution:
  1. Check TTL in config: grep -A 5 "ttl_days" memory/config.yaml
  2. Run cleanup: python3 scripts/memory.py claude-code cleanup
  3. Add cron for periodic cleanup
```

---

### 2.4 Compression Issues

#### Compression not reducing size
```
Cause: Content not compressible or wrong mode
Solution:
  1. Check content type detection: 
     head -100 large_file.txt | grep -E "(^{|^```|ERROR|WARN)"
  2. Force mode: compress.sh json|code|logs|markdown claude-code < input
  3. Check headroom working: headroom compress --mode generic < input
```

#### "headroom: command not found" in compress.sh
```
Cause: Binary path not resolved
Solution:
  1. Check config: grep binary_path compression/config.yaml
  2. Verify binary: ls -la /root/agent-enhancements/headroom/target/release/headroom
  3. Rebuild: cd headroom && cargo build --release
  4. Set env: export HEADROOM_BIN="/root/agent-enhancements/headroom/target/release/headroom"
```

#### Compression timeout
```
Cause: Input too large or headroom hanging
Solution:
  1. Check input size: wc -c input.txt
  2. Fallback triggers at 50KB (see compress.py)
  3. Increase timeout in compress.py if needed
```

---

### 2.5 Agent Config Issues

#### Agent config not applied
```
Cause: Config file in wrong location or wrong format
Solution:
  1. Verify config location:
     Claude: ~/.claude/CLAUDE.md + settings.json
     Codex: ~/.codex/config.yaml
     etc.
  2. Check format validity:
     python3 -c "import json; json.load(open('~/.claude/settings.json'))"
     python3 -c "import yaml; yaml.safe_load(open('~/.codex/config.yaml'))"
  3. Re-run setup.sh to regenerate
```

#### "Agent not detected" but agent installed
```
Cause: CLI name different or not in PATH
Solution:
  1. Check exact command: which claude codex opencode cursor gemini windsurf kiro
  2. For Copilot: gh extension list | grep copilot
  3. Add alias if needed: alias claude-code='/path/to/claude'
```

#### System prompt not loading
```
Cause: Prompt file missing or path wrong
Solution:
  1. Check prompts dir: ls /root/agent-enhancements/unified-integration/prompts/
  2. Verify source: ls /root/agent-enhancements/system-prompts-and-models-of-ai-tools/
  3. Re-run setup.sh prompts section
```

---

### 2.6 Update Issues

#### update-skills.sh fails
```
Cause: Git errors, network, or repo structure changed
Solution:
  1. Check each repo: cd /root/agent-enhancements/agentic-awesome-skills && git status
  2. Manual pull: git pull origin main
  3. Check for conflicts: git diff
  4. If structure changed, update setup.sh aggregation logic
```

#### Skill count decreased after update
```
Cause: Upstream removed skills or changed structure
Solution:
  1. Compare counts: grep total_skills skills/all-skills.json
  2. Check git log: cd agentic-awesome-skills && git log --oneline -20
  3. Verify find logic in setup.sh matches new structure
```

---

### 2.7 Performance Issues

#### Setup.sh takes too long
```
Cause: Processing 3,000+ skills sequentially
Solution:
  - Normal: 30-60 seconds for full aggregation
  - Use ECC_TEST_JOBS=4 for parallel (if modified)
  - Check disk I/O: iotop
```

#### Memory usage high during compression
```
Cause: Large input files
Solution:
  1. Check input size limits in compress.py (50KB fallback)
  2. Stream processing for large files
  3. Use headroom streaming mode
```

#### Agent startup slow
```
Cause: Memory init or skill index loading
Solution:
  1. Memory init is one-time: init-memory.sh
  2. Skill index cached in memory after first load
  3. Check for network calls in config (should be none)
```

---

## 3. Debug Mode

### 3.1 Enable Verbose Logging
```bash
# Setup with debug
bash -x /root/agent-enhancements/unified-integration/setup.sh 2>&1 | tee setup.log

# Individual functions
bash -c 'source setup.sh; detect_agents'
bash -c 'source setup.sh; aggregate_skills'
```

### 3.2 Hook Debugging
```bash
# Test memory hook directly
python3 /root/agent-enhancements/unified-integration/memory/hooks/claude-code-memory-hook.py save debug_test "test value" session_context
python3 /root/agent-enhancements/unified-integration/memory/hooks/claude-code-memory-hook.py load debug_test session_context
python3 /root/agent-enhancements/unified-integration/memory/hooks/claude-code-memory-hook.py list session_context
```

### 3.3 Compression Debugging
```bash
# Test with verbose
/root/agent-enhancements/unified-integration/compression/compress.sh auto claude-code < large_file.txt 2>&1

# Test headroom directly
/root/agent-enhancements/headroom/target/release/headroom compress --mode auto < large_file.txt
```

### 3.4 Skill Loading Debugging
```bash
# Test skill loader
python3 /root/agent-enhancements/unified-integration/scripts/load-skills.py claude-code "your task description" 2>&1

# Check index
python3 -c "
import json
with open('/root/agent-enhancements/unified-integration/skills/all-skills.json') as f:
    d = json.load(f)
    print(f'Total: {d[\"total_skills\"]}')
    print(f'Categories: {d[\"categories\"]}')
    print(f'Agents: {d[\"agent_skill_counts\"]}')
"
```

---

## 4. Log Analysis

### 4.1 Setup Logs
```bash
# Last setup run
grep -E "(SUCCESS|WARN|ERROR)" setup.log

# Specific component
grep "aggregate_skills" setup.log -A 20
```

### 4.2 Agent Logs
```bash
# Claude Code
claude --debug 2>&1 | grep -E "(hook|memory|skill)"

# Codex
codex --debug 2>&1 | grep -E "(hook|memory|skill)"
```

### 4.3 Memory Logs
```bash
# Check SQLite directly
sqlite3 ~/.agent-memory/memory.db "SELECT agent, project, memory_type, key, substr(value,1,50), updated_at FROM memories ORDER BY updated_at DESC LIMIT 20;"
```

---

## 5. Recovery Procedures

### 5.1 Full Reset (Nuclear Option)
```bash
# 1. Backup configs
cp -r ~/.claude ~/.claude.backup
cp -r ~/.codex ~/.codex.backup
# ... etc

# 2. Clean memory
rm -rf ~/.agent-memory

# 3. Clean unified integration generated files
rm -rf /root/agent-enhancements/unified-integration/{skills,memory,compression,prompts,config}/*

# 4. Re-run setup
/root/agent-enhancements/unified-integration/setup.sh

# 5. Restore any custom configs from backup
```

### 5.2 Partial Reset - Skills Only
```bash
rm -rf /root/agent-enhancements/unified-integration/skills/*
/root/agent-enhancements/unified-integration/setup.sh
```

### 5.3 Partial Reset - Memory Only
```bash
rm -rf ~/.agent-memory
/root/agent-enhancements/unified-integration/memory/init-memory.sh
```

### 5.4 Partial Reset - Agent Configs Only
```bash
rm ~/.claude/CLAUDE.md ~/.claude/settings.json
rm ~/.codex/config.yaml
# ... etc
/root/agent-enhancements/unified-integration/setup.sh
```

---

## 6. Getting Help

### 6.1 Self-Service
1. Check this guide
2. Run diagnostics in Section 1
3. Check logs in Section 4
4. Try recovery in Section 5

### 6.2 Report Issues
When reporting, include:
- Agent name and version
- Command that failed
- Full error output
- Relevant log snippets
- Output of diagnostic commands

### 6.3 Known Limitations
- Windows: Some paths/permissions differ (use WSL)
- Copilot: Limited hook support (VS Code only)
- Kiro: Memory hooks not fully tested
- Large repos: Skill loading may need optimization

---

## 7. FAQ

**Q: Can I use this without running setup.sh?**
A: No, setup.sh generates all configs and indexes. Run once after clone/update.

**Q: How often should I run update-skills.sh?**
A: Monthly, or when upstream sources release updates.

**Q: Can I add my own skills locally?**
A: Yes, create `$BASE_DIR/local-skills/` and add to setup.sh aggregation.

**Q: Does this work offline?**
A: Yes, after initial setup. update-skills.sh needs network.

**Q: Can I share memory between agents?**
A: Not directly - each agent has separate namespace. Use project_context for sharing.

**Q: How do I backup my memories?**
A: Copy ~/.agent-memory/memory.db or export via memory.py list.

---

**End of Troubleshooting Guide**