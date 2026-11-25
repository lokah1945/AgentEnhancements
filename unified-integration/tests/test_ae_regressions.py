"""Regression coverage for the ae CLI scheduler and Windows XML bridge.

All tests use isolated state roots; no crontab, Task Scheduler or network is
touched. The module is registered in run-tests.py so CI exercises it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS = TESTS_DIR.parent / "scripts"
AE_SCRIPT = SCRIPTS / "ae.py"


class AeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = {
            "AGENT_MEMORY_ROOT": str(self.root / "memory"),
            "AGENT_ENHANCEMENTS_STATE_DIR": str(self.root / "state"),
            "AGENT_ENHANCEMENTS_API_FILE": str(self.root / "ui.api.json"),
            "HOME": str(self.root / "home"),
        }
        patcher = mock.patch.dict(os.environ, self.env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.name = "ae_regression_%d" % id(self)
        sys.modules.pop(self.name, None)
        spec = importlib.util.spec_from_file_location(self.name, AE_SCRIPT)
        self.ae = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.ae)
        self.addCleanup(sys.modules.pop, self.name, None)

    @staticmethod
    def parse_xml(text: str):
        from xml.etree import ElementTree
        normalized = re.sub(
            r'<\?xml\s+version="1\.0"\s+encoding="[^"]+"\?>',
            '<?xml version="1.0"?>', text, count=1,
        )
        return ElementTree.fromstring(normalized)


class XmlEscapeTests(AeCase):
    def test_xml_escape_escapes_five_entities(self):
        self.assertEqual(self.ae._xml_escape('&<>"\''),
                         "&amp;&lt;&gt;&quot;&apos;")
        self.assertEqual(self.ae._xml_escape("&amp;"), "&amp;amp;")

    def test_windows_task_xml_well_formed_with_special_chars(self):
        user = 'DOM\\u&<>"\''
        command = 'C:\\Python\\python.exe "C:\\AE dir\\ae.py" --learning'
        with mock.patch.object(self.ae, "_windows_current_user", return_value=user):
            xml = self.ae._windows_task_xml(command, "    <TimeTrigger/>", "0 0 * * *")
        task = self.parse_xml(xml)
        self.assertEqual(task.findtext(".//{*}Principal/{*}UserId"), user)
        self.assertEqual(task.findtext(".//{*}Exec/{*}Command"),
                         "C:\\Python\\python.exe")
        self.assertIn("ae.py", task.findtext(".//{*}Exec/{*}Arguments"))

    def test_windows_status_reports_cron_expression(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-16"?>'
            '<Task><RegistrationInfo><Description>AE cron: 15 2 * * 1'
            '</Description></RegistrationInfo><Triggers><WeeklyTrigger/>'
            '</Triggers></Task>'
        )
        with mock.patch.object(self.ae, "is_windows", return_value=True), \
             mock.patch.object(self.ae, "run_cmd", return_value=types.SimpleNamespace(
                 returncode=0, stdout=xml, stderr="")):
            status = self.ae.get_schedule_status()
        self.assertEqual(status["cron_expression"], "15 2 * * 1")

    def test_windows_status_without_description_is_unknown(self):
        xml = '<Task><Triggers><WeeklyTrigger/></Triggers></Task>'
        with mock.patch.object(self.ae, "is_windows", return_value=True), \
             mock.patch.object(self.ae, "run_cmd", return_value=types.SimpleNamespace(
                 returncode=0, stdout=xml, stderr="")):
            status = self.ae.get_schedule_status()
        self.assertEqual(status["cron_expression"], "unknown")


class WindowsTriggerTests(AeCase):
    def test_yearly_uses_monthly_january_trigger(self):
        trigger = self.ae._cron_to_windows_trigger("0 0 1 1 *")
        self.assertIn("<MonthlyTrigger>", trigger)
        self.assertIn("<January/>", trigger)
        self.assertIn("<Day>1</Day>", trigger)
        self.assertNotIn("MonthlyDOWTrigger", trigger)

    def test_sunday_time_has_windows_trigger(self):
        for expression in ("15 2 * * 0", "15 2 * * 7"):
            trigger = self.ae._cron_to_windows_trigger(expression)
            self.assertIsNotNone(trigger, expression)
            self.assertIn("T02:15:00", trigger)
            self.assertIn("<Sunday/>", trigger)


class LearningLockTests(AeCase):
    def test_corrupt_lock_self_heals(self):
        lock = self.ae.SCHEDULE_STATE_DIR / "learning.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("12345\n(not-a-date)\n", encoding="utf-8")
        self.assertEqual(self.ae._acquire_learning_lock(), lock)
        self.assertIsNone(self.ae._acquire_learning_lock())


if __name__ == "__main__":
    unittest.main()
