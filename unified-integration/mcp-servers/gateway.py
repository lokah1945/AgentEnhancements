#!/usr/bin/env python3
"""Native MCP gateway: live credentials, tool visibility and optional subprocesses.

All three CLIs connect to this stable server. Configuration edits update tools
without an agent command. Calls are gated again against a fresh snapshot so a
client's cached tool list cannot bypass credential removal.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any

import jsonschema
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.server import Server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.stdio import stdio_server

UI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(UI / "scripts"))
from api_config import (
    BUILTINS,
    ROOT,
    cloud_available,
    read_config,
    redact,
    server_state,
    value,
)
from mcp_readiness import mark_ready


def public_name(server: str, tool: str) -> str:
    """Keep portable MCP names unique and below the 64 character limit."""
    raw = server.removesuffix("-mcp").replace("-", "_") + "_" + tool
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", raw)
    if len(safe) > 64 or safe != raw:
        safe = safe[:51] + "_" + hashlib.sha256(raw.encode()).hexdigest()[:12]
    return safe


def failed(message: str) -> types.CallToolResult:
    """An explicit tool error rather than a successful-looking error envelope."""
    return types.CallToolResult(
        isError=True, content=[types.TextContent(type="text", text=message)]
    )


class External:
    """Own stdio/client contexts in one task; never leak credentials to stderr."""

    def __init__(self, name: str, settings: dict, config: dict):
        self.name = name
        self.settings = settings
        self.config = config
        self.tools: list[types.Tool] = []
        self.queue: asyncio.Queue = asyncio.Queue()
        self.ready = asyncio.Event()
        self.task: asyncio.Task | None = None
        self.pending: set[asyncio.Future] = set()
        self.finished_at = 0.0

    async def run(self) -> None:
        """Initialize only an explicitly configured installed backend."""
        command = [
            arg.replace("{repo}", str(ROOT)).replace("{python}", sys.executable)
            for arg in self.settings["command"]
        ]
        # MCP SDK supplies a minimal platform environment. Only references from
        # this backend are added; unrelated API keys are never forwarded.
        env = {
            name: value(ref, self.config)
            for name, ref in self.settings.get("env", {}).items()
        }
        params = StdioServerParameters(
            command=command[0], args=command[1:], env=env, cwd=str(ROOT)
        )
        try:
            with open(os.devnull, "w") as errors:
                async with stdio_client(params, errlog=errors) as (reader, writer):
                    async with ClientSession(
                        reader, writer, read_timeout_seconds=timedelta(seconds=90)
                    ) as session:
                        await session.initialize()
                        cursor = None
                        for _ in range(100):
                            page = await session.list_tools(cursor=cursor)
                            self.tools.extend(page.tools)
                            cursor = page.nextCursor
                            if not cursor:
                                break
                        else:
                            raise ValueError("too many tools pages")
                        self.ready.set()
                        while True:
                            item = await self.queue.get()
                            if item is None:
                                break
                            tool, arguments, result = item
                            try:
                                response = await session.call_tool(tool, arguments)
                            except Exception:
                                response = failed(
                                    "External MCP request failed; verify its installation and authorization."
                                )
                                if not result.done():
                                    result.set_result(response)
                                raise RuntimeError(
                                    "external connection unavailable"
                                ) from None
                            if not result.done():
                                result.set_result(response)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.tools = []
        finally:
            self.finished_at = time.monotonic()
            self.ready.set()
            self.tools = []
            for result in self.pending:
                if not result.done():
                    result.set_result(
                        failed("External MCP disconnected or its credentials changed.")
                    )
            while not self.queue.empty():
                item = self.queue.get_nowait()
                if item and not item[2].done():
                    item[2].set_result(failed("External MCP is unavailable."))

    async def call(self, name: str, arguments: dict) -> types.CallToolResult:
        """Forward one tool call on the established connection."""
        if not self.task or self.task.done():
            return failed("External MCP is unavailable.")
        result = asyncio.get_running_loop().create_future()
        self.pending.add(result)
        try:
            await self.queue.put((name, arguments, result))
            return await result
        finally:
            self.pending.discard(result)

    async def stop(self) -> None:
        """Cancel on credential rotation/removal; close contexts in their owner task."""
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)


class Gateway:
    """Compose built-in tools and ready external tools from a live API snapshot."""

    def __init__(self):
        self.modules: dict[str, Any] = {}
        self.definitions: dict[str, list[types.Tool]] = {}
        self.externals: dict[str, External] = {}
        self.fingerprints: dict[str, str] = {}
        self.sessions: set = set()
        self.module_locks = {name: asyncio.Lock() for name in BUILTINS}
        self.signature = ""
        self.marker: Path | None = None
        self.lock = asyncio.Lock()
        self.server = Server(
            "agent-enhancements", version="2.2.0", lifespan=self.lifespan
        )
        self.server.list_tools()(self.list_tools)
        # Validate the *current* schema ourselves, not an SDK cache from before
        # a key was removed. Return a CallToolResult for correct error semantics.
        self.server.call_tool(validate_input=False)(self.call_tool)

    async def load(self) -> None:
        """Import trusted bundled implementations, preserving their MCP schemas."""
        for name in BUILTINS:
            spec = importlib.util.spec_from_file_location(
                "ae_gateway_" + name.replace("-", "_"),
                UI / "mcp-servers" / name / "server.py",
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            self.modules[name] = module
            self.definitions[name] = await module.mcp.list_tools()

    async def refresh(self, config: dict) -> None:
        """Start/stop only changed external servers; a blank key prevents launch."""
        async with self.lock:
            desired = {}
            for name, settings in config.get("mcp", {}).items():
                if name in BUILTINS or not server_state(name, config)["visible"]:
                    continue
                env = {
                    key: value(ref, config)
                    for key, ref in settings.get("env", {}).items()
                }
                desired[name] = hashlib.sha256(
                    json.dumps([settings, env], sort_keys=True).encode()
                ).hexdigest()
            for name in list(self.externals):
                worker = self.externals[name]
                retry = (
                    worker.task.done() and time.monotonic() - worker.finished_at >= 30
                )
                if desired.get(name) != self.fingerprints.get(name) or retry:
                    await self.externals.pop(name).stop()
                    self.fingerprints.pop(name, None)
            for name, fingerprint in desired.items():
                if name in self.externals:
                    continue
                worker = External(name, config["mcp"][name], config)
                self.externals[name] = worker
                self.fingerprints[name] = fingerprint
                worker.task = asyncio.create_task(worker.run())

    def tools(self, config: dict) -> dict[str, tuple[str, str, types.Tool]]:
        """Build a fresh tool catalog; local subsets require no cloud credential."""
        result = {}
        sources = {
            **self.definitions,
            **{key: worker.tools for key, worker in self.externals.items()},
        }
        for name, definitions in sources.items():
            if not server_state(name, config)["visible"]:
                continue
            for original in definitions:
                if (
                    name == "vision-mcp"
                    and original.name == "describe"
                    and not cloud_available(name, config=config)
                ):
                    continue
                tool = original.model_copy(deep=True)
                tool.name = public_name(name, original.name)
                if original.name == "health":
                    tool.annotations = types.ToolAnnotations(
                        readOnlyHint=True, destructiveHint=False, idempotentHint=True
                    )
                if name == "embeddings-mcp" and original.name in (
                    "embed",
                    "embed_batch",
                ):
                    choices = (
                        ["local", "openai"]
                        if cloud_available(name, config=config)
                        else ["local"]
                    )
                    tool.inputSchema["properties"]["backend"] = {
                        "type": "string",
                        "enum": choices,
                        "default": "local",
                    }
                    tool.description = (
                        "Embed text with a deterministic local vector by default. Available backends: "
                        + ", ".join(choices)
                        + "."
                    )
                result[tool.name] = (name, original.name, tool)
        return result

    def remember_session(self) -> None:
        """Remember connected clients for tools/list_changed notifications."""
        try:
            self.sessions.add(self.server.request_context.session)
        except LookupError:
            pass  # Direct unit invocation outside a protocol request.

    async def list_tools(self) -> list[types.Tool]:
        """Return currently usable tools; never include missing-key cloud tools."""
        self.remember_session()
        config, _ = read_config()
        if self.marker is None:
            try:
                self.marker = mark_ready()
            except OSError:
                pass  # Coordination failure must not hide otherwise usable tools.
        return [entry[2] for entry in self.tools(config).values()]

    async def call_tool(self, name: str, arguments: dict) -> types.CallToolResult:
        """Gate stale names, validate current schemas, then execute the backend."""
        self.remember_session()
        config, _ = read_config()
        entry = self.tools(config).get(name)
        if not entry:
            return failed(
                "Tool is unavailable in the current ui.api.json configuration."
            )
        server, original, tool = entry
        try:
            jsonschema.validate(arguments, tool.inputSchema)
        except jsonschema.ValidationError:
            return failed(
                "Arguments do not match this tool's currently available schema."
            )
        try:
            if server in self.modules:
                # Bundled sync tools include blocking IO. Keep the MCP event
                # loop available for cancellation, list changes and other calls.
                async with self.module_locks[server]:
                    result = await asyncio.to_thread(
                        lambda: asyncio.run(
                            self.modules[server].mcp.call_tool(original, arguments)
                        )
                    )
                if isinstance(result, tuple):
                    response = types.CallToolResult(
                        content=list(result[0]), structuredContent=result[1]
                    )
                elif isinstance(result, dict):
                    response = types.CallToolResult(
                        content=[
                            types.TextContent(type="text", text=json.dumps(result))
                        ],
                        structuredContent=result,
                    )
                else:
                    response = types.CallToolResult(content=list(result))
                if (
                    response.structuredContent is None
                    and len(response.content) == 1
                    and response.content[0].type == "text"
                ):
                    try:
                        data = json.loads(response.content[0].text)
                        if isinstance(data, dict):
                            response.structuredContent = data
                    except ValueError:
                        pass
                if (
                    isinstance(response.structuredContent, dict)
                    and "error" in response.structuredContent
                ):
                    response.isError = True
            else:
                # A rotation invalidates the previous backend immediately,
                # including the interval before the polling watcher runs.
                worker = self.externals[server]
                refs = worker.settings.get("env", {})
                if any(
                    value(ref, config) != value(ref, worker.config)
                    for ref in refs.values()
                ):
                    return failed("Credentials changed; MCP reconnect is in progress.")
                response = await worker.call(original, arguments)

            # Some external MCPs echo environment values in error messages.
            def clean(item: Any) -> Any:
                if isinstance(item, str):
                    return redact(item, config)
                if isinstance(item, list):
                    return [clean(x) for x in item]
                if isinstance(item, dict):
                    return {redact(k, config): clean(v) for k, v in item.items()}
                return item

            return types.CallToolResult.model_validate(
                clean(response.model_dump(mode="json"))
            )
        except Exception:
            return failed(
                "MCP execution failed. Verify input files and backend availability."
            )

    async def watch(self) -> None:
        """Refresh automatically; notifications carry no credential material."""
        while True:
            config, _ = read_config()
            await self.refresh(config)
            current = json.dumps(
                [
                    entry[2].model_dump(mode="json")
                    for entry in self.tools(config).values()
                ],
                sort_keys=True,
            )
            if current != self.signature:
                self.signature = current
                for session in list(self.sessions):
                    try:
                        await session.send_tool_list_changed()
                    except Exception:
                        self.sessions.discard(session)
            await asyncio.sleep(0.5)

    @asynccontextmanager
    async def lifespan(self, _server: Server):
        """Own watcher and child lifetimes within the native stdio connection."""
        await self.load()
        watcher = asyncio.create_task(self.watch())
        try:
            yield {}
        finally:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
            await asyncio.gather(*(worker.stop() for worker in self.externals.values()))
            if self.marker:
                try:
                    self.marker.unlink(missing_ok=True)
                except OSError:
                    pass


async def main() -> None:
    """Run one native gateway; no launcher or explicit agent call is required."""
    gateway = Gateway()
    async with stdio_server() as (reader, writer):
        await gateway.server.run(
            reader,
            writer,
            gateway.server.create_initialization_options(
                notification_options=NotificationOptions(tools_changed=True)
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
