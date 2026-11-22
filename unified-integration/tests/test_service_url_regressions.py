"""Regressions for credential transport and network error handling in the
embeddings-mcp and vision-mcp cloud adapters.

All credentials, endpoints and images below are fixtures; no test opens a
real network connection.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module

SCRIPTS = UI_DIR / "scripts"
SERVERS = UI_DIR / "mcp-servers"
sys.path.insert(0, str(SCRIPTS))

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 32
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32
BMP = b"BM" + b"\x00" * 32


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class _Opener:
    """Stand-in for urllib's opener: records requests, returns or raises."""

    def __init__(self, outcome):
        self.outcome = outcome
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return _Response(self.outcome)


class CredsNetTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ae-creds-net-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env = {
            "HOME": str(self.root / "home"),
            "AGENT_ENHANCEMENTS_STATE_DIR": str(self.root / "ae-state"),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "AGENT_ENHANCEMENTS_API_FILE": str(self.root / "ui.api.json"),
        }
        environment = patch.dict(os.environ, self.env)
        environment.start()
        self.addCleanup(environment.stop)
        self.config = {"version": 1, "api_keys": {"OPENAI_API_KEY": "fixture-key"},
                       "connections": {}, "mcp": {}}
        self.write_config()
        self.embeddings = load_module("creds_net_embeddings", SERVERS / "embeddings-mcp" / "server.py")
        self.vision = load_module("creds_net_vision", SERVERS / "vision-mcp" / "server.py")

    def write_config(self):
        Path(self.env["AGENT_ENHANCEMENTS_API_FILE"]).write_text(json.dumps(self.config))

    def set_base(self, url):
        self.config["connections"]["OPENAI_BASE_URL"] = url
        self.write_config()

    def image(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return str(path)

    def with_opener(self, module, outcome):
        opener = _Opener(outcome)
        patcher = patch.object(module.urllib.request, "build_opener", return_value=opener)
        patcher.start()
        self.addCleanup(patcher.stop)
        return opener

    def forbid_sockets(self):
        def refuse(*args, **kwargs):
            raise AssertionError("a socket was opened")

        for target in ("create_connection", "socket"):
            patcher = patch.object(socket, target, side_effect=refuse)
            patcher.start()
            self.addCleanup(patcher.stop)


class SafeServiceUrlTests(unittest.TestCase):
    def test_https_and_loopback_http_only(self):
        api = load_module("creds_net_api_config", SCRIPTS / "api_config.py")
        allowed = [
            "https://api.openai.com/v1",
            "https://proxy.example/v1",
            "http://127.0.0.1:8080/v1",
            "http://localhost:9000",
            "http://[::1]:8000/v1",
        ]
        refused = [
            "http://api.openai.com/v1",
            "http://example.com/v1",
            "http://10.0.0.5/v1",
            "ftp://api.openai.com/v1",
            "https://user:pass@api.openai.com/v1",
            "https://api.openai.com/v1#frag",
            "https:///v1",
            "",
            None,
            "http://[::1",
        ]
        for url in allowed:
            with self.subTest(url=url):
                self.assertTrue(api.safe_service_url(url))
        for url in refused:
            with self.subTest(url=url):
                self.assertFalse(api.safe_service_url(url))


class CleartextEndpointTests(CredsNetTest):
    def test_embeddings_refuses_remote_http_before_any_socket(self):
        self.set_base("http://example.com/v1")
        self.forbid_sockets()
        result = self.embeddings.embed("fixture", backend="openai")
        self.assertIn("error", result)
        self.assertIn("OPENAI_BASE_URL", result["error"])

    def test_vision_refuses_remote_http_before_any_socket(self):
        self.set_base("http://api.openai.com/v1")
        self.forbid_sockets()
        result = self.vision.describe(self.image("fixture.png", PNG))
        self.assertIn("error", result)
        self.assertIn("OPENAI_BASE_URL", result["error"])

    def test_loopback_http_still_reaches_the_opener(self):
        self.set_base("http://127.0.0.1:9/v1")
        body = json.dumps({"data": [{"embedding": [0.5, 0.5]}]}).encode()
        opener = self.with_opener(self.embeddings, body)
        result = self.embeddings.embed("fixture", backend="openai")
        self.assertNotIn("error", result)
        self.assertEqual(opener.requests[0].full_url, "http://127.0.0.1:9/v1/embeddings")


class VisionMediaTypeTests(CredsNetTest):
    def sent_media(self, opener):
        payload = json.loads(opener.requests[0].data)
        url = payload["messages"][0]["content"][1]["image_url"]["url"]
        return url.split(";", 1)[0]

    def test_media_type_follows_magic_bytes_not_extension(self):
        reply = json.dumps({"choices": [{"message": {"content": "fixture"}}]}).encode()
        for name, data, expected in (
            ("anim.gif", GIF, "data:image/gif"),
            ("photo.webp", WEBP, "data:image/webp"),
            ("mislabelled.jpg", PNG, "data:image/png"),
        ):
            with self.subTest(name=name):
                opener = self.with_opener(self.vision, reply)
                result = self.vision.describe(self.image(name, data))
                self.assertEqual(result.get("mode"), "openai", result)
                self.assertEqual(self.sent_media(opener), expected)

    def test_bmp_is_refused_without_upload(self):
        opener = self.with_opener(self.vision, b"{}")
        result = self.vision.describe(self.image("scan.bmp", BMP))
        self.assertIn("error", result)
        self.assertIn("bmp", result["error"])
        self.assertEqual(opener.requests, [])


class NetworkErrorTests(CredsNetTest):
    def test_embeddings_read_failures_return_actionable_errors(self):
        import http.client

        for outcome in (TimeoutError("read timed out"), ConnectionResetError(),
                        http.client.IncompleteRead(b"")):
            with self.subTest(outcome=type(outcome).__name__):
                self.with_opener(self.embeddings, outcome)
                result = self.embeddings.embed("fixture", backend="openai")
                self.assertIn("timed out", result["error"])

    def test_embeddings_malformed_json_returns_error(self):
        for body in (b"not json", b"{}", b'{"data": [{}]}', b'{"data": []}', b'{"data": [1]}'):
            with self.subTest(body=body):
                self.with_opener(self.embeddings, body)
                result = self.embeddings.embed("fixture", backend="openai")
                self.assertIn("unexpected response", result["error"])

    def test_vision_read_failures_and_malformed_replies_return_error(self):
        import http.client

        png = self.image("fixture.png", PNG)
        for outcome in (TimeoutError("read timed out"), OSError("reset"),
                        http.client.IncompleteRead(b""), b'{"choices": []}',
                        b'{"choices": null}'):
            with self.subTest(outcome=repr(outcome)):
                self.with_opener(self.vision, outcome)
                result = self.vision.describe(png)
                self.assertIn("Vision API call failed", result["error"])

    def test_vision_fallback_reports_corrupt_image(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow is not installed")
        self.config["api_keys"] = {}
        self.write_config()
        result = self.vision.describe(self.image("truncated.png", PNG))
        self.assertIn("cannot decode image", result["error"])


if __name__ == "__main__":
    unittest.main()
