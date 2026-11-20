#!/usr/bin/env python3
"""Private credential configuration for AgentEnhancements MCP services.

The canonical file is <repository>/ui.api.json (schema version 2). It is
the only AE-managed source of API keys, provider connections, adaptive
preflight settings and MCP overrides. Empty entries deliberately do not
inherit credentials from the process environment, and no other file
(model.json, preflight.key, .env, a personal provider list) is consulted
at runtime. Never serialize values through the status/diagnostic
interface.

Version 2 stores every ``api_keys`` reference as an array of strings so
one provider can hold several keys. Blank/whitespace entries are not
credentials; identical keys are de-duplicated. First-party adapters pick
a key per HTTP request through :func:`request_keys`; readiness checks use
:func:`has_usable_key`, which never advances the rotation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import threading
import time
from typing import Any

UI = Path(__file__).resolve().parent.parent
ROOT = UI.parent
TEMPLATE = UI / "config/ui.api.example.json"
CONFIG_VERSION = 2
SUPPORTED_VERSIONS = (1, 2)
PREFLIGHT_KEY_REF = "PREFLIGHT_API_KEY"
REFERENCE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
MAX_KEYS_PER_REFERENCE = 32

BUILTINS = (
    "embeddings-mcp",
    "task-router-mcp",
    "ffmpeg-mcp",
    "vision-mcp",
    "graphrag-mcp",
    "arxiv-mcp",
    "google-news-mcp",
    "video-mcp",
    "style-mcp",
    "search-mcp",
)
# Built-in servers that stay hidden until the user opts in. task-router
# executes arbitrary bash/python payloads - equivalent to the agent's own
# shell - so exposing it to the model must be an explicit user choice
# (docs/SAFETY.md). Setting "enabled": true in ui.api.json overrides this.
DEFAULT_DISABLED = frozenset({"task-router-mcp"})
# Built-in servers whose every tool needs a credential. At least one of the
# listed references must hold a usable key (any_of); local-only built-ins
# are absent and stay visible without keys.
BUILTIN_ANY_OF = {
    "search-mcp": (
        "YOU_API_KEY",
        "TAVILY_API_KEY",
        "EXA_API_KEY",
        "FIRECRAWL_API_KEY",
        "NEWSAPI_KEY",
        "SERPER_API_KEY",
    ),
}
SECRET_PATTERN = re.compile(
    r"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]+|sk-(?:ant-)?[A-Za-z0-9_-]{16,}"
    r"|\bAKIA[A-Z0-9]{16}\b"
    r"|(?i:\b(?:Bearer|Basic)\s+[^\s\"',}]+)"
    r"|(?i:(?:api[_-]?key|access[_-]?token|password|secret|authorization)"
    r"[\"']?\s*[:=]\s*[\"']?(?:(?:Bearer|Basic)\s+)?[^\s\"',}]+)"
)

# Credential pool state: in-memory, per process. Rotation indexes are keyed
# by reference name; cooldowns by a digest of (reference, key) so no key
# value is retained beyond what the configuration snapshot already holds.
_pool_lock = threading.Lock()
_rotation: dict[str, int] = {}
_cooldown: dict[str, float] = {}


def config_path() -> Path:
    """Allow isolated test installations without changing the canonical default."""
    return Path(
        os.environ.get("AGENT_ENHANCEMENTS_API_FILE", ROOT / "ui.api.json")
    ).expanduser()


def initialize() -> Path:
    """Create the private empty template once; preserve every user edit."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if not path.is_symlink():
            path.chmod(0o600)
        return path
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(TEMPLATE.read_text(encoding="utf-8"))
    return path


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate configuration field")
        result[key] = value
    return result


def _normalize_keys(raw: Any, version: int) -> list[str]:
    """Trimmed, de-duplicated usable keys in file order."""
    if version == 1:
        if not isinstance(raw, str):
            raise ValueError("version 1 credential values must be strings")
        raw = [raw]
    elif not isinstance(raw, list) or any(not isinstance(v, str) for v in raw):
        raise ValueError("version 2 credential values must be string arrays")
    if len(raw) > MAX_KEYS_PER_REFERENCE:
        raise ValueError("too many keys for one reference")
    result: list[str] = []
    for item in raw:
        item = item.strip()
        if item and item not in result:
            result.append(item)
    return result


def validate_document(doc: Any) -> dict:
    """Validate one parsed document and return a normalized copy.

    Raises ValueError with a value-free message on any contract violation.
    Unknown top-level fields are preserved; ``api_keys`` becomes
    ``{reference: [usable keys]}`` regardless of the on-disk version.
    """
    if not isinstance(doc, dict):
        raise ValueError("configuration must be an object")
    version = doc.get("version")
    if type(version) is not int or version not in SUPPORTED_VERSIONS:
        raise ValueError("unsupported configuration version")
    keys = doc.get("api_keys", {})
    if not isinstance(keys, dict):
        raise ValueError("api_keys must be an object")
    connections = doc.get("connections", {})
    if not isinstance(connections, dict) or any(
        not isinstance(v, str) for v in connections.values()
    ):
        raise ValueError("connection values must be strings")
    servers = doc.get("mcp", {})
    if not isinstance(servers, dict):
        raise ValueError("mcp must be an object")
    for server in servers.values():
        if not isinstance(server, dict) or not isinstance(
            server.get("enabled", True), bool
        ):
            raise ValueError("invalid MCP entry")
        for field in ("required", "optional", "any_of", "command"):
            value = server.get(field, [])
            if not isinstance(value, list) or any(
                not isinstance(x, str) for x in value
            ):
                raise ValueError("invalid MCP list")
        env = server.get("env", {})
        if not isinstance(env, dict) or any(
            not isinstance(v, str) for v in env.values()
        ):
            raise ValueError("MCP environment must contain reference names")
    preflight = doc.get("preflight", {})
    if not isinstance(preflight, dict):
        raise ValueError("preflight must be an object")
    normalized = dict(doc)
    normalized["api_keys"] = {
        name: _normalize_keys(raw, version) for name, raw in keys.items()
    }
    normalized["connections"] = dict(connections)
    normalized["mcp"] = servers
    normalized["preflight"] = preflight
    return normalized


def _load_raw(path: Path) -> Any:
    """Parse the file with duplicate-field rejection and a size bound."""
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("configuration too large")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)


def read_config() -> tuple[dict, str | None]:
    """Read a complete snapshot; malformed/missing files fail closed for cloud APIs."""
    try:
        return validate_document(_load_raw(config_path())), None
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        # Exception text can include source JSON and credentials. Keep it private.
        return {
            "api_keys": {},
            "connections": {},
            "mcp": {},
            "preflight": {},
        }, "config_unavailable_or_invalid"


def keys(name: str, config: dict | None = None) -> list[str]:
    """All usable keys for one reference (normalized snapshot order)."""
    if config is None:
        config, _ = read_config()
    found = config.get("api_keys", {}).get(name)
    if isinstance(found, list):
        return [k for k in found if isinstance(k, str) and k.strip()]
    if isinstance(found, str) and found.strip():  # un-normalized caller input
        return [found.strip()]
    result = config.get("connections", {}).get(name, "")
    return [result.strip()] if isinstance(result, str) and result.strip() else []


def value(name: str, config: dict | None = None) -> str:
    """Resolve one reference to its first usable value, never from inherited env.

    Single-secret consumers (external stdio MCP subprocesses, built-in
    OpenAI calls) receive this stable first key; only first-party adapters
    that call :func:`request_keys` rotate.
    """
    found = keys(name, config)
    return found[0] if found else ""


def has_usable_key(name: str, config: dict | None = None) -> bool:
    """Pure readiness probe: never advances rotation or touches cooldowns."""
    return bool(keys(name, config))


def _digest(name: str, key: str) -> str:
    return hashlib.sha256(f"{name}\0{key}".encode("utf-8")).hexdigest()


def request_keys(name: str, config: dict | None = None) -> list[str]:
    """Ordered key candidates for ONE outgoing request.

    The rotation pointer for ``name`` advances exactly once per call, so
    consecutive requests start on consecutive keys (round-robin per
    request). Keys cooling down after a 401/429-style failure are moved
    out of the candidate list until their cooldown ends. The list reflects
    the snapshot passed in, so a removed key is never offered again.
    """
    available = keys(name, config)
    if not available:
        return []
    now = time.monotonic()
    with _pool_lock:
        start = _rotation.get(name, 0) % len(available)
        _rotation[name] = start + 1
        ordered = available[start:] + available[:start]
        return [k for k in ordered if _cooldown.get(_digest(name, k), 0.0) <= now]


def select_key_for_request(name: str, config: dict | None = None) -> str:
    """The key the next request should use ('' when none is usable)."""
    candidates = request_keys(name, config)
    return candidates[0] if candidates else ""


def report_key_failure(name: str, key: str, cooldown_seconds: float) -> None:
    """Pause one key after a key-specific failure (bounded to 1-300 s)."""
    if not key:
        return
    seconds = min(max(float(cooldown_seconds), 1.0), 300.0)
    with _pool_lock:
        _cooldown[_digest(name, key)] = time.monotonic() + seconds


def key_health(name: str, config: dict | None = None) -> dict:
    """Value-free health: counts only."""
    available = keys(name, config)
    now = time.monotonic()
    with _pool_lock:
        cooling = sum(
            1 for k in available if _cooldown.get(_digest(name, k), 0.0) > now
        )
    return {"keys": len(available), "cooling_down": cooling}


def all_keys_for_redaction(config: dict | None = None) -> set[str]:
    """Every configured key value (including ones cooling down)."""
    if config is None:
        config, _ = read_config()
    secrets: set[str] = set()
    for raw in config.get("api_keys", {}).values():
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            if isinstance(item, str):
                secrets.update(s for s in (item, item.strip()) if s)
    return secrets


def redact(text: str, config: dict | None = None) -> str:
    """Remove configured and recognizable secrets from diagnostics and notes."""
    for secret in sorted(all_keys_for_redaction(config), key=len, reverse=True):
        text = text.replace(secret, "[redacted]")
    return SECRET_PATTERN.sub("[redacted]", text)


def server_state(name: str, config: dict | None = None) -> dict:
    """Return redacted readiness; configuration alone is not a connectivity probe."""
    if config is None:
        config, error = read_config()
    else:
        error = None
    settings = config.get("mcp", {}).get(name, {})
    enabled_by_default = name not in DEFAULT_DISABLED
    if settings.get("enabled", enabled_by_default) is False:
        reason = (
            "disabled" if "enabled" in settings else "disabled_by_default"
        )
        return {"visible": False, "reason": reason}
    any_of = list(settings.get("any_of", [])) or list(BUILTIN_ANY_OF.get(name, ()))
    if name in BUILTINS:
        # Built-in local tools remain useful during a partial/invalid JSON
        # edit; credential-only built-ins need one usable key (any_of).
        if any_of and not any(has_usable_key(ref, config) for ref in any_of):
            return {"visible": False, "reason": "missing_credentials",
                    "missing_any_of": any_of}
        return {"visible": True, "reason": "local_tools_available"}
    if error:
        return {"visible": False, "reason": error}
    if not settings:
        return {"visible": False, "reason": "not_configured"}
    missing = [key for key in settings.get("required", []) if not value(key, config)]
    if missing:
        return {"visible": False, "reason": "missing_credentials", "missing": missing}
    if any_of and not any(has_usable_key(ref, config) for ref in any_of):
        return {"visible": False, "reason": "missing_credentials",
                "missing_any_of": any_of}
    command = settings.get("command", [])
    if not command:
        return {"visible": False, "reason": "runtime_not_configured"}
    executable = (
        command[0].replace("{python}", sys.executable).replace("{repo}", str(ROOT))
    )
    if not shutil.which(executable):
        return {"visible": False, "reason": "executable_not_installed"}
    return {"visible": True, "reason": "configured"}


def cloud_available(
    server: str, key: str = "OPENAI_API_KEY", config: dict | None = None
) -> bool:
    """Apply tool-level gating as well as server-level enablement."""
    if config is None:
        config, _ = read_config()
    return bool(value(key, config)) and server_state(server, config)["visible"]


# --- One-time migration (v1 file, legacy preflight model.json/key file) ---


def _legacy_preflight_dir() -> Path:
    from project_paths import config_root
    return config_root()


def _read_private_text(path: Path, limit: int = 64 * 1024) -> str | None:
    """Read a regular, owner-only, non-symlink file; None when unsafe/absent."""
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                             | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        return None
    with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            return None
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            return None
        try:
            text = stream.read(limit + 1)
        except UnicodeError:
            return None
        return None if len(text) > limit else text


def _write_private_atomic(path: Path, text: str) -> None:
    """Same-directory temp file (0600), fsync, then atomic replace."""
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ui-api-")
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def migrate(legacy_dir: Path | None = None) -> dict:
    """Upgrade ui.api.json to version 2 once; idempotent and value-free.

    - version 1 string credentials become one-element arrays (blank -> []);
    - unknown fields are preserved verbatim;
    - a legacy adaptive-preflight ``model.json`` and owner-only
      ``preflight.key`` from the AE config directory are imported into
      ``preflight`` / ``api_keys.PREFLIGHT_API_KEY`` only when ui.api.json
      has no ``preflight`` section yet. The legacy files are left in place
      (no deletion) and are never read at runtime.
    - a private backup ``ui.api.json.backup.<timestamp>`` is written
      before the atomic replace; the original stays untouched on failure.
    """
    path = config_path()
    if not path.exists() and not path.is_symlink():
        initialize()
        return {"status": "initialized", "file": str(path)}
    if path.is_symlink() or not path.is_file():
        return {"status": "refused", "reason": "not_a_regular_file"}
    try:
        raw = _load_raw(path)
        validate_document(raw)
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        return {"status": "refused", "reason": "config_unavailable_or_invalid"}

    report: dict[str, Any] = {"status": "already_current", "file": str(path),
                              "from_version": raw["version"]}
    doc = copy.deepcopy(raw)
    changed = False
    if doc["version"] == 1:
        doc["api_keys"] = {
            name: ([item.strip()] if item.strip() else [])
            for name, item in doc.get("api_keys", {}).items()
        }
        doc["version"] = CONFIG_VERSION
        changed = True

    if "preflight" not in doc:
        directory = Path(legacy_dir) if legacy_dir else _legacy_preflight_dir()
        legacy = _read_private_text(directory / "model.json")
        if legacy is None and (directory / "model.json").is_file():
            # Readable but not owner-only: still non-secret settings.
            try:
                legacy = (directory / "model.json").read_text(encoding="utf-8")[:65536]
            except (OSError, UnicodeError):
                legacy = None
        preflight: dict[str, Any] | None = None
        if legacy is not None:
            try:
                old = json.loads(legacy, object_pairs_hook=_unique_object)
            except ValueError:
                old = None
                report["legacy_model_json"] = "invalid_not_imported"
            if isinstance(old, dict):
                preflight = {
                    "mode": old.get("adaptive_preflight_mode", 0),
                    "sdk": old.get("sdk", ""),
                    "endpoint": old.get("endpoint", ""),
                    "model": old.get("model", ""),
                    "api_key_ref": PREFLIGHT_KEY_REF,
                }
                report["legacy_model_json"] = "imported"
        key_text = _read_private_text(directory / "preflight.key")
        legacy_key = next(
            (line.strip() for line in (key_text or "").splitlines() if line.strip()), ""
        )
        if legacy_key:
            current = doc.setdefault("api_keys", {}).get(PREFLIGHT_KEY_REF, [])
            if not [k for k in current if isinstance(k, str) and k.strip()]:
                doc["api_keys"][PREFLIGHT_KEY_REF] = [legacy_key]
                report["legacy_preflight_key"] = "imported"
        if preflight is not None:
            doc["preflight"] = preflight
        if preflight is not None or legacy_key:
            changed = True

    if not changed:
        return report
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    validate_document(json.loads(text, object_pairs_hook=_unique_object))
    backup = path.with_name(
        f"{path.name}.backup.{time.strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
    )
    _write_private_atomic(backup, path.read_text(encoding="utf-8"))
    _write_private_atomic(path, text)
    report.update(status="migrated", to_version=CONFIG_VERSION, backup=str(backup))
    return report


def status() -> dict:
    """Safe for terminal output: values are never part of this result."""
    config, error = read_config()
    catalog = json.loads((ROOT / "plugin-catalog/mcp-servers.json").read_text())
    names = sorted(
        set(BUILTINS)
        | set(config.get("mcp", {}))
        | {s["id"] for s in catalog["servers"]}
    )
    return {
        "file": str(config_path()),
        "configuration": error or "valid",
        "version": config.get("version"),
        "migration_pending": config.get("version") == 1,
        "credentials": {
            key: len(keys(key, config)) for key in config.get("api_keys", {})
        },
        "servers": {name: server_state(name, config) for name in names},
        "cloud_tools": {
            "vision_describe": cloud_available("vision-mcp", config=config),
            "embeddings_openai": cloud_available("embeddings-mcp", config=config),
        },
    }


def main() -> int:
    """Initialize, migrate or print status without revealing secrets."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("init", "status", "migrate"), default="status", nargs="?"
    )
    args = parser.parse_args()
    if args.action == "init":
        print(initialize())
    elif args.action == "migrate":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        result = migrate()
        print(json.dumps(result, indent=2))
        return 1 if result["status"] == "refused" else 0
    else:
        print(json.dumps(status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
