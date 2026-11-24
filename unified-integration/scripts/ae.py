#!/usr/bin/env python3
"""ae - AgentEnhancements unified CLI.

Provides:
  ae --help                    Show this help
  ae --status                  Show installation/host/observer/learning/schedule status
  ae --learning                Run one-shot evidence review and learning
  ae --schedule <expr>         Manage scheduled learning runs
  ae --schedule status         Show schedule status
  ae --schedule off            Disable scheduled learning
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import subprocess
import tempfile
import re
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
UNIFIED_DIR = SCRIPT_DIR.parent
BASE_DIR = UNIFIED_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from project_paths import memory_root

# Constants
AE_MARKER = "# AgentEnhancements scheduled learning"
SCHEDULE_STATE_DIR = memory_root() / "schedule"
SCHEDULE_STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)

# Windows Task Scheduler task name
WINDOWS_TASK_NAME = "AgentEnhancementsScheduledLearning"

def emit(data: Any, exit_code: int = 0) -> None:
    """Emit JSON output and exit."""
    if isinstance(data, (dict, list)):
        json.dump(data, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    else:
        print(data)
    sys.stdout.write("\n")
    sys.exit(exit_code)

def die(message: str, exit_code: int = 1) -> None:
    """Print error to stderr and exit."""
    print(f"[ae] {message}", file=sys.stderr)
    sys.exit(exit_code)

def run_cmd(cmd: List[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    try:
        return subprocess.run(cmd, capture_output=capture, text=True, check=False)
    except Exception as e:
        die(f"command failed: {e}", 2)

def get_installation_id() -> str:
    """Get a unique identifier for this AE installation."""
    import hashlib
    return hashlib.sha256(str(BASE_DIR).encode()).hexdigest()[:16]

def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform.startswith("win")

def _load_task_observer():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "task_observer", SCRIPT_DIR / "task-observer.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_observer_workspace() -> Path:
    """Get the Task Observer workspace path."""
    task_observer = _load_task_observer()
    return task_observer.workspace_root()

def check_observer_enabled() -> Dict[str, Any]:
    """Check if Task Observer is enabled."""
    task_observer = _load_task_observer()
    ws = task_observer.workspace_root()
    return {
        "enabled": not task_observer.is_disabled(ws),
        "workspace": str(ws),
        "open_observations": len(list((ws / "skill-observations" / "observation-log").glob("*.md"))) if (ws / "skill-observations" / "observation-log").exists() else 0
    }

def cmd_help(args: argparse.Namespace) -> None:
    """Show help."""
    help_text = """ae - AgentEnhancements unified CLI

Usage:
  ae --help                    Show this help
  ae --status                  Show installation/host/observer/learning/schedule status
  ae --learning                Run one-shot evidence review and learning
  ae --schedule <expr>         Schedule learning run (e.g., @hourly, '0 * * * *')
  ae --schedule status         Show schedule status
  ae --schedule off            Disable scheduled learning

Examples:
  ae --schedule @hourly              # Run learning every hour at minute 0
  ae --schedule '0 * * * *'          # Same as @hourly (5-field cron)
  ae --schedule '15 2 * * 1'         # Every Monday 02:15
  ae --schedule @daily               # Daily at midnight (if supported)
  ae --schedule off                  # Remove AE's scheduled job

Notes:
  - Scheduling is opt-in (default OFF). No schedule is created by setup.sh.
  - Linux: uses user crontab with AE-owned marker comments.
  - Windows: uses Task Scheduler (schtasks) - limited cron expression support.
  - Scheduled runs execute 'ae --learning' one-shot; no auto-promotion.
  - Concurrent runs are protected by file-based locking.
"""
    emit({"help": help_text.strip()})

def cmd_status(args: argparse.Namespace) -> None:
    """Show AE status."""
    # Check installation
    install_id = get_installation_id()

    # Check host bridges
    host_bridges = {}
    for host in ["claude-code", "codex", "opencode", "hermes"]:
        host_bridges[host] = "unknown"

    # Check observer
    observer = check_observer_enabled()

    # Check learning readiness
    learning_ready = observer["enabled"]

    # Check schedule
    schedule_info = get_schedule_status()

    # Blockers
    blockers = []
    if not observer["enabled"]:
        blockers.append("Task Observer disabled")
    if not schedule_info.get("supported", False):
        blockers.append("Scheduler not available on this platform")

    status = {
        "installation_id": install_id,
        "base_dir": str(BASE_DIR),
        "host_bridges": host_bridges,
        "observer": observer,
        "learning": {"ready": learning_ready},
        "schedule": schedule_info,
        "blockers": blockers,
    }
    emit(status)

def _acquire_learning_lock() -> Optional[Path]:
    """Acquire a file-based lock for learning execution.

    Returns the lock file path if acquired, None if another process holds the lock.
    """
    lock_path = SCHEDULE_STATE_DIR / "learning.lock"
    try:
        # Use O_CREAT | O_EXCL for atomic lock creation
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(f"{os.getpid()}\n{datetime.now(timezone.utc).isoformat()}\n")
        return lock_path
    except FileExistsError:
        # Lock exists - check if stale (older than 1 hour)
        try:
            content = lock_path.read_text().strip().split("\n")
            if len(content) >= 2:
                lock_time = datetime.fromisoformat(content[1].replace("Z", "+00:00"))
                if datetime.now(timezone.utc) - lock_time > timedelta(hours=1):
                    # Stale lock - remove and retry once
                    lock_path.unlink(missing_ok=True)
                    return _acquire_learning_lock()
        except Exception:
            pass
        return None
    except Exception:
        return None


def _release_learning_lock(lock_path: Optional[Path]) -> None:
    """Release the learning lock."""
    if lock_path and lock_path.exists():
        try:
            lock_path.unlink()
        except Exception:
            pass


def cmd_learning(args: argparse.Namespace) -> None:
    """Run one-shot evidence review and learning."""
    task_observer = _load_task_observer()

    # Acquire learning lock to prevent concurrent runs (MASTER_PROMPT §8.3)
    lock_path = _acquire_learning_lock()
    if lock_path is None:
        emit({
            "status": "BLOCKED",
            "reason": "Another learning process is running (lock held)",
            "evidence_reviewed": 0,
            "proposals": [],
            "staged": 0,
        })
        return

    try:
        # Preflight checks
        observer = check_observer_enabled()
        if not observer["enabled"]:
            emit({
                "status": "BLOCKED",
                "reason": "Task Observer is disabled",
                "evidence_reviewed": 0,
                "proposals": [],
                "staged": 0,
            })
            return

        # Evidence inventory - read from Task Observer
        ws = get_observer_workspace()
        log_dir = ws / "skill-observations" / "observation-log"
        updates_dir = ws / "skill-updates"

        evidence_items = []
        if log_dir.exists():
            for obs_file in sorted(log_dir.glob("*.md")):
                try:
                    content = obs_file.read_text(encoding="utf-8", errors="replace")
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            frontmatter = parts[1]
                            body = parts[2]
                            evidence_items.append({
                                "file": obs_file.name,
                                "frontmatter": frontmatter.strip(),
                                "body_preview": body.strip()[:200],
                            })
                except Exception:
                    pass

        if not evidence_items:
            emit({
                "status": "NO_NEW_EVIDENCE",
                "message": "No new evidence found in Task Observer",
                "evidence_reviewed": 0,
                "proposals": [],
                "staged": 0,
            })
            return

        # Validate evidence and group by skill
        validated = []
        skill_groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in evidence_items:
            if "title" in item["frontmatter"] and "status" in item["frontmatter"]:
                validated.append(item)
                # Extract skills from frontmatter
                fm = item["frontmatter"]
                skills = []
                for line in fm.split("\n"):
                    if line.strip().startswith("skill:"):
                        # Parse skill: [skill1, skill2]
                        skills_str = line.split(":", 1)[1].strip()
                        skills_str = skills_str.strip("[]")
                        for s in skills_str.split(","):
                            s = s.strip().strip('"\'')
                            if s:
                                skills.append(s)
                for skill in skills:
                    skill_groups.setdefault(skill, []).append(item)

        # Generate proposals per skill (first pass - no staging yet)
        proposals = []

        def extract_title(fm: str) -> str:
            for line in fm.split("\n"):
                if line.strip().startswith("title:"):
                    return line.split("title:", 1)[1].strip().strip('"\'')
            return ""

        for skill, items in skill_groups.items():
            if not skill or skill == "-":
                continue
            evidence_refs = [item["file"] for item in items]
            # Build a summary of the issues for this skill
            issues = "; ".join([extract_title(item["frontmatter"]) for item in items[:3]])
            if len(items) > 3:
                issues += f" (+{len(items) - 3} more)"

            proposal = {
                "evidence_refs": evidence_refs,
                "target": skill,
                "reason": f"Multiple observations for skill '{skill}': {issues}",
                "confidence": 0.7,
                "risk": "low",
                "expected_change": f"Update skill '{skill}' based on observed patterns",
                "test_design": f"Verify skill '{skill}' behavior with test tasks",
            }
            proposals.append(proposal)

        # Also include any observations that couldn't be grouped by skill
        ungrouped = [item for item in validated if not any(
            item["file"] in refs for refs in [p["evidence_refs"] for p in proposals]
        )]
        for item in ungrouped:
            proposals.append({
                "evidence_refs": [item["file"]],
                "target": "ungrouped",
                "reason": f"Observation without clear skill target: {extract_title(item['frontmatter'])[:80]}",
                "confidence": 0.5,
                "risk": "low",
                "expected_change": "Review manually",
                "test_design": "Manual review required",
            })

        # Second pass: stage candidates for valid skill targets
        # Skip generic/invalid targets like "capability_mapping" or "ungrouped"
        INVALID_TARGETS = {"capability_mapping", "ungrouped", "-", ""}
        staged = []

        for proposal in proposals:
            skill = proposal["target"]
            if skill in INVALID_TARGETS:
                continue

            evidence_refs = proposal["evidence_refs"]
            # Find the items for this skill to build changes description
            items = []
            for item in validated:
                if item["file"] in evidence_refs:
                    items.append(item)

            try:
                changes_lines = [f"Proposed updates based on {len(items)} observation(s):"]
                for item in items:
                    changes_lines.append(f"- {extract_title(item['frontmatter'])}")
                changes = "\n".join(changes_lines)
                stage_result = task_observer.stage_candidate(
                    root=ws,
                    skill_name=skill,
                    changes=changes,
                    source_observations=evidence_refs,
                )
                if stage_result.startswith("staged:"):
                    stage_path = stage_result.split("staged: ")[1].split(" (diff:")[0]
                    diff_path = stage_result.split("diff: ")[1].split(")")[0] if "diff:" in stage_result else ""
                    staged.append({
                        "skill": skill,
                        "stage_path": stage_path,
                        "diff_path": diff_path,
                        "observations": evidence_refs,
                    })
                    proposal["staged"] = True
                    proposal["stage_path"] = stage_path
                else:
                    # Staging refused or degraded - include in proposal as blocker
                    proposal["stage_blocker"] = stage_result
                    proposal["staged"] = False
            except Exception as e:
                proposal["stage_blocker"] = f"staging error: {type(e).__name__}: {e}"
                proposal["staged"] = False

        emit({
            "status": "COMPLETED",
            "evidence_reviewed": len(evidence_items),
            "validated": len(validated),
            "proposals": proposals,
            "staged": len(staged),
            "staged_candidates": staged,
            "message": "Learning review completed. Staged candidates require explicit approval (promote) before promotion.",
        })
    finally:
        _release_learning_lock(lock_path)

def parse_cron_expression(expr: str) -> Dict[str, Any]:
    """Parse and validate a cron expression."""
    aliases = {
        "@hourly": "0 * * * *",
        "@daily": "0 0 * * *",
        "@weekly": "0 0 * * 0",
        "@monthly": "0 0 1 * *",
        "@yearly": "0 0 1 1 *",
    }

    if expr in aliases:
        return {"valid": True, "normalized": aliases[expr], "original": expr, "is_alias": True}

    parts = expr.split()
    if len(parts) != 5:
        return {"valid": False, "error": "Cron expression must have exactly 5 fields (minute hour day-of-month month day-of-week)"}

    field_names = ["minute", "hour", "day-of-month", "month", "day-of-week"]
    ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]

    for i, (part, (min_v, max_v)) in enumerate(zip(parts, ranges)):
        if not validate_cron_field(part, min_v, max_v):
            return {"valid": False, "error": f"Invalid {field_names[i]} field: {part}"}

    return {"valid": True, "normalized": expr, "original": expr, "is_alias": False}

def validate_cron_field(field: str, min_v: int, max_v: int) -> bool:
    """Validate a single cron field."""
    if field == "*":
        return True
    if "-" in field:
        try:
            start, end = field.split("-", 1)
            start_i, end_i = int(start), int(end)
            return min_v <= start_i <= max_v and min_v <= end_i <= max_v and start_i <= end_i
        except ValueError:
            return False
    if "/" in field:
        base, step = field.split("/", 1)
        if base == "*":
            try:
                return 1 <= int(step) <= (max_v - min_v + 1)
            except ValueError:
                return False
        return False
    if "," in field:
        try:
            return all(min_v <= int(v) <= max_v for v in field.split(","))
        except ValueError:
            return False
    try:
        return min_v <= int(field) <= max_v
    except ValueError:
        return False

# ==================== Linux crontab implementation ====================

def get_crontab() -> List[str]:
    """Get current user crontab."""
    result = run_cmd(["crontab", "-l"])
    if result.returncode != 0:
        if "no crontab" in result.stderr.lower():
            return []
        die(f"failed to read crontab: {result.stderr}")
    return result.stdout.strip().split("\n") if result.stdout.strip() else []

def set_crontab(lines: List[str]) -> None:
    """Set user crontab."""
    content = "\n".join(lines) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cron", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        result = run_cmd(["crontab", tmp_path])
        if result.returncode != 0:
            die(f"failed to write crontab: {result.stderr}")
    finally:
        os.unlink(tmp_path)

def find_ae_job(crontab_lines: List[str]) -> Optional[int]:
    """Find AE's scheduled job in crontab."""
    marker = f"{AE_MARKER} {get_installation_id()}"
    for i, line in enumerate(crontab_lines):
        if marker in line:
            return i
    return None

# ==================== Windows Task Scheduler implementation ====================

def _xml_escape(text: str) -> str:
    text = text.replace("&", "&")
    text = text.replace("&", "&")
    return text

def _windows_current_user() -> str:
    """Get current Windows user as DOMAIN\\USER or USER."""
    user = os.environ.get("USERNAME") or os.getlogin()
    domain = os.environ.get("USERDOMAIN")
    return f"{domain}\\{user}" if domain else user

def _windows_task_xml(command: str, trigger_xml: str) -> str:
    """Render Task Scheduler XML for command and trigger."""
    principal = (
        f"    <UserId>{_xml_escape(_windows_current_user())}</UserId>\n"
        "    <LogonType>S4U</LogonType>\n"
        "    <RunLevel>LeastPrivilege</RunLevel>"
    )
    return (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
        "  <Triggers>\n"
        f"{trigger_xml}\n"
        "  </Triggers>\n"
        '  <Principals>\n    <Principal id="Author">\n'
        f"{principal}\n"
        "    </Principal>\n  </Principals>\n"
        "  <Settings>\n"
        "    <Hidden>true</Hidden>\n"
        "    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n"
        "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n"
        "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n"
        "    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>\n"
        "    <StartWhenAvailable>true</StartWhenAvailable>\n"
        "  </Settings>\n"
        '  <Actions Context="Author">\n'
        f"    <Exec>\n      <Command>{_xml_escape(command)}</Command>\n    </Exec>\n"
        "  </Actions>\n"
        "</Task>\n"
    )

def _cron_to_windows_trigger(cron_expr: str) -> Optional[str]:
    """Convert 5-field cron expression to Windows Task Scheduler trigger XML.

    Returns None if expression cannot be represented on Windows.
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        return None
    minute, hour, dom, month, dow = parts

    # Helper: parse time
    def parse_time(h: str, m: str) -> str:
        return f"{int(h):02d}:{int(m):02d}:00"

    # @hourly / 0 * * * *
    if minute == "0" and hour == "*" and dom == "*" and month == "*" and dow == "*":
        start = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        return (
            "    <TimeTrigger>\n"
            f"      <StartBoundary>{start}</StartBoundary>\n"
            "      <Enabled>true</Enabled>\n"
            "      <Repetition>\n"
            "        <Interval>PT1H</Interval>\n"
            "        <StopAtDurationEnd>false</StopAtDurationEnd>\n"
            "      </Repetition>\n"
            "    </TimeTrigger>"
        )

    # @daily / 0 0 * * *
    if minute == "0" and hour == "0" and dom == "*" and month == "*" and dow == "*":
        return (
            "    <TimeTrigger>\n"
            f"      <StartBoundary>T00:00:00</StartBoundary>\n"
            "      <Enabled>true</Enabled>\n"
            "      <Repetition>\n"
            "        <Interval>P1D</Interval>\n"
            "        <StopAtDurationEnd>false</StopAtDurationEnd>\n"
            "      </Repetition>\n"
            "    </TimeTrigger>"
        )

    # @weekly / 0 0 * * 0 (Sunday)
    if minute == "0" and hour == "0" and dom == "*" and month == "*" and dow in ("0", "7"):
        return (
            "    <WeeklyTrigger>\n"
            f"      <StartBoundary>T00:00:00</StartBoundary>\n"
            "      <Enabled>true</Enabled>\n"
            "      <DaysOfWeek>\n        <Sunday/>\n      </DaysOfWeek>\n"
            "      <WeeksInterval>1</WeeksInterval>\n"
            "    </WeeklyTrigger>"
        )

    # Specific day of week: 0 H * * DOW
    if minute != "*" and hour != "*" and dom == "*" and month == "*" and dow not in ("*", "0", "7"):
        # Single day of week
        dow_map = {"1": "Monday", "2": "Tuesday", "3": "Wednesday",
                   "4": "Thursday", "5": "Friday", "6": "Saturday"}
        if dow in dow_map:
            return (
                "    <WeeklyTrigger>\n"
                f"      <StartBoundary>T{int(hour):02d}:{int(minute):02d}:00</StartBoundary>\n"
                "      <Enabled>true</Enabled>\n"
                f"      <DaysOfWeek>\n        <{dow_map[dow]}/>\n      </DaysOfWeek>\n"
                "      <WeeksInterval>1</WeeksInterval>\n"
                "    </WeeklyTrigger>"
            )

    # Weekdays (1-5): 0 H * * 1-5
    if minute != "*" and hour != "*" and dom == "*" and month == "*" and dow == "1-5":
        return (
            "    <WeeklyTrigger>\n"
            f"      <StartBoundary>T{int(hour):02d}:{int(minute):02d}:00</StartBoundary>\n"
            "      <Enabled>true</Enabled>\n"
            "      <DaysOfWeek>\n"
            "        <Monday/>\n        <Tuesday/>\n        <Wednesday/>\n"
            "        <Thursday/>\n        <Friday/>\n"
            "      </DaysOfWeek>\n"
            "      <WeeksInterval>1</WeeksInterval>\n"
            "    </WeeklyTrigger>"
        )

    # @monthly / 0 0 1 * *
    if minute == "0" and hour == "0" and dom == "1" and month == "*" and dow == "*":
        return (
            "    <MonthlyTrigger>\n"
            "      <StartBoundary>T00:00:00</StartBoundary>\n"
            "      <Enabled>true</Enabled>\n"
            "      <DaysOfMonth>\n        <Day>1</Day>\n      </DaysOfMonth>\n"
            "      <Months>\n"
            "        <January/><February/><March/><April/><May/><June/>\n"
            "        <July/><August/><September/><October/><November/><December/>\n"
            "      </Months>\n"
            "    </MonthlyTrigger>"
        )

    # Specific day of month: 0 H DOM * *
    if minute != "*" and hour != "*" and dom != "*" and month == "*" and dow == "*":
        try:
            dom_int = int(dom)
            if 1 <= dom_int <= 28:  # Only 1-28 safe for all months
                return (
                    "    <MonthlyTrigger>\n"
                    f"      <StartBoundary>T{int(hour):02d}:{int(minute):02d}:00</StartBoundary>\n"
                    "      <Enabled>true</Enabled>\n"
                    f"      <DaysOfMonth>\n        <Day>{dom_int}</Day>\n      </DaysOfMonth>\n"
                    "      <Months>\n"
                    "        <January/><February/><March/><April/><May/><June/>\n"
                    "        <July/><August/><September/><October/><November/><December/>\n"
                    "      </Months>\n"
                    "    </MonthlyTrigger>"
                )
        except ValueError:
            pass

    # @yearly / 0 0 1 1 *
    if minute == "0" and hour == "0" and dom == "1" and month == "1" and dow == "*":
        return (
            "    <MonthlyDOWTrigger>\n"
            "      <StartBoundary>T00:00:00</StartBoundary>\n"
            "      <Enabled>true</Enabled>\n"
            "      <DaysOfWeek>\n        <Sunday/>\n      </DaysOfWeek>\n"
            "      <WhichWeek>First</WhichWeek>\n"
            "      <Months>\n        <January/>\n      </Months>\n"
            "    </MonthlyDOWTrigger>"
        )

    # Every N minutes: */N * * * *
    if minute.startswith("*/") and hour == "*" and dom == "*" and month == "*" and dow == "*":
        try:
            interval = int(minute[2:])
            if 1 <= interval <= 59:
                start = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                return (
                    "    <TimeTrigger>\n"
                    f"      <StartBoundary>{start}</StartBoundary>\n"
                    "      <Enabled>true</Enabled>\n"
                    "      <Repetition>\n"
                    f"        <Interval>PT{interval}M</Interval>\n"
                    "        <StopAtDurationEnd>false</StopAtDurationEnd>\n"
                    "      </Repetition>\n"
                    "    </TimeTrigger>"
                )
        except ValueError:
            pass

    # Multiple hours: 0 H1,H2 * * *
    if minute != "*" and "," in hour and dom == "*" and month == "*" and dow == "*":
        hours = [h.strip() for h in hour.split(",")]
        triggers = []
        for h in hours:
            try:
                h_int = int(h)
                if 0 <= h_int <= 23:
                    triggers.append(
                        "    <DailyTrigger>\n"
                        f"      <StartBoundary>T{h_int:02d}:{int(minute):02d}:00</StartBoundary>\n"
                        "      <Enabled>true</Enabled>\n"
                        "    </DailyTrigger>"
                    )
            except ValueError:
                return None
        if triggers:
            return "\n".join(triggers)

    # Cannot represent on Windows
    return None

def _register_windows_task(xml: str) -> None:
    """Register a Windows task from XML."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", encoding="utf-16", delete=False) as f:
        f.write(xml)
        tmp_path = f.name
    try:
        result = run_cmd(["schtasks", "/Create", "/TN", WINDOWS_TASK_NAME, "/XML", tmp_path, "/F"])
        if result.returncode != 0:
            die(f"failed to create Windows task: {result.stderr}")

        # Verify registration
        query = run_cmd(["schtasks", "/Query", "/TN", WINDOWS_TASK_NAME, "/XML"])
        if query.returncode != 0:
            die(f"failed to verify Windows task: {query.stderr}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

def _delete_windows_task() -> bool:
    """Delete the Windows task. Returns True if deleted, False if not found."""
    result = run_cmd(["schtasks", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"])
    return result.returncode == 0

def _get_windows_task_status() -> Dict[str, Any]:
    """Get Windows task status."""
    result = run_cmd(["schtasks", "/Query", "/TN", WINDOWS_TASK_NAME, "/XML"])
    if result.returncode != 0:
        return {"supported": True, "active": False}

    try:
        # Parse XML to get trigger info
        raw = result.stdout
        # Fix encoding declaration
        normalized = re.sub(
            r'<\?xml\s+version="1\.0"\s+encoding="[^"]+"\?>',
            '<?xml version="1.0"?>',
            raw,
            count=1,
        )
        task = ElementTree.fromstring(normalized)

        # Extract trigger info
        triggers = task.findall(".//{*}Trigger")
        cron_expr = "unknown"
        for trigger in triggers:
            # Try to reconstruct cron from trigger
            pass

        return {
            "supported": True,
            "active": True,
            "task_name": WINDOWS_TASK_NAME,
            "cron_expression": cron_expr,
        }
    except Exception:
        return {"supported": True, "active": True, "task_name": WINDOWS_TASK_NAME}

def get_schedule_status() -> Dict[str, Any]:
    """Get current schedule status."""
    if is_windows():
        return _get_windows_task_status()

    # Linux/Unix: use crontab
    result = run_cmd(["which", "crontab"])
    crontab_available = result.returncode == 0

    if not crontab_available:
        return {
            "supported": False,
            "reason": "crontab not available",
            "active": False,
        }

    crontab_lines = get_crontab()
    job_idx = find_ae_job(crontab_lines)

    if job_idx is not None:
        line = crontab_lines[job_idx]
        parts = line.split()
        if len(parts) >= 6:
            cron_expr = " ".join(parts[:5])
            command = " ".join(parts[6:])
            return {
                "supported": True,
                "active": True,
                "cron_expression": cron_expr,
                "command": command,
                "line_number": job_idx + 1,
            }

    return {
        "supported": True,
        "active": False,
    }

def cmd_schedule(args: argparse.Namespace) -> None:
    """Manage scheduled learning runs."""
    if not hasattr(args, "schedule") or args.schedule is None:
        emit(get_schedule_status())
        return

    expr = args.schedule

    if expr == "status":
        emit(get_schedule_status())
        return

    if expr == "off":
        if is_windows():
            deleted = _delete_windows_task()
            if deleted:
                emit({"status": "DISABLED", "message": "AE scheduled learning disabled"})
            else:
                emit({"status": "ALREADY_DISABLED", "message": "No AE scheduled job found"})
        else:
            crontab_lines = get_crontab()
            job_idx = find_ae_job(crontab_lines)
            if job_idx is not None:
                crontab_lines.pop(job_idx)
                set_crontab(crontab_lines)
                emit({"status": "DISABLED", "message": "AE scheduled learning disabled"})
            else:
                emit({"status": "ALREADY_DISABLED", "message": "No AE scheduled job found"})
        return

    parsed = parse_cron_expression(expr)
    if not parsed["valid"]:
        die(f"Invalid schedule expression: {parsed['error']}")

    if expr == "@reboot":
        die("@reboot is not supported for learning schedule")

    if len(expr.split()) == 6:
        die("6-field cron expressions (with seconds) are not supported")

    if any(c in expr for c in [";", "&", "|", "$", "`", "&&", "||"]):
        die("Shell commands in cron expression are not allowed")

    ae_cmd = f"{sys.executable} {SCRIPT_DIR / 'ae.py'} --learning"

    if is_windows():
        trigger_xml = _cron_to_windows_trigger(parsed["normalized"])
        if trigger_xml is None:
            die(f"Cron expression '{expr}' cannot be represented on Windows Task Scheduler. "
                f"Supported: @hourly, @daily, @weekly, @monthly, @yearly, "
                f"*/N * * * *, 0 H * * 1-5, 0 H * * DOW, 0 0 1-28 * *")

        xml = _windows_task_xml(ae_cmd, trigger_xml)
        _register_windows_task(xml)

        emit({
            "status": "CREATED",
            "cron_expression": parsed["normalized"],
            "original": parsed["original"],
            "command": ae_cmd,
            "platform": "windows",
        })
    else:
        # Linux/Unix: use crontab
        marker = f"{AE_MARKER} {get_installation_id()}"
        cron_line = f"{parsed['normalized']} {ae_cmd} # {marker}"

        crontab_lines = get_crontab()
        job_idx = find_ae_job(crontab_lines)

        if job_idx is not None:
            crontab_lines[job_idx] = cron_line
            action = "UPDATED"
        else:
            crontab_lines.append(cron_line)
            action = "CREATED"

        set_crontab(crontab_lines)

        emit({
            "status": action,
            "cron_expression": parsed["normalized"],
            "original": parsed["original"],
            "command": ae_cmd,
            "platform": "linux",
        })

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ae",
        description="AgentEnhancements unified CLI",
        add_help=False,
    )
    parser.add_argument("--help", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--learning", action="store_true")
    parser.add_argument("--schedule", nargs="?", const="status", metavar="EXPR")

    args = parser.parse_args()

    if args.help or (not args.status and not args.learning and args.schedule is None):
        cmd_help(args)
    elif args.status:
        cmd_status(args)
    elif args.learning:
        cmd_learning(args)
    elif args.schedule is not None:
        cmd_schedule(args)

    return 0

if __name__ == "__main__":
    import hashlib
    sys.exit(main())