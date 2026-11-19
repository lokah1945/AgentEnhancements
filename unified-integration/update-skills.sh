#!/bin/bash
# Update Skills from Source Repositories
# Pulls latest changes from all skill sources and re-runs aggregation

set -euo pipefail

# Allow BASE_DIR to be overridden via environment variable.
# Default: the repository root that contains this script.
SCRIPT_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-$(cd "$SCRIPT_SOURCE_DIR/.." && pwd)}"
UNIFIED_DIR="$BASE_DIR/unified-integration"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Update a git repository
update_repo() {
    local repo_dir="$1"
    local repo_name="$2"

    if [ ! -d "$repo_dir/.git" ]; then
        log_warn "$repo_name: Not a git repository (vendored copy), skipping"
        return 0
    fi

    log_info "Updating $repo_name..."

    # Run in a subshell so the working directory of this script is not changed
    (
        cd "$repo_dir"

        # Fetch latest changes
        if ! git fetch origin 2>/dev/null; then
            log_warn "$repo_name: Fetch failed (no remote or network issue)"
            exit 0
        fi

        # Compare against FETCH_HEAD: "origin/HEAD" is usually unset in
        # plain clones, which previously made every repo report
        # "Already up to date" even when updates existed.
        local behind
        behind=$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null || echo "0")
        if [ "$behind" -gt 0 ]; then
            log_info "$repo_name: $behind commits behind, pulling..."
            if git pull --ff-only origin HEAD 2>/dev/null; then
                log_success "$repo_name: Updated successfully"
            else
                log_error "$repo_name: Pull failed"
                exit 1
            fi
        else
            log_info "$repo_name: Already up to date"
        fi
    ) || return 1

    return 0
}

# Main update flow
main() {
    echo "========================================"
    echo "  Updating Skills from Sources"
    echo "========================================"
    echo ""

    # Update all skill sources. A failure in one source must not abort the
    # whole update, so each update is allowed to fail independently.
    update_repo "$BASE_DIR/agentic-awesome-skills" "agentic-awesome-skills" \
        || log_warn "agentic-awesome-skills: update failed, continuing"
    update_repo "$BASE_DIR/ECC" "ECC" \
        || log_warn "ECC: update failed, continuing"
    update_repo "$BASE_DIR/ponytail" "ponytail" \
        || log_warn "ponytail: update failed, continuing"
    update_repo "$BASE_DIR/superpowers" "superpowers" \
        || log_warn "superpowers: update failed, continuing"
    update_repo "$BASE_DIR/system-prompts-and-models-of-ai-tools" "system-prompts-and-models-of-ai-tools" \
        || log_warn "system-prompts-and-models-of-ai-tools: update failed, continuing"
    update_repo "$BASE_DIR/claude-mem" "claude-mem" \
        || log_warn "claude-mem: update failed, continuing"
    update_repo "$BASE_DIR/headroom" "headroom" \
        || log_warn "headroom: update failed, continuing"

    # replica-skill is vendored (not a git checkout). Update manually by
    # re-vendoring from https://github.com/Jakeschincariol/replica-skill
    # (remove .git after cloning, keep LICENSE).
    if [ -d "$BASE_DIR/replica-skill" ] && [ ! -d "$BASE_DIR/replica-skill/.git" ]; then
        log_warn "replica-skill: vendored copy (no .git) - update manually via re-vendor"
    fi

    # anthropic-skills is vendored (not a git checkout). Update manually by
    # re-vendoring from https://github.com/anthropics/skills (remove .git
    # after cloning; each skill carries its own Apache-2.0 LICENSE.txt).
    if [ -d "$BASE_DIR/anthropic-skills" ] && [ ! -d "$BASE_DIR/anthropic-skills/.git" ]; then
        log_warn "anthropic-skills: vendored copy (no .git) - update manually via re-vendor"
    fi

    # agency-agents is vendored (not a git checkout). Re-vendor from
    # https://github.com/msitarzewski/agency-agents, then re-run the
    # converter so agency-agents/skills/ matches the upstream personas:
    #   python3 scripts/convert_agency_agents.py && python3 scripts/gen_agency_catalog.py
    if [ -d "$BASE_DIR/agency-agents" ] && [ ! -d "$BASE_DIR/agency-agents/.git" ]; then
        log_warn "agency-agents: vendored copy (no .git) - update manually via re-vendor + re-convert"
    fi

    # task-observer is vendored (not a git checkout). Update deliberately:
    # never move silently to a new upstream HEAD. Pin, diff, review, then
    # re-vendor per docs/UPDATING.md; the pin and checksums live in
    # task-observer/VENDORED.json (upstream:
    # https://github.com/rebelytics/one-skill-to-rule-them-all, CC-BY-4.0).
    if [ -d "$BASE_DIR/task-observer" ] && [ ! -d "$BASE_DIR/task-observer/.git" ]; then
        log_warn "task-observer: vendored copy (no .git) - update manually via re-vendor (see task-observer/VENDORED.md); keep the pin and checksums in sync"
    fi

    # Re-run skills aggregation
    log_info "Re-aggregating skills..."
    # Draining setup through head terminated it with SIGPIPE after 20
    # matching log lines, then hid the failed/incomplete installation.
    if ! "$UNIFIED_DIR/setup.sh"; then
        log_error "Setup failed; the update is incomplete"
        return 1
    fi

    # Rebuild headroom if updated
    if [ -f "$BASE_DIR/headroom/Cargo.toml" ] && [ "${AGENT_ENHANCEMENTS_BUILD_HEADROOM:-0}" = "1" ]; then
        log_info "Rebuilding headroom..."
        (cd "$BASE_DIR/headroom" && cargo build --locked --release -p headroom-cli 2>&1 | tail -5) || log_warn "headroom: rebuild failed"
        if [ -f "$BASE_DIR/headroom/target/release/headroom" ]; then
            log_success "headroom rebuilt"
        fi
    fi

    # claude-mem is vendored without .git (like every source here), so a
    # post-update npm build can never apply; the dead branch was removed
    # (audit AE-20). If a future re-vendor ships build artifacts that need
    # refreshing, do it as part of the documented re-vendor procedure.

    echo ""
    echo "========================================"
    echo "  Update Complete!"
    echo "========================================"
    echo ""
    echo "Run the setup script again to apply changes:"
    echo "  $UNIFIED_DIR/setup.sh"
}

main "$@"
