#!/usr/bin/env python3
"""Private, live credential configuration shared by integrations and MCP tools.

The canonical file is <repository>/ui.api.json. Empty entries deliberately do
not inherit credentials from the process environment. Never serialize values
through the status/diagnostic interface.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

UI = Path(__file__).resolve().parent.parent
ROOT = UI.parent
TEMPLATE = UI / "config/ui.api.example.json"
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
)


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


def write_config(config: dict) -> None:
    """Replace canonical credentials atomically with private permissions."""
    path = config_path()
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ui-api-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(config, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def migrate_claude_auth(env: dict) -> bool:
    """Import existing custom auth once; empty canonical edits stay empty."""
    names = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
    if not any(isinstance(env.get(name), str) and env[name].strip() for name in names):
        return False
    initialize()
    config, error = read_config()
    if error:
        raise ValueError("Cannot migrate Claude auth: ui.api.json must be valid")
    for name in names:
        if not value(name, config):
            config.setdefault("api_keys", {})[name] = env.get(name, "")
    write_config(config)
    for name in names:
        env.pop(name, None)
    return True


def read_config() -> tuple[dict, str | None]:
    """Read a complete snapshot; malformed/missing files fail closed for cloud APIs."""
    try:
        path = config_path()
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("configuration too large")
        doc = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
        )
        if (
            not isinstance(doc, dict)
            or type(doc.get("version")) is not int
            or doc.get("version") != 1
        ):
            raise ValueError("unsupported configuration version")
        for section in ("api_keys", "connections"):
            values = doc.get(section, {})
            if not isinstance(values, dict) or any(
                not isinstance(v, str) for v in values.values()
            ):
                raise ValueError("credential and connection values must be strings")
        servers = doc.get("mcp", {})
        if not isinstance(servers, dict):
            raise ValueError("mcp must be an object")
        for server in servers.values():
            if not isinstance(server, dict) or not isinstance(
                server.get("enabled", True), bool
            ):
                raise ValueError("invalid MCP entry")
            for field in ("required", "optional", "command"):
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
        return doc, None
    except (OSError, ValueError, TypeError, UnicodeError):
        # Exception text can include source JSON and credentials. Keep it private.
        return {
            "api_keys": {},
            "connections": {},
            "mcp": {},
        }, "config_unavailable_or_invalid"


def value(name: str, config: dict | None = None) -> str:
    """Resolve one reference from the central file, never from inherited env."""
    if config is None:
        config, _ = read_config()
    for section in ("api_keys", "connections"):
        result = config.get(section, {}).get(name, "")
        if isinstance(result, str) and result.strip():
            return result.strip()
    return ""


def redact(text: str, config: dict | None = None) -> str:
    """Remove configured secret values from project-generated diagnostics/notes."""
    if config is None:
        config, _ = read_config()
    secrets = {
        s
        for raw in config.get("api_keys", {}).values()
        for s in (raw, raw.strip())
        if s
    }
    for secret in sorted(secrets, key=len, reverse=True):
        if secret:
            text = text.replace(secret, "[redacted]")
    return text


def server_state(name: str, config: dict | None = None) -> dict:
    """Return redacted readiness; configuration alone is not a connectivity probe."""
    if config is None:
        config, error = read_config()
    else:
        error = None
    settings = config.get("mcp", {}).get(name, {})
    if settings.get("enabled", True) is False:
        return {"visible": False, "reason": "disabled"}
    # Built-in local tools remain useful during a partial/invalid JSON edit.
    if name in BUILTINS:
        return {"visible": True, "reason": "local_tools_available"}
    if error:
        return {"visible": False, "reason": error}
    if not settings:
        return {"visible": False, "reason": "not_configured"}
    missing = [key for key in settings.get("required", []) if not value(key, config)]
    if missing:
        return {"visible": False, "reason": "missing_credentials", "missing": missing}
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
        "credentials": {
            key: bool(value(key, config)) for key in config.get("api_keys", {})
        },
        "servers": {name: server_state(name, config) for name in names},
        "cloud_tools": {
            "vision_describe": cloud_available("vision-mcp", config=config),
            "embeddings_openai": cloud_available("embeddings-mcp", config=config),
        },
    }


def main() -> int:
    """Initialize configuration, print safe status, or serve Claude's key helper."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("init", "status", "claude-key"), default="status", nargs="?"
    )
    args = parser.parse_args()
    if args.action == "init":
        print(initialize())
    elif args.action == "claude-key":
        # Called directly by Claude apiKeyHelper, never by diagnostic scripts.
        config, _ = read_config()
        key = value("ANTHROPIC_AUTH_TOKEN", config) or value(
            "ANTHROPIC_API_KEY", config
        )
        if not key:
            return 1
        print(key)
    else:
        print(json.dumps(status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
