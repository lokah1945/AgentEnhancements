#!/usr/bin/env python3
"""
AgentEnhancements Subagent Handler — Manage subagent-specific capability pointers.
Handles SubagentStart/SubagentStop events, focused preflight for subagents,
and coordinates capability injection across multiple subagents.
"""

import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from stage_detector import StageDetector, TaskStage, AgentRole, StageDetectionResult
from registry import SkillRegistry


@dataclass
class SubagentContext:
    """Context for a subagent."""
    subagent_id: str
    task: str
    role: str
    parent_session_id: str
    started_at: float
    capabilities_injected: List[str] = field(default_factory=list)
    stage: TaskStage = TaskStage.UNKNOWN


class SubagentHandler:
    """
    Handle subagent lifecycle and capability injection.

    Features:
    - SubagentStart: Extract role/task, run focused preflight
    - SubagentStop: Flush observations, cleanup
    - Coordinate capability injection (avoid duplicates)
    - Track subagent hierarchy
    """

    def __init__(self, base_dir: Path, registry: SkillRegistry):
        self.base_dir = base_dir
        self.registry = registry
        self.stage_detector = StageDetector(base_dir)

        # Active subagents
        self._subagents: Dict[str, SubagentContext] = {}

        # Injected capabilities per session (to avoid duplicates)
        self._injected_per_session: Dict[str, Set[str]] = {}

    def on_subagent_start(self, event_data: Dict, session_id: str) -> Dict[str, Any]:
        """
        Handle SubagentStart event.
        Returns capability injection for the subagent.
        """
        subagent_id = event_data.get("subagent_id", str(uuid.uuid4())[:8])
        task = event_data.get("task", "")
        role = event_data.get("role", "subagent")

        # Detect stage/role
        detection = self.stage_detector.detect_from_subagent_event(event_data)

        # Create subagent context
        ctx = SubagentContext(
            subagent_id=subagent_id,
            task=task,
            role=role,
            parent_session_id=session_id,
            started_at=time.time(),
            stage=detection.stage,
        )

        # Store context
        self._subagents[subagent_id] = ctx

        # Initialize session injection tracking
        if session_id not in self._injected_per_session:
            self._injected_per_session[session_id] = set()

        # Run focused preflight for subagent
        capabilities = self._run_focused_preflight(task, detection, session_id)

        # Record injected capabilities
        injected_ids = [c.entry.slug for c in capabilities]
        ctx.capabilities_injected = injected_ids
        self._injected_per_session[session_id].update(injected_ids)

        return {
            "subagent_id": subagent_id,
            "stage": detection.stage.value,
            "role": detection.role.value,
            "capabilities": [self._capability_to_dict(c) for c in capabilities],
            "token_estimate": sum(c.entry.estimated_tokens for c in capabilities),
        }

    def on_subagent_stop(self, event_data: Dict, session_id: str) -> Dict[str, Any]:
        """
        Handle SubagentStop event.
        Returns summary of subagent execution.
        """
        subagent_id = event_data.get("subagent_id", "")
        result = event_data.get("result", {})

        ctx = self._subagents.pop(subagent_id, None)

        return {
            "subagent_id": subagent_id,
            "duration_seconds": time.time() - ctx.started_at if ctx else 0,
            "capabilities_used": ctx.capabilities_injected if ctx else [],
            "result_summary": str(result)[:200],
        }

    def _run_focused_preflight(
        self,
        task: str,
        detection: StageDetectionResult,
        session_id: str
    ) -> List:
        """Run focused preflight for subagent's specific need."""
        # Get composition from registry
        composition = self.registry.map_task_enhanced(
            task,
            agent_type="claude-code",  # Default, would come from context
            stage=detection.stage.value,
            role=detection.role.value,
            token_budget=200,  # Smaller budget for subagents
            max_results=4,
        )

        # Filter out already injected capabilities
        already_injected = self._injected_per_session.get(session_id, set())
        primary = [c for c in composition.primary if c.entry.slug not in already_injected]
        supporting = [c for c in composition.supporting if c.entry.slug not in already_injected]
        optional = [c for c in composition.optional if c.entry.slug not in already_injected]

        return primary + supporting + optional

    def _capability_to_dict(self, cap) -> Dict:
        """Convert ranked capability to dict."""
        return {
            "id": cap.entry.slug,
            "type": "skill",
            "category": cap.entry.category,
            "readiness": cap.readiness.value if hasattr(cap.readiness, 'value') else str(cap.readiness),
            "tokens": cap.entry.estimated_tokens,
            "role": cap.role.value if hasattr(cap.role, 'value') else str(cap.role),
        }

    def get_subagent_status(self, subagent_id: str) -> Optional[Dict]:
        """Get status of a subagent."""
        ctx = self._subagents.get(subagent_id)
        if not ctx:
            return None

        return {
            "subagent_id": ctx.subagent_id,
            "task": ctx.task,
            "role": ctx.role,
            "stage": ctx.stage.value,
            "started_at": ctx.started_at,
            "duration": time.time() - ctx.started_at,
            "capabilities_injected": ctx.capabilities_injected,
        }

    def list_active_subagents(self, session_id: str) -> List[Dict]:
        """List active subagents for a session."""
        return [
            self.get_subagent_status(sid)
            for sid, ctx in self._subagents.items()
            if ctx.parent_session_id == session_id
        ]

    def check_duplicate_injection(self, capability_id: str, session_id: str) -> bool:
        """Check if capability was already injected in this session."""
        return capability_id in self._injected_per_session.get(session_id, set())

    def cleanup_session(self, session_id: str):
        """Cleanup session tracking."""
        self._injected_per_session.pop(session_id, None)


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Subagent Handler CLI")
    parser.add_argument("command", choices=["start", "stop", "status", "list", "check-duplicate"])
    parser.add_argument("--session", required=True, help="Session ID")
    parser.add_argument("--subagent", help="Subagent ID")
    parser.add_argument("--task", help="Subagent task")
    parser.add_argument("--role", default="subagent", help="Subagent role")
    parser.add_argument("--base-dir", help="Base directory")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent

    registry = SkillRegistry(base_dir)
    handler = SubagentHandler(base_dir, registry)

    if args.command == "start":
        if not args.task:
            parser.error("Task required for start")
        event = {
            "subagent_id": args.subagent or str(uuid.uuid4())[:8],
            "task": args.task,
            "role": args.role,
        }
        result = handler.on_subagent_start(event, args.session)
        print(json.dumps(result, indent=2))

    elif args.command == "stop":
        if not args.subagent:
            parser.error("Subagent ID required for stop")
        event = {"subagent_id": args.subagent, "result": {}}
        result = handler.on_subagent_stop(event, args.session)
        print(json.dumps(result, indent=2))

    elif args.command == "status":
        if not args.subagent:
            parser.error("Subagent ID required for status")
        status = handler.get_subagent_status(args.subagent)
        if status:
            print(json.dumps(status, indent=2))
        else:
            print(f"Subagent not found: {args.subagent}")

    elif args.command == "list":
        subagents = handler.list_active_subagents(args.session)
        print(json.dumps(subagents, indent=2))

    elif args.command == "check-duplicate":
        if not args.subagent:
            parser.error("Capability ID required (use --subagent for capability ID)")
        is_dup = handler.check_duplicate_injection(args.subagent, args.session)
        print(json.dumps({"duplicate": is_dup}))


if __name__ == "__main__":
    main()