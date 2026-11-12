#!/bin/bash
# Update Skills from Source Repositories
# Pulls latest changes from all skill sources and re-runs aggregation

set -euo pipefail

BASE_DIR="${AGENT_ENHANCEMENTS_BASE_DIR:-/root/agent-enhancements}"
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
        log_warn "$repo_name: Not a git repository, skipping"
        return
    fi

    log_info "Updating $repo_name..."
    cd "$repo_dir"

    # Fetch latest changes
    if git fetch origin 2>/dev/null; then
        # Check if there are updates
        local behind=$(git rev-list --count HEAD..origin/HEAD 2>/dev/null || echo "0")
        if [ "$behind" -gt 0 ]; then
            log_info "$repo_name: $behind commits behind, pulling..."
            if git pull origin HEAD 2>/dev/null; then
                log_success "$repo_name: Updated successfully"
                return 0
            else
                log_error "$repo_name: Pull failed"
                return 1
            fi
        else
            log_info "$repo_name: Already up to date"
            return 0
        fi
    else
        log_warn "$repo_name: Fetch failed (no remote or network issue)"
        return 1
    fi
}

# Main update flow
main() {
    echo "========================================"
    echo "  Updating Skills from Sources"
    echo "========================================"
    echo ""

    # Update all skill sources
    update_repo "$BASE_DIR/agentic-awesome-skills" "agentic-awesome-skills"
    update_repo "$BASE_DIR/ECC" "ECC"
    update_repo "$BASE_DIR/ponytail" "ponytail"
    update_repo "$BASE_DIR/superpowers" "superpowers"
    update_repo "$BASE_DIR/system-prompts-and-models-of-ai-tools" "system-prompts-and-models-of-ai-tools"
    update_repo "$BASE_DIR/claude-mem" "claude-mem"
    update_repo "$BASE_DIR/headroom" "headroom"

    # replica-skill is vendored (not a git checkout). Update manually by
    # re-vendoring from https://github.com/Jakeschincariol/replica-skill
    # (remove .git after cloning, keep LICENSE).
    if [ -d "$BASE_DIR/replica-skill" ] && [ ! -d "$BASE_DIR/replica-skill/.git" ]; then
        log_warn "replica-skill: vendored copy (no .git) - update manually via re-vendor"
    fi

    # Re-run skills aggregation
    log_info "Re-aggregating skills..."
    "$UNIFIED_DIR/setup.sh" 2>&1 | grep -E "Aggregate|process|complete|skill" | head -20

    # Rebuild headroom if updated
    if [ -f "$BASE_DIR/headroom/Cargo.toml" ]; then
        log_info "Rebuilding headroom..."
        cd "$BASE_DIR/headroom" && cargo build --release 2>&1 | tail -5
        if [ -f "$BASE_DIR/headroom/target/release/headroom" ]; then
            log_success "headroom rebuilt"
        fi
    fi

    # Rebuild claude-mem if updated
    if [ -f "$BASE_DIR/claude-mem/package.json" ]; then
        log_info "Rebuilding claude-mem..."
        cd "$BASE_DIR/claude-mem" && npm run build 2>&1 | tail -5
        log_success "claude-mem rebuilt"
    fi

    echo ""
    echo "========================================"
    echo "  Update Complete!"
    echo "========================================"
    echo ""
    echo "Run the setup script again to apply changes:"
    echo "  $UNIFIED_DIR/setup.sh"
}

main "$@"