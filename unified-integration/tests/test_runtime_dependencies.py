"""Existing runtimes must refresh dependency constraints after an AE update."""
import json
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

    def test_prepare_refresh_rollback_and_concurrent_reuse(self):
        with tempfile.TemporaryDirectory(prefix='ae-dependency-refresh-') as temp:
            root = Path(temp)
            ui = root / 'repo/unified-integration'
            (ui / 'scripts').mkdir(parents=True)
            script = ui / 'scripts/setup-mcp.sh'
            for name in ('setup-mcp.sh', 'project_paths.py', 'runtime_dependencies.py'):
                shutil.copyfile(UI_DIR / 'scripts' / name, script.parent / name)
            requirements = ui / 'requirements.txt'
            requirements.write_text('filelock>=4.2.1,<5\n')
            check = ui / 'mcp-servers/check-protocol.py'
            check.parent.mkdir()
            check.write_text('print("fixture healthy")\n')
            data = root / 'data'
            python = data / 'runtime/venv/bin/python'
            python.parent.mkdir(parents=True)
            python.write_text('#!/bin/sh\nprintf \'{}\\n\'\n')
            python.chmod(0o755)
            tools = root / 'bin'
            tools.mkdir()
            log = root / 'installer-calls'
            uv = tools / 'uv'
            uv.write_text('#!' + sys.executable + '\n'
                          'import os, sys\nfrom pathlib import Path\n'
                          'if sys.argv[1] == "venv":\n'
                          '    target = Path(sys.argv[-1]) / "bin/python"\n'
                          '    target.parent.mkdir()\n'
                          f'    target.write_text({python.read_text()!r})\n'
                          '    target.chmod(0o700)\n'
                          'if sys.argv[1:3] == ["pip", "install"]:\n'
                          '    with Path(os.environ["AE_TEST_INSTALL_LOG"]).open("a") as log:\n'
                          '        log.write("installed\\n")\n'
                          '    if "invalid" in Path(sys.argv[-1]).read_text():\n'
                          '        sys.exit(42)\n')
            uv.chmod(0o755)
            env = dict(os.environ, HOME=str(root / 'home'), XDG_DATA_HOME=str(data),
                       AGENT_ENHANCEMENTS_STATE_DIR=str(data),
                       AE_TEST_INSTALL_LOG=str(log), PATH=str(tools)+os.pathsep+os.environ['PATH'])

            def setup(mode='--prepare'):
                return subprocess.run(['bash', str(script), mode], env=env,
                                      text=True, capture_output=True, timeout=20)

            self.assertEqual(setup('--incorrect').returncode, 2)
            self.assertEqual(setup('--check').returncode, 0)
            self.assertFalse(log.exists())
            result = setup()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(log.is_file(), 'import-only check accepted stale dependencies')
            first = python.resolve()
            self.assertNotEqual(first, python)
            self.assertEqual(json.loads((first.parents[1] / 'ae-runtime.json').read_text())['packages'], {})
            self.assertTrue(list((data / 'runtime').glob('legacy-venv-*/bin/python')))
            self.assertEqual(len(log.read_text().splitlines()), 1)
            self.assertEqual(setup().returncode, 0)
            self.assertEqual(len(log.read_text().splitlines()), 1)

            requirements.write_text('invalid\n')
            self.assertNotEqual(setup().returncode, 0)
            self.assertEqual(python.resolve(), first)
            self.assertEqual(setup('--check').returncode, 0)
            requirements.write_text('filelock>=4.2.2,<5\n')
            command = ['bash', str(script), '--prepare']
            with subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE) as other:
                result = setup()
                _, stderr = other.communicate(timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(other.returncode, 0, stderr)
            self.assertEqual(len(log.read_text().splitlines()), 3)
            self.assertNotEqual(python.resolve(), first)

            requirements.write_text('filelock>=4.2.1,<5\n')
            self.assertEqual(setup().returncode, 0)
            self.assertEqual(python.resolve(), first)
            self.assertEqual(len(log.read_text().splitlines()), 3)

            missing = dict(env, AGENT_ENHANCEMENTS_STATE_DIR=str(root / 'missing'))
            result = subprocess.run(['bash', str(script), '--check'], env=missing,
                                    text=True, capture_output=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'missing').exists())


if __name__ == '__main__':
    unittest.main()
