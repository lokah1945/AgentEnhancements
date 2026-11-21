#!/usr/bin/env bash
QUIET=0
# Auto-detect project root from script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
UNIFIED_DIR="$BASE_DIR/unified-integration"
SKILLS_DIR="$UNIFIED_DIR/skills"
# Use environment variables for user config dirs, fallback to defaults
CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
AGENTS_CONFIG_DIR="${AGENTS_CONFIG_DIR:-$HOME/.agents}"
CODEX_CONFIG_DIR="${CODEX_CONFIG_DIR:-$HOME/.codex}"
OPENCODE_CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
TARGETS=("$CLAUDE_CONFIG_DIR/skills" "$AGENTS_CONFIG_DIR/skills" "$CODEX_CONFIG_DIR/skills" "$OPENCODE_CONFIG_DIR/skills")

link_skill() {
    local name="$1"
    local category="$2"
    local src="$SKILLS_DIR/by-category/$category/$name"

    if [ ! -f "$src/SKILL.md" ]; then
        echo "[WARN] not in registry (no SKILL.md): $name"
        return 0
    fi

    local target
    for target in "${TARGETS[@]}"; do
        mkdir -p "$target"
        local dst="$target/$name"
        if [ -e "$dst" ] || [ -L "$dst" ]; then
            if [ ! -L "$dst" ]; then
                echo "[WARN] skip $target/$name: exists and is not a symlink (user-owned)"
                continue
            fi
            local current
            current="$(readlink "$dst" 2>/dev/null || true)"
            case "$current" in
                "$SKILLS_DIR"/*) ;;
                *)
                    echo "[WARN] skip $target/$name: symlink points outside the registry ($current)"
                    continue
                    ;;
            esac
        fi
        ln -sfn "$src" "$dst"
        echo "[INFO] linked $name -> $target/$name"
    done
}

cat /tmp/superpowers_skills.txt | tr -d "\r" | while IFS=$'\t' read -r name category; do
    echo "Processing: $name ($category)"
    link_skill "$name" "$category"
done