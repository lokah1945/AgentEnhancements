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

# Sources linked by default (context-frugal profile, CONTRACT.md §8.4):
# task-observer is ambient - its activation rides the lifecycle
# runtime, so the native link is what makes the bundle discoverable.
# Superpowers provides the core workflow discipline (using-superpowers,
# systematic-debugging, brainstorming, etc.) that makes the catalog
# usable - without it, agents don't know to check for skills first.
# Everything else in the 3.3k-skill catalog stays fully reachable
# through the on-demand discovery surface (lifecycle hook suggestions
# + registry.py search/map/show), so the default native metadata cost
# stays bounded while ensuring the process framework is present.
DEFAULT_SOURCES="task-observer Superpowers"

# Curated sets a user may request explicitly (--set curated):
# well-scoped sources with bounded per-session metadata cost (~3.5k
# tokens of native descriptions). The full catalog stays reachable on
# demand; "--set all" is audited, never default.
CURATED_SOURCES="anthropic-skills replica-skill task-observer"

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

# Audit an existing installation for the heavy-exposure patterns the
# context contract forbids as defaults (CONTRACT.md §8.4): a full-catalog
# link set from an older install (or a manual --set all), and links whose
# target no longer exists. Prints findings; fixes only apply with
# --migrate, and only ever touch registry-owned symlinks.
audit_install() {
    local migrate="$1"
    local findings=0
    local target
    for target in "${TARGETS[@]}"; do
        [ -d "$target" ] || continue
        local ours=0 stale=0 entry
        local stale_names=""
        for entry in "$target"/*; do
            [ -L "$entry" ] || continue
            local current
            current="$(readlink "$entry" 2>/dev/null || true)"
            case "$current" in
                "$SKILLS_DIR"/*)
                    ours=$((ours + 1))
                    if [ ! -e "$entry" ]; then
                        stale=$((stale + 1))
                        stale_names="$stale_names $(basename "$entry")"
                    fi
                    ;;
            esac
        done
        if [ "$ours" -gt 50 ]; then
            findings=$((findings + 1))
            log_warn "$target: $ours registry-owned links - full-catalog exposure"
            log_warn "  (native metadata for every linked skill enters each session;"
            log_warn "   the default profile links task-observer and Superpowers)."
            if [ "$migrate" = "yes" ]; then
                log_info "  migrating: unlinking all but the default set..."
                # Park each default-set link under a dot-prefixed name the
                # removal glob cannot see. A park failure (slot conflict,
                # mv error) LEAVES the link in place with a warning rather
                # than letting the removal loop unlink a default skill.
                local keep_line kname dst
                while IFS=$'\t' read -r kname _keepcat; do
                    [ -n "$kname" ] || continue
                    dst="$target/$kname"
                    if [ -L "$dst" ]; then
                        if [ -e "$target/.ae-keep-$kname" ] && [ ! -L "$target/.ae-keep-$kname" ]; then
                            log_warn "  keep slot conflict at .ae-keep-$kname; leaving $kname in place"
                            continue
                        fi
                        if ! mv "$dst" "$target/.ae-keep-$kname"; then
                            log_warn "  could not park $kname; leaving it in place"
                            continue
                        fi
                    fi
                done < <(resolve_skills sources "$DEFAULT_SOURCES")
                local entry2
                for entry2 in "$target"/*; do
                    [ -L "$entry2" ] || continue
                    local cur
                    cur="$(readlink "$entry2" 2>/dev/null || true)"
                    case "$cur" in
                        "$SKILLS_DIR"/*) rm -f "$entry2" ;;
                    esac
                done
                local keep2
                for keep2 in "$target"/.ae-keep-*; do
                    [ -e "$keep2" ] || [ -L "$keep2" ] || continue
                    local base
                    base="$(basename "$keep2")"
                    base="${base#.ae-keep-}"
                    if [ -e "$target/$base" ] || [ -L "$target/$base" ]; then
                        log_warn "  conflict restoring $base; kept at $keep2"
                        continue
                    fi
                    mv "$keep2" "$target/$base" || log_warn "  restore failed: $keep2"
                done
                log_info "  migrated: default set kept, others unlinked"
            else
                log_info "  run with --migrate to keep only the default set"
            fi
        fi
        if [ "$stale" -gt 0 ]; then
            findings=$((findings + 1))
            log_warn "$target: $stale stale link(s) (target missing):$stale_names"
            if [ "$migrate" = "yes" ]; then
                local sname
                for sname in $stale_names; do
                    rm -f "$target/$sname"
                done
                log_info "  stale links removed"
            fi
        fi
    done
    if [ "$findings" -eq 0 ]; then
        log_info "audit: no heavy-exposure or stale links found"
    fi
    return 0
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
            case "$2" in
                all)
                    SET_SOURCES="*"
                    ;;
                curated)
                    SET_SOURCES="$CURATED_SOURCES"
                    ;;
                *)
                    SET_SOURCES="$2"
                    ;;
            esac
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
        --audit)
            ACTION="audit"
            shift
            ;;
        --migrate)
            ACTION="migrate"
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

if [ "$ACTION" = "audit" ] || [ "$ACTION" = "migrate" ]; then
    audit_install "$([ "$ACTION" = "migrate" ] && echo yes || echo no)"
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
if [ "$SET_SOURCES" = "*" ]; then
    log_warn "--set all links the ENTIRE catalog (~130k tokens of native skill"
    log_warn "descriptions for some harnesses - the historical 200k cold-start"
    log_warn "report traces to this path). Prefer on-demand discovery:"
    log_warn "  registry.py search \"<task>\"   # bounded cards"
    log_warn "  link-skills.sh --set curated   # bounded native set"
fi
