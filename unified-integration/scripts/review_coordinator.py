#!/usr/bin/env python3
"""
AgentEnhancements Review Coordinator — Selective independent review guidance.
Coordinates review for high-risk changes: security, data loss, migrations, release gates.
"""

import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class ReviewTrigger(Enum):
    """Triggers that require independent review."""
    SECURITY_CHANGE = "security_change"
    DATA_LOSS_RISK = "data_loss_risk"
    LARGE_MIGRATION = "large_migration"
    CROSS_MODULE_CHANGE = "cross_module_change"
    RELEASE_GATE = "release_gate"
    AUTH_CHANGE = "auth_change"
    CONFIG_CRITICAL = "config_critical"


class ReviewStatus(Enum):
    """Review status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


@dataclass
class ReviewFinding:
    """A single review finding."""
    id: str
    severity: str  # critical, high, medium, low, info
    category: str  # security, correctness, performance, maintainability
    file: str
    line: int
    description: str
    suggestion: str
    evidence: str = ""


@dataclass
class ReviewResult:
    """Result of a review."""
    review_id: str
    status: ReviewStatus
    trigger: ReviewTrigger
    reviewer: str
    findings: List[ReviewFinding]
    summary: str
    timestamp: str


class ReviewTriggerDetector:
    """Detect when review is needed based on changes."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def detect_triggers(self, diff: str, user_request: str = "", context: Optional[Dict] = None) -> List[ReviewTrigger]:
        """Detect review triggers from diff and context."""
        triggers = []
        diff_lower = diff.lower()
        request_lower = user_request.lower()

        # Security changes
        security_patterns = [
            r"auth|password|secret|token|key|credential",
            r"oauth|jwt|session|cookie|csrf",
            r"encrypt|decrypt|hash|salt|bcrypt",
            r"permission|rbac|acl|authorization",
            r"sql.*inject|xss|csrf|ssrf",
        ]
        if any(re.search(p, diff_lower) or re.search(p, request_lower) for p in security_patterns):
            triggers.append(ReviewTrigger.SECURITY_CHANGE)
            triggers.append(ReviewTrigger.AUTH_CHANGE)

        # Data loss risk
        data_loss_patterns = [
            r"drop\s+(table|column|index|database)",
            r"delete\s+from|truncate",
            r"alter\s+table.*drop",
            r"migration.*destructive",
            r"data.*loss|data.*corrupt",
        ]
        if any(re.search(p, diff_lower) for p in data_loss_patterns):
            triggers.append(ReviewTrigger.DATA_LOSS_RISK)

        # Large migration
        migration_patterns = [
            r"alembic|migration",
            r"schema.*change",
            r"create\s+table",
            r"alter\s+table",
            r"migrate",
        ]
        migration_count = sum(len(re.findall(p, diff_lower)) for p in migration_patterns)
        if migration_count >= 2:
            triggers.append(ReviewTrigger.LARGE_MIGRATION)

        # Cross-module change
        # Check if diff touches multiple directories/modules
        diff_dirs = set()
        for line in diff.split("\n"):
            if line.startswith("+++") or line.startswith("---"):
                path = line[4:].strip()
                # Skip git diff prefixes (a/, b/)
                if path.startswith(("a/", "b/")):
                    path = path[2:]
                if "/" in path:
                    diff_dirs.add(path.split("/")[0])
        if len(diff_dirs) >= 3:
            triggers.append(ReviewTrigger.CROSS_MODULE_CHANGE)

        # Release gate
        release_patterns = [
            r"version|release|deploy|publish",
            r"changelog|changelog",
            r"tag.*v\d+",
        ]
        if any(re.search(p, request_lower) for p in release_patterns):
            triggers.append(ReviewTrigger.RELEASE_GATE)

        # Config critical
        config_patterns = [
            r"config\.yaml|config\.json|\.env|settings\.py",
            r"dockerfile|docker[-\s]compose",
            r"kubernetes|k8s|helm",
            r"ci/cd|pipeline|workflow",
        ]
        if any(re.search(p, diff_lower) or re.search(p, request_lower) for p in config_patterns):
            triggers.append(ReviewTrigger.CONFIG_CRITICAL)

        return list(set(triggers))  # Deduplicate


class ReviewPackageBuilder:
    """Build review package with all context needed."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def build_package(
        self,
        task_id: str,
        diff: str,
        user_request: str,
        triggers: List[ReviewTrigger],
        check_results: List[Dict],
        context: Optional[Dict] = None
    ) -> Dict:
        """Build complete review package."""
        import time

        # Get changed files
        files = self._extract_files(diff)

        # Get relevant contracts/policies
        contracts = self._get_relevant_contracts(triggers)

        package = {
            "review_id": f"review_{task_id}_{int(time.time())}",
            "task_id": task_id,
            "triggers": [t.value for t in triggers],
            "timestamp": time.time(),
            "user_request": user_request,
            "diff_summary": self._summarize_diff(diff),
            "changed_files": files,
            "diff": diff[:50000],  # Limit size
            "check_results": check_results,
            "contracts": contracts,
            "context": context or {},
            "instructions": self._get_review_instructions(triggers),
        }

        return package

    def _extract_files(self, diff: str) -> List[Dict]:
        """Extract file changes from diff."""
        files = []
        current_file = None

        for line in diff.split("\n"):
            if line.startswith("+++") or line.startswith("---"):
                path = line[4:].strip()
                if path != "/dev/null":
                    current_file = path
            elif line.startswith("@@") and current_file:
                # Parse hunk header
                files.append({"file": current_file, "hunk": line})

        return files

    def _summarize_diff(self, diff: str) -> Dict:
        """Summarize diff statistics."""
        additions = sum(1 for line in diff.split("\n") if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in diff.split("\n") if line.startswith("-") and not line.startswith("---"))
        files_changed = len(set(line[4:].split("\t")[0] for line in diff.split("\n") if line.startswith("+++") or line.startswith("---")))

        return {
            "files_changed": files_changed,
            "additions": additions,
            "deletions": deletions,
            "net_change": additions - deletions,
        }

    def _get_relevant_contracts(self, triggers: List[ReviewTrigger]) -> Dict[str, str]:
        """Get relevant contract/policy documents."""
        contracts = {}
        contract_files = {
            ReviewTrigger.SECURITY_CHANGE: ["CONTRACT.md", "SECURITY.md"],
            ReviewTrigger.AUTH_CHANGE: ["CONTRACT.md", "SECURITY.md"],
            ReviewTrigger.DATA_LOSS_RISK: ["CONTRACT.md", "BACKUP.md"],
            ReviewTrigger.LARGE_MIGRATION: ["CONTRACT.md", "MIGRATION.md"],
            ReviewTrigger.CROSS_MODULE_CHANGE: ["CONTRACT.md", "ARCHITECTURE.md"],
            ReviewTrigger.RELEASE_GATE: ["CONTRACT.md", "RELEASE.md"],
            ReviewTrigger.CONFIG_CRITICAL: ["CONTRACT.md", "CONFIGURATION.md"],
        }

        for trigger in triggers:
            for fname in contract_files.get(trigger, []):
                fpath = self.base_dir / fname
                if fpath.exists():
                    contracts[fname] = fpath.read_text(encoding="utf-8")[:5000]

        return contracts

    def _get_review_instructions(self, triggers: List[ReviewTrigger]) -> str:
        """Get review instructions based on triggers."""
        instructions = [
            "INDEPENDENT REVIEW INSTRUCTIONS",
            "=" * 50,
            "You are reviewing this change as an independent reviewer.",
            "You receive: requirements, diff, contracts, and check evidence.",
            "You do NOT receive: implementer's narrative or justification.",
            "",
            "Evaluate each finding independently. Report:",
            "1. Correctness - does the change do what's required?",
            "2. Security - are there vulnerabilities introduced?",
            "3. Performance - any regressions or improvements?",
            "4. Maintainability - code quality, patterns, debt?",
            "5. Compliance - does it follow contracts/policies?",
            "",
        ]

        trigger_instructions = {
            ReviewTrigger.SECURITY_CHANGE: [
                "SECURITY REVIEW FOCUS:",
                "- Check for hardcoded secrets, keys, passwords",
                "- Verify authentication/authorization logic",
                "- Look for injection vulnerabilities (SQL, XSS, etc.)",
                "- Verify encryption/decryption usage",
                "- Check permission boundaries",
            ],
            ReviewTrigger.DATA_LOSS_RISK: [
                "DATA LOSS REVIEW FOCUS:",
                "- Verify destructive operations have safeguards",
                "- Check backup/rollback procedures",
                "- Confirm data migration is reversible",
                "- Validate foreign key constraints",
            ],
            ReviewTrigger.LARGE_MIGRATION: [
                "MIGRATION REVIEW FOCUS:",
                "- Verify migration is idempotent",
                "- Check rollback procedure exists",
                "- Verify schema changes match models",
                "- Confirm data integrity constraints",
            ],
            ReviewTrigger.CROSS_MODULE_CHANGE: [
                "CROSS-MODULE REVIEW FOCUS:",
                "- Verify module boundaries respected",
                "- Check for circular dependencies",
                "- Confirm API contracts maintained",
                "- Validate shared state handling",
            ],
            ReviewTrigger.RELEASE_GATE: [
                "RELEASE GATE REVIEW FOCUS:",
                "- Verify versioning follows semver",
                "- Check changelog completeness",
                "- Confirm all checks pass",
                "- Verify rollback plan exists",
            ],
        }

        for trigger in triggers:
            if trigger in trigger_instructions:
                instructions.extend(trigger_instructions[trigger])
                instructions.append("")

        return "\n".join(instructions)


class ReviewCoordinator:
    """Coordinate independent reviews for high-risk changes."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.detector = ReviewTriggerDetector(base_dir)
        self.builder = ReviewPackageBuilder(base_dir)
        self._reviews: Dict[str, ReviewResult] = {}

    def should_review(self, diff: str, user_request: str = "", context: Optional[Dict] = None) -> List[ReviewTrigger]:
        """Check if review is needed."""
        return self.detector.detect_triggers(diff, user_request, context)

    def create_review_package(
        self,
        task_id: str,
        diff: str,
        user_request: str,
        check_results: List[Dict],
        context: Optional[Dict] = None
    ) -> Dict:
        """Create review package for external reviewer."""
        triggers = self.should_review(diff, user_request, context)
        if not triggers:
            return {"review_needed": False}

        package = self.builder.build_package(
            task_id, diff, user_request, triggers, check_results, context
        )
        package["review_needed"] = True
        return package

    def submit_review(self, review_id: str, reviewer: str, findings: List[Dict], status: str, summary: str) -> ReviewResult:
        """Submit review result."""
        import time

        review_findings = [ReviewFinding(**f) for f in findings]
        review_status = ReviewStatus(status)

        result = ReviewResult(
            review_id=review_id,
            status=review_status,
            trigger=ReviewTrigger(triggers[0].value) if (triggers := self._get_triggers_for_review(review_id)) else ReviewTrigger.SECURITY_CHANGE,
            reviewer=reviewer,
            findings=review_findings,
            summary=summary,
            timestamp=time.time(),
        )

        self._reviews[review_id] = result
        return result

    def _get_triggers_for_review(self, review_id: str) -> List[ReviewTrigger]:
        """Extract triggers from review_id."""
        # Parse review_id format: review_{task_id}_{timestamp}
        return []  # Simplified

    def get_review_status(self, review_id: str) -> Optional[ReviewResult]:
        """Get review status."""
        return self._reviews.get(review_id)

    def list_pending_reviews(self) -> List[str]:
        """List pending review IDs."""
        return [
            rid for rid, r in self._reviews.items()
            if r.status == ReviewStatus.PENDING
        ]


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Review Coordinator CLI")
    parser.add_argument("command", choices=["detect", "package", "submit", "status", "list"])
    parser.add_argument("--diff", help="Git diff")
    parser.add_argument("--request", help="User request")
    parser.add_argument("--task-id", help="Task ID")
    parser.add_argument("--review-id", help="Review ID")
    parser.add_argument("--reviewer", help="Reviewer name")
    parser.add_argument("--findings", help="Findings JSON")
    parser.add_argument("--status", help="Review status")
    parser.add_argument("--summary", help="Review summary")
    parser.add_argument("--check-results", help="Check results JSON")
    parser.add_argument("--context", help="Context JSON")
    parser.add_argument("--base-dir", help="Base directory")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent

    coordinator = ReviewCoordinator(base_dir)

    if args.command == "detect":
        if not args.diff:
            parser.error("--diff required")
        triggers = coordinator.should_review(args.diff, args.request or "")
        print(json.dumps([t.value for t in triggers], indent=2))

    elif args.command == "package":
        if not args.diff or not args.task_id:
            parser.error("--diff and --task-id required")
        check_results = json.loads(args.check_results) if args.check_results else []
        context = json.loads(args.context) if args.context else None
        package = coordinator.create_review_package(
            args.task_id, args.diff, args.request or "", check_results, context
        )
        print(json.dumps(package, indent=2))

    elif args.command == "submit":
        if not args.review_id or not args.reviewer or not args.findings or not args.status:
            parser.error("--review-id, --reviewer, --findings, --status required")
        findings = json.loads(args.findings)
        coordinator.submit_review(args.review_id, args.reviewer, findings, args.status, args.summary or "")
        print(f"Review {args.review_id} submitted")

    elif args.command == "status":
        if not args.review_id:
            parser.error("--review-id required")
        result = coordinator.get_review_status(args.review_id)
        if result:
            print(json.dumps(asdict(result), indent=2, default=str))
        else:
            print(f"Review not found: {args.review_id}")

    elif args.command == "list":
        pending = coordinator.list_pending_reviews()
        print(json.dumps(pending, indent=2))


if __name__ == "__main__":
    main()