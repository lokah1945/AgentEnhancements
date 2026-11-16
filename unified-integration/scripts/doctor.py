#!/usr/bin/env python3
"""Verify installed native configurations and call their exact MCP commands.

Run with the interpreter returned by setup-mcp.sh --prepare. No model API
is called, no production service is restarted, and no config is modified.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import tomlkit
import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from native_config import read_json
from native_hermes import hermes_base, hermes_roots, host_selection_path

UI = Path(__file__).resolve().parent.parent
COMMANDS = {"claude-code": "claude", "codex": "codex",
            "opencode": "opencode", "hermes": "hermes"}


def targets(agents: list[str]) -> list[tuple[str, Path, dict]]:
    """Read the actual configuration file used by each selected host."""
    home = Path.home()
    xdg = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
    result = []
    for agent in agents:
        if agent == "hermes":
            for root in hermes_roots(require_exists=False):
                path = root / "config.yaml"
                try:
                    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                    cfg = doc.get("mcp_servers", {}).get("agent-enhancements", {})
                    plugins = doc.get("plugins", {})
                    if ("agent-enhancements" not in plugins.get("enabled", [])
                            or "agent-enhancements" in plugins.get("disabled", [])
                            or not (root / "plugins/agent-enhancements/__init__.py").is_file()):
                        raise ValueError("Hermes lifecycle plugin is not active")
                except (OSError, ValueError, AttributeError, yaml.YAMLError) as exc:
                    cfg = {"diagnosis": f"Hermes configuration unavailable ({type(exc).__name__})"}
                name = root.name if root.parent == hermes_base() / "profiles" else "default"
                result.append((f"hermes/{name}", path, cfg))
            continue
        if agent == "claude-code":
            custom = os.environ.get("CLAUDE_CONFIG_DIR")
            path = Path(custom) / ".claude.json" if custom else home / ".claude.json"
            key = "mcpServers"
        elif agent == "codex":
            path = Path(os.environ.get("CODEX_HOME", home / ".codex")) / "config.toml"
            key = "mcp_servers"
        else:
            root = xdg / "opencode"
            path = root / "opencode.jsonc"
            if not path.exists():
                path = root / "opencode.json"
            key = "mcp"
        try:
            doc = tomlkit.parse(path.read_text()).unwrap() if agent == "codex" else read_json(path)
            servers = doc.get(key, {})
            cfg = servers.get("servers", {}).get("agent-enhancements", {}) if agent == "opencode" else servers.get("agent-enhancements", {})
        except (OSError, ValueError, AttributeError, TypeError) as exc:
            cfg = {"diagnosis": f"Host configuration unavailable ({type(exc).__name__})"}
        result.append((agent, path, cfg))
    return result


async def probe(label: str, path: Path, config: dict) -> dict:
    """Count each native target once, including every failed scenario."""
    row = {"agent": label, "config": str(path), "passed": False}
    if not isinstance(config, dict):
        return {**row, "diagnosis": "Managed gateway configuration must be an object"}
    if not config or "diagnosis" in config:
        return {**row, "diagnosis": config.get("diagnosis", "Managed gateway is missing")}
    agent = label.split("/", 1)[0]
    executable = shutil.which(COMMANDS[agent])
    if not executable:
        return {**row, "diagnosis": "Agent CLI is not installed"}
    if config.get("enabled") is False or config.get("disabled") is True:
        return {**row, "diagnosis": "Managed gateway is disabled"}
    command = config.get("command")
    if isinstance(command, list):
        if not command or not all(isinstance(item, str) for item in command):
            return {**row, "diagnosis": "Invalid gateway command"}
        command, arguments = command[0], command[1:]
    else:
        arguments = config.get("args", [])
    if (not isinstance(command, str) or not isinstance(arguments, list)
            or not all(isinstance(item, str) for item in arguments)
            or str(UI / "mcp-servers/gateway.py") not in arguments):
        return {**row, "diagnosis": "Gateway command does not point to this installation"}
    host_args = [executable]
    if agent == "hermes" and path.parent.parent == hermes_base() / "profiles":
        host_args.extend(["-p", path.parent.name])
    try:
        version = await asyncio.to_thread(subprocess.run, [*host_args, "--version"],
                                         capture_output=True, text=True, timeout=15)
        if version.returncode:
            return {**row, "diagnosis": "Agent CLI cannot start"}
        row["version"] = version.stdout.splitlines()[0].strip()[:100] if version.stdout.strip() else "unknown"
        if agent == "opencode" and not row["version"].removeprefix("opencode v").startswith("2."):
            return {**row, "diagnosis": "OpenCode 2 is required"}
        async with asyncio.timeout(25):
            with tempfile.TemporaryFile(mode="w+") as errors:
                async with stdio_client(StdioServerParameters(
                    command=command, args=arguments,
                    env=config.get("env", config.get("environment", {})),
                ), errlog=errors) as (reader, writer):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        listing = await session.list_tools()
                        names = {tool.name for tool in listing.tools}
                        if "ae_health" not in names:
                            raise ValueError("gateway health tool missing")
                        result = await session.call_tool("ae_health", {})
                        state = result.structuredContent or {}
                        if result.isError or state.get("status") != "ok":
                            raise ValueError("gateway is not healthy")
                        if "embeddings_embed" in names:
                            embed = await session.call_tool("embeddings_embed", {"text": "AE doctor", "backend": "local"})
                            if embed.isError:
                                raise ValueError("local tool call failed")
                        row.update(passed=True, tools=len(names), health="ok",
                                   local_tool="called" if "embeddings_embed" in names else "disabled")
    except Exception as exc:
        row["diagnosis"] = f"Native/MCP verification failed ({type(exc).__name__})"
    return row


def summarize(rows: list[dict]) -> dict:
    """A failed or missing target must never disappear from release evidence."""
    return {"targets": len(rows), "passed": sum(bool(row["passed"]) for row in rows),
            "failed": sum(not row["passed"] for row in rows), "results": rows,
            "model_auth": "not tested by doctor; use native CLI smoke tests"}


async def inspect(agents: list[str]) -> dict:
    """Bound concurrent gateway processes and retain all results."""
    semaphore = asyncio.Semaphore(2)

    async def bounded(target):
        async with semaphore:
            return await probe(*target)

    rows = await asyncio.gather(*(bounded(target) for target in targets(agents)))
    return summarize(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents", help="comma-separated native agents; saved selection by default")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    selected = (args.agents.split(",") if args.agents else
                read_json(host_selection_path()).get("agents") or
                [agent for agent, command in COMMANDS.items() if shutil.which(command)])
    if not selected or any(agent not in COMMANDS for agent in selected):
        parser.error("select at least one installed supported native agent")
    report = asyncio.run(inspect(list(dict.fromkeys(selected))))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for row in report["results"]:
            print(f"{'PASS' if row['passed'] else 'FAIL'} {row['agent']}: {row.get('diagnosis', 'native config + MCP health + local tool')}")
        print(f"Native targets: {report['passed']}/{report['targets']} passed")
    return 0 if report["targets"] and not report["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
