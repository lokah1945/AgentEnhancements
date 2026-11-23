"""Gateway regressions: bundled-module serialization, external timeouts, ae_health.

All servers, tools, credentials and backends below are in-process fixtures.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import anyio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module

SERVERS = UI_DIR / "mcp-servers"
sys.path.insert(0, str(UI_DIR / "scripts"))


class GatewayTestCase(unittest.TestCase):
    """Isolate configuration and state under one temporary root."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="ae-gateway-test-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.api_file = root / "ui.api.json"
        environment = patch.dict(os.environ, {
            "HOME": str(root / "home"),
            "AGENT_ENHANCEMENTS_STATE_DIR": str(root / "ae-state"),
            "AGENT_MEMORY_ROOT": str(root / "memory"),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "AGENT_ENHANCEMENTS_API_FILE": str(self.api_file),
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.config: dict = {"version": 1, "api_keys": {}, "connections": {}, "mcp": {}}
        self.write_config()
        self.gw = load_module("gateway_regressions_gateway", SERVERS / "gateway.py")

    def write_config(self) -> None:
        """Persist the fixture configuration the gateway reads live."""
        self.api_file.write_text(json.dumps(self.config))


class BundledLockTests(GatewayTestCase):
    """A cancelled call must keep its module locked until its thread ends."""

    server = "embeddings-mcp"

    def make_gateway(self):
        """A gateway with one blocking fake bundled module that counts overlap."""
        gateway = self.gw.Gateway()
        state = SimpleNamespace(active=0, peak=0, entered=threading.Event(),
                                release=threading.Event(), guard=threading.Lock())

        async def call_tool(*_args):
            with state.guard:
                state.active += 1
                state.peak = max(state.peak, state.active)
            state.entered.set()
            await asyncio.to_thread(state.release.wait, 5)
            with state.guard:
                state.active -= 1
            return {"ok": True}

        gateway.modules[self.server] = SimpleNamespace(mcp=SimpleNamespace(call_tool=call_tool))
        gateway.definitions[self.server] = [self.gw.types.Tool(
            name="embed", inputSchema={"type": "object", "properties": {}})]
        return gateway, state

    async def wait_entered(self, state) -> None:
        """Wait until the fake module runs inside its worker thread."""
        for _ in range(300):
            if state.entered.is_set():
                return
            await asyncio.sleep(0.01)
        self.fail("bundled call never started")

    def test_cancelled_call_holds_module_lock_until_thread_finishes(self):
        async def check():
            gateway, state = self.make_gateway()
            first = asyncio.create_task(gateway.call_tool("embeddings_embed", {}))
            await self.wait_entered(state)
            first.cancel()
            await asyncio.sleep(0.05)
            self.assertTrue(gateway.module_locks[self.server].locked())
            second = asyncio.create_task(gateway.call_tool("embeddings_embed", {}))
            await asyncio.sleep(0.1)
            self.assertEqual(state.active, 1, "second call ran beside the cancelled one")
            state.release.set()
            await asyncio.gather(first, return_exceptions=True)
            response = await asyncio.wait_for(second, timeout=5)
            self.assertFalse(response.isError)
            self.assertTrue(first.cancelled())
            self.assertEqual(state.peak, 1)

        asyncio.run(check())

    def test_anyio_cancel_scope_does_not_release_lock_early(self):
        # The MCP lowlevel server cancels handlers through anyio cancel
        # scopes, which re-deliver cancellation on every await.
        async def check():
            gateway, state = self.make_gateway()
            released_early = []

            async def handler(scope_ready):
                with anyio.CancelScope() as scope:
                    scope_ready.append(scope)
                    await gateway.call_tool("embeddings_embed", {})

            scopes: list = []
            async with anyio.create_task_group() as group:
                group.start_soon(handler, scopes)
                await self.wait_entered(state)
                scopes[0].cancel()
                await asyncio.sleep(0.1)
                released_early.append(not gateway.module_locks[self.server].locked())
                state.release.set()
            self.assertEqual(released_early, [False])
            self.assertFalse(gateway.module_locks[self.server].locked())

        anyio.run(check)


class ExternalTimeoutTests(GatewayTestCase):
    """The SDK read timeout must not be reported as an invalid request."""

    def run_external(self, error_code: int):
        """Drive External.run with a fake session whose call raises McpError."""
        gw = self.gw

        class FakeSession:
            def __init__(self, *_args, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_exc):
                return False

            async def initialize(self):
                return None

            async def list_tools(self, cursor=None):
                return SimpleNamespace(tools=[gw.types.Tool(
                    name="slow", inputSchema={"type": "object"})], nextCursor=None)

            async def call_tool(self, *_args):
                raise gw.McpError(gw.types.ErrorData(code=error_code, message="fixture"))

        @asynccontextmanager
        async def fake_stdio(*_args, **_kwargs):
            yield (None, None)

        async def check():
            worker = gw.External("fixture-mcp", {"command": [sys.executable]}, self.config)
            with patch.object(gw, "ClientSession", FakeSession), \
                    patch.object(gw, "stdio_client", fake_stdio), \
                    patch.object(gw, "external_launch_current", lambda *_a: True), \
                    patch.object(gw, "external_command", lambda command: command):
                worker.task = asyncio.create_task(worker.run())
                await asyncio.wait_for(worker.ready.wait(), timeout=5)
                response = await asyncio.wait_for(worker.call("slow", {}), timeout=5)
                await worker.stop()
            return response

        return asyncio.run(check())

    def test_request_timeout_is_reported_as_timeout(self):
        response = self.run_external(408)
        self.assertTrue(response.isError)
        self.assertIn("timed out", response.content[0].text)
        self.assertNotIn("invalid arguments", response.content[0].text)

    def test_other_json_rpc_errors_still_report_rejection(self):
        response = self.run_external(-32602)
        self.assertTrue(response.isError)
        self.assertIn("invalid arguments", response.content[0].text)


class HealthDeadlineTests(GatewayTestCase):
    """ae_health probes run concurrently and a stuck backend times out."""

    def test_stuck_backend_reports_timeout_without_blocking_others(self):
        for name in ("stuck-mcp", "quick-mcp", "slow-mcp"):
            self.config["mcp"][name] = {"command": [sys.executable]}
        self.write_config()
        gw = self.gw

        async def check():
            gateway = gw.Gateway()
            gateway.health_timeout = 0.5
            ready = asyncio.Event()
            ready.set()
            config, _ = gw.read_config()
            hang = asyncio.Event()

            def worker(behaviour):
                async def call(*_args):
                    if behaviour == "hang":
                        await hang.wait()
                    elif behaviour == "slow":
                        await asyncio.sleep(0.3)
                    return gw.types.CallToolResult(content=[gw.types.TextContent(
                        type="text", text=json.dumps({"status": "ok"}))])
                return SimpleNamespace(
                    tools=[gw.types.Tool(name=tool, inputSchema={"type": "object"})
                           for tool in ("health", "work")],
                    ready=ready, call=call,
                    task=asyncio.get_running_loop().create_future(),
                )

            for name, behaviour in (("stuck-mcp", "hang"), ("quick-mcp", "ok"),
                                    ("slow-mcp", "slow")):
                gateway.externals[name] = worker(behaviour)
                gateway.fingerprints[name] = gw.external_fingerprint(
                    config["mcp"][name], config)
            started = time.monotonic()
            response = await asyncio.wait_for(gateway.call_tool("ae_health", {}), timeout=5)
            elapsed = time.monotonic() - started
            await asyncio.sleep(0)
            return response, elapsed

        response, elapsed = asyncio.run(check())
        backends = response.structuredContent["backends"]
        self.assertEqual(backends["stuck-mcp"], {"status": "timeout"})
        self.assertEqual(backends["quick-mcp"]["status"], "ok")
        self.assertEqual(backends["slow-mcp"]["status"], "ok")
        self.assertEqual(response.structuredContent["status"], "degraded")
        # Concurrent probes: about one deadline, not the sum of all waits.
        self.assertLess(elapsed, 2.0)


if __name__ == "__main__":
    unittest.main()
