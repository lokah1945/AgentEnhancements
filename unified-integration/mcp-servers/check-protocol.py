#!/usr/bin/env python3
"""Check every built MCP server over stdio, including initialize/list/call.

This checks the protocol used by real clients, not direct function imports.
No model calls, API keys, or external network requests are needed.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from api_config import BUILTINS


async def check(name: str, script: str, health_tool: str = "health") -> bool:
    """Initialize one subprocess and call its advertised health tool."""
    try:
        async with asyncio.timeout(25):
            with tempfile.TemporaryFile(mode="w+") as log:
                async with stdio_client(
                    StdioServerParameters(
                        command=sys.executable,
                        args=[script],
                    ),
                    errlog=log,
                ) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        if health_tool not in {tool.name for tool in tools.tools}:
                            raise ValueError("health tool missing")
                        result = await session.call_tool(health_tool, {})
                        if result.isError:
                            raise ValueError("health tool returned an MCP error")
                        # Prefer structuredContent when the server sends
                        # it: the consolidated gateway health tool puts
                        # {"status": ..., "backends": {...}} there and a
                        # per-server dict in the text payload, so text-only
                        # parsing could never see the overall verdict.
                        health = None
                        if getattr(result, "structuredContent", None):
                            try:
                                health = json.loads(
                                    json.dumps(result.structuredContent)
                                )
                            except (TypeError, ValueError):
                                health = None
                        if not isinstance(health, dict):
                            text = "\n".join(
                                c.text for c in result.content
                                if c.type == "text"
                            )
                            health = json.loads(text) if text else {}
                        # A plain server reports itself; the gateway
                        # reports one entry per backend. Any dict whose
                        # values are themselves status dicts is a
                        # per-backend report without an overall verdict.
                        overall = health.get("status")
                        if overall is None:
                            values = [v for v in health.values()
                                      if isinstance(v, dict)]
                            if values and all(
                                isinstance(v, dict) for v in health.values()
                            ):
                                overall = (
                                    "ok"
                                    if all(
                                        v.get("status") == "ok"
                                        for v in values
                                    )
                                    else "degraded"
                                )
                            elif "backends" not in health:
                                overall = "ok"
                        if overall != "ok":
                            raise ValueError(
                                "server is not healthy: "
                                + json.dumps(health)[:300]
                            )
                        print(
                            f"[ok] {name}: stdio initialize + {len(tools.tools)} tools + health"
                        )
                        return True
    except Exception as exc:
        print(f"[FAIL] {name}: {type(exc).__name__}", file=sys.stderr)
        return False


async def main() -> None:
    """Probe the exact built server set in the canonical template."""
    directory = Path(__file__).resolve().parent
    results = await asyncio.gather(
        *[
            check(name, str(directory / name / "server.py"))
            for name in BUILTINS
        ],
        check("agent-enhancements", str(directory / "gateway.py"), "ae_health"),
    )
    print(f"MCP protocol: {sum(results)}/{len(results)} passed")
    if not all(results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
