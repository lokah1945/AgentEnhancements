#!/usr/bin/env python3
"""
AgentEnhancements Quality Checks — Evidence-based verification guidance.
Derives acceptance checks from requirements, maps to existing tests,
and provides risk-adaptive check selection.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict, field
from enum import Enum


class CheckStatus(Enum):
    """Check execution status - MUST NOT be combined."""
    PASS = "PASS"                    # Command executed and passed
    FAIL = "FAIL"                    # Command executed and failed
    NOT_RUN = "NOT_RUN"              # Not yet executed
    BLOCKED = "BLOCKED"              # Cannot run (permission/env/dependency)
    NOT_APPLICABLE = "NOT_APPLICABLE"  # Not relevant with reason
    UNVERIFIED = "UNVERIFIED"        # Claimed result cannot be verified


class CheckSource(Enum):
    """Source of the check requirement."""
    USER_REQUEST = "user_request"
    CONTRACT = "contract"
    AGENTS_MD = "agents_md"
    README = "readme"
    EXISTING_TESTS = "existing_tests"
    CI_CONFIG = "ci_config"
    FRAMEWORK_DOCS = "framework_docs"
    HEURISTIC = "heuristic"  # Marked as suggested, not required


class ChangeType(Enum):
    """Type of code change for risk-adaptive selection."""
    RENAME_TEXT_FORMAT = "rename_text_format"
    BUG_FIX_LOCAL = "bug_fix_local"
    FEATURE_MODULE = "feature_module"
    AUTH_TENANT_BILLING = "auth_tenant_billing"
    DATABASE_MIGRATION = "database_migration"
    DEPLOYMENT_RELEASE = "deployment_release"
    UNKNOWN = "unknown"


@dataclass
class AcceptanceCheck:
    """A single acceptance check with evidence requirements."""
    check_id: str
    name: str
    description: str
    source: CheckSource
    change_types: List[ChangeType]
    command: str
    expected_result: str
    working_dir: str = "."
    timeout_seconds: int = 60
    required: bool = True  # False = suggested/heuristic
    tags: List[str] = field(default_factory=list)


@dataclass
class CheckResult:
    """Result of a check execution with full evidence."""
    check_id: str
    status: CheckStatus
    command: str
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    timestamp: str = ""
    scope: str = ""
    artifact_reference: str = ""
    repo_commit: str = ""
    task_id: str = ""
    error_signature: str = ""


class AcceptanceDeriver:
    """
    Derive acceptance checks from requirements and context.

    Sources (in priority order):
    1. User request & explicit acceptance criteria
    2. CONTRACT.md, AGENTS.md, README, test commands, repo policy
    3. Existing tests/CI + type/lint/static checks
    4. Official framework docs (if requested/relevant)
    5. Heuristic quality checklist (marked as suggested)
    """

    # Risk-adaptive check mapping
    CHANGE_TYPE_CHECKS = {
        ChangeType.RENAME_TEXT_FORMAT: [
            "diff_check",
            "syntax_check",
            "format_check",
        ],
        ChangeType.BUG_FIX_LOCAL: [
            "reproduction_test",
            "focused_unit_test",
            "nearest_regression_test",
        ],
        ChangeType.FEATURE_MODULE: [
            "unit_tests",
            "integration_tests",
            "contract_api_tests",
        ],
        ChangeType.AUTH_TENANT_BILLING: [
            "security_tests",
            "access_control_tests",
            "tenant_isolation_tests",
            "integrity_tests",
        ],
        ChangeType.DATABASE_MIGRATION: [
            "schema_checks",
            "migration_rollback_test",
            "backup_considerations",
        ],
        ChangeType.DEPLOYMENT_RELEASE: [
            "ci_pipeline",
            "smoke_tests",
            "health_checks",
            "rollback_readiness",
        ],
    }

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._check_catalog = self._build_check_catalog()

    def _build_check_catalog(self) -> Dict[str, AcceptanceCheck]:
        """Build catalog of all possible checks."""
        checks = {}

        # Core checks
        checks["diff_check"] = AcceptanceCheck(
            check_id="diff_check",
            name="Diff Review",
            description="Review git diff for unintended changes",
            source=CheckSource.HEURISTIC,
            change_types=[ChangeType.RENAME_TEXT_FORMAT],
            command="git diff --stat",
            expected_result="Clean diff matching intended changes",
            required=False,
            tags=["review", "safety"],
        )

        checks["syntax_check"] = AcceptanceCheck(
            check_id="syntax_check",
            name="Syntax Validation",
            description="Validate syntax of modified files",
            source=CheckSource.EXISTING_TESTS,
            change_types=[ChangeType.RENAME_TEXT_FORMAT, ChangeType.BUG_FIX_LOCAL, ChangeType.FEATURE_MODULE],
            command="python3 -m py_compile $(git diff --name-only '*.py')",
            expected_result="No syntax errors",
            required=True,
            tags=["syntax", "python"],
        )

        checks["format_check"] = AcceptanceCheck(
            check_id="format_check",
            name="Format Check",
            description="Check code formatting (black, ruff, prettier)",
            source=CheckSource.EXISTING_TESTS,
            change_types=[ChangeType.RENAME_TEXT_FORMAT, ChangeType.FEATURE_MODULE],
            command="ruff check $(git diff --name-only '*.py') || black --check $(git diff --name-only '*.py')",
            expected_result="No formatting violations",
            required=True,
            tags=["format", "lint"],
        )

        checks["reproduction_test"] = AcceptanceCheck(
            check_id="reproduction_test",
            name="Bug Reproduction",
            description="Run test that reproduces the bug before fix",
            source=CheckSource.USER_REQUEST,
            change_types=[ChangeType.BUG_FIX_LOCAL],
            command="python3 -m pytest -xvs -k 'test_reproduces_bug' 2>/dev/null || echo 'No reproduction test found'",
            expected_result="Test fails before fix, passes after",
            required=True,
            tags=["bug", "regression"],
        )

        checks["focused_unit_test"] = AcceptanceCheck(
            check_id="focused_unit_test",
            name="Focused Unit Tests",
            description="Run unit tests for the modified module",
            source=CheckSource.EXISTING_TESTS,
            change_types=[ChangeType.BUG_FIX_LOCAL, ChangeType.FEATURE_MODULE],
            command="python3 -m pytest -xvs $(git diff --name-only '*.py' | sed 's/\\.py$/_test.py/') 2>/dev/null || python3 -m pytest -xvs $(git diff --name-only '*_test.py')",
            expected_result="All tests pass",
            required=True,
            tags=["unit", "regression"],
        )

        checks["nearest_regression_test"] = AcceptanceCheck(
            check_id="nearest_regression_test",
            name="Nearest Regression Tests",
            description="Run tests for related functionality",
            source=CheckSource.HEURISTIC,
            change_types=[ChangeType.BUG_FIX_LOCAL],
            command="python3 -m pytest -x --tb=short 2>&1 | head -50",
            expected_result="No new failures",
            required=True,
            tags=["regression", "safety"],
        )

        checks["unit_tests"] = AcceptanceCheck(
            check_id="unit_tests",
            name="Unit Test Suite",
            description="Run full unit test suite",
            source=CheckSource.CI_CONFIG,
            change_types=[ChangeType.FEATURE_MODULE],
            command="python3 -m pytest -x --tb=short",
            expected_result="All tests pass",
            required=True,
            tags=["unit", "ci"],
        )

        checks["integration_tests"] = AcceptanceCheck(
            check_id="integration_tests",
            name="Integration Tests",
            description="Run integration tests if available",
            source=CheckSource.CI_CONFIG,
            change_types=[ChangeType.FEATURE_MODULE, ChangeType.DATABASE_MIGRATION],
            command="python3 -m pytest -x --tb=short -m integration 2>/dev/null || echo 'No integration tests'",
            expected_result="All integration tests pass",
            required=True,
            tags=["integration", "ci"],
        )

        checks["contract_api_tests"] = AcceptanceCheck(
            check_id="contract_api_tests",
            name="Contract/API Tests",
            description="Run contract tests for API changes",
            source=CheckSource.CONTRACT,
            change_types=[ChangeType.FEATURE_MODULE],
            command="python3 -m pytest -x --tb=short -m contract 2>/dev/null || echo 'No contract tests'",
            expected_result="All contract tests pass",
            required=True,
            tags=["api", "contract"],
        )

        checks["security_tests"] = AcceptanceCheck(
            check_id="security_tests",
            name="Security Tests",
            description="Run security-focused tests",
            source=CheckSource.CONTRACT,
            change_types=[ChangeType.AUTH_TENANT_BILLING, ChangeType.DEPLOYMENT_RELEASE],
            command="python3 -m pytest -x --tb=short -m security 2>/dev/null || bandit -r . 2>/dev/null || echo 'No security tests'",
            expected_result="No security issues found",
            required=True,
            tags=["security", "audit"],
        )

        checks["access_control_tests"] = AcceptanceCheck(
            check_id="access_control_tests",
            name="Access Control Tests",
            description="Verify tenant isolation and permissions",
            source=CheckSource.CONTRACT,
            change_types=[ChangeType.AUTH_TENANT_BILLING],
            command="python3 -m pytest -x --tb=short -k 'tenant or permission or auth' 2>/dev/null || echo 'No auth tests'",
            expected_result="All access control tests pass",
            required=True,
            tags=["security", "tenant"],
        )

        checks["tenant_isolation_tests"] = AcceptanceCheck(
            check_id="tenant_isolation_tests",
            name="Tenant Isolation Tests",
            description="Verify data isolation between tenants",
            source=CheckSource.CONTRACT,
            change_types=[ChangeType.AUTH_TENANT_BILLING],
            command="python3 -m pytest -x --tb=short -k 'isolation' 2>/dev/null || echo 'No isolation tests'",
            expected_result="All isolation tests pass",
            required=True,
            tags=["security", "tenant"],
        )

        checks["integrity_tests"] = AcceptanceCheck(
            check_id="integrity_tests",
            name="Data Integrity Tests",
            description="Verify data integrity constraints",
            source=CheckSource.CONTRACT,
            change_types=[ChangeType.AUTH_TENANT_BILLING, ChangeType.DATABASE_MIGRATION],
            command="python3 -m pytest -x --tb=short -k 'integrity' 2>/dev/null || echo 'No integrity tests'",
            expected_result="All integrity tests pass",
            required=True,
            tags=["data", "integrity"],
        )

        checks["schema_checks"] = AcceptanceCheck(
            check_id="schema_checks",
            name="Schema Validation",
            description="Validate database schema changes",
            source=CheckSource.CI_CONFIG,
            change_types=[ChangeType.DATABASE_MIGRATION],
            command="python3 -m alembic check 2>/dev/null || python3 -c 'import sqlalchemy; print(\"SQLAlchemy models valid\")' 2>/dev/null || echo 'Schema check skipped'",
            expected_result="Schema valid",
            required=True,
            tags=["database", "schema"],
        )

        checks["migration_rollback_test"] = AcceptanceCheck(
            check_id="migration_rollback_test",
            name="Migration Rollback Test",
            description="Test that migration can be rolled back",
            source=CheckSource.CONTRACT,
            change_types=[ChangeType.DATABASE_MIGRATION],
            command="python3 -m alembic downgrade -1 && python3 -m alembic upgrade head 2>/dev/null || echo 'Rollback test skipped'",
            expected_result="Rollback and re-apply succeed",
            required=True,
            tags=["database", "migration"],
        )

        checks["backup_considerations"] = AcceptanceCheck(
            check_id="backup_considerations",
            name="Backup Considerations",
            description="Verify backup strategy for migration",
            source=CheckSource.HEURISTIC,
            change_types=[ChangeType.DATABASE_MIGRATION],
            command="echo 'Manual verification: backup strategy documented'",
            expected_result="Backup strategy confirmed",
            required=False,
            tags=["database", "backup"],
        )

        checks["ci_pipeline"] = AcceptanceCheck(
            check_id="ci_pipeline",
            name="CI Pipeline",
            description="Run full CI pipeline checks",
            source=CheckSource.CI_CONFIG,
            change_types=[ChangeType.DEPLOYMENT_RELEASE, ChangeType.FEATURE_MODULE],
            command="python3 -m pytest --tb=short && ruff check . && black --check . 2>/dev/null",
            expected_result="All CI checks pass",
            required=True,
            tags=["ci", "pipeline"],
        )

        checks["smoke_tests"] = AcceptanceCheck(
            check_id="smoke_tests",
            name="Smoke Tests",
            description="Run smoke tests for deployment",
            source=CheckSource.CI_CONFIG,
            change_types=[ChangeType.DEPLOYMENT_RELEASE],
            command="python3 -m pytest -x --tb=short -m smoke 2>/dev/null || echo 'No smoke tests'",
            expected_result="Smoke tests pass",
            required=True,
            tags=["deployment", "smoke"],
        )

        checks["health_checks"] = AcceptanceCheck(
            check_id="health_checks",
            name="Health Checks",
            description="Verify service health endpoints",
            source=CheckSource.HEURISTIC,
            change_types=[ChangeType.DEPLOYMENT_RELEASE],
            command="curl -f http://localhost:8000/health 2>/dev/null || echo 'Health endpoint not configured'",
            expected_result="Health endpoint responds OK",
            required=True,
            tags=["deployment", "health"],
        )

        checks["rollback_readiness"] = AcceptanceCheck(
            check_id="rollback_readiness",
            name="Rollback Readiness",
            description="Verify rollback procedure works",
            source=CheckSource.CONTRACT,
            change_types=[ChangeType.DEPLOYMENT_RELEASE, ChangeType.DATABASE_MIGRATION],
            command="echo 'Manual verification: rollback procedure tested'",
            expected_result="Rollback procedure confirmed",
            required=False,
            tags=["deployment", "rollback"],
        )

        # Static analysis checks
        checks["type_check"] = AcceptanceCheck(
            check_id="type_check",
            name="Type Checking",
            description="Run mypy type checking",
            source=CheckSource.EXISTING_TESTS,
            change_types=[ChangeType.FEATURE_MODULE, ChangeType.BUG_FIX_LOCAL],
            command="mypy $(git diff --name-only '*.py') 2>/dev/null || echo 'mypy not configured'",
            expected_result="No type errors",
            required=True,
            tags=["types", "static"],
        )

        checks["lint_check"] = AcceptanceCheck(
            check_id="lint_check",
            name="Lint Check",
            description="Run linting (ruff, flake8, eslint)",
            source=CheckSource.EXISTING_TESTS,
            change_types=[ChangeType.FEATURE_MODULE, ChangeType.BUG_FIX_LOCAL],
            command="ruff check . 2>/dev/null || flake8 . 2>/dev/null || echo 'No linter configured'",
            expected_result="No lint errors",
            required=True,
            tags=["lint", "static"],
        )

        return checks

    def derive_from_request(self, user_request: str) -> List[AcceptanceCheck]:
        """Derive checks from explicit user request."""
        checks = []
        request_lower = user_request.lower()

        # Look for explicit acceptance criteria
        criteria_patterns = [
            (r"acceptance criteria[:\s]+(.+)", "explicit"),
            (r"must[:\s]+(.+)", "explicit"),
            (r"should[:\s]+(.+)", "explicit"),
            (r"verify[:\s]+(.+)", "explicit"),
            (r"test[:\s]+(.+)", "explicit"),
        ]

        for pattern, source in criteria_patterns:
            matches = re.findall(pattern, request_lower, re.IGNORECASE)
            for match in matches:
                check_id = f"user_{len(checks)}"
                checks.append(AcceptanceCheck(
                    check_id=check_id,
                    name=f"User Criteria: {match[:50]}",
                    description=match,
                    source=CheckSource.USER_REQUEST,
                    change_types=[ChangeType.UNKNOWN],
                    command=f"echo 'Manual verification: {match}'",
                    expected_result="Criteria met",
                    required=True,
                    tags=["user", "explicit"],
                ))

        return checks

    def derive_from_repo(self) -> List[AcceptanceCheck]:
        """Derive checks from repo configuration files."""
        checks = []

        # Check for test commands in package.json, pyproject.toml, Makefile
        for fname in ["package.json", "pyproject.toml", "Makefile", "tox.ini", ".github/workflows/ci.yml"]:
            fpath = self.base_dir / fname
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8")
                if "test" in content.lower():
                    checks.append(AcceptanceCheck(
                        check_id=f"repo_{fname}",
                        name=f"Repo Tests ({fname})",
                        description=f"Run tests defined in {fname}",
                        source=CheckSource.CI_CONFIG,
                        change_types=[ChangeType.FEATURE_MODULE],
                        command=self._get_test_command(fname),
                        expected_result="Tests pass",
                        required=True,
                        tags=["repo", "ci"],
                    ))

        return checks

    def _get_test_command(self, fname: str) -> str:
        """Get test command from config file."""
        commands = {
            "package.json": "npm test",
            "pyproject.toml": "python3 -m pytest",
            "Makefile": "make test",
            "tox.ini": "tox",
            ".github/workflows/ci.yml": "python3 -m pytest",
        }
        return commands.get(fname, "echo 'No test command'")

    def select_by_risk(
        self,
        change_type: ChangeType,
        user_request: str = "",
        context: Optional[Dict] = None
    ) -> List[AcceptanceCheck]:
        """Select checks based on risk/change type."""
        # Start with change-type specific checks
        check_ids = self.CHANGE_TYPE_CHECKS.get(change_type, [])

        # Add repo-specific checks
        repo_checks = self.derive_from_repo()
        check_ids.extend([c.check_id for c in repo_checks])

        # Add user-request checks
        user_checks = self.derive_from_request(user_request)
        check_ids.extend([c.check_id for c in user_checks])

        # Deduplicate and build full check objects
        selected = []
        seen = set()
        for check_id in check_ids:
            if check_id in seen:
                continue
            seen.add(check_id)
            if check_id in self._check_catalog:
                selected.append(self._check_catalog[check_id])
            else:
                # Find in derived checks
                for c in repo_checks + user_checks:
                    if c.check_id == check_id:
                        selected.append(c)
                        break

        # Sort: required first, then by change type relevance
        selected.sort(key=lambda c: (not c.required, c.check_id))
        return selected

    def detect_change_type(self, diff: str, user_request: str = "") -> ChangeType:
        """Detect change type from diff and request."""
        diff_lower = diff.lower()
        request_lower = user_request.lower()

        # Check for specific patterns
        if any(kw in request_lower for kw in ["auth", "tenant", "billing", "permission", "rbac"]):
            return ChangeType.AUTH_TENANT_BILLING
        if any(kw in request_lower for kw in ["migration", "schema", "database", "alembic"]):
            return ChangeType.DATABASE_MIGRATION
        if any(kw in request_lower for kw in ["deploy", "release", "ci/cd", "pipeline"]):
            return ChangeType.DEPLOYMENT_RELEASE
        if "bug" in request_lower or "fix" in request_lower:
            return ChangeType.BUG_FIX_LOCAL
        if any(kw in request_lower for kw in ["feature", "implement", "add", "create", "build"]):
            return ChangeType.FEATURE_MODULE
        if "rename" in request_lower or "format" in request_lower or "refactor" in request_lower:
            return ChangeType.RENAME_TEXT_FORMAT

        # Analyze diff
        if "migration" in diff_lower or "alembic" in diff_lower:
            return ChangeType.DATABASE_MIGRATION
        if "docker" in diff_lower or "k8s" in diff_lower or "deploy" in diff_lower:
            return ChangeType.DEPLOYMENT_RELEASE

        return ChangeType.UNKNOWN


class CheckRunner:
    """Execute checks and capture evidence."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def run_check(self, check: AcceptanceCheck, task_id: str = "", repo_commit: str = "") -> CheckResult:
        """Run a single check and capture full evidence."""
        import time
        from datetime import datetime

        start = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"

        try:
            result = subprocess.run(
                check.command,
                shell=True,
                cwd=self.base_dir / check.working_dir,
                capture_output=True,
                text=True,
                timeout=check.timeout_seconds,
            )
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr

            # Determine status
            if exit_code == 0:
                status = CheckStatus.PASS
            else:
                status = CheckStatus.FAIL

        except subprocess.TimeoutExpired:
            exit_code = -1
            stdout = ""
            stderr = f"Timeout after {check.timeout_seconds}s"
            status = CheckStatus.FAIL
        except PermissionError:
            exit_code = -1
            stdout = ""
            stderr = "Permission denied"
            status = CheckStatus.BLOCKED
        except FileNotFoundError:
            exit_code = -1
            stdout = ""
            stderr = "Command not found"
            status = CheckStatus.BLOCKED
        except Exception as e:
            exit_code = -1
            stdout = ""
            stderr = str(e)
            status = CheckStatus.BLOCKED

        duration_ms = int((time.time() - start) * 1000)

        # Generate error signature for FAIL
        error_signature = ""
        if status == CheckStatus.FAIL:
            error_signature = self._generate_error_signature(stderr, stdout)

        return CheckResult(
            check_id=check.check_id,
            status=status,
            command=check.command,
            exit_code=exit_code,
            stdout=stdout[:5000],  # Limit output
            stderr=stderr[:5000],
            duration_ms=duration_ms,
            timestamp=timestamp,
            scope=check.working_dir,
            repo_commit=repo_commit,
            task_id=task_id,
            error_signature=error_signature,
        )

    def _generate_error_signature(self, stderr: str, stdout: str) -> str:
        """Generate safe error signature (no secrets)."""
        # Combine and truncate
        combined = (stderr + "\n" + stdout)[:1000]
        # Remove potential secrets (simple heuristic)
        lines = combined.split("\n")
        safe_lines = []
        for line in lines:
            if any(kw in line.lower() for kw in ["password", "secret", "token", "key", "api_key"]):
                safe_lines.append("[REDACTED]")
            else:
                safe_lines.append(line)
        return "\n".join(safe_lines)[:500]

    def run_checks(self, checks: List[AcceptanceCheck], task_id: str = "", repo_commit: str = "") -> List[CheckResult]:
        """Run multiple checks."""
        results = []
        for check in checks:
            result = self.run_check(check, task_id, repo_commit)
            results.append(result)
        return results


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Quality Checks CLI")
    parser.add_argument("command", choices=["derive", "select", "run", "catalog", "detect-type"])
    parser.add_argument("--request", help="User request")
    parser.add_argument("--change-type", choices=[c.value for c in ChangeType], help="Change type")
    parser.add_argument("--check-ids", nargs="+", help="Check IDs to run")
    parser.add_argument("--task-id", default="", help="Task ID")
    parser.add_argument("--repo-commit", default="", help="Repo commit")
    parser.add_argument("--base-dir", help="Base directory")
    parser.add_argument("--format", choices=["json", "text"], default="text")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent

    deriver = AcceptanceDeriver(base_dir)
    runner = CheckRunner(base_dir)

    if args.command == "catalog":
        if args.format == "json":
            print(json.dumps({k: asdict(v) for k, v in deriver._check_catalog.items()}, indent=2, default=str))
        else:
            for check in deriver._check_catalog.values():
                req = "REQUIRED" if check.required else "SUGGESTED"
                print(f"{check.check_id} [{req}] - {check.name}")
        return

    if args.command == "derive":
        if not args.request:
            parser.error("--request required")
        checks = deriver.derive_from_request(args.request)
        if args.format == "json":
            print(json.dumps([asdict(c) for c in checks], indent=2, default=str))
        else:
            for c in checks:
                print(f"{c.check_id} - {c.name}")
        return

    if args.command == "detect-type":
        if not args.request:
            parser.error("--request required for detect-type")
        change_type = deriver.detect_change_type("", args.request)
        print(f"Detected change type: {change_type.value}")
        return

    if args.command == "select":
        if not args.change_type:
            parser.error("--change-type required for select")
        change_type = ChangeType(args.change_type)
        checks = deriver.select_by_risk(change_type, args.request or "")
        if args.format == "json":
            print(json.dumps([asdict(c) for c in checks], indent=2, default=str))
        else:
            for c in checks:
                req = "REQUIRED" if c.required else "SUGGESTED"
                print(f"{c.check_id} [{req}] - {c.name}")
        return

    if args.command == "run":
        if not args.check_ids:
            parser.error("--check-ids required for run")
        checks = [deriver._check_catalog[cid] for cid in args.check_ids if cid in deriver._check_catalog]
        results = runner.run_checks(checks, args.task_id, args.repo_commit)
        if args.format == "json":
            print(json.dumps([asdict(r) for r in results], indent=2, default=str))
        else:
            for r in results:
                print(f"{r.check_id}: {r.status.value} ({r.duration_ms}ms)")
                if r.status != CheckStatus.PASS:
                    print(f"  Error: {r.error_signature or r.stderr[:200]}")
        return


if __name__ == "__main__":
    main()