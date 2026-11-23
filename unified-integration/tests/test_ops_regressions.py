"""Regressions for the ops layer: cadence.sh, CI workflows, Dependabot."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import yaml

from helpers import REPO_DIR

CADENCE = REPO_DIR / "scripts/cadence.sh"
WORKFLOWS = REPO_DIR / ".github/workflows"
ZERO_SHA = "0" * 40


def _cadence_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ("AGENT_MEMORY_ROOT", "TASK_OBSERVER_WORKSPACE",
                        "AGENT_ENHANCEMENTS_STATE_DIR")}
    env.update(extra)
    return env


class CadenceWorkspaceTests(unittest.TestCase):
    """Weekly mode must find the workspace task-observer.py itself uses."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()

    def _weekly(self, **env):
        return subprocess.run(
            ["bash", str(CADENCE), "weekly"], capture_output=True, text=True,
            env=_cadence_env(HOME=str(self.home), **env), timeout=120)

    def test_default_follows_state_dir_not_home_agent_memory(self):
        state = self.root / "state"
        workspace = state / "memory/task-observer"
        workspace.mkdir(parents=True)
        result = self._weekly(AGENT_ENHANCEMENTS_STATE_DIR=str(state))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("not found", result.stderr)
        self.assertIn(str(workspace), result.stdout)
        self.assertNotIn(".agent-memory", result.stdout + result.stderr)

    def test_task_observer_workspace_override_wins(self):
        workspace = self.root / "explicit-ws"
        workspace.mkdir()
        result = self._weekly(
            TASK_OBSERVER_WORKSPACE=str(workspace),
            AGENT_MEMORY_ROOT=str(self.root / "unused-memory"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(workspace), result.stdout)

    def test_missing_workspace_still_reported(self):
        missing = self.root / "memory"
        result = self._weekly(AGENT_MEMORY_ROOT=str(missing))
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"not found at {missing}/task-observer", result.stderr)


class CadenceMonthlyOrderTests(unittest.TestCase):
    def test_registry_build_runs_before_library_map(self):
        text = CADENCE.read_text()
        body = text[text.index("audit_registry() {"):]
        body = body[:body.index("\n}\n")]
        build = body.index('scripts/registry.py" build')
        library_map = body.index("scripts/build-library-map.py")
        self.assertLess(build, library_map,
                        "library map reads agent-registry.json; build it first")


class CommitPolicyRangeTests(unittest.TestCase):
    """The advisory commit check must inspect PR commits, not an empty range."""

    @classmethod
    def setUpClass(cls):
        workflow = yaml.safe_load((WORKFLOWS / "ci.yml").read_text())
        cls.script = next(
            step["run"] for step in workflow["jobs"]["static-checks"]["steps"]
            if step.get("name") == "Commit message policy (advisory)")

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        self.env = env
        self._git("init", "-q", "-b", "main")
        self._git("commit", "-q", "--allow-empty", "-m", "fix: base\n\nAgent: test")
        self.base = self._git("rev-parse", "HEAD").strip()
        self._git("checkout", "-q", "-b", "topic")
        self._git("commit", "-q", "--allow-empty", "-m", "bad subject from PR")
        self.topic = self._git("rev-parse", "HEAD").strip()
        # Mirror actions/checkout on pull_request: a synthetic merge commit.
        self._git("checkout", "-q", "main")
        self._git("commit", "-q", "--allow-empty", "-m", "chore: main moved\n\nAgent: test")
        self._git("merge", "-q", "--no-ff", "--no-edit", "topic")

    def _git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True, text=True, env=self.env).stdout

    def _render(self, pr_base, before):
        expr = "${{ github.event.pull_request.base.sha || github.event.before }}"
        self.assertIn(expr, self.script)
        return self.script.replace(expr, pr_base or before)

    def _run(self, pr_base="", before=""):
        result = subprocess.run(["bash", "-c", self._render(pr_base, before)],
                                cwd=self.repo, capture_output=True, text=True,
                                env=self.env, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_pull_request_range_uses_base_sha(self):
        out = self._run(pr_base=self.base)
        self.assertIn("non-conventional subject: bad subject from PR", out)
        self.assertNotIn("Merge branch", out, "merge commit must be skipped")

    def test_push_range_uses_before(self):
        out = self._run(before=self.base)
        self.assertIn("bad subject from PR", out)

    def test_new_branch_push_falls_back(self):
        out = self._run(before=ZERO_SHA)
        self.assertIn("bad subject from PR", out)


class WorkflowHygieneTests(unittest.TestCase):
    def _workflows(self):
        return {p.name: yaml.safe_load(p.read_text())
                for p in sorted(WORKFLOWS.glob("*.yml"))}

    def test_every_job_sets_timeout(self):
        for name, workflow in self._workflows().items():
            for job_id, job in workflow["jobs"].items():
                with self.subTest(workflow=name, job=job_id):
                    self.assertIn("timeout-minutes", job)

    def test_actions_are_sha_pinned(self):
        for name, workflow in self._workflows().items():
            for job in workflow["jobs"].values():
                for step in job["steps"]:
                    if "uses" in step:
                        with self.subTest(workflow=name, uses=step["uses"]):
                            self.assertRegex(step["uses"], r"@[0-9a-f]{40}$")


class DependencyAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = WORKFLOWS / "dependency-audit.yml"
        cls.text = path.read_text()
        cls.workflow = yaml.safe_load(cls.text)
        # PyYAML reads the bare `on:` key as boolean True.
        cls.triggers = cls.workflow.get("on", cls.workflow.get(True))
        cls.commands = "\n".join(
            step.get("run", "") for job in cls.workflow["jobs"].values()
            for step in job["steps"])

    def test_scans_gate_the_build(self):
        self.assertNotRegex(self.commands, r"\|\|\s*true")
        for job in self.workflow["jobs"].values():
            for step in job["steps"]:
                self.assertNotIn("continue-on-error", step)

    def test_scans_every_lock_file(self):
        self.assertIn("-r unified-integration/requirements.txt", self.commands)
        self.assertIn("--require-hashes", self.commands)
        self.assertIn("cargo audit --file headroom/Cargo.lock", self.commands)
        self.assertIn("cargo audit --file ECC/ecc2/Cargo.lock", self.commands)
        dirs = {step.get("working-directory") for job in self.workflow["jobs"].values()
                for step in job["steps"] if "npm audit" in step.get("run", "")}
        self.assertEqual(dirs, {"mcp-servers/agent_browser", "ECC"})
        for path in ("unified-integration/requirements.txt", "headroom/Cargo.lock",
                     "ECC/ecc2/Cargo.lock", "ECC/package-lock.json",
                     "mcp-servers/agent_browser/package-lock.json"):
            self.assertTrue((REPO_DIR / path).is_file(), path)

    def test_runs_on_schedule_and_lock_changes(self):
        self.assertIn("schedule", self.triggers)
        self.assertIn("workflow_dispatch", self.triggers)
        self.assertIn("headroom/Cargo.lock", self.triggers["pull_request"]["paths"])
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})

    def test_tool_versions_are_pinned(self):
        self.assertRegex(self.commands, r"pip-audit==\d+\.\d+\.\d+")
        self.assertRegex(self.commands, r"uv==\d+\.\d+\.\d+")
        match = re.search(
            r"cargo install cargo-audit --locked --version (\d+)\.(\d+)\.(\d+)",
            self.commands)
        self.assertIsNotNone(match)
        # cargo-audit < 0.22 cannot parse the CVSS 4.0 vectors in the current
        # RustSec database and fails before scanning anything.
        self.assertGreaterEqual(tuple(map(int, match.groups()[:2])), (0, 22))
        self.assertIn("cargo audit update-db", self.commands)

    def test_cargo_scans_do_not_ignore_advisories(self):
        # Patchable advisories are fixed in the lock, not ignored.
        self.assertNotIn("--ignore", self.commands)

    def test_lock_drift_check_matches_documented_compile_command(self):
        updating = " ".join((REPO_DIR / "docs/UPDATING.md").read_text().split())
        documented = re.search(r"uv pip compile (.*?) --output-file", updating)
        self.assertIsNotNone(documented)
        flags = [f for f in documented.group(1).split() if f != "\\"]
        drift = " ".join(self.commands.replace("\\\n", " ").split())
        self.assertIn("uv pip compile", drift)
        for flag in flags:
            with self.subTest(flag=flag):
                self.assertIn(flag, drift)
        # Hashes must be recomputed, not reused from the committed lock.
        self.assertIn("/--hash=/d", drift)
        self.assertIn("diff -u", drift)


class CargoLockAdvisoryTests(unittest.TestCase):
    """Scanned Cargo locks stay at or above the patched advisory releases."""

    PATCHED = {
        "url": (2, 5, 9),       # RUSTSEC-2026-0592
        "cookie": (0, 18, 3),   # RUSTSEC-2026-0594
    }

    def test_locks_carry_patched_versions(self):
        import tomllib
        for lock in ("headroom/Cargo.lock", "ECC/ecc2/Cargo.lock"):
            packages = tomllib.loads((REPO_DIR / lock).read_text())["package"]
            for pkg in packages:
                floor = self.PATCHED.get(pkg["name"])
                if floor is None:
                    continue
                version = tuple(int(part) for part in
                                pkg["version"].split("-")[0].split(".")[:3])
                with self.subTest(lock=lock, crate=pkg["name"]):
                    self.assertGreaterEqual(version, floor)


class DependabotTests(unittest.TestCase):
    def test_owned_ecosystems_only(self):
        config = yaml.safe_load((REPO_DIR / ".github/dependabot.yml").read_text())
        self.assertEqual(config["version"], 2)
        updates = {(u["package-ecosystem"], u["directory"]) for u in config["updates"]}
        self.assertEqual(updates, {
            ("github-actions", "/"),
            ("pip", "/unified-integration"),
            ("npm", "/mcp-servers/agent_browser"),
        })
        for _, directory in updates:
            self.assertFalse(re.match(r"^/(headroom|ECC)(/|$)", directory))

    def test_pip_lock_gets_security_updates_only(self):
        # Dependabot's pip-compile cannot reproduce the uv-compiled universal
        # hashed lock, so version updates for it are disabled.
        config = yaml.safe_load((REPO_DIR / ".github/dependabot.yml").read_text())
        pip = [u for u in config["updates"] if u["package-ecosystem"] == "pip"]
        self.assertEqual(len(pip), 1)
        self.assertEqual(pip[0].get("open-pull-requests-limit"), 0)


class ContractClaimTests(unittest.TestCase):
    def test_commit_checks_described_as_advisory(self):
        text = (REPO_DIR / "CONTRACT.md").read_text()
        self.assertNotIn("Block push, require re-commit", text)
        self.assertNotIn("Codex config.yaml", text)
        self.assertIn("advisory CI warning", text)
        self.assertIn(".github/workflows/dependency-audit.yml", text)


if __name__ == "__main__":
    unittest.main()
