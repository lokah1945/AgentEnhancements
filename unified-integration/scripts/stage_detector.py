#!/usr/bin/env python3
"""
AgentEnhancements Stage Detector — Detect task stage and agent role from host events.
Provides stage/role hints for capability selection.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum


class TaskStage(Enum):
    """Task stage indicators."""
    UNDERSTAND = "understand"
    PLAN = "plan"
    IMPLEMENT = "implement"
    DEBUG = "debug"
    VERIFY = "verify"
    RELEASE = "release"
    UNKNOWN = "unknown"


class AgentRole(Enum):
    """Agent role types."""
    MAIN = "main"
    SUBAGENT = "subagent"
    REVIEWER = "reviewer"
    UNKNOWN = "unknown"


@dataclass
class StageDetectionResult:
    """Result of stage/role detection."""
    stage: TaskStage
    role: AgentRole
    confidence: float
    signals: List[str]
    subagent_id: Optional[str] = None
    subagent_task: Optional[str] = None


class StageDetector:
    """
    Detect task stage and agent role from host events and context.

    Supports:
    - Claude Code: UserPromptSubmit (initial), SubagentStart/SubagentStop
    - Codex: equivalent hooks
    - OpenCode: plugin lifecycle events
    """

    # Stage detection patterns
    STAGE_PATTERNS = {
        TaskStage.UNDERSTAND: [
            r"\b(explore|understand|analyze|investigate|read|review|overview)\b",
            r"\b(what is|how does|explain|describe|show me)\b",
            r"\b(getting started|introduction|orientation)\b",
        ],
        TaskStage.PLAN: [
            r"\b(plan|design|architect|strategize|roadmap)\b",
            r"\b(create a plan|design a|architecture for)\b",
            r"\b(spec|specification|requirements)\b",
        ],
        TaskStage.IMPLEMENT: [
            r"\b(implement|build|create|write|develop|code|generate)\b",
            r"\b(add|modify|update|refactor|extend)\b",
            r"\b(feature|function|component|module|service)\b",
        ],
        TaskStage.DEBUG: [
            r"\b(debug|fix|resolve|troubleshoot|error|bug|issue)\b",
            r"\b(failing|broken|not working|crash|exception)\b",
            r"\b(test fail|regression|timeout|memory leak)\b",
        ],
        TaskStage.VERIFY: [
            r"\b(test|verify|validate|check|audit|review)\b",
            r"\b(run tests|integration test|e2e|smoke test)\b",
            r"\b(security|performance|accessibility|compliance)\b",
        ],
        TaskStage.RELEASE: [
            r"\b(release|deploy|publish|ship|deliver)\b",
            r"\b(ci/cd|pipeline|staging|production)\b",
            r"\b(rollback|hotfix|patch|version)\b",
        ],
    }

    # Role detection patterns
    ROLE_PATTERNS = {
        AgentRole.SUBAGENT: [
            r"subagent",
            r"parallel",
            r"delegate",
            r"spawn",
        ],
        AgentRole.REVIEWER: [
            r"review",
            r"audit",
            r"approve",
            r"check",
        ],
    }

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def detect_from_prompt(self, prompt: str, context: Optional[Dict] = None) -> StageDetectionResult:
        """Detect stage from user prompt."""
        prompt_lower = prompt.lower()
        stage_scores = {}

        for stage, patterns in self.STAGE_PATTERNS.items():
            score = 0
            matched = []
            for pattern in patterns:
                matches = re.findall(pattern, prompt_lower, re.IGNORECASE)
                if matches:
                    score += len(matches)
                    matched.extend(matches)
            if score > 0:
                stage_scores[stage] = (score, matched)

        if stage_scores:
            best_stage = max(stage_scores, key=lambda s: stage_scores[s][0])
            confidence = min(stage_scores[best_stage][0] / 5.0, 1.0)
            signals = [f"prompt:{m}" for m in stage_scores[best_stage][1]]
        else:
            best_stage = TaskStage.UNKNOWN
            confidence = 0.0
            signals = []

        # Check context for additional signals
        if context:
            stage_scores, signals = self._check_context_signals(context, stage_scores, signals)
            # Re-evaluate best stage after context signals
            if stage_scores:
                best_stage = max(stage_scores, key=lambda s: stage_scores[s][0])
                confidence = min(stage_scores[best_stage][0] / 5.0, 1.0)

        return StageDetectionResult(
            stage=best_stage,
            role=AgentRole.MAIN,
            confidence=confidence,
            signals=signals,
        )

    def detect_from_subagent_event(self, event_data: Dict) -> StageDetectionResult:
        """Detect stage/role from SubagentStart event."""
        subagent_id = event_data.get("subagent_id", "")
        subagent_task = event_data.get("task", "")
        subagent_role = event_data.get("role", "")

        # Detect stage from subagent task
        stage_result = self.detect_from_prompt(subagent_task)

        # Determine role
        role = AgentRole.SUBAGENT
        if subagent_role:
            role_lower = subagent_role.lower()
            if "review" in role_lower:
                role = AgentRole.REVIEWER

        return StageDetectionResult(
            stage=stage_result.stage,
            role=role,
            confidence=stage_result.confidence,
            signals=stage_result.signals + [f"subagent:{subagent_id}"],
            subagent_id=subagent_id,
            subagent_task=subagent_task,
        )

    def detect_from_continuation(self, context: Dict) -> StageDetectionResult:
        """Detect stage from continuation context (mid-task)."""
        recent_tools = context.get("recent_tools", [])
        session_duration = context.get("session_duration", 0)

        signals = []

        # Analyze recent tool usage
        tool_categories = self._categorize_tools(recent_tools)
        signals.extend([f"tool:{cat}" for cat in tool_categories])

        # Infer stage from tool pattern
        if tool_categories & {"read", "grep", "glob", "list"}:
            stage = TaskStage.UNDERSTAND
        elif tool_categories & {"write", "edit", "bash", "task"}:
            stage = TaskStage.IMPLEMENT
        elif tool_categories & {"test", "check"}:
            stage = TaskStage.VERIFY
        else:
            stage = TaskStage.UNKNOWN

        confidence = min(len(tool_categories) / 3.0, 1.0)

        return StageDetectionResult(
            stage=stage,
            role=AgentRole.MAIN,
            confidence=confidence,
            signals=signals,
        )

    def _categorize_tools(self, tools: List[Dict]) -> Set[str]:
        """Categorize recent tools by function."""
        categories = set()
        tool_map = {
            "read_file": "read", "read": "read", "cat": "read",
            "write_file": "write", "write": "write", "create": "write",
            "edit_file": "edit", "edit": "edit", "modify": "edit",
            "bash": "bash", "run": "bash", "exec": "bash",
            "glob": "glob", "grep": "grep", "search": "grep",
            "list_dir": "list", "ls": "list",
            "task": "task", "subagent": "task",
        }
        for tool in tools:
            tool_name = tool.get("tool", "").lower()
            if tool_name in tool_map:
                categories.add(tool_map[tool_name])
        return categories

    def _check_context_signals(
        self,
        context: Dict,
        stage_scores: Dict,
        signals: List[str]
    ) -> tuple:
        """Check context for additional stage signals."""
        # Check for explicit stage hint
        if "stage" in context:
            try:
                explicit_stage = TaskStage(context["stage"])
                if explicit_stage not in stage_scores:
                    stage_scores[explicit_stage] = (0, [])
                score, matched = stage_scores[explicit_stage]
                stage_scores[explicit_stage] = (score + 10, matched + ["explicit"])
                signals.append("explicit_stage")
            except ValueError:
                pass

        # Check for role hint
        if "role" in context:
            signals.append(f"role_hint:{context['role']}")

        return stage_scores, signals

    def get_stage_guidance(self, stage: TaskStage) -> Dict[str, Any]:
        """Get capability guidance for a stage."""
        guidance = {
            TaskStage.UNDERSTAND: {
                "priority_capabilities": ["read", "search", "analyze", "documentation"],
                "suggested_skills": ["code-navigation", "dependency-analysis", "architectural-review"],
                "avoid": ["heavy-refactoring", "deployment"],
            },
            TaskStage.PLAN: {
                "priority_capabilities": ["design", "architect", "specification"],
                "suggested_skills": ["system-design", "api-design", "database-design"],
                "avoid": ["implementation-details", "debugging"],
            },
            TaskStage.IMPLEMENT: {
                "priority_capabilities": ["write", "edit", "refactor", "test"],
                "suggested_skills": ["framework-specific", "best-practices", "testing"],
                "avoid": ["exploration", "high-level-design"],
            },
            TaskStage.DEBUG: {
                "priority_capabilities": ["diagnose", "trace", "profile", "log-analysis"],
                "suggested_skills": ["debugging", "profiling", "error-analysis"],
                "avoid": ["new-features", "refactoring"],
            },
            TaskStage.VERIFY: {
                "priority_capabilities": ["test", "validate", "audit", "check"],
                "suggested_skills": ["testing", "security-audit", "performance-testing"],
                "avoid": ["implementation", "exploration"],
            },
            TaskStage.RELEASE: {
                "priority_capabilities": ["deploy", "package", "configure", "monitor"],
                "suggested_skills": ["deployment", "ci-cd", "release-management"],
                "avoid": ["development", "debugging"],
            },
            TaskStage.UNKNOWN: {
                "priority_capabilities": [],
                "suggested_skills": [],
                "avoid": [],
            },
        }
        return guidance.get(stage, guidance[TaskStage.UNKNOWN])


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Stage Detector CLI")
    parser.add_argument("command", choices=["detect", "detect-subagent", "detect-continuation", "guidance"])
    parser.add_argument("prompt", nargs="?", help="Task prompt")
    parser.add_argument("--context", help="Context JSON")
    parser.add_argument("--event", help="Subagent event JSON")
    parser.add_argument("--base-dir", help="Base directory")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent

    detector = StageDetector(base_dir)

    context = json.loads(args.context) if args.context else None
    event = json.loads(args.event) if args.event else None

    if args.command == "detect":
        if not args.prompt:
            parser.error("Prompt required")
        result = detector.detect_from_prompt(args.prompt, context)
        print(json.dumps({
            "stage": result.stage.value,
            "role": result.role.value,
            "confidence": result.confidence,
            "signals": result.signals,
        }, indent=2))

    elif args.command == "detect-subagent":
        if not args.event:
            parser.error("Event required")
        result = detector.detect_from_subagent_event(event)
        print(json.dumps({
            "stage": result.stage.value,
            "role": result.role.value,
            "confidence": result.confidence,
            "signals": result.signals,
            "subagent_id": result.subagent_id,
            "subagent_task": result.subagent_task,
        }, indent=2))

    elif args.command == "detect-continuation":
        if not context:
            parser.error("Context required")
        result = detector.detect_from_continuation(context)
        print(json.dumps({
            "stage": result.stage.value,
            "role": result.role.value,
            "confidence": result.confidence,
            "signals": result.signals,
        }, indent=2))

    elif args.command == "guidance":
        if not args.prompt:
            parser.error("Prompt required for stage")
        stage = TaskStage(args.prompt)
        print(json.dumps(detector.get_stage_guidance(stage), indent=2))


if __name__ == "__main__":
    main()