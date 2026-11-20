"""Adaptive preflight (Modes 0/1/2) regression tests - CONTRACT 8.5.

Covers the architecture review 2026-11-19 implementation gates:
- model.json contract: strict mode typing, Mode 2 field validation,
  duplicate-field rejection, reload-per-prompt, diagnosis-on-fallback.
- Mode 0 parity: missing file, explicit 0 and every failure path render
  the legacy discovery cards byte-identically; memory effects run
  exactly once; zero egress.
- Selection output contract: parse/validate every decision shape.
- Exact-ID resolution: typed ids never bind to a same-named entry
  (audit 12 alias probe), server-level MCP visibility, skill file
  proof, fictitious-id rejection, required-vs-optional distinction.
- Mode 2 end-to-end against a local TLS fixture: structured output
  request, lookup round, compatibility re-issue, no-retry on HTTP
  errors, deadline enforcement, refusal, invalid JSON.
- Mode 1: adapter-supplied native selection, validated by the same
  handler; never auto-switches to Mode 2.
- Live-model tests are opt-in (AE_PREFLIGHT_LIVE=1), mirroring the
  AE_MCP_NETWORK_TESTS pattern.
"""

import json
import os
import socket
import sqlite3
import subprocess
import ssl
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR, REPO_DIR, load_module, run

SCRIPTS = UI_DIR / "scripts"
RUNTIME = SCRIPTS / "runtime.py"
sys.path.insert(0, str(SCRIPTS))

PROMPT = ("Query laporan melambat. Periksa kenapa planner memilih scan "
          "tabel dan ukur pengaruh penambahan indeks. Stack PostgreSQL.")


def fixture_ca(directory: Path):
    """A local CA + server certificate so the https endpoint contract is
    exercised against 127.0.0.1 without touching any system trust.

    The CA carries explicit CA:TRUE + keyCertSign extensions: OpenSSL
    3.5.7 (the bundled TLS of Python 3.13) rejects CA certificates
    without a key usage extension when they vouch for a server cert.
    """
    if subprocess.run(["which", "openssl"], capture_output=True).returncode:
        raise unittest.SkipTest("openssl unavailable for the TLS fixture")
    cert, key = directory / "srv.pem", directory / "srv-key.pem"
    ca, ca_key = directory / "ca.pem", directory / "ca-key.pem"
    ext = directory / "ext.cnf"
    ext.write_text(
        "subjectAltName=IP:127.0.0.1\n"
        "basicConstraints=CA:FALSE\n"
        "keyUsage=digitalSignature,keyEncipherment\n"
        "extendedKeyUsage=serverAuth\n"
    )
    commands = [
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(ca_key), "-out", str(ca), "-days", "2",
         "-subj", "/CN=AE test CA",
         "-addext", "basicConstraints=critical,CA:TRUE",
         "-addext", "keyUsage=critical,keyCertSign,cRLSign"],
        ["openssl", "req", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(key), "-out", str(directory / "srv.csr"),
         "-subj", "/CN=127.0.0.1"],
        ["openssl", "x509", "-req", "-in", str(directory / "srv.csr"),
         "-CA", str(ca), "-CAkey", str(ca_key), "-CAcreateserial",
         "-out", str(cert), "-days", "2", "-extfile", str(ext)],
    ]
    for command in commands:
        done = subprocess.run(command, capture_output=True)
        assert done.returncode == 0, done.stderr.decode()[:200]
    for path in (cert, key, ca, ca_key):
        path.chmod(0o600)
    return cert, key, ca


class SelectorFixture:
    """Scripted https chat-completions endpoint recording every request."""

    def __init__(self, responses, delay=0.0):
        self.responses = list(responses)
        self.delay = delay
        self.requests = []

        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                record = {
                    "received_at": time.monotonic(),
                    "path": self.path,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "payload": body,
                }
                outer.requests.append(record)
                if outer.delay:
                    time.sleep(outer.delay)
                item = outer.responses.pop(0) if outer.responses else None
                if item is None:
                    status, document = 200, {"choices": [
                        {"message": {"content": "{}"}}]}
                elif isinstance(item, tuple):
                    status, document = item
                else:  # a bare response document means HTTP 200
                    status, document = 200, item
                raw = json.dumps(document).encode()
                record["response"] = document
                record["status"] = status
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    record["completed_at"] = time.monotonic()
                except (BrokenPipeError, ConnectionResetError):
                    # A client that hit its deadline walks away; the
                    # response nobody reads must not spam the suite.
                    pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.cert, self.key, self.ca = fixture_ca(Path(tempfile.mkdtemp()))
        context.load_cert_chain(self.cert, self.key)
        self.httpd.socket = context.wrap_socket(self.httpd.socket,
                                                server_side=True)
        self.port = self.httpd.server_port
        threading.Thread(target=self.httpd.serve_forever,
                         daemon=True).start()

    @property
    def endpoint(self):
        """OpenAI-protocol base (includes /v1)."""
        return f"https://127.0.0.1:{self.port}/v1"

    @property
    def endpoint_base(self):
        """Anthropic-protocol base (the SDK appends /v1/messages)."""
        return f"https://127.0.0.1:{self.port}"

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    @staticmethod
    def selection(decision, **extra):
        return {"choices": [{"message": {"content": json.dumps(
            {"decision": decision, **extra})}}]}


class PreflightTestCase(unittest.TestCase):
    """Common isolation: fresh module, temp model.json, empty ui.api.json."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.model_file = self.root / "model.json"
        self.env = {
            "AGENT_ENHANCEMENTS_STATE_DIR": str(self.root / 'ae-state'),
            "AGENT_ENHANCEMENTS_MODEL_FILE": str(self.model_file),
            "AGENT_ENHANCEMENTS_API_FILE": str(self.root / "ui.api.json"),
            "AGENT_MEMORY_ROOT": str(self.root / "memory"),
            "HOME": str(self.root / "home"),
            "XDG_CONFIG_HOME": str(self.root / "home" / ".config"),
            "AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY": "fixture-key",
        }
        for key, value in self.env.items():
            os.environ[key] = value
        self.module = load_module("adaptive_preflight_test", SCRIPTS / "adaptive_preflight.py")

    def tearDown(self):
        for key in self.env:
            os.environ.pop(key, None)

    def write_model(self, document):
        self.model_file.write_text(json.dumps(document))

    def runtime_event(self, event, agent="codex", env=None):
        merged = dict(self.env)
        merged.update(env or {})
        return run(
            [sys.executable, str(RUNTIME), agent],
            env=merged, input_text=json.dumps(event),
        )

    @staticmethod
    def context_of(stdout):
        if not stdout.strip():
            return ""
        return json.loads(stdout)["hookSpecificOutput"]["additionalContext"]

    def memory_rows(self):
        database = Path(self.env["AGENT_MEMORY_ROOT"]) / "memory.db"
        with sqlite3.connect(database) as conn:
            return conn.execute(
                "SELECT key FROM memories WHERE key LIKE 'session:%'"
            ).fetchall()


# ---------------------------------------------------------------------------
# model.json contract (review 9)
# ---------------------------------------------------------------------------


class ModelConfigTests(PreflightTestCase):
    def _check(self, content, mode, diagnosis=""):
        self.model_file.write_text(content)
        config = self.module.load_model_config()
        self.assertEqual(config.mode, mode, content)
        if diagnosis:
            self.assertIn(diagnosis, config.diagnosis, content)
        else:
            self.assertEqual(config.diagnosis, "", content)

    def test_missing_file_is_silent_mode_0(self):
        self.assertEqual(self.module.load_model_config().mode, 0)
        self.assertEqual(self.module.load_model_config().diagnosis, "")

    def test_valid_modes(self):
        self._check('{"adaptive_preflight_mode": 0}', 0)
        self._check('{"adaptive_preflight_mode": 1}', 1)
        self._check('{"adaptive_preflight_mode": 2, "endpoint": '
                    '"https://openrouter.ai/api/v1", "sdk": "openai", '
                    '"model": "provider/model"}', 2)

    def test_mode_must_be_exact_integer(self):
        for bad in ("true", '"0"', '"2"', "2.0", "3", "-1", "null"):
            self._check(f'{{"adaptive_preflight_mode": {bad}}}', 0,
                        "mode_not_0_1_or_2")

    def test_mode2_field_validation(self):
        cases = [
            '{"adaptive_preflight_mode": 2}',
            '{"adaptive_preflight_mode": 2, "sdk": "openai", "model": "x"}',
            '{"adaptive_preflight_mode": 2, "endpoint": "http://h.example", '
            '"sdk": "openai", "model": "x"}',
            '{"adaptive_preflight_mode": 2, "endpoint": "ftp://h.example", '
            '"sdk": "openai", "model": "x"}',
            '{"adaptive_preflight_mode": 2, "endpoint": '
            '"https://user:pw@h.example", "sdk": "openai", "model": "x"}',
        ]
        for content in cases:
            self._check(content, 0, "endpoint")
        self._check('{"adaptive_preflight_mode": 2, "endpoint": '
                    '"https://h.example", "sdk": "cohere", "model": "x"}',
                    0, "sdk")
        self._check('{"adaptive_preflight_mode": 2, "endpoint": '
                    '"https://h.example", "sdk": "anthropic"}', 0, "model")

    def test_duplicate_fields_rejected(self):
        self._check('{"adaptive_preflight_mode": 0, '
                    '"adaptive_preflight_mode": 1}', 0, "model_json_invalid")

    def test_broken_json_and_non_object_rejected(self):
        self._check("{broken", 0, "model_json_invalid")
        self._check("[]", 0, "not_an_object")
        self._check('"mode 2 please"', 0, "not_an_object")

    def test_mode_0_and_1_ignore_custom_fields(self):
        self._check('{"adaptive_preflight_mode": 1, "endpoint": '
                    '"http://ignored.example", "sdk": "bogus", "model": ""}', 1)
        self._check('{"adaptive_preflight_mode": 0, "endpoint": "nope"}', 0)

    def test_config_is_reread_per_call(self):
        self._check('{"adaptive_preflight_mode": 0}', 0)
        self._check('{"adaptive_preflight_mode": 1}', 1)
        self.model_file.unlink()
        self.assertEqual(self.module.load_model_config().mode, 0)

    def test_default_path_follows_checkout_state_and_ignores_global_xdg(self):
        os.environ.pop("AGENT_ENHANCEMENTS_MODEL_FILE")
        home = self.root / 'ae-state/config'
        home.mkdir(parents=True, exist_ok=True)
        (home / "model.json").write_text('{"adaptive_preflight_mode": 1}')
        self.assertEqual(self.module.load_model_config().mode, 1)
        (home / "model.json").unlink()
        self.assertEqual(self.module.load_model_config().mode, 0)


# ---------------------------------------------------------------------------
# Selection output contract (review 11)
# ---------------------------------------------------------------------------


class SelectionContractTests(PreflightTestCase):
    def parse(self, payload):
        return self.module.parse_selection(payload)

    def test_valid_shapes(self):
        selection = self.parse({"decision": "selected", "items": [
            {"id": "skill:docx", "required": True, "reason": "doc work"},
            {"id": "mcp:ffmpeg-mcp"},  # required defaults to True
        ]})
        self.assertEqual([i.id for i in selection.items],
                         ["skill:docx", "mcp:ffmpeg-mcp"])
        self.assertTrue(selection.items[1].required)

        self.assertEqual(self.parse({"decision": "abstain"}).decision, "abstain")
        lookup = self.parse({"decision": "lookup",
                             "queries": ["postgres indexing", "video probe"]})
        self.assertEqual(lookup.queries, ["postgres indexing", "video probe"])
        self.assertEqual(self.parse({"decision": "unresolved",
                                     "reason": "no eq capability"}).reason,
                         "no eq capability")

    def test_invalid_shapes_rejected(self):
        bad_payloads = [
            None,
            [],
            "selected",
            {},
            {"decision": "bogus"},
            {"decision": "selected", "items": []},
            {"decision": "selected", "items": [{"id": ""}]},
            {"decision": "selected", "items": [{"id": 42}]},
            {"decision": "selected", "items": [{"id": "x", "required": "yes"}]},
            {"decision": "selected", "items": [
                {"id": f"skill:s{i}"} for i in range(13)]},
            {"decision": "lookup", "queries": []},
            {"decision": "lookup", "queries": [""]},
            {"decision": "lookup", "queries": [42]},
            {"decision": "lookup", "queries": [f"q{i}" for i in range(5)]},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(self.module.PreflightError):
                    self.parse(payload)

    def test_unknown_extra_fields_are_tolerated(self):
        selection = self.parse({"decision": "abstain", "extra": "ignored",
                                "temperature": 0.7})
        self.assertEqual(selection.decision, "abstain")


# ---------------------------------------------------------------------------
# Exact-ID resolution + internal read surface (review 12 / 8.3)
# ---------------------------------------------------------------------------


class ExactIdResolutionTests(PreflightTestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_module("registry_preflight_test",
                                   SCRIPTS / "registry.py")

    def test_typed_id_never_aliases_to_same_named_entry(self):
        # The audit's alias probe: capability:task-observer used to bind
        # to skill:task-observer through the name surface.
        capability = self.module._registry().find_entry(
            "capability:task-observer")
        self.assertEqual(capability["id"], "capability:task-observer")
        self.assertEqual(capability["type"], "capability")
        skill = self.module._registry().find_entry("skill:task-observer")
        self.assertEqual(skill["id"], "skill:task-observer")
        # The CLI name surface keeps its legacy behavior.
        self.assertEqual(self.module._registry().find_entry("task-observer")["id"],
                         "skill:task-observer")

    def test_cli_show_respects_typed_ids(self):
        rc, out, _ = run([sys.executable, str(SCRIPTS / "registry.py"),
                          "show", "capability:task-observer", "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["id"], "capability:task-observer")
        rc, out, _ = run([sys.executable, str(SCRIPTS / "registry.py"),
                          "show", "skill:task-observer", "--json"])
        self.assertEqual(json.loads(out)["id"], "skill:task-observer")

    def test_fictitious_id_is_not_found(self):
        self.assertIsNone(self.module._registry().find_entry(
            "skill:does-not-exist-xyz"))
        self.assertIsNone(self.module._registry().find_entry(""))

    def test_paged_search_finds_long_tail_item(self):
        page = self.module._registry().paged_search(
            "PostgreSQL EXPLAIN ANALYZE optimize query indexing slow query "
            "plan", limit=5)
        self.assertLessEqual(page["sent"], 5)
        self.assertIn("skill:postgresql-optimization",
                      [card["id"] for card in page["cards"]])
        self.assertTrue(page["has_more"])
        self.assertGreater(page["matched"], page["sent"])
        # every card carries readiness so blockers stay visible
        for card in page["cards"]:
            self.assertIn("ready", card)

    def test_paged_list_is_stable_and_counted(self):
        first = self.module._registry().paged_list(entry_type="mcp",
                                                   offset=0, limit=10)
        again = self.module._registry().paged_list(entry_type="mcp",
                                                   offset=0, limit=10)
        self.assertEqual([c["id"] for c in first["cards"]],
                         [c["id"] for c in again["cards"]])
        self.assertEqual(first["matched"], 40)
        self.assertTrue(first["has_more"])
        ids = [c["id"] for c in first["cards"]]
        self.assertEqual(ids, sorted(ids))
        # prefix filtering narrows without hiding the count
        page = self.module._registry().paged_list(prefix="mcp:ffmpeg",
                                                   limit=10)
        self.assertEqual(page["matched"], 1)
        self.assertEqual(page["cards"][0]["id"], "mcp:ffmpeg-mcp")

    def test_registry_revision_tracks_source_changes(self):
        revision = self.module.registry_revision()
        index = SCRIPTS.parent / "skills" / "all-skills.json"
        stamp = index.stat()
        os.utime(index, (stamp.st_atime + 5, stamp.st_mtime + 5))
        try:
            self.assertNotEqual(self.module.registry_revision(), revision)
        finally:
            os.utime(index, (stamp.st_atime, stamp.st_mtime))


# ---------------------------------------------------------------------------
# Package resolution and rendering (review 11 / 7C)
# ---------------------------------------------------------------------------


class PackageResolutionTests(PreflightTestCase):
    def select(self, items):
        return self.module.parse_selection({"decision": "selected",
                                            "items": items})

    def test_skill_resolves_direct_read_with_file_proof(self):
        package, unmet = self.module.build_package(self.select(
            [{"id": "skill:postgresql-optimization"}]))
        self.assertEqual(unmet, [])
        item = package[0]
        self.assertEqual(item.delivery, "direct_read")
        self.assertTrue(Path(item.ref).is_file())

    def test_directory_link_alone_does_not_prove_a_loaded_skill(self):
        registry = self.module._registry()
        linked = next(e for e in registry.load_skill_entries()
                      if e.get("natively_linked_by_default")
                      and (REPO_DIR / e["source_path"]).is_file())
        with tempfile.TemporaryDirectory() as targets:
            (Path(targets) / linked["name"]).mkdir()
            with patch.dict(os.environ, {"AGENT_SKILLS_NATIVE_TARGETS": targets}):
                package, unmet = self.module.build_package(self.select(
                    [{"id": linked["id"]}]))
        self.assertEqual(unmet, [])
        self.assertEqual(package[0].delivery, "direct_read")

    def test_plugin_resolves_guide(self):
        package, unmet = self.module.build_package(self.select(
            [{"id": "plugin:openmontage", "required": False}]))
        self.assertEqual(unmet, [])
        self.assertEqual(package[0].type, "plugin")
        self.assertEqual(package[0].delivery, "direct_read")
        self.assertTrue(package[0].ref.endswith("SKILL.md"))

    def test_required_plugin_runtime_without_entrypoint_falls_back(self):
        package, unmet = self.module.build_package(self.select(
            [{"id": "plugin:openmontage"}]))
        self.assertEqual(package, [])
        self.assertEqual(len(unmet), 1)
        self.assertIn("runtime", unmet[0])

    def test_mcp_visibility_gates_delivery(self):
        # Server visibility alone cannot prove delivery in a host session.
        package, unmet = self.module.build_package(self.select(
            [{"id": "mcp:ffmpeg-mcp"}]))
        self.assertEqual(package, [])
        self.assertEqual(len(unmet), 1)
        # An unconfigured external server is honestly unavailable.
        package, unmet = self.module.build_package(self.select(
            [{"id": "mcp:serper-mcp", "required": False}]))
        self.assertEqual(package, [])
        self.assertEqual(unmet, [])

    def test_visible_server_does_not_prove_real_or_fictitious_tools(self):
        package, unmet = self.module.build_package(self.select(
            [{"id": "tool:ffmpeg-mcp/ffmpeg_probe"},
             {"id": "tool:ffmpeg-mcp/ae_missing_fixture_tool"},
             {"id": "tool:vision-mcp/vision_describe"}]))
        self.assertEqual(package, [])
        self.assertEqual(len(unmet), 3)
        package, unmet = self.module.build_package(self.select(
            [{"id": "tool:unknown-server/some_tool", "required": False}]))
        self.assertEqual(package, [])

    def host_event(self):
        """The private bridge view, matching actual OpenCode 2 ToolInfo fields."""
        path = Path(self.env["AGENT_ENHANCEMENTS_API_FILE"])
        revision = f"{path.stat().st_size}:{path.stat().st_mtime_ns}" if path.exists() else "missing"
        return {"session_id": "fixture-session", "ae_host_inventory": {
            "host": "opencode", "session_id": "fixture-session",
            "source": "ctx.tool.list", "observed_at": time.time(),
            "api_revision": revision, "gateway": "agent-enhancements",
            "tools": [{"name": "ffmpeg_probe", "id": "agent-enhancements_ffmpeg_probe",
                       "namespace": "agent-enhancements", "codemode": True,
                       "input_schema": {"type": "object", "properties": {"path": {"type": "string"}},
                                        "required": ["path"]}}],
        }}

    def test_exact_host_tool_proof_maps_to_the_executable_reference(self):
        event = self.host_event()
        package, unmet = self.module.build_package(self.select([
            {"id": "tool:ffmpeg-mcp/ffmpeg_probe"},
            {"id": "tool:vision-mcp/vision_describe", "required": False},
            {"id": "tool:ffmpeg-mcp/ae_missing_fixture_tool", "required": False},
        ]), agent="opencode", event=event)
        self.assertEqual(unmet, [])
        self.assertEqual(len(package), 1)
        self.assertEqual(package[0].ref, 'tools["agent-enhancements"].ffmpeg_probe')
        self.assertEqual(package[0].delivery, "callable")

    def test_mcp_delivery_names_only_tools_observed_in_this_session(self):
        package, unmet = self.module.build_package(self.select([
            {"id": "mcp:ffmpeg-mcp"}]), agent="opencode", event=self.host_event())
        self.assertEqual(unmet, [])
        self.assertEqual(package[0].ref, 'tools["agent-enhancements"].ffmpeg_probe')

    def test_host_inventory_cannot_cross_sessions_or_survive_config_changes(self):
        for mutate in (lambda e: e.update(session_id="another-session"),
                       lambda e: e["ae_host_inventory"].update(observed_at=0),
                       lambda e: e["ae_host_inventory"].update(api_revision="stale")):
            event = self.host_event()
            mutate(event)
            with self.assertRaises(self.module.PreflightError):
                self.module.build_package(self.select([
                    {"id": "tool:ffmpeg-mcp/ffmpeg_probe"}]), agent="opencode", event=event)

    def test_wrong_namespace_server_prefix_or_schema_is_not_callable(self):
        for key, value in [("namespace", "other-gateway"), ("input_schema", None),
                           ("id", "other-server_ffmpeg_probe")]:
            event = self.host_event()
            event["ae_host_inventory"]["tools"][0][key] = value
            package, unmet = self.module.build_package(self.select([
                {"id": "tool:ffmpeg-mcp/ffmpeg_probe"}]), agent="opencode", event=event)
            self.assertEqual(package, [])
            self.assertEqual(len(unmet), 1)

    def test_cached_cloud_tool_is_rejected_when_its_credential_is_absent(self):
        event = self.host_event()
        event["ae_host_inventory"]["tools"].append({
            "name": "vision_describe", "id": "agent-enhancements_vision_describe",
            "namespace": "agent-enhancements", "codemode": True,
            "input_schema": {"type": "object"},
        })
        package, unmet = self.module.build_package(self.select([
            {"id": "tool:vision-mcp/vision_describe"}]), agent="opencode", event=event)
        self.assertEqual(package, [])
        self.assertEqual(len(unmet), 1)

    def test_required_unavailable_goes_to_unmet(self):
        _, unmet = self.module.build_package(self.select(
            [{"id": "mcp:serper-mcp"},
             {"id": "skill:totally-fictitious"}]))
        self.assertEqual(len(unmet), 2)

    def test_render_preserves_more_than_eight_compact_required_items(self):
        items = [self.module.ResolvedItem(
            id=f"skill:s{i}", type="skill", ref=f"/s/{i}/SKILL.md",
            delivery="direct_read", purpose="Inspect", required=True,
        ) for i in range(12)]
        text = self.module.render_package(items, "rev0123456789")
        budget = self.module._budget()
        self.assertLessEqual(budget.approx_tokens(text), budget.MAX_SKILL_CARDS)
        for item in items:
            self.assertIn(item.id + " ", text)
            self.assertIn(item.ref, text)
        self.assertNotIn("trimmed", text)

    def test_render_rejects_overflow_instead_of_losing_required_references(self):
        items = [
            self.module.ResolvedItem(
                id=f"skill:fixture-{i}", type="skill",
                ref="/long/path/to/some/checkout/skills/fixture/" * 5 + "SKILL.md",
                delivery="direct_read",
                purpose=("Purpose line that keeps going and going to "
                         "stress the token budget " * 3)[:120],
                note="note " * 20, required=True)
            for i in range(12)
        ]
        with self.assertRaisesRegex(self.module.PreflightError,
                                    "package_budget_exceeded"):
            self.module.render_package(items, "rev0123456789")

    def test_render_drops_optional_items_before_required_instructions(self):
        required = [self.module.ResolvedItem(
            id=f"skill:s{i}", type="skill", ref=f"/s/{i}/SKILL.md",
            delivery="direct_read", purpose="Inspect", required=True,
        ) for i in range(10)]
        optional = self.module.ResolvedItem(
            id="skill:optional", type="skill", ref="/" + "long/" * 400,
            delivery="direct_read", purpose="Optional", required=False,
        )
        text = self.module.render_package([optional, *required], "rev")
        self.assertNotIn(optional.id, text)
        for item in required:
            self.assertIn(item.id + " ", text)
            self.assertIn(item.ref, text)

    def test_render_marks_optional_items(self):
        item = self.module.ResolvedItem(
            id="mcp:ffmpeg-mcp", type="mcp", ref="ffmpeg-mcp",
            delivery="callable", purpose="Editing video non-linearly.",
            required=False)
        text = self.module.render_package([item], "rev")
        self.assertIn("(optional)", text)
        self.assertIn("use: ffmpeg-mcp", text.replace("  use:", "use:"))


# ---------------------------------------------------------------------------
# Mode 0 parity (review 16, stage-1 gate)
# ---------------------------------------------------------------------------


class Mode0ParityTests(PreflightTestCase):
    def setUp(self):
        super().setUp()
        self.event = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "parity-session",
            "cwd": str(REPO_DIR),
            "prompt": PROMPT,
        }
        self.runtime = load_module("runtime_parity_test", RUNTIME)

    def legacy_render(self):
        return self.runtime.skill_context("codex", PROMPT)

    def test_missing_file_renders_legacy_cards(self):
        rc, out, err = self.runtime_event(self.event)
        self.assertEqual(rc, 0, err)
        self.assertEqual(err, "")
        self.assertEqual(self.context_of(out), self.legacy_render())
        self.assertIn("skill candidates", self.context_of(out))

    def test_explicit_mode_0_renders_legacy_cards(self):
        self.write_model({"adaptive_preflight_mode": 0})
        rc, out, err = self.runtime_event(self.event)
        self.assertEqual(rc, 0, err)
        self.assertEqual(err, "")
        self.assertEqual(self.context_of(out), self.legacy_render())

    def test_invalid_config_renders_legacy_cards_with_diagnosis(self):
        self.model_file.write_text('{"adaptive_preflight_mode": "2"}')
        rc, out, err = self.runtime_event(self.event)
        self.assertEqual(rc, 0)
        self.assertEqual(self.context_of(out), self.legacy_render())
        self.assertIn("model.json rejected", err)

    def test_mode2_invalid_settings_never_touch_the_network(self):
        self.write_model({"adaptive_preflight_mode": 2,
                          "endpoint": "http://insecure.example",
                          "sdk": "openai", "model": "x"})
        with patch.object(socket, "socket") as blocked:
            blocked.side_effect = AssertionError("egress in mode 0 fallback")
            result = self.module.preflight_context(
                "codex", PROMPT, {}, fallback=lambda a, p: self.legacy_render())
        self.assertEqual(result.context, self.legacy_render())
        self.assertEqual(result.effective_mode, 0)
        self.assertIn("endpoint", result.fallback_reason)

    def test_memory_effect_runs_exactly_once_per_mode(self):
        for mode_file in (None, {"adaptive_preflight_mode": 0}):
            if mode_file:
                self.write_model(mode_file)
            else:
                self.model_file.unlink(missing_ok=True)
            rc, out, err = self.runtime_event(self.event)
            self.assertEqual(rc, 0, err)
            rows = [row for row in self.memory_rows()
                    if row[0].endswith(":task")]
            self.assertEqual(len(rows), 1, mode_file)

    def test_mode0_never_opens_a_socket(self):
        # In-process proof that the default path is egress-free.
        with patch.object(socket, "socket") as blocked:
            blocked.side_effect = AssertionError("egress on Mode 0")
            context = self.runtime.prompt_context("codex", PROMPT, {})
        self.assertEqual(context, self.legacy_render())

    def test_private_bridge_envelope_keeps_mode0_context_and_one_memory_effect(self):
        rc, out, err = run([sys.executable, str(RUNTIME), "opencode", "--bridge"],
                           env=self.env, input_text=json.dumps(self.event))
        self.assertEqual(rc, 0, err)
        envelope = json.loads(out)
        expected = self.runtime.skill_context("opencode", PROMPT)
        self.assertEqual(envelope["context"], expected)
        self.assertEqual(envelope["fallback"], expected)
        tasks = [r for r in self.memory_rows() if r[0].endswith(":task")]
        self.assertEqual(len(tasks), 1)


# ---------------------------------------------------------------------------
# Mode 1: adapter-supplied native selection (review 5 / 10)
# ---------------------------------------------------------------------------


class Mode1Tests(PreflightTestCase):
    def setUp(self):
        super().setUp()
        self.write_model({"adaptive_preflight_mode": 1})
        self.event = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "mode1-session",
            "cwd": str(REPO_DIR),
            "prompt": PROMPT,
        }
        self.runtime = load_module("runtime_mode1_test", RUNTIME)
        self.legacy = self.runtime.skill_context("codex", PROMPT)

    def test_missing_native_selection_falls_back_without_network(self):
        with patch.object(socket, "socket") as blocked:
            blocked.side_effect = AssertionError("mode 1 must not egress")
            result = self.module.preflight_context(
                "codex", PROMPT, {}, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.context, self.legacy)
        self.assertEqual(result.effective_mode, 0)
        self.assertIn("mode1_native_selection_unavailable",
                      result.fallback_reason)

    def test_valid_native_selection_renders_package(self):
        event = dict(self.event, ae_native_selection={
            "decision": "selected",
            "items": [{"id": "skill:postgresql-optimization",
                       "reason": "planner analysis"}],
        })
        with patch.object(socket, "socket") as blocked:
            blocked.side_effect = AssertionError("mode 1 must not egress")
            result = self.module.preflight_context(
                "codex", PROMPT, event, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.effective_mode, 1)
        self.assertIn("skill:postgresql-optimization", result.context)
        self.assertNotIn("skill candidates", result.context)

    def test_invalid_native_selection_falls_back(self):
        event = dict(self.event, ae_native_selection={"decision": "bogus"})
        result = self.module.preflight_context(
            "codex", PROMPT, event, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.context, self.legacy)
        self.assertEqual(result.effective_mode, 0)

    def test_auto_on_opencode_is_unsupported_even_with_a_fixture_payload(self):
        event = dict(self.event, ae_native_selection={"decision": "abstain"})
        result = self.module.preflight_context(
            "opencode", PROMPT, event, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.context, self.legacy)
        self.assertEqual(result.fallback_reason, "mode1_host_unsupported")

    def test_native_handoff_must_be_a_final_selection(self):
        event = dict(self.event, ae_native_selection={
            "decision": "lookup", "queries": ["PostgreSQL"],
        })
        result = self.module.preflight_context(
            "codex", PROMPT, event, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.context, self.legacy)
        self.assertEqual(result.fallback_reason, "mode1_selection_not_final")

    def test_registry_change_during_selection_discards_the_package(self):
        event = dict(self.event, ae_native_selection={
            "decision": "selected", "items": [{"id": "skill:postgresql-optimization"}],
        })
        with patch.object(self.module, "registry_revision", side_effect=["before", "after"]):
            result = self.module.preflight_context(
                "codex", PROMPT, event, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.context, self.legacy)
        self.assertEqual(result.fallback_reason, "registry_changed")

    def test_registry_change_during_render_also_discards_the_package(self):
        event = dict(self.event, ae_native_selection={
            "decision": "selected", "items": [{"id": "skill:postgresql-optimization"}],
        })
        with patch.object(self.module, "registry_revision", side_effect=["same", "same", "changed"]):
            result = self.module.preflight_context(
                "codex", PROMPT, event, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.context, self.legacy)
        self.assertEqual(result.fallback_reason, "registry_changed")

    def test_required_package_overflow_returns_the_complete_legacy_fallback(self):
        item = self.module.ResolvedItem(
            id="skill:fixture", type="skill", ref="/long/" * 400 + "SKILL.md",
            delivery="direct_read", purpose="Inspect", required=True,
        )
        event = dict(self.event, ae_native_selection={
            "decision": "selected", "items": [{"id": "skill:fixture"}],
        })
        with patch.object(self.module, "build_package", return_value=([item], [])):
            result = self.module.preflight_context(
                "codex", PROMPT, event, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.context, self.legacy)
        self.assertEqual(result.effective_mode, 0)
        self.assertEqual(result.fallback_reason, "package_budget_exceeded")

    def test_result_expiring_during_render_is_discarded(self):
        event = dict(self.event, ae_native_selection={
            "decision": "selected", "items": [{"id": "skill:postgresql-optimization"}],
        })
        render = self.module.render_package

        def slow_render(*args, **kwargs):
            time.sleep(0.12)
            return render(*args, **kwargs)

        with patch.dict(os.environ, {"AE_PREFLIGHT_DEADLINE_MS": "100"}), \
                patch.object(self.module, "render_package", side_effect=slow_render):
            result = self.module.preflight_context(
                "codex", PROMPT, event, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.context, self.legacy)
        self.assertEqual(result.fallback_reason, "timeout")

    def test_mode1_never_switches_to_mode2(self):
        # Even with a fully configured custom endpoint stored alongside,
        # a failing Mode 1 stays on Mode 0 for the turn (review 14).
        self.write_model({"adaptive_preflight_mode": 1,
                          "endpoint": "https://openrouter.ai/api/v1",
                          "sdk": "openai", "model": "provider/free"})
        with patch.object(socket, "socket") as blocked:
            blocked.side_effect = AssertionError("no auto mode switch")
            result = self.module.preflight_context(
                "codex", PROMPT, {}, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.effective_mode, 0)

    def test_native_selection_required_item_unavailable_falls_back(self):
        event = dict(self.event, ae_native_selection={
            "decision": "selected",
            "items": [{"id": "mcp:serper-mcp"}],
        })
        result = self.module.preflight_context(
            "codex", PROMPT, event, fallback=lambda a, p: self.legacy)
        self.assertEqual(result.context, self.legacy)
        self.assertIn("required_capability_unavailable",
                      result.fallback_reason)


# ---------------------------------------------------------------------------
# Mode 2: custom model through the runtime (review 9 / 12 / 13)
# ---------------------------------------------------------------------------


class Mode2EndToEndTests(PreflightTestCase):
    def setUp(self):
        super().setUp()
        self.event = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "mode2-session",
            "cwd": str(REPO_DIR),
            "prompt": PROMPT,
        }
        self.runtime = load_module("runtime_mode2_test", RUNTIME)
        self.legacy = self.runtime.skill_context("codex", PROMPT)
        self.fixture = None

    def tearDown(self):
        if self.fixture:
            self.fixture.stop()
        super().tearDown()

    def start(self, responses, delay=0.0):
        self.fixture = SelectorFixture(responses, delay=delay)
        self.write_model({"adaptive_preflight_mode": 2,
                          "endpoint": self.fixture.endpoint,
                          "sdk": "openai",
                          "model": "fixture/selector"})
        return self.fixture

    def run_event(self, env=None):
        merged = {"SSL_CERT_FILE": str(self.fixture.ca)}
        merged.update(env or {})
        return self.runtime_event(self.event, env=merged)

    def test_selected_package_replaces_the_candidate_cards(self):
        fixture = self.start([SelectorFixture.selection("selected", items=[
            {"id": "skill:postgresql-optimization", "reason": "planner"},
            {"id": "plugin:openmontage", "required": False},
        ])])
        rc, out, err = self.run_event()
        self.assertEqual(rc, 0, err)
        self.assertEqual(err, "")
        context = self.context_of(out)
        self.assertNotIn("skill candidates", context)
        self.assertIn("preflight: selected capability package", context)
        self.assertIn("skill:postgresql-optimization", context)
        self.assertIn("(optional)", context)
        self.assertEqual(len(fixture.requests), 1)
        request = fixture.requests[0]
        self.assertEqual(request["path"], "/v1/chat/completions")
        self.assertEqual(request["headers"]["authorization"],
                         "Bearer fixture-key")
        self.assertEqual(request["payload"]["model"], "fixture/selector")
        self.assertEqual(request["payload"]["response_format"]["type"],
                         "json_schema")
        self.assertTrue(
            request["payload"]["response_format"]["json_schema"]["strict"])

    def test_lookup_round_uses_local_catalog_then_selects(self):
        fixture = self.start([
            SelectorFixture.selection("lookup", queries=[
                "PostgreSQL EXPLAIN ANALYZE optimize query indexing"]),
            SelectorFixture.selection("selected", items=[
                {"id": "skill:postgresql-optimization"}]),
        ])
        rc, out, err = self.run_event()
        self.assertEqual(rc, 0, err)
        self.assertIn("skill:postgresql-optimization", self.context_of(out))
        self.assertEqual(len(fixture.requests), 2)
        # Round two carries the local lookup results, not a repeated ask.
        second_user = fixture.requests[1]["payload"]["messages"][1]["content"]
        self.assertIn("skill:postgresql-optimization", second_user)

    def test_abstain_renders_no_context(self):
        fixture = self.start([SelectorFixture.selection("abstain")])
        rc, out, err = self.run_event()
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.strip(), "")
        self.assertEqual(err, "")
        self.assertEqual(len(fixture.requests), 1)

    def test_unresolved_falls_back_with_diagnosis(self):
        self.start([SelectorFixture.selection("unresolved")])
        rc, out, err = self.run_event()
        self.assertEqual(rc, 0)
        self.assertEqual(self.context_of(out), self.legacy)
        self.assertIn("selection_unresolved", err)

    def test_invalid_json_falls_back_without_retry(self):
        fixture = self.start([{"choices": [{"message": {
            "content": "definitely not json"}}]}])
        rc, out, err = self.run_event()
        self.assertEqual(self.context_of(out), self.legacy)
        self.assertIn("invalid_json", err)
        self.assertEqual(len(fixture.requests), 1)

    def test_refusal_falls_back(self):
        fixture = self.start([{"choices": [{"message": {
            "refusal": "I cannot help with that"}}]}])
        rc, out, err = self.run_event()
        self.assertEqual(self.context_of(out), self.legacy)
        self.assertIn("refusal", err)

    def test_http_error_falls_back_without_retry(self):
        for status in (429, 500, 503):
            with self.subTest(status=status):
                fixture = self.start([(status, {"error": "boom"})])
                rc, out, err = self.run_event()
                self.assertEqual(self.context_of(out), self.legacy)
                self.assertIn(f"http_{status}", err)
                self.assertEqual(len(fixture.requests), 1,
                                 "SDK-style auto-retry is forbidden")

    def test_response_format_compatibility_reissue(self):
        fixture = self.start([
            (400, {"error": {"message": "response_format not supported"}}),
            SelectorFixture.selection("selected", items=[
                {"id": "skill:postgresql-optimization"}]),
        ])
        rc, out, err = self.run_event()
        self.assertEqual(rc, 0, err)
        self.assertIn("skill:postgresql-optimization", self.context_of(out))
        self.assertEqual(len(fixture.requests), 2)
        self.assertIn("response_format", fixture.requests[0]["payload"])
        self.assertNotIn("response_format", fixture.requests[1]["payload"])
        self.assertIn("Output JSON only",
                      fixture.requests[1]["payload"]["messages"][0]["content"])

    def test_deadline_enforced_and_fallback_is_fast(self):
        self.start([SelectorFixture.selection("selected", items=[
            {"id": "skill:docx"}])], delay=5.0)
        started = time.monotonic()
        rc, out, err = self.run_event(env={"AE_PREFLIGHT_DEADLINE_MS": "400"})
        elapsed = time.monotonic() - started
        self.assertEqual(rc, 0)
        self.assertEqual(self.context_of(out), self.legacy)
        self.assertIn("timeout", err)
        self.assertLess(elapsed, 4.0,
                        "fallback must beat the host hook timeout")

    def test_missing_key_falls_back_before_any_request(self):
        fixture = self.start([SelectorFixture.selection("abstain")])
        rc, out, err = self.run_event(
            env={"AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY": ""})
        self.assertEqual(self.context_of(out), self.legacy)
        self.assertIn("api_key_unavailable", err)
        self.assertEqual(fixture.requests, [])

    def test_required_unavailable_capability_falls_back(self):
        self.start([SelectorFixture.selection("selected", items=[
            {"id": "mcp:serper-mcp", "reason": "web search"}])])
        rc, out, err = self.run_event()
        self.assertEqual(self.context_of(out), self.legacy)
        self.assertIn("required_capability_unavailable", err)

    def test_optional_unavailable_capability_is_dropped(self):
        self.start([SelectorFixture.selection("selected", items=[
            {"id": "skill:postgresql-optimization"},
            {"id": "mcp:serper-mcp", "required": False},
        ])])
        rc, out, err = self.run_event()
        self.assertEqual(rc, 0, err)
        context = self.context_of(out)
        self.assertIn("skill:postgresql-optimization", context)
        self.assertNotIn("serper-mcp", context)

    def test_fictitious_required_id_falls_back(self):
        self.start([SelectorFixture.selection("selected", items=[
            {"id": "skill:not-in-the-catalog"}])])
        rc, out, err = self.run_event()
        self.assertEqual(self.context_of(out), self.legacy)
        self.assertIn("required_capability_unavailable", err)

    def test_memory_still_saved_exactly_once_on_mode2_fallback(self):
        self.start([(500, {"error": "boom"})])
        rc, out, err = self.run_event()
        self.assertEqual(rc, 0)
        rows = [row for row in self.memory_rows()
                if row[0].endswith(":task")]
        self.assertEqual(len(rows), 1)

    def test_opencode_text_bridge_receives_the_package(self):
        self.start([SelectorFixture.selection("selected", items=[
            {"id": "skill:postgresql-optimization"}])])
        merged = dict(self.env)
        merged["SSL_CERT_FILE"] = str(self.fixture.ca)
        proc = subprocess.run(
            [sys.executable, str(RUNTIME), "opencode", "--text"],
            input=json.dumps(self.event), capture_output=True, text=True,
            env=merged, timeout=30,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("preflight: selected capability package", proc.stdout)
        self.assertNotIn("fallback", proc.stderr)


class AnthropicProtocolTests(PreflightTestCase):
    def test_anthropic_messages_shape(self):
        fixture = SelectorFixture([{
            "content": [{"type": "text", "text": json.dumps({
                "decision": "selected",
                "items": [{"id": "skill:docx"}]})}],
            "stop_reason": "end_turn",
        }])
        self.addCleanup(fixture.stop)
        self.write_model({"adaptive_preflight_mode": 2,
                          "endpoint": fixture.endpoint_base,
                          "sdk": "anthropic",
                          "model": "fixture/claude"})
        event = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "anthropic-session",
            "cwd": str(REPO_DIR),
            "prompt": "convert this report to a word document",
        }
        rc, out, err = run(
            [sys.executable, str(RUNTIME), "codex"],
            env={**self.env, "SSL_CERT_FILE": str(fixture.ca)},
            input_text=json.dumps(event),
        )
        self.assertEqual(rc, 0, err)
        self.assertEqual(err, "")
        self.assertIn("skill:docx", self.context_of(out))
        request = fixture.requests[0]
        self.assertEqual(request["path"], "/v1/messages")
        self.assertEqual(request["headers"]["x-api-key"], "fixture-key")
        self.assertEqual(request["headers"]["anthropic-version"],
                         "2023-06-01")
        payload = request["payload"]
        self.assertEqual(payload["model"], "fixture/claude")
        self.assertIn("Output JSON only", payload["system"])
        self.assertEqual(payload["messages"][0]["role"], "user")

    def test_redirect_is_refused(self):
        fixture = SelectorFixture([])
        self.addCleanup(fixture.stop)
        # A 302 makes urllib's no-redirect handler raise HTTPError 302.
        fixture.responses.append((302, {}))
        self.write_model({"adaptive_preflight_mode": 2,
                          "endpoint": fixture.endpoint,
                          "sdk": "openai", "model": "fixture"})
        event = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "redirect-session",
            "cwd": str(REPO_DIR), "prompt": "probe",
        }
        rc, out, err = run(
            [sys.executable, str(RUNTIME), "codex"],
            env={**self.env, "SSL_CERT_FILE": str(fixture.ca)},
            input_text=json.dumps(event),
        )
        self.assertEqual(rc, 0)
        self.assertIn("http_302", err)
        self.assertEqual(len(fixture.requests), 1)


# ---------------------------------------------------------------------------
# Credential resolution (review 9 / 14)
# ---------------------------------------------------------------------------


class CredentialResolverTests(PreflightTestCase):
    def test_env_var_wins(self):
        os.environ["AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY"] = "from-env"
        self.assertEqual(
            self.module.resolve_api_key("https://any.example/api/v1"),
            "from-env")

    def test_key_file_requires_owner_only_permissions(self):
        os.environ.pop("AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY", None)
        directory = self.module.config_dir()
        directory.mkdir(parents=True, exist_ok=True)
        key_file = directory / "preflight.key"
        key_file.write_text("file-secret\nsecond-line-ignored\n")
        key_file.chmod(0o600)
        self.assertEqual(
            self.module.resolve_api_key("https://127.0.0.1:9/v1"),
            "file-secret")
        key_file.chmod(0o644)
        self.assertEqual(
            self.module.resolve_api_key("https://127.0.0.1:9/v1"), "",
            "a group/other-readable key file must be refused")

    def test_no_secret_leaks_into_status_report(self):
        self.write_model({"adaptive_preflight_mode": 2,
                          "endpoint": "https://openrouter.example/api/v1",
                          "sdk": "openai", "model": "provider/free"})
        os.environ["AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY"] = "super-secret"
        report = json.dumps(self.module.status_report())
        self.assertIn("api_key_present", report)
        self.assertNotIn("super-secret", report)
        os.environ["AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY"] = ""
        report = self.module.status_report()
        self.assertFalse(report["api_key_present"])


# ---------------------------------------------------------------------------
# Opt-in live model check (mirrors AE_MCP_NETWORK_TESTS)
# ---------------------------------------------------------------------------


class LiveModelTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("AE_PREFLIGHT_LIVE") == "1",
        "set AE_PREFLIGHT_LIVE=1 (and provide a real model.json + key) "
        "for live selector calls")
    def test_live_selection_or_abstain(self):
        module = load_module("adaptive_preflight_live",
                             SCRIPTS / "adaptive_preflight.py")
        config = module.load_model_config()
        self.assertEqual(config.mode, 2,
                         "live check needs a real user-scope model.json")
        deadline = module.Deadline(8.0)
        selection = module.run_custom_selection(
            PROMPT, config, deadline,
            module.resolve_api_key(config.endpoint))
        self.assertIn(selection.decision, ("selected", "abstain"))
        if selection.decision == "selected":
            items, unmet = module.build_package(selection)
            self.assertEqual(unmet, [])
            self.assertTrue(items)


if __name__ == "__main__":
    unittest.main()
