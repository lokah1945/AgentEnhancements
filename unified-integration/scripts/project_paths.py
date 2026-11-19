#!/usr/bin/env python3
"""Canonical checkout-local storage and subprocess environment for AE."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]


def state_root() -> Path:
    """Use this checkout, with an explicit override for isolated fixtures."""
    path = Path(os.environ.get('AGENT_ENHANCEMENTS_STATE_DIR', ROOT / '.agentenhancements')).expanduser()
    if not path.is_absolute():
        raise ValueError('AE state directory must be absolute')
    return path


def memory_root() -> Path:
    """Keep explicit memory overrides compatible with isolated installations."""
    return Path(os.environ.get('AGENT_MEMORY_ROOT', state_root() / 'memory')).expanduser()


def config_root() -> Path:
    return state_root() / 'config'


def runtime_root() -> Path:
    return state_root() / 'runtime'


def prepare() -> Path:
    """Create private directories without following a state-directory symlink."""
    root = state_root()
    for path in (root, root / 'config', root / 'memory', root / 'runtime',
                 root / 'cache', root / 'cache/tmp'):
        if path.is_symlink():
            raise OSError('Refusing symlinked AE state directory')
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.chmod(0o700)
    return root


def validate_installation_scope() -> None:
    """A normal install must not capture legacy paths from a different checkout."""
    paths = [state_root(), memory_root(), ROOT / 'headroom/target',
             ROOT / 'headroom/target/release/headroom',
             Path(os.environ.get('AGENT_ENHANCEMENTS_API_FILE', ROOT / 'ui.api.json')).expanduser(),
             Path(os.environ.get('AGENT_ENHANCEMENTS_MODEL_FILE', config_root() / 'model.json')).expanduser()]
    observer = os.environ.get('TASK_OBSERVER_WORKSPACE')
    if observer:
        paths.append(Path(observer).expanduser())
    headroom = os.environ.get('HEADROOM_BIN')
    if headroom:
        paths.append(Path(shutil.which(headroom) or headroom).expanduser())
    if any(not path.resolve().is_relative_to(ROOT) for path in paths):
        raise ValueError('AE installation requires state, memory, API/model files and headroom inside this checkout; clear external overrides')


def environment() -> dict[str, str]:
    """Keep AE caches and temporary work local without relocating host configs."""
    root = prepare()
    cache = root / 'cache'
    return {
        'AGENT_ENHANCEMENTS_STATE_DIR': str(root),
        'AGENT_MEMORY_ROOT': str(memory_root()),
        'AGENT_ENHANCEMENTS_API_FILE': str(Path(os.environ.get('AGENT_ENHANCEMENTS_API_FILE', ROOT / 'ui.api.json')).expanduser()),
        'AGENT_ENHANCEMENTS_MODEL_FILE': str(Path(os.environ.get('AGENT_ENHANCEMENTS_MODEL_FILE', config_root() / 'model.json')).expanduser()),
        'TASK_OBSERVER_WORKSPACE': str(Path(os.environ.get('TASK_OBSERVER_WORKSPACE', memory_root() / 'task-observer')).expanduser()),
        'HEADROOM_BIN': os.environ.get('HEADROOM_BIN', str(ROOT / 'headroom/target/release/headroom')),
        'XDG_CACHE_HOME': str(cache),
        'UV_CACHE_DIR': str(cache / 'uv'),
        'PIP_CACHE_DIR': str(cache / 'pip'),
        'TIKTOKEN_CACHE_DIR': str(cache / 'tiktoken'),
        'HF_HOME': str(cache / 'huggingface'),
        'TORCH_HOME': str(cache / 'torch'),
        'npm_config_cache': str(cache / 'npm'),
        'CARGO_HOME': str(cache / 'cargo'),
        'CARGO_TARGET_DIR': str(ROOT / 'headroom/target'),
        'PUPPETEER_CACHE_DIR': str(cache / 'puppeteer'),
        'PLAYWRIGHT_BROWSERS_PATH': str(cache / 'playwright'),
        # AE modules and venv packages cache beside their checkout-local
        # source. An empty prefix also avoids recompiling system stdlib
        # into a fresh state directory on every native hook invocation.
        'PYTHONPYCACHEPREFIX': '',
        'TMPDIR': str(cache / 'tmp'),
        'TMP': str(cache / 'tmp'),
        'TEMP': str(cache / 'tmp'),
    }


def main() -> None:
    if sys.argv[1:] == ['shell']:
        for key, value in environment().items():
            print('export ' + key + '=' + shlex.quote(value))
    elif sys.argv[1:] == ['runtime']:
        print(runtime_root())
    elif sys.argv[1:] == ['validate']:
        try:
            validate_installation_scope()
        except (OSError, ValueError, RuntimeError) as error:
            raise SystemExit(str(error))
    else:
        raise SystemExit('Usage: project_paths.py shell|runtime|validate')


if __name__ == '__main__':
    main()
