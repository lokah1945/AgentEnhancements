#!/usr/bin/env python3
"""Mock schtasks.exe adapter for testing Windows Task Scheduler integration.

This fixture provides mock schtasks output for testing cron expression
translation and Windows scheduling logic without requiring Windows.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Mock schtasks output templates
SCHTASKS_QUERY_XML_TEMPLATE = '''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>{date}</Date>
    <Author>{author}</Author>
    <Description>AE scheduled learning</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>{start_boundary}</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>{interval}</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <LogonType>ServiceAccount</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <Hidden>true</Hidden>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <StartWhenAvailable>true</StartWhenAvailable>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>python.exe</Command>
      <Arguments>ae.py --learning</Arguments>
    </Exec>
  </Actions>
</Task>'''

SCHTASKS_LIST_OUTPUT = """TaskName                                 Next Run Time          Status
========================================= ====================== ===============
AE-Scheduled-Learning                    2026-11-24 2:00:00 AM  Ready
"""

SCHTASKS_QUERY_OUTPUT = """Folder: \\
HostName:                             DESKTOP-ABC123
TaskName:                               AE-Scheduled-Learning
Next Run Time:                          2026-11-24 2:00:00 AM
Status:                                 Ready
Logon Mode:                             Interactive/Background
Last Run Time:                          N/A
Last Result:                            0
Author:                                 DESKTOP-ABC123\\User
Task To Run:                            python.exe ae.py --learning
Start In:                               C:\\AgentEnhancements
Comment:                                AE scheduled learning
Scheduled Task State:                   Enabled
Idle Time:                              Disabled
Power Management:                       Stop If On Batteries, No Start On Batteries
Run Only If Network Available:          False
Run As User:                            SYSTEM
Delete Task If Not Rescheduled:         False
Stop Task If Runs Longer Than:          0
Stop If On Batteries:                   True
Repeat:                                 Every: 1 Hour(s), 0 Minute(s)
Repeat Until:                           Duration: Indefinitely
Repeat Stop If Still Running:           False
"""

SCHTASKS_DELETE_OUTPUT = "SUCCESS: The scheduled task \"AE-Scheduled-Learning\" was successfully deleted."

SCHTASKS_CREATE_OUTPUT = "SUCCESS: The scheduled task \"AE-Scheduled-Learning\" has successfully been created."

SCHTASKS_CHANGE_ENABLE_OUTPUT = "SUCCESS: The scheduled task \"AE-Scheduled-Learning\" has successfully been changed."

SCHTASKS_CHANGE_DISABLE_OUTPUT = "SUCCESS: The scheduled task \"AE-Scheduled-Learning\" has successfully been changed."

SCHTASKS_END_OUTPUT = "SUCCESS: The scheduled task \"AE-Scheduled-Learning\" has successfully been ended."

SCHTASKS_RUN_OUTPUT = "SUCCESS: Attempted to run the scheduled task \"AE-Scheduled-Learning\"."

SCHTASKS_NOT_FOUND = """ERROR: The system cannot find the file specified."""


class MockSchtasks:
    """Mock schtasks.exe for testing Windows scheduling."""

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.current_time = datetime.now()

    def add_task(self, name: str, command: str, trigger_type: str = "daily",
                 interval: str = "PT1H", start_boundary: Optional[str] = None):
        """Add a mock task."""
        if start_boundary is None:
            start_boundary = self.current_time.strftime("%Y-%m-%dT%H:%M:%S")

        self.tasks[name] = {
            "name": name,
            "command": command,
            "trigger_type": trigger_type,
            "interval": interval,
            "start_boundary": start_boundary,
            "enabled": True,
            "last_run": None,
            "last_result": 0,
        }

    def run(self, args: List[str]) -> Dict[str, Any]:
        """Mock schtasks execution."""
        if len(args) < 2:
            return {"returncode": 1, "stdout": "", "stderr": "Invalid arguments"}

        subcommand = args[1]

        if subcommand == "/Query":
            return self._handle_query(args)
        elif subcommand == "/Create":
            return self._handle_create(args)
        elif subcommand == "/Delete":
            return self._handle_delete(args)
        elif subcommand == "/Change":
            return self._handle_change(args)
        elif subcommand == "/End":
            return self._handle_end(args)
        elif subcommand == "/Run":
            return self._handle_run(args)
        elif subcommand == "/XML":
            return self._handle_xml(args)

        return {"returncode": 1, "stdout": "", "stderr": f"Unknown subcommand: {subcommand}"}

    def _handle_query(self, args: List[str]) -> Dict[str, Any]:
        """Handle schtasks /Query."""
        tn_idx = args.index("/TN") if "/TN" in args else -1
        if tn_idx == -1 or tn_idx + 1 >= len(args):
            return {"returncode": 1, "stdout": "", "stderr": "Missing /TN argument"}

        task_name = args[tn_idx + 1]

        if task_name not in self.tasks:
            return {"returncode": 1, "stdout": "", "stderr": SCHTASKS_NOT_FOUND}

        task = self.tasks[task_name]
        if "/XML" in args:
            xml = SCHTASKS_QUERY_XML_TEMPLATE.format(
                date=self.current_time.strftime("%Y-%m-%d"),
                author="DESKTOP-ABC123\\User",
                start_boundary=task["start_boundary"],
                interval=task["interval"],
            )
            return {"returncode": 0, "stdout": xml, "stderr": ""}

        return {"returncode": 0, "stdout": SCHTASKS_QUERY_OUTPUT, "stderr": ""}

    def _handle_create(self, args: List[str]) -> Dict[str, Any]:
        """Handle schtasks /Create."""
        # Parse XML file
        xml_idx = args.index("/XML") if "/XML" in args else -1
        tn_idx = args.index("/TN") if "/TN" in args else -1

        if xml_idx == -1 or tn_idx == -1:
            return {"returncode": 1, "stdout": "", "stderr": "Missing /XML or /TN argument"}

        xml_file = args[xml_idx + 1]
        task_name = args[tn_idx + 1]

        # In real implementation, would parse XML
        # For mock, just create a basic task
        self.tasks[task_name] = {
            "name": task_name,
            "command": "python.exe ae.py --learning",
            "trigger_type": "daily",
            "interval": "PT1H",
            "start_boundary": self.current_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "enabled": True,
            "last_run": None,
            "last_result": 0,
        }

        return {"returncode": 0, "stdout": SCHTASKS_CREATE_OUTPUT, "stderr": ""}

    def _handle_delete(self, args: List[str]) -> Dict[str, Any]:
        """Handle schtasks /Delete."""
        tn_idx = args.index("/TN") if "/TN" in args else -1
        if tn_idx == -1 or tn_idx + 1 >= len(args):
            return {"returncode": 1, "stdout": "", "stderr": "Missing /TN argument"}

        task_name = args[tn_idx + 1]
        force = "/F" in args

        if task_name not in self.tasks:
            if force:
                return {"returncode": 0, "stdout": SCHTASKS_DELETE_OUTPUT, "stderr": ""}
            return {"returncode": 1, "stdout": "", "stderr": SCHTASKS_NOT_FOUND}

        del self.tasks[task_name]
        return {"returncode": 0, "stdout": SCHTASKS_DELETE_OUTPUT, "stderr": ""}

    def _handle_change(self, args: List[str]) -> Dict[str, Any]:
        """Handle schtasks /Change."""
        tn_idx = args.index("/TN") if "/TN" in args else -1
        if tn_idx == -1 or tn_idx + 1 >= len(args):
            return {"returncode": 1, "stdout": "", "stderr": "Missing /TN argument"}

        task_name = args[tn_idx + 1]

        if task_name not in self.tasks:
            return {"returncode": 1, "stdout": "", "stderr": SCHTASKS_NOT_FOUND}

        if "/ENABLE" in args:
            self.tasks[task_name]["enabled"] = True
            return {"returncode": 0, "stdout": SCHTASKS_CHANGE_ENABLE_OUTPUT, "stderr": ""}
        elif "/DISABLE" in args:
            self.tasks[task_name]["enabled"] = False
            return {"returncode": 0, "stdout": SCHTASKS_CHANGE_DISABLE_OUTPUT, "stderr": ""}

        return {"returncode": 1, "stdout": "", "stderr": "Missing /ENABLE or /DISABLE"}

    def _handle_end(self, args: List[str]) -> Dict[str, Any]:
        """Handle schtasks /End."""
        tn_idx = args.index("/TN") if "/TN" in args else -1
        if tn_idx == -1 or tn_idx + 1 >= len(args):
            return {"returncode": 1, "stdout": "", "stderr": "Missing /TN argument"}

        task_name = args[tn_idx + 1]

        if task_name not in self.tasks:
            return {"returncode": 1, "stdout": "", "stderr": SCHTASKS_NOT_FOUND}

        return {"returncode": 0, "stdout": SCHTASKS_END_OUTPUT, "stderr": ""}

    def _handle_run(self, args: List[str]) -> Dict[str, Any]:
        """Handle schtasks /Run."""
        tn_idx = args.index("/TN") if "/TN" in args else -1
        if tn_idx == -1 or tn_idx + 1 >= len(args):
            return {"returncode": 1, "stdout": "", "stderr": "Missing /TN argument"}

        task_name = args[tn_idx + 1]

        if task_name not in self.tasks:
            return {"returncode": 1, "stdout": "", "stderr": SCHTASKS_NOT_FOUND}

        self.tasks[task_name]["last_run"] = self.current_time.isoformat()
        self.tasks[task_name]["last_result"] = 0

        return {"returncode": 0, "stdout": SCHTASKS_RUN_OUTPUT, "stderr": ""}

    def _handle_xml(self, args: List[str]) -> Dict[str, Any]:
        """Handle schtasks /Query /TN name /XML."""
        return self._handle_query(args)


# Pre-defined test cases for cron expression translation
CRON_TO_SCHTASKS_TESTS = [
    {
        "name": "hourly",
        "cron": "@hourly",
        "cron_normalized": "0 * * * *",
        "expected_trigger": {
            "type": "TimeTrigger",
            "repetition_interval": "PT1H",
            "start_boundary": "any",  # Any valid start time
        },
        "description": "Run at minute 0 every hour"
    },
    {
        "name": "daily_midnight",
        "cron": "@daily",
        "cron_normalized": "0 0 * * *",
        "expected_trigger": {
            "type": "TimeTrigger",
            "repetition_interval": "P1D",
            "start_boundary": "T00:00:00",
        },
        "description": "Run daily at midnight"
    },
    {
        "name": "weekly_monday",
        "cron": "0 2 * * 1",
        "cron_normalized": "0 2 * * 1",
        "expected_trigger": {
            "type": "WeeklyTrigger",
            "days_of_week": ["Monday"],
            "start_boundary": "T02:00:00",
        },
        "description": "Run every Monday at 2:00 AM"
    },
    {
        "name": "monthly_first",
        "cron": "@monthly",
        "cron_normalized": "0 0 1 * *",
        "expected_trigger": {
            "type": "MonthlyTrigger",
            "days_of_month": [1],
            "start_boundary": "T00:00:00",
        },
        "description": "Run on the 1st of every month at midnight"
    },
    {
        "name": "yearly",
        "cron": "@yearly",
        "cron_normalized": "0 0 1 1 *",
        "expected_trigger": {
            "type": "MonthlyTrigger",
            "months": ["January"],
            "days_of_month": [1],
            "start_boundary": "T00:00:00",
        },
        "description": "Run yearly on January 1st at midnight"
    },
    {
        "name": "every_15_minutes",
        "cron": "*/15 * * * *",
        "cron_normalized": "*/15 * * * *",
        "expected_trigger": {
            "type": "TimeTrigger",
            "repetition_interval": "PT15M",
            "start_boundary": "any",
        },
        "description": "Run every 15 minutes"
    },
    {
        "name": "every_30_minutes",
        "cron": "*/30 * * * *",
        "cron_normalized": "*/30 * * * *",
        "expected_trigger": {
            "type": "TimeTrigger",
            "repetition_interval": "PT30M",
            "start_boundary": "any",
        },
        "description": "Run every 30 minutes"
    },
    {
        "name": "daily_6am_6pm",
        "cron": "0 6,18 * * *",
        "cron_normalized": "0 6,18 * * *",
        "expected_trigger": {
            "type": "MultipleTriggers",
            "triggers": [
                {"type": "DailyTrigger", "start_boundary": "T06:00:00"},
                {"type": "DailyTrigger", "start_boundary": "T18:00:00"},
            ],
        },
        "description": "Run daily at 6:00 AM and 6:00 PM"
    },
    {
        "name": "weekdays_9am",
        "cron": "0 9 * * 1-5",
        "cron_normalized": "0 9 * * 1-5",
        "expected_trigger": {
            "type": "WeeklyTrigger",
            "days_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "start_boundary": "T09:00:00",
        },
        "description": "Run weekdays at 9:00 AM"
    },
    {
        "name": "specific_day",
        "cron": "30 14 15 * *",
        "cron_normalized": "30 14 15 * *",
        "expected_trigger": {
            "type": "MonthlyTrigger",
            "days_of_month": [15],
            "start_boundary": "T14:30:00",
        },
        "description": "Run on the 15th of every month at 2:30 PM"
    },
]


# Cron expressions NOT representable in Windows Task Scheduler
UNSUPPORTED_CRON_EXPRESSIONS = [
    {
        "expression": "*/7 * * * *",
        "reason": "7-minute intervals not representable as ISO 8601 duration (PT7M is valid but schtasks has minimum 1 minute)",
        "workaround": "Use */5 or */10 instead",
    },
    {
        "expression": "0 0 31 * *",
        "reason": "Day 31 doesn't exist in all months; Windows MonthlyTrigger requires valid days for all months",
        "workaround": "Use '0 0 28 * *' or last day of month logic",
    },
    {
        "expression": "0 0 L * *",
        "reason": "Last day of month (L) not supported in Windows Task Scheduler",
        "workaround": "Use monthly trigger with specific day or PowerShell script to calculate",
    },
    {
        "expression": "0 0 * * 1#2",
        "reason": "Nth weekday of month (1#2 = 2nd Monday) not supported",
        "workaround": "Use MonthlyDOWTrigger with WhichWeek=Second",
    },
    {
        "expression": "0 0 1W * *",
        "reason": "Nearest weekday (1W) not supported",
        "workaround": "Manual calculation needed",
    },
    {
        "expression": "0 0 1/2 * *",
        "reason": "Step values in day-of-month (every 2 days) not directly supported",
        "workaround": "Use multiple triggers or daily with condition",
    },
    {
        "expression": "@reboot",
        "reason": "Boot trigger is supported but AE explicitly rejects it for learning schedule",
        "workaround": "Use BootTrigger in Task Scheduler XML directly",
    },
    {
        "expression": "0 0 * * * *",
        "reason": "6-field cron (with seconds) not supported",
        "workaround": "Use 5-field cron",
    },
]


def main():
    """Output test fixtures as JSON."""
    fixture = {
        "mock_schtasks": {
            "query_xml_template": SCHTASKS_QUERY_XML_TEMPLATE,
            "list_output": SCHTASKS_LIST_OUTPUT,
            "query_output": SCHTASKS_QUERY_OUTPUT,
            "delete_output": SCHTASKS_DELETE_OUTPUT,
            "create_output": SCHTASKS_CREATE_OUTPUT,
            "change_enable_output": SCHTASKS_CHANGE_ENABLE_OUTPUT,
            "change_disable_output": SCHTASKS_CHANGE_DISABLE_OUTPUT,
            "end_output": SCHTASKS_END_OUTPUT,
            "run_output": SCHTASKS_RUN_OUTPUT,
            "not_found": SCHTASKS_NOT_FOUND,
        },
        "cron_to_schtasks_tests": CRON_TO_SCHTASKS_TESTS,
        "unsupported_cron_expressions": UNSUPPORTED_CRON_EXPRESSIONS,
    }

    json.dump(fixture, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()