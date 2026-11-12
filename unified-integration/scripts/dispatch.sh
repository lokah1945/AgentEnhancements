#!/usr/bin/env bash
# Orchestrator dispatcher: pick a catalog plugin (or orchestrator tier) from a
# natural-language prompt, per docs/ROUTER_POLICY.md.
# Resolves catalog plugin guides AND vendored anthropic-skills (docx, pdf,
# pptx, xlsx, mcp-builder, skill-creator, webapp-testing, claude-api).
# Usage:
#   bash dispatch.sh "<user_prompt>"
#   bash dispatch.sh --dry-run "<user_prompt>"   # print plan only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIFIED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="$(cd "$UNIFIED_DIR/.." && pwd)"
CATALOG_DIR="$BASE_DIR/plugin-catalog"

log_info()  { echo -e "\033[0;34m[dispatch]\033[0m $1"; }

# Classify intent by keyword heuristics (see docs/ROUTER_POLICY.md)
classify() {
    local lc
    lc=$(echo "$1" | tr '[:upper:]' '[:lower:]')

    # Orchestrator tier first
    if echo "$lc" | grep -qE '(build product|greenfield|from scratch|bangun .* dari nol)'; then echo "bmad-method"; return; fi
    if echo "$lc" | grep -qE '(kerjakan semua|do all|selesaikan|clear backlog)'; then echo "gsd"; return; fi
    if echo "$lc" | grep -qE '(investigate|telusuri|cari tahu kenapa)'; then echo "rea"; return; fi

    # Anthropic official technical skills (vendored + natively linked)
    if echo "$lc" | grep -qE '(mcp server|build .*mcp|model context protocol)'; then echo "mcp-builder"; return; fi
    if echo "$lc" | grep -qE '(create .*skill|new skill|buat skill|improve .*skill|skill eval|edit .*skill|skill creator)'; then echo "skill-creator"; return; fi
    if echo "$lc" | grep -qE '(test .*web.?app|webapp test|playwright|e2e .*web|browser screenshot)'; then echo "webapp-testing"; return; fi
    if echo "$lc" | grep -qE '(claude api|anthropic api|claude sdk)'; then echo "claude-api"; return; fi

    # Anthropic official document skills: file-format intents are the most
    # specific signals, so they precede the generic plugin tier.
    if echo "$lc" | grep -qE '(\.docx|\.dotx|word doc|word document|dokumen word|surat .*word)'; then echo "docx"; return; fi
    if echo "$lc" | grep -qE '(\.pdf|pdf)'; then echo "pdf"; return; fi
    if echo "$lc" | grep -qE '(\.pptx|\.potx|powerpoint)'; then echo "pptx"; return; fi
    if echo "$lc" | grep -qE '(\.xlsx|\.xlsm|\.xltx|\.csv|\.tsv|excel|spreadsheet)'; then echo "xlsx"; return; fi

    # Plugin tier
    if echo "$lc" | grep -qE '(clone app|clone aplikasi|clone .* app|klon|replica|reverse engineer|rebuild app|build my own version|versi sendiri)'; then echo "replica-skill"; return; fi
    if echo "$lc" | grep -qE '(typescript|refactor ts|zod|generic)'; then echo "mattpocock-skills"; return; fi
    if echo "$lc" | grep -qE '(prototype|sketch|numpy|torch|first principle)'; then echo "karpathy-skills"; return; fi
    if echo "$lc" | grep -qE '(\bperf\b|performance|lighthouse|core web vitals|a11y|accessibility)'; then echo "agent-skills-addyosmani"; return; fi
    if echo "$lc" | grep -qE '(knowledge graph|entity relation|graphify)'; then echo "graphify"; return; fi
    if echo "$lc" | grep -qE '(deep research|literature|citation)'; then echo "agent-reach"; return; fi
    if echo "$lc" | grep -qE '(explain|understand|jelaskan|apa itu|feynman)'; then echo "understand-anything"; return; fi
    if echo "$lc" | grep -qE '(recent|last 30 days|update terbaru|trend)'; then echo "last-30-days"; return; fi
    if echo "$lc" | grep -qE '(token budget|compress prompt|too long)'; then echo "gstack"; return; fi
    if echo "$lc" | grep -qE '(caveman|minimize prompt|shorthand)'; then echo "caveman"; return; fi
    if echo "$lc" | grep -qE '(design system|design tokens|spec ui)'; then echo "ui-ux-pro-max"; return; fi
    if echo "$lc" | grep -qE '(polish|impeccable|alignment|kontras)'; then echo "impeccable"; return; fi
    if echo "$lc" | grep -qE '(slide|deck|presentation|ppt|keynote)'; then echo "ppt-master"; return; fi
    if echo "$lc" | grep -qE '(diagram|flowchart|mermaid|d2|erd|sequence)'; then echo "diagram-design"; return; fi
    if echo "$lc" | grep -qE '(anthropic skill|official skill|structured output|document qa|multimodal)'; then echo "anthropic-skills"; return; fi
    if echo "$lc" | grep -qE '(video|montage|edit video|reels|shorts|ffmpeg)'; then echo "openmontage"; return; fi
    if echo "$lc" | grep -qE '(avatar|talking head|personalized video|voice clone|lip.?sync)'; then echo "hyperframes"; return; fi
    if echo "$lc" | grep -qE '(humanize|ai-ism|terlalu ai|terlalu kaku)'; then echo "humanizer"; return; fi

    # Fallback default
    echo "rea"
}

find_guide() {
    local slug="$1"
    local category
    for category in code research tokens-optimization design multimedia-writing; do
        local candidate="$CATALOG_DIR/$category/$slug/SKILL.md"
        if [ -f "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    # Vendored Anthropic official skills (aggregated + natively linked at
    # install time; the vendor copy is the pristine reference).
    local vendor_candidate="$BASE_DIR/anthropic-skills/skills/$slug/SKILL.md"
    if [ -f "$vendor_candidate" ]; then
        echo "$vendor_candidate"
        return 0
    fi
    return 1
}

dry_run=0
if [ "${1:-}" = "--dry-run" ]; then
    dry_run=1
    shift
fi

prompt="${1:-}"
if [ -z "$prompt" ]; then
    echo "Usage: $0 [--dry-run] \"<user_prompt>\""
    exit 2
fi

# Explicit override: "[skill:slug]" prefix skips heuristics
skill=""
if echo "$prompt" | grep -qE '^\[skill:[a-z0-9-]+\]'; then
    skill=$(echo "$prompt" | sed -E 's/^\[skill:([a-z0-9-]+)\].*/\1/')
fi
if [ -z "$skill" ]; then
    skill=$(classify "$prompt")
fi

guide=$(find_guide "$skill") || {
    log_info "Tidak menemukan SKILL.md untuk: $skill"
    exit 1
}

echo "=== Dispatch Plan ==="
echo "User prompt : $prompt"
echo "Skill match : $skill"
echo "Guide       : $guide"
echo "======================"

if [ "$dry_run" = "1" ]; then
    log_info "dry-run: tidak eksekusi - hanya rencana"
    exit 0
fi

log_info "Membaca panduan SKILL.md..."
echo "(Di production, ini akan invoke agent runtime dengan prompt + skill context)"
exit 0
