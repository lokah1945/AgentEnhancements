# Contributing Guide

**Version**: 2.0  
**Last Updated**: 2026-11-01  
**Audience**: All contributors, agents, maintainers

---

## 1. Governance

This project operates under the **Agent Development Contract (CONTRACT.md)**. All contributions MUST comply with its rules. Read it first.

---

## 2. Ways to Contribute

### 2.1 Bug Reports
- Use the issue template
- Include: agent, command, error output, diagnostics
- Run troubleshooting steps first

### 2.2 Feature Requests
- Describe the problem, not just the solution
- Explain which agents benefit
- Consider backward compatibility

### 2.3 Code Changes
- Follow the workflow in Section 4
- One logical change per PR
- Tests required for new functionality

### 2.4 Skill Contributions
- **Preferred**: Contribute to upstream sources (agentic-awesome-skills, ECC, etc.)
- **Local**: Add to `local-skills/` and update setup.sh
- See `SKILLS.md` for format requirements

### 2.5 Documentation
- Update relevant docs/ files for any interface change
- Follow style guide in Section 6

---

## 3. Development Environment

### 3.1 Prerequisites
```bash
# Required
bash 4.0+
python3 3.8+
sqlite3
git

# For headroom
rust 1.70+ (cargo)

# For claude-mem
node 18+ (npm/bun)

# For ECC tests
node 18+ (npm)
```

### 3.2 Setup
```bash
# Clone
git clone <repo-url>
cd agent-enhancements

# Install dependencies
cd headroom && cargo build --release
cd ../claude-mem && npm install
cd ../ECC && npm install

# Verify
bash -n unified-integration/setup.sh
python3 -m py_compile unified-integration/scripts/*.py
```

---

## 4. Contribution Workflow

### 4.1 Standard Flow
```bash
# 1. Create branch
git checkout -b type/short-description
# Types: fix, feat, docs, refactor, chore, test

# 2. Make changes
# - Minimal, focused
# - Follow code standards (Section 5)
# - Update docs/ if interface changes

# 3. Test
cd ECC && node tests/run-all.js
# Must pass all tests

# 4. Commit
git add .
git commit -m "type(scope): description"
# See Section 5.1 for commit format

# 5. Push & PR
git push origin type/short-description
# Create PR with description
```

### 4.2 Skill Update Flow
```bash
# Monthly or on-demand
./unified-integration/update-skills.sh

# Review changes
git diff unified-integration/skills/

# Regenerate configs
./unified-integration/setup.sh

# Commit
git commit -m "chore(skills): update from upstream sources"
```

### 4.3 Hotfix Flow
```bash
# Critical production issue only
git checkout -b hotfix/critical-bug main
# Minimal fix only
git commit -m "fix(scope): critical one-line description"
# Push, PR, merge immediately
```

---

## 5. Code Standards

### 5.1 Commit Messages (Conventional Commits)

```
type(scope): subject

body (optional)

footer (optional)
```

**Types**:
| Type | Use For |
|------|---------|
| fix | Bug fix |
| feat | New feature |
| docs | Documentation only |
| refactor | Code restructuring |
| chore | Maintenance, deps, build |
| test | Test additions/changes |
| style | Formatting, no logic change |

**Scopes**:
| Scope | Area |
|-------|------|
| setup | setup.sh, update-skills.sh |
| skills | Aggregation, index, loader |
| memory | SQLite, hooks, config |
| compression | headroom, fallback, config |
| prompts | System prompts, detection |
| agents | Agent configs, launcher |
| scripts | load-skills.py, memory.py, compress.py |
| docs | Documentation in docs/ |
| deps | Dependency updates |

**Examples**:
```
fix(memory): prevent SQL injection in hooks
feat(skills): add Ponytail source to aggregation
docs(config): add HEADROOM_BIN env var documentation
refactor(setup): extract skill parsing to functions
chore(deps): update headroom to latest rust edition
```

### 5.2 Bash Standards
```bash
# File header
#!/bin/bash
# Description
# Author: ...

# Strict mode
set -euo pipefail

# Functions for logging
log_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
log_warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }
log_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

# No global mutable state
# Use local variables in functions
# Quote all variables: "$VAR"
# Use functions, not inline code blocks
```

### 5.3 Python Standards
```python
#!/usr/bin/env python3
"""
Module description.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Type hints required
def function_name(param: str) -> Dict[str, Any]:
    """Docstring with args, returns, raises."""
    pass

if __name__ == "__main__":
    # Entry point
    pass
```

### 5.4 YAML/JSON Standards
- 2-space indentation
- No trailing spaces
- Consistent quoting (double for YAML strings with special chars)
- Sort keys alphabetically in JSON

---

## 6. Documentation Style

### 6.1 Markdown Standards
- Frontmatter on all docs:
  ```markdown
  ---
  title: "Document Title"
  version: "2.0"
  last_updated: "2026-11-01"
  audience: "users|agents|devops|all"
  ---
  ```
- Headers: `# H1`, `## H2`, `### H3`
- Code blocks with language: ```bash, ```python, ```yaml
- Tables for structured data
- Relative links only: `[link](OTHER.md)`
- No HTML

### 6.2 Required Updates
| Change | Update |
|--------|--------|
| New env var | CONFIGURATION.md + CONTRACT.md |
| New agent | AGENTS.md + CONTRACT.md + setup.sh |
| Schema change | ARCHITECTURE.md + CONFIGURATION.md |
| New skill source | SKILLS.md + setup.sh |
| Bug fix | TROUBLESHOOTING.md (if user-facing) |
| Any interface change | CHANGELOG.md |

---

## 7. Testing Requirements

### 7.1 Mandatory
```bash
# Before any commit
cd ECC && node tests/run-all.js
# All tests must pass

# Before PR
# Same + lint if configured
```

### 7.2 For Specific Changes
| Change | Additional Tests |
|--------|------------------|
| Hooks | Test memory hooks manually |
| Skills | Verify skill count in all-skills.json |
| Compression | Test with various input types |
| Agent configs | Verify configs generated correctly |
| Memory | Test save/load/list/cleanup |

### 7.3 Test Coverage Targets
| Component | Target |
|-----------|--------|
| Hooks | 100% |
| Skills loader | 90%+ |
| Memory | 95%+ |
| Compression | 80%+ |

---

## 8. Review Process

### 8.1 PR Requirements
- [ ] CONTRACT.md compliance
- [ ] Tests pass
- [ ] Docs updated
- [ ] Commit messages conventional
- [ ] No "fixed|new|v\d+" in filenames
- [ ] No hardcoded paths (use env vars)
- [ ] No SQL string interpolation

### 8.2 Reviewer Checklist
- [ ] Changes match PR description
- [ ] No scope creep
- [ ] Edge cases handled
- [ ] Error messages clear
- [ ] Backward compatibility maintained

### 8.3 Merge Requirements
- At least 1 approval (maintainer)
- All CI checks pass
- No merge conflicts
- Squash commits if >3 commits

---

## 9. Release Process

### 9.1 Versioning
- **Major**: Breaking schema changes
- **Minor**: New features, agents, sources
- **Patch**: Bug fixes, docs, refactoring

### 9.2 Release Steps
```bash
# 1. Update version in CONTRACT.md
# 2. Update CHANGELOG.md
# 3. Tag: git tag -a v2.1.0 -m "Release v2.1.0"
# 4. Push: git push origin v2.1.0
# 5. CI builds artifacts
```

---

## 10. Code of Conduct

### 10.1 Our Standards
- Respect all contributors
- Constructive feedback only
- No harassment, discrimination
- Focus on technical merit

### 10.2 Enforcement
- Violations → warning → temporary ban → permanent ban
- Report to maintainers

---

## 11. License

By contributing, you agree your contributions are licensed under the project's license (see LICENSE file).

---

**End of Contributing Guide**