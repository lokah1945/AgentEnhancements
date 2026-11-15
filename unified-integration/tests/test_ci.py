"""Exercise the actual workflow scripts against isolated CI inputs."""

import json
import os
from pathlib import Path
import shlex
import tempfile
import unittest

import yaml

from helpers import REPO_DIR, run


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workflow = yaml.safe_load((REPO_DIR / ".github/workflows/ci.yml").read_text())
        cls.ecc_check = next(
            step["run"] for step in workflow["jobs"]["ecc-tests"]["steps"]
            if step.get("name") == "Run ECC tests"
        )
        cls.mcp_check = next(
            step["run"] for step in workflow["jobs"]["mcp-servers"]["steps"]
            if step.get("name") == "Run the MCP regression module (offline mode)"
        )
        cls.steps = workflow["jobs"]["static-checks"]["steps"]
        cls.shell_steps = [
            step for job in workflow["jobs"].values() for step in job["steps"]
            if "run" in step
        ]
        cls.json_check = next(
            step["run"] for step in cls.steps
            if step.get("name") == "JSON validity of the skills index and friends"
        )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for directory in ("unified-integration", "scripts", "plugin-catalog", "skills"):
            (self.root / directory).mkdir()
        (self.root / "skills/manifest.json").write_text(json.dumps({}))
        (self.root / "unified-integration/index.json").write_text(json.dumps({}))

    def test_workflow_shell_steps_parse(self):
        for step in self.shell_steps:
            with self.subTest(step=step["name"]):
                rc, _, err = run(["bash", "-n"], input_text=step["run"])
                self.assertEqual(rc, 0, err)

    def test_json_check_accepts_valid_owned_files(self):
        rc, out, err = run(["bash", "-e", "-c", self.json_check], cwd=self.root)
        self.assertEqual(rc, 0, out + err)

    def test_json_check_rejects_invalid_owned_file(self):
        (self.root / "plugin-catalog/broken.json").write_text("{broken")
        rc, out, err = run(["bash", "-e", "-c", self.json_check], cwd=self.root)
        self.assertNotEqual(rc, 0, out + err)
        self.assertIn("invalid JSON", out)

    def test_json_check_excludes_dependencies(self):
        directory = self.root / "scripts/node_modules/example"
        directory.mkdir(parents=True)
        (directory / "fixture.json").write_text("{not project JSON")
        rc, out, err = run(["bash", "-e", "-c", self.json_check], cwd=self.root)
        self.assertEqual(rc, 0, out + err)

    def test_ecc_mutating_and_timing_suites_are_serial(self):
        tests = self.root / "tests/ci"
        tests.mkdir(parents=True)
        for name, content in (
            ("build.test.js", "build-opencode"),
            ("rename.test.js", ".backup-"),
            ("dist.test.js", "dist.backup"),
            ("timing.test.js", "time budget"),
            ("ordinary.test.js", "independent test"),
        ):
            (tests / name).write_text(content)
        binaries = self.root / "bin"
        binaries.mkdir()
        node = binaries / "node"
        node.write_text(
            '#!/usr/bin/env python3\nimport json, os\n'
            'print(json.dumps({key: os.environ.get(key) for key in '
            '("ECC_TEST_SERIAL", "ECC_TEST_JOBS")}))\n'
        )
        node.chmod(0o755)
        rc, out, err = run(
            ["bash", "-e", "-o", "pipefail", "-c", self.ecc_check],
            cwd=self.root, env={"PATH": str(binaries) + os.pathsep + os.environ["PATH"]},
        )
        self.assertEqual(rc, 0, err)
        settings = json.loads(out)
        self.assertEqual(settings["ECC_TEST_JOBS"], "4")
        self.assertEqual(
            settings["ECC_TEST_SERIAL"].split(","),
            ["ci/build.test.js", "ci/dist.test.js", "ci/rename.test.js", "ci/timing.test.js"],
        )

    def test_mcp_regression_uses_prepared_runtime(self):
        runtime = self.root / "runtime/bin/python"
        runtime.parent.mkdir(parents=True)
        runtime.write_text('#!/bin/bash\nprintf "prepared MCP runtime\\n"\n')
        runtime.chmod(0o755)
        scripts = self.root / "unified-integration/scripts"
        scripts.mkdir()
        (scripts / "setup-mcp.sh").write_text(
            '#!/bin/bash\n[ "$1" = "--prepare" ] || exit 2\n'
            f'printf "%s\\n" {shlex.quote(str(runtime))}\n'
        )
        rc, out, err = run(
            ["bash", "-e", "-o", "pipefail", "-c", self.mcp_check], cwd=self.root
        )
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(out.strip(), "prepared MCP runtime")
