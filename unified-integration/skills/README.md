# Unified Skills Registry

This directory contains aggregated skills from multiple sources:

1. **agentic-awesome-skills** - 2,781 skills (primary source)
2. **ECC** - Additional skills and commands
3. **Ponytail** - Additional skills and hooks
4. **Superpowers** - Additional skills
5. **replica-skill** - 11 app-cloning sub-skills
6. **anthropic-skills** - 19 official Anthropic skills (docx, pdf, pptx,
   xlsx, skill-creator, mcp-builder, webapp-testing, claude-api, ...)

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
