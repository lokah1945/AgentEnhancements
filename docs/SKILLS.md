---
title: Skills
version: 1.2
last_updated: 2026-11-13
audience: users, contributors
---

# Skills

## Sources

| Source | Directory | Notes |
|--------|-----------|-------|
| agentic-awesome-skills | `agentic-awesome-skills/skills/` | primary source |
| ECC | `ECC/skills/` | |
| Ponytail | `ponytail/skills/` | |
| Superpowers | `superpowers/skills/` | |
| replica-skill | `replica-skill/` | 11 app-cloning sub-skills (repo-root layout) |
| anthropic-skills | `anthropic-skills/skills/` | 19 official Anthropic skills (docx, pdf, pptx, xlsx, skill-creator, mcp-builder, webapp-testing, claude-api, ...); processed LAST so the official version wins name collisions |

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
- The index is keyed by skill name: when two sources ship the same name, the
  LATER source in the aggregation order wins (mirroring the directory
  overwrite). anthropic-skills runs last, so official copies replace
  third-party versions of the same skill.
- Frontmatter is re-parsed from the SKILL.md file (PyYAML or built-in
  parser) so multi-line YAML values (block scalars like `>-`) become real
  descriptions.
- `by-agent/` is populated only for the canonical agents: `claude-code`,
  `codex`, `cursor`, `gemini-cli`, `opencode`, `copilot`, `windsurf`,
  `kiro`.

## Native activation (auto-discovery at runtime)

`setup.sh` symlinks a curated set into the directories that Agent Skills
compatible harnesses read automatically:

- `~/.claude/skills/` - Claude Code personal skills
- `~/.agents/skills/` - cross-agent Agent Skills standard (agentskills.io)

Default curated set: **anthropic-skills (19) + replica-skill (11)**.

```bash
bash unified-integration/scripts/link-skills.sh                    # default set
bash unified-integration/scripts/link-skills.sh --set superpowers  # one source
bash unified-integration/scripts/link-skills.sh <skill-name>       # specific skills
bash unified-integration/scripts/link-skills.sh --set all          # everything
bash unified-integration/scripts/link-skills.sh --status
bash unified-integration/scripts/link-skills.sh --unlink [names]
```

Only symlinks owned by the registry are created, refreshed or removed;
user-owned directories, files and foreign symlinks are never touched.

## Using skills

```bash
# map a task to skills + plugins + MCP servers (recommended)
python3 unified-integration/scripts/registry.py map "clean this excel spreadsheet"

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
