#!/usr/bin/env bash
# Native skill activation: link skills from the unified registry into the
# directories that coding agents read AUTOMATICALLY at runtime:
#
#   ~/.claude/skills/   Claude Code personal skills (auto-discovered)
#   ~/.agents/skills/   cross-agent Agent Skills standard (agentskills.io)
#
# One install of AgentEnhancements aggregates every source into the unified
# registry; this tool then makes a chosen subset natively discoverable so
# no per-agent, per-skill installation is ever needed.
#
# Usage:
#   link-skills.sh                          # default curated set
#   link-skills.sh --set anthropic-skills   # one source
#   link-skills.sh --set replica-skill
#   link-skills.sh --set superpowers
#   link-skills.sh --set all                # everything (large context!)
#   link-skills.sh <skill-name> [...]       # specific skills by name
#   link-skills.sh --status                 # what is linked where
#   link-skills.sh --unlink [names ...]     # remove our links (all or named)
#   link-skills.sh --quiet                  # suppress per-skill output
#
# Environment:
#   AGENT_SKILLS_NATIVE_TARGETS  colon-separated target directories
#                               (default: ~/.claude/skills:$HOME/.agents/skills)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-$(cd "$UNIFIED_DIR/.." && pwd)}"
SKILLS_DIR="${AGENT_SKILLS_DIR:-$UNIFIED_DIR/skills}"

# Sources linked by default: the official Anthropic skills plus the
# app-cloning pipeline. Production-grade, well-scoped, and together small
# enough to keep per-session skill metadata cheap for every harness.
DEFAULT_SOURCES="anthropic-skills replica-skill"

QUIET=0

log_info()  { [ "$QUIET" = "1" ] || echo -e "\033[0;34m[link-skills]\033[0m $1"; }
log_warn()  { echo -e "\033[1;33m[link-skills:WARN]\033[0m $1" >&2; }
log_error() { echo -e "\033[0;31m[link-skills:ERROR]\033[0m $1" >&2; }

# ---------------------------------------------------------------------------
# Resolve "name<TAB>category" pairs from the unified index.
# mode: sources | names | all
# ---------------------------------------------------------------------------
resolve_skills() {
    local mode="$1"
    local filter="$2"
    INDEX_FILE="$SKILLS_DIR/all-skills.json" FILTER_MODE="$mode" FILTER="$filter" \
    python3 -c "
import json
import os

with open(os.environ['INDEX_FILE'], encoding='utf-8') as f:
    data = json.load(f)

mode = os.environ['FILTER_MODE']
filt = os.environ['FILTER']
wanted = [w for w in filt.split() if w]

seen = set()
for skill in data.get('skills', []):
    name = skill.get('name') or ''
    if not name or name in seen:
        continue
    if mode == 'sources' and skill.get('source') not in wanted:
        continue
    if mode == 'names' and name not in wanted:
        continue
    seen.add(name)
    print(name + '\t' + skill.get('category', 'general'))
"
}

# ---------------------------------------------------------------------------
# Link one skill directory into every target. Never clobbers user data:
# existing real directories/files are skipped with a warning, and only
# symlinks owned by this registry are refreshed.
# ---------------------------------------------------------------------------
link_skill() {
    local name="$1"
    local category="$2"
    local src="$SKILLS_DIR/by-category/$category/$name"

    if [ ! -f "$src/SKILL.md" ]; then
        log_warn "not in registry (no SKILL.md): $name"
        return 0
    fi

    local target
    for target in "${TARGETS[@]}"; do
        mkdir -p "$target"
        local dst="$target/$name"
        if [ -e "$dst" ] || [ -L "$dst" ]; then
            if [ ! -L "$dst" ]; then
                log_warn "skip $target/$name: exists and is not a symlink (user-owned)"
                continue
            fi
            local current
            current="$(readlink "$dst" 2>/dev/null || true)"
            case "$current" in
                "$SKILLS_DIR"/*) ;;  # ours: refresh below
                *)
                    log_warn "skip $target/$name: symlink points outside the registry ($current)"
                    continue
                    ;;
            esac
        fi
        ln -sfn "$src" "$dst"
        [ "$QUIET" = "1" ] || log_info "linked $name -> $target/$name"
    done
    LINKED=$((LINKED + 1))
}

unlink_named() {
    local name="$1"
    local target
    for target in "${TARGETS[@]}"; do
        local dst="$target/$name"
        if [ -L "$dst" ]; then
            local current
            current="$(readlink "$dst" 2>/dev/null || true)"
            case "$current" in
                "$SKILLS_DIR"/*)
                    rm -f "$dst"
                    [ "$QUIET" = "1" ] || log_info "unlinked $target/$name"
                    ;;
                *) log_warn "keep $target/$name: not owned by this registry" ;;
            esac
        fi
    done
}

show_status() {
    local target
    for target in "${TARGETS[@]}"; do
        echo "Target: $target"
        if [ ! -d "$target" ]; then
            echo "  (does not exist yet)"
            continue
        fi
        local total=0 ours=0
        local entry
        # shellcheck disable=SC2045
        for entry in "$target"/*; do
            [ -e "$entry" ] || [ -L "$entry" ] || continue
            total=$((total + 1))
            if [ -L "$entry" ]; then
                local current
                current="$(readlink "$entry" 2>/dev/null || true)"
                case "$current" in
                    "$SKILLS_DIR"/*)
                        ours=$((ours + 1))
                        echo "  [ours] $(basename "$entry") -> $current"
                        ;;
                esac
            fi
        done
        echo "  entries: $total, managed by AgentEnhancements: $ours"
    done
}

usage() {
    sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
ACTION="link"
SKILL_FILTER=""
SET_SOURCES=""

while [ $# -gt 0 ]; do
    case "$1" in
        --set)
            [ $# -ge 2 ] || { log_error "--set requires a value"; exit 2; }
            if [ "$2" = "all" ]; then
                SET_SOURCES="*"
            else
                SET_SOURCES="$2"
            fi
            shift 2
            ;;
        --all)
            SET_SOURCES="*"
            shift
            ;;
        --status)
            ACTION="status"
            shift
            ;;
        --unlink)
            ACTION="unlink"
            shift
            ;;
        --quiet)
            QUIET=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --*)
            log_error "unknown option: $1"
            usage >&2
            exit 2
            ;;
        *)
            SKILL_FILTER="$SKILL_FILTER $1"
            shift
            ;;
    esac
done

# Resolve link targets (colon-separated override supported)
TARGETS=()
IFS=':' read -r -a RAW_TARGETS <<< "${AGENT_SKILLS_NATIVE_TARGETS:-$HOME/.claude/skills:$HOME/.agents/skills}"
for t in "${RAW_TARGETS[@]}"; do
    [ -n "$t" ] && TARGETS+=("$t")
done
if [ ${#TARGETS[@]} -eq 0 ]; then
    log_error "no link targets configured"
    exit 2
fi

if [ "$ACTION" = "status" ]; then
    show_status
    exit 0
fi

if [ ! -f "$SKILLS_DIR/all-skills.json" ]; then
    log_error "unified index not found at $SKILLS_DIR/all-skills.json - run setup.sh first"
    exit 1
fi

if [ "$ACTION" = "unlink" ]; then
    if [ -n "$SKILL_FILTER" ]; then
        for name in $SKILL_FILTER; do
            unlink_named "$name"
        done
    else
        # Unlink everything owned by this registry
        UNLINK_NAMES="$(resolve_skills all "")"
        while IFS=$'\t' read -r name _category; do
            [ -n "$name" ] || continue
            unlink_named "$name"
        done <<< "$UNLINK_NAMES"
    fi
    log_info "unlink complete (only registry-owned symlinks were removed)"
    exit 0
fi

# Action: link
LINKED=0
if [ -n "$SKILL_FILTER" ]; then
    RESOLVED="$(resolve_skills names "$SKILL_FILTER")"
    if [ -z "$RESOLVED" ]; then
        log_error "no skills matched:$SKILL_FILTER (check the name in all-skills.json)"
        exit 1
    fi
elif [ -n "$SET_SOURCES" ]; then
    if [ "$SET_SOURCES" = "*" ]; then
        RESOLVED="$(resolve_skills all "")"
    else
        RESOLVED="$(resolve_skills sources "$SET_SOURCES")"
    fi
else
    RESOLVED="$(resolve_skills sources "$DEFAULT_SOURCES")"
fi

if [ -z "$RESOLVED" ]; then
    log_error "no skills resolved - run setup.sh to (re)build the registry first"
    exit 1
fi

while IFS=$'\t' read -r name category; do
    [ -n "$name" ] || continue
    link_skill "$name" "$category"
done <<< "$RESOLVED"

log_info "done: $LINKED skill(s) linked into ${#TARGETS[@]} target directory(ies)"
if [ "$SET_SOURCES" = "*" ] || [ "$SET_SOURCES" = "all" ]; then
    log_warn "--all links the ENTIRE catalog: per-session skill metadata may be heavy for some harnesses"
fi
