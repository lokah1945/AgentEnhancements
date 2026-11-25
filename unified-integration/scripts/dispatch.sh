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

# Priority order for overlapping clean-code skills (lower number = higher priority)
# Per Karpathy SKILL.md: "Ponytail, Superpowers, and ECC clean-code membahas domain yang beririsan.
# Ikuti aturan prioritas proyek; gunakan satu suara, bukan replikasi prinsip yang sama di banyak tempat."
declare -A SKILL_PRIORITY=(
    [karpathy-skills]=10   # General coding principles (highest for coding tasks)
    [superpowers]=20       # Workflow discipline
    [ecc]=30               # Agent config generation
    [ponytail]=40          # Linting/code quality
)

# Check if a skill is in the clean-code priority group
is_clean_code_skill() {
    case "$1" in
        karpathy-skills|superpowers|ecc|ponytail) return 0 ;;
        *) return 1 ;;
    esac
}

# Get priority for a skill (lower = higher priority)
get_skill_priority() {
    local skill="$1"
    echo "${SKILL_PRIORITY[$skill]:-999}"
}

# Classify intent by keyword heuristics (see docs/ROUTER_POLICY.md)
# Returns all matching skills, not just the first one
classify_all() {
    local lc
    lc=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    local matches=()

    # Orchestrator tier first (highest precedence, no overlap)
    if echo "$lc" | grep -qE '(build product|greenfield|from scratch|bangun .* dari nol)'; then matches+=("bmad-method"); fi
    if echo "$lc" | grep -qE '(kerjakan semua|do all|selesaikan|clear backlog)'; then matches+=("gsd"); fi
    if echo "$lc" | grep -qE '(reverse engineer|reksayasa balik|decompil|disassembl|binary analysis|analisis binary|apk analysis|inspect (the )?(binary|executable|apk))'; then matches+=("rea"); fi

    # Anthropic official technical skills
    if echo "$lc" | grep -qE '(mcp server|build .*mcp|model context protocol)'; then matches+=("mcp-builder"); fi
    if echo "$lc" | grep -qE '(create .*skill|new skill|buat skill|improve .*skill|skill eval|edit .*skill|skill creator)'; then matches+=("skill-creator"); fi
    if echo "$lc" | grep -qE '(test .*web.?app|webapp test|playwright|e2e .*web|browser screenshot)'; then matches+=("webapp-testing"); fi
    if echo "$lc" | grep -qE '(claude api|anthropic api|claude sdk)'; then matches+=("claude-api"); fi

    # Anthropic official document skills
    if echo "$lc" | grep -qE '(\.docx|\.dotx|word doc|word document|dokumen word|surat .*word)'; then matches+=("docx"); fi
    if echo "$lc" | grep -qE '(\.pdf|pdf)'; then matches+=("pdf"); fi
    if echo "$lc" | grep -qE '(\.pptx|\.potx|powerpoint)'; then matches+=("pptx"); fi
    if echo "$lc" | grep -qE '(\.xlsx|\.xlsm|\.xltx|\.csv|\.tsv|excel|spreadsheet)'; then matches+=("xlsx"); fi

    # Plugin tier
    if echo "$lc" | grep -qE '(clone app|clone aplikasi|clone .* app|klon|replica|rebuild app|build my own version|versi sendiri)'; then matches+=("replica-skill"); fi
    if echo "$lc" | grep -qE '(typescript|refactor ts|zod|\bgenerics?\b)'; then matches+=("mattpocock-skills"); fi
    if echo "$lc" | grep -qE '(prototype|sketch|numpy|torch|first principle)'; then matches+=("karpathy-skills"); fi
    if echo "$lc" | grep -qE '\b(fix|bug|refactor|review|debug|implement|simplif(y|ication)?|clean.code|over.engineer)\b'; then matches+=("karpathy-skills"); fi
    if echo "$lc" | grep -qE '(\bperf\b|performance|lighthouse|core web vitals|a11y|accessibility)'; then matches+=("agent-skills-addyosmani"); fi
    if echo "$lc" | grep -qE '(knowledge graph|entity relation|graphify)'; then matches+=("graphify"); fi
    if echo "$lc" | grep -qE '(deep research|literature|citation)'; then matches+=("agent-reach"); fi
    if echo "$lc" | grep -qE '(explain|understand|jelaskan|apa itu|feynman|investigate|telusuri|cari tahu kenapa)'; then matches+=("understand-anything"); fi
    if echo "$lc" | grep -qE '(recent|last 30 days|update terbaru|trend)'; then matches+=("last-30-days"); fi
    if echo "$lc" | grep -qE '(token budget|compress prompt|too long)'; then matches+=("gstack"); fi
    if echo "$lc" | grep -qE '(caveman|minimize prompt|shorthand)'; then matches+=("caveman"); fi
    if echo "$lc" | grep -qE '(design system|design tokens|spec ui)'; then matches+=("ui-ux-pro-max"); fi
    if echo "$lc" | grep -qE '(polish|impeccable|alignment|kontras)'; then matches+=("impeccable"); fi
    if echo "$lc" | grep -qE '(slide|\bdecks?\b|presentation|\bppt\b|keynote)'; then matches+=("ppt-master"); fi
    if echo "$lc" | grep -qE '(diagram|flowchart|mermaid|\bd2\b|\berds?\b|sequence diagram)'; then matches+=("diagram-design"); fi
    if echo "$lc" | grep -qE '(anthropic skill|official skill|structured output|document qa|multimodal)'; then matches+=("anthropic-skills"); fi
    if echo "$lc" | grep -qE '(video|montage|edit video|reels|shorts|ffmpeg)'; then matches+=("openmontage"); fi
    if echo "$lc" | grep -qE '(avatar|talking head|personalized video|voice clone|lip.?sync)'; then matches+=("hyperframes"); fi
    if echo "$lc" | grep -qE '(humanize|ai-ism|terlalu ai|terlalu kaku)'; then matches+=("humanizer"); fi

    # Agency division packs
    if echo "$lc" | grep -qE '(nexus|multi-agent pipeline|orchestrat|orkestrasi)'; then matches+=("nexus"); fi
    if echo "$lc" | grep -qE '(threat model|pentest|penetration|incident response|siem|appsec|dfir)'; then matches+=("security"); fi
    if echo "$lc" | grep -qE '(playwright|cypress|e2e test|performance test|load test|accessibility audit)'; then matches+=("testing"); fi
    if echo "$lc" | grep -qE '(frontend|backend architect|devops|\bsre\b|code review|database optim)'; then matches+=("engineering"); fi
    if echo "$lc" | grep -qE '(\bppc\b|google ads|paid social|ad campaign|conversion tracking)'; then matches+=("paid-media"); fi
    if echo "$lc" | grep -qE '(growth hack|content calendar|seo audit|social media strategy|tiktok|xiaohongshu)'; then matches+=("marketing"); fi
    if echo "$lc" | grep -qE '(\bprds?\b|sprint priorit|product roadmap|user feedback)'; then matches+=("product"); fi
    if echo "$lc" | grep -qE '(discovery call|meddpicc|outbound|sales pipeline|\brfps?\b)'; then matches+=("sales"); fi
    if echo "$lc" | grep -qE '(ui design|ux research|brand identity|design system)'; then matches+=("design"); fi
    if echo "$lc" | grep -qE '(\bgis\b|arcgis|maplibre|spatial data|geospasial)'; then matches+=("gis"); fi
    if echo "$lc" | grep -qE '(\bunity|unreal|godot|roblox|game design|game economy)'; then matches+=("game-development"); fi
    if echo "$lc" | grep -qE '(visionos|webxr|spatial computing|vision pro)'; then matches+=("spatial-computing"); fi

    # Deduplicate matches
    printf '%s\n' "${matches[@]}" | sort -u
}

# Resolve to single best skill using priority rules
resolve_skill() {
    local prompt="$1"
    local matches
    mapfile -t matches < <(classify_all "$prompt")

    # Handle bash mapfile quirk: empty output may produce one empty element
    if [ ${#matches[@]} -eq 0 ] || { [ ${#matches[@]} -eq 1 ] && [ -z "${matches[0]}" ]; }; then
        echo "none"
        return
    fi

    # Single match - return it
    if [ ${#matches[@]} -eq 1 ]; then
        echo "${matches[0]}"
        return
    fi

    # Multiple matches - apply priority rules
    # Orchestrator tier always wins (bmad-method, gsd, rea)
    for m in "${matches[@]}"; do
        case "$m" in
            bmad-method|gsd|rea) echo "$m"; return ;;
        esac
    done

    # Anthropic technical skills win over plugin tier
    for m in "${matches[@]}"; do
        case "$m" in
            mcp-builder|skill-creator|webapp-testing|claude-api) echo "$m"; return ;;
        esac
    done

    # Document format skills win
    for m in "${matches[@]}"; do
        case "$m" in
            docx|pdf|pptx|xlsx) echo "$m"; return ;;
        esac
    done

    # Clean-code skills: apply priority
    local clean_code_matches=()
    for m in "${matches[@]}"; do
        if is_clean_code_skill "$m"; then
            clean_code_matches+=("$m")
        fi
    done

    if [ ${#clean_code_matches[@]} -gt 0 ]; then
        # Select highest priority (lowest number)
        local best="${clean_code_matches[0]}"
        local best_prio=$(get_skill_priority "$best")
        for m in "${clean_code_matches[@]}"; do
            local prio=$(get_skill_priority "$m")
            if [ "$prio" -lt "$best_prio" ]; then
                best="$m"
                best_prio="$prio"
            fi
        done
        echo "$best"
        return
    fi

    # For other multiple matches, prefer the first one (original order)
    echo "${matches[0]}"
}

# Backward compatibility: classify returns single best skill
classify() {
    resolve_skill "$1"
}

find_guide() {
    local slug="$1"
    local category
    for category in code research tokens-optimization design multimedia-writing agency; do
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

# Honest abstain: no catalog skill matched, ordinary agent tools suffice.
if [ "$skill" = "none" ]; then
    echo "=== Dispatch Plan ==="
    echo "User prompt : $prompt"
    echo "Skill match : none (no catalog skill fits; use ordinary tools)"
    echo "======================"
    log_info "Tidak ada skill katalog yang cocok - lanjutkan dengan ordinary tools"
    exit 0
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
