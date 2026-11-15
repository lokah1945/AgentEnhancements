# Unified Skills Registry

This directory contains aggregated skills from multiple sources:

1. **agentic-awesome-skills** - 2,781 skills (primary source)
2. **ECC** - Additional skills and commands
3. **Ponytail** - Additional skills and hooks
4. **Superpowers** - Additional skills
5. **replica-skill** - 11 app-cloning sub-skills
6. **anthropic-skills** - 19 official Anthropic skills (docx, pdf, pptx,
   xlsx, skill-creator, mcp-builder, webapp-testing, claude-api, ...)
7. **agency-agents** - 283 AI-persona skills from The Agency (18 divisions,
   converted to Agent Skills format by scripts/convert_agency_agents.py)
8. **task-observer** - vendored ambient skill-observation meta-skill
   (rebelytics/one-skill-to-rule-them-all, CC-BY-4.0, pinned; root-layout
   source: one skill bundle whose SKILL.md sits at the source root)

## Structure

```
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
│   └── kiro/
└── all-skills.json
```

## Usage

Skills are in SKILL.md format with frontmatter:
- name, description, risk, source, date_added, author, tags, tools (compatible agents)

To use a skill, the agent should:
1. Match task keywords to skill's "When to Use" section
2. Load the skill's detailed guide
3. Apply the skill's patterns and procedures
