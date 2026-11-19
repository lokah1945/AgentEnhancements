"""Project-owned defaults must survive a fresh checkout and a foreign cwd."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import UI_DIR


class ProjectLocalStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='ae-local-state-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'fresh checkout'
        self.scripts = self.repo / 'unified-integration/scripts'
        self.scripts.mkdir(parents=True)
        for path in (UI_DIR / 'scripts').glob('*.py'):
            shutil.copyfile(path, self.scripts / path.name)
        shutil.copyfile(UI_DIR / 'scripts/setup-mcp.sh', self.scripts / 'setup-mcp.sh')
        (self.scripts.parent / 'requirements.txt').write_text('fixture-package==1.0\n')
        self.home = self.root / 'external-home'
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), PYTHONDONTWRITEBYTECODE='1',
                        XDG_CONFIG_HOME=str(self.home / '.config'),
                        XDG_DATA_HOME=str(self.home / '.local/share'),
                        XDG_CACHE_HOME=str(self.home / '.cache'))
        for key in ('AGENT_MEMORY_ROOT', 'AGENT_ENHANCEMENTS_MODEL_FILE',
                    'AGENT_ENHANCEMENTS_API_FILE',
                    'AGENT_ENHANCEMENTS_STATE_DIR', 'TASK_OBSERVER_WORKSPACE',
                    'AGENT_ENHANCEMENTS_BASE_DIR'):
            self.env.pop(key, None)

    def test_default_data_paths_belong_to_the_checkout_even_with_global_xdg(self):
        code = '''import json,sys,importlib.util
sys.path.insert(0,sys.argv[1])
import memory,adaptive_preflight,native_hermes
spec=importlib.util.spec_from_file_location('local_observer',sys.argv[1]+'/task-observer.py')
observer=importlib.util.module_from_spec(spec);sys.modules[spec.name]=observer;spec.loader.exec_module(observer)
print(json.dumps([str(memory.MEMORY_ROOT),str(adaptive_preflight.model_config_path()),
                 str(observer.workspace_root()),str(native_hermes.host_selection_path())]))
'''
        result = subprocess.run([sys.executable, '-c', code, str(self.scripts)],
                                cwd=self.home, env=self.env, text=True,
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        for value in json.loads(result.stdout):
            self.assertTrue(Path(value).is_relative_to(self.repo), value)
        self.assertFalse((self.home / '.agent-memory').exists())

    def test_runtime_preparation_creates_dependencies_and_cache_inside_checkout(self):
        tools = self.root / 'tools'
        tools.mkdir()
        uv = tools / 'uv'
        uv.write_text('#!' + sys.executable + '\nimport pathlib,sys\n'
                      'if sys.argv[1]=="venv":\n'
                      ' p=pathlib.Path(sys.argv[-1])/"bin/python"\n'
                      ' p.parent.mkdir(parents=True);p.write_text("#!/bin/sh\\nexit 0\\n");p.chmod(0o700)\n')
        uv.chmod(0o700)
        env = dict(self.env, PATH=str(tools)+os.pathsep+os.environ['PATH'])
        result = subprocess.run(['bash', str(self.scripts / 'setup-mcp.sh'), '--prepare'],
                                cwd=self.home, env=env, capture_output=True,
                                text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        python = Path(result.stdout.strip())
        self.assertTrue(python.is_relative_to(self.repo), str(python))
        self.assertTrue(python.is_file())
        self.assertEqual((self.repo / '.agentenhancements').stat().st_mode & 0o777, 0o700)
        self.assertFalse((self.home / '.local/share/agentenhancements').exists())

    def test_default_compressor_does_not_select_a_global_path_binary(self):
        tools = self.root / 'foreign-tools'
        tools.mkdir()
        binary = tools / 'headroom'
        binary.write_text('#!/bin/sh\nexit 99\n')
        binary.chmod(0o700)
        env = dict(self.env, PATH=str(tools)+os.pathsep+os.environ['PATH'])
        env.pop('HEADROOM_BIN', None)
        code = 'import sys;sys.path.insert(0,sys.argv[1]);import compress;print(compress.get_headroom_bin())'
        result = subprocess.run([sys.executable, '-c', code, str(self.scripts)],
                                cwd=self.home, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'None')

    def test_installation_accepts_local_defaults_and_refuses_global_state_override(self):
        command = [sys.executable, str(self.scripts / 'project_paths.py'), 'validate']
        local = subprocess.run(command, env=self.env, cwd=self.home, capture_output=True, text=True)
        self.assertEqual(local.returncode, 0, local.stderr)
        external = subprocess.run(command, env=dict(self.env, AGENT_MEMORY_ROOT=str(self.home / 'memory')),
                                  cwd=self.home, capture_output=True, text=True)
        self.assertNotEqual(external.returncode, 0)
        self.assertFalse((self.home / 'memory').exists())


if __name__ == '__main__':
    unittest.main()
