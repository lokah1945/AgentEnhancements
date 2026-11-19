"""Run the registry CI build stage against controlled source and index files."""

import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml


class RegistryWorkflowTests(unittest.TestCase):
    def test_job_environment_only_uses_contexts_available_before_runner_assignment(self):
        # GitHub Contexts reference: jobs.<job_id>.env cannot use runner.*.
        allowed = {'github', 'needs', 'strategy', 'matrix', 'vars', 'secrets', 'inputs'}
        workflows = Path(__file__).resolve().parents[2] / '.github/workflows'
        for workflow in workflows.glob('*.yml'):
            doc = yaml.safe_load(workflow.read_text())
            for name, job in doc.get('jobs', {}).items():
                for key, value in job.get('env', {}).items():
                    for expression in re.findall(r'\$\{\{(.*?)\}\}', str(value)):
                        roots = set(re.findall(r'(?<![\w.])([A-Za-z_]\w*)\.', expression))
                        with self.subTest(workflow=workflow.name, job=name, variable=key):
                            self.assertLessEqual(roots, allowed)

    def test_vendor_changes_are_aggregated_before_registry_build(self):
        workflow = Path(__file__).resolve().parents[2] / ".github/workflows/registry-regeneration.yml"
        doc = yaml.safe_load(workflow.read_text())
        script = next(step["run"] for step in doc["jobs"]["regenerate-registry"]["steps"]
                      if step.get("name") == "Build capability registry")
        with tempfile.TemporaryDirectory(prefix="ae-workflow-") as directory:
            root = Path(directory)
            scripts = root / "unified-integration/scripts"
            scripts.mkdir(parents=True)
            (root / "source.txt").write_text("new source skill")
            (root / "index.txt").write_text("old source skill")
            (root / "unified-integration/setup.sh").write_text(
                '#!/bin/bash\nset -euo pipefail\ncp source.txt index.txt\n'
            )
            (scripts / "registry.py").write_text(
                'from pathlib import Path\nPath("registry.txt").write_text(Path("index.txt").read_text())\n'
            )
            env = {"PATH": os.environ["PATH"], "HOME": str(root / "home"),
                   "AGENT_MEMORY_ROOT": str(root / "memory"),
                   "XDG_CONFIG_HOME": str(root / "config"), "XDG_DATA_HOME": str(root / "data"),
                   "CODEX_HOME": str(root / "codex")}
            result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((root / "index.txt").read_text(), "new source skill")
            self.assertEqual((root / "registry.txt").read_text(), "new source skill")


if __name__ == "__main__":
    unittest.main()
