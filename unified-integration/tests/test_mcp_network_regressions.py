#!/usr/bin/env python3
"""Regression tests for the google-news, graphrag and task-router MCP servers.

- google-news: each language requests its canonical edition (hl/gl/ceid), not
  a mismatched triple that Google redirects to the English US feed.
- graphrag: corpus ids are validated (1..64 chars) on every tool; ids longer
  than 64 characters no longer truncate onto, and overwrite, another corpus.
- task-router: background children are killed when the task ends, completion
  is not delayed by them, output already produced is kept, workspaces are
  removed for every finished task and the finished-task registry is capped.
"""
import importlib.util
import os
import shlex
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import UI_DIR

SERVERS_DIR = Path(os.environ.get("AE_MCP_A_SERVERS_DIR", UI_DIR / "mcp-servers"))


def setUpModule():
    """Keep generated MCP state away from the user's data."""
    global _directory, _environment
    _directory = tempfile.TemporaryDirectory()
    _environment = patch.dict(os.environ, {
        "AGENT_ENHANCEMENTS_API_FILE": str(Path(_directory.name) / "no-credentials.json"),
        "AGENT_MEMORY_ROOT": str(Path(_directory.name) / "memory"),
        "AGENT_ENHANCEMENTS_STATE_DIR": str(Path(_directory.name) / "state"),
    })
    _environment.start()


def tearDownModule():
    _environment.stop()
    _directory.cleanup()


def load_server(slug: str):
    spec = importlib.util.spec_from_file_location(
        "mcp_a_" + slug.replace("-", "_"), SERVERS_DIR / slug / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _alive(pid: int) -> bool:
    """True while pid exists and is not a zombie."""
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except (FileNotFoundError, ProcessLookupError, IndexError):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    return state not in ("Z", "X")


class TestGoogleNewsEditions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("google-news-mcp")

    def _url_for(self, **kwargs) -> str:
        seen = []

        def fake_fetch(url):
            seen.append(url)
            return "<rss><channel><item><title>t</title></item></channel></rss>"

        with patch.object(self.mod, "_fetch", side_effect=fake_fetch):
            result = self.mod.TOOLS["top"](**kwargs)
        self.assertNotIn("error", result)
        self.assertEqual(len(seen), 1)
        return seen[0]

    def test_each_language_uses_its_canonical_edition(self):
        expected = {
            "en": "hl=en-US&gl=US&ceid=US:en",
            "jp": "hl=ja&gl=JP&ceid=JP:ja",
            "kr": "hl=ko&gl=KR&ceid=KR:ko",
            "zh": "hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
            "id": "hl=id&gl=ID&ceid=ID:id",
            "de": "hl=de&gl=DE&ceid=DE:de",
            "fr": "hl=fr&gl=FR&ceid=FR:fr",
            "es": "hl=es-419&gl=US&ceid=US:es-419",
            "pt": "hl=pt-BR&gl=BR&ceid=BR:pt-419",
        }
        self.assertEqual(sorted(expected), self.mod.health()["languages"])
        for lang, edition in expected.items():
            url = self._url_for(lang=lang)
            self.assertEqual(url, f"{self.mod.BASE}?{edition}", lang)

    def test_topic_search_keeps_the_edition(self):
        url = self._url_for(topic="AI agents", lang="JP")
        self.assertEqual(url, f"{self.mod.BASE}/search?q=AI%20agents&hl=ja&gl=JP&ceid=JP:ja")

    def test_fetch_transport_errors_return_error_shape(self):
        import http.client
        errors = [TimeoutError("read timed out"), ConnectionResetError("reset"),
                  http.client.IncompleteRead(b"partial"),
                  http.client.RemoteDisconnected("closed")]
        for index, exc in enumerate(errors):
            with self.subTest(error=type(exc).__name__):
                url = f"https://news.google.com/rss/regression-{index}-{time.time_ns()}"
                with patch.object(self.mod, "_cache_get", return_value=None), \
                        patch.object(self.mod, "_cache_put") as put, \
                        patch.object(self.mod.urllib.request, "urlopen", side_effect=exc):
                    result = self.mod._fetch(url)
                self.assertIsInstance(result, dict)
                self.assertEqual(set(result), {"error", "hint"})
                self.assertIn(type(exc).__name__, result["error"])
                put.assert_not_called()


class TestGraphRAGCorpusIds(unittest.TestCase):
    DOCS_A = [{"id": "a", "text": "Alice works at Acme Corp in Boston."}]
    DOCS_B = [{"id": "b", "text": "Zed works at Globex Inc in Springfield."}]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        with patch.dict(os.environ, {"AGENT_MEMORY_ROOT": self.tmp.name}):
            self.mod = load_server("graphrag-mcp")

    def test_overlong_ids_are_rejected_instead_of_colliding(self):
        first, second = "A" * 64 + "x", "A" * 64 + "y"
        self.assertIn("error", self.mod.TOOLS["index"](first, documents=self.DOCS_A))
        self.assertIn("error", self.mod.TOOLS["index"](second, documents=self.DOCS_B))
        self.assertEqual(list(self.mod.STORE_DIR.glob("*.json")) if self.mod.STORE_DIR.is_dir() else [], [])

    def test_sixty_four_character_id_round_trips(self):
        corpus = "B" * 64
        self.assertNotIn("error", self.mod.TOOLS["index"](corpus, documents=self.DOCS_A))
        status = self.mod.TOOLS["status"](corpus)
        self.assertNotIn("error", status)
        self.assertEqual(status["corpus_id"], corpus)
        self.assertIn("alice", [e["entity"] for e in status["top_entities"]])
        self.assertTrue((self.mod.STORE_DIR / f"{corpus}.json").is_file())

    def test_query_and_status_reject_invalid_ids(self):
        # 'a.b' used to be cleaned to 'ab' and read another corpus.
        self.assertNotIn("error", self.mod.TOOLS["index"]("ab", documents=self.DOCS_A))
        for bad in ("a.b", "", "C" * 65, "../ab", None):
            self.assertIn("corpus_id must match", self.mod.TOOLS["query"](bad, "Alice?").get("error", ""), bad)
            self.assertIn("corpus_id must match", self.mod.TOOLS["status"](bad).get("error", ""), bad)


@unittest.skipUnless(os.name == "posix", "process-group cleanup is POSIX-only")
class TestTaskRouterLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("task-router-mcp")

    def _wait_finished(self, task_id, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            entry = self.mod.TOOLS["track"](task_id)
            if entry.get("status") in ("done", "failed", "cancelled") and "finished_at" in entry:
                return entry
            time.sleep(0.05)
        self.fail(f"task {task_id} did not finish: {self.mod.TOOLS['track'](task_id)}")

    def _kill_later(self, pid: int):
        def cleanup():
            try:
                os.kill(pid, 9)
            except (ProcessLookupError, PermissionError):
                pass
        self.addCleanup(cleanup)

    def test_background_child_is_killed_and_does_not_delay_completion(self):
        task = self.mod.TOOLS["dispatch"](kind="bash", command="sleep 77.5 & echo $!")
        started = time.time()
        entry = self._wait_finished(task["task_id"])
        elapsed = time.time() - started
        self.assertEqual(entry["status"], "done", entry)
        pid = int(entry["stdout"].split()[0])
        self._kill_later(pid)
        self.assertLess(elapsed, 1.5, "a background child delayed completion")
        deadline = time.time() + 3
        while _alive(pid) and time.time() < deadline:
            time.sleep(0.05)
        self.assertFalse(_alive(pid), "background child outlived its task")

    def test_output_is_kept_when_a_detached_process_holds_the_pipes(self):
        # setsid escapes the task's group, so the pipes stay open past the
        # reader join timeout: output already written must still be reported.
        task = self.mod.TOOLS["dispatch"](
            kind="bash", command="echo early-output; setsid sleep 6 & echo pid=$!")
        entry = self._wait_finished(task["task_id"])
        for token in entry["stdout"].split():
            if token.startswith("pid="):
                self._kill_later(int(token[4:]))
        self.assertIn("early-output", entry["stdout"])

    def test_workspace_removed_for_finished_tasks(self):
        for kwargs in ({"kind": "bash", "command": "pwd"},
                       {"kind": "bash", "command": "pwd; exit 3"},
                       {"kind": "python", "code": "import os; print(os.getcwd())"}):
            task = self.mod.TOOLS["dispatch"](**kwargs)
            entry = self._wait_finished(task["task_id"])
            workspace = Path(entry["stdout"].strip().splitlines()[0])
            self.assertIn(task["task_id"], workspace.name)
            self.assertFalse(workspace.exists(), f"{kwargs} left {workspace}")
            self.assertNotIn(task["task_id"], self.mod._WORKSPACES)

    def test_finished_registry_is_capped(self):
        with patch.object(self.mod, "MAX_FINISHED_TASKS", 3):
            ids = []
            for index in range(6):
                task = self.mod.TOOLS["dispatch"](kind="bash", command=f"echo {index}")
                ids.append(task["task_id"])
                self._wait_finished(task["task_id"])
            known = {t["id"] for t in self.mod.TOOLS["list_tasks"]()["tasks"]}
        self.assertIn(ids[-1], known)
        self.assertNotIn(ids[0], known)
        finished = [t for t in self.mod._TASKS.values()
                    if t["status"] in ("done", "failed", "cancelled")]
        # three kept before the last dispatch, plus the newest task
        self.assertLessEqual(len(finished), 4)

    def test_timeout_still_reports_and_cleans_up(self):
        code = "import time; time.sleep(30)"
        command = shlex.join([sys.executable, "-c", code]) + " & wait"
        task = self.mod.TOOLS["dispatch"](kind="bash", command=command, timeout=1)
        entry = self._wait_finished(task["task_id"])
        self.assertEqual(entry["status"], "failed")
        self.assertIn("timeout", entry["stderr"])


if __name__ == "__main__":
    unittest.main()
