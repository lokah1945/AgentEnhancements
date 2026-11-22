"""Private, atomic configuration updates shared by native host adapters."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

import json5


def managed_integration_path(value: object, *suffix: str) -> bool:
    """Recognize our canonical entry points even after a checkout moves."""
    if not isinstance(value, (str, Path)):
        return False
    path = Path(value).expanduser()
    parts = ("unified-integration", *suffix)
    return path.is_absolute() and path.parts[-len(parts):] == parts


def write(path: Path, content: str) -> None:
    """Preserve unchanged files and keep private backups of actual changes.

    A symlinked config (e.g. managed dotfiles) is updated at its target so
    the link survives; replacing the link itself would silently detach the
    user's managed copy. resolve() is non-strict, so a dangling link still
    writes to its intended target.
    """
    if path.is_symlink():
        path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        backup = path.with_name(path.name + ".backup." + stamp)
        shutil.copy2(path, backup)
        backup.chmod(0o600)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_json(path: Path) -> dict:
    """Reject invalid or non-object configuration without overwriting it."""
    doc = json5.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(doc, dict):
        raise ValueError(f"configuration must be an object: {path}")
    return doc


def write_json(path: Path, doc: dict) -> None:
    """Write JSON; original JSONC comments remain in the private backup."""
    write(path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def merge_instructions(path: Path, content: str) -> None:
    """Refresh only our marked block, preserving personal instructions."""
    begin = "<!-- agent-enhancements:begin -->"
    end = "<!-- agent-enhancements:end -->"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if existing.count(begin) != existing.count(end) or existing.count(begin) > 1:
        raise ValueError(f"ambiguous instruction markers: {path}")
    if begin in existing and existing.index(begin) > existing.index(end):
        raise ValueError(f"reversed instruction markers: {path}")
    block = f"{begin}\n{content.rstrip()}\n{end}"
    if begin in existing:
        merged = re.sub(re.escape(begin) + r".*?" + re.escape(end),
                        lambda _: block, existing, flags=re.S)
    else:
        merged = existing + ("\n\n" if existing else "") + block + "\n"
    write(path, merged)
