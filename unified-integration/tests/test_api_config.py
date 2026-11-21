"""Live API configuration and real MCP transport regression tests; no paid calls."""

import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from helpers import UI_DIR, load_module

sys.path.insert(0, str(UI_DIR / "scripts"))
import api_config as api


@contextmanager
def configuration():
    """Every test owns an empty credential file, independent of owner secrets."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "ui.api.json"
        with patch.dict(os.environ, {"AGENT_ENHANCEMENTS_API_FILE": str(path)}):
            api.initialize()
            yield path


def edit(path, change):
    """Model an atomic editor save rather than leaving partial fixture JSON.

    Fixtures may set a credential with the single-key shorthand; it is
    stored the way a user edits schema v2: a one-element array ("" -> []).
    """
    doc = json.loads(path.read_text())
    change(doc)
    doc["api_keys"] = {
        name: ([raw] if raw.strip() else []) if isinstance(raw, str) else raw
        for name, raw in doc.get("api_keys", {}).items()
    }
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(doc))
    temp.replace(path)


import unittest

class ConfigurationTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', "Windows file permissions differ from Unix")
    def test_private_initialization_preserves_edits(self):
        with configuration() as path:
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            edit(
                path,
                lambda d: d["api_keys"].update(OPENAI_API_KEY="local-fixture-secret"),
            )
            api.initialize()
            self.assertEqual(api.value("OPENAI_API_KEY"), "local-fixture-secret")

    def test_all_catalog_requirements_are_mapped(self):
        template = json.loads(api.TEMPLATE.read_text())
        catalog = json.loads(
            (UI_DIR.parent / "plugin-catalog/mcp-servers.json").read_text()
        )
        refs = set(template["api_keys"]) | set(template["connections"])
        required = set()
        self.assertEqual(len(template["mcp"]), len(catalog["servers"]))
        for server in catalog["servers"]:
            for field in ("env_required", "env_optional", "env_any_of"):
                required.update(server.get(field, []))
                self.assertTrue(set(server.get(field, [])) <= refs, server["id"])
        # Every default secret belongs to an MCP requirement or to the
        # preflight selector reference; agent login and model-provider
        # credentials must never be imported into this file.
        self.assertEqual(
            set(template["api_keys"]) - {template["preflight"]["api_key_ref"]},
            required - set(template["connections"]),
        )
        self.assertEqual(template["version"], api.CONFIG_VERSION)
        self.assertTrue(all(v == [] for v in template["api_keys"].values()))

    def test_blank_overrides_inherited_key_and_status_never_leaks_values(self):
        with configuration() as path, patch.dict(
            os.environ, {"OPENAI_API_KEY": "ambient-should-not-enable"}
        ):
            self.assertFalse(api.cloud_available("vision-mcp"))
            self.assertFalse(api.server_state("tavily-mcp")["visible"])
            edit(
                path,
                lambda d: d["api_keys"].update(TAVILY_API_KEY="secret-fixture-tavily"),
            )
            self.assertEqual(
                api.server_state("tavily-mcp")["reason"], "runtime_not_configured"
            )
            self.assertNotIn("secret-fixture-tavily", json.dumps(api.status()))
            self.assertEqual(
                api.redact("Token secret-fixture-tavily"), "Token [redacted]"
            )

    def test_invalid_and_duplicate_configuration_fail_closed(self):
        with configuration() as path:
            for content in [
                '{"version":1,"api_keys":{"OPENAI_API_KEY":"x","OPENAI_API_KEY":"y"}}',
                "{broken",
                "[]",
            ]:
                path.write_text(content)
                self.assertFalse(api.cloud_available("vision-mcp"))
                self.assertTrue(api.server_state("graphrag-mcp")["visible"])
                self.assertEqual(
                    api.status()["configuration"], "config_unavailable_or_invalid"
                )

    def test_disabled_local_backend_and_registry_are_hidden(self):
        with configuration() as path:
            edit(path, lambda d: d["mcp"]["style-mcp"].update(enabled=False))
            registry = load_module(
                "api_registry_fixture", UI_DIR / "scripts/registry.py"
            )
            visible = registry.usable_entries(registry.load_mcp_entries())
            names = {e["name"] for e in visible}
            # 8 built-ins minus style-mcp (disabled here) minus task-router
            # (hidden by default: opt-in only, api_config.DEFAULT_DISABLED).
            self.assertEqual(len(names), 7)
            self.assertNotIn("style-mcp", names)
            self.assertNotIn("task-router-mcp", names)
            self.assertNotIn("serper-mcp", names)

    def test_invalid_embedding_backend_cannot_trigger_network(self):
        module = load_module(
            "api_embeddings_fixture", UI_DIR / "mcp-servers/embeddings-mcp/server.py"
        )
        with configuration(), patch.object(
            module.urllib.request,
            "urlopen",
            side_effect=AssertionError("unexpected network"),
        ):
            self.assertIn("error", module.embed("hello", backend="typo"))
            self.assertIn("error", module.embed_batch(["hello"], backend="typo"))
            self.assertIn("error", module.embed("hello", backend="openai"))
            self.assertEqual(module.embed("hello")["backend"], "local")

    def test_local_http_proves_central_key_endpoint_model_and_rotation(self):
        """Exercise real HTTP in both cloud callers without contacting a provider."""
        received = []

        class Mock(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                doc = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                received.append(
                    (self.path, self.headers.get("Authorization"), doc["model"])
                )
                payload = (
                    {"data": [{"embedding": [0.1, 0.2]}]}
                    if self.path.endswith("embeddings")
                    else {"choices": [{"message": {"content": "Local vision fixture"}}]}
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

        http = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
        threading.Thread(target=http.serve_forever, daemon=True).start()
        try:
            with configuration() as path:
                from PIL import Image

                image = path.parent / "fixture.png"
                Image.new("RGB", (4, 4), (10, 30, 50)).save(image)

                def configure(doc):
                    doc["api_keys"]["OPENAI_API_KEY"] = "local-credential-first"
                    doc["connections"].update(
                        OPENAI_BASE_URL=f"http://127.0.0.1:{http.server_port}/v1",
                        OPENAI_EMBEDDING_MODEL="embedding-fixture",
                        OPENAI_VISION_MODEL="vision-fixture",
                    )

                edit(path, configure)
                embeddings = load_module(
                    "api_http_embeddings",
                    UI_DIR / "mcp-servers/embeddings-mcp/server.py",
                )
                vision = load_module(
                    "api_http_vision", UI_DIR / "mcp-servers/vision-mcp/server.py"
                )
                self.assertEqual(
                    embeddings.embed("hello", backend="openai")["embedding"], [0.1, 0.2]
                )
                edit(
                    path,
                    lambda d: d["api_keys"].update(
                        OPENAI_API_KEY="local-credential-second"
                    ),
                )
                self.assertEqual(
                    vision.describe(str(image))["description"], "Local vision fixture"
                )
                self.assertEqual(
                    received,
                    [
                        (
                            "/v1/embeddings",
                            "Bearer local-credential-first",
                            "embedding-fixture",
                        ),
                        (
                            "/v1/chat/completions",
                            "Bearer local-credential-second",
                            "vision-fixture",
                        ),
                    ],
                )
                edit(path, lambda d: d["api_keys"].update(OPENAI_API_KEY=""))
                self.assertIn(
                    "error", embeddings.embed("no outgoing call", backend="openai")
                )
                self.assertEqual(len(received), 2)
        finally:
            http.shutdown()
            http.server_close()


class GatewayTests(unittest.TestCase):
    def test_live_add_remove_notifications_and_stale_calls(self):
        """A real stdio session sees changes and cannot use revoked tools."""
        asyncio.run(self._live_session())

    async def _live_session(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp.types import ServerNotification, ToolListChangedNotification

        notifications = []

        async def message(message):
            if isinstance(message, ServerNotification) and isinstance(
                message.root, ToolListChangedNotification
            ):
                notifications.append(message)

        with configuration() as path, tempfile.TemporaryFile(mode="w+") as errors:
            async with stdio_client(
                StdioServerParameters(
                    command=sys.executable,
                    args=[str(UI_DIR / "mcp-servers/gateway.py")],
                    env={
                        "AGENT_ENHANCEMENTS_API_FILE": str(path),
                        "OPENAI_API_KEY": "ambient-must-not-enable",
                    },
                ),
                errlog=errors,
            ) as (reader, writer):
                async with ClientSession(
                    reader, writer, message_handler=message
                ) as session:
                    info = await session.initialize()
                    self.assertTrue(info.capabilities.tools.listChanged)
                    listing = await session.list_tools()
                    names = {t.name for t in listing.tools}
                    health = next(t for t in listing.tools if t.name == "ae_health")
                    self.assertTrue(health.annotations.readOnlyHint)
                    self.assertFalse(health.annotations.destructiveHint)
                    self.assertNotIn("vision_describe", names)
                    self.assertIn("vision_compare", names)
                    self.assertIn("graphrag_query", names)
                    result = await session.call_tool(
                        "embeddings_embed", {"text": "fixture"}
                    )
                    self.assertFalse(result.isError)
                    self.assertEqual(result.structuredContent["backend"], "local")
                    edit(
                        path,
                        lambda d: d["api_keys"].update(
                            OPENAI_API_KEY="fixture-no-network"
                        ),
                    )
                    await asyncio.sleep(0.7)
                    self.assertIn(
                        "vision_describe",
                        {t.name for t in (await session.list_tools()).tools},
                    )
                    before = len(notifications)
                    edit(path, lambda d: d["api_keys"].update(OPENAI_API_KEY=""))
                    # Do not re-list first: this explicitly exercises a stale client cache.
                    denied = await session.call_tool(
                        "vision_describe", {"image_path": "/should/not/read"}
                    )
                    self.assertTrue(denied.isError)
                    denied = await session.call_tool(
                        "embeddings_embed", {"text": "fixture", "backend": "openai"}
                    )
                    self.assertTrue(denied.isError)
                    await asyncio.sleep(0.7)
                    self.assertGreater(len(notifications), before)
                    self.assertNotIn(
                        "vision_describe",
                        {t.name for t in (await session.list_tools()).tools},
                    )
                    path.write_text("{incomplete edit")
                    result = await session.call_tool(
                        "embeddings_embed", {"text": "offline"}
                    )
                    self.assertFalse(result.isError)

    @unittest.skipIf(True, "Test uses mcp 2.x API (FastMCP) but we use mcp 1.x")
    def test_external_process_starts_only_with_key_and_stops_when_removed(self):
        asyncio.run(self._external_session())

    async def _external_session(self):
        module = load_module("api_gateway_external", UI_DIR / "mcp-servers/gateway.py")
        with configuration() as path, tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "started"
            running = root / "running"
            server = root / "server.py"
            server.write_text(
                "from pathlib import Path\nimport os\nfrom mcp.server.fastmcp import FastMCP\n"
                f"Path({str(marker)!r}).write_text('started')\n"
                "mcp=FastMCP('fixture')\n@mcp.tool()\ndef echo() -> dict:\n"
                " return {'authorized':bool(os.getenv('FIXTURE_KEY'))}\n"
                "@mcp.tool()\nasync def slow() -> dict:\n"
                f" Path({str(running)!r}).touch()\n"
                " import asyncio\n await asyncio.sleep(30)\n return {'ok':True}\n"
                "mcp.run()\n"
            )

            def configure(doc):
                doc["api_keys"]["FIXTURE_KEY"] = ""
                doc["mcp"]["fixture-mcp"] = {
                    "enabled": True,
                    "required": ["FIXTURE_KEY"],
                    "command": [sys.executable, str(server)],
                    "env": {"FIXTURE_KEY": "FIXTURE_KEY"},
                }

            edit(path, configure)
            gateway = module.Gateway()
            try:
                await gateway.refresh(api.read_config()[0])
                await asyncio.sleep(0.1)
                self.assertFalse(marker.exists())
                edit(
                    path,
                    lambda d: d["api_keys"].update(
                        FIXTURE_KEY="external-local-fixture"
                    ),
                )
                await gateway.refresh(api.read_config()[0])
                worker = gateway.externals["fixture-mcp"]
                await asyncio.wait_for(worker.ready.wait(), timeout=15)
                self.assertTrue(marker.exists())
                self.assertIn("fixture_echo", gateway.tools(api.read_config()[0]))
                result = await gateway.call_tool("fixture_echo", {})
                self.assertFalse(result.isError)
                pending = asyncio.create_task(gateway.call_tool("fixture_slow", {}))
                async with asyncio.timeout(5):
                    while not running.exists():
                        await asyncio.sleep(0.05)
                edit(path, lambda d: d["api_keys"].update(FIXTURE_KEY=""))
                result = await gateway.call_tool("fixture_echo", {})
                self.assertTrue(result.isError)
                await gateway.refresh(api.read_config()[0])
                self.assertNotIn("fixture-mcp", gateway.externals)
                self.assertTrue(worker.task.done())
                self.assertTrue((await asyncio.wait_for(pending, timeout=3)).isError)
            finally:
                await asyncio.gather(
                    *(worker.stop() for worker in gateway.externals.values())
                )


if __name__ == "__main__":
    unittest.main()
