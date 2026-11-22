"""Security regressions reproduced by the 2026-11-19 isolated audit.

All credentials, files, endpoints and lifecycle events below are fixtures.
"""

from __future__ import annotations

import contextlib
import asyncio
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, load_module

SCRIPTS = UI_DIR / "scripts"
SERVERS = UI_DIR / "mcp-servers"
sys.path.insert(0, str(SCRIPTS))


class IsolatedSecurityTest(unittest.TestCase):
    """Keep every test state and credential source under one temporary root."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ae-security-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env = {
            "HOME": str(self.root / "home"),
            "AGENT_ENHANCEMENTS_STATE_DIR": str(self.root / 'ae-state'),
            "AGENT_MEMORY_ROOT": str(self.root / "memory"),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "CODEX_HOME": str(self.root / "codex"),
            "CLAUDE_CONFIG_DIR": str(self.root / "claude"),
            "HERMES_HOME": str(self.root / "hermes"),
            "TASK_OBSERVER_WORKSPACE": str(self.root / "observer"),
            "AGENT_ENHANCEMENTS_API_FILE": str(self.root / "ui.api.json"),
        }
        environment = patch.dict(os.environ, self.env)
        environment.start()
        self.addCleanup(environment.stop)
        self.config = {"version": 1, "api_keys": {}, "connections": {}, "mcp": {}}
        self.write_config()

    def write_config(self):
        Path(self.env["AGENT_ENHANCEMENTS_API_FILE"]).write_text(json.dumps(self.config))

    def module(self, name, source):
        return load_module("security_" + name, source)


class MemorySecurityTests(IsolatedSecurityTest):
    def test_existing_memory_directory_is_private(self):
        directory = Path(self.env["AGENT_MEMORY_ROOT"])
        directory.mkdir(mode=0o755)
        directory.chmod(0o755)
        memory = self.module("memory_mode", SCRIPTS / "memory.py")
        memory.AgentMemory("codex", project="fixture").save("task", "private fixture")
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual((directory / "memory.db").stat().st_mode & 0o777, 0o600)

    def test_memory_database_symlink_cannot_modify_another_database(self):
        target = self.root / "other.db"
        with sqlite3.connect(target) as connection:
            connection.execute("CREATE TABLE protected (value TEXT)")
        before = target.read_bytes()
        directory = Path(self.env["AGENT_MEMORY_ROOT"])
        directory.mkdir()
        (directory / "memory.db").symlink_to(target)
        memory = self.module("memory_symlink", SCRIPTS / "memory.py")
        with self.assertRaises(OSError):
            memory.AgentMemory("codex", project="fixture")
        self.assertEqual(target.read_bytes(), before)

    def test_concurrent_memory_writers_preserve_all_rows_and_private_files(self):
        memory = self.module("memory_concurrency", SCRIPTS / "memory.py")

        def save(number):
            storage = memory.AgentMemory("codex", project="fixture")
            storage.save(f"key-{number}", "fixture", ttl_days=7)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(save, range(24)))
        storage = memory.AgentMemory("codex", project="fixture")
        self.assertEqual(len(storage.list(limit=30)), 24)
        for path in Path(self.env["AGENT_MEMORY_ROOT"]).glob("memory.db*"):
            self.assertEqual(path.stat().st_mode & 0o077, 0)

    def test_bearer_credentials_are_not_saved_by_lifecycle_events(self):
        token = "opaque-authorization-fixture-credential"
        for event_name, field in [("UserPromptSubmit", "prompt"), ("Stop", "last_assistant_message")]:
            event = {"hook_event_name": event_name, "session_id": event_name,
                     "cwd": str(self.root), field: f"Authorization: Bearer {token}"}
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "runtime.py"), "codex"],
                input=json.dumps(event), capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
        with sqlite3.connect(Path(self.env["AGENT_MEMORY_ROOT"]) / "memory.db") as connection:
            values = connection.execute("SELECT value FROM memories").fetchall()
        self.assertTrue(values)
        self.assertTrue(all(token not in value for (value,) in values))


class PreflightSecurityTests(IsolatedSecurityTest):
    def setUp(self):
        super().setUp()
        self.preflight = self.module("preflight", SCRIPTS / "adaptive_preflight.py")

    def test_selector_never_receives_configured_or_bearer_credentials(self):
        configured = "opaque-configured-fixture-credential"
        preflight_key = "opaque-preflight-fixture-credential"
        bearer = "opaque-bearer-fixture-credential"
        self.config["api_keys"]["OPENAI_API_KEY"] = configured
        self.write_config()
        sent = []

        def infer(config, system, user, deadline, api_key):
            sent.append(user)
            return {"decision": "abstain"}

        config = self.preflight.ModelConfig(mode=2, endpoint="https://fixture.invalid/v1", sdk="openai", model="fixture")
        prompt = f"Review database indexes. {configured} {preflight_key} Authorization: Bearer {bearer}"
        with patch.object(self.preflight, "call_model", side_effect=infer):
            self.preflight.run_custom_selection(prompt, config, self.preflight.Deadline(5), preflight_key)
        self.assertEqual(len(sent), 1)
        for secret in (configured, preflight_key, bearer):
            self.assertNotIn(secret, sent[0])
        self.assertIn("database indexes", sent[0])

    def test_selector_response_details_cannot_leak_credentials_into_stderr(self):
        token = "opaque-diagnostic-fixture-credential"
        self.config["api_keys"]["OPENAI_API_KEY"] = token
        self.config["preflight"] = {"mode": 1}
        self.write_config()
        errors = io.StringIO()
        event = {"ae_native_selection": {"decision": "unresolved", "reason": token + "\nforged-log-line"}}
        with contextlib.redirect_stderr(errors):
            result = self.preflight.preflight_context("codex", "fixture", event, lambda *args: "fallback")
        self.assertEqual(result.context, "fallback")
        self.assertNotIn(token, errors.getvalue())
        self.assertEqual(len(errors.getvalue().splitlines()), 1)

    def test_late_abstain_result_falls_back_after_deadline(self):
        self.config["preflight"] = {
            "mode": 2, "endpoint": "https://fixture.invalid/v1", "sdk": "openai", "model": "fixture"}
        self.config["api_keys"]["PREFLIGHT_API_KEY"] = "fixture-only"
        self.write_config()
        os.environ["AE_PREFLIGHT_DEADLINE_MS"] = "100"

        def delayed(*args):
            time.sleep(0.15)
            return {"decision": "abstain"}

        registry = SimpleNamespace(paged_search=lambda *args, **kwargs: {"cards": []})
        with patch.object(self.preflight, "call_model", side_effect=delayed), \
                patch.object(self.preflight, "_registry", return_value=registry), \
                patch.object(self.preflight, "_catalog_overview", return_value="Fixture catalog"), \
                contextlib.redirect_stderr(io.StringIO()):
            result = self.preflight.preflight_context("codex", "fixture", {}, lambda *args: "fallback")
        self.assertEqual(result.effective_mode, 0)
        self.assertEqual(result.context, "fallback")

    def test_legacy_key_sources_and_model_json_are_ignored_at_runtime(self):
        directory = self.preflight.config_dir()
        directory.mkdir(parents=True)
        (directory / "model.json").write_text(json.dumps({
            "adaptive_preflight_mode": 2, "endpoint": "https://fixture.invalid/v1",
            "sdk": "openai", "model": "fixture"}))
        key_file = directory / "preflight.key"
        key_file.write_text("legacy-file-fixture")
        key_file.chmod(0o600)
        with patch.dict(os.environ, {
                "AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY": "ambient-env-fixture",
                "AGENT_ENHANCEMENTS_MODEL_FILE": str(directory / "model.json")}):
            config = self.preflight.load_model_config()
            self.assertEqual((config.mode, config.diagnosis), (0, ""))
            forced = self.preflight.ModelConfig(
                mode=2, endpoint="https://fixture.invalid/v1", sdk="openai", model="fixture")
            self.assertEqual(self.preflight.resolve_api_key(forced), "")

    def test_migration_never_imports_a_symlinked_legacy_key(self):
        api = self.module("migrate_symlink", SCRIPTS / "api_config.py")
        directory = self.root / "legacy"
        directory.mkdir()
        target = self.root / "other-owner-key-fixture"
        target.write_text("fixture-only")
        target.chmod(0o600)
        (directory / "preflight.key").symlink_to(target)
        result = api.migrate(legacy_dir=directory)
        self.assertNotIn("legacy_preflight_key", result)
        self.assertNotIn("fixture-only", Path(self.env["AGENT_ENHANCEMENTS_API_FILE"]).read_text())

    def test_migration_never_imports_symlinked_legacy_selector_settings(self):
        api = self.module("migrate_model_link", SCRIPTS / "api_config.py")
        directory = self.root / "legacy"
        directory.mkdir()
        target = self.root / "outside-settings.json"
        target.write_text(json.dumps({"adaptive_preflight_mode": 1}))
        (directory / "model.json").symlink_to(target)

        api.migrate(legacy_dir=directory)

        self.assertNotIn("preflight", json.loads(api.config_path().read_text()))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX file types required")
    def test_nonregular_configuration_returns_a_diagnosis(self):
        path = Path(self.env["AGENT_ENHANCEMENTS_API_FILE"])
        path.unlink()
        os.mkfifo(path)
        output = subprocess.check_output([sys.executable, str(SCRIPTS / "api_config.py"),
                                          "status"], text=True, timeout=3)
        self.assertEqual(json.loads(output)["configuration"], "config_unavailable_or_invalid")

    def test_non_utf8_api_config_falls_back_with_a_diagnosis(self):
        Path(self.env["AGENT_ENHANCEMENTS_API_FILE"]).write_bytes(b"\xffinvalid")
        config = self.preflight.load_model_config()
        self.assertEqual(config.mode, 0)
        self.assertIn("ui_api_json_invalid", config.diagnosis)

    def test_expired_deadline_prevents_protocol_compatibility_request(self):
        calls = []

        def post(*args):
            calls.append(args)
            time.sleep(0.12)
            raise self.preflight.PreflightError("http_400")

        with patch.object(self.preflight, "_post_json", side_effect=post):
            with self.assertRaises(self.preflight.PreflightError):
                self.preflight.call_openai_compatible(
                    "https://fixture.invalid/v1", "fixture", "fixture", "fixture", "fixture",
                    self.preflight.Deadline(0.1),
                )
        self.assertEqual(len(calls), 1)

    def test_slow_response_body_cannot_extend_preflight_socket_deadline(self):
        class SlowBody(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                body = b'{"decision":"abstain"}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    for byte in body:
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        time.sleep(0.03)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowBody)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        start = time.monotonic()
        with self.assertRaises(self.preflight.PreflightError):
            self.preflight._post_json(f"http://127.0.0.1:{server.server_port}/", {}, {}, 0.1)
        self.assertLess(time.monotonic() - start, 0.45)


class FfmpegSecurityTests(IsolatedSecurityTest):
    def setUp(self):
        super().setUp()
        self.ffmpeg = self.module("ffmpeg", SERVERS / "ffmpeg-mcp" / "server.py")

    def test_allowed_root_does_not_include_prefix_siblings(self):
        allowed = self.root / "allowed"
        allowed.mkdir()
        outside = self.root / "allowed-private" / "output.mp4"
        with patch.object(self.ffmpeg, "_allowed_roots", return_value=[allowed]):
            target, error = self.ffmpeg._validate_path(str(outside), must_exist=False)
        self.assertIsNone(target)
        self.assertIn("outside", error)

    def test_concat_rejects_newline_directives_in_input_filenames(self):
        first = self.root / "clip'\nfile 'injected.mp4"
        second = self.root / "clip2.mp4"
        first.touch()
        second.touch()
        invoked = []

        def execute(command):
            invoked.append(command)
            return {"ok": True}

        with patch.object(self.ffmpeg, "_run", side_effect=execute):
            result = self.ffmpeg.concat([str(first), str(second)], str(self.root / "out.mp4"))
        self.assertIn("error", result)
        self.assertEqual(invoked, [])

    def test_concat_does_not_clobber_predictable_scratch_symlink(self):
        clips = [self.root / "one.mp4", self.root / "two.mp4"]
        for clip in clips:
            clip.touch()
        protected = self.root / "protected.txt"
        protected.write_text("protected fixture")
        scratch = self.root / "output.concat.txt"
        scratch.symlink_to(protected)
        output = self.root / "output.mp4"

        def execute(command):
            # Stand in for ffmpeg: concat verifies the output was produced.
            output.write_bytes(b"fixture video")
            return {"ok": True}

        with patch.object(self.ffmpeg, "_run", side_effect=execute):
            result = self.ffmpeg.concat([str(p) for p in clips], str(output))
        self.assertTrue(result.get("ok"), result)
        self.assertEqual(protected.read_text(), "protected fixture")
        self.assertTrue(scratch.is_symlink())


class CredentialRedirectTests(IsolatedSecurityTest):
    def test_authenticated_mcp_requests_do_not_forward_keys_across_redirects(self):
        received = []
        redirected = []

        class Sink(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                received.append(self.headers.get("Authorization"))
                raw = json.dumps({"data": [{"embedding": [1.0]}], "choices": [{"message": {"content": "fixture"}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        sink = ThreadingHTTPServer(("127.0.0.1", 0), Sink)
        sink_thread = threading.Thread(target=sink.serve_forever, daemon=True)
        sink_thread.start()
        self.addCleanup(sink.server_close)
        self.addCleanup(sink.shutdown)

        class Redirect(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                redirected.append(self.path)
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{sink.server_port}/receive")
                self.send_header("Content-Length", "0")
                self.end_headers()

        origin = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
        threading.Thread(target=origin.serve_forever, daemon=True).start()
        self.addCleanup(origin.server_close)
        self.addCleanup(origin.shutdown)
        self.config["api_keys"]["OPENAI_API_KEY"] = "fixture-key-never-forward"
        self.config["connections"]["OPENAI_BASE_URL"] = f"http://127.0.0.1:{origin.server_port}/v1"
        self.write_config()
        image = self.root / "fixture.png"
        # Real PNG magic so vision's content sniffing accepts the file and the
        # request actually reaches the redirecting origin.
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        embeddings = self.module("redirect_embeddings", SERVERS / "embeddings-mcp" / "server.py")
        vision = self.module("redirect_vision", SERVERS / "vision-mcp" / "server.py")
        calls = {"embeddings": lambda: embeddings.embed("fixture", backend="openai"),
                 "vision": lambda: vision.describe(str(image))}
        for name, call in calls.items():
            with self.subTest(call=name):
                before = len(redirected)
                response = call()
                self.assertIn("error", response)
                # The request must reach the origin so the redirect guard is
                # what stops it, not an earlier input validation failure.
                self.assertGreater(len(redirected), before, response)
        self.assertEqual(received, [])


class GatewayHealthSecurityTests(IsolatedSecurityTest):
    def test_builtin_rechecks_readiness_after_awaiting_backend_lock(self):
        gateway_module = self.module("queued_gateway", SERVERS / "gateway.py")

        async def check(*, in_executor_queue):
            gateway = gateway_module.Gateway()
            server = "embeddings-mcp"
            called = []

            async def call(*args):
                called.append(args)
                return {"ok": True}

            gateway.modules[server] = SimpleNamespace(mcp=SimpleNamespace(call_tool=call))
            tool = gateway_module.types.Tool(
                name="embed", inputSchema={"type": "object", "properties": {}},
            )
            gateway.definitions[server] = [tool]
            def revoke():
                self.config["mcp"][server] = {"enabled": False}
                self.write_config()

            if in_executor_queue:
                submit = asyncio.to_thread

                async def revoke_before_running(function, *args):
                    revoke()
                    return await submit(function, *args)

                with patch.object(asyncio, "to_thread", revoke_before_running):
                    response = await gateway.call_tool("embeddings_embed", {})
            else:
                async with gateway.module_locks[server]:
                    pending = asyncio.create_task(gateway.call_tool("embeddings_embed", {}))
                    await asyncio.sleep(0)
                    revoke()
                response = await asyncio.wait_for(pending, timeout=3)
            self.assertTrue(response.isError)
            self.assertEqual(called, [])

        for in_executor_queue in (False, True):
            with self.subTest(in_executor_queue=in_executor_queue):
                self.config["mcp"].clear()
                self.write_config()
                asyncio.run(check(in_executor_queue=in_executor_queue))

    def test_health_redacts_secrets_before_truncation_in_every_field(self):
        gateway_module = self.module("health_gateway", SERVERS / "gateway.py")
        from mcp import types

        secret = "opaque-health-fixture-" + "x" * 240
        self.config["api_keys"]["OPENAI_API_KEY"] = secret
        self.config["mcp"]["fixture-mcp"] = {"command": [sys.executable]}
        self.write_config()

        async def check():
            gateway = gateway_module.Gateway()
            ready = asyncio.Event()
            ready.set()
            calls = []

            async def call(*args):
                calls.append(args)
                return types.CallToolResult(content=[types.TextContent(
                    type="text", text=json.dumps({"status": secret, "reason": secret}),
                )])

            gateway.externals["fixture-mcp"] = SimpleNamespace(
                tools=[types.Tool(name=name, inputSchema={"type": "object"})
                       for name in ("fixture", "other")] + [
                           types.Tool(name="sensitive_metadata", description=secret,
                                      inputSchema={"type": "object"}),
                       ],
                ready=ready, call=call, task=asyncio.get_running_loop().create_future(),
            )
            config, _ = gateway_module.read_config()
            gateway.fingerprints["fixture-mcp"] = gateway_module.external_fingerprint(
                config["mcp"]["fixture-mcp"], config)
            tools = await gateway.list_tools()
            self.assertNotIn("fixture_sensitive_metadata", {tool.name for tool in tools})
            result = await gateway.call_tool("ae_health", {})
            self.assertEqual(calls, [("health", {})])
            return result

        response = asyncio.run(check())
        rendered = json.dumps(response.model_dump(mode="json"))
        self.assertNotIn(secret, rendered)
        self.assertNotIn(secret[:100], rendered)
        self.assertIn("[redacted]", rendered)


class AuditLogSecurityTests(IsolatedSecurityTest):
    def setUp(self):
        super().setUp()
        # Scripts resolve their audit destination relative to installation.
        # Copy only the utilities and their shared redactor into a fixture.
        self.scripts = self.root / "installation" / "scripts"
        self.scripts.mkdir(parents=True)
        for name in ("consent-gate.sh", "audit-trail.sh", "api_config.py"):
            shutil.copyfile(SCRIPTS / name, self.scripts / name)
        self.audit = self.scripts.parent / "memory" / "audit"

    def invoke(self, script, arguments, input_text=""):
        return subprocess.run(["bash", str(self.scripts / script), *arguments],
                              input=input_text, text=True, capture_output=True, timeout=10)

    def test_audit_and_consent_logs_are_private_under_permissive_umask(self):
        old = os.umask(0o022)
        try:
            decision = self.invoke("audit-trail.sh", ["decision", "fixture", "safe fixture"])
            consent = self.invoke("consent-gate.sh", ["fixture", "synthetic-reference"], input_text="")
        finally:
            os.umask(old)
        self.assertEqual(decision.returncode, 0, decision.stderr)
        self.assertEqual(consent.returncode, 1, consent.stderr)
        self.assertEqual(self.audit.stat().st_mode & 0o777, 0o700)
        for path in self.audit.glob("*.jsonl"):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_audit_and_consent_text_never_persists_configured_credentials(self):
        token = "opaque-audit-fixture-credential"
        self.config["api_keys"]["OPENAI_API_KEY"] = token
        self.write_config()
        decision = self.invoke("audit-trail.sh", ["decision", "fixture", token])
        consent = self.invoke("consent-gate.sh", [token, "synthetic-reference"], input_text="")
        self.assertEqual(decision.returncode, 0, decision.stderr)
        self.assertEqual(consent.returncode, 1, consent.stderr)
        for path in self.audit.glob("*.jsonl"):
            self.assertNotIn(token, path.read_text())

    def test_log_symlinks_cannot_redirect_or_modify_other_files(self):
        self.audit.mkdir(parents=True)
        for script, filename, arguments in (
            ("audit-trail.sh", "decisions.jsonl", ["decision", "fixture", "safe fixture"]),
            ("consent-gate.sh", "consent.jsonl", ["fixture", "synthetic-reference"]),
        ):
            with self.subTest(script=script):
                target = self.root / (script + ".personal")
                target.write_text("preserve personal data")
                (self.audit / filename).symlink_to(target)
                result = self.invoke(script, arguments, input_text="y\n")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(target.read_text(), "preserve personal data")

    def test_consent_output_redacts_credentials_before_confirmation(self):
        token = "opaque-confirmation-fixture-credential"
        self.config["api_keys"]["OPENAI_API_KEY"] = token
        self.write_config()
        result = self.invoke("consent-gate.sh", [token, "synthetic-reference"], input_text="")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(token, result.stdout)


class ObserverSecurityTests(IsolatedSecurityTest):
    def test_observation_fields_redact_configured_and_bearer_credentials(self):
        token = "opaque-observer-configured-fixture"
        bearer = "opaque-observer-bearer-fixture"
        self.config["api_keys"]["OPENAI_API_KEY"] = token
        self.write_config()
        observer = self.module("observer", SCRIPTS / "task-observer.py")
        workspace = Path(self.env["TASK_OBSERVER_WORKSPACE"])
        result = observer.log_observation(
            workspace, title="fixture privacy regression", issue=token,
            improvement="redact credentials", principle=f"Authorization: Bearer {bearer}",
        )
        observations = list(observer.log_dir(workspace).glob("[0-9]*.md"))
        self.assertEqual(len(observations), 1, result)
        content = observations[0].read_text()
        self.assertNotIn(token, content)
        self.assertNotIn(bearer, content)

    def test_bootstrap_ensures_workspace_is_private(self):
        observer = self.module("observer_modes", SCRIPTS / "task-observer.py")
        workspace = Path(self.env["TASK_OBSERVER_WORKSPACE"])
        workspace.mkdir(mode=0o755)
        workspace.chmod(0o755)
        self.assertEqual(observer.bootstrap_workspace(workspace), "ok")
        self.assertEqual(workspace.stat().st_mode & 0o777, 0o700)


class CredentialRedactionTests(IsolatedSecurityTest):
    def test_every_key_of_a_multi_key_reference_is_redacted(self):
        api = self.module("provider_redact", SCRIPTS / "api_config.py")
        self.config = {"version": 2, "api_keys": {"TAVILY_API_KEY": [
            "opaque-first-provider-fixture", " opaque-second-provider-fixture "]},
            "connections": {}, "mcp": {}}
        self.write_config()
        config, _ = api.read_config()
        # A cooling-down key is still a secret and must still be redacted.
        api.report_key_failure("TAVILY_API_KEY", "opaque-second-provider-fixture", 60)
        cleaned = api.redact(
            "upstream error opaque-first-provider-fixture / opaque-second-provider-fixture", config)
        self.assertEqual(cleaned, "upstream error [redacted] / [redacted]")

    def test_sk_pattern_needs_a_left_boundary_and_still_redacts_keys(self):
        # Final audit 2026-11-20 (P2): words ending in "sk" followed by a
        # slug (task-, risk-, desk-) were redacted, corrupting tool results.
        api = self.module("sk_boundary", SCRIPTS / "api_config.py")
        ordinary = ("see /repo/task-observer-improvements-v2/README and "
                    "risk-assessment-for-production-rollout or desk-booking-service-frontend")
        self.assertEqual(api.redact(ordinary), ordinary)
        for leaked in ("sk-proj-abcdefghijklmnop0123", "sk-ant-api03-abcdefghijklmnop",
                       "sk-abcdefghijklmnopqrstu"):
            for context in (f"key {leaked} end", f"KEY={leaked}", f'"{leaked}"', f"x:{leaked}"):
                self.assertNotIn(leaked, api.redact(context), context)

    def test_common_provider_credential_formats_are_redacted(self):
        # Final audit 2026-11-20 (P1): user-pasted credentials in these formats
        # reached the Mode 2 selector (and memory) unredacted. Fixtures are
        # synthetic and assembled at runtime.
        api = self.module("provider_formats", SCRIPTS / "api_config.py")
        body = "Ab3dE5gH7jK9mN1pQ3sT5vX7zB9cD1fG3hJ5kL7"
        hexed = "0123456789abcdef0123456789abcdef"
        leaks = {
            "gitlab": "glpat-" + body[:20], "tavily": "tvly-dev-" + body[:24],
            "firecrawl": "fc-" + hexed, "google": "AIza" + body[:35],
            "slack": "xoxb-" + "123456789012-" + body[:24], "huggingface": "hf_" + body[:34],
            "groq": "gsk_" + body[:40], "xai": "xai-" + body[:40], "npm": "npm_" + body[:36],
            "stripe": "sk_live_" + body[:24], "stripe-restricted": "rk_live_" + body[:24],
            "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0." + body[:30],
        }
        for name, secret in leaks.items():
            with self.subTest(format=name):
                self.assertNotIn(secret, api.redact(f"please use {secret} for this"))
        pem = ("-----BEGIN OPENSSH PRIVATE KEY-----\n" + body + "\n"
               "-----END OPENSSH PRIVATE KEY-----")
        self.assertNotIn(body, api.redact(f"key:\n{pem}\nthanks"))
        uri = api.redact("connect to postgres://report:" + body[:12] + "@db.internal:5432/sales")
        self.assertNotIn(body[:12], uri)
        self.assertIn("postgres://", uri)
        self.assertIn("@db.internal:5432/sales", uri)
        ordinary = ("fix fc-barcelona-fan-page, the xai-sdk docs, hf_hub_download(), "
                    "npm_config_cache and https://example.com/path@v1 or user@example.com")
        self.assertEqual(api.redact(ordinary), ordinary)

    def test_personal_search_provider_file_is_never_opened(self):
        """A sentinel search_providers.json at the checkout root stays untouched."""
        api = self.module("provider_isolation", SCRIPTS / "api_config.py")
        sentinel = str(api.ROOT / "search_providers.json")
        real_open = open
        opened = []

        def guarded(file, *args, **kwargs):
            if str(file) == sentinel:
                opened.append(file)
            return real_open(file, *args, **kwargs)

        # Path.read_text/Path.open resolve io.open at call time.
        with patch("builtins.open", guarded), patch("io.open", guarded):
            api.status()
            api.redact("text")
            api.server_state("search-mcp")
            api.migrate(legacy_dir=self.root / "no-legacy")
        self.assertEqual(opened, [])
        source = (SCRIPTS / "api_config.py").read_text()
        gateway = (SERVERS / "gateway.py").read_text()
        self.assertNotIn("search_providers", source + gateway)


class SearchCacheSecurityTests(IsolatedSecurityTest):
    def test_public_search_caches_are_private_and_isolated_by_memory_root(self):
        for server in ("arxiv-mcp", "google-news-mcp"):
            with self.subTest(server=server), patch("tempfile.gettempdir", return_value=str(self.root)):
                with patch.dict(os.environ, {"AGENT_MEMORY_ROOT": str(self.root / "first-user")}):
                    first = self.module(server + "_first", SERVERS / server / "server.py")
                with patch.dict(os.environ, {"AGENT_MEMORY_ROOT": str(self.root / "second-user")}):
                    second = self.module(server + "_second", SERVERS / server / "server.py")
                first._cache_put("fixture-key", "private-fixture-body")
                self.assertIsNone(second._cache_get("fixture-key"))
                self.assertEqual(first.CACHE_DIR.stat().st_mode & 0o777, 0o700)
                self.assertEqual((first.CACHE_DIR / "fixture-key.xml").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
