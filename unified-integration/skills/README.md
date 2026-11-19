# Unified Skills Registry

This directory contains aggregated skills from multiple sources:

1. **agentic-awesome-skills** - primary skill source
2. **ECC** - Additional skills and commands
3. **Ponytail** - Additional skills and hooks
4. **Superpowers** - Additional skills
5. **replica-skill** - app-cloning sub-skills
6. **anthropic-skills** - official Anthropic skills (docx, pdf, pptx,
   xlsx, skill-creator, mcp-builder, webapp-testing, claude-api, ...)
7. **agency-agents** - AI-persona skills from The Agency (division bundles,
   converted to Agent Skills format by scripts/convert_agency_agents.py)
8. **task-observer** - vendored ambient skill-observation meta-skill
   (rebelytics/one-skill-to-rule-them-all, CC-BY-4.0, pinned; root-layout
   source: one skill bundle whose SKILL.md sits at the source root)

Current counts are generated from the canonical index and catalogs in
[the capability inventory](../../docs/CAPABILITY_COUNTS.md). The index below
is the source of truth for the skills available in this installation.

## Structure

```text
skills/
├── by-category/
│   ├── security/
│   ├── architecture/
│   ├── testing/
│   ├── refactoring/
│   ├── code-review/
│   ├── documentation/
│   ├── devops/
│   ├── ai-ml/
│   └── productivity/
├── by-agent/
│   ├── claude-code/
│   ├── codex/
│   ├── cursor/
│   ├── gemini-cli/
│   ├── opencode/
│   ├── copilot/
│   ├── windsurf/
│   ├── kiro/
│   └── hermes/
└── all-skills.json
```

## Usage

Skills are in SKILL.md format with frontmatter:

- name, description, risk, source, date_added, author, tags, tools (compatible
  agents)

To use a skill, the agent should:

1. Match task keywords to skill's "When to Use" section
2. Load the skill's detailed guide
3. Apply the skill's patterns and procedures
