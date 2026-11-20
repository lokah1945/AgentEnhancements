#!/usr/bin/env bash
# AgentEnhancements Unified Integration Setup
# Installs skills for Cursor, Claude Code, and other CLIs

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
CLAUDE_DIR="$HOME/.claude"
CURSOR_RULES_DIR="$HOME/.cursor/rules"

echo "🔧 AgentEnhancements Setup"
echo "Repo: $REPO_ROOT"
echo ""

# --- Helper: install skill as Claude Code skill ---
install_claude_skill() {
    local skill_slug="$1"
    local skill_path="$2"
    local target_dir="$CLAUDE_DIR/skills/$skill_slug"

    mkdir -p "$target_dir"
    cp "$skill_path" "$target_dir/SKILL.md"
    echo "  ✓ Installed $skill_slug → $target_dir"
}

# --- Helper: install skill as Cursor rule ---
install_cursor_rule() {
    local skill_slug="$1"
    local skill_path="$2"
    local rule_name="agent-enhancements-$skill_slug.mdc"
    local target_path="$CURSOR_RULES_DIR/$rule_name"

    mkdir -p "$CURSOR_RULES_DIR"
    # Convert SKILL.md to Cursor .mdc format
    cat > "$target_path" <<EOF
---
description: AgentEnhancements skill: $skill_slug
globs: ["**/*"]
alwaysApply: false
---
$(cat "$skill_path")
EOF
    echo "  ✓ Installed Cursor rule: $rule_name"
}

# --- Main installation ---
main() {
    echo "📦 Discovering skills..."
    mapfile -t skill_files < <(find "$SKILLS_DIR" -name "SKILL.md" -type f | sort)

    if [[ ${#skill_files[@]} -eq 0 ]]; then
        echo "⚠️  No skills found in $SKILLS_DIR"
        exit 1
    fi

    echo "Found ${#skill_files[@]} skills."
    echo ""

    # Install for Claude Code
    echo "🤖 Installing for Claude Code ($CLAUDE_DIR/skills)..."
    mkdir -p "$CLAUDE_DIR/skills"
    for skill_file in "${skill_files[@]}"; do
        # Extract slug from path: skills/<category>/<slug>/SKILL.md
        rel_path="${skill_file#$SKILLS_DIR/}"
        slug="${rel_path%/SKILL.md}"
        slug="${slug##*/}"  # get last component
        install_claude_skill "$slug" "$skill_file"
    done

    # Install for Cursor
    echo ""
    echo "📝 Installing for Cursor ($CURSOR_RULES_DIR)..."
    mkdir -p "$CURSOR_RULES_DIR"
    for skill_file in "${skill_files[@]}"; do
        rel_path="${skill_file#$SKILLS_DIR/}"
        slug="${rel_path%/SKILL.md}"
        slug="${slug##*/}"
        install_cursor_rule "$slug" "$skill_file"
    done

    # Create central Cursor rule (agent-enhancements.mdc)
    cat > "$CURSOR_RULES_DIR/agent-enhancements.mdc" <<'EOF'
---
description: AgentEnhancements — Centralized system prompt (Karpathy + Anthropic patterns)
globs: ["**/*"]
alwaysApply: true
---
# AgentEnhancements — Centralized System Prompt

This rule loads all AgentEnhancements skills. Individual skills are in `.cursor/rules/agent-enhancements-*.mdc`.

See `skills/**/SKILL.md` for full skill specifications.
EOF
    echo "  ✓ Created central rule: agent-enhancements.mdc"

    # Build catalog
    echo ""
    echo "📋 Building skill catalog..."
    python3 "$REPO_ROOT/unified-integration/scripts/registry.py" rebuild

    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "Next steps:"
    echo "  - Claude Code: skills auto-loaded from ~/.claude/skills/"
    echo "  - Cursor: rules active in ~/.cursor/rules/"
    echo "  - Discover skills: python3 unified-integration/scripts/registry.py map \"<task>\""
}

main "$@"