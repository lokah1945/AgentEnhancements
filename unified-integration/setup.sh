#!/bin/bash
# Unified AI Agent Enhancement Setup
# Configures all agent enhancements for: Claude Code, Codex, OpenCode, Cursor, Gemini CLI, Windsurf, Copilot, Kiro, etc.
#
# CONTRACT §2.1: Single source of truth — this is the canonical entrypoint for Linux/macOS/WSL/Git Bash.
# The shared Python core (installer.py) is called for cross-platform installation logic.
# Windows PowerShell entrypoint: setup.ps1 (also calls installer.py).

set -euo pipefail

# =============================================================================
# ONE-LINER INSTALL SUPPORT (AE-11)
# If piped (no BASH_SOURCE), clone/fetch to persistent dir and re-exec from there.
# =============================================================================
if [ -z "${BASH_SOURCE[0]:-}" ]; then
    INSTALL_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-$HOME/.local/share/AgentEnhancements}"
    AE_REF="${AGENT_ENHANCEMENTS_REF:-}"
    if [ ! -f "$INSTALL_DIR/unified-integration/setup.sh" ]; then
        git clone https://github.com/lokah1945/AgentEnhancements.git "$INSTALL_DIR"
        if [ -n "$AE_REF" ]; then
            if ! git -C "$INSTALL_DIR" fetch --quiet origin "$AE_REF" ||
               ! git -C "$INSTALL_DIR" checkout --quiet --detach FETCH_HEAD; then
                echo "[agent-enhancements] requested revision unavailable; refusing unpinned installation" >&2
                exit 1
            fi
        fi
    elif [ -d "$INSTALL_DIR/.git" ]; then
        if [ -n "$AE_REF" ]; then
            if ! git -C "$INSTALL_DIR" diff --quiet ||
               ! git -C "$INSTALL_DIR" diff --cached --quiet ||
               ! git -C "$INSTALL_DIR" fetch --quiet origin "$AE_REF" ||
               ! git -C "$INSTALL_DIR" checkout --quiet --detach FETCH_HEAD; then
                echo "[agent-enhancements] cannot safely select requested revision; installation aborted" >&2
                exit 1
            fi
        elif ! git -C "$INSTALL_DIR" pull --ff-only --quiet origin master 2>/dev/null; then
            echo "[agent-enhancements] cannot fast-forward installation; existing files preserved" >&2
            exit 1
        fi
    fi
    exec bash "$INSTALL_DIR/unified-integration/setup.sh" "$@"
fi

# =============================================================================
# LOCAL EXECUTION SETUP
# =============================================================================
# Enable recursive globbing and nullglob for prompt discovery
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

# =============================================================================
# SKILL AGGREGATION (Bash-specific, vendor-aware, keeps CONTRACT §2.3)
# This is the ONLY place that copies from vendored sources into unified-integration/skills/
# =============================================================================

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

get_skill_category() {
    local skill_file="$1"
    local category=$(parse_skill_frontmatter "$skill_file" "category")
    if [ -z "$category" ]; then category="general"; fi
    echo "$category"
}

get_skill_name() {
    local skill_file="$1"
    local name=$(parse_skill_frontmatter "$skill_file" "name")
    if [ -z "$name" ]; then name=$(basename "$(dirname "$skill_file")"); fi
    echo "$name"
}

get_skill_description() { parse_skill_frontmatter "$1" "description"; }
get_skill_tags() {
    local skill_file="$1"
    awk '
    /^---$/ { in_fm = !in_fm; next }
    in_fm && /^tags:/ { in_tags = 1; next }
    in_fm && in_tags && /^[[:space:]]*-/ {
        sub(/^[[:space:]]*-[[:space:]]*/, "")
        gsub(/^["'"'"']|["'"'"']$/, "")
        print; next
    }
    in_fm && in_tags && !/^[[:space:]]*-/ { in_tags = 0 }
    ' "$skill_file"
}
get_skill_tools() {
    local skill_file="$1"
    awk '
    /^---$/ { in_fm = !in_fm; next }
    in_fm && /^tools:/ { in_tools = 1; next }
    in_fm && in_tools && /^[[:space:]]*-/ {
        sub(/^[[:space:]]*-[[:space:]]*/, "")
        gsub(/^["'"'"']|["'"'"']$/, "")
        print; next
    }
    in_fm && in_tools && !/^[[:space:]]*-/ { in_tools = 0 }
    ' "$skill_file"
}
get_skill_risk() {
    local skill_file="$1"
    local risk=$(parse_skill_frontmatter "$skill_file" "risk")
    if [ -z "$risk" ]; then risk="safe"; fi
    echo "$risk"
}

# Aggregate skills from all vendored sources
# Aggregation order matters: later sources win name collisions (CONTRACT §2.3)
# Order: agentic-awesome-skills, ECC, Ponytail, Superpowers, replica-skill,
#        anthropic-skills (official wins), agency-agents, task-observer (pinned wins)
aggregate_skills() {
    log_info "Aggregating skills from vendored sources..."

    SKILLS_DIR="$UNIFIED_DIR/skills"

    # Security: refuse symlinked registry directories
    ensure_registry_directory() {
        if [ -L "$1" ]; then
            log_error "Refusing symlinked registry directory: $1"
            return 1
        fi
        mkdir -p "$1"
    }
    ensure_registry_directory "$SKILLS_DIR"
    ensure_registry_directory "$SKILLS_DIR/by-category"
    ensure_registry_directory "$SKILLS_DIR/by-agent"

    # Create category directories
    CATEGORIES=("security" "architecture" "testing" "refactoring" "code-review" "documentation" "devops" "ai-ml" "productivity" "general")
    for cat in "${CATEGORIES[@]}"; do
        ensure_registry_directory "$SKILLS_DIR/by-category/$cat"
    done

    # Create agent directories
    AGENT_LIST=("claude-code" "codex" "cursor" "gemini-cli" "opencode" "copilot" "windsurf" "kiro" "hermes")
    for agent in "${AGENT_LIST[@]}"; do
        ensure_registry_directory "$SKILLS_DIR/by-agent/$agent"
    done

    # Metadata accumulation (ASCII unit/record separators, no code interpolation)
    SKILLS_META="$SKILLS_DIR/.skills-meta.tmp"
    : > "$SKILLS_META"

    process_skills_source() {
        local source_name="$1"
        local source_dir="$2"
        local skills_count=0

        if [ ! -d "$source_dir" ]; then
            log_warn "Source directory not found: $source_dir"
            return
        fi

        log_info "Processing $source_name skills from $source_dir..."

        # Find skill directories (directories containing SKILL.md), one level deep
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
                    security|architecture|testing|refactoring|code-review|documentation|devops|ai-ml|productivity) ;;
                    *) skill_category="general" ;;
                esac

                # Sanitize skill name for filesystem safety
                skill_name="${skill_name//\//-}"
                skill_name="${skill_name//\\/-}"
                skill_name="${skill_name//$'\0'/}"
                skill_name=$(printf '%s' "$skill_name" | tr -d '\000-\037\177')
                if [ -z "$skill_name" ] || [ "$skill_name" = "." ] || [ "$skill_name" = ".." ]; then
                    log_warn "Skipping skill with invalid name in $skill_dir"
                    continue
                fi

                # Copy to by-category/ (replace existing)
                target_dir="$SKILLS_DIR/by-category/$skill_category/$skill_name"
                mkdir -p "$(dirname "$target_dir")"
                rm -rf "$target_dir"
                if ! cp -r "$skill_dir" "$target_dir"; then
                    log_error "Failed to copy skill bundle: $skill_name"
                    return 1
                fi

                # Copy to by-agent/ for each compatible tool
                while IFS= read -r tool; do
                    if [ -n "$tool" ]; then
                        case "$tool" in
                            claude-code|codex|cursor|gemini-cli|opencode|copilot|windsurf|kiro|hermes)
                                agent_target_dir="$SKILLS_DIR/by-agent/$tool/$skill_name"
                                mkdir -p "$(dirname "$agent_target_dir")"
                                rm -rf "$agent_target_dir"
                                if ! cp -r "$skill_dir" "$agent_target_dir"; then
                                    log_error "Failed to copy agent skill bundle: $skill_name"
                                    return 1
                                fi
                                ;;
                        esac
                    fi
                done <<< "$skill_tools"

                # Append metadata record for index builder
                printf '%s\x1f%s\x1f%s\x1f%s\x1f%s\x1f%s\x1f%s\x1f%s\x1e' \
                    "$skill_name" "$skill_category" "$skill_description" \
                    "$skill_risk" "$source_name" "$skill_tags" "$skill_tools" \
                    "$skill_dir/SKILL.md" \
                    >> "$SKILLS_META"
                skills_count=$((skills_count + 1))
            fi
        done < <(find "$source_dir" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)

        # Root-layout source: SKILL.md at source root (task-observer)
        if [ -f "$source_dir/SKILL.md" ]; then
            skill_dir="$source_dir"
            skill_name=$(get_skill_name "$skill_dir/SKILL.md")
            skill_category=$(get_skill_category "$skill_dir/SKILL.md")
            skill_description=$(get_skill_description "$skill_dir/SKILL.md")
            skill_risk=$(get_skill_risk "$skill_dir/SKILL.md")
            skill_tags=$(get_skill_tags "$skill_dir/SKILL.md")
            skill_tools=$(get_skill_tools "$skill_dir/SKILL.md")

            case "$skill_category" in
                security|architecture|testing|refactoring|code-review|documentation|devops|ai-ml|productivity) ;;
                *) skill_category="general" ;;
            esac

            skill_name="${skill_name//\//-}"
            if [ -z "$skill_name" ] || [ "$skill_name" = "." ] || [ "$skill_name" = ".." ]; then
                log_warn "Skipping skill with invalid name '${skill_name}' in $skill_dir"
            else
                target_dir="$SKILLS_DIR/by-category/$skill_category/$skill_name"
                mkdir -p "$(dirname "$target_dir")"
                rm -rf "$target_dir"
                if ! cp -r "$skill_dir" "$target_dir"; then
                    log_error "Failed to copy skill bundle: $skill_name"
                    return 1
                fi

                while IFS= read -r tool; do
                    if [ -n "$tool" ]; then
                        case "$tool" in
                            claude-code|codex|cursor|gemini-cli|opencode|copilot|windsurf|kiro|hermes)
                                agent_target_dir="$SKILLS_DIR/by-agent/$tool/$skill_name"
                                mkdir -p "$(dirname "$agent_target_dir")"
                                rm -rf "$agent_target_dir"
                                if ! cp -r "$skill_dir" "$agent_target_dir"; then
                                    log_error "Failed to copy agent skill bundle: $skill_name"
                                    return 1
                                fi
                                ;;
                        esac
                    fi
                done <<< "$skill_tools"

                printf '%s\x1f%s\x1f%s\x1f%s\x1f%s\x1f%s\x1f%s\x1f%s\x1e' \
                    "$skill_name" "$skill_category" "$skill_description" \
                    "$skill_risk" "$source_name" "$skill_tags" "$skill_tools" \
                    "$skill_dir/SKILL.md" \
                    >> "$SKILLS_META"
                skills_count=$((skills_count + 1))
            fi
        fi

        log_success "$source_name: processed $skills_count skills"
    }

    # Aggregation order (later wins collisions)
    if [ -d "$BASE_DIR/agentic-awesome-skills/skills" ]; then
        process_skills_source "agentic-awesome-skills" "$BASE_DIR/agentic-awesome-skills/skills"
    fi
    if [ -d "$BASE_DIR/ECC/skills" ]; then
        process_skills_source "ECC" "$BASE_DIR/ECC/skills"
    fi
    if [ -d "$BASE_DIR/ponytail/skills" ]; then
        process_skills_source "Ponytail" "$BASE_DIR/ponytail/skills"
    fi
    if [ -d "$BASE_DIR/superpowers/skills" ]; then
        process_skills_source "Superpowers" "$BASE_DIR/superpowers/skills"
    fi
    if [ -d "$BASE_DIR/replica-skill" ]; then
        process_skills_source "replica-skill" "$BASE_DIR/replica-skill"
    fi
    if [ -d "$BASE_DIR/anthropic-skills/skills" ]; then
        process_skills_source "anthropic-skills" "$BASE_DIR/anthropic-skills/skills"
    fi
    if [ -d "$BASE_DIR/agency-agents/skills" ]; then
        for agency_div in "$BASE_DIR"/agency-agents/skills/*/; do
            [ -d "$agency_div" ] || continue
            process_skills_source "agency-agents" "$agency_div"
        done
    fi
    if [ -d "$BASE_DIR/task-observer" ]; then
        process_skills_source "task-observer" "$BASE_DIR/task-observer"
    fi

    # Create final unified skills index with metadata
    log_info "Creating unified skills index..."
    SKILLS_META_FILE="$SKILLS_META" SKILLS_INDEX_OUT="$SKILLS_DIR/all-skills.json" \
    BASE_DIR_FOR_INDEX="$BASE_DIR" \
    python3 -c "
import json
import os
from datetime import datetime, timezone

meta_path = os.environ['SKILLS_META_FILE']
out_path = os.environ['SKILLS_INDEX_OUT']
base_dir = os.environ.get('BASE_DIR_FOR_INDEX', '')

def mini_frontmatter_parse(fm_lines):
    data = {}
    key = None
    mode = None
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
                buf.append(s[1:].strip().strip('\"\\''))
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
            buf = [v.strip('\"\\'')]
            flush()
    flush()
    return data

def parse_frontmatter_file(path):
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
    rel_agg = rel_agg.replace('\\\\', '/')

    source_path = ''
    if skill_file and base_dir:
        try:
            source_path = os.path.relpath(skill_file, base_dir)
        except ValueError:
            source_path = skill_file
    source_path = source_path.replace('\\\\', '/')

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

# Later sources win name collisions
skills = list(skills_by_name.values())
skills.sort(key=lambda s: s['name'])

categories = {}
for skill in skills:
    cat = skill.get('category', 'general')
    categories[cat] = categories.get(cat, 0) + 1

agent_counts = {}
for skill in skills:
    for tool in skill.get('tools', []):
        agent_counts[tool] = agent_counts.get(tool, 0) + 1

sources_seen = list(dict.fromkeys(s['source'] for s in skills))

unified = {
    'version': '1.1',
    'sources': sources_seen,
    'skills': skills,
    'total_skills': len(skills),
    'categories': categories,
    'agents_supported': ['claude-code', 'codex', 'cursor', 'gemini-cli', 'opencode', 'copilot', 'windsurf', 'kiro', 'hermes'],
    'agent_skill_counts': agent_counts,
    'last_updated': datetime.now(timezone.utc).isoformat()
}

try:
    with open(out_path, encoding='utf-8') as f:
        previous = json.load(f)
except (OSError, ValueError):
    previous = None
if isinstance(previous, dict):
    previous_core = {k: v for k, v in previous.items() if k != 'last_updated'}
    unified_core = {k: v for k, v in unified.items() if k != 'last_updated'}
    if previous_core == unified_core:
        print(f'Unified skills index unchanged ({len(skills)} skills); timestamp preserved')
    else:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(unified, f, indent=2)
        print(f'Unified skills index created with {len(skills)} skills')
else:
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(unified, f, indent=2)
    print(f'Unified skills index created with {len(skills)} skills')
"

    # Clean up temp file
    rm -f "$SKILLS_META"

    # Quality gate: check for block-scalar placeholders in descriptions
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

# =============================================================================
# MAIN INSTALLATION FLOW
# =============================================================================

# Parse command line arguments
COMMAND="${1:-install}"
shift || true

PYTHON_ARGS=()
DRY_RUN=false
VERBOSE=false
SKIP_SKILLS=false

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=true; PYTHON_ARGS+=("--dry-run") ;;
        --verbose|-v) VERBOSE=true; PYTHON_ARGS+=("--verbose") ;;
        --skip-skills) SKIP_SKILLS=true ;;
        --agents) shift; PYTHON_ARGS+=("--agents" "$@"); break ;;
        --force) PYTHON_ARGS+=("--force") ;;
        --skip-hooks) PYTHON_ARGS+=("--skip-hooks") ;;
        --skip-mcp) PYTHON_ARGS+=("--skip-mcp") ;;
        --skip-memory) PYTHON_ARGS+=("--skip-memory") ;;
        --skip-compression) PYTHON_ARGS+=("--skip-compression") ;;
        *) log_warn "Unknown option: $1" ;;
    esac
    shift || true
done

case "$COMMAND" in
    install)
        # Step 1: Aggregate skills (unless skipped)
        if [ "$SKIP_SKILLS" = false ]; then
            aggregate_skills
        else
            log_info "Skipping skill aggregation (--skip-skills)"
        fi

        # Step 2: Delegate to Python installer for cross-platform logic
        log_info "Running cross-platform installation via installer.py..."
        PYTHON_CMD="${PYTHON:-python3}"
        if ! "$PYTHON_CMD" -m installer install "${PYTHON_ARGS[@]}"; then
            log_error "Installation failed"
            exit 1
        fi
        log_success "Installation complete!"
        ;;

    detect)
        log_info "Detecting available agents..."
        PYTHON_CMD="${PYTHON:-python3}"
        "$PYTHON_CMD" -m installer detect "${PYTHON_ARGS[@]}"
        ;;

    aggregate-skills)
        aggregate_skills
        ;;

    *)
        log_error "Unknown command: $COMMAND"
        echo "Usage: $0 [install|detect|aggregate-skills] [options]"
        echo "Options:"
        echo "  --dry-run           Preview changes without applying"
        echo "  --verbose, -v       Verbose output"
        echo "  --skip-skills       Skip skill aggregation"
        echo "  --agents <list>     Specific agents to configure"
        echo "  --force             Force reinstall"
        echo "  --skip-hooks        Skip hook installation"
        echo "  --skip-mcp          Skip MCP setup"
        echo "  --skip-memory       Skip memory setup"
        echo "  --skip-compression  Skip compression setup"
        exit 1
        ;;
esac