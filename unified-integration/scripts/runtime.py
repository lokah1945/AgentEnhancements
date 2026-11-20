#!/usr/bin/env python3
"""
AgentEnhancements Hook Runtime — Core lifecycle hook handlers for all supported agents.
Provides SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop handlers.
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory import MemoryManager
from registry import SkillRegistry
from adaptive_preflight import AdaptivePreflight


@dataclass
class HookContext:
    """Context passed to all hook handlers."""
    session_id: str
    agent_type: str  # claude-code, codex, opencode, hermes, cursor, gemini, copilot, windsurf, kiro
    project_root: str
    user_id: str
    timestamp: float
    metadata: Dict[str, Any]


@dataclass
class SkillCard:
    """A skill recommendation card for injection."""
    slug: str
    category: str
    version: str
    trigger_keywords: List[str]
    mcp_servers: List[str]
    path: str
    relevance_score: float
    reason: str


class HookRuntime:
    """
    Central hook runtime managing all lifecycle events.
    Integrates with memory, registry, adaptive preflight, and compression.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.base_dir = Path(self.config.get("base_dir", Path(__file__).parent.parent))
        self.agent_type = self.config.get("agent_type", "claude-code")
        self.session_id = self.config.get("session_id", str(uuid.uuid4())[:8])
        self.user_id = self.config.get("user_id", os.getenv("USER", "unknown"))

        # Initialize subsystems
        self.memory = MemoryManager(self.base_dir / ".agentenhancements" / "memory")
        self.registry = SkillRegistry(self.base_dir)
        self.preflight = AdaptivePreflight(self.base_dir, self.registry)

        # Session state
        self._tool_calls: List[Dict] = []
        self._session_start_time = time.time()
        self._skills_injected_this_turn = False

    def _create_context(self, extra: Optional[Dict] = None) -> HookContext:
        ctx = HookContext(
            session_id=self.session_id,
            agent_type=self.agent_type,
            project_root=str(self.base_dir),
            user_id=self.user_id,
            timestamp=time.time(),
            metadata=extra or {}
        )
        return ctx

    # =========================================================================
    # SESSION START
    # =========================================================================
    def on_session_start(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle SessionStart event.
        - Bootstrap Task Observer
        - Recall session memory (7-day TTL)
        - Initialize compression budget
        """
        ctx = self._create_context({"event": "SessionStart"})

        # Recall relevant memories
        memories = self.memory.recall_session(self.session_id, max_age_days=7)

        # Load task observer state if exists
        observer_state = self.memory.load("task_observer", "state", default={})

        # Prepare injection for first prompt
        injection = {
            "type": "session_start",
            "session_id": self.session_id,
            "recalled_memories": memories[:10],  # Limit to 10 most relevant
            "observer_state": observer_state,
            "compression_budget": self.config.get("compression_budget", 200000),
            "compression_trigger": self.config.get("compression_trigger", 0.75),
            "ae_version": "1.0.0",
        }

        # Save session start marker
        self.memory.save("start", {
            "timestamp": ctx.timestamp,
            "agent_type": self.agent_type,
            "project_root": str(self.base_dir),
        }, memory_type="session_context", session_id=self.session_id)

        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": json.dumps(injection)
            }
        }

    # =========================================================================
    # USER PROMPT SUBMIT - Core capability selection
    # =========================================================================
    def on_user_prompt_submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle UserPromptSubmit event.
        - Extract task intent from user prompt
        - Run adaptive preflight (Mode 0/1/2)
        - Select and validate capabilities
        - Inject bounded skill package (<=400 tokens)
        """
        ctx = self._create_context({"event": "UserPromptSubmit"})

        user_prompt = payload.get("prompt", "")
        if not user_prompt:
            return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}

        # Save prompt to memory
        self.memory.save(str(ctx.timestamp), {
            "prompt": user_prompt[:500],
            "timestamp": ctx.timestamp,
        }, memory_type="session_context", session_id=self.session_id)

        # Run adaptive preflight to get capability package
        preflight_result = self.preflight.run(
            task_description=user_prompt,
            agent_type=self.agent_type,
            session_id=self.session_id,
            context={
                "recent_tools": self._tool_calls[-20:],  # Last 20 tool calls
                "session_duration": time.time() - self._session_start_time,
            }
        )

        # Build injection package
        injection = {
            "type": "capability_package",
            "session_id": self.session_id,
            "mode": preflight_result.mode.value if hasattr(preflight_result.mode, 'value') else preflight_result.mode,
            "selected_skills": [asdict(s) for s in preflight_result.skills],
            "selected_plugins": [asdict(s) for s in preflight_result.plugins],
            "selected_mcp_servers": [asdict(s) for s in preflight_result.mcp_servers],
            "selected_builtins": [asdict(s) for s in preflight_result.builtins],
            "lookup_results": preflight_result.lookups,
            "warnings": preflight_result.warnings,
            "token_estimate": preflight_result.token_estimate,
            "fallback_used": preflight_result.fallback_used,
        }

        # Save selection for continuity
        self.memory.save(str(ctx.timestamp), injection, memory_type="session_context", session_id=self.session_id)

        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": json.dumps(injection)
            }
        }

    # =========================================================================
    # PRE TOOL USE - Record tool invocation
    # =========================================================================
    def on_pre_tool_use(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PreToolUse event - record tool name for session memory."""
        ctx = self._create_context({"event": "PreToolUse"})

        tool_name = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {})

        # Record for session continuity
        tool_record = {
            "tool": tool_name,
            "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else [],
            "timestamp": ctx.timestamp,
        }
        self._tool_calls.append(tool_record)

        # Keep only last 100
        if len(self._tool_calls) > 100:
            self._tool_calls = self._tool_calls[-100:]

        # Save to memory
        self.memory.save(str(ctx.timestamp), tool_record, memory_type="session_context", session_id=self.session_id)

        return {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}

    # =========================================================================
    # POST TOOL USE - Record tool result
    # =========================================================================
    def on_post_tool_use(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PostToolUse event - record tool result for session memory."""
        ctx = self._create_context({"event": "PostToolUse"})

        tool_name = payload.get("tool_name", "")
        tool_result = payload.get("tool_result", {})

        # Update last tool call with result info
        if self._tool_calls and self._tool_calls[-1]["tool"] == tool_name:
            self._tool_calls[-1]["result_summary"] = str(tool_result)[:200]
            self._tool_calls[-1]["completed_at"] = ctx.timestamp

        # Save to memory
        self.memory.save(str(ctx.timestamp), {
            "tool": tool_name,
            "result_summary": str(tool_result)[:500],
            "timestamp": ctx.timestamp,
        }, memory_type="session_context", session_id=self.session_id)

        return {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}

    # =========================================================================
    # STOP - Session end, save summary
    # =========================================================================
    def on_stop(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Stop event - save session summary and flush observers."""
        ctx = self._create_context({"event": "Stop"})

        # Build session summary
        summary = {
            "session_id": self.session_id,
            "agent_type": self.agent_type,
            "duration_seconds": time.time() - self._session_start_time,
            "tool_calls_count": len(self._tool_calls),
            "tools_used": list(set(t["tool"] for t in self._tool_calls)),
            "skills_injected": self._count_skills_injected(),
            "timestamp": ctx.timestamp,
        }

        # Save session summary
        self.memory.save("summary", summary, memory_type="session_context", session_id=self.session_id)

        # Flush task observer
        observer_state = self._flush_task_observer()
        if observer_state:
            self.memory.save("task_observer", "state", observer_state, memory_type="persistent")

        # Cleanup old memories (TTL)
        self.memory.cleanup_expired()

        return {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": json.dumps({"session_summary": summary})
            }
        }

    def _count_skills_injected(self) -> int:
        """Count unique skills injected this session."""
        selections = self.memory.query("selection", limit=100)
        skills = set()
        for sel in selections:
            data = sel.get("data", {})
            for skill in data.get("selected_skills", []):
                skills.add(skill.get("slug", ""))
        return len(skills)

    def _flush_task_observer(self) -> Optional[Dict]:
        """Flush task observer state."""
        # This would integrate with the task-observer meta-skill
        return self.memory.load("task_observer", "pending", default=None)


# =========================================================================
# CLI ENTRY POINT
# =========================================================================
def main():
    """Main entry point for hook execution."""
    if len(sys.argv) < 2:
        print("Usage: runtime.py <hook_event> [payload_json]", file=sys.stderr)
        sys.exit(1)

    hook_event = sys.argv[1]
    payload = {}
    if len(sys.argv) > 2:
        try:
            payload = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            payload = {"raw": sys.argv[2]}

    # Load config
    config_path = Path(__file__).parent.parent / "config" / "runtime.json"
    config = {}
    if config_path.exists():
        config = json.loads(config_path.read_text())

    runtime = HookRuntime(config)

    # Dispatch to handler
    handlers = {
        "SessionStart": runtime.on_session_start,
        "UserPromptSubmit": runtime.on_user_prompt_submit,
        "PreToolUse": runtime.on_pre_tool_use,
        "PostToolUse": runtime.on_post_tool_use,
        "Stop": runtime.on_stop,
    }

    handler = handlers.get(hook_event)
    if not handler:
        print(f"Unknown hook event: {hook_event}", file=sys.stderr)
        sys.exit(1)

    try:
        result = handler(payload)
        print(json.dumps(result))
    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        # Fail open - return empty result to not block agent
        print(json.dumps({"hookSpecificOutput": {"hookEventName": hook_event}}))


if __name__ == "__main__":
    main()