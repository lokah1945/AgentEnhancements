# AgentEnhancements

A unified integration platform that aggregates essential AI agent skills, tools, and configurations from multiple open-source projects into a single, cohesive developer experience. This project eliminates the need to install and configure each component individually.

## Overview

AgentEnhancements brings together 7 complementary projects that enhance AI coding agents (Claude Code, Cursor, Windsurf, Copilot, etc.) with:

- **2788+ specialized skills/agents** for every development task
- **Context compression & memory management** for long-running sessions
- **System prompts** optimized for each AI tool
- **Unified configuration** that works across all major AI coding assistants

---

## Included Projects

| Project | Description | Key Features |
|---------|-------------|--------------|
| **[agentic-awesome-skills](./agentic-awesome-skills)** | Massive curated collection of AI agent skills | 2788 skills, categorized by domain, auto-installable plugins |
| **[claude-mem](./claude-mem)** | Persistent memory layer for AI agents | Cross-session memory, automatic summarization, multi-agent support |
| **[ECC](./ECC)** | Enhanced Claude Code configuration | 316 skills, custom commands, hooks, MCP servers, dashboards |
| **[headroom](./headroom)** | Context compression & token budget management | Rust-based, 75% trigger, 200k budget, proxy server |
| **[ponytail](./ponytail)** | Skills framework & plugin system | Cross-platform skills, hook integration, multiple AI tool support |
| **[superpowers](./superpowers)** | Developer productivity skills collection | 17 skill categories, automated workflows, team sharing |
| **[system-prompts-and-models-of-ai-tools](./system-prompts-and-models-of-ai-tools)** | Reference system prompts from 25+ AI tools | Anthropic, Cursor, Windsurf, Copilot, Devin, and more |

---

## Quick Start

### One-Line Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/lokah1945/agent-enhancements/main/unified-integration/setup.sh | bash
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/lokah1945/agent-enhancements.git
cd agent-enhancements

# Run the unified setup
./unified-integration/setup.sh
```

The setup script will:
1. Detect your AI coding assistants (Claude Code, Cursor, Windsurf, etc.)
2. Install relevant skills from all 7 projects
3. Configure system prompts for each detected tool
4. Set up memory persistence (claude-mem)
5. Enable context compression (headroom)
6. Configure hooks for automatic memory save/compression

---

## Architecture

```
agent-enhancements/
├── unified-integration/           # Main integration layer
│   ├── setup.sh                   # One-line installer
│   ├── launch-agent.sh            # Agent launcher with env config
│   ├── config/                    # Shared configurations
│   ├── prompts/                   # System prompts per AI tool
│   ├── skills/                    # Aggregated skills index
│   │   ├── by-category/           # Skills organized by domain
│   │   ├── by-agent/              # Skills organized by agent type
│   │   ├── all-skills.json        # Complete skills catalog
│   │   └── agentic-awesome-skills-index.json
│   ├── memory/                    # Memory integration (claude-mem)
│   ├── compression/               # Context compression (headroom)
│   └── scripts/                   # Utility scripts
│
├── agentic-awesome-skills/        # 2788 skills, plugins, catalog
├── claude-mem/                    # Memory persistence layer
├── ECC/                           # Enhanced Claude Code config
├── headroom/                      # Context compression (Rust)
├── ponytail/                      # Skills framework
├── superpowers/                   # Productivity skills
└── system-prompts-and-models-of-ai-tools/  # Reference prompts
```

---

## Skills Catalog

Skills are organized into 10 categories with 2788+ total skills:

| Category | Count | Examples |
|----------|-------|----------|
| **AI/ML** | 200+ | Model training, RAG pipelines, LLM optimization |
| **Architecture** | 150+ | System design, DDD, microservices, event-driven |
| **Code Review** | 180+ | Security audit, performance, best practices |
| **DevOps** | 220+ | CI/CD, Kubernetes, Terraform, monitoring |
| **Documentation** | 120+ | API docs, README generation, ADRs |
| **General** | 300+ | Research, planning, debugging, refactoring |
| **Productivity** | 400+ | Task management, automation, shortcuts |
| **Refactoring** | 250+ | Rust, TypeScript, legacy modernization |
| **Security** | 280+ | Penetration testing, secrets, compliance |
| **Testing** | 200+ | E2E, unit, property-based, contract testing |

### Using Skills

Skills auto-load based on your project context. Explicit invocation:

```bash
# In Claude Code
/skill code-review --effort high

# List available skills
/skill --list

# Search skills
/skill --search "security audit"
```

---

## Memory System (claude-mem)

Persistent, cross-session memory that survives agent restarts:

```bash
# Automatic - memories save on:
# - Task completion
# - Key decisions made
# - Session end

# Manual memory operations
/remember "User prefers TypeScript strict mode"
/recall "typescript preferences"
/forget "outdated decision"
```

Memory is stored in `.claude/memory/` per project, with global memories in `~/.claude/memory/`.

---

## Context Compression (headroom)

Automatic token budget management for long conversations:

- **Budget**: 200,000 tokens
- **Trigger**: 75% utilization (150k tokens)
- **Compression**: Summarizes old context, preserves recent + critical info
- **Proxy Mode**: Works as transparent proxy for any AI API

```bash
# Start headroom proxy
headroom proxy --port 8080 --target https://api.anthropic.com

# Use with any client
export ANTHROPIC_BASE_URL=http://localhost:8080
```

---

## System Prompts

Optimized system prompts for each AI coding assistant:

| Tool | Prompt File |
|------|-------------|
| Claude Code | `unified-integration/prompts/claude-code-system-prompt.txt` |
| Cursor | `unified-integration/prompts/cursor-system-prompt.txt` |
| Windsurf | `unified-integration/prompts/windsurf-system-prompt.txt` |
| GitHub Copilot | `unified-integration/prompts/copilot-system-prompt.txt` |
| Codex | `unified-integration/prompts/codex-system-prompt.txt` |
| Gemini CLI | `unified-integration/prompts/gemini-cli-system-prompt.txt` |
| Kiro | `unified-integration/prompts/kiro-system-prompt.txt` |
| OpenCode | `unified-integration/prompts/opencode-system-prompt.txt` |
| Universal | `unified-integration/prompts/universal-system-prompt.txt` |

---

## Configuration

### Global Config (`~/.claude/settings.json`)

```json
{
  "skills": {
    "autoLoad": true,
    "categories": ["all"],
    "customPaths": ["~/agent-enhancements/unified-integration/skills"]
  },
  "memory": {
    "enabled": true,
    "autoSave": ["task_complete", "decision_made", "session_end"],
    "plugin": "~/.claude/plugins/claude-mem"
  },
  "compression": {
    "enabled": true,
    "budget": 200000,
    "triggerPercent": 75,
    "proxy": "headroom"
  },
  "hooks": {
    "PreToolUse": ["memory_save", "context_compress"],
    "PostToolUse": ["memory_save"],
    "Stop": ["memory_save"]
  }
}
```

### Per-Project Config (`.claude/settings.local.json`)

```json
{
  "skills": {
    "enabled": ["code-review", "security", "testing", "refactoring"]
  },
  "memory": {
    "projectMemories": true
  }
}
```

---

## MCP Servers

The following MCP servers are pre-configured:

| Server | Purpose | Auto-Connect |
|--------|---------|--------------|
| **headroom** | Context compression proxy | Yes |
| **skills-loader** | Dynamic skill loading | Yes |
| **memory** | Persistent memory access | Yes |

Add custom MCP servers in `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "npx",
      "args": ["-y", "@my/mcp-server"]
    }
  }
}
```

---

## Contributing

This is an aggregation project. To contribute:

1. **Upstream projects**: Contribute to the original repositories
2. **Integration layer**: Improve `unified-integration/` scripts and configs
3. **Documentation**: Enhance this README and guides

### Referenced Projects (Upstream)

| Project | Repository | License |
|---------|------------|---------|
| agentic-awesome-skills | [Original Repo](https://github.com/agentic-awesome/agentic-awesome-skills) | MIT |
| claude-mem | [Original Repo](https://github.com/claude-mem/claude-mem) | MIT |
| ECC | [Original Repo](https://github.com/ecc-project/ecc) | MIT |
| headroom | [Original Repo](https://github.com/headroom/headroom) | MIT/Apache-2.0 |
| ponytail | [Original Repo](https://github.com/ponytail/ponytail) | MIT |
| superpowers | [Original Repo](https://github.com/superpowers/superpowers) | MIT |
| system-prompts-and-models-of-ai-tools | [Original Repo](https://github.com/system-prompts/system-prompts-and-models-of-ai-tools) | CC-BY-4.0 |

> **Note**: This repository contains copies of the above projects for unified distribution. They are **not forks** — they are vendored dependencies. For changes to individual projects, please contribute upstream.

---

## License

This aggregation is released under **MIT License**. Individual projects retain their original licenses (see table above).

---

## Support

- **Issues**: [GitHub Issues](https://github.com/lokah1945/agent-enhancements/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lokah1945/agent-enhancements/discussions)
- **Documentation**: See `docs/` folder and individual project READMEs

---

## Acknowledgments

Built on the incredible work of the open-source AI tooling community. Special thanks to the maintainers of all 7 integrated projects for making their work available for composition.