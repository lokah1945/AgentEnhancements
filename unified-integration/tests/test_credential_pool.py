"""ui.api.json v2 credentials, one-time migration, per-request key pool,
first-party search adapters and dependency-aware readiness.

Every test owns a temporary ui.api.json (AGENT_ENHANCEMENTS_API_FILE) with
synthetic keys. No provider is contacted: the search adapters' single
network seam (``_transport``) is replaced by a recorder, and the real stdio
gateway check never calls a credentialed tool.
"""

import asyncio
import contextlib
import io
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
import api_config as api  # noqa: E402

SERVERS = UI_DIR / "mcp-servers"
KEYS3 = ["fixture-key-a", "fixture-key-b", "fixture-key-c"]


def reset_pool():
    with api._pool_lock:
        api._rotation.clear()
        api._cooldown.clear()


class IsolatedConfig(unittest.TestCase):
    """Temporary ui.api.json; process environment never supplies secrets."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="ae-pool-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / "ui.api.json"
        env = patch.dict(os.environ, {
            "AGENT_ENHANCEMENTS_API_FILE": str(self.path),
            "AGENT_ENHANCEMENTS_STATE_DIR": str(self.root / "state"),
            "AGENT_MEMORY_ROOT": str(self.root / "memory"),
        })
        env.start()
        self.addCleanup(env.stop)
        reset_pool()
        self.addCleanup(reset_pool)

    def write(self, api_keys=None, **extra):
        doc = {"version": 2, "api_keys": api_keys or {}, "connections": {}, "mcp": {}}
        doc.update(extra)
        self.path.write_text(json.dumps(doc))
        self.path.chmod(0o600)
        config, error = api.read_config()
        self.assertIsNone(error)
        return config


# ---------------------------------------------------------------------------
# P1: schema v2, template, validation
# ---------------------------------------------------------------------------


class SchemaTests(IsolatedConfig):
    def test_missing_file_initializes_private_v2_template_without_keys(self):
        self.assertFalse(self.path.exists())
        result = api.migrate()
        self.assertEqual(result["status"], "initialized")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        config, error = api.read_config()
        self.assertIsNone(error)
        self.assertEqual(config["version"], 2)
        self.assertTrue(config["api_keys"])
        self.assertFalse(any(config["api_keys"].values()), "template carries no keys")
        self.assertEqual(config["preflight"]["mode"], 0)

    def test_blank_whitespace_empty_and_absent_are_not_credentials(self):
        config = self.write({"TAVILY_API_KEY": ["", "   "], "EXA_API_KEY": []})
        for ref in ("TAVILY_API_KEY", "EXA_API_KEY", "YOU_API_KEY"):
            self.assertFalse(api.has_usable_key(ref, config), ref)
            self.assertEqual(api.request_keys(ref, config), [])
        state = api.server_state("search-mcp", config)
        self.assertEqual((state["visible"], state["reason"]), (False, "missing_credentials"))

    def test_keys_are_trimmed_and_deduplicated_in_order(self):
        config = self.write({"TAVILY_API_KEY": [" k1 ", "k2", "k1", "", "k3 "]})
        self.assertEqual(api.keys("TAVILY_API_KEY", config), ["k1", "k2", "k3"])

    def test_invalid_shapes_fail_closed(self):
        cases = [
            {"version": 2, "api_keys": {"X": "string-in-v2"}},
            {"version": 2, "api_keys": {"X": [["nested"]]}},
            {"version": 2, "api_keys": {"X": [1]}},
            {"version": 2, "api_keys": {"X": ["k"] * 33}},
            {"version": 3, "api_keys": {}},
            {"version": True, "api_keys": {}},
            {"version": 2, "api_keys": {}, "preflight": []},
            {"version": 2, "api_keys": {}, "mcp": {"x": {"any_of": "NOT_A_LIST"}}},
        ]
        for doc in cases:
            with self.subTest(doc=doc):
                self.path.write_text(json.dumps(doc))
                config, error = api.read_config()
                self.assertEqual(error, "config_unavailable_or_invalid")
                self.assertFalse(api.server_state("search-mcp")["visible"])
                self.assertTrue(api.server_state("graphrag-mcp")["visible"],
                                "local built-ins survive a broken edit")

    def test_unknown_fields_are_preserved_and_ignored(self):
        config = self.write({"YOU_API_KEY": ["k"]}, custom_note={"keep": True})
        self.assertEqual(config["custom_note"], {"keep": True})
        self.assertTrue(api.has_usable_key("YOU_API_KEY", config))

    def test_environment_never_supplies_a_missing_key(self):
        self.write({"TAVILY_API_KEY": []})
        with patch.dict(os.environ, {"TAVILY_API_KEY": "ambient", "YOU_API_KEY": "ambient"}):
            self.assertFalse(api.has_usable_key("TAVILY_API_KEY"))
            self.assertFalse(api.server_state("search-mcp")["visible"])

    def test_status_reports_counts_never_values(self):
        self.write({"TAVILY_API_KEY": KEYS3, "YOU_API_KEY": []})
        text = json.dumps(api.status())
        for key in KEYS3:
            self.assertNotIn(key, text)
        report = api.status()
        self.assertEqual(report["credentials"]["TAVILY_API_KEY"], 3)
        self.assertEqual(report["credentials"]["YOU_API_KEY"], 0)
        self.assertFalse(report["migration_pending"])
        self.assertNotIn("search_providers", report)


# ---------------------------------------------------------------------------
# P1: one-time migration (v1 file, legacy preflight files)
# ---------------------------------------------------------------------------


class MigrationTests(IsolatedConfig):
    def v1(self, **extra):
        doc = {"version": 1, "api_keys": {"TAVILY_API_KEY": " v1-fixture-key ",
                                          "YOU_API_KEY": "", "EXA_API_KEY": "   "},
               "connections": {"OPENAI_BASE_URL": "https://example.invalid/v1"},
               "mcp": {"custom-mcp": {"enabled": False}}, "user_field": [1, 2]}
        doc.update(extra)
        self.path.write_text(json.dumps(doc))
        self.path.chmod(0o600)
        return doc

    def test_v1_is_readable_and_reported_as_pending(self):
        self.v1()
        config, error = api.read_config()
        self.assertIsNone(error)
        self.assertEqual(api.keys("TAVILY_API_KEY", config), ["v1-fixture-key"])
        self.assertTrue(api.status()["migration_pending"])

    def test_v1_migrates_once_with_private_backup_and_no_loss(self):
        original = self.v1()
        legacy = self.root / "no-legacy"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = api.migrate(legacy_dir=legacy)
        self.assertEqual(result["status"], "migrated")
        self.assertNotIn("v1-fixture-key", json.dumps(result))
        doc = json.loads(self.path.read_text())
        self.assertEqual(doc["version"], 2)
        self.assertEqual(doc["api_keys"], {"TAVILY_API_KEY": ["v1-fixture-key"],
                                           "YOU_API_KEY": [], "EXA_API_KEY": []})
        for field in ("connections", "mcp", "user_field"):
            self.assertEqual(doc[field], original[field])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        backup = Path(result["backup"])
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(backup.read_text()), original)
        self.assertEqual(list(self.root.glob(".ui-api-*")), [], "no temp file left")
        again = api.migrate(legacy_dir=legacy)
        self.assertEqual(again["status"], "already_current")
        self.assertEqual(len(list(self.root.glob("ui.api.json.backup.*"))), 1)

    def test_legacy_model_json_and_key_file_are_imported_once(self):
        self.v1()
        legacy = self.root / "legacy"
        legacy.mkdir()
        (legacy / "model.json").write_text(json.dumps({
            "adaptive_preflight_mode": 2, "endpoint": "https://selector.invalid/v1",
            "sdk": "openai", "model": "fixture-model"}))
        key = legacy / "preflight.key"
        key.write_text("legacy-preflight-fixture\n")
        key.chmod(0o600)
        result = api.migrate(legacy_dir=legacy)
        self.assertEqual(result["legacy_model_json"], "imported")
        self.assertEqual(result["legacy_preflight_key"], "imported")
        self.assertNotIn("legacy-preflight-fixture", json.dumps(result))
        doc = json.loads(self.path.read_text())
        self.assertEqual(doc["preflight"], {
            "mode": 2, "sdk": "openai", "endpoint": "https://selector.invalid/v1",
            "model": "fixture-model", "api_key_ref": "PREFLIGHT_API_KEY"})
        self.assertEqual(doc["api_keys"]["PREFLIGHT_API_KEY"], ["legacy-preflight-fixture"])
        self.assertTrue((legacy / "model.json").exists(), "legacy files are not deleted")
        # Re-run: preflight exists, so nothing is imported or overwritten again.
        (legacy / "model.json").write_text('{"adaptive_preflight_mode": 1}')
        self.assertEqual(api.migrate(legacy_dir=legacy)["status"], "already_current")
        self.assertEqual(json.loads(self.path.read_text())["preflight"]["mode"], 2)

    def test_group_readable_key_file_is_not_imported(self):
        self.write({})
        legacy = self.root / "legacy"
        legacy.mkdir()
        key = legacy / "preflight.key"
        key.write_text("exposed-fixture")
        key.chmod(0o644)
        result = api.migrate(legacy_dir=legacy)
        self.assertNotIn("legacy_preflight_key", result)
        self.assertNotIn("exposed-fixture", self.path.read_text())

    def test_malformed_or_symlinked_file_is_refused_unchanged(self):
        self.path.write_text('{"version": 1, broken')
        before = self.path.read_bytes()
        self.assertEqual(api.migrate(legacy_dir=self.root)["status"], "refused")
        self.assertEqual(self.path.read_bytes(), before)
        self.path.unlink()
        target = self.root / "elsewhere.json"
        target.write_text(json.dumps({"version": 1, "api_keys": {}}))
        self.path.symlink_to(target)
        self.assertEqual(api.migrate(legacy_dir=self.root)["reason"], "not_a_regular_file")
        self.assertEqual(json.loads(target.read_text())["version"], 1)

    def test_failed_replace_keeps_the_original(self):
        original = self.v1()
        with patch.object(api.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                api.migrate(legacy_dir=self.root / "none")
        self.assertEqual(json.loads(self.path.read_text()), original)
        self.assertEqual(list(self.root.glob(".ui-api-*")), [])

    def test_migrate_cli_prints_no_values(self):
        self.v1()
        import subprocess
        result = subprocess.run(
            [sys.executable, str(UI_DIR / "scripts/api_config.py"), "migrate"],
            env={**os.environ}, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"status": "migrated"', result.stdout)
        self.assertNotIn("v1-fixture-key", result.stdout + result.stderr)


# ---------------------------------------------------------------------------
# P2: credential pool
# ---------------------------------------------------------------------------


class PoolTests(IsolatedConfig):
    def test_round_robin_advances_once_per_request(self):
        config = self.write({"TAVILY_API_KEY": KEYS3})
        firsts = [api.select_key_for_request("TAVILY_API_KEY", config) for _ in range(6)]
        self.assertEqual(firsts, KEYS3 + KEYS3)

    def test_readiness_and_health_never_move_the_pointer(self):
        config = self.write({"TAVILY_API_KEY": KEYS3})
        self.assertEqual(api.select_key_for_request("TAVILY_API_KEY", config), KEYS3[0])
        for _ in range(20):
            api.has_usable_key("TAVILY_API_KEY", config)
            api.server_state("search-mcp", config)
            api.key_health("TAVILY_API_KEY", config)
            api.status()
            api.value("TAVILY_API_KEY", config)
        self.assertEqual(api.select_key_for_request("TAVILY_API_KEY", config), KEYS3[1])

    def test_cooldown_skips_a_key_until_it_expires(self):
        config = self.write({"TAVILY_API_KEY": KEYS3})
        clock = [1000.0]
        with patch.object(api.time, "monotonic", side_effect=lambda: clock[0]):
            api.report_key_failure("TAVILY_API_KEY", KEYS3[0], 60)
            self.assertEqual(api.key_health("TAVILY_API_KEY", config),
                             {"keys": 3, "cooling_down": 1})
            for _ in range(6):
                self.assertNotIn(KEYS3[0], api.request_keys("TAVILY_API_KEY", config))
            clock[0] += 61
            seen = {api.select_key_for_request("TAVILY_API_KEY", config) for _ in range(3)}
            self.assertEqual(seen, set(KEYS3))

    def test_revoked_key_is_never_offered_again(self):
        config = self.write({"TAVILY_API_KEY": KEYS3})
        api.select_key_for_request("TAVILY_API_KEY", config)
        config = self.write({"TAVILY_API_KEY": [KEYS3[2]]})
        for _ in range(5):
            self.assertEqual(api.request_keys("TAVILY_API_KEY", config), [KEYS3[2]])
        config = self.write({"TAVILY_API_KEY": []})
        self.assertEqual(api.select_key_for_request("TAVILY_API_KEY", config), "")

    def test_concurrent_requests_are_evenly_distributed(self):
        config = self.write({"TAVILY_API_KEY": KEYS3})
        picked, lock = [], threading.Lock()

        def worker():
            for _ in range(10):
                key = api.select_key_for_request("TAVILY_API_KEY", config)
                with lock:
                    picked.append(key)

        threads = [threading.Thread(target=worker) for _ in range(9)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual({k: picked.count(k) for k in KEYS3}, {k: 30 for k in KEYS3})


# ---------------------------------------------------------------------------
# P3: first-party search adapters (official request contracts, mocked wire)
# ---------------------------------------------------------------------------


class Wire:
    """Recorder standing in for search-mcp's single network seam."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout):
        headers = {k.lower(): v for k, v in request.header_items()}
        body = json.loads(request.data) if request.data else None
        self.requests.append({"url": request.full_url, "method": request.get_method(),
                              "headers": headers, "body": body, "timeout": timeout})
        status, payload, extra = self.responses.pop(0) if len(self.responses) > 1 \
            else self.responses[0]
        return status, extra, json.dumps(payload).encode()


def ok(payload):
    return (200, payload, {})


YOU_PAYLOAD = {"results": {"web": [{"url": "https://a.example", "title": "A",
                                    "description": "about a", "snippets": ["s"],
                                    "page_age": "2026-11-01T00:00:00"}]},
               "metadata": {"search_uuid": "u"}}
TAVILY_PAYLOAD = {"results": [{"title": "T", "url": "https://t.example",
                               "content": "tavily content", "score": 0.8,
                               "published_date": "Tue, 11 Mar 2025 17:00:00 GMT"}]}
EXA_PAYLOAD = {"results": [{"title": "E", "url": "https://e.example", "text": "exa text",
                            "publishedDate": "2026-01-01T00:00:00.000Z", "author": "x"}]}
FIRECRAWL_PAYLOAD = {"success": True, "data": {"web": [
    {"title": "F", "url": "https://f.example", "description": "fire", "markdown": None}]}}
NEWSAPI_PAYLOAD = {"status": "ok", "totalResults": 1, "articles": [
    {"source": {"id": None, "name": "Wire"}, "title": "N", "url": "https://n.example",
     "description": "news", "publishedAt": "2026-11-19T10:00:00Z"}]}


SERPER_PAYLOAD = {"searchParameters": {"q": "q", "type": "search", "engine": "google"},
                  "organic": [{"title": "S", "link": "https://s.example", "snippet": "serp",
                               "position": 1, "date": "2 days ago"}], "credits": 1}


class AdapterTests(IsolatedConfig):
    def setUp(self):
        super().setUp()
        self.search = load_module("search_mcp_under_test", SERVERS / "search-mcp/server.py")

    def run_with(self, wire, *args, **kwargs):
        with patch.object(self.search, "_transport", wire):
            return self.search.run_search(*args, **kwargs)

    def test_each_provider_uses_its_documented_contract(self):
        refs = {"you": "YOU_API_KEY", "tavily": "TAVILY_API_KEY", "exa": "EXA_API_KEY",
                "firecrawl": "FIRECRAWL_API_KEY", "newsapi": "NEWSAPI_KEY",
                "serper": "SERPER_API_KEY"}
        self.write({ref: [f"{name}-fixture"] for name, ref in refs.items()})
        cases = {
            "you": (YOU_PAYLOAD, "https://ydc-index.io/v1/search", "POST",
                    ("x-api-key", "you-fixture"), {"query": "q", "count": 3, "freshness": "week"}),
            "tavily": (TAVILY_PAYLOAD, "https://api.tavily.com/search", "POST",
                       ("authorization", "Bearer tavily-fixture"),
                       {"query": "q", "max_results": 3, "time_range": "week"}),
            "exa": (EXA_PAYLOAD, "https://api.exa.ai/search", "POST",
                    ("x-api-key", "exa-fixture"), None),
            "firecrawl": (FIRECRAWL_PAYLOAD, "https://api.firecrawl.dev/v2/search", "POST",
                          ("authorization", "Bearer firecrawl-fixture"),
                          {"query": "q", "limit": 3, "tbs": "qdr:w"}),
            "newsapi": (NEWSAPI_PAYLOAD, None, "GET", ("x-api-key", "newsapi-fixture"), None),
            "serper": (SERPER_PAYLOAD, "https://google.serper.dev/search", "POST",
                       ("x-api-key", "serper-fixture"), {"q": "q", "num": 3, "tbs": "qdr:w"}),
        }
        for provider, (payload, url, method, header, body) in cases.items():
            with self.subTest(provider=provider):
                wire = Wire([ok(payload)])
                result = self.run_with(wire, provider, "q", 3, "week")
                self.assertNotIn("error", result, result)
                sent = wire.requests[0]
                self.assertEqual(sent["method"], method)
                if url:
                    self.assertEqual(sent["url"], url)
                self.assertEqual(sent["headers"][header[0]], header[1])
                self.assertIn("agentenhancements", sent["headers"]["user-agent"].lower())
                if body is not None:
                    self.assertEqual(sent["body"], body)
                item = result["results"][0]
                self.assertEqual(item["provider"], provider)
                self.assertTrue(item["url"].startswith("https://"))
                self.assertTrue(item["title"] and item["snippet"])
                self.assertNotIn(f"{provider}-fixture", json.dumps(result))
        exa = Wire([ok(EXA_PAYLOAD)])
        self.run_with(exa, "exa", "q", 3, "week")
        self.assertEqual(exa.requests[0]["body"]["numResults"], 3)
        self.assertIn("startPublishedDate", exa.requests[0]["body"])
        self.assertEqual(exa.requests[0]["body"]["contents"]["text"]["maxCharacters"], 500)
        news = Wire([ok(NEWSAPI_PAYLOAD)])
        self.run_with(news, "newsapi", "climate q", 3, "week")
        url = news.requests[0]["url"]
        self.assertTrue(url.startswith("https://newsapi.org/v2/everything?"))
        self.assertIn("q=climate+q", url)
        self.assertIn("pageSize=3", url)
        self.assertNotIn("apiKey", url, "the key travels in a header, never the URL")

    def test_six_requests_rotate_three_keys_per_request(self):
        self.write({"YOU_API_KEY": KEYS3})
        wire = Wire([ok(YOU_PAYLOAD)])
        for _ in range(6):
            self.assertNotIn("error", self.run_with(wire, "you", "q"))
        used = [r["headers"]["x-api-key"] for r in wire.requests]
        self.assertEqual(used, KEYS3 + KEYS3)

    def test_429_fails_over_to_the_next_key_and_cools_the_first(self):
        self.write({"TAVILY_API_KEY": KEYS3[:2]})
        wire = Wire([(429, {"detail": "slow down " + KEYS3[0]}, {"Retry-After": "30"}),
                     ok(TAVILY_PAYLOAD)])
        result = self.run_with(wire, "tavily", "q")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual([r["headers"]["authorization"] for r in wire.requests],
                         ["Bearer " + KEYS3[0], "Bearer " + KEYS3[1]])
        health = api.key_health("TAVILY_API_KEY")
        self.assertEqual(health, {"keys": 2, "cooling_down": 1})
        self.assertNotIn(KEYS3[0], json.dumps(result))

    def test_all_keys_failing_is_bounded_and_value_free(self):
        self.write({"EXA_API_KEY": KEYS3 + ["fixture-key-d"]})
        wire = Wire([(401, {"error": "bad key " + KEYS3[0]}, {})])
        result = self.run_with(wire, "exa", "q")
        self.assertEqual(len(wire.requests), self.search.MAX_ATTEMPTS)
        self.assertEqual(result["reason"], "all_tried_keys_failed")
        text = json.dumps(result)
        for key in KEYS3:
            self.assertNotIn(key, text)
        # Every tried key is cooling down: the next call does not hammer them.
        self.assertEqual(api.key_health("EXA_API_KEY")["cooling_down"], 3)

    def test_non_key_errors_do_not_fail_over(self):
        self.write({"YOU_API_KEY": KEYS3})
        for status in (400, 422, 500, 503):
            with self.subTest(status=status):
                wire = Wire([(status, {}, {})])
                result = self.run_with(wire, "you", "q")
                self.assertEqual((result["error"], len(wire.requests)), (f"http_{status}", 1))

    def test_network_errors_never_echo_request_details(self):
        self.write({"YOU_API_KEY": KEYS3[:1]})

        def boom(request, timeout):
            raise OSError("connect failed for " + KEYS3[0])

        result = self.run_with(boom, "you", "q")
        self.assertEqual(result["error"], "network_error")
        self.assertNotIn(KEYS3[0], json.dumps(result))

    def test_redirects_are_refused(self):
        handler = self.search._NoRedirect()
        with self.assertRaises(self.search.ProviderError) as caught:
            handler.redirect_request(None, None, 302, "Found", {}, "https://other.example/")
        self.assertEqual(caught.exception.code, "redirect_refused_http_302")

    def test_unavailable_provider_and_bad_input_never_reach_the_network(self):
        self.write({"YOU_API_KEY": []})
        wire = Wire([ok(YOU_PAYLOAD)])
        self.assertEqual(self.run_with(wire, "you", "q")["reason"], "no_usable_key")
        self.write({"YOU_API_KEY": ["k"]})
        for args in (("you", ""), ("you", "x" * 401), ("serper", "q"), ("you", "q", 5, "hour")):
            self.assertIn("error", self.run_with(wire, *args))
        self.assertIn("error", self.run_with(wire, "firecrawl", "q", 5, "year"))
        self.assertEqual(wire.requests, [])

    def test_provider_table_matches_readiness_and_gateway_order(self):
        gateway_source = (SERVERS / "gateway.py").read_text()
        self.assertEqual(self.search.PROVIDER_REFS, api.BUILTIN_ANY_OF["search-mcp"])
        order = ("you", "tavily", "exa", "firecrawl", "newsapi", "serper")
        self.assertIn(f"SEARCH_PROVIDERS = {order!r}".replace("'", '"'), gateway_source)
        self.assertEqual(self.search.PROVIDER_ORDER, order)


# ---------------------------------------------------------------------------
# P4: dependency-aware readiness, gateway gating, stale calls
# ---------------------------------------------------------------------------


class ReadinessTests(IsolatedConfig):
    def test_any_of_required_optional_semantics(self):
        python = sys.executable
        mcp = {
            "any-only": {"any_of": ["A_KEY", "B_KEY"], "command": [python]},
            "required-and-any": {"required": ["R_KEY"], "any_of": ["A_KEY", "B_KEY"],
                                 "optional": ["O_KEY"], "command": [python]},
            "key-but-no-runtime": {"required": ["R_KEY"], "command": []},
            "key-but-missing-binary": {"required": ["R_KEY"],
                                       "command": ["ae-fixture-binary-that-does-not-exist"]},
        }
        config = self.write({"B_KEY": ["b"], "R_KEY": ["r"]}, mcp=mcp)
        state = {name: api.server_state(name, config)["reason"] for name in mcp}
        self.assertEqual(state, {
            "any-only": "configured",
            "required-and-any": "configured",
            "key-but-no-runtime": "runtime_not_configured",
            "key-but-missing-binary": "executable_not_installed",
        })
        config = self.write({"R_KEY": ["r"]}, mcp=mcp)
        self.assertEqual(api.server_state("required-and-any", config)["reason"],
                         "missing_credentials")
        self.assertEqual(api.server_state("required-and-any", config)["missing_any_of"],
                         ["A_KEY", "B_KEY"])

    def test_search_server_needs_any_provider_and_explicit_disable_wins(self):
        config = self.write({})
        self.assertFalse(api.server_state("search-mcp", config)["visible"])
        config = self.write({"NEWSAPI_KEY": ["n"]})
        self.assertTrue(api.server_state("search-mcp", config)["visible"])
        config = self.write({"NEWSAPI_KEY": ["n"]}, mcp={"search-mcp": {"enabled": False}})
        self.assertEqual(api.server_state("search-mcp", config)["reason"], "disabled")
        # Local built-ins and keyless search alternatives stay available.
        config = self.write({})
        for name in ("arxiv-mcp", "google-news-mcp", "embeddings-mcp"):
            self.assertTrue(api.server_state(name, config)["visible"], name)

    def test_registry_hides_search_without_keys(self):
        registry = load_module("registry_pool", UI_DIR / "scripts/registry.py")
        entries = [{"type": "mcp", "name": "search-mcp", "id": "mcp:search-mcp"},
                   {"type": "mcp", "name": "arxiv-mcp", "id": "mcp:arxiv-mcp"}]
        self.write({})
        self.assertEqual([e["name"] for e in registry.usable_entries(entries)], ["arxiv-mcp"])
        self.write({"EXA_API_KEY": ["e"]})
        self.assertEqual([e["name"] for e in registry.usable_entries(entries)],
                         ["search-mcp", "arxiv-mcp"])


class GatewayGatingTests(IsolatedConfig):
    def setUp(self):
        super().setUp()
        self.gateway_module = load_module("gateway_pool", SERVERS / "gateway.py")
        self.gateway = self.gateway_module.Gateway()
        asyncio.run(self.gateway.load())

    def test_tool_and_provider_enum_follow_live_keys(self):
        config = self.write({})
        self.assertNotIn("search_web", self.gateway.tools(config))
        config = self.write({"TAVILY_API_KEY": KEYS3, "NEWSAPI_KEY": ["n"]})
        tool = self.gateway.tools(config)["search_web"][2]
        self.assertEqual(tool.inputSchema["properties"]["provider"]["enum"], ["tavily", "newsapi"])
        self.assertEqual(tool.inputSchema["properties"]["provider"]["default"], "tavily")
        self.assertNotIn("search_health", self.gateway.tools(config))
        for key in KEYS3:
            self.assertNotIn(key, json.dumps(tool.model_dump(mode="json")))

    def test_calls_are_gated_on_the_current_snapshot(self):
        self.write({"TAVILY_API_KEY": KEYS3})
        module = self.gateway.modules["search-mcp"]
        wire = Wire([ok(TAVILY_PAYLOAD)])
        with patch.object(module, "_transport", wire):
            result = asyncio.run(self.gateway.call_tool(
                "search_web", {"query": "q", "provider": "tavily"}))
            self.assertFalse(result.isError, result)
            denied = asyncio.run(self.gateway.call_tool(
                "search_web", {"query": "q", "provider": "you"}))
            self.assertTrue(denied.isError, "provider without a key is not in the enum")
            implicit = asyncio.run(self.gateway.call_tool("search_web", {"query": "q"}))
            self.assertFalse(implicit.isError, implicit.model_dump(mode="json"))
            self.assertEqual(implicit.structuredContent["provider"], "tavily")
            self.write({"TAVILY_API_KEY": []})
            stale = asyncio.run(self.gateway.call_tool(
                "search_web", {"query": "q", "provider": "tavily"}))
            self.assertTrue(stale.isError)
        self.assertEqual(len(wire.requests), 2, "revoked tool never reached the network")
        self.assertNotIn(KEYS3[0], json.dumps(result.model_dump(mode="json")))


class GatewayStdioTests(IsolatedConfig):
    def test_real_session_lists_search_only_while_a_key_exists(self):
        """Real stdio MCP session; no credentialed tool is ever called."""
        asyncio.run(self._session())

    async def _session(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        self.write({})
        with tempfile.TemporaryFile(mode="w+") as errors:
            params = StdioServerParameters(
                command=sys.executable, args=[str(SERVERS / "gateway.py")],
                env={"AGENT_ENHANCEMENTS_API_FILE": str(self.path),
                     "AGENT_ENHANCEMENTS_STATE_DIR": str(self.root / "state"),
                     "AGENT_MEMORY_ROOT": str(self.root / "memory"),
                     "YOU_API_KEY": "ambient-must-not-enable"})
            async with stdio_client(params, errlog=errors) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    names = {t.name for t in (await session.list_tools()).tools}
                    self.assertNotIn("search_web", names)
                    self.assertIn("arxiv_search", names)
                    self.write({"YOU_API_KEY": ["fixture-only-never-sent"]})
                    await asyncio.sleep(0.8)
                    tools = {t.name: t for t in (await session.list_tools()).tools}
                    self.assertIn("search_web", tools)
                    self.assertEqual(
                        tools["search_web"].inputSchema["properties"]["provider"]["enum"], ["you"])
                    self.write({"YOU_API_KEY": []})
                    denied = await session.call_tool("search_web", {"query": "q"})
                    self.assertTrue(denied.isError)
            errors.seek(0)
            self.assertNotIn("fixture-only-never-sent", errors.read())


class LiveSearchTests(unittest.TestCase):
    """Opt-in paid calls: AE_SEARCH_LIVE=1 and AGENT_ENHANCEMENTS_API_FILE
    pointing at a private ui.api.json with real keys. One small query per
    configured provider; outputs are checked for shape and key leakage."""

    @unittest.skipUnless(os.environ.get("AE_SEARCH_LIVE") == "1",
                         "set AE_SEARCH_LIVE=1 with a private ui.api.json holding real keys")
    def test_each_configured_provider_answers_live(self):
        search = load_module("search_mcp_live", SERVERS / "search-mcp/server.py")
        config, error = api.read_config()
        self.assertIsNone(error)
        providers = search.available_providers(config)
        self.assertTrue(providers, "no provider key configured")
        secrets = api.all_keys_for_redaction(config)
        for provider in providers:
            for freshness in (None, "week"):
                if provider == "firecrawl" and freshness == "week":
                    freshness = "day"
                with self.subTest(provider=provider, freshness=freshness):
                    result = search.run_search(provider, "python programming language",
                                               2, freshness, config)
                    self.assertNotIn("error", result, result)
                    self.assertGreaterEqual(result["count"], 1)
                    for item in result["results"]:
                        self.assertTrue(item["url"].startswith("http"), item)
                        self.assertTrue(item["title"], item)
                    text = json.dumps(result)
                    for secret in secrets:
                        self.assertNotIn(secret, text)


if __name__ == "__main__":
    unittest.main()
