---
title: Skills
version: 1.1
last_updated: 2026-11-01
audience: users, contributors
---

# Skills

## Sources

| Source | Directory | Notes |
|--------|-----------|-------|
| agentic-awesome-skills | `agentic-awesome-skills/skills/` | primary, 2,884 skills |
| ECC | `ECC/skills/` | |
| Ponytail | `ponytail/skills/` | |
| Superpowers | `superpowers/skills/` | |

## SKILL.md frontmatter

Skills are discovered by the presence of a `SKILL.md` with YAML frontmatter:

```yaml
---
name: my-skill
category: security        # normalized to one of the 10 canonical buckets
description: What this skill does
risk: safe                # defaults to "safe"
tags:
  - security
  - audit
tools:                    # compatible agents; unknown values are indexed
  - claude-code           # but do not create by-agent directories
---
```

Category normalization (anything else falls back to `general`):
`security`, `architecture`, `testing`, `refactoring`, `code-review`,
`documentation`, `devops`, `ai-ml`, `productivity`, `general`.

## Aggregation rules (R301-R304)

- Skills are aggregated **only** via `aggregate_skills()` in `setup.sh` -
  never copied manually (R004).
- The whole skill directory is copied recursively, not just SKILL.md (R303).
- Copies are idempotent: an existing target is removed before the copy, so
  re-running `setup.sh` never nests or duplicates trees.
- The unified index is rebuilt from scratch on every run (R304); skill
  metadata travels through a record file, never through code interpolation.
- `by-agent/` is populated only for the canonical agents: `claude-code`,
  `codex`, `cursor`, `gemini-cli`, `opencode`, `copilot`, `windsurf`,
  `kiro`.

## Using skills

```bash
# find skills for a task
python3 unified-integration/scripts/load-skills.py claude-code "security audit"

# inside Claude Code
/skill code-review --effort high
/skill --list
```

The loader supports two on-disk layouts: directory skills
(`by-category/<cat>/<name>/SKILL.md`) and legacy flat skills
(`by-category/<cat>/<name>.md`).

## Updating skills

Run `unified-integration/update-skills.sh`. Vendored directories that are
not git repositories are skipped with a warning - refresh them by
re-copying from upstream per [UPDATING.md](UPDATING.md).
