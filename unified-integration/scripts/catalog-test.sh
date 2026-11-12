#!/usr/bin/env bash
# Smoke test one plugin from plugin-catalog: manifest validity, SKILL.md guide,
# frontmatter consistency, suggested MCP servers, registry wiring.
# Usage: bash catalog-test.sh <plugin-slug>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="$(cd "$UNIFIED_DIR/.." && pwd)"
CATALOG_DIR="$BASE_DIR/plugin-catalog"
REGISTRY_DIR="$UNIFIED_DIR/skills/by-category"

pass() { echo -e "\033[0;32m[PASS]\033[0m $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $*"; }
fail() { echo -e "\033[0;31m[FAIL]\033[0m $*"; }

slug="${1:-}"
if [ -z "$slug" ]; then
    echo "Usage: $0 <plugin-slug>"
    exit 2
fi

# Locate manifest across categories
manifest=""
category_found=""
for category in code research tokens-optimization design multimedia-writing; do
    candidate="$CATALOG_DIR/$category/$slug.json"
    if [ -f "$candidate" ]; then
        manifest="$candidate"
        category_found="$category"
        break
    fi
done

if [ -z "$manifest" ]; then
    fail "Manifest tidak ditemukan untuk slug: $slug"
    exit 1
fi

echo "=== Test plugin: $slug (category: $category_found) ==="

# 1. Manifest valid JSON + required fields
echo "1. Manifest validation..."
if jq -e . "$manifest" > /dev/null 2>&1; then
    pass "JSON valid: $manifest"
else
    fail "JSON invalid: $manifest"
    exit 1
fi

required_fields=(id name slug category version status description capabilities mcp_servers_suggested trigger_keywords)
for field in "${required_fields[@]}"; do
    if jq -e --arg f "$field" '.[$f] != null' "$manifest" > /dev/null; then
        pass "  field $field: OK"
    else
        fail "  field $field: MISSING"
        exit 1
    fi
done

# 2. SKILL.md guide exists
echo "2. SKILL.md guide..."
guide="$CATALOG_DIR/$category_found/$slug/SKILL.md"
if [ -f "$guide" ]; then
    size=$(wc -c < "$guide")
    if [ "$size" -gt 500 ]; then
        pass "SKILL.md ada ($size bytes)"
    else
        fail "SKILL.md terlalu pendek ($size bytes)"
        exit 1
    fi
else
    fail "SKILL.md hilang: $guide"
    exit 1
fi

# 3. Frontmatter consistency
echo "3. Frontmatter consistency..."
if head -10 "$guide" | grep -q "^slug: $slug"; then
    pass "slug match"
else
    warn "slug di frontmatter tidak match (cek manual)"
fi
if head -10 "$guide" | grep -q "^category: $category_found"; then
    pass "category match"
else
    warn "category di frontmatter tidak match"
fi

# 4. Suggested MCP servers
echo "4. MCP servers (suggested list)..."
mcp_count=$(jq '.mcp_servers_suggested | length' "$manifest")
if [ "$mcp_count" -gt 0 ]; then
    pass "$mcp_count MCP server disarankan:"
    jq -r '.mcp_servers_suggested[]' "$manifest" | sed 's/^/    - /'
else
    warn "tidak ada MCP server disarankan"
fi

# 5. Integration readiness
echo "5. Integration readiness..."
status=$(jq -r '.status' "$manifest")
if [ "$status" = "integrated-ready" ] || [ "$status" = "integrated" ]; then
    pass "status: $status (siap wiring)"
else
    warn "status: $status"
fi

# 6. Registry wiring
echo "6. Registry wiring (by-category)..."
link="$REGISTRY_DIR/$category_found/$slug"
if [ -L "$link" ] || [ -d "$link" ]; then
    pass "ter-wire di unified-integration/skills/by-category/"
else
    warn "belum ter-wire (jalankan catalog-wire.sh)"
fi

echo "=== Test selesai untuk $slug ==="
exit 0
