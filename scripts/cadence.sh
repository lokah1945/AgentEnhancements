#!/usr/bin/env bash
# AgentEnhancements Ongoing Cadence Script
# Run weekly for task observer review, monthly for registry audit

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/../unified-integration" && pwd)"

log() { printf '[cadence] %s\n' "$*"; }
warn() { printf '[cadence] WARN: %s\n' "$*" >&2; }

# Resolve the observation workspace with task-observer.py's own resolver
# (TASK_OBSERVER_WORKSPACE, then AGENT_MEMORY_ROOT, then
# AGENT_ENHANCEMENTS_STATE_DIR/memory, then <repo>/.agentenhancements/memory)
# so the shell and Python defaults can never drift apart.
resolve_workspace() {
    python3 - "$UNIFIED_DIR/scripts" <<'PY'
import importlib.util
import sys

scripts = sys.argv[1]
sys.path.insert(0, scripts)
spec = importlib.util.spec_from_file_location("task_observer", f"{scripts}/task-observer.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(module.workspace_root())
PY
}

# Weekly: Task Observer Review
review_observer() {
    log "Running weekly task observer review..."

    local WORKSPACE
    if ! WORKSPACE="$(resolve_workspace)"; then
        warn "Could not resolve the task observer workspace"
        return 1
    fi

    if [ ! -d "$WORKSPACE" ]; then
        warn "Task observer workspace not found at $WORKSPACE"
        return 1
    fi
    
    python3 "$UNIFIED_DIR/scripts/task-observer.py" status --workspace "$WORKSPACE"
    
    # List open observations
    open_count=$(python3 "$UNIFIED_DIR/scripts/task-observer.py" status --workspace "$WORKSPACE" 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('open_observations', 0))")
    
    if [ "$open_count" -gt 0 ]; then
        log "Found $open_count open observations - review recommended"
        python3 "$UNIFIED_DIR/scripts/task-observer.py" review --workspace "$WORKSPACE"
    else
        log "No open observations"
    fi
    
    log "Task observer review complete"
}

# Monthly: Registry Audit
audit_registry() {
    log "Running monthly registry audit..."
    
    # Build registry
    log "Building capability registry..."
    python3 "$UNIFIED_DIR/scripts/registry.py" build

    # Regenerate library map. Must run AFTER registry.py build: the map reads
    # its family counts from agent-registry.json (as in registry-regeneration.yml).
    log "Regenerating library map..."
    python3 "$UNIFIED_DIR/scripts/build-library-map.py"
    
    # Validate catalog
    log "Validating plugin catalog..."
    python3 "$UNIFIED_DIR/scripts/catalog-validate.py"
    
    # Check for drift
    log "Checking for registry drift..."
    if ! git -C "$UNIFIED_DIR/.." diff --exit-code -- skills/library-map.json unified-integration/skills/agent-registry.json unified-integration/skills/all-skills.json 2>/dev/null; then
        warn "Registry files have drifted from committed versions"
        git -C "$UNIFIED_DIR/.." diff -- skills/library-map.json unified-integration/skills/agent-registry.json unified-integration/skills/all-skills.json
        return 1
    fi
    
    # Run doctor
    log "Running doctor check..."
    python3 "$UNIFIED_DIR/scripts/doctor.py"
    
    log "Registry audit complete"
}

# Main
case "${1:-help}" in
    weekly|observer)
        review_observer
        ;;
    monthly|registry)
        audit_registry
        ;;
    all)
        review_observer
        echo "---"
        audit_registry
        ;;
    help|*)
        echo "Usage: $0 {weekly|monthly|all}"
        echo "  weekly   - Run task observer review (weekly cadence)"
        echo "  monthly  - Run registry audit (monthly cadence)"
        echo "  all      - Run both"
        exit 1
        ;;
esac