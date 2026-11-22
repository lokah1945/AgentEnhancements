#!/usr/bin/env python3
"""Prepare and publish the checkout-local Python environment for setup-mcp.sh."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile

from project_paths import runtime_root

UI = Path(__file__).resolve().parent.parent
REQUIREMENTS = UI / "requirements.txt"
RECORD = "ae-runtime.json"
PROTOCOL_CHECK = UI / "mcp-servers/check-protocol.py"
RUNTIME_INVENTORY = """import mcp, PIL, yaml, tomlkit, json5, jsonschema, filelock
from importlib.metadata import distributions
import json
print(json.dumps({d.metadata['Name']: d.version for d in distributions()}))
"""


def packages(directory: Path) -> dict[str, str]:
    """Inspect actual imports and the distribution versions in this venv."""
    return json.loads(subprocess.check_output(
        [str(directory / "bin/python"), "-c", RUNTIME_INVENTORY],
        stderr=subprocess.DEVNULL, text=True, timeout=15,
    ))


def ready(directory: Path, identity: dict[str, str]) -> bool:
    """Reuse a verified generation only at its original absolute path."""
    try:
        record = json.loads((directory / RECORD).read_text(encoding="utf-8"))
        if not isinstance(record, dict) or any(
            record.get(key) != value for key, value in (identity | {"path": str(directory)}).items()
        ):
            return False
        return record.get("packages") == packages(directory)
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def install(directory: Path, identity: dict[str, str], lock_bytes: bytes) -> None:
    """Install hash-verified wheels, check dependencies and exercise stdio."""
    python = str(directory / "bin/python")
    uv = shutil.which("uv")
    with tempfile.NamedTemporaryFile(dir=directory.parent, suffix=".txt") as lockfile:
        lockfile.write(lock_bytes)
        lockfile.flush()
        options = ["--require-hashes", "--only-binary", ":all:", "-r", lockfile.name]
        if uv:
            commands = (
                [uv, "venv", "--python", sys.executable, str(directory)],
                [uv, "pip", "install", "--python", python, *options],
                [uv, "pip", "check", "--python", python],
            )
        else:
            pip = [python, "-m", "pip", "--disable-pip-version-check"]
            commands = (
                [sys.executable, "-m", "venv", str(directory)],
                [*pip, "install", *options],
                [*pip, "check"],
            )
        for command in commands:
            subprocess.run(command, check=True, stdout=sys.stderr)
    subprocess.run([python, str(PROTOCOL_CHECK)],
                   check=True, stdout=sys.stderr, timeout=60)
    record = {**identity, "path": str(directory), "packages": packages(directory)}
    (directory / RECORD).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                                    encoding="utf-8")


def activate(active: Path, candidate: Path) -> None:
    """Switch the stable path; preserve the old physical venv on first upgrade."""
    root = active.parent
    with tempfile.TemporaryDirectory(prefix=".activate-", dir=root) as directory:
        link = Path(directory) / "venv"
        link.symlink_to(candidate.relative_to(root), target_is_directory=True)
        legacy = None
        if not active.is_symlink() and active.is_dir():
            legacy = Path(tempfile.mkdtemp(prefix="legacy-venv-", dir=root))
            active.replace(legacy)
        try:
            link.replace(active)
        except BaseException:
            if legacy is not None:
                legacy.replace(active)
            raise


def managed_target(active: Path, generations: Path) -> Path:
    """Accept a legacy environment or a link directly into the managed directory."""
    if generations.is_symlink() or (active.exists() and not active.is_dir()):
        raise ValueError("Refusing an unexpected AE runtime path")
    if not active.is_symlink():
        return active
    target = active.parent / os.readlink(active)
    if target.parent != generations or target.is_symlink():
        raise ValueError("Refusing a venv symlink outside the managed environments")
    return target


def prepare() -> Path:
    """Serialize writers and publish only a complete, verified environment."""
    root = runtime_root()
    active = root / "venv"
    generations = root / "environments"
    descriptor = os.open(root / ".prepare.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        lock_bytes = REQUIREMENTS.read_bytes()
        identity = {"requirements_sha256": hashlib.sha256(lock_bytes).hexdigest(),
                    "python": sys.version.split()[0], "platform": sysconfig.get_platform()}

        def verify_lock() -> None:
            if REQUIREMENTS.read_bytes() != lock_bytes:
                raise ValueError("Requirements changed while the environment was being prepared")

        current = managed_target(active, generations)
        if ready(current, identity):
            verify_lock()
            return active / "bin/python"
        generations.mkdir(mode=0o700, exist_ok=True)
        for candidate in sorted(generations.glob("venv-*")):
            if candidate.is_dir() and not candidate.is_symlink() and ready(candidate, identity):
                verify_lock()
                activate(active, candidate)
                return active / "bin/python"

        candidate = Path(tempfile.mkdtemp(prefix="venv-", dir=generations))
        try:
            print("[setup-mcp] Preparing locked Python runtime", file=sys.stderr)
            install(candidate, identity, lock_bytes)
            verify_lock()
            activate(active, candidate)
        except BaseException:
            if not active.is_symlink() or root / os.readlink(active) != candidate:
                shutil.rmtree(candidate)
            raise
    return active / "bin/python"


def main() -> int:
    """Print the stable interpreter path or report a failed preparation."""
    try:
        if sys.argv[1:] == ["--check"]:
            root = runtime_root()
            active = root / "venv"
            managed_target(active, root / "environments")
            return subprocess.run([str(active / "bin/python"), str(PROTOCOL_CHECK)],
                                  check=False).returncode
        print(prepare())
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print("[setup-mcp] Runtime preparation failed. Check Python, wheel availability "
              "and the dependency or protocol diagnostics above.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
