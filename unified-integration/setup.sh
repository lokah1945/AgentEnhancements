#!/bin/bash
# Unified AI Agent Enhancement Setup - FIXED VERSION
# Configures all agent enhancements for: Claude Code, Codex, OpenCode, Cursor, Gemini CLI, Windsurf, Copilot, Kiro, etc.

set -euo pipefail

# Enable recursive globbing (needed for prompt discovery) and make
# non-matching globs expand to nothing instead of the literal pattern.
shopt -s globstar nullglob

# Allow BASE_DIR to be overridden via environment variable.
# Default: the repository root that contains this script (works from any
# checkout location, not only /root/agent-enhancements).
SCRIPT_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-$(cd "$SCRIPT_SOURCE_DIR/.." && pwd)}"
UNIFIED_DIR="$BASE_DIR/unified-integration"
mkdir -p "$UNIFIED_DIR/config"

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
    if command -v gh &> /dev/null && gh extension list 2>/dev/null | grep -q copilot; then
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

    # Write detected agents in a way that is safe for empty arrays
    # (older bash such as macOS 3.2 errors on "${AGENTS[@]}" when empty).
    if [ ${#AGENTS[@]} -eq 0 ]; then
        echo "AGENTS=()" > "$UNIFIED_DIR/config/detected-agents.sh"
    else
        printf 'AGENTS=(%s)\n' "${AGENTS[*]}" > "$UNIFIED_DIR/config/detected-agents.sh"
    fi
}

# Setup system prompts for each agent
setup_prompts() {
    log_info "Setting up system prompts for all agents..."

    PROMPTS_DIR="$BASE_DIR/system-prompts-and-models-of-ai-tools"

    for agent in "${AGENTS[@]}"; do
        case "$agent" in
            claude-code)
                # Find Claude Code prompt in the actual directory structure
                local prompt_file=""
                for f in "$PROMPTS_DIR/Anthropic"/**/*laude*Code*/Prompt*.txt "$PROMPTS_DIR/Anthropic"/**/*laude*Code*/*.txt; do
                    if [ -f "$f" ]; then
                        prompt_file="$f"
                        break
                    fi
                done
                if [ -n "$prompt_file" ] && [ -f "$prompt_file" ]; then
                    cp "$prompt_file" "$UNIFIED_DIR/prompts/claude-code-system-prompt.txt"
                    log_success "Claude Code system prompt configured from $prompt_file"
                else
                    log_warn "Claude Code prompt not found in $PROMPTS_DIR/Anthropic/"
                fi
                ;;
            codex)
                # Find Codex prompt
                local prompt_file=""
                for f in "$PROMPTS_DIR/OpenAI"/**/*odex*/*.txt "$PROMPTS_DIR/OpenAI"/**/*odex*/*.md; do
                    if [ -f "$f" ]; then
                        prompt_file="$f"
                        break
                    fi
                done
                if [ -n "$prompt_file" ] && [ -f "$prompt_file" ]; then
                    cp "$prompt_file" "$UNIFIED_DIR/prompts/codex-system-prompt.txt"
                    log_success "Codex system prompt configured from $prompt_file"
                else
                    log_warn "Codex prompt not found in $PROMPTS_DIR/OpenAI/"
                fi
                ;;
            opencode)
                # Find OpenCode prompt
                local prompt_file=""
                for f in "$PROMPTS_DIR"/**/[Oo]pen[Cc]ode*/*.txt "$PROMPTS_DIR"/**/[Oo]pen[Cc]ode*/*.md; do
                    if [ -f "$f" ]; then
                        prompt_file="$f"
                        break
                    fi
                done
                if [ -n "$prompt_file" ] && [ -f "$prompt_file" ]; then
                    cp "$prompt_file" "$UNIFIED_DIR/prompts/opencode-system-prompt.txt"
                    log_success "OpenCode system prompt configured from $prompt_file"
                else
                    log_warn "OpenCode prompt not found"
                fi
                ;;
            cursor)
                # Find Cursor prompt
                local prompt_file=""
                for f in "$PROMPTS_DIR/Cursor Prompts"/*.txt "$PROMPTS_DIR/Cursor Prompts"/*.md; do
                    if [ -f "$f" ]; then
                        prompt_file="$f"
                        break
                    fi
                done
                if [ -n "$prompt_file" ] && [ -f "$prompt_file" ]; then
                    cp "$prompt_file" "$UNIFIED_DIR/prompts/cursor-system-prompt.txt"
                    log_success "Cursor system prompt configured from $prompt_file"
                else
                    log_warn "Cursor prompt not found in $PROMPTS_DIR/Cursor Prompts/"
                fi
                ;;
            gemini-cli)
                # Find Gemini prompt
                local prompt_file=""
                for f in "$PROMPTS_DIR/Google"/**/*emini*/*.txt "$PROMPTS_DIR/Google"/**/*emini*/*.md; do
                    if [ -f "$f" ]; then
                        prompt_file="$f"
                        break
                    fi
                done
                if [ -n "$prompt_file" ] && [ -f "$prompt_file" ]; then
                    cp "$prompt_file" "$UNIFIED_DIR/prompts/gemini-cli-system-prompt.txt"
                    log_success "Gemini CLI system prompt configured from $prompt_file"
                else
                    log_warn "Gemini CLI prompt not found in $PROMPTS_DIR/Google/"
                fi
                ;;
            windsurf)
                # Find Windsurf prompt
                local prompt_file=""
                for f in "$PROMPTS_DIR/Windsurf"/*.txt "$PROMPTS_DIR/Windsurf"/*.md; do
                    if [ -f "$f" ]; then
                        prompt_file="$f"
                        break
                    fi
                done
                if [ -n "$prompt_file" ] && [ -f "$prompt_file" ]; then
                    cp "$prompt_file" "$UNIFIED_DIR/prompts/windsurf-system-prompt.txt"
                    log_success "Windsurf system prompt configured from $prompt_file"
                else
                    log_warn "Windsurf prompt not found in $PROMPTS_DIR/Windsurf/"
                fi
                ;;
            kiro)
                # Find Kiro prompt (source dir ships flat .txt prompt files)
                local prompt_file=""
                for f in "$PROMPTS_DIR/Kiro"/*.txt "$PROMPTS_DIR/Kiro"/*.md; do
                    if [ -f "$f" ]; then
                        prompt_file="$f"
                        break
                    fi
                done
                if [ -n "$prompt_file" ] && [ -f "$prompt_file" ]; then
                    cp "$prompt_file" "$UNIFIED_DIR/prompts/kiro-system-prompt.txt"
                    log_success "Kiro system prompt configured from $prompt_file"
                else
                    log_warn "Kiro prompt not found in $PROMPTS_DIR/Kiro/"
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

# Parse YAML frontmatter from SKILL.md file
parse_skill_frontmatter() {
    local skill_file="$1"
    local field="$2"

    if [ ! -f "$skill_file" ]; then
        echo ""
        return
    fi

    # Extract frontmatter between --- delimiters
    awk -v field="$field" '
    /^---$/ { in_fm = !in_fm; next }
    in_fm && $0 ~ "^" field ":" {
        sub("^" field ": *", "")
        gsub(/^["'"'"']|["'"'"']$/, "")
        print
        exit
    }
    ' "$skill_file"
}

# Get skill category from frontmatter
get_skill_category() {
    local skill_file="$1"
    local category=$(parse_skill_frontmatter "$skill_file" "category")
    if [ -z "$category" ]; then
        category="general"
    fi
    echo "$category"
}

# Get skill name from frontmatter
get_skill_name() {
    local skill_file="$1"
    local name=$(parse_skill_frontmatter "$skill_file" "name")
    if [ -z "$name" ]; then
        # Fallback to directory name
        name=$(basename "$(dirname "$skill_file")")
    fi
    echo "$name"
}

# Get skill description from frontmatter
get_skill_description() {
    local skill_file="$1"
    parse_skill_frontmatter "$skill_file" "description"
}

# Get skill tags from frontmatter
get_skill_tags() {
    local skill_file="$1"
    local tags=$(awk '
    /^---$/ { in_fm = !in_fm; next }
    in_fm && /^tags:/ { in_tags = 1; next }
    in_fm && in_tags && /^[[:space:]]*-/ {
        sub(/^[[:space:]]*-[[:space:]]*/, "")
        gsub(/^["'"'"']|["'"'"']$/, "")
        print
        next
    }
    in_fm && in_tags && !/^[[:space:]]*-/ { in_tags = 0 }
    ' "$skill_file")
    echo "$tags"
}

# Get skill tools (compatible agents) from frontmatter
get_skill_tools() {
    local skill_file="$1"
    local tools=$(awk '
    /^---$/ { in_fm = !in_fm; next }
    in_fm && /^tools:/ { in_tools = 1; next }
    in_fm && in_tools && /^[[:space:]]*-/ {
        sub(/^[[:space:]]*-[[:space:]]*/, "")
        gsub(/^["'"'"']|["'"'"']$/, "")
        print
        next
    }
    in_fm && in_tools && !/^[[:space:]]*-/ { in_tools = 0 }
    ' "$skill_file")
    echo "$tools"
}

# Get skill risk from frontmatter
get_skill_risk() {
    local skill_file="$1"
    local risk=$(parse_skill_frontmatter "$skill_file" "risk")
    if [ -z "$risk" ]; then
        risk="safe"
    fi
    echo "$risk"
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
EOF

    # Create category directories
    CATEGORIES=("security" "architecture" "testing" "refactoring" "code-review" "documentation" "devops" "ai-ml" "productivity" "general")
    for cat in "${CATEGORIES[@]}"; do
        mkdir -p "$SKILLS_DIR/by-category/$cat"
    done

    # Create agent directories
    AGENT_LIST=("claude-code" "codex" "cursor" "gemini-cli" "opencode" "copilot" "windsurf" "kiro")
    for agent in "${AGENT_LIST[@]}"; do
        mkdir -p "$SKILLS_DIR/by-agent/$agent"
    done

    # Accumulate skill metadata into a record file (fields separated by
    # ASCII unit separator \x1f, records by record separator \x1e).
    # Metadata is NEVER interpolated into code - the index builder reads
    # this file, which eliminates the code-injection vector that existed
    # when frontmatter values were spliced into "python3 -c" source.
    SKILLS_META="$SKILLS_DIR/.skills-meta.tmp"
    : > "$SKILLS_META"

    # Process skills from a source directory
    process_skills_source() {
        local source_name="$1"
        local source_dir="$2"
        local skills_count=0

        if [ ! -d "$source_dir" ]; then
            log_warn "Source directory not found: $source_dir"
            return
        fi

        log_info "Processing $source_name skills from $source_dir..."

        # Find all skill directories (directories containing SKILL.md)
        while IFS= read -r -d '' skill_dir; do
            if [ -f "$skill_dir/SKILL.md" ]; then
                skill_name=$(get_skill_name "$skill_dir/SKILL.md")
                skill_category=$(get_skill_category "$skill_dir/SKILL.md")
                skill_description=$(get_skill_description "$skill_dir/SKILL.md")
                skill_risk=$(get_skill_risk "$skill_dir/SKILL.md")
                skill_tags=$(get_skill_tags "$skill_dir/SKILL.md")
                skill_tools=$(get_skill_tools "$skill_dir/SKILL.md")

                # Normalize category
                case "$skill_category" in
                    security|architecture|testing|refactoring|code-review|documentation|devops|ai-ml|productivity)
                        ;;
                    *)
                        skill_category="general"
                        ;;
                esac

                # Sanitize skill name: it is used as a directory name, so it
                # must not contain path separators (prevents escaping the
                # target directory on copy).
                skill_name="${skill_name//\//-}"

                # Copy entire skill directory to by-category/.
                # Remove any previous copy first: "cp -r src dst" nests the
                # source inside dst when dst already exists, so without this
                # re-running setup duplicated skill trees on every run.
                target_dir="$SKILLS_DIR/by-category/$skill_category/$skill_name"
                mkdir -p "$(dirname "$target_dir")"
                rm -rf "$target_dir"
                cp -r "$skill_dir" "$target_dir" 2>/dev/null || true

                # Also copy to by-agent/ for each compatible tool.
                # Only the canonical agent directories are populated.
                while IFS= read -r tool; do
                    if [ -n "$tool" ]; then
                        case "$tool" in
                            claude-code|codex|cursor|gemini-cli|opencode|copilot|windsurf|kiro)
                                agent_target_dir="$SKILLS_DIR/by-agent/$tool/$skill_name"
                                mkdir -p "$(dirname "$agent_target_dir")"
                                rm -rf "$agent_target_dir"
                                cp -r "$skill_dir" "$agent_target_dir" 2>/dev/null || true
                                ;;
                            *)
                                # Unknown tool name: keep it in the index but
                                # do not create arbitrary directories from it.
                                ;;
                        esac
                    fi
                done <<< "$skill_tools"

                # Append metadata record for the index builder. The 8th
                # field is the SKILL.md path: the builder re-parses the
                # frontmatter from the file so that YAML block scalars
                # (">-" / "|-") become real descriptions instead of the
                # marker string the awk extraction produces.
                printf '%s\x1f%s\x1f%s\x1f%s\x1f%s\x1f%s\x1f%s\x1f%s\x1e' \
                    "$skill_name" "$skill_category" "$skill_description" \
                    "$skill_risk" "$source_name" "$skill_tags" "$skill_tools" \
                    "$skill_dir/SKILL.md" \
                    >> "$SKILLS_META"
                # NB: use arithmetic expansion, not bash arithmetic
                # post-increment: post-increment from zero evaluates to
                # zero, which returns exit status 1 and aborts the
                # script under "set -e".
                skills_count=$((skills_count + 1))
            fi
        done < <(find "$source_dir" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)

        log_success "$source_name: processed $skills_count skills"
    }

    # Aggregate from agentic-awesome-skills (primary)
    if [ -d "$BASE_DIR/agentic-awesome-skills/skills" ]; then
        process_skills_source "agentic-awesome-skills" "$BASE_DIR/agentic-awesome-skills/skills"
    fi

    # Process skills from ECC
    if [ -d "$BASE_DIR/ECC/skills" ]; then
        process_skills_source "ECC" "$BASE_DIR/ECC/skills"
    fi

    # Process skills from Ponytail
    if [ -d "$BASE_DIR/ponytail/skills" ]; then
        process_skills_source "Ponytail" "$BASE_DIR/ponytail/skills"
    fi

    # Process skills from Superpowers
    if [ -d "$BASE_DIR/superpowers/skills" ]; then
        process_skills_source "Superpowers" "$BASE_DIR/superpowers/skills"
    fi

    # Process skills from replica-skill (app cloning pipeline, 11 sub-skills)
    # Source layout: skill dirs live at the repository root (replica-recon/ etc.)
    if [ -d "$BASE_DIR/replica-skill" ]; then
        process_skills_source "replica-skill" "$BASE_DIR/replica-skill"
    fi

    # Process skills from anthropics/skills (official Anthropic skills:
    # docx, pdf, pptx, xlsx, skill-creator, mcp-builder, webapp-testing,
    # claude-api, design skills and more - 19 in total). Processed LAST on
    # purpose: 13 of these names also exist as third-party copies inside
    # agentic-awesome-skills, and the official vendored version must win.
    if [ -d "$BASE_DIR/anthropic-skills/skills" ]; then
        process_skills_source "anthropic-skills" "$BASE_DIR/anthropic-skills/skills"
    fi

    # Create final unified skills index with metadata.
    # All paths are passed via environment variables; no shell values are
    # interpolated into the Python source.
    log_info "Creating unified skills index..."
    SKILLS_META_FILE="$SKILLS_META" SKILLS_INDEX_OUT="$SKILLS_DIR/all-skills.json" \
    BASE_DIR_FOR_INDEX="$BASE_DIR" \
    python3 -c "
import json
import os
from datetime import datetime

meta_path = os.environ['SKILLS_META_FILE']
out_path = os.environ['SKILLS_INDEX_OUT']
base_dir = os.environ.get('BASE_DIR_FOR_INDEX', '')


def mini_frontmatter_parse(fm_lines):
    # Parse the YAML subset used by SKILL.md frontmatter: plain/quoted
    # scalars, folded and literal block scalars (>, >-, |, |-) and dash
    # lists. Fallback when PyYAML is unavailable. Values are data only.
    data = {}
    key = None
    mode = None  # None | 'scalar' | 'block' | 'list'
    buf = []

    def flush():
        if key is None:
            return
        if mode == 'list':
            data[key] = [b for b in buf if b]
        elif mode == 'block':
            data[key] = ' '.join(part.strip() for part in buf).strip()
        else:
            data[key] = buf[0] if buf else ''

    for raw in fm_lines:
        line = raw.rstrip('\n')
        if not line.strip():
            continue
        indented = line[:1] in (' ', '\t')
        s = line.strip()
        if mode == 'block' and indented:
            buf.append(s)
            continue
        if mode == 'list' and indented:
            if s.startswith('-'):
                buf.append(s[1:].strip().strip('\"\''))
            continue
        if indented or s.startswith('#') or ':' not in s:
            continue
        flush()
        k, _, v = s.partition(':')
        key = k.strip()
        v = v.strip()
        if v in ('>', '>-', '>+', '|', '|-', '|+'):
            mode = 'block'
            buf = []
        elif v == '':
            mode = 'list'
            buf = []
        else:
            mode = 'scalar'
            buf = [v.strip('\"\'')]
            flush()
    flush()
    return data


def parse_frontmatter_file(path):
    # Return the frontmatter dict of a SKILL.md file (best effort).
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.read().split('\n')
    except OSError:
        return {}
    if not lines or lines[0].strip() != '---':
        return {}
    fm_lines = []
    closed = False
    for line in lines[1:]:
        if line.strip() == '---':
            closed = True
            break
        fm_lines.append(line)
    if not closed:
        return {}
    try:
        import yaml
        data = yaml.safe_load('\n'.join(fm_lines))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return mini_frontmatter_parse(fm_lines)


skills_by_name = {}
with open(meta_path, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

for record in content.split('\x1e'):
    if not record.strip():
        continue
    fields = record.split('\x1f')
    while len(fields) < 8:
        fields.append('')
    name, category, description, risk, source, tags, tools, skill_file = fields[:8]

    # Re-parse the frontmatter from the source file so that multi-line
    # YAML values (block scalars such as '>-') become real descriptions
    # in the index. The awk-extracted fields above remain the fallback.
    fm = parse_frontmatter_file(skill_file) if skill_file else {}

    fm_desc = fm.get('description')
    if isinstance(fm_desc, str) and fm_desc.strip():
        description = fm_desc.strip()

    fm_tags = fm.get('tags') if isinstance(fm.get('tags'), list) else []
    tag_list = [str(t).strip() for t in fm_tags if str(t).strip()]
    if not tag_list:
        tag_list = [t.strip() for t in tags.split('\n') if t.strip()]

    fm_tools = fm.get('tools') if isinstance(fm.get('tools'), list) else []
    tool_list = [str(t).strip() for t in fm_tools if str(t).strip()]
    if not tool_list:
        tool_list = [t.strip() for t in tools.split('\n') if t.strip()]

    skills_dir_root = os.path.dirname(out_path)
    agg_path = os.path.join(skills_dir_root, 'by-category', category, name, 'SKILL.md')
    try:
        rel_agg = os.path.relpath(agg_path, base_dir) if base_dir else agg_path
    except ValueError:
        rel_agg = agg_path

    source_path = ''
    if skill_file and base_dir:
        try:
            source_path = os.path.relpath(skill_file, base_dir)
        except ValueError:
            source_path = skill_file

    skills_by_name[name] = {
        'name': name,
        'category': category,
        'description': description,
        'risk': risk,
        'source': source,
        'tags': tag_list,
        'tools': tool_list,
        'when_to_use': description,
        'path': rel_agg,
        'source_path': source_path
    }

# Later sources win name collisions, mirroring the by-directory overwrite
# semantics in process_skills_source (aggregation order: agentic, ECC,
# Ponytail, Superpowers, replica-skill, anthropic-skills - so the official
# Anthropic version replaces third-party copies of the same skill name).
skills = list(skills_by_name.values())

# Count categories
categories = {}
for skill in skills:
    cat = skill.get('category', 'general')
    categories[cat] = categories.get(cat, 0) + 1

# Count agents
agent_counts = {}
for skill in skills:
    for tool in skill.get('tools', []):
        agent_counts[tool] = agent_counts.get(tool, 0) + 1

# Sources in first-seen order (avoids a hardcoded list drifting out of sync)
sources_seen = list(dict.fromkeys(s['source'] for s in skills))

# Create final unified index
unified = {
    'version': '1.1',
    'sources': sources_seen,
    'skills': skills,
    'total_skills': len(skills),
    'categories': categories,
    'agents_supported': ['claude-code', 'codex', 'cursor', 'gemini-cli', 'opencode', 'copilot', 'windsurf', 'kiro'],
    'agent_skill_counts': agent_counts,
    'last_updated': datetime.utcnow().isoformat() + 'Z'
}

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(unified, f, indent=2)

print(f'Unified skills index created with {len(skills)} skills')
"

    # Clean up temp file
    rm -f "$SKILLS_META"

    # Frontmatter parsing quality gate: block-scalar markers that
    # survived into descriptions indicate a parsing gap.
    BAD_DESC=$(SKILLS_INDEX_OUT="$SKILLS_DIR/all-skills.json" python3 -c "
import json, os
with open(os.environ['SKILLS_INDEX_OUT'], encoding='utf-8') as f:
    data = json.load(f)
bad = sum(1 for s in data['skills']
          if (s.get('description') or '').strip() in ('>', '>-', '>+', '|', '|-', '|+'))
print(bad)
") || BAD_DESC="?"
    BAD_DESC="${BAD_DESC:-?}"
    if [ "$BAD_DESC" = "0" ]; then
        log_success "All skill descriptions parsed (no block-scalar placeholders)"
    else
        log_warn "Index still contains ${BAD_DESC} block-scalar placeholder descriptions"
    fi

    log_success "Skills aggregation complete"
}

# Setup claude-mem for persistent memory
setup_memory() {
    log_info "Setting up persistent memory (claude-mem)..."

    MEMORY_DIR="$UNIFIED_DIR/memory"
    mkdir -p "$MEMORY_DIR/hooks"

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
      plugin_path: "${AGENT_ENHANCEMENTS_BASE_DIR}/claude-mem/.claude-plugin"
      enabled: true

    codex:
      plugin_path: "${AGENT_ENHANCEMENTS_BASE_DIR}/claude-mem/.codex-plugin"
      enabled: true

    cursor:
      plugin_path: "${AGENT_ENHANCEMENTS_BASE_DIR}/claude-mem/.cursor-plugin"
      enabled: true

    opencode:
      plugin_path: "${AGENT_ENHANCEMENTS_BASE_DIR}/claude-mem/.opencode"
      enabled: true

    gemini-cli:
      plugin_path: "${AGENT_ENHANCEMENTS_BASE_DIR}/claude-mem/.gemini"
      enabled: true

    windsurf:
      plugin_path: "${AGENT_ENHANCEMENTS_BASE_DIR}/claude-mem/.windsurf"
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

    # Create agent-specific memory hook scripts using Python for safe SQL
    for agent in "${AGENTS[@]}"; do
        cat > "$MEMORY_DIR/hooks/${agent}-memory-hook.py" << 'PYEOF'
#!/usr/bin/env python3
"""
Memory hook for AGENT_PLACEHOLDER
This script is called by the agent to save/load memory
Uses parameterized queries to prevent SQL injection
"""

import sqlite3
import sys
import os
import json
from datetime import datetime

AGENT = "AGENT_PLACEHOLDER"
MEMORY_ROOT = os.environ.get("AGENT_MEMORY_ROOT", os.path.expanduser("~/.agent-memory"))
DB_PATH = os.path.join(MEMORY_ROOT, "memory.db")

def init_db():
    os.makedirs(MEMORY_ROOT, exist_ok=True)
    os.makedirs(os.path.join(MEMORY_ROOT, "projects"), exist_ok=True)
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
                embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(agent, project, memory_type, key)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_project ON memories(agent, project)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON memories(expires_at)")

def save_memory(key, value, memory_type="session_context", project=None, metadata=None, ttl_days=None):
    if project is None:
        project = os.path.basename(os.getcwd())

    expires_at = None
    if ttl_days:
        from datetime import timedelta
        # SQLite format ("YYYY-MM-DD HH:MM:SS") so that comparisons
        # against datetime('now') work: the ISO "T" separator sorts
        # after a space and broke timely expiry cleanup.
        expires_at = (datetime.now() + timedelta(days=ttl_days)).strftime("%Y-%m-%d %H:%M:%S")

    meta_json = json.dumps(metadata) if metadata else None

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO memories
            (agent, project, memory_type, key, value, metadata, updated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
        """, (AGENT, project, memory_type, key, value, meta_json, expires_at))

def load_memory(key, memory_type="session_context", project=None):
    if project is None:
        project = os.path.basename(os.getcwd())

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT value FROM memories
            WHERE agent=? AND project=? AND memory_type=? AND key=?
            ORDER BY updated_at DESC LIMIT 1
        """, (AGENT, project, memory_type, key))
        row = cursor.fetchone()
        return row[0] if row else None

def list_memories(memory_type=None, project=None, limit=20):
    if project is None:
        project = os.path.basename(os.getcwd())

    with sqlite3.connect(DB_PATH) as conn:
        if memory_type:
            cursor = conn.execute("""
                SELECT memory_type, key, value, metadata, updated_at
                FROM memories
                WHERE agent=? AND project=? AND memory_type=?
                ORDER BY updated_at DESC LIMIT ?
            """, (AGENT, project, memory_type, limit))
        else:
            cursor = conn.execute("""
                SELECT memory_type, key, value, metadata, updated_at
                FROM memories
                WHERE agent=? AND project=?
                ORDER BY updated_at DESC LIMIT ?
            """, (AGENT, project, limit))

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

def delete_memory(key, memory_type="session_context", project=None):
    if project is None:
        project = os.path.basename(os.getcwd())

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            DELETE FROM memories
            WHERE agent=? AND project=? AND memory_type=? AND key=?
        """, (AGENT, project, memory_type, key))
        return cursor.rowcount > 0

def cleanup_expired():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            DELETE FROM memories
            WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
        """)
        return cursor.rowcount

def main():
    if len(sys.argv) < 2:
        print("Usage: memory-hook.py <command> [args...]")
        print("Commands: save <key> <value> [type] [project] [ttl_days]")
        print("          load <key> [type] [project]")
        print("          list [type] [project] [limit]")
        print("          delete <key> [type] [project]")
        print("          cleanup")
        sys.exit(1)

    init_db()
    command = sys.argv[1]

    if command == "save":
        if len(sys.argv) < 4:
            print("Usage: memory-hook.py save <key> <value> [type] [project] [ttl_days]")
            sys.exit(1)
        key = sys.argv[2]
        value = sys.argv[3]
        mem_type = sys.argv[4] if len(sys.argv) > 4 else "session_context"
        project = sys.argv[5] if len(sys.argv) > 5 else None
        ttl = int(sys.argv[6]) if len(sys.argv) > 6 else None
        save_memory(key, value, mem_type, project, ttl_days=ttl)
        print(f"Saved: {key} ({mem_type})")

    elif command == "load":
        if len(sys.argv) < 3:
            print("Usage: memory-hook.py load <key> [type] [project]")
            sys.exit(1)
        key = sys.argv[2]
        mem_type = sys.argv[3] if len(sys.argv) > 3 else "session_context"
        project = sys.argv[4] if len(sys.argv) > 4 else None
        value = load_memory(key, mem_type, project)
        if value:
            print(value)
        else:
            print(f"Memory not found: {key}", file=sys.stderr)
            sys.exit(1)

    elif command == "list":
        mem_type = sys.argv[2] if len(sys.argv) > 2 else None
        project = sys.argv[3] if len(sys.argv) > 3 else None
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 20
        memories = list_memories(mem_type, project, limit)
        for m in memories:
            print(f"[{m['type']}] {m['key']}: {m['value']} (updated: {m['updated']})")

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: memory-hook.py delete <key> [type] [project]")
            sys.exit(1)
        key = sys.argv[2]
        mem_type = sys.argv[3] if len(sys.argv) > 3 else "session_context"
        project = sys.argv[4] if len(sys.argv) > 4 else None
        if delete_memory(key, mem_type, project):
            print(f"Deleted: {key}")
        else:
            print(f"Not found: {key}")
            sys.exit(1)

    elif command == "cleanup":
        count = cleanup_expired()
        print(f"Cleaned up {count} expired memories")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
PYEOF
        sed -i "s/AGENT_PLACEHOLDER/$agent/g" "$MEMORY_DIR/hooks/${agent}-memory-hook.py"
        chmod +x "$MEMORY_DIR/hooks/${agent}-memory-hook.py"

        # Also create a bash wrapper for backward compatibility
        cat > "$MEMORY_DIR/hooks/${agent}-memory-hook.sh" << 'SHEOF'
#!/bin/bash
# Bash wrapper for memory hook - delegates to Python script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT="AGENT_PLACEHOLDER"
exec python3 "$SCRIPT_DIR/${AGENT}-memory-hook.py" "$@"
SHEOF
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
    HEADROOM_CMD=""
    if [ -f "$BASE_DIR/headroom/target/release/headroom" ]; then
        log_success "headroom binary found at $BASE_DIR/headroom/target/release/headroom"
        HEADROOM_CMD="$BASE_DIR/headroom/target/release/headroom"
    elif command -v headroom &> /dev/null; then
        log_success "headroom binary found in PATH"
        HEADROOM_CMD="headroom"
    elif [ -f "$BASE_DIR/headroom/Cargo.toml" ]; then
        if command -v cargo &> /dev/null; then
            log_info "Building headroom from source..."
            if (cd "$BASE_DIR/headroom" && cargo build --release 2>&1 | tail -20); then
                if [ -f "$BASE_DIR/headroom/target/release/headroom" ]; then
                    HEADROOM_CMD="$BASE_DIR/headroom/target/release/headroom"
                    log_success "headroom built successfully"
                else
                    log_warn "headroom build did not produce a binary, will use fallback compression"
                    HEADROOM_CMD=""
                fi
            else
                log_warn "headroom build failed, will use fallback compression"
                HEADROOM_CMD=""
            fi
        else
            log_warn "cargo not found, will use fallback compression"
            HEADROOM_CMD=""
        fi
    else
        log_warn "headroom not found, using fallback"
        HEADROOM_CMD=""
    fi

    # Create compression configuration
    cat > "$COMPRESSION_DIR/config.yaml" << EOF
# Context Compression Configuration

compression:
  # Engine: headroom, native, or none
  engine: "headroom"

  # Headroom settings
  headroom:
    binary_path: "${HEADROOM_CMD:-headroom}"
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

    # Create compression wrapper script
    cat > "$COMPRESSION_DIR/compress.sh" << 'EOF'
#!/bin/bash
# Universal context compression wrapper

set -euo pipefail

# Resolve the installation root from this script's location; the
# AGENT_ENHANCEMENTS_BASE_DIR environment variable overrides it.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(dirname "$SCRIPT_DIR")"
BASE_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-$(dirname "$UNIFIED_DIR")}"
CONFIG_FILE="$UNIFIED_DIR/compression/config.yaml"

INPUT="${1:-/dev/stdin}"
MODE="${2:-auto}"
AGENT="${3:-claude-code}"

# Find headroom binary: env override first, then repo build, then PATH
HEADROOM_BIN="${HEADROOM_BIN:-}"
if [ -z "$HEADROOM_BIN" ]; then
    if [ -x "$BASE_DIR/headroom/target/release/headroom" ]; then
        HEADROOM_BIN="$BASE_DIR/headroom/target/release/headroom"
    elif command -v headroom &> /dev/null; then
        HEADROOM_BIN="headroom"
    fi
fi

# Read stdin once into a temp file so content detection and compression
# both see the full stream. Previously the detection pass consumed stdin
# and the compression pass received nothing.
TMP_INPUT="$(mktemp "${TMPDIR:-/tmp}/compress-input.XXXXXX")"
trap 'rm -f "$TMP_INPUT"' EXIT
if [ "$INPUT" = "-" ] || [ "$INPUT" = "/dev/stdin" ]; then
    cat > "$TMP_INPUT"
    INPUT="$TMP_INPUT"
fi

if [ -n "$HEADROOM_BIN" ]; then
    case "$MODE" in
        code|logs|json|markdown|generic)
            "$HEADROOM_BIN" compress --mode "$MODE" < "$INPUT"
            ;;
        auto)
            # Detect content type from the first 100 lines
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
        *)
            echo "Unknown mode: $MODE (use auto, code, logs, json, markdown or generic)" >&2
            exit 1
            ;;
    esac
else
    # Fallback: basic compression without headroom.
    # "|| true" because head closing the pipe early (truncation at 5000
    # lines) raises SIGPIPE for upstream stages under "set -o pipefail",
    # which is expected behaviour here, not an error.
    cat "$INPUT" | \
        # Remove trailing whitespace
        sed 's/[[:space:]]\+$//' | \
        # Compress repeated lines (keep first occurrence)
        awk '!seen[$0]++' | \
        # Limit output
        head -5000 || true
fi
EOF
    chmod +x "$COMPRESSION_DIR/compress.sh"

    log_success "Context compression configured"
}

# Create agent-specific configurations (non-destructive merge)
create_agent_configs() {
    log_info "Creating agent-specific configurations (preserving existing)..."

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

    log_success "Agent configurations merged"
}

# Merge JSON configs using Python - replace hooks, preserve other keys
merge_json_config() {
    local target_file="$1"
    local enhancement_json="$2"
    local backup_file="${target_file}.backup.$(date +%s)"

    if [ ! -f "$target_file" ]; then
        # No existing config - write enhancement directly
        echo "$enhancement_json" > "$target_file"
        log_info "Created new config: $target_file"
        return
    fi

    # Backup original
    cp "$target_file" "$backup_file"
    log_info "Backed up existing config to $backup_file"

    # Merge using Python - replace hooks key, preserve other keys.
    # Paths and payload are passed via environment variables so that
    # JSON escape sequences (\") survive intact: routing them through a
    # Python string literal stripped the backslashes and produced invalid
    # JSON. It also removes any injection risk from file paths.
    TARGET_FILE="$target_file" ENHANCEMENT_JSON="$enhancement_json" \
    python3 -c "
import json
import os
import sys

target = os.environ['TARGET_FILE']

with open(target, 'r') as f:
    existing = json.load(f)

enhancement = json.loads(os.environ['ENHANCEMENT_JSON'])

# For hooks, replace entirely. For other keys, deep merge.
def merge_configs(base, update):
    for key, value in update.items():
        if key == 'hooks':
            # Replace hooks entirely (don't merge lists)
            base[key] = value
        elif key in base and isinstance(base[key], dict) and isinstance(value, dict):
            merge_configs(base[key], value)
        else:
            # New key or non-dict - add/update
            base[key] = value

merge_configs(existing, enhancement)

with open(target, 'w') as f:
    json.dump(existing, f, indent=2)
"
    log_success "Merged enhancement into $target_file (hooks replaced, other keys preserved)"
}

# Merge a marker-guarded markdown section into an AGENTS.md-style file
# (used for Codex and OpenCode global instructions). Content outside the
# markers is always preserved, so user-maintained instructions survive
# repeated setup runs.
merge_agents_md() {
    local target_file="$1"
    local section_file="$2"

    AGENTS_MD_TARGET="$target_file" AGENTS_MD_SECTION_FILE="$section_file" \
    python3 -c "
import os

target = os.environ['AGENTS_MD_TARGET']
section_file = os.environ['AGENTS_MD_SECTION_FILE']
BEGIN = '<!-- agent-enhancements:begin -->'
END = '<!-- agent-enhancements:end -->'

with open(section_file, 'r', encoding='utf-8') as f:
    section = f.read().rstrip()

existing = ''
if os.path.exists(target):
    with open(target, 'r', encoding='utf-8', errors='replace') as f:
        existing = f.read()

block = BEGIN + '\n' + section + '\n' + END
if BEGIN in existing and END in existing:
    pre, rest = existing.split(BEGIN, 1)
    _, post = rest.split(END, 1)
    merged = pre + block + post
elif existing.strip():
    merged = existing.rstrip() + '\n\n' + block + '\n'
else:
    merged = block + '\n'

os.makedirs(os.path.dirname(target), exist_ok=True)
with open(target, 'w', encoding='utf-8') as f:
    f.write(merged)
"
}

# Merge YAML configs using Python - replace hooks, preserve other keys
merge_yaml_config() {
    local target_file="$1"
    local enhancement_yaml="$2"
    local backup_file="${target_file}.backup.$(date +%s)"

    if [ ! -f "$target_file" ]; then
        echo "$enhancement_yaml" > "$target_file"
        log_info "Created new config: $target_file"
        return
    fi

    cp "$target_file" "$backup_file"
    log_info "Backed up existing config to $backup_file"

    TARGET_FILE="$target_file" ENHANCEMENT_YAML="$enhancement_yaml" \
    python3 -c "
import os
import sys

try:
    import yaml
except ImportError:
    print('PyYAML is required for YAML config merging (pip install pyyaml)', file=sys.stderr)
    sys.exit(1)

target = os.environ['TARGET_FILE']

with open(target, 'r') as f:
    existing = yaml.safe_load(f) or {}

enhancement = yaml.safe_load(os.environ['ENHANCEMENT_YAML'])

# For hooks, replace entirely. For other keys, deep merge.
def merge_configs(base, update):
    for key, value in update.items():
        if key == 'hooks':
            # Replace hooks entirely (don't merge lists)
            base[key] = value
        elif key in base and isinstance(base[key], dict) and isinstance(value, dict):
            merge_configs(base[key], value)
        else:
            # New key or non-dict - add/update
            base[key] = value

merge_configs(existing, enhancement)

with open(target, 'w') as f:
    yaml.dump(existing, f, default_flow_style=False, sort_keys=False)
"
    log_success "Merged enhancement into $target_file (hooks replaced, other keys preserved)"
}

create_claude_code_config() {
    CLAUDE_DIR="$HOME/.claude"
    mkdir -p "$CLAUDE_DIR"

    # Always update CLAUDE.md (it's documentation, not credentials)
    cat > "$CLAUDE_DIR/CLAUDE.md" << EOF
# Claude Code Enhanced Configuration

## System Prompt
@$UNIFIED_DIR/prompts/claude-code-system-prompt.txt

## Skills
- Source: $UNIFIED_DIR/skills
- Auto-load: true
- Categories: all
- Native activation: curated set (anthropic-skills + replica-skill) is
  symlinked into ~/.claude/skills/ and ~/.agents/skills/ at setup time;
  add more with: bash $UNIFIED_DIR/scripts/link-skills.sh --set all
- Task-to-capability mapping: python3 $UNIFIED_DIR/scripts/registry.py map "<task>"

## Memory (claude-mem)
- Enabled: true
- Plugin: $BASE_DIR/claude-mem/.claude-plugin
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

    # Merge hooks into existing settings.json (preserves env, credentials, etc.)
    ENHANCEMENT_JSON='{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "'"$UNIFIED_DIR"'/memory/hooks/claude-code-memory-hook.py save \"pre_tool_use:${TOOL_NAME}\" \"${TOOL_INPUT}\" session_context"
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
            "command": "'"$UNIFIED_DIR"'/memory/hooks/claude-code-memory-hook.py save \"post_tool_use:${TOOL_NAME}\" \"${TOOL_RESULT}\" session_context"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "'"$UNIFIED_DIR"'/memory/hooks/claude-code-memory-hook.py save \"session_summary\" \"${SESSION_SUMMARY}\" session_context"
          }
        ]
      }
    ]
  }
}'
    merge_json_config "$CLAUDE_DIR/settings.json" "$ENHANCEMENT_JSON"
    log_success "Claude Code configuration merged (credentials preserved)"
}

create_codex_config() {
    CODEX_DIR="$HOME/.codex"
    mkdir -p "$CODEX_DIR"

    # Codex CLI reads ~/.codex/AGENTS.md for global instructions and
    # ~/.codex/config.toml (TOML) for settings. It has no native
    # skills/memory/hooks config keys, so the integration is delivered as
    # instructions in AGENTS.md. (Older setup versions wrote config.yaml,
    # which Codex never reads; it is cleaned up below.)
    AGENTS_SECTION_FILE="$(mktemp "${TMPDIR:-/tmp}/codex-agents.XXXXXX")"
    cat > "$AGENTS_SECTION_FILE" << EOF
## AgentEnhancements integration

### Skills catalog (3,000+ skills, on-demand)
- Find skills for a task: python3 $UNIFIED_DIR/scripts/load-skills.py codex "<task description>"
- Read a skill: $UNIFIED_DIR/skills/by-category/<category>/<skill-name>/SKILL.md
- Full index: $UNIFIED_DIR/skills/all-skills.json

When a task matches a skill in the catalog, load its SKILL.md and follow it.

### Persistent memory (cross-session)
Codex has no automatic hook system, so invoke memory explicitly:
- Task start: python3 $UNIFIED_DIR/scripts/memory.py codex load "project_context"
- After a decision: python3 $UNIFIED_DIR/scripts/memory.py codex save "<key>" "<value>"
- List memories: python3 $UNIFIED_DIR/scripts/memory.py codex list

### Context compression
For long transcripts:
$UNIFIED_DIR/compression/compress.sh <input-file> <auto|code|logs|json|markdown|generic>

### Reference system prompt
$UNIFIED_DIR/prompts/codex-system-prompt.txt

### Native skills (auto-discovered)
A curated set (anthropic-skills 19 + replica-skill 11) is symlinked into
~/.claude/skills/ and ~/.agents/skills/ by setup.sh, so Agent Skills
compatible harnesses pick it up automatically. Add more:
bash $UNIFIED_DIR/scripts/link-skills.sh --set superpowers|<skill-name>|--all

### Task-to-capability mapping
python3 $UNIFIED_DIR/scripts/registry.py map "<task description>"
(covers skills, catalog plugins and MCP servers in one query)
EOF
    merge_agents_md "$CODEX_DIR/AGENTS.md" "$AGENTS_SECTION_FILE"
    rm -f "$AGENTS_SECTION_FILE"

    # Remove the stale config.yaml written by older setup versions
    # (signature-checked: only files carrying our integration keys).
    if [ -f "$CODEX_DIR/config.yaml" ] && grep -q '^system_prompt: "@' "$CODEX_DIR/config.yaml" 2>/dev/null; then
        rm -f "$CODEX_DIR/config.yaml"
        log_info "Removed stale ~/.codex/config.yaml (Codex reads config.toml, never YAML)"
    fi

    log_success "Codex configuration merged (~/.codex/AGENTS.md)"
}

create_opencode_config() {
    OPENCODE_DIR="$HOME/.config/opencode"
    mkdir -p "$OPENCODE_DIR"

    # OpenCode reads ~/.config/opencode/opencode.json (schema:
    # https://opencode.ai/config.json) - NOT config.json. Valid keys used
    # here: "instructions" (extra instruction files) and "skills" (skill
    # directories; OpenCode scans grouping directories up to six levels,
    # so by-category/<category>/<skill>/SKILL.md is discovered).
    ENHANCEMENT_JSON='{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["'"$UNIFIED_DIR"'/prompts/opencode-system-prompt.txt"],
  "skills": ["'"$UNIFIED_DIR"'/skills/by-category"]
}'
    merge_json_config "$OPENCODE_DIR/opencode.json" "$ENHANCEMENT_JSON"

    # Global instructions, marker-guarded (user content preserved)
    AGENTS_SECTION_FILE="$(mktemp "${TMPDIR:-/tmp}/opencode-agents.XXXXXX")"
    cat > "$AGENTS_SECTION_FILE" << EOF
## AgentEnhancements integration

### Skills catalog (3,000+ skills, on-demand)
- Find skills for a task: python3 $UNIFIED_DIR/scripts/load-skills.py opencode "<task description>"
- Read a skill: $UNIFIED_DIR/skills/by-category/<category>/<skill-name>/SKILL.md
- Full index: $UNIFIED_DIR/skills/all-skills.json
- Native discovery: the skills array in opencode.json points at
  $UNIFIED_DIR/skills/by-category (narrow it to specific categories
  to reduce per-session skill metadata).
- Native activation: a curated set (anthropic-skills + replica-skill) is
  also symlinked into ~/.agents/skills/ by setup.sh; add more with
  bash $UNIFIED_DIR/scripts/link-skills.sh --set all

### Persistent memory (cross-session)
Invoke memory explicitly (no automatic hooks):
- python3 $UNIFIED_DIR/scripts/memory.py opencode save "<key>" "<value>"
- python3 $UNIFIED_DIR/scripts/memory.py opencode load "<key>"

### Context compression
$UNIFIED_DIR/compression/compress.sh <input-file> <auto|code|logs|json|markdown|generic>

### Reference system prompt
$UNIFIED_DIR/prompts/opencode-system-prompt.txt
EOF
    merge_agents_md "$OPENCODE_DIR/AGENTS.md" "$AGENTS_SECTION_FILE"
    rm -f "$AGENTS_SECTION_FILE"

    # Remove the stale config.json written by older setup versions
    # (signature-checked: only files carrying our fictional keys).
    if [ -f "$OPENCODE_DIR/config.json" ] && grep -q '"systemPrompt"' "$OPENCODE_DIR/config.json" 2>/dev/null; then
        rm -f "$OPENCODE_DIR/config.json"
        log_info "Removed stale ~/.config/opencode/config.json (OpenCode reads opencode.json)"
    fi

    log_success "OpenCode configuration merged (~/.config/opencode/opencode.json + AGENTS.md)"
}

create_cursor_config() {
    # Cursor reads rules from ~/.cursor/rules/*.mdc (global rules) or
    # .cursor/rules/ per project. settings.json is Cursor's real settings
    # file and must not carry integration keys, so the legacy fictional
    # keys are removed from it (signature-checked) and the integration
    # moves to a global rule.
    CURSOR_RULES_DIR="$HOME/.cursor/rules"
    mkdir -p "$CURSOR_RULES_DIR"

    # .mdc rule with frontmatter; invoked based on relevance (not alwaysApply)
    cat > "$CURSOR_RULES_DIR/agent-enhancements.mdc" << EOF
---
description: AgentEnhancements skills catalog, memory and context compression
alwaysApply: false
---
## AgentEnhancements integration

### Skills catalog (3,000+ skills, on-demand)
- Find skills for a task: python3 $UNIFIED_DIR/scripts/load-skills.py cursor "<task description>"
- Read a skill: $UNIFIED_DIR/skills/by-category/<category>/<skill-name>/SKILL.md
- Full index: $UNIFIED_DIR/skills/all-skills.json
- Task-to-capability mapping (skills + plugins + MCP):
  python3 $UNIFIED_DIR/scripts/registry.py map "<task description>"
- Native activation: curated set symlinked into ~/.agents/skills/ by
  setup.sh; add more: bash $UNIFIED_DIR/scripts/link-skills.sh --set all

### Persistent memory (cross-session)
Invoke memory explicitly:
- python3 $UNIFIED_DIR/scripts/memory.py cursor save "<key>" "<value>"
- python3 $UNIFIED_DIR/scripts/memory.py cursor load "<key>"

### Context compression
$UNIFIED_DIR/compression/compress.sh <input-file> <auto|code|logs|json|markdown|generic>
EOF

    # Remove fictional integration keys that older setup versions merged
    # into Cursor's real settings file (signature-checked).
    local settings_file="$HOME/.cursor/settings.json"
    if [ -f "$settings_file" ] && grep -q '"systemPrompt"' "$settings_file" 2>/dev/null; then
        SETTINGS_FILE="$settings_file" python3 -c "
import json, os
path = os.environ['SETTINGS_FILE']
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)
for key in ('systemPrompt', 'skills', 'memory', 'compression', 'hooks'):
    data.pop(key, None)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"
        log_info "Cleaned fictional integration keys from ~/.cursor/settings.json"
    fi

    log_success "Cursor configuration merged (~/.cursor/rules/agent-enhancements.mdc)"
}

create_gemini_config() {
    GEMINI_DIR="$HOME/.gemini"
    mkdir -p "$GEMINI_DIR"

    # Gemini CLI reads ~/.gemini/GEMINI.md as the global context file
    # (hierarchical memory). That is the activation channel; the YAML
    # below remains as a reference summary of the integration settings.
    AGENTS_SECTION_FILE="$(mktemp "${TMPDIR:-/tmp}/gemini-agents.XXXXXX")"
    cat > "$AGENTS_SECTION_FILE" << EOF
## AgentEnhancements integration

### Skills catalog (3,000+ skills, on-demand)
- Find skills for a task: python3 $UNIFIED_DIR/scripts/load-skills.py gemini-cli "<task description>"
- Read a skill: $UNIFIED_DIR/skills/by-category/<category>/<skill-name>/SKILL.md
- Full index: $UNIFIED_DIR/skills/all-skills.json
- Task-to-capability mapping (skills + plugins + MCP):
  python3 $UNIFIED_DIR/scripts/registry.py map "<task description>"
- Native activation: curated set symlinked into ~/.agents/skills/ by
  setup.sh; add more: bash $UNIFIED_DIR/scripts/link-skills.sh --set all

### Persistent memory (cross-session)
Invoke memory explicitly:
- python3 $UNIFIED_DIR/scripts/memory.py gemini-cli save "<key>" "<value>"
- python3 $UNIFIED_DIR/scripts/memory.py gemini-cli load "<key>"

### Context compression
$UNIFIED_DIR/compression/compress.sh <input-file> <auto|code|logs|json|markdown|generic>
EOF
    merge_agents_md "$GEMINI_DIR/GEMINI.md" "$AGENTS_SECTION_FILE"
    rm -f "$AGENTS_SECTION_FILE"

    ENHANCEMENT_YAML='
system_prompt: "@'"$UNIFIED_DIR"'/prompts/gemini-cli-system-prompt.txt"

skills:
  directory: "'"$UNIFIED_DIR"'/skills"
  auto_load: true

memory:
  enabled: true
  plugin: "'"$BASE_DIR"'/claude-mem/.gemini"

compression:
  enabled: true
  engine: "headroom"
  budget: 1000000

hooks:
  pre_tool: "'"$UNIFIED_DIR"'/memory/hooks/gemini-cli-memory-hook.py save"
  post_tool: "'"$UNIFIED_DIR"'/memory/hooks/gemini-cli-memory-hook.py save"
  stop: "'"$UNIFIED_DIR"'/memory/hooks/gemini-cli-memory-hook.py save session_end"
'
    merge_yaml_config "$GEMINI_DIR/config.yaml" "$ENHANCEMENT_YAML"
    log_success "Gemini CLI configuration merged (~/.gemini/GEMINI.md + reference config.yaml)"
}

create_windsurf_config() {
    # Windsurf reads global rules from ~/.codeium/windsurf/rules/.
    # The legacy ~/.windsurf/config.yaml was never read by Windsurf and is
    # cleaned up below (signature-checked).
    WINDSURF_RULES_DIR="$HOME/.codeium/windsurf/rules"
    mkdir -p "$WINDSURF_RULES_DIR"

    AGENTS_SECTION_FILE="$(mktemp "${TMPDIR:-/tmp}/windsurf-agents.XXXXXX")"
    cat > "$AGENTS_SECTION_FILE" << EOF
## AgentEnhancements integration

### Skills catalog (3,000+ skills, on-demand)
- Find skills for a task: python3 $UNIFIED_DIR/scripts/load-skills.py windsurf "<task description>"
- Read a skill: $UNIFIED_DIR/skills/by-category/<category>/<skill-name>/SKILL.md
- Full index: $UNIFIED_DIR/skills/all-skills.json
- Task-to-capability mapping (skills + plugins + MCP):
  python3 $UNIFIED_DIR/scripts/registry.py map "<task description>"
- Native activation: curated set symlinked into ~/.agents/skills/ by
  setup.sh; add more: bash $UNIFIED_DIR/scripts/link-skills.sh --set all

### Persistent memory (cross-session)
Invoke memory explicitly:
- python3 $UNIFIED_DIR/scripts/memory.py windsurf save "<key>" "<value>"
- python3 $UNIFIED_DIR/scripts/memory.py windsurf load "<key>"

### Context compression
$UNIFIED_DIR/compression/compress.sh <input-file> <auto|code|logs|json|markdown|generic>
EOF
    merge_agents_md "$WINDSURF_RULES_DIR/agent-enhancements.md" "$AGENTS_SECTION_FILE"
    rm -f "$AGENTS_SECTION_FILE"

    # Remove the stale config.yaml written by older setup versions
    # (signature-checked: only files carrying our integration keys).
    local legacy_config="$HOME/.windsurf/config.yaml"
    if [ -f "$legacy_config" ] && grep -q '^system_prompt: "@' "$legacy_config" 2>/dev/null; then
        rm -f "$legacy_config"
        log_info "Removed stale ~/.windsurf/config.yaml (Windsurf reads ~/.codeium/windsurf/rules/)"
    fi

    log_success "Windsurf configuration merged (~/.codeium/windsurf/rules/agent-enhancements.md)"
}

create_copilot_config() {
    COPILOT_DIR="$HOME/.config/github-copilot"
    mkdir -p "$COPILOT_DIR"

    ENHANCEMENT_YAML='
skills:
  directory: "'"$UNIFIED_DIR"'/skills"
  auto_load: true

memory:
  enabled: true
  # Copilot uses VS Code settings for memory

compression:
  enabled: true
  engine: "headroom"
  budget: 32000
'
    merge_yaml_config "$COPILOT_DIR/config.yaml" "$ENHANCEMENT_YAML"
    log_success "GitHub Copilot configuration merged"
}

create_kiro_config() {
    KIRO_DIR="$HOME/.kiro"
    mkdir -p "$KIRO_DIR"

    ENHANCEMENT_YAML='
system_prompt: "@'"$UNIFIED_DIR"'/prompts/kiro-system-prompt.txt"

skills:
  directory: "'"$UNIFIED_DIR"'/skills"
  auto_load: true

memory:
  enabled: true

compression:
  enabled: true
  engine: "headroom"
  budget: 128000
'
    merge_yaml_config "$KIRO_DIR/config.yaml" "$ENHANCEMENT_YAML"
    log_success "Kiro configuration merged"
}

# Create universal launcher script
create_launcher() {
    log_info "Creating universal launcher..."

    cat > "$UNIFIED_DIR/launch-agent.sh" << 'EOF'
#!/bin/bash
# Universal AI Agent Launcher with Enhancements

set -euo pipefail

AGENT="${1:-claude-code}"
if [ $# -gt 0 ]; then
    shift
fi

# Resolve installation paths from this script's location; environment
# variables take precedence.
UNIFIED_DIR="${AGENT_ENHANCEMENTS_UNIFIED_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
BASE_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-$(dirname "$UNIFIED_DIR")}"

# Detected agents (written by setup.sh); pre-declared so the script also
# works when the file is missing.
AGENTS=()
# shellcheck source=/dev/null
source "$UNIFIED_DIR/config/detected-agents.sh" 2>/dev/null || true

# Validate agent
if [[ ! " ${AGENTS[*]:-} " =~ " ${AGENT} " ]]; then
    echo "Agent '$AGENT' not detected. Available: ${AGENTS[*]:-none}"
    echo "Run $UNIFIED_DIR/setup.sh to (re)detect installed agents."
    echo "Usage: $0 <agent> [args...]"
    exit 1
fi

# Initialize memory
if [ -x "$UNIFIED_DIR/memory/init-memory.sh" ]; then
    "$UNIFIED_DIR/memory/init-memory.sh"
else
    echo "Warning: memory initializer not found at $UNIFIED_DIR/memory/init-memory.sh" >&2
fi

# Set environment variables
export AGENT_MEMORY_ROOT="${AGENT_MEMORY_ROOT:-$HOME/.agent-memory}"
export AGENT_SKILLS_DIR="$UNIFIED_DIR/skills"
export AGENT_COMPRESSION_CONFIG="$UNIFIED_DIR/compression/config.yaml"
export AGENT_PROMPTS_DIR="$UNIFIED_DIR/prompts"
export AGENT_ENHANCEMENTS_BASE_DIR="$BASE_DIR"
export AGENT_ENHANCEMENTS_UNIFIED_DIR="$UNIFIED_DIR"

# Launch agent with enhancements
case "$AGENT" in
    claude-code) exec claude "$@" ;;
    codex)       exec codex "$@" ;;
    opencode)    exec opencode "$@" ;;
    cursor)      exec cursor "$@" ;;
    gemini-cli)  exec gemini "$@" ;;
    windsurf)    exec windsurf "$@" ;;
    copilot)     exec gh copilot "$@" ;;
    kiro)        exec kiro "$@" ;;
    *)
        echo "Unknown agent: $AGENT"
        exit 1
        ;;
esac
EOF
    chmod +x "$UNIFIED_DIR/launch-agent.sh"

    # Create symlink for easy access (if we have permission)
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

SKILLS_DIR = Path(os.environ.get(
    "AGENT_SKILLS_DIR",
    str(Path(__file__).resolve().parent.parent / "skills"),
))

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
        """Load a specific skill by name.

        Supports both on-disk layouts produced by this project:
        - directory skills: by-category/<category>/<name>/SKILL.md
        - flat skills:      by-category/<category>/<name>.md
        """
        # Search in all category directories
        for cat_dir in (SKILLS_DIR / "by-category").iterdir():
            if cat_dir.is_dir():
                for candidate in (
                    cat_dir / skill_name / "SKILL.md",
                    cat_dir / f"{skill_name}.md",
                ):
                    if candidate.exists():
                        return self._parse_skill(candidate)

        # Search in agent-specific directories
        agent_dir = SKILLS_DIR / "by-agent" / self.agent
        if agent_dir.exists():
            for candidate in (
                agent_dir / skill_name / "SKILL.md",
                agent_dir / f"{skill_name}.md",
            ):
                if candidate.exists():
                    return self._parse_skill(candidate)

        return {}

    def _parse_skill(self, skill_file: Path) -> Dict:
        """Parse SKILL.md file"""
        content = skill_file.read_text()
        # Parse frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    import yaml
                    frontmatter = yaml.safe_load(parts[1])
                except ImportError:
                    print(
                        "Warning: PyYAML is not installed; returning raw skill content",
                        file=sys.stderr,
                    )
                    return {"raw": content, "file": str(skill_file)}
                body = parts[2].strip()
                return {"frontmatter": frontmatter, "body": body, "file": str(skill_file)}
        return {"raw": content, "file": str(skill_file)}


def main():
    if len(sys.argv) < 3 or not sys.argv[2:]:
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
            # SQLite format ("YYYY-MM-DD HH:MM:SS") so that comparisons
            # against datetime('now') work: the ISO "T" separator sorts
            # after a space and broke timely expiry cleanup.
            expires_at = (datetime.now() + timedelta(days=ttl_days)).strftime("%Y-%m-%d %H:%M:%S")

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
            sys.exit(1)

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
import re
from pathlib import Path
from typing import Optional

HEADROOM_BIN = os.environ.get("HEADROOM_BIN", "headroom")


def _default_fallback_bin() -> str:
    """Locate the repo-built headroom binary without hardcoding paths."""
    base = os.environ.get("AGENT_ENHANCEMENTS_BASE_DIR")
    if base:
        return os.path.join(base, "headroom", "target", "release", "headroom")
    # Repo layout: <base>/unified-integration/scripts/compress.py
    return str(Path(__file__).resolve().parent.parent.parent / "headroom" / "target" / "release" / "headroom")


FALLBACK_BIN = _default_fallback_bin()

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

# Link curated skills into the native skill directories that agents read
# automatically at runtime (Claude Code: ~/.claude/skills, Agent Skills
# standard: ~/.agents/skills). Failure is non-fatal: the full catalog
# stays reachable through the loader utilities.
link_native_skills() {
    log_info "Linking curated skills into native agent skill directories..."
    if bash "$UNIFIED_DIR/scripts/link-skills.sh" --quiet; then
        log_success "Native skill activation complete (~/.claude/skills, ~/.agents/skills)"
    else
        log_warn "Native skill linking failed - agents still reach the full catalog via the loader"
    fi
}

# Main setup flow
main() {
    echo "========================================"
    echo "  Unified AI Agent Enhancement Setup"
    echo "========================================"
    echo ""
    echo "Base directory: $BASE_DIR"
    echo "Unified directory: $UNIFIED_DIR"
    echo ""

    detect_agents
    setup_prompts
    aggregate_skills
    setup_memory
    setup_compression
    create_agent_configs
    link_native_skills
    create_launcher
    create_skills_loader
    create_memory_util
    create_compression_util

    echo ""
    echo "========================================"
    echo "  Setup Complete!"
    echo "========================================"
    echo ""
    echo "Configured agents: ${AGENTS[*]:-none}"
    echo ""
    echo "Next steps:"
    echo "  1. Run: $UNIFIED_DIR/memory/init-memory.sh"
    echo "  2. Launch enhanced agent: $UNIFIED_DIR/launch-agent.sh <agent>"
    echo "  3. Or use: agent-enhanced <agent> (if symlink created)"
    echo "  4. Link more skills natively: $UNIFIED_DIR/scripts/link-skills.sh --set all"
    echo "  5. Map capabilities for a task: python3 $UNIFIED_DIR/scripts/registry.py map \"<task>\""
    echo ""
    echo "Config files created in:"
    echo "  - $UNIFIED_DIR/config/"
    echo "  - $UNIFIED_DIR/prompts/"
    echo "  - $UNIFIED_DIR/skills/"
    echo "  - $UNIFIED_DIR/memory/"
    echo "  - $UNIFIED_DIR/compression/"
    echo ""
    echo "Agent configs also placed in (per detected agent):"
    echo "  - ~/.claude/settings.json + CLAUDE.md          (Claude Code: hooks + instructions)"
    echo "  - ~/.codex/AGENTS.md                            (Codex: global instructions)"
    echo "  - ~/.config/opencode/opencode.json + AGENTS.md  (OpenCode: schema-valid config + instructions)"
    echo "  - ~/.cursor/rules/agent-enhancements.mdc        (Cursor: global rule)"
    echo "  - ~/.gemini/GEMINI.md + config.yaml             (Gemini CLI: global context + reference)"
    echo "  - ~/.codeium/windsurf/rules/agent-enhancements.md (Windsurf: global rule)"
    echo "  - ~/.config/github-copilot/config.yaml          (Copilot: reference config)"
    echo "  - ~/.kiro/config.yaml                           (Kiro: reference config)"
    echo ""
    echo "Native skill activation (all Agent Skills compatible harnesses):"
    echo "  - ~/.claude/skills/   curated set linked (Claude Code auto-discovery)"
    echo "  - ~/.agents/skills/   curated set linked (cross-agent standard)"
    echo ""
    echo "Environment variables for customization:"
    echo "  AGENT_ENHANCEMENTS_BASE_DIR - Override base directory (default: repository root detected from setup.sh location)"
    echo "  AGENT_MEMORY_ROOT - Override memory storage location (default: ~/.agent-memory)"
    echo "  HEADROOM_BIN - Override headroom binary path"
}

main "$@"