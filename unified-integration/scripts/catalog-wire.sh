#!/usr/bin/env bash
# Wire plugin-catalog integration guides into the unified skills registry.
# Creates symlinks under unified-integration/skills/by-category/<category>/<slug>
# so catalog plugins are visible alongside aggregated skills.
# NOTE: this script does NOT modify all-skills.json - the unified index is
# regenerated exclusively by the aggregation pipeline in setup.sh (CONTRACT R304).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="$(cd "$UNIFIED_DIR/.." && pwd)"
CATALOG_DIR="$BASE_DIR/plugin-catalog"
REGISTRY_DIR="$UNIFIED_DIR/skills/by-category"

log_info()  { echo -e "\033[0;34m[wire]\033[0m $1"; }
log_success() { echo -e "\033[0;32m[wire]\033[0m $1"; }
log_warn()  { echo -e "\033[1;33m[wire]\033[0m $1"; }

wire_catalog() {
    if [ ! -d "$CATALOG_DIR" ]; then
        log_warn "plugin-catalog/ tidak ditemukan: $CATALOG_DIR"
        exit 1
    fi

    log_info "Wiring plugin-catalog ke $REGISTRY_DIR ..."
    local categories=(code research tokens-optimization design multimedia-writing)
    local count=0

    for category in "${categories[@]}"; do
        local category_dir="$CATALOG_DIR/$category"
        [ -d "$category_dir" ] || continue
        mkdir -p "$REGISTRY_DIR/$category"
        for plugin_dir in "$category_dir"/*/; do
            [ -d "$plugin_dir" ] || continue
            local slug
            slug="$(basename "$plugin_dir")"
            local target="$REGISTRY_DIR/$category/$slug"
            if [ -e "$target" ] || [ -L "$target" ]; then
                if [ -L "$target" ]; then
                    # Refresh an existing catalog symlink
                    rm -f "$target"
                elif [ -d "$target" ]; then
                    # Real directory: belongs to the aggregation pipeline.
                    # Never delete aggregated skills - skip with a warning.
                    log_warn "skip: $category/$slug sudah ada sebagai direktori hasil agregasi (bukan symlink)"
                    continue
                else
                    log_warn "skip: $category/$slug adalah file biasa, tidak ditimpa"
                    continue
                fi
            fi
            ln -s "$plugin_dir" "$target"
            count=$((count + 1))
            log_success "linked: $category/$slug"
        done
    done

    log_info "Selesai: $count plugin guide ter-wire ke registry."
}

wire_catalog
