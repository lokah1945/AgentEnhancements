#!/usr/bin/env python3
"""
AgentEnhancements Correction Loop — Safe self-correction guidance.
Analyzes check failures, recommends capabilities, manages iteration.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum

from quality_checks import CheckResult, CheckStatus, ChangeType
from registry import SkillRegistry
from load_skills import LoadSkills


class FailureCategory(Enum):
    """Categories of check failures."""
    SYNTAX_ERROR = "syntax_error"
    TYPE_ERROR = "type_error"
    TEST_FAILURE = "test_failure"
    LINT_ERROR = "lint_error"
    MISSING_DEPENDENCY = "missing_dependency"
    CONFIGURATION_ERROR = "configuration_error"
    PERMISSION_ERROR = "permission_error"
    TIMEOUT = "timeout"
    ASSERTION_ERROR = "assertion_error"
    IMPORT_ERROR = "import_error"
    RUNTIME_ERROR = "runtime_error"
    UNKNOWN = "unknown"


@dataclass
class Hypothesis:
    """A testable hypothesis for a failure."""
    id: str
    category: FailureCategory
    description: str
    test_command: str
    expected_outcome: str
    confidence: float
    recommended_capability: Optional[str] = None


@dataclass
class CorrectionStep:
    """A correction step with minimal change."""
    hypothesis: Hypothesis
    change_description: str
    files_to_modify: List[str]
    verification_checks: List[str]
    estimated_tokens: int


class FailureAnalyzer:
    """Analyze check failures and generate hypotheses."""

    # Error pattern to category mapping
    ERROR_PATTERNS = [
        (r"SyntaxError|IndentationError|TabError", FailureCategory.SYNTAX_ERROR),
        (r"TypeError|AttributeError.*object has no attribute", FailureCategory.TYPE_ERROR),
        (r"AssertionError|FAILED.*test_|pytest.*failed", FailureCategory.TEST_FAILURE),
        (r"ruff|flake8|ESLint|pylint|mypy", FailureCategory.LINT_ERROR),
        (r"ModuleNotFoundError|ImportError|No module named", FailureCategory.IMPORT_ERROR),
        (r"Missing dependency|not installed|pip install", FailureCategory.MISSING_DEPENDENCY),
        (r"Permission denied|access denied|unauthorized", FailureCategory.PERMISSION_ERROR),
        (r"Timeout|timed out|deadline exceeded", FailureCategory.TIMEOUT),
        (r"ConfigError|ConfigurationError|Invalid config", FailureCategory.CONFIGURATION_ERROR),
    ]

    # Category to capability mapping
    CATEGORY_CAPABILITIES = {
        FailureCategory.SYNTAX_ERROR: ["python-basics", "code-quality"],
        FailureCategory.TYPE_ERROR: ["type-safety", "mypy-skills"],
        FailureCategory.TEST_FAILURE: ["testing", "pytest-skills", "debugging"],
        FailureCategory.LINT_ERROR: ["code-quality", "ruff-skills", "formatting"],
        FailureCategory.MISSING_DEPENDENCY: ["dependency-management", "pip-skills"],
        FailureCategory.CONFIGURATION_ERROR: ["config-management", "yaml-skills"],
        FailureCategory.PERMISSION_ERROR: ["security", "file-permissions"],
        FailureCategory.TIMEOUT: ["performance", "async-skills"],
        FailureCategory.ASSERTION_ERROR: ["testing", "debugging"],
        FailureCategory.IMPORT_ERROR: ["python-basics", "module-structure"],
        FailureCategory.RUNTIME_ERROR: ["debugging", "error-handling"],
    }

    def __init__(self, base_dir: Path, registry: SkillRegistry):
        self.base_dir = base_dir
        self.registry = registry
        self.loader = LoadSkills(base_dir, registry)

    def analyze_failure(self, result: CheckResult) -> List[Hypothesis]:
        """Analyze a check failure and generate testable hypotheses."""
        hypotheses = []

        # Determine failure category
        category = self._categorize_failure(result)

        # Get stderr/stdout for analysis
        output = (result.stderr + "\n" + result.stdout).lower()

        # Generate hypotheses based on category
        if category == FailureCategory.SYNTAX_ERROR:
            hypotheses.extend(self._hypothesize_syntax_error(result, output))
        elif category == FailureCategory.TYPE_ERROR:
            hypotheses.extend(self._hypothesize_type_error(result, output))
        elif category == FailureCategory.TEST_FAILURE:
            hypotheses.extend(self._hypothesize_test_failure(result, output))
        elif category == FailureCategory.LINT_ERROR:
            hypotheses.extend(self._hypothesize_lint_error(result, output))
        elif category == FailureCategory.IMPORT_ERROR:
            hypotheses.extend(self._hypothesize_import_error(result, output))
        elif category == FailureCategory.MISSING_DEPENDENCY:
            hypotheses.extend(self._hypothesize_missing_dependency(result, output))
        elif category == FailureCategory.CONFIGURATION_ERROR:
            hypotheses.extend(self._hypothesize_config_error(result, output))
        elif category == FailureCategory.PERMISSION_ERROR:
            hypotheses.extend(self._hypothesize_permission_error(result, output))
        elif category == FailureCategory.TIMEOUT:
            hypotheses.extend(self._hypothesize_timeout(result, output))
        else:
            hypotheses.extend(self._hypothesize_generic(result, output))

        # Add capability recommendations
        for hyp in hypotheses:
            hyp.recommended_capability = self._recommend_capability(hyp.category)

        return hypotheses

    def _categorize_failure(self, result: CheckResult) -> FailureCategory:
        """Categorize failure from error output."""
        output = (result.stderr + "\n" + result.stdout).lower()

        for pattern, category in self.ERROR_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                return category

        # Check error signature
        if result.error_signature:
            for pattern, category in self.ERROR_PATTERNS:
                if re.search(pattern, result.error_signature, re.IGNORECASE):
                    return category

        return FailureCategory.UNKNOWN

    def _hypothesize_syntax_error(self, result: CheckResult, output: str) -> List[Hypothesis]:
        return [Hypothesis(
            id="syntax_1",
            category=FailureCategory.SYNTAX_ERROR,
            description="Syntax error in modified Python file",
            test_command="python3 -m py_compile $(git diff --name-only '*.py')",
            expected_outcome="Identifies specific file and line with syntax error",
            confidence=0.9,
        )]

    def _hypothesize_type_error(self, result: CheckResult, output: str) -> List[Hypothesis]:
        hypotheses = [
            Hypothesis(
                id="type_1",
                category=FailureCategory.TYPE_ERROR,
                description="Type mismatch in function call or assignment",
                test_command="mypy $(git diff --name-only '*.py') 2>/dev/null || echo 'mypy not available'",
                expected_outcome="Shows specific type errors with line numbers",
                confidence=0.8,
            ),
            Hypothesis(
                id="type_2",
                category=FailureCategory.TYPE_ERROR,
                description="Missing type annotations causing inference issues",
                test_command="mypy --strict $(git diff --name-only '*.py') 2>/dev/null || echo 'mypy not available'",
                expected_outcome="Reveals missing annotations",
                confidence=0.6,
            ),
        ]
        return hypotheses

    def _hypothesize_test_failure(self, result: CheckResult, output: str) -> List[Hypothesis]:
        return [Hypothesis(
            id="test_1",
            category=FailureCategory.TEST_FAILURE,
            description="Test assertion failed - logic error or changed behavior",
            test_command="python3 -m pytest -xvs --tb=long $(git diff --name-only '*_test.py') 2>/dev/null",
            expected_outcome="Shows exact assertion failure with values",
            confidence=0.9,
        )]

    def _hypothesize_lint_error(self, result: CheckResult, output: str) -> List[Hypothesis]:
        return [Hypothesis(
            id="lint_1",
            category=FailureCategory.LINT_ERROR,
            description="Code style or formatting violation",
            test_command="ruff check $(git diff --name-only '*.py') 2>/dev/null || echo 'ruff not available'",
            expected_outcome="Lists specific lint violations with fix suggestions",
            confidence=0.9,
        )]

    def _hypothesize_import_error(self, result: CheckResult, output: str) -> List[Hypothesis]:
        return [Hypothesis(
            id="import_1",
            category=FailureCategory.IMPORT_ERROR,
            description="Missing or incorrect import",
            test_command="python3 -c \"import $(echo '{}' | grep -oP 'No module named \\K\\w+' | head -1)\" 2>&1 || echo 'Check import path'",
            expected_outcome="Confirms missing module or path issue",
            confidence=0.8,
        )]

    def _hypothesize_missing_dependency(self, result: CheckResult, output: str) -> List[Hypothesis]:
        return [Hypothesis(
            id="dep_1",
            category=FailureCategory.MISSING_DEPENDENCY,
            description="Required package not installed",
            test_command="pip list | grep -i $(echo '{}' | grep -oP 'No module named \\K\\w+' | head -1) || echo 'Not installed'",
            expected_outcome="Confirms package missing",
            confidence=0.9,
        )]

    def _hypothesize_config_error(self, result: CheckResult, output: str) -> List[Hypothesis]:
        return [Hypothesis(
            id="config_1",
            category=FailureCategory.CONFIGURATION_ERROR,
            description="Configuration file syntax or validation error",
            test_command="python3 -c \"import yaml; yaml.safe_load(open('config.yaml'))\" 2>&1 || echo 'Check config format'",
            expected_outcome="Identifies config file issue",
            confidence=0.7,
        )]

    def _hypothesize_permission_error(self, result: CheckResult, output: str) -> List[Hypothesis]:
        return [Hypothesis(
            id="perm_1",
            category=FailureCategory.PERMISSION_ERROR,
            description="File or resource permission issue",
            test_command="ls -la $(echo '{}' | grep -oP 'Permission denied.*\\K\\S+' | head -1) 2>/dev/null || echo 'Check file permissions'",
            expected_outcome="Shows file permissions",
            confidence=0.7,
        )]

    def _hypothesize_timeout(self, result: CheckResult, output: str) -> List[Hypothesis]:
        return [Hypothesis(
            id="timeout_1",
            category=FailureCategory.TIMEOUT,
            description="Operation exceeded time limit",
            test_command="echo 'Review timeout settings and optimize slow operations'",
            expected_outcome="Identifies slow operation",
            confidence=0.6,
        )]

    def _hypothesize_generic(self, result: CheckResult, output: str) -> List[Hypothesis]:
        return [Hypothesis(
            id="generic_1",
            category=FailureCategory.UNKNOWN,
            description="Unknown failure - investigate error output",
            test_command=f"echo 'Error: {result.error_signature or result.stderr[:200]}'",
            expected_outcome="Provides starting point for investigation",
            confidence=0.3,
        )]

    def _recommend_capability(self, category: FailureCategory) -> Optional[str]:
        """Recommend a skill capability for the failure category."""
        capabilities = self.CATEGORY_CAPABILITIES.get(category, [])
        if not capabilities:
            return None

        # Check which capability is available
        for cap in capabilities:
            composition = self.loader.get_minimal_set(
                f"help with {cap}",
                "claude-code",
                max_tokens=200
            )
            if composition.primary or composition.supporting:
                return cap

        return capabilities[0] if capabilities else None


class CorrectionPlanner:
    """Plan minimal correction steps."""

    def __init__(self, base_dir: Path, registry: SkillRegistry):
        self.base_dir = base_dir
        self.registry = registry
        self.analyzer = FailureAnalyzer(base_dir, registry)

    def plan_correction(self, result: CheckResult) -> List[CorrectionStep]:
        """Plan correction steps for a failed check."""
        hypotheses = self.analyzer.analyze_failure(result)
        steps = []

        for hyp in hypotheses:
            if hyp.confidence < 0.4:
                continue  # Skip low-confidence hypotheses

            step = self._create_step(hyp, result)
            if step:
                steps.append(step)

        # Sort by confidence
        steps.sort(key=lambda s: -s.hypothesis.confidence)
        return steps[:3]  # Max 3 steps

    def _create_step(self, hypothesis: Hypothesis, result: CheckResult) -> Optional[CorrectionStep]:
        """Create a correction step from hypothesis."""
        # Determine files to modify based on git diff
        files = self._get_relevant_files(result)

        # Get verification checks
        verification = self._get_verification_checks(hypothesis.category)

        return CorrectionStep(
            hypothesis=hypothesis,
            change_description=f"Fix {hypothesis.category.value}: {hypothesis.description}",
            files_to_modify=files,
            verification_checks=verification,
            estimated_tokens=100,
        )

    def _get_relevant_files(self, result: CheckResult) -> List[str]:
        """Get files relevant to the failure."""
        import subprocess
        try:
            diff_files = subprocess.run(
                "git diff --name-only",
                shell=True, cwd=self.base_dir, capture_output=True, text=True
            ).stdout.strip().split("\n")
            return [f for f in diff_files if f]
        except Exception:
            return []

    def _get_verification_checks(self, category: FailureCategory) -> List[str]:
        """Get checks to verify the fix."""
        verification_map = {
            FailureCategory.SYNTAX_ERROR: ["syntax_check"],
            FailureCategory.TYPE_ERROR: ["type_check", "syntax_check"],
            FailureCategory.TEST_FAILURE: ["focused_unit_test", "nearest_regression_test"],
            FailureCategory.LINT_ERROR: ["format_check", "lint_check"],
            FailureCategory.IMPORT_ERROR: ["syntax_check"],
            FailureCategory.MISSING_DEPENDENCY: ["syntax_check"],
            FailureCategory.CONFIGURATION_ERROR: ["syntax_check"],
            FailureCategory.PERMISSION_ERROR: [],
            FailureCategory.TIMEOUT: ["focused_unit_test"],
        }
        return verification_map.get(category, ["nearest_regression_test"])


class LoopController:
    """Control the correction loop with safety limits."""

    MAX_ITERATIONS = 5
    MAX_TOTAL_TOKENS = 2000

    def __init__(self, base_dir: Path, registry: SkillRegistry):
        self.base_dir = base_dir
        self.registry = registry
        self.planner = CorrectionPlanner(base_dir, registry)
        self.runner = None  # Will be set externally
        self.iteration = 0
        self.total_tokens = 0

    def should_continue(self, results: List[CheckResult]) -> bool:
        """Determine if loop should continue."""
        if self.iteration >= self.MAX_ITERATIONS:
            return False

        # Check if any required checks still failing
        failed_required = any(
            r.status == CheckStatus.FAIL
            for r in results
        )
        if not failed_required:
            return False

        return True

    def run_iteration(self, failed_results: List[CheckResult]) -> List[CorrectionStep]:
        """Run one correction iteration."""
        self.iteration += 1
        all_steps = []

        for result in failed_results:
            if result.status != CheckStatus.FAIL:
                continue

            steps = self.planner.plan_correction(result)
            all_steps.extend(steps)

            # Track tokens
            for step in steps:
                self.total_tokens += step.estimated_tokens

        return all_steps

    def get_status(self) -> Dict:
        """Get loop status."""
        return {
            "iteration": self.iteration,
            "max_iterations": self.MAX_ITERATIONS,
            "total_tokens": self.total_tokens,
            "max_tokens": self.MAX_TOTAL_TOKENS,
            "should_stop": self.iteration >= self.MAX_ITERATIONS or self.total_tokens >= self.MAX_TOTAL_TOKENS,
        }


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Correction Loop CLI")
    parser.add_argument("command", choices=["analyze", "plan", "status"])
    parser.add_argument("--result", help="CheckResult JSON")
    parser.add_argument("--task-id", default="", help="Task ID")
    parser.add_argument("--base-dir", help="Base directory")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent

    registry = SkillRegistry(base_dir)
    analyzer = FailureAnalyzer(base_dir, registry)
    planner = CorrectionPlanner(base_dir, registry)

    if args.command == "analyze":
        if not args.result:
            parser.error("--result required")
        result = CheckResult(**json.loads(args.result))
        hypotheses = analyzer.analyze_failure(result)
        print(json.dumps([asdict(h) for h in hypotheses], indent=2, default=str))

    elif args.command == "plan":
        if not args.result:
            parser.error("--result required")
        result = CheckResult(**json.loads(args.result))
        steps = planner.plan_correction(result)
        print(json.dumps([asdict(s) for s in steps], indent=2, default=str))

    elif args.command == "status":
        controller = LoopController(base_dir, registry)
        print(json.dumps(controller.get_status(), indent=2))


if __name__ == "__main__":
    main()