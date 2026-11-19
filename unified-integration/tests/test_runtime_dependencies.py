"""Existing runtimes must refresh dependency constraints after an AE update."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import UI_DIR


class RuntimeDependencyRefreshTests(unittest.TestCase):
    def test_mcp_smoke_uses_the_prepared_project_runtime(self):
        with tempfile.TemporaryDirectory(prefix='ae-mcp-runtime-') as temp:
            root = Path(temp)
            home = root / 'home'
            home.mkdir()
            claude = home / '.claude'
            claude.mkdir()
            (claude / '.claude.json').write_text(
                '{"mcpServers":{"agent-enhancements":{"command":"fixture"}}}')
            data = root / 'custom-data'
            python = data / 'runtime/venv/bin/python'
            python.parent.mkdir(parents=True)
            marker = root / 'selected-runtime'
            python.write_text('#!' + sys.executable + '\nimport os,sys\n'
                              'from pathlib import Path\n'
                              'Path(os.environ["AE_TEST_RUNTIME_MARKER"]).touch()\n'
                              'os.execv(sys.executable,[sys.executable]+sys.argv[1:])\n')
            python.chmod(0o755)
            tools = root / 'bin'
            tools.mkdir()
            default_python = tools / 'python3'
            default_python.write_text('#!/bin/sh\nexit 3\n')
            default_python.chmod(0o755)
            env = dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(data),
                       AGENT_ENHANCEMENTS_STATE_DIR=str(data),
                       CLAUDE_CONFIG_DIR=str(claude),
                       AGENT_ENHANCEMENTS_API_FILE=str(root / 'missing-api.json'),
                       AE_TEST_RUNTIME_MARKER=str(marker),
                       PATH=str(tools)+os.pathsep+os.environ['PATH'])
            result = subprocess.run(['bash', str(UI_DIR / 'scripts/mcp-test.sh'),
                                     '--server', 'embeddings-mcp'], env=env,
                                    text=True, capture_output=True, timeout=20)
            self.assertTrue(marker.is_file(), 'mcp-test ignored the prepared project runtime')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_filelock_runtime_includes_published_security_fixes(self):
        from importlib.metadata import version
        installed = tuple(int(part) for part in version('filelock').split('.')[:3])
        self.assertGreaterEqual(installed, (4, 2, 1))

    def test_importable_legacy_environment_refreshes_once_per_requirements_change(self):
        with tempfile.TemporaryDirectory(prefix='ae-dependency-refresh-') as temp:
            root = Path(temp)
            ui = root / 'repo/unified-integration'
            (ui / 'scripts').mkdir(parents=True)
            script = ui / 'scripts/setup-mcp.sh'
            shutil.copyfile(UI_DIR / 'scripts/setup-mcp.sh', script)
            shutil.copyfile(UI_DIR / 'scripts/project_paths.py', script.parent / 'project_paths.py')
            requirements = ui / 'requirements.txt'
            requirements.write_text('filelock>=4.2.1,<5\n')
            data = root / 'data'
            python = data / 'runtime/venv/bin/python'
            python.parent.mkdir(parents=True)
            python.write_text('#!' + sys.executable + '\nimport os,sys\n'
                              'if len(sys.argv)>2 and sys.argv[1]=="-c" and '
                              'sys.argv[2].startswith("import mcp"):\n    sys.exit(0)\n'
                              'os.execv(sys.executable,[sys.executable]+sys.argv[1:])\n')
            python.chmod(0o755)
            tools = root / 'bin'
            tools.mkdir()
            log = root / 'installer-calls'
            uv = tools / 'uv'
            uv.write_text('#!/bin/sh\nprintf "installed\\n" >> "$AE_TEST_INSTALL_LOG"\n')
            uv.chmod(0o755)
            env = dict(os.environ, HOME=str(root / 'home'), XDG_DATA_HOME=str(data),
                       AGENT_ENHANCEMENTS_STATE_DIR=str(data),
                       AE_TEST_INSTALL_LOG=str(log), PATH=str(tools)+os.pathsep+os.environ['PATH'])

            def prepare():
                result = subprocess.run(['bash', str(script), '--prepare'], env=env,
                                        text=True, capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)

            prepare()
            self.assertTrue(log.is_file(), 'import-only check accepted stale dependencies')
            self.assertEqual(len(log.read_text().splitlines()), 1)
            prepare()
            self.assertEqual(len(log.read_text().splitlines()), 1)
            requirements.write_text('filelock>=4.2.2,<5\n')
            prepare()
            self.assertEqual(len(log.read_text().splitlines()), 2)


if __name__ == '__main__':
    unittest.main()
