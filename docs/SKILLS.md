# Skills System Documentation

**Version**: 2.0  
**Last Updated**: 2026-11-01  
**Audience**: All agents, skill authors

---

## 1. Overview

The skills system provides **3,127+ curated skills** aggregated from 4 upstream sources, organized for automatic discovery and agent-neutral consumption.

### 1.1 Sources

| Source | Skills | Description |
|--------|--------|-------------|
| agentic-awesome-skills | 2,791 | Primary community-curated skills |
| ECC | 314 | Enterprise-grade agent skills |
| Ponytail | 7 | Lightweight utility skills |
| Superpowers | 15 | Agent workflow skills |

### 1.2 Total by Category

| Category | Count | Description |
|----------|-------|-------------|
| security | ~180 | Auditing, hardening, threat modeling |
| architecture | ~220 | System design, patterns, decisions |
| testing | ~190 | TDD, integration, property-based |
| refactoring | ~130 | Code cleanup, modernization |
| code-review | ~100 | Review practices, checklists |
| documentation | ~90 | Technical writing, API docs |
| devops | ~170 | CI/CD, deployment, infrastructure |
| ai-ml | ~210 | ML pipelines, model ops, prompts |
| productivity | ~320 | Workflows, automation, tools |
| general | ~1,517 | Miscellaneous, cross-cutting |

---

## 2. Skill Format (SKILL.md)

### 2.1 Required Frontmatter

```yaml
---
name: "unique-skill-id"              # kebab-case, unique across all sources
description: "One-line summary of what this skill does and when to use it"
risk: "safe|medium|critical"         # safe=read-only, medium=may modify, critical=high impact
source: "agentic-awesome-skills"     # Origin: agentic-awesome-skills, ECC, Ponytail, Superpowers
date_added: "2026-11-01"             # ISO 8601 date
author: "author-name"                # Original author (optional)
category: "security"                 # One of the 10 standard categories
tags:                                # Searchable keywords
  - "security"
  - "audit"
  - "owasp"
tools:                               # Compatible agents (subset of 8)
  - "claude-code"
  - "codex"
  - "cursor"
---
```

### 2.2 Required Sections

Every SKILL.md MUST contain:

```markdown
# Skill Title

Brief overview paragraph.

## When to Use This Skill

- Specific trigger condition 1
- Specific trigger condition 2
- Keywords that should activate this skill

## When NOT to Use This Skill

- Conditions where this skill is inappropriate
- Simpler alternatives

## Limitations

- Scope boundaries
- What this skill does NOT do
- Required permissions/inputs

## Detailed Guide

Reference to detailed guide file:
Read [the detailed guide](references/detailed-guide.md) before executing this skill.

## Examples

### Example 1: Basic Usage
```bash
# Command or code example
```

### Example 2: Advanced Usage
```python
# Code example
```

## Verification Checklist

Before marking work complete:
- [ ] Checklist item 1
- [ ] Checklist item 2
```

---

## 3. Directory Structure

### 3.1 Source Layout (Upstream)

Each source has its own structure:
```
agentic-awesome-skills/
├── skills/
│   ├── skill-name-1/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   └── scripts/
│   └── skill-name-2/
│       ├── SKILL.md
│       └── references/

ECC/
├── skills/
│   ├── skill-name/
│   │   └── SKILL.md
```

### 3.2 Unified Layout (After Aggregation)

```
unified-integration/skills/
├── all-skills.json              # Master index (canonical)
├── by-category/
│   ├── security/
│   │   ├── skill-name-1/        # Full skill directory copied
│   │   │   ├── SKILL.md
│   │   │   ├── references/
│   │   │   └── scripts/
│   │   └── skill-name-2/
│   ├── architecture/
│   └── ...
└── by-agent/
    ├── claude-code/
    │   ├── skill-name-1/        # Copy for claude-code compatible skills
    │   └── skill-name-3/
    ├── codex/
    └── ...
```

---

## 4. Aggregation Pipeline

### 4.1 Process (`aggregate_skills()` in setup.sh)

```bash
# For each source:
process_skills_source "source-name" "/path/to/source/skills"

process_skills_source() {
    # 1. Find all directories containing SKILL.md
    find "$source_dir" -mindepth 1 -maxdepth 1 -type d | while read skill_dir; do
        if [ -f "$skill_dir/SKILL.md" ]; then
            # 2. Parse frontmatter
            skill_name=$(get_skill_name)
            skill_category=$(get_skill_category)
            skill_tags=$(get_skill_tags)
            skill_tools=$(get_skill_tools)
            
            # 3. Normalize category
            case "$skill_category" in
                security|architecture|testing|...) ;;
                *) skill_category="general" ;;
            esac
            
            # 4. Copy ENTIRE directory (recursive)
            cp -r "$skill_dir" "by-category/$skill_category/$skill_name"
            
            # 5. Copy to agent-specific dirs
            for tool in $skill_tools; do
                cp -r "$skill_dir" "by-agent/$tool/$skill_name"
            done
            
            # 6. Add to unified JSON index
            python3 -c "add_to_index(...)"
        fi
    done
}
```

### 4.2 Output: all-skills.json

```json
{
  "version": "1.0",
  "sources": ["agentic-awesome-skills", "ECC", "Ponytail", "Superpowers"],
  "skills": [
    {
      "name": "skill-name",
      "category": "security",
      "description": "Skill description...",
      "risk": "critical",
      "source": "agentic-awesome-skills",
      "tags": ["security", "audit", "owasp"],
      "tools": ["claude-code", "codex", "cursor"],
      "when_to_use": "Skill description..."
    }
  ],
  "total_skills": 3127,
  "categories": {
    "security": 180,
    "architecture": 220,
    ...
  },
  "agent_skill_counts": {
    "claude-code": 2800,
    "codex": 2750,
    ...
  },
  "last_updated": "2026-11-01T12:00:00Z"
}
```

---

## 5. Skill Discovery & Loading

### 5.1 Automatic (Agent-Side)

Agents should auto-load skills based on task keywords:

```python
# In agent's context loading:
loader = SkillsLoader(agent="claude-code")
skills = loader.find_skills("security audit of authentication system")

# Returns top 5 matching skills with scores
```

### 5.2 Manual (User-Side)

```bash
# List all skills
python3 scripts/load-skills.py claude-code "list all"

# Search by keyword
python3 scripts/load-skills.py claude-code "refactor legacy code"

# Load specific skill
python3 scripts/load-skills.py claude-code "007"
```

### 5.3 Scoring Algorithm

```
Score = 0
+2 per keyword match in when_to_use
+3 per tag match
+1 per keyword match in description
+5 if agent in skill.tools
```

---

## 6. Adding New Skills

### 6.1 To Upstream Sources

**Preferred**: Contribute to upstream (agentic-awesome-skills, ECC, etc.)
- Follow their contribution guidelines
- Wait for merge and release
- Run `update-skills.sh` to pull

### 6.2 Local Override (Not Recommended)

If absolutely necessary:
1. Create skill directory under a new source: `local-skills/my-skill/`
2. Add `SKILL.md` with full frontmatter
3. Add to `setup.sh` aggregation:
   ```bash
   process_skills_source "local" "$BASE_DIR/local-skills"
   ```
4. Run `setup.sh`

### 6.3 Skill Validation

Before adding, validate:
```bash
# Check frontmatter
python3 -c "
import yaml
with open('SKILL.md') as f:
    content = f.read()
    if content.startswith('---'):
        fm = yaml.safe_load(content.split('---')[1])
        required = ['name', 'description', 'risk', 'source', 'date_added', 'category', 'tools']
        for r in required:
            assert r in fm, f'Missing: {r}'
        assert fm['risk'] in ['safe', 'medium', 'critical']
        assert fm['category'] in ['security', 'architecture', 'testing', 'refactoring', 'code-review', 'documentation', 'devops', 'ai-ml', 'productivity', 'general']
        print('VALID')
"
```

---

## 7. Skill Categories Reference

### 7.1 Security
- Vulnerability scanning
- Code auditing
- Threat modeling (STRIDE, PASTA)
- OWASP compliance
- Penetration testing
- Secret detection
- Supply chain security

### 7.2 Architecture
- System design patterns
- Microservices vs monolith
- Database design
- API design (REST, GraphQL, gRPC)
- Event-driven architecture
- CQRS, Event Sourcing

### 7.3 Testing
- TDD workflows
- Property-based testing
- Contract testing
- Mutation testing
- Integration testing
- E2E testing
- Test data management

### 7.4 Refactoring
- Code smells detection
- Legacy modernization
- Dependency updates
- Dead code removal
- Performance optimization
- Technical debt management

### 7.5 Code Review
- Review checklists
- Security review
- Performance review
- Architecture review
- Automated review tools

### 7.6 Documentation
- API documentation
- Architecture decision records
- Runbook creation
- Technical specifications
- User guides

### 7.7 DevOps
- CI/CD pipelines
- Infrastructure as Code
- Kubernetes operations
- Monitoring & alerting
- Deployment strategies
- Incident response

### 7.8 AI/ML
- Model training workflows
- Prompt engineering
- RAG pipelines
- Model evaluation
- MLOps
- Feature engineering

### 7.9 Productivity
- Git workflows
- Terminal automation
- Code generation
- Debugging techniques
- Learning/onboarding

### 7.10 General
- Cross-cutting concerns
- Meta-skills
- Tool-specific skills

---

## 8. Best Practices

### 8.1 For Skill Authors
1. **One skill, one purpose** - Don't combine unrelated capabilities
2. **Clear triggers** - `When to Use` must be specific and actionable
3. **Complete frontmatter** - All fields required for proper indexing
4. **Include references** - Link to detailed guides, not inline everything
5. **Test compatibility** - Verify `tools` list matches actual support

### 8.2 For Agents
1. **Trust the index** - Use `all-skills.json` for discovery
2. **Filter by agent** - Only load skills where `agent in tools`
3. **Score intelligently** - Use tags > description > when_to_use
4. **Cache results** - Don't re-parse on every task

### 8.3 For Maintainers
1. **Monthly updates** - Run `update-skills.sh` regularly
2. **Validate counts** - Check `total_skills` matches expectation
3. **Monitor categories** - Ensure no category dominates
4. **Audit tools list** - Verify agent compatibility stays current

---

## 9. Troubleshooting Skills

| Issue | Cause | Solution |
|-------|-------|----------|
| Skill not found | Not in all-skills.json | Re-run `setup.sh` |
| Wrong category | Frontmatter category invalid | Fix SKILL.md frontmatter |
| Not loading for agent | Agent not in `tools` | Add agent to tools array |
| Missing references | Directory not copied recursively | Check `cp -r` in setup.sh |
| Duplicate skills | Same name in multiple sources | Namespacing or deduplication |

---

## 10. Migration Guide

### From v1 (Pre-Unified)
- Old: Separate skill dirs per source
- New: Unified `all-skills.json` + `by-category/` + `by-agent/`
- Migration: Re-run `setup.sh` - automatic

### Adding New Source
1. Clone source to `$BASE_DIR/new-source/`
2. Ensure skills have SKILL.md with frontmatter
3. Add to `setup.sh` aggregation
4. Test with `setup.sh`
5. Commit changes

---

**End of Skills Documentation**