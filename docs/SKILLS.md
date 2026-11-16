---
title: Skills
version: 1.4
last_updated: 2026-11-16
audience: users, contributors
---

# Skills

## Sources

| Source | Directory | Notes |
| -------- | ----------- | ------- |
| agentic-awesome-skills | `agentic-awesome-skills/skills/` | primary source |
| ECC | `ECC/skills/` | |
| Ponytail | `ponytail/skills/` | |
| Superpowers | `superpowers/skills/` | |
| replica-skill | `replica-skill/` | 11 app-cloning sub-skills (repo-root layout) |
| agency-agents | `agency-agents/skills/` | 283 The Agency personas in 18 division subdirectories (converted from the vendored upstream by `scripts/convert_agency_agents.py`); names are prefixed `agency-` so they never collide |
| anthropic-skills | `anthropic-skills/skills/` | 19 official Anthropic skills (docx, pdf, pptx, xlsx, skill-creator, mcp-builder, webapp-testing, claude-api, ...); processed LAST so the official version wins name collisions |
| task-observer | `task-observer/` | the ambient skill-observation meta-skill (rebelytics/one-skill-to-rule-them-all, CC-BY-4.0, pinned; see [TASK_OBSERVER.md](TASK_OBSERVER.md)); **root-layout source**: its SKILL.md sits at the source root and is aggregated as a single skill |

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
  `kiro`, `hermes`.

## Native activation (auto-discovery at runtime)

`setup.sh` symlinks a curated set into the directories that Agent Skills
compatible harnesses read automatically:

- `~/.claude/skills/` - Claude Code personal skills
- `~/.codex/skills/` - Codex native skills
- `~/.config/opencode/skills/` - OpenCode native skills
- `~/.agents/skills/` - cross-agent Agent Skills standard (agentskills.io)

Default set: **task-observer (1) + Superpowers (15)** = 16 skills. The optional
`--set curated` collection selects anthropic-skills (19), replica-skill (11)
and task-observer (1).

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

**Skill discovery is flexible**: default 8 skill cards per prompt, configurable via `AE_MAX_SKILL_CARDS` env var. Agents decide which skills to actually read/use from the suggestions.

## Using skills

After setup, normal natural-language tasks trigger native discovery and prompt
routing automatically in Claude Code, current Codex, OpenCode 2 and selected
Hermes profiles. The default set supplies bounded workflow metadata;
prompt-time routing searches the complete
3,378-skill catalog without injecting all descriptions into every request.
Matching is lexical with a small English/Indonesian alias set, so recommendations
are guidance, not a guarantee that every task will select the ideal skill.
Agent aliases such as `Codex`/`codex-cli` are normalized during matching; tools
such as `python` are not mistaken for incompatible agent names.

The following commands are optional inspection/debugging utilities:

```bash
# map a task to skills + plugins + MCP servers (recommended)
python3 unified-integration/scripts/registry.py map "clean this excel spreadsheet"

# find skills for a task
python3 unified-integration/scripts/load-skills.py claude-code "security audit"

# inspect native links
bash unified-integration/scripts/link-skills.sh --status
```

The loader supports two on-disk layouts: directory skills
(`by-category/<cat>/<name>/SKILL.md`) and legacy flat skills
(`by-category/<cat>/<name>.md`).

## Updating skills

Run `unified-integration/update-skills.sh`. Vendored directories that are
not git repositories are skipped with a warning - refresh them by
re-copying from upstream per [UPDATING.md](UPDATING.md).
