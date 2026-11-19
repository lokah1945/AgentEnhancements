"""Exercise installer failure and path boundaries with disposable skill bundles."""
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import sys
import tempfile
import unittest

from helpers import UI_DIR


class SetupSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ae-setup-safety-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.unified = self.repo / 'unified-integration'
        self.unified.mkdir(parents=True)
        self.env = dict(os.environ, HOME=str(self.root / 'home'),
                        AGENT_MEMORY_ROOT=str(self.root / 'memory'),
                        AGENT_ENHANCEMENTS_BASE_DIR=str(self.repo))

    def aggregate(self):
        bundle = self.repo / 'agentic-awesome-skills/skills/probe'
        bundle.mkdir(parents=True)
        (bundle / 'SKILL.md').write_text(
            '---\nname: probe\ncategory: general\ndescription: Safe test bundle\n---\nExample\n')
        source = (UI_DIR / 'setup.sh').read_text().rsplit('\nmain "$@"', 1)[0]
        script = self.unified / 'setup.sh'
        script.write_text(source + '\naggregate_skills\n')
        return subprocess.run(['bash', str(script)], env=self.env,
                              capture_output=True, text=True, timeout=30)

    def test_aggregation_refuses_symlinked_destination_without_deleting_data(self):
        outside = self.root / 'outside'
        (outside / 'probe').mkdir(parents=True)
        marker = outside / 'probe/personal.txt'
        marker.write_text('keep me')
        categories = self.unified / 'skills/by-category'
        categories.mkdir(parents=True)
        (categories / 'general').symlink_to(outside, target_is_directory=True)
        result = self.aggregate()
        self.assertTrue(marker.is_file(), 'aggregation deleted data through a category symlink')
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_copy_failure_aborts_instead_of_indexing_missing_bundle(self):
        tools = self.root / 'bin'
        tools.mkdir()
        copy = tools / 'cp'
        copy.write_text('#!/bin/sh\nexit 9\n')
        copy.chmod(0o755)
        self.env['PATH'] = str(tools) + os.pathsep + os.environ['PATH']
        result = self.aggregate()
        self.assertNotEqual(result.returncode, 0, 'setup silently indexed a bundle whose copy failed')

    def test_linker_rejects_registry_name_traversal(self):
        registry = self.unified / 'skills'
        (registry / 'by-category/general').mkdir(parents=True)
        escaped_source = registry / 'by-category/escape'
        escaped_source.mkdir()
        (escaped_source / 'SKILL.md').write_text('synthetic test skill')
        (registry / 'all-skills.json').write_text(json.dumps({'skills': [
            {'name': '../escape', 'category': 'general', 'source': 'Superpowers'}]}))
        target = self.root / 'native/skills'
        self.env.update(AGENT_SKILLS_DIR=str(registry), AGENT_SKILLS_NATIVE_TARGETS=str(target))
        result = subprocess.run(['bash', str(UI_DIR / 'scripts/link-skills.sh'), '--set', 'all'],
                                env=self.env, capture_output=True, text=True, timeout=20)
        self.assertFalse((target.parent / 'escape').is_symlink(),
                         'index name escaped the native skill destination')
        self.assertIn('invalid', result.stderr.lower())

    def test_memory_initializer_creates_private_storage_and_refuses_db_symlink(self):
        tools = self.root / 'sqlite-bin'
        tools.mkdir()
        sqlite = tools / 'sqlite3'
        sqlite.write_text('#!' + sys.executable + '\nimport sqlite3,sys\n'
                          'with sqlite3.connect(sys.argv[1]) as c:\n'
                          '    c.executescript(sys.stdin.read())\n')
        sqlite.chmod(0o755)
        self.env['PATH'] = str(tools) + os.pathsep + os.environ['PATH']
        script = UI_DIR / 'memory/init-memory.sh'
        result = subprocess.run(['bash', '-c', 'umask 022; exec bash "$1"', 'audit', str(script)],
                                env=self.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        memory = Path(self.env['AGENT_MEMORY_ROOT'])
        self.assertEqual(memory.stat().st_mode & 0o777, 0o700)
        self.assertEqual((memory / 'memory.db').stat().st_mode & 0o777, 0o600)
        (memory / 'memory.db').unlink()
        outside = self.root / 'outside.db'
        outside.write_text('user data')
        (memory / 'memory.db').symlink_to(outside)
        refused = subprocess.run(['bash', str(script)], env=self.env,
                                 capture_output=True, text=True, timeout=20)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(outside.read_text(), 'user data')

    def test_legacy_memory_hook_refuses_database_symlink(self):
        memory = Path(self.env['AGENT_MEMORY_ROOT'])
        memory.mkdir()
        target = self.root / 'private.db'
        with sqlite3.connect(target) as connection:
            connection.execute('CREATE TABLE personal(value TEXT)')
        original = target.read_bytes()
        (memory / 'memory.db').symlink_to(target)
        result = subprocess.run([sys.executable, str(UI_DIR / 'memory/hooks/codex-memory-hook.py'),
                                 'cleanup'], env=self.env, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), original)

    def test_piped_installer_refuses_missing_pin(self):
        tools = self.root / 'bootstrap-bin'
        tools.mkdir()
        git = tools / 'git'
        git.write_text('#!/bin/bash\n'
                       'if [ "$1" = clone ]; then\n'
                       ' mkdir -p "$3/unified-integration"\n'
                       ' printf "#!/bin/sh\\nprintf bootstrap-executed\\\\n\\n" > "$3/unified-integration/setup.sh"\n'
                       ' exit 0\nfi\n'
                       'case " $* " in *" checkout "*) exit 1;; esac\nexit 0\n')
        git.chmod(0o755)
        env = dict(self.env, PATH=str(tools)+os.pathsep+os.environ['PATH'],
                   AGENT_ENHANCEMENTS_REF='missing-audit-fixture-ref',
                   AGENT_ENHANCEMENTS_BASE_DIR=str(self.root / 'installation'))
        result = subprocess.run(['bash'], input=(UI_DIR / 'setup.sh').read_text(), env=env,
                                capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0, 'invalid pin executed the default branch')
        self.assertNotIn('bootstrap-executed', result.stdout)

    def test_compression_reference_config_has_no_machine_path_after_build(self):
        binary = self.repo / 'headroom/target/release/headroom'
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/bin/sh\nexit 0\n')
        binary.chmod(0o755)
        source = (UI_DIR / 'setup.sh').read_text().rsplit('\nmain "$@"', 1)[0]
        script = self.unified / 'setup.sh'
        script.write_text(source + '\nsetup_compression\n')
        result = subprocess.run(['bash', str(script)], env=self.env,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        config = (self.unified / 'compression/config.yaml').read_text()
        self.assertNotIn(str(self.root), config)


if __name__ == '__main__':
    unittest.main()
