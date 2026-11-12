# Updating Guide

**Version**: 2.0  
**Last Updated**: 2026-11-01  
**Audience**: Users, DevOps, maintainers

---

## 1. Overview

This guide covers all update procedures for the AgentEnhancements project.

### Update Categories

| Category | Frequency | Command | Risk |
|----------|-----------|---------|------|
| Skill Sources | Monthly | `./update-skills.sh` | Low |
| Project Dependencies | As needed | Manual | Medium |
| Core Tools (headroom, claude-mem) | Quarterly | Manual | Medium |
| Setup Script | Per release | Git pull | Low |
| Agent CLIs | Per agent release | Agent-specific | Low |

---

## 2. Updating Skill Sources (Monthly)

### 2.1 Automated Update (Recommended)

```bash
# Run the update script
/root/agent-enhancements/unified-integration/update-skills.sh

# What it does:
# 1. Git pulls all source repos (agentic-awesome-skills, ECC, ponytail, superpowers, etc.)
# 2. Rebuilds headroom if updated
# 3. Rebuilds claude-mem if updated
# 4. Prompts to re-run setup.sh
```

### 2.2 Manual Update (If Automated Fails)

```bash
# 1. Update each source
cd /root/agent-enhancements/agentic-awesome-skills && git pull origin main
cd /root/agent-enhancements/ECC && git pull origin main
cd /root/agent-enhancements/ponytail && git pull origin main
cd /root/agent-enhancements/superpowers && git pull origin main
cd /root/agent-enhancements/system-prompts-and-models-of-ai-tools && git pull origin main
cd /root/agent-enhancements/claude-mem && git pull origin main
cd /root/agent-enhancements/headroom && git pull origin main

# 2. Rebuild compiled components
cd /root/agent-enhancements/headroom && cargo build --release
cd /root/agent-enhancements/claude-mem && npm run build

# 3. Regenerate all configs
/root/agent-enhancements/unified-integration/setup.sh
```

### 2.3 Verify Update

```bash
# Check skill counts
python3 -c "
import json
with open('/root/agent-enhancements/unified-integration/skills/all-skills.json') as f:
    d = json.load(f)
    print(f'Total skills: {d[\"total_skills\"]}')
    print(f'Categories: {d[\"categories\"]}')
    print(f'Last updated: {d[\"last_updated\"]}')
"

# Test skill loading
python3 /root/agent-enhancements/unified-integration/scripts/load-skills.py claude-code "security audit"

# Test all agents
for agent in claude-code codex opencode cursor gemini-cli windsurf kiro; do
    /root/agent-enhancements/unified-integration/launch-agent.sh $agent --version 2>&1 | head -1
done
```

---

## 3. Updating Core Dependencies

### 3.0 anthropic-skills and replica-skill (vendored skill suites)

Both are vendored copies (no `.git`), so `update-skills.sh` skips them with
a warning. Refresh them by re-vendoring:

```bash
# anthropic-skills (19 official Anthropic skills, Apache-2.0)
cd /tmp && git clone --depth 1 https://github.com/anthropics/skills.git fresh
rm -rf "$AGENT_ENHANCEMENTS_BASE_DIR/anthropic-skills"
mkdir -p "$AGENT_ENHANCEMENTS_BASE_DIR/anthropic-skills"
cp -r fresh/. "$AGENT_ENHANCEMENTS_BASE_DIR/anthropic-skills/"
rm -rf "$AGENT_ENHANCEMENTS_BASE_DIR/anthropic-skills/.git"   # keep the vendor clean

# replica-skill: same procedure from https://github.com/Jakeschincariol/replica-skill
# (keep the original LICENSE file that ships with it)

# Then re-aggregate, rebuild the registry and re-link native skills:
cd "$AGENT_ENHANCEMENTS_BASE_DIR" && ./unified-integration/setup.sh
```

Verify: `python3 unified-integration/scripts/registry.py stats` should
report the new skill count for the `anthropic-skills` source, and
`bash unified-integration/scripts/link-skills.sh --status` should still
show the curated set linked.

### 3.1 headroom (Rust)

```bash
# Check current version
/root/agent-enhancements/headroom/target/release/headroom --version

# Update
cd /root/agent-enhancements/headroom
git fetch origin
git log --oneline HEAD..origin/main  # Check what's new
git pull origin main
cargo build --release

# Verify
/root/agent-enhancements/headroom/target/release/headroom --version

# Test compression
echo "test" | /root/agent-enhancements/unified-integration/compression/compress.sh auto claude-code
```

### 3.2 claude-mem (Node.js)

```bash
# Check current version
cd /root/agent-enhancements/claude-mem && npm list

# Update
cd /root/agent-enhancements/claude-mem
git fetch origin
git log --oneline HEAD..origin/main
git pull origin main
npm install
npm run build

# Verify plugin paths exist
ls /root/agent-enhancements/claude-mem/.claude-plugin
ls /root/agent-enhancements/claude-mem/.codex-plugin
# ... etc
```

### 3.3 ECC (Node.js - for tests)

```bash
cd /root/agent-enhancements/ECC
git fetch origin
git log --oneline HEAD..origin/main
git pull origin main
npm install

# Run tests
node tests/run-all.js
```

---

## 4. Updating Setup Script

### 4.1 From Git

```bash
cd /root/agent-enhancements
git fetch origin
git log --oneline HEAD..origin/main  # Review changes
git pull origin main

# Re-run setup to apply any changes
/root/agent-enhancements/unified-integration/setup.sh
```

### 4.2 Verify Setup Script Changes

```bash
# Check for breaking changes
grep -n "BREAKING\|breaking\|major" /root/agent-enhancements/unified-integration/setup.sh

# Verify syntax
bash -n /root/agent-enhancements/unified-integration/setup.sh
python3 -m py_compile /root/agent-enhancements/unified-integration/scripts/*.py
```

---

## 5. Updating Agent CLIs

Each agent has its own update mechanism:

### 5.1 Claude Code
```bash
# Usually auto-updates, or:
claude --version
# Check releases at: https://github.com/anthropics/claude-code/releases
```

### 5.2 Codex
```bash
codex --version
# Update via: npm update -g @openai/codex (if npm-based)
```

### 5.3 OpenCode
```bash
opencode --version
# Check: https://github.com/opencode-ai/opencode/releases
```

### 5.4 Cursor
```bash
# Auto-updates via app
cursor --version
```

### 5.5 Gemini CLI
```bash
gemini --version
# Update: npm update -g @google/gemini-cli
```

### 5.6 Windsurf
```bash
# Auto-updates via app
windsurf --version
```

### 5.7 GitHub Copilot
```bash
gh extension upgrade copilot
gh copilot --version
```

### 5.8 Kiro
```bash
kiro --version
# Check: https://github.com/kiro-ai/kiro/releases
```

---

## 6. Post-Update Verification Checklist

After ANY update, run these checks:

### 6.1 Core System
- [ ] `bash -n unified-integration/setup.sh` - Syntax OK
- [ ] `python3 -m py_compile unified-integration/scripts/*.py` - Python OK
- [ ] `unified-integration/memory/init-memory.sh` - Memory DB OK
- [ ] `unified-integration/compression/compress.sh auto claude-code < /dev/null` - Compression OK

### 6.2 Skills
- [ ] `ls unified-integration/skills/all-skills.json` - Index exists
- [ ] `python3 -c "import json; d=json.load(open('unified-integration/skills/all-skills.json')); print(d['total_skills'])"` - Count > 3000
- [ ] `python3 unified-integration/scripts/load-skills.py claude-code "test"` - Skills load

### 6.3 Agent Configs
- [ ] `ls ~/.claude/CLAUDE.md ~/.claude/settings.json` - Claude config exists
- [ ] `ls ~/.codex/config.yaml` - Codex config exists
- [ ] `ls ~/.config/opencode/config.json` - OpenCode config exists
- [ ] `ls ~/.cursor/settings.json` - Cursor config exists
- [ ] `ls ~/.gemini/config.yaml` - Gemini config exists
- [ ] `ls ~/.windsurf/config.yaml` - Windsurf config exists
- [ ] `ls ~/.config/github-copilot/config.yaml` - Copilot config exists
- [ ] `ls ~/.kiro/config.yaml` - Kiro config exists

### 6.4 Agent Launch
- [ ] `unified-integration/launch-agent.sh claude-code --version` - Launches
- [ ] `unified-integration/launch-agent.sh codex --version` - Launches
- [ ] `unified-integration/launch-agent.sh opencode --version` - Launches

### 6.5 Tests
- [ ] `cd ECC && node tests/run-all.js` - All pass

---

## 7. Rollback Procedures

### 7.1 Rollback Skill Update
```bash
# If skill update broke something
cd /root/agent-enhancements/agentic-awesome-skills
git log --oneline -5  # Find previous commit
git checkout <previous-commit-hash>
# Repeat for other sources if needed
/root/agent-enhancements/unified-integration/setup.sh
```

### 7.2 Rollback headroom
```bash
cd /root/agent-enhancements/headroom
git log --oneline -5
git checkout <previous-commit-hash>
cargo build --release
```

### 7.3 Rollback claude-mem
```bash
cd /root/agent-enhancements/claude-mem
git log --oneline -5
git checkout <previous-commit-hash>
npm install && npm run build
```

### 7.4 Full Rollback (Nuclear)
```bash
# 1. Restore agent configs from backup
rm -rf ~/.claude ~/.codex ~/.config/opencode ~/.cursor ~/.gemini ~/.windsurf ~/.config/github-copilot ~/.kiro
cp -r ~/.claude.backup ~/.claude
cp -r ~/.codex.backup ~/.codex
# ... etc

# 2. Reset project to known good commit
cd /root/agent-enhancements
git log --oneline -10
git checkout <known-good-commit>

# 3. Re-run setup
/root/agent-enhancements/unified-integration/setup.sh
```

---

## 8. Scheduled Maintenance

### 8.1 Monthly (Automate with Cron)
```bash
# Add to crontab: 0 2 1 * * /root/agent-enhancements/unified-integration/update-skills.sh >> /var/log/agent-enhancements-update.log 2>&1

# Or use systemd timer:
# /etc/systemd/system/agent-enhancements-update.service
# /etc/systemd/system/agent-enhancements-update.timer
```

### 8.2 Quarterly
- [ ] Update headroom to latest Rust edition
- [ ] Update claude-mem dependencies
- [ ] Update ECC dependencies
- [ ] Review agent CLI versions
- [ ] Run full test suite
- [ ] Update documentation if needed

### 8.3 Annually
- [ ] Review CONTRACT.md for relevance
- [ ] Audit all dependencies for security
- [ ] Performance benchmark
- [ ] Architecture review

---

## 9. Automated Update Pipeline (CI/CD)

### 9.1 GitHub Actions Example
```yaml
# .github/workflows/update-skills.yml
name: Monthly Skill Update
on:
  schedule:
    - cron: '0 2 1 * *'  # Monthly 2 AM
  workflow_dispatch: {}

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Update skills
        run: |
          cd /root/agent-enhancements
          ./unified-integration/update-skills.sh
      - name: Run tests
        run: |
          cd ECC && node tests/run-all.js
      - name: Create PR
        uses: peter-evans/create-pull-request@v5
        with:
          title: "chore(skills): monthly update from upstream"
          body: "Automated monthly skill source update"
```

---

## 10. Troubleshooting Updates

| Issue | Solution |
|-------|----------|
| Git pull fails | Check network, credentials, resolve conflicts manually |
| Cargo build fails | Update Rust: `rustup update`, check Cargo.toml |
| NPM install fails | Clear cache: `npm cache clean --force`, check Node version |
| Tests fail after update | Check CHANGELOG.md for breaking changes, adapt code |
| Skill count dropped | Upstream removed skills - verify with git log |
| Agent config not updated | Re-run setup.sh manually |
| Memory DB locked | Kill processes: `lsof ~/.agent-memory/memory.db` |

---

## 11. Version Compatibility Matrix

| Component | Min Version | Current | Notes |
|-----------|-------------|---------|-------|
| bash | 4.0 | 5.x | |
| python3 | 3.8 | 3.11+ | |
| sqlite3 | 3.30 | 3.40+ | |
| rust | 1.70 | 1.75+ | For headroom |
| node | 18 | 20+ | For claude-mem, ECC |
| git | 2.30 | 2.40+ | |

---

## 12. Support

For update issues:
1. Check this guide
2. Run diagnostic commands in TROUBLESHOOTING.md
3. Check CHANGELOG.md for breaking changes
4. Report with: component, version, error, steps to reproduce

---

**End of Updating Guide**