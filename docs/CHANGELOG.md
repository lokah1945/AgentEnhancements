# Changelog

**Version**: 2.0  
**Last Updated**: 2026-11-01  
**Audience**: All users, agents, maintainers

---

## Format

Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/):
- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

---

## [2.0.0] - 2026-11-01

### Added
- **CONTRACT.md**: Binding governance contract for all agents
- **docs/ARCHITECTURE.md**: Complete system architecture documentation
- **docs/CONFIGURATION.md**: Full configuration reference with all env vars
- **docs/SKILLS.md**: Skills system documentation (format, aggregation, categories)
- **docs/AGENTS.md**: Per-agent setup guides and feature matrix
- **docs/TROUBLESHOOTING.md**: Comprehensive troubleshooting guide
- **docs/CONTRIBUTING.md**: Contribution workflow and standards
- **docs/UPDATING.md**: Update procedures for skills, deps, tools
- **unified-integration/update-skills.sh**: Automated skill source update script
- **Environment variable overrides**: `AGENT_ENHANCEMENTS_BASE_DIR`, `AGENT_MEMORY_ROOT`, `HEADROOM_BIN`
- **Python memory hooks**: Parameterized SQL queries (security fix)
- **Skill category normalization**: Automatic mapping to 10 standard categories
- **Full skill directory copying**: Recursive copy preserves references/scripts
- **Agent-specific skill directories**: `by-agent/<agent>/` for auto-loading
- **Unified skills index metadata**: agent_skill_counts, proper timestamps
- **Flexible prompt detection**: Glob patterns for all agent prompt sources
- **Headroom binary detection priority**: Built > PATH > source build
- **Compression mode auto-detection**: JSON, code, logs, markdown, generic
- **Fallback compression**: Native Python when headroom unavailable

### Changed
- **setup.sh**: Complete rewrite - removed all critical bugs
  - Removed 20-skill limit per source (was `mapfile -n 20`)
  - Fixed date expansion bug (was literal `$(date -Iseconds)`)
  - All 4 sources now aggregated into unified index
  - Skills copied to correct categories from frontmatter
  - Full skill directories copied (not just SKILL.md)
  - SQL injection fixed (Python hooks with parameterized queries)
  - Hardcoded paths replaced with env vars
  - Fake fallback counts removed (real counts from parsing)
  - Prompt paths use flexible glob patterns
  - Headroom detection logic fixed
- **Renamed setup-fixed.sh → setup.sh** (canonical name)
- **Documentation moved to docs/**: Centralized all docs
- **Memory hooks**: Rewritten in Python with bash wrappers
- **All agent configs**: Regenerated with new paths and features

### Fixed
- **Critical**: Skill aggregation only processed 20 skills per source
- **Critical**: Unified index missing ECC/Ponytail/Superpowers skills
- **Critical**: SQL injection vulnerability in memory hooks
- **Critical**: Date timestamp stored as literal string
- **High**: All external skills forced into "general" category
- **High**: Only SKILL.md copied, missing references/scripts
- **High**: Hardcoded `/root/agent-enhancements/` paths
- **Medium**: Fake skill counts in fallback JSON
- **Medium**: Prompt detection failed for actual directory structures
- **Medium**: Headroom binary detection unreliable

### Security
- Memory hooks now use parameterized SQL queries
- Input validation on all hook parameters
- Size limits on stored memory values
- TTL enforcement for automatic cleanup

### Deprecated
- Bash-only memory hooks (replaced by Python + wrapper)
- Manual skill copying (use aggregation pipeline only)
- Hardcoded paths in configs (use env vars)
- Fake fallback data (always generate from source)

---

## [1.0.0] - 2026-10-15 (Implicit - Pre-Unification)

### Added
- Initial unified integration concept
- Basic setup.sh with agent detection
- Skills aggregation from agentic-awesome-skills
- Memory system with SQLite
- Compression with headroom
- Agent config generation (8 agents)
- Universal launcher script
- Skills loader utility
- Memory utility
- Compression utility

### Known Issues (Fixed in 2.0.0)
- 20-skill limit per source
- Date expansion bug
- Incomplete skill aggregation
- Wrong categorization
- Partial skill copying
- SQL injection in hooks
- Hardcoded paths
- Fake fallback counts
- Prompt path mismatches
- Headroom detection issues

---

## Upgrade Guide: 1.x → 2.0

### Breaking Changes
1. **Config paths changed**: All agent configs regenerated
2. **Memory hooks rewritten**: Python required (was bash-only)
3. **Skills index schema changed**: New fields (agent_skill_counts, when_to_use)
4. **Setup script renamed**: setup-fixed.sh → setup.sh
3. **Documentation moved**: Now in docs/ directory

### Migration Steps
```bash
# 1. Backup current configs
cp -r ~/.claude ~/.claude.backup
cp -r ~/.codex ~/.codex.backup
# ... etc

# 2. Run new setup
/root/agent-enhancements/unified-integration/setup.sh

# 3. Verify all agents work
/root/agent-enhancements/unified-integration/launch-agent.sh claude-code --version

# 4. Restore any customizations from backup
```

### Rollback
```bash
# If issues, restore from backup
rm -rf ~/.claude ~/.codex ~/.config/opencode ~/.cursor ~/.gemini ~/.windsurf ~/.config/github-copilot ~/.kiro
cp -r ~/.claude.backup ~/.claude
# ... etc
```

---

## Future Roadmap

### 2.1 (Planned)
- Web UI for skill browsing
- Skill effectiveness analytics
- Cross-agent memory sharing (opt-in)
- Parallel skill aggregation

### 2.2 (Planned)
- Plugin system for custom engines
- Remote memory backend (Redis)
- Skill marketplace integration
- Agent performance benchmarks

### 3.0 (Vision)
- Multi-repo skill federation
- AI-assisted skill generation
- Real-time skill updates
- Enterprise SSO integration

---

**End of Changelog**