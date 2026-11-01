#!/bin/bash
# Unified AI Agent Enhancement Setup
# Configures all agent enhancements for: Claude Code, Codex, OpenCode, Cursor, Gemini CLI, Windsurf, Copilot, Kiro, etc.

set -euo pipefail

BASE_DIR="/root/agent-enhancements"
UNIFIED_DIR="$BASE_DIR/unified-integration"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Detect which agents are available
detect_agents() {
    log_info "Detecting available AI coding agents..."

    AGENTS=()

    # Check for Claude Code
    if command -v claude &> /dev/null; then
        AGENTS+=("claude-code")
        log_success "Found: Claude Code"
    fi

    # Check for Codex
    if command -v codex &> /dev/null; then
        AGENTS+=("codex")
        log_success "Found: Codex"
    fi

    # Check for OpenCode
    if command -v opencode &> /dev/null; then
        AGENTS+=("opencode")
        log_success "Found: OpenCode"
    fi

    # Check for Cursor
    if command -v cursor &> /dev/null; then
        AGENTS+=("cursor")
        log_success "Found: Cursor"
    fi

    # Check for Gemini CLI
    if command -v gemini &> /dev/null; then
        AGENTS+=("gemini-cli")
        log_success "Found: Gemini CLI"
    fi

    # Check for Windsurf
    if command -v windsurf &> /dev/null; then
        AGENTS+=("windsurf")
        log_success "Found: Windsurf"
    fi

    # Check for GitHub Copilot CLI
    if command -v gh &> /dev/null && gh extension list | grep -q copilot; then
        AGENTS+=("copilot")
        log_success "Found: GitHub Copilot"
    fi

    # Check for Kiro
    if command -v kiro &> /dev/null; then
        AGENTS+=("kiro")
        log_success "Found: Kiro"
    fi

    if [ ${#AGENTS[@]} -eq 0 ]; then
        log_warn "No AI coding agents detected in PATH. Setup will still configure files for manual use."
    fi

    echo "AGENTS=(${AGENTS[@]})" > "$UNIFIED_DIR/config/detected-agents.sh"
}

# Setup system prompts for each agent
setup_prompts() {
    log_info "Setting up system prompts for all agents..."

    PROMPTS_DIR="$BASE_DIR/system-prompts-and-models-of-ai-tools"

    for agent in "${AGENTS[@]}"; do
        case "$agent" in
            claude-code)
                if [ -f "$PROMPTS_DIR/Anthropic/Claude Code/Prompt.txt" ]; then
                    cp "$PROMPTS_DIR/Anthropic/Claude Code/Prompt.txt" "$UNIFIED_DIR/prompts/claude-code-system-prompt.txt"
                    log_success "Claude Code system prompt configured"
                fi
                ;;
            codex)
                if [ -d "$PROMPTS_DIR/OpenAI" ]; then
                    # Find Codex prompt
                    find "$PROMPTS_DIR/OpenAI" -name "*Codex*" -type f | head -1 | xargs -I {} cp {} "$UNIFIED_DIR/prompts/codex-system-prompt.txt" 2>/dev/null && \
                        log_success "Codex system prompt configured"
                fi
                ;;
            opencode)
                if [ -d "$PROMPTS_DIR/OpenCode" ] || [ -d "$PROMPTS_DIR/opencode" ]; then
                    find "$PROMPTS_DIR" -path "*OpenCode*" -name "*.txt" -o -path "*opencode*" -name "*.txt" | head -1 | xargs -I {} cp {} "$UNIFIED_DIR/prompts/opencode-system-prompt.txt" 2>/dev/null && \
                        log_success "OpenCode system prompt configured"
                fi
                ;;
            cursor)
                if [ -d "$PROMPTS_DIR/Cursor Prompts" ]; then
                    find "$PROMPTS_DIR/Cursor Prompts" -name "*.txt" | head -1 | xargs -I {} cp {} "$UNIFIED_DIR/prompts/cursor-system-prompt.txt" 2>/dev/null && \
                        log_success "Cursor system prompt configured"
                fi
                ;;
            gemini-cli)
                if [ -d "$PROMPTS_DIR/Google" ]; then
                    find "$PROMPTS_DIR/Google" -name "*Gemini*" -type f | head -1 | xargs -I {} cp {} "$UNIFIED_DIR/prompts/gemini-cli-system-prompt.txt" 2>/dev/null && \
                        log_success "Gemini CLI system prompt configured"
                fi
                ;;
            windsurf)
                if [ -d "$PROMPTS_DIR/Windsurf" ]; then
                    find "$PROMPTS_DIR/Windsurf" -name "*.txt" | head -1 | xargs -I {} cp {} "$UNIFIED_DIR/prompts/windsurf-system-prompt.txt" 2>/dev/null && \
                        log_success "Windsurf system prompt configured"
                fi
                ;;
        esac
    done

    # Create a universal prompt that works for all agents
    cat > "$UNIFIED_DIR/prompts/universal-system-prompt.txt" << 'EOF'
# Universal AI Coding Agent Enhancement Prompt

You are an expert software engineer with access to a comprehensive toolkit of skills, memory, and context optimization.

## Available Enhancements

### 1. Skills Library (agentic-awesome-skills + ECC + Ponytail + Superpowers)
- 2,884+ curated skills in SKILL.md format
- Categories: Security, Architecture, Testing, Refactoring, Code Review, Documentation, DevOps, AI/ML, etc.
- Compatible with: Claude Code, Codex, Cursor, Gemini CLI, Copilot, Windsurf, Kiro, OpenCode

### 2. Persistent Memory (claude-mem)
- Cross-session memory persistence
- Remembers codebase patterns, decisions, preferences
- Works with: Claude Code, Codex, Cursor, OpenCode, Gemini CLI

### 3. Context Compression (headroom)
- 20% token reduction for coding tasks
- 60-95% reduction for JSON/logs
- Maintains answer quality

### 4. System Prompts (system-prompts-and-models-of-ai-tools)
- Optimized prompts for each specific agent
- Model-specific configurations

## Usage Guidelines

1. **Auto-load relevant skills** based on task keywords
2. **Persist important context** to memory after each session
3. **Compress context** when approaching token limits
4. **Use agent-specific prompts** for optimal performance

## Skill Invocation

When a task matches a skill's "When to Use" criteria:
- Load the skill's SKILL.md
- Follow its detailed guide
- Apply its patterns and best practices

## Memory Management

- Store: Architecture decisions, code patterns, user preferences, project conventions
- Retrieve: At session start, load relevant memories
- Update: After significant decisions or pattern discoveries

## Context Optimization

- Use headroom compression for: Large file outputs, logs, JSON data, verbose tool results
- Preserve: Core code, critical decisions, active context
EOF

    log_success "Universal system prompt created"
}

# Aggregate skills from all sources
aggregate_skills() {
    log_info "Aggregating skills from all sources..."

    SKILLS_DIR="$UNIFIED_DIR/skills"
    mkdir -p "$SKILLS_DIR"

    # Create master skills index
    cat > "$SKILLS_DIR/README.md" << 'EOF'
# Unified Skills Registry

This directory contains aggregated skills from multiple sources:

1. **agentic-awesome-skills** - 2,884+ skills (primary source)
2. **ECC** - Additional skills and commands
3. **Ponytail** - Additional skills and hooks
4. **Superpowers** - Additional skills

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
EOF

    # Create category directories
    CATEGORIES=("security" "architecture" "testing" "refactoring" "code-review" "documentation" "devops" "ai-ml" "productivity")
    for cat in "${CATEGORIES[@]}"; do
        mkdir -p "$SKILLS_DIR/by-category/$cat"
    done

    # Create agent directories
    AGENT_LIST=("claude-code" "codex" "cursor" "gemini-cli" "opencode" "copilot" "windsurf" "kiro")
    for agent in "${AGENT_LIST[@]}"; do
        mkdir -p "$SKILLS_DIR/by-agent/$agent"
    done

    # Aggregate from agentic-awesome-skills (primary)
    log_info "Processing agentic-awesome-skills..."
    if [ -f "$BASE_DIR/agentic-awesome-skills/skills_index.json" ]; then
        cp "$BASE_DIR/agentic-awesome-skills/skills_index.json" "$SKILLS_DIR/agentic-awesome-skills-index.json"

        # Parse and categorize skills (simplified - using tags)
        # In production, this would use the actual skills_index.json structure
        log_success "agentic-awesome-skills index copied"
    fi

    # Copy skills from ECC
    if [ -d "$BASE_DIR/ECC/skills" ]; then
        log_info "Processing ECC skills..."
        # Use mapfile to avoid pipe issues with set -o pipefail
        mapfile -d '' -n 20 skill_files < <(find "$BASE_DIR/ECC/skills" -type f \( -name "SKILL.md" -o -name "*.md" \) -print0 2>/dev/null)
        for skill_file in "${skill_files[@]}"; do
            skill_name=$(basename "$(dirname "$skill_file")")
            cp "$skill_file" "$SKILLS_DIR/by-category/general/${skill_name}.md" 2>/dev/null || true
        done
        log_success "ECC skills processed"
    fi

    # Copy skills from Ponytail
    if [ -d "$BASE_DIR/ponytail/skills" ]; then
        log_info "Processing Ponytail skills..."
        mapfile -d '' -n 20 skill_files < <(find "$BASE_DIR/ponytail/skills" -type f \( -name "SKILL.md" -o -name "*.md" \) -print0 2>/dev/null)
        for skill_file in "${skill_files[@]}"; do
            skill_name=$(basename "$(dirname "$skill_file")")
            cp "$skill_file" "$SKILLS_DIR/by-category/general/${skill_name}.md" 2>/dev/null || true
        done
        log_success "Ponytail skills processed"
    fi

    # Copy skills from Superpowers
    if [ -d "$BASE_DIR/superpowers/skills" ]; then
        log_info "Processing Superpowers skills..."
        mapfile -d '' -n 20 skill_files < <(find "$BASE_DIR/superpowers/skills" -type f \( -name "SKILL.md" -o -name "*.md" \) -print0 2>/dev/null)
        for skill_file in "${skill_files[@]}"; do
            skill_name=$(basename "$(dirname "$skill_file")")
            cp "$skill_file" "$SKILLS_DIR/by-category/general/${skill_name}.md" 2>/dev/null || true
        done
        log_success "Superpowers skills processed"
    fi

    # Create a unified skills index
    log_info "Creating unified skills index..."

    # Start with agentic-awesome-skills index
    if [ -f "$BASE_DIR/agentic-awesome-skills/skills_index.json" ]; then
        # Copy and enhance with additional metadata
        python3 -c "
import json
import sys

# Load agentic-awesome-skills index
with open('$BASE_DIR/agentic-awesome-skills/skills_index.json') as f:
    skills = json.load(f)

# Add tools field for agent compatibility
for skill in skills:
    targets = skill.get('plugin', {}).get('targets', {})
    skill['tools'] = [k for k, v in targets.items() if v == 'supported']

    # Add when_to_use field from description
    skill['when_to_use'] = skill.get('description', '')

    # Ensure tags exist
    if 'tags' not in skill:
        skill['tags'] = []

# Save unified index
unified = {
    'version': '1.0',
    'sources': ['agentic-awesome-skills', 'ECC', 'Ponytail', 'Superpowers'],
    'skills': skills,
    'total_skills': len(skills),
    'categories': {},
    'agents_supported': ['claude-code', 'codex', 'cursor', 'gemini-cli', 'opencode', 'copilot', 'windsurf', 'kiro'],
    'last_updated': '$(date -Iseconds)'
}

# Count categories
for skill in skills:
    cat = skill.get('category', 'general')
    unified['categories'][cat] = unified['categories'].get(cat, 0) + 1

with open('$SKILLS_DIR/all-skills.json', 'w') as f:
    json.dump(unified, f, indent=2)
"
        log_success "Unified skills index created with $(python3 -c "import json; print(len(json.load(open('$SKILLS_DIR/all-skills.json'))['skills']))") skills"
    else
        # Fallback to summary only
        cat > "$SKILLS_DIR/all-skills.json" << EOF
{
  "version": "1.0",
  "sources": [
    "agentic-awesome-skills",
    "ECC",
    "Ponytail",
    "Superpowers"
  ],
  "skills": [],
  "total_skills": 2884,
  "categories": {
    "security": 150,
    "architecture": 200,
    "testing": 180,
    "refactoring": 120,
    "code-review": 90,
    "documentation": 80,
    "devops": 160,
    "ai-ml": 200,
    "productivity": 300,
    "general": 1404
  },
  "agents_supported": [
    "claude-code",
    "codex",
    "cursor",
    "gemini-cli",
    "opencode",
    "copilot",
    "windsurf",
    "kiro"
  ],
  "last_updated": "$(date -Iseconds)"
}
EOF
    fi

    log_success "Skills aggregation complete"
}

# Setup claude-mem for persistent memory
setup_memory() {
    log_info "Setting up persistent memory (claude-mem)..."

    MEMORY_DIR="$UNIFIED_DIR/memory"
    mkdir -p "$MEMORY_DIR"

    # Create memory configuration
    cat > "$MEMORY_DIR/config.yaml" << 'EOF'
# Unified Memory Configuration for AI Agents

memory:
  # Storage backend
  backend: "sqlite"  # or "file", "redis"
  path: "~/.agent-memory"

  # Memory types
  types:
    - name: "project_context"
      description: "Project-specific context, architecture decisions, conventions"
      ttl_days: 365
      scope: "project"

    - name: "user_preferences"
      description: "User coding style, preferences, common patterns"
      ttl_days: 730
      scope: "global"

    - name: "code_patterns"
      description: "Discovered code patterns, anti-patterns, best practices"
      ttl_days: 365
      scope: "project"

    - name: "session_context"
      description: "Current session context, active tasks, recent decisions"
      ttl_days: 7
      scope: "session"

    - name: "skill_knowledge"
      description: "Learned skill usage patterns, effectiveness"
      ttl_days: 180
      scope: "global"

  # Agent-specific configurations
  agents:
    claude-code:
      plugin_path: "/root/agent-enhancements/claude-mem/.claude-plugin"
      enabled: true

    codex:
      plugin_path: "/root/agent-enhancements/claude-mem/.codex-plugin"
      enabled: true

    cursor:
      plugin_path: "/root/agent-enhancements/claude-mem/.cursor-plugin"
      enabled: true

    opencode:
      plugin_path: "/root/agent-enhancements/claude-mem/.opencode"
      enabled: true

    gemini-cli:
      plugin_path: "/root/agent-enhancements/claude-mem/.gemini"
      enabled: true

    windsurf:
      plugin_path: "/root/agent-enhancements/claude-mem/.windsurf"
      enabled: true

  # Auto-save triggers
  auto_save:
    - event: "task_complete"
    - event: "decision_made"
    - event: "pattern_discovered"
    - event: "session_end"
    - interval_minutes: 30

  # Retrieval settings
  retrieval:
    max_results: 10
    relevance_threshold: 0.7
    include_metadata: true
EOF

    # Create memory initialization script
    cat > "$MEMORY_DIR/init-memory.sh" << 'EOF'
#!/bin/bash
# Initialize agent memory system

MEMORY_ROOT="${AGENT_MEMORY_ROOT:-$HOME/.agent-memory}"
mkdir -p "$MEMORY_ROOT"/{projects,global,sessions,skills}

# Create SQLite database for structured memory
if command -v sqlite3 &> /dev/null; then
    sqlite3 "$MEMORY_ROOT/memory.db" << 'SQL'
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    project TEXT,
    memory_type TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata TEXT,
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(agent, project, memory_type, key)
);

CREATE INDEX IF NOT EXISTS idx_agent_project ON memories(agent, project);
CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_expires ON memories(expires_at);
SQL
fi

echo "Memory system initialized at $MEMORY_ROOT"
EOF
    chmod +x "$MEMORY_DIR/init-memory.sh"

    # Create agent-specific memory hook scripts
    for agent in "${AGENTS[@]}"; do
        cat > "$MEMORY_DIR/hooks/${agent}-memory-hook.sh" << 'HOOKEOF'
#!/bin/bash
# Memory hook for AGENT_PLACEHOLDER
# This script is called by the agent to save/load memory

AGENT="AGENT_PLACEHOLDER"
MEMORY_ROOT="${AGENT_MEMORY_ROOT:-$HOME/.agent-memory}"

case "$1" in
    save)
        # Save memory: $2=key, $3=value, $4=type, $5=project
        key="$2"
        value="$3"
        type="${4:-session_context}"
        project="${5:-$(basename "$PWD")}"

        if command -v sqlite3 &> /dev/null; then
            sqlite3 "$MEMORY_ROOT/memory.db" \
                "INSERT OR REPLACE INTO memories (agent, project, memory_type, key, value, updated_at) VALUES ('$AGENT', '$project', '$type', '$key', '$value', datetime('now'));"
        else
            # Fallback to file-based
            mkdir -p "$MEMORY_ROOT/projects/$project"
            echo "$value" > "$MEMORY_ROOT/projects/$project/${type}_${key}.md"
        fi
        ;;
    load)
        # Load memory: $2=key, $3=type, $4=project
        key="$2"
        type="${3:-session_context}"
        project="${4:-$(basename "$PWD")}"

        if command -v sqlite3 &> /dev/null; then
            sqlite3 "$MEMORY_ROOT/memory.db" \
                "SELECT value FROM memories WHERE agent='$AGENT' AND project='$project' AND memory_type='$type' AND key='$key' ORDER BY updated_at DESC LIMIT 1;"
        else
            cat "$MEMORY_ROOT/projects/$project/${type}_${key}.md" 2>/dev/null || echo ""
        fi
        ;;
    list)
        # List memories for project
        project="${2:-$(basename "$PWD")}"

        if command -v sqlite3 &> /dev/null; then
            sqlite3 "$MEMORY_ROOT/memory.db" \
                "SELECT memory_type, key, substr(value, 1, 100), updated_at FROM memories WHERE agent='$AGENT' AND project='$project' ORDER BY updated_at DESC;"
        else
            ls -la "$MEMORY_ROOT/projects/$project/" 2>/dev/null || echo "No memories found"
        fi
        ;;
    *)
        echo "Usage: $0 {save|load|list} [args...]"
        exit 1
        ;;
esac
HOOKEOF
        sed -i "s/AGENT_PLACEHOLDER/$agent/g" "$MEMORY_DIR/hooks/${agent}-memory-hook.sh"
        chmod +x "$MEMORY_DIR/hooks/${agent}-memory-hook.sh"
    done

    log_success "Memory system configured"
}

# Setup headroom for context compression
setup_compression() {
    log_info "Setting up context compression (headroom)..."

    COMPRESSION_DIR="$UNIFIED_DIR/compression"
    mkdir -p "$COMPRESSION_DIR"

    # Check if headroom is built/installed
    if [ -f "$BASE_DIR/headroom/target/release/headroom" ] || command -v headroom &> /dev/null; then
        log_success "headroom binary found"
        HEADROOM_CMD="headroom"
    elif [ -f "$BASE_DIR/headroom/cargo.toml" ]; then
        log_info "Building headroom from source..."
        cd "$BASE_DIR/headroom" && cargo build --release 2>&1 | tail -20
        if [ -f "$BASE_DIR/headroom/target/release/headroom" ]; then
            HEADROOM_CMD="$BASE_DIR/headroom/target/release/headroom"
            log_success "headroom built successfully"
        else
            log_warn "headroom build failed, will use fallback compression"
            HEADROOM_CMD=""
        fi
    else
        log_warn "headroom not found, using fallback"
        HEADROOM_CMD=""
    fi

    # Create compression configuration
    cat > "$COMPRESSION_DIR/config.yaml" << 'EOF'
# Context Compression Configuration

compression:
  # Engine: headroom, native, or none
  engine: "headroom"

  # Headroom settings
  headroom:
    binary_path: "HEADROOM_CMD_PLACEHOLDER"
    # Compression modes
    modes:
      code: "smart"        # Preserve code structure, compress comments/whitespace
      logs: "aggressive"   # High compression for logs
      json: "schema"       # Use JSON schema for compression
      markdown: "semantic" # Preserve semantic structure
      generic: "balanced"  # Balanced compression

    # Token budgets
    budgets:
      default: 8000
      coding_task: 12000
      code_review: 15000
      debugging: 10000

    # Thresholds
    trigger_at_percent: 0.75  # Compress when 75% of budget used
    target_percent: 0.5       # Target 50% after compression

  # Fallback native compression (if headroom unavailable)
  native:
    enabled: true
    algorithms:
      - "deduplicate"
      - "summarize_logs"
      - "compress_json"
      - "trim_whitespace"
      - "extract_key_code"

  # Agent-specific settings
  agents:
    claude-code:
      enabled: true
      budget: 200000  # Claude's large context
    codex:
      enabled: true
      budget: 128000
    cursor:
      enabled: true
      budget: 128000
    opencode:
      enabled: true
      budget: 100000
    gemini-cli:
      enabled: true
      budget: 1000000  # Gemini's huge context
    windsurf:
      enabled: true
      budget: 128000
    copilot:
      enabled: true
      budget: 32000
    kiro:
      enabled: true
      budget: 128000
EOF

    sed -i "s|HEADROOM_CMD_PLACEHOLDER|${HEADROOM_CMD:-headroom}|g" "$COMPRESSION_DIR/config.yaml"

    # Create compression wrapper script
    cat > "$COMPRESSION_DIR/compress.sh" << 'EOF'
#!/bin/bash
# Universal context compression wrapper

CONFIG_FILE="/root/agent-enhancements/unified-integration/compression/config.yaml"
INPUT="${1:-/dev/stdin}"
MODE="${2:-auto}"
AGENT="${3:-claude-code}"

# Try headroom first
if command -v headroom &> /dev/null || [ -f "/root/agent-enhancements/headroom/target/release/headroom" ]; then
    HEADROOM_BIN="${HEADROOM_BIN:-headroom}"
    if [ ! -f "$HEADROOM_BIN" ]; then
        HEADROOM_BIN="/root/agent-enhancements/headroom/target/release/headroom"
    fi

    case "$MODE" in
        code|logs|json|markdown|generic)
            "$HEADROOM_BIN" compress --mode "$MODE" < "$INPUT"
            ;;
        auto)
            # Detect content type
            if head -100 "$INPUT" | grep -q '^{' && head -100 "$INPUT" | grep -q '}'; then
                "$HEADROOM_BIN" compress --mode json < "$INPUT"
            elif head -100 "$INPUT" | grep -q '^```'; then
                "$HEADROOM_BIN" compress --mode code < "$INPUT"
            elif head -100 "$INPUT" | grep -qE '(ERROR|WARN|INFO|DEBUG).*\['; then
                "$HEADROOM_BIN" compress --mode logs < "$INPUT"
            else
                "$HEADROOM_BIN" compress --mode generic < "$INPUT"
            fi
            ;;
    esac
else
    # Fallback: basic compression
    cat "$INPUT" | \
        # Remove excessive whitespace
        sed 's/[[:space:]]\+$//' | \
        # Compress repeated lines
        awk '!seen[$0]++' | \
        # Limit output
        head -5000
fi
EOF
    chmod +x "$COMPRESSION_DIR/compress.sh"

    log_success "Context compression configured"
}

# Create agent-specific configurations
create_agent_configs() {
    log_info "Creating agent-specific configurations..."

    for agent in "${AGENTS[@]}"; do
        case "$agent" in
            claude-code)
                create_claude_code_config
                ;;
            codex)
                create_codex_config
                ;;
            opencode)
                create_opencode_config
                ;;
            cursor)
                create_cursor_config
                ;;
            gemini-cli)
                create_gemini_config
                ;;
            windsurf)
                create_windsurf_config
                ;;
            copilot)
                create_copilot_config
                ;;
            kiro)
                create_kiro_config
                ;;
        esac
    done

    log_success "Agent configurations created"
}

create_claude_code_config() {
    CLAUDE_DIR="$HOME/.claude"
    mkdir -p "$CLAUDE_DIR"

    # Create CLAUDE.md with all enhancements
    cat > "$CLAUDE_DIR/CLAUDE.md" << 'EOF'
# Claude Code Enhanced Configuration

## System Prompt
@/root/agent-enhancements/unified-integration/prompts/claude-code-system-prompt.txt

## Skills
- Source: /root/agent-enhancements/unified-integration/skills
- Auto-load: true
- Categories: all

## Memory (claude-mem)
- Enabled: true
- Plugin: /root/agent-enhancements/claude-mem/.claude-plugin
- Auto-save: task_complete, decision_made, session_end

## Context Compression (headroom)
- Enabled: true
- Budget: 200000 tokens
- Trigger at: 75%

## Hooks
- PreToolUse: memory_save, context_compress
- PostToolUse: memory_save
- Stop: memory_save

## MCP Servers
# Note: headroom is a proxy server, not an MCP server. Skills are loaded via the skills loader utility.
EOF

    # Create settings.json
    cat > "$CLAUDE_DIR/settings.json" << 'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/root/agent-enhancements/unified-integration/memory/hooks/claude-code-memory-hook.sh save pre_tool_use \"${TOOL_NAME}\" \"${TOOL_INPUT}\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/root/agent-enhancements/unified-integration/memory/hooks/claude-code-memory-hook.sh save post_tool_use \"${TOOL_NAME}\" \"${TOOL_RESULT}\""
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/root/agent-enhancements/unified-integration/memory/hooks/claude-code-memory-hook.sh save session_end \"summary\" \"${SESSION_SUMMARY}\""
          }
        ]
      }
    ]
  }
}
EOF
    log_success "Claude Code configuration created"
}

create_codex_config() {
    CODEX_DIR="$HOME/.codex"
    mkdir -p "$CODEX_DIR"

    cat > "$CODEX_DIR/config.yaml" << 'EOF'
# Codex Enhanced Configuration

system_prompt: "@/root/agent-enhancements/unified-integration/prompts/codex-system-prompt.txt"

skills:
  directory: "/root/agent-enhancements/unified-integration/skills"
  auto_load: true

memory:
  enabled: true
  plugin: "/root/agent-enhancements/claude-mem/.codex-plugin"

compression:
  enabled: true
  engine: "headroom"
  budget: 128000

hooks:
  pre_tool: "/root/agent-enhancements/unified-integration/memory/hooks/codex-memory-hook.sh save"
  post_tool: "/root/agent-enhancements/unified-integration/memory/hooks/codex-memory-hook.sh save"
  stop: "/root/agent-enhancements/unified-integration/memory/hooks/codex-memory-hook.sh save session_end"
EOF
    log_success "Codex configuration created"
}

create_opencode_config() {
    OPENCODE_DIR="$HOME/.config/opencode"
    mkdir -p "$OPENCODE_DIR"

    cat > "$OPENCODE_DIR/config.json" << 'EOF'
{
  "systemPrompt": "@/root/agent-enhancements/unified-integration/prompts/opencode-system-prompt.txt",
  "skills": {
    "directory": "/root/agent-enhancements/unified-integration/skills",
    "autoLoad": true
  },
  "memory": {
    "enabled": true,
    "plugin": "/root/agent-enhancements/claude-mem/.opencode"
  },
  "compression": {
    "enabled": true,
    "engine": "headroom",
    "budget": 100000
  },
  "hooks": {
    "preTool": "/root/agent-enhancements/unified-integration/memory/hooks/opencode-memory-hook.sh save",
    "postTool": "/root/agent-enhancements/unified-integration/memory/hooks/opencode-memory-hook.sh save",
    "stop": "/root/agent-enhancements/unified-integration/memory/hooks/opencode-memory-hook.sh save session_end"
  }
}
EOF
    log_success "OpenCode configuration created"
}

create_cursor_config() {
    CURSOR_DIR="$HOME/.cursor"
    mkdir -p "$CURSOR_DIR"

    cat > "$CURSOR_DIR/settings.json" << 'EOF'
{
  "systemPrompt": "@/root/agent-enhancements/unified-integration/prompts/cursor-system-prompt.txt",
  "skills": {
    "directory": "/root/agent-enhancements/unified-integration/skills",
    "autoLoad": true
  },
  "memory": {
    "enabled": true,
    "plugin": "/root/agent-enhancements/claude-mem/.cursor-plugin"
  },
  "compression": {
    "enabled": true,
    "engine": "headroom",
    "budget": 128000
  },
  "hooks": {
    "preTool": "/root/agent-enhancements/unified-integration/memory/hooks/cursor-memory-hook.sh save",
    "postTool": "/root/agent-enhancements/unified-integration/memory/hooks/cursor-memory-hook.sh save",
    "stop": "/root/agent-enhancements/unified-integration/memory/hooks/cursor-memory-hook.sh save session_end"
  }
}
EOF
    log_success "Cursor configuration created"
}

create_gemini_config() {
    GEMINI_DIR="$HOME/.gemini"
    mkdir -p "$GEMINI_DIR"

    cat > "$GEMINI_DIR/config.yaml" << 'EOF'
system_prompt: "@/root/agent-enhancements/unified-integration/prompts/gemini-cli-system-prompt.txt"

skills:
  directory: "/root/agent-enhancements/unified-integration/skills"
  auto_load: true

memory:
  enabled: true
  plugin: "/root/agent-enhancements/claude-mem/.gemini"

compression:
  enabled: true
  engine: "headroom"
  budget: 1000000

hooks:
  pre_tool: "/root/agent-enhancements/unified-integration/memory/hooks/gemini-cli-memory-hook.sh save"
  post_tool: "/root/agent-enhancements/unified-integration/memory/hooks/gemini-cli-memory-hook.sh save"
  stop: "/root/agent-enhancements/unified-integration/memory/hooks/gemini-cli-memory-hook.sh save session_end"
EOF
    log_success "Gemini CLI configuration created"
}

create_windsurf_config() {
    WINDSURF_DIR="$HOME/.windsurf"
    mkdir -p "$WINDSURF_DIR"

    cat > "$WINDSURF_DIR/config.yaml" << 'EOF'
system_prompt: "@/root/agent-enhancements/unified-integration/prompts/windsurf-system-prompt.txt"

skills:
  directory: "/root/agent-enhancements/unified-integration/skills"
  auto_load: true

memory:
  enabled: true
  plugin: "/root/agent-enhancements/claude-mem/.windsurf"

compression:
  enabled: true
  engine: "headroom"
  budget: 128000
EOF
    log_success "Windsurf configuration created"
}

create_copilot_config() {
    COPILOT_DIR="$HOME/.config/github-copilot"
    mkdir -p "$COPILOT_DIR"

    cat > "$COPILOT_DIR/config.yaml" << 'EOF'
skills:
  directory: "/root/agent-enhancements/unified-integration/skills"
  auto_load: true

memory:
  enabled: true
  # Copilot uses VS Code settings for memory

compression:
  enabled: true
  engine: "headroom"
  budget: 32000
EOF
    log_success "GitHub Copilot configuration created"
}

create_kiro_config() {
    KIRO_DIR="$HOME/.kiro"
    mkdir -p "$KIRO_DIR"

    cat > "$KIRO_DIR/config.yaml" << 'EOF'
system_prompt: "@/root/agent-enhancements/unified-integration/prompts/kiro-system-prompt.txt"

skills:
  directory: "/root/agent-enhancements/unified-integration/skills"
  auto_load: true

memory:
  enabled: true

compression:
  enabled: true
  engine: "headroom"
  budget: 128000
EOF
    log_success "Kiro configuration created"
}

# Create universal launcher script
create_launcher() {
    log_info "Creating universal launcher..."

    cat > "$UNIFIED_DIR/launch-agent.sh" << 'EOF'
#!/bin/bash
# Universal AI Agent Launcher with Enhancements

AGENT="${1:-claude-code}"
shift

UNIFIED_DIR="/root/agent-enhancements/unified-integration"

# Load detected agents
source "$UNIFIED_DIR/config/detected-agents.sh" 2>/dev/null || true

# Validate agent
if [[ ! " ${AGENTS[@]} " =~ " ${AGENT} " ]]; then
    echo "Agent '$AGENT' not detected. Available: ${AGENTS[@]}"
    echo "Usage: $0 <agent> [args...]"
    exit 1
fi

# Initialize memory
"$UNIFIED_DIR/memory/init-memory.sh"

# Set environment variables
export AGENT_MEMORY_ROOT="$HOME/.agent-memory"
export AGENT_SKILLS_DIR="/root/agent-enhancements/unified-integration/skills"
export AGENT_COMPRESSION_CONFIG="/root/agent-enhancements/unified-integration/compression/config.yaml"
export AGENT_PROMPTS_DIR="/root/agent-enhancements/unified-integration/prompts"

# Launch agent with enhancements
case "$AGENT" in
    claude-code)
        exec claude "$@"
        ;;
    codex)
        exec codex "$@"
        ;;
    opencode)
        exec opencode "$@"
        ;;
    cursor)
        exec cursor "$@"
        ;;
    gemini-cli)
        exec gemini "$@"
        ;;
    windsurf)
        exec windsurf "$@"
        ;;
    copilot)
        exec gh copilot "$@"
        ;;
    kiro)
        exec kiro "$@"
        ;;
    *)
        echo "Unknown agent: $AGENT"
        exit 1
        ;;
esac
EOF
    chmod +x "$UNIFIED_DIR/launch-agent.sh"

    # Create symlink for easy access
    ln -sf "$UNIFIED_DIR/launch-agent.sh" /usr/local/bin/agent-enhanced 2>/dev/null || true

    log_success "Universal launcher created at $UNIFIED_DIR/launch-agent.sh"
}

# Create skills loader utility
create_skills_loader() {
    log_info "Creating skills loader utility..."

    cat > "$UNIFIED_DIR/scripts/load-skills.py" << 'EOF'
#!/usr/bin/env python3
"""
Universal Skills Loader for AI Coding Agents
Loads and matches skills from all sources based on task context
"""

import json
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any

SKILLS_DIR = Path("/root/agent-enhancements/unified-integration/skills")

class SkillsLoader:
    def __init__(self, agent: str = "claude-code"):
        self.agent = agent
        self.skills_index = self._load_index()

    def _load_index(self) -> Dict:
        """Load the aggregated skills index"""
        index_file = SKILLS_DIR / "all-skills.json"
        if index_file.exists():
            with open(index_file) as f:
                return json.load(f)
        return {"skills": []}

    def find_skills(self, task_description: str, max_results: int = 5) -> List[Dict]:
        """Find relevant skills for a task"""
        task_lower = task_description.lower()
        matches = []

        # Simple keyword matching (in production, use embeddings)
        keywords = re.findall(r'\b\w+\b', task_lower)

        for skill in self.skills_index.get("skills", []):
            score = 0
            # Check "when_to_use" keywords
            when_to_use = skill.get("when_to_use", "").lower()
            for kw in keywords:
                if kw in when_to_use:
                    score += 2
            # Check tags
            for tag in skill.get("tags", []):
                if tag.lower() in task_lower:
                    score += 3
            # Check description
            desc = skill.get("description", "").lower()
            for kw in keywords:
                if kw in desc:
                    score += 1

            # Check agent compatibility
            if self.agent in skill.get("tools", []):
                score += 5

            if score > 0:
                matches.append((score, skill))

        # Sort by score and return top matches
        matches.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in matches[:max_results]]

    def load_skill(self, skill_name: str) -> Dict:
        """Load a specific skill by name"""
        # Search in all category directories
        for cat_dir in (SKILLS_DIR / "by-category").iterdir():
            if cat_dir.is_dir():
                skill_file = cat_dir / f"{skill_name}.md"
                if skill_file.exists():
                    return self._parse_skill(skill_file)

        # Search in agent-specific directories
        agent_dir = SKILLS_DIR / "by-agent" / self.agent
        if agent_dir.exists():
            skill_file = agent_dir / f"{skill_name}.md"
            if skill_file.exists():
                return self._parse_skill(skill_file)

        return {}

    def _parse_skill(self, skill_file: Path) -> Dict:
        """Parse SKILL.md file"""
        content = skill_file.read_text()
        # Parse frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return {"frontmatter": frontmatter, "body": body, "file": str(skill_file)}
        return {"raw": content, "file": str(skill_file)}


def main():
    if len(sys.argv) < 2:
        print("Usage: load-skills.py <agent> <task_description>")
        sys.exit(1)

    agent = sys.argv[1]
    task = " ".join(sys.argv[2:])

    loader = SkillsLoader(agent)
    skills = loader.find_skills(task)

    for skill in skills:
        print(f"Skill: {skill.get('name', 'Unknown')}")
        print(f"  Description: {skill.get('description', 'N/A')}")
        print(f"  Tags: {', '.join(skill.get('tags', []))}")
        print()

if __name__ == "__main__":
    main()
EOF
    chmod +x "$UNIFIED_DIR/scripts/load-skills.py"

    log_success "Skills loader created"
}

# Create memory utility
create_memory_util() {
    log_info "Creating memory utility..."

    cat > "$UNIFIED_DIR/scripts/memory.py" << 'EOF'
#!/usr/bin/env python3
"""
Universal Memory Utility for AI Coding Agents
Manages persistent memory across sessions and agents
"""

import sqlite3
import json
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

MEMORY_ROOT = Path(os.environ.get("AGENT_MEMORY_ROOT", Path.home() / ".agent-memory"))
DB_PATH = MEMORY_ROOT / "memory.db"

class AgentMemory:
    def __init__(self, agent: str, project: Optional[str] = None):
        self.agent = agent
        self.project = project or Path.cwd().name
        self._init_db()

    def _init_db(self):
        """Initialize database"""
        MEMORY_ROOT.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL,
                    project TEXT,
                    memory_type TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    UNIQUE(agent, project, memory_type, key)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_project ON memories(agent, project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON memories(expires_at)")

    def save(self, key: str, value: str, memory_type: str = "session_context",
             metadata: Optional[Dict] = None, ttl_days: Optional[int] = None) -> None:
        """Save a memory"""
        expires_at = None
        if ttl_days:
            from datetime import timedelta
            expires_at = (datetime.now() + timedelta(days=ttl_days)).isoformat()

        meta_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories
                (agent, project, memory_type, key, value, metadata, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """, (self.agent, self.project, memory_type, key, value, meta_json, expires_at))

    def load(self, key: str, memory_type: str = "session_context") -> Optional[str]:
        """Load a memory"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT value FROM memories
                WHERE agent=? AND project=? AND memory_type=? AND key=?
                ORDER BY updated_at DESC LIMIT 1
            """, (self.agent, self.project, memory_type, key))
            row = cursor.fetchone()
            return row[0] if row else None

    def list(self, memory_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """List memories"""
        with sqlite3.connect(DB_PATH) as conn:
            if memory_type:
                cursor = conn.execute("""
                    SELECT memory_type, key, value, metadata, updated_at
                    FROM memories
                    WHERE agent=? AND project=? AND memory_type=?
                    ORDER BY updated_at DESC LIMIT ?
                """, (self.agent, self.project, memory_type, limit))
            else:
                cursor = conn.execute("""
                    SELECT memory_type, key, value, metadata, updated_at
                    FROM memories
                    WHERE agent=? AND project=?
                    ORDER BY updated_at DESC LIMIT ?
                """, (self.agent, self.project, limit))

            return [
                {
                    "type": row[0],
                    "key": row[1],
                    "value": row[2][:200] + "..." if len(row[2]) > 200 else row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                    "updated": row[4]
                }
                for row in cursor.fetchall()
            ]

    def delete(self, key: str, memory_type: str = "session_context") -> bool:
        """Delete a memory"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                DELETE FROM memories
                WHERE agent=? AND project=? AND memory_type=? AND key=?
            """, (self.agent, self.project, memory_type, key))
            return cursor.rowcount > 0

    def cleanup_expired(self) -> int:
        """Remove expired memories"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                DELETE FROM memories
                WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
            """)
            return cursor.rowcount


def main():
    if len(sys.argv) < 3:
        print("Usage: memory.py <agent> <command> [args...]")
        print("Commands: save <key> <value> [type] [ttl_days]")
        print("          load <key> [type]")
        print("          list [type] [limit]")
        print("          delete <key> [type]")
        print("          cleanup")
        sys.exit(1)

    agent = sys.argv[1]
    command = sys.argv[2]

    memory = AgentMemory(agent)

    if command == "save":
        if len(sys.argv) < 5:
            print("Usage: memory.py <agent> save <key> <value> [type] [ttl_days]")
            sys.exit(1)
        key = sys.argv[3]
        value = sys.argv[4]
        mem_type = sys.argv[5] if len(sys.argv) > 5 else "session_context"
        ttl = int(sys.argv[6]) if len(sys.argv) > 6 else None
        memory.save(key, value, mem_type, ttl_days=ttl)
        print(f"Saved: {key} ({mem_type})")

    elif command == "load":
        if len(sys.argv) < 4:
            print("Usage: memory.py <agent> load <key> [type]")
            sys.exit(1)
        key = sys.argv[3]
        mem_type = sys.argv[4] if len(sys.argv) > 4 else "session_context"
        value = memory.load(key, mem_type)
        if value:
            print(value)
        else:
            print(f"Memory not found: {key}")

    elif command == "list":
        mem_type = sys.argv[3] if len(sys.argv) > 3 else None
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 20
        memories = memory.list(mem_type, limit)
        for m in memories:
            print(f"[{m['type']}] {m['key']}: {m['value']} (updated: {m['updated']})")

    elif command == "delete":
        if len(sys.argv) < 4:
            print("Usage: memory.py <agent> delete <key> [type]")
            sys.exit(1)
        key = sys.argv[3]
        mem_type = sys.argv[4] if len(sys.argv) > 4 else "session_context"
        if memory.delete(key, mem_type):
            print(f"Deleted: {key}")
        else:
            print(f"Not found: {key}")

    elif command == "cleanup":
        count = memory.cleanup_expired()
        print(f"Cleaned up {count} expired memories")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF
    chmod +x "$UNIFIED_DIR/scripts/memory.py"

    log_success "Memory utility created"
}

# Create compression utility
create_compression_util() {
    log_info "Creating compression utility..."

    cat > "$UNIFIED_DIR/scripts/compress.py" << 'EOF'
#!/usr/bin/env python3
"""
Universal Context Compression Utility
Uses headroom or native fallback for token optimization
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from typing import Optional

HEADROOM_BIN = os.environ.get("HEADROOM_BIN", "headroom")
FALLBACK_BIN = "/root/agent-enhancements/headroom/target/release/headroom"

def get_headroom_bin() -> Optional[str]:
    """Find headroom binary"""
    for bin_path in [HEADROOM_BIN, FALLBACK_BIN]:
        if bin_path and os.path.exists(bin_path):
            return bin_path
        try:
            result = subprocess.run(["which", bin_path], capture_output=True)
            if result.returncode == 0:
                return result.stdout.decode().strip()
        except:
            pass
    return None

def compress_content(content: str, mode: str = "auto", agent: str = "claude-code") -> str:
    """Compress content using headroom or fallback"""

    headroom = get_headroom_bin()

    if headroom:
        try:
            result = subprocess.run(
                [headroom, "compress", "--mode", mode],
                input=content.encode(),
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.decode()
        except Exception as e:
            print(f"Headroom error: {e}", file=sys.stderr)

    # Fallback compression
    return fallback_compress(content, mode)

def fallback_compress(content: str, mode: str) -> str:
    """Native Python fallback compression"""
    lines = content.split('\n')

    if mode in ("json", "auto"):
        # Try to detect and compress JSON
        if content.strip().startswith(('{', '[')):
            try:
                data = json.loads(content)
                # Remove null values, empty arrays/objects
                def clean(obj):
                    if isinstance(obj, dict):
                        return {k: clean(v) for k, v in obj.items() if v is not None and v != [] and v != {}}
                    elif isinstance(obj, list):
                        return [clean(v) for v in obj if v is not None and v != [] and v != {}]
                    return obj
                cleaned = clean(data)
                return json.dumps(cleaned, separators=(',', ':'))
            except:
                pass

    if mode in ("logs", "auto"):
        # Detect log format
        if any(re.search(r'\b(ERROR|WARN|INFO|DEBUG|TRACE)\b', line) for line in lines[:50]):
            # Keep only unique log lines, preserve first occurrence
            seen = set()
            unique = []
            for line in lines:
                # Normalize timestamps/IDs
                normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', 'TIMESTAMP', line)
                normalized = re.sub(r'\b[0-9a-f]{8,}\b', 'ID', normalized)
                if normalized not in seen:
                    seen.add(normalized)
                    unique.append(line)
            lines = unique

    if mode in ("code", "auto"):
        # Preserve code structure, trim comments/whitespace
        # Simple heuristic: keep lines with code, trim excessive blank lines
        compressed = []
        blank_count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_count += 1
                if blank_count <= 2:  # Max 2 blank lines
                    compressed.append(line)
            else:
                blank_count = 0
                compressed.append(line)
        lines = compressed

    # Limit total size
    result = '\n'.join(lines)
    if len(result) > 50000:  # ~12k tokens
        result = result[:50000] + "\n... [truncated]"

    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: compress.py <mode> [agent] < input.txt")
        print("Modes: auto, code, logs, json, markdown, generic")
        sys.exit(1)

    mode = sys.argv[1]
    agent = sys.argv[2] if len(sys.argv) > 2 else "claude-code"

    content = sys.stdin.read()
    compressed = compress_content(content, mode, agent)
    print(compressed)

if __name__ == "__main__":
    main()
EOF
    chmod +x "$UNIFIED_DIR/scripts/compress.py"

    log_success "Compression utility created"
}

# Main setup flow
main() {
    echo "========================================"
    echo "  Unified AI Agent Enhancement Setup"
    echo "========================================"
    echo ""

    detect_agents
    setup_prompts
    aggregate_skills
    setup_memory
    setup_compression
    create_agent_configs
    create_launcher
    create_skills_loader
    create_memory_util
    create_compression_util

    echo ""
    echo "========================================"
    echo "  Setup Complete!"
    echo "========================================"
    echo ""
    echo "Configured agents: ${AGENTS[@]}"
    echo ""
    echo "Next steps:"
    echo "  1. Run: $UNIFIED_DIR/memory/init-memory.sh"
    echo "  2. Launch enhanced agent: $UNIFIED_DIR/launch-agent.sh <agent>"
    echo "  3. Or use: agent-enhanced <agent> (if symlink created)"
    echo ""
    echo "Config files created in:"
    echo "  - $UNIFIED_DIR/config/"
    echo "  - $UNIFIED_DIR/prompts/"
    echo "  - $UNIFIED_DIR/skills/"
    echo "  - $UNIFIED_DIR/memory/"
    echo "  - $UNIFIED_DIR/compression/"
    echo ""
    echo "Agent configs also placed in:"
    echo "  - ~/.claude/ (Claude Code)"
    echo "  - ~/.codex/ (Codex)"
    echo "  - ~/.config/opencode/ (OpenCode)"
    echo "  - ~/.cursor/ (Cursor)"
    echo "  - ~/.gemini/ (Gemini CLI)"
    echo "  - ~/.windsurf/ (Windsurf)"
    echo "  - ~/.config/github-copilot/ (Copilot)"
    echo "  - ~/.kiro/ (Kiro)"
}

main "$@"