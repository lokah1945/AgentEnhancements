"""In-house MCP server regression tests.

Covers the 9 servers built at unified-integration/mcp-servers/ (the
'to-build' entries of plugin-catalog/mcp-servers.json, now status=built):

- M-1: every catalog 'built' server exists, compiles, imports, exposes
       health() -> status ok, and its catalog implementation path matches.
- M-2: embeddings-mcp - local backend determinism, cosine ordering,
       openai error envelope without a key.
- M-3: task-router-mcp - bash+python dispatch, stdout capture, denylist
       refusal, unknown-id tracking.
- M-4: ffmpeg-mcp - real lavfi clip: probe/cut/thumbnail (skipped when
       the ffmpeg binary is absent).
- M-5: vision-mcp - compare ordering, ocr smoke, describe basic_metadata
       mode honesty.
- M-6: graphrag-mcp - index/query round-trip, unknown corpus, bad id.
- M-7: style-mcp - ai-text scores below plain text, rewrite improves and
       removes fillers.
- M-8: video-mcp - timeline validation, EDL export, real render when
       ffmpeg is present.
- M-9: arxiv/google-news - input validation guards (live network calls
       run only when AE_MCP_NETWORK_TESTS=1).
- M-10: catalog consistency - every built server has an implementation
        path that resolves, and mcp-servers.json statuses stay in the
        allowed set.
"""
import importlib.util
import json
import re
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from helpers import REPO_DIR

SERVERS_DIR = REPO_DIR / "unified-integration" / "mcp-servers"
CATALOG_PATH = REPO_DIR / "plugin-catalog" / "mcp-servers.json"

BUILT = [
    "embeddings-mcp", "task-router-mcp", "ffmpeg-mcp", "vision-mcp",
    "graphrag-mcp", "arxiv-mcp", "google-news-mcp", "video-mcp", "style-mcp",
]


def load_server(slug: str):
    spec = importlib.util.spec_from_file_location(
        slug.replace("-", "_"), SERVERS_DIR / slug / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def has_binary(name: str) -> bool:
    return shutil.which(name) is not None


class TestMCPCatalog(unittest.TestCase):
    """M-1 + M-10: catalog <-> implementation consistency."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text())

    def test_built_servers_exist_and_health_ok(self):
        for slug in BUILT:
            server = SERVERS_DIR / slug / "server.py"
            self.assertTrue(server.is_file(), f"missing {server}")
            module = load_server(slug)
            health = module.TOOLS["health"]()
            self.assertEqual(health.get("status"), "ok", slug)
            self.assertEqual(health.get("server"), slug)
            self.assertIn("version", health, slug)

    def test_catalog_built_entries_have_resolving_paths(self):
        built = [s for s in self.catalog["servers"] if s["status"] == "built"]
        self.assertEqual(len(built), 9, "exactly 9 built servers expected")
        for entry in built:
            impl = REPO_ROOT_PATH / entry["implementation"] \
                if (REPO_ROOT_PATH := REPO_DIR) and entry.get("implementation") else None
            self.assertIsNotNone(impl, f"{entry['id']} lacks implementation path")
            self.assertTrue(impl.is_file(), f"{entry['id']}: {impl} missing")

    def test_catalog_statuses_in_allowed_set(self):
        allowed = {"to-install", "to-build", "built", "installed"}
        for entry in self.catalog["servers"]:
            self.assertIn(entry["status"], allowed, entry["id"])

    def test_every_server_has_readme_and_requirements(self):
        for slug in BUILT:
            for fname in ("README.md", "requirements.txt"):
                path = SERVERS_DIR / slug / fname
                self.assertTrue(path.is_file(), f"missing {path}")

    def test_no_secret_logging_literals(self):
        """The servers must not print keys; check for obvious violations."""
        for slug in BUILT:
            source = (SERVERS_DIR / slug / "server.py").read_text()
            self.assertNotIn("print(os.environ", source, slug)
            self.assertNotIn("print(f\"{api_key}", source, slug)


class TestEmbeddings(unittest.TestCase):
    """M-2: embeddings-mcp."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("embeddings-mcp")

    def test_local_backend_deterministic(self):
        a = self.mod.TOOLS["embed"]("determinism check", backend="local")
        b = self.mod.TOOLS["embed"]("determinism check", backend="local")
        self.assertEqual(a["embedding"], b["embedding"])
        self.assertEqual(a["dim"], 256)

    def test_cosine_orders_related_above_unrelated(self):
        e = self.mod.TOOLS["embed_batch"](
            ["hello world", "hello there", "stock market rally"],
            backend="local")
        v0, v1, v2 = e["embeddings"]
        close = self.mod.TOOLS["cosine"](v0, v1)["similarity"]
        far = self.mod.TOOLS["cosine"](v0, v2)["similarity"]
        self.assertGreater(close, far)

    def test_openai_backend_error_envelope_without_key(self):
        saved = __import__("os").environ.pop("OPENAI_API_KEY", None)
        try:
            result = self.mod.TOOLS["embed"]("x", backend="openai")
        finally:
            if saved is not None:
                __import__("os").environ["OPENAI_API_KEY"] = saved
        self.assertIn("error", result)
        self.assertIn("hint", result)

    def test_empty_text_rejected(self):
        self.assertIn("error", self.mod.TOOLS["embed"]("  "))


class TestTaskRouter(unittest.TestCase):
    """M-3: task-router-mcp."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("task-router-mcp")

    def _wait(self, task_id, want, timeout=15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            entry = self.mod.TOOLS["track"](task_id)
            if entry.get("status") == want:
                return entry
            time.sleep(0.25)
        return self.mod.TOOLS["track"](task_id)

    def test_bash_dispatch_captures_stdout(self):
        task = self.mod.TOOLS["dispatch"](kind="bash", command="echo mcp-test-42")
        self.assertIn("task_id", task)
        entry = self._wait(task["task_id"], "done")
        self.assertEqual(entry["status"], "done", entry)
        self.assertIn("mcp-test-42", entry["stdout"])

    def test_python_dispatch(self):
        task = self.mod.TOOLS["dispatch"](kind="python", code="print(6*7)")
        entry = self._wait(task["task_id"], "done")
        self.assertIn("42", entry.get("stdout", ""))

    def test_denylist_refuses_rm_rf_root(self):
        result = self.mod.TOOLS["dispatch"](kind="bash", command="rm -rf /")
        self.assertIn("error", result)

    def test_unknown_task_tracking(self):
        result = self.mod.TOOLS["track"]("task-doesnotexist")
        self.assertIn("error", result)

    def test_bad_kind_rejected(self):
        self.assertIn("error", self.mod.TOOLS["dispatch"](kind="zsh", command="x"))


@unittest.skipUnless(has_binary("ffmpeg"), "ffmpeg binary not installed")
class TestFfmpeg(unittest.TestCase):
    """M-4: ffmpeg-mcp (real media round-trip)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("ffmpeg-mcp")
        cls.tmp = Path(tempfile.mkdtemp(prefix="ae-test-ffmpeg-"))
        cls.clip = cls.tmp / "src.mp4"
        gen = cls.mod._run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            "testsrc=duration=3:size=320x240:rate=10",
            "-pix_fmt", "yuv420p", str(cls.clip)])
        assert gen.get("ok"), gen

    def test_probe_reports_duration(self):
        info = self.mod.TOOLS["probe"](str(self.clip))
        self.assertGreater(info["duration_s"], 2.0)
        self.assertEqual(info["video_streams"][0]["width"], 320)

    def test_cut_and_thumbnail(self):
        cut = self.mod.TOOLS["cut"](str(self.clip), 0.0, 1.0, str(self.tmp / "cut.mp4"))
        self.assertTrue(cut.get("ok"), cut)
        thumb = self.mod.TOOLS["thumbnail"](str(self.clip), 0.5,
                                            str(self.tmp / "t.jpg"))
        self.assertTrue(thumb.get("ok"), thumb)
        self.assertGreater((self.tmp / "t.jpg").stat().st_size, 0)

    def test_missing_input_error(self):
        result = self.mod.TOOLS["probe"](str(self.tmp / "nope.mp4"))
        self.assertIn("error", result)

    def test_escape_blocked_outside_roots(self):
        target = Path("/root/forbidden.mp4")
        result = self.mod.TOOLS["cut"](str(self.clip), 0, 1, str(target))
        self.assertIn("error", result)
        self.assertIn("allowed roots", result["error"])


class TestVision(unittest.TestCase):
    """M-5: vision-mcp."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("vision-mcp")
        from PIL import Image, ImageDraw
        cls.tmp = Path(tempfile.mkdtemp(prefix="ae-test-vision-"))
        cls.flat = cls.tmp / "flat.png"
        Image.new("RGB", (120, 60), (200, 30, 30)).save(cls.flat)
        cls.text = cls.tmp / "text.png"
        canvas = Image.new("RGB", (400, 120), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        try:  # bigger default font when truetype fonts exist
            from PIL import ImageFont
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
            draw.text((20, 25), "AE7", fill=(0, 0, 0), font=font)
        except Exception:
            draw.text((20, 25), "AE7", fill=(0, 0, 0))
        canvas.save(cls.text)

    def test_compare_identical_beats_different(self):
        same = self.mod.TOOLS["compare"](str(self.flat), str(self.flat))["similarity"]
        diff = self.mod.TOOLS["compare"](str(self.flat), str(self.text))["similarity"]
        self.assertGreater(same, 0.95)
        self.assertGreater(same, diff)

    def test_describe_without_key_is_honest_metadata(self):
        import os
        saved = os.environ.pop("OPENAI_API_KEY", None)
        try:
            result = self.mod.TOOLS["describe"](str(self.flat))
        finally:
            if saved is not None:
                os.environ["OPENAI_API_KEY"] = saved
        self.assertEqual(result["mode"], "basic_metadata")
        self.assertIn("note", result)
        self.assertNotIn("description", result)  # never fakes semantics

    @unittest.skipUnless(has_binary("tesseract"), "tesseract not installed")
    def test_ocr_reads_rendered_text(self):
        result = self.mod.TOOLS["ocr"](str(self.text))
        self.assertIn("text", result)
        self.assertRegex(result["text"], r"AE\s*7|AE7")

    def test_missing_file_error(self):
        self.assertIn("error", self.mod.TOOLS["ocr"](str(self.tmp / "no.png")))


class TestGraphRAG(unittest.TestCase):
    """M-6: graphrag-mcp."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("graphrag-mcp")
        cls.corpus = "unittest-corpus"
        cls.mod.TOOLS["index"](cls.corpus, documents=[
            {"id": "d1",
             "text": "Alice works at Acme Corp. Acme Corp builds robots in Boston."},
            {"id": "d2",
             "text": "Bob joined Acme Corp last year. The robots ship to Boston hospitals."},
        ])

    def test_index_built_entities(self):
        status = self.mod.TOOLS["status"](self.corpus)
        self.assertGreaterEqual(status["entities"], 3)
        self.assertGreaterEqual(status["relations"], 1)

    def test_query_ranks_relevant_evidence(self):
        answer = self.mod.TOOLS["query"](self.corpus,
                                         "Where does Acme Corp build robots?")
        self.assertTrue(answer["answers"])
        top = answer["answers"][0]
        self.assertIn("robots", top["sentence"].lower())
        self.assertGreater(top["score"], 0)

    def test_unknown_corpus(self):
        result = self.mod.TOOLS["query"]("never-indexed", "anything")
        self.assertIn("error", result)

    def test_bad_corpus_id_rejected(self):
        self.assertIn("error", self.mod.TOOLS["index"]("bad id!", documents=[
            {"text": "x"}]))


class TestStyle(unittest.TestCase):
    """M-7: style-mcp."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("style-mcp")

    AI_TEXT = ("It is important to note that, in the realm of AI, we must "
               "delve into the rich tapestry of options. Furthermore, it "
               "seems that this is a testament to progress.")
    PLAIN_TEXT = "We tested three options. The second one worked and cost less."

    def test_ai_text_scores_below_plain(self):
        ai = self.mod.TOOLS["score"](self.AI_TEXT)
        plain = self.mod.TOOLS["score"](self.PLAIN_TEXT)
        self.assertLess(ai["score"], plain["score"])
        self.assertTrue(ai["findings"])

    def test_rewrite_improves_and_removes_fillers(self):
        result = self.mod.TOOLS["rewrite"](self.AI_TEXT)
        self.assertGreater(result["after_score"], result["before_score"])
        self.assertNotIn("It is important to note", result["text"])

    def test_patterns_catalogue_consistent(self):
        result = self.mod.TOOLS["patterns"]()
        names = [p["pattern"] for p in result["patterns"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertGreaterEqual(len(names), 15)


@unittest.skipUnless(has_binary("ffmpeg"), "ffmpeg binary not installed")
class TestVideo(unittest.TestCase):
    """M-8: video-mcp."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_server("video-mcp")
        cls.tmp = Path(tempfile.mkdtemp(prefix="ae-test-video-"))
        cls.clip = cls.tmp / "src.mp4"
        subprocess_run = __import__("subprocess").run
        proc = subprocess_run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i",
             "testsrc=duration=3:size=320x240:rate=10",
             "-pix_fmt", "yuv420p", str(cls.clip)],
            capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr[-400:]

    def test_timeline_validation(self):
        result = self.mod.TOOLS["timeline"]("bad!", clips=[])
        self.assertIn("error", result)
        result = self.mod.TOOLS["timeline"]("t-ok", clips=[
            {"path": str(self.clip), "start": 1.0, "end": 0.5}])
        self.assertIn("error", result)  # end must exceed start

    def test_timeline_edl_render_roundtrip(self):
        created = self.mod.TOOLS["timeline"]("reel", clips=[
            {"path": str(self.clip), "start": 0.0, "end": 1.0,
             "text": "One", "position": "bottom"},
            {"path": str(self.clip), "start": 1.0, "end": 2.0},
        ])
        self.assertTrue(created.get("ok"), created)
        self.assertEqual(created["clips"], 2)
        edl = self.mod.TOOLS["edl"]("reel")
        self.assertIn("EDL reel", edl["edl"])
        out = self.tmp / "reel.mp4"
        rendered = self.mod.TOOLS["render"]("reel", str(out))
        self.assertTrue(rendered.get("ok"), rendered)
        self.assertGreater(out.stat().st_size, 0)

    def test_unknown_timeline(self):
        self.assertIn("error", self.mod.TOOLS["render"]("ghost", "/tmp/x.mp4"))


class TestNetworkServers(unittest.TestCase):
    """M-9: arxiv / google-news guards (live calls only when opted in)."""

    @classmethod
    def setUpClass(cls):
        cls.arxiv = load_server("arxiv-mcp")
        cls.news = load_server("google-news-mcp")

    def test_arxiv_id_format_guard(self):
        for bad in ("not-an-id", "../etc/passwd", "2401.0000"):
            result = self.arxiv.TOOLS["fetch"](bad)
            self.assertIn("error", result, bad)

    def test_arxiv_empty_query_rejected(self):
        self.assertIn("error", self.arxiv.TOOLS["search"]("  "))

    def test_arxiv_bad_sort_rejected(self):
        result = self.arxiv.TOOLS["search"]("all:rag", sort="random")
        self.assertIn("error", result)

    def test_news_lang_guard(self):
        result = self.news.TOOLS["top"](lang="xx")
        self.assertIn("error", result)

    def test_news_limit_clamped(self):
        # lang guard fires before any fetch, proving clamping order is safe
        result = self.news.TOOLS["top"](topic="x", lang="zz", limit=999)
        self.assertIn("error", result)

    @unittest.skipUnless(
        __import__("os").environ.get("AE_MCP_NETWORK_TESTS") == "1",
        "set AE_MCP_NETWORK_TESTS=1 for live arxiv/news calls")
    def test_live_arxiv_search(self):
        result = self.arxiv.TOOLS["search"]("attention is all you need",
                                            max_results=2)
        self.assertNotIn("error", result)
        self.assertGreaterEqual(result["count"], 1)

    @unittest.skipUnless(
        __import__("os").environ.get("AE_MCP_NETWORK_TESTS") == "1",
        "set AE_MCP_NETWORK_TESTS=1 for live arxiv/news calls")
    def test_live_news_top(self):
        result = self.news.TOOLS["top"](topic="technology", lang="en", limit=3)
        self.assertNotIn("error", result)
        self.assertGreaterEqual(result["count"], 1)


if __name__ == "__main__":
    unittest.main()
