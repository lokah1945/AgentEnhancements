# Task 1 Report: Install Runtime Hooks for All Agents

**Status: DONE**

## Summary
Successfully modified `unified-integration/scripts/native-integration.py` to install runtime hooks for all three agents: claude-code, codex, and opencode.

## Changes Made
- **File**: `unified-integration/scripts/native-integration.py`
- **Lines modified**: Added hook installation for opencode in the `install()` function (around line 244)
- **Change**: Added `merge_hooks(doc, agent)` call in the opencode `if not mcp_only:` block

## Implementation Details
The `merge_hooks()` function was already being used for claude-code and codex. For opencode, the hook installation was missing. Added a single line to invoke `merge_hooks(doc, agent)` for opencode, which creates the proper hook structure with `runtime.py opencode` for all EVENTS (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop).

## Test Results
All verification tests pass:
```
PASS: claude-code hooks installed
PASS: codex hooks installed
PASS: opencode hooks installed
```

MCP gateway registration verified for all three agents:
- claude-code: ~/.claude.json ✅
- codex: ~/.codex/config.toml ✅
- opencode: ~/.config/opencode/opencode.jsonc ✅

## Commits Made
- `5ccdaef1` - feat(native): install runtime hooks for codex and opencode

## Concerns
None. The implementation follows the existing pattern used for claude-code and codex, ensuring consistency across all three agents.