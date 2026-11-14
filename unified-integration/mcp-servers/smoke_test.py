#!/usr/bin/env python3
"""Manual smoke test: import each in-house MCP server, call health() and
one functional tool per server. Run from the mcp-servers/ directory:

    python3 smoke_test.py
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVERS = [
    "embeddings-mcp", "task-router-mcp", "ffmpeg-mcp", "vision-mcp",
    "graphrag-mcp", "arxiv-mcp", "google-news-mcp", "video-mcp", "style-mcp",
]


def load(slug: str):
    spec = importlib.util.spec_from_file_location(
        slug.replace("-", "_"), HERE / slug / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failures = []

    for slug in SERVERS:
        try:
            mod = load(slug)
            health = mod.TOOLS["health"]()
            assert health["status"] == "ok", health
            print(f"[ok] {slug:18s} health -> {health['server']} v{health['version']}")
        except Exception as exc:
            failures.append((slug, f"health/import: {exc}"))
            print(f"[FAIL] {slug}: {exc}")
            continue

    # embeddings: local embed + cosine
    mod = load("embeddings-mcp")
    a = mod.TOOLS["embed"]("hello world", backend="local")
    b = mod.TOOLS["embed"]("hello there", backend="local")
    c = mod.TOOLS["embed"]("stock market rally", backend="local")
    sim_close = mod.TOOLS["cosine"](a["embedding"], b["embedding"])["similarity"]
    sim_far = mod.TOOLS["cosine"](a["embedding"], c["embedding"])["similarity"]
    assert sim_close > sim_far, (sim_close, sim_far)
    print(f"[ok] embeddings-mcp     cosine close={sim_close} far={sim_far}")

    # task-router: bash + python dispatch
    mod = load("task-router-mcp")
    t1 = mod.TOOLS["dispatch"](kind="bash", command="echo router-ok")
    time.sleep(1.2)
    r1 = mod.TOOLS["track"](t1["task_id"])
    assert "router-ok" in r1.get("stdout", ""), r1
    t2 = mod.TOOLS["dispatch"](kind="python", code="print(6*7)")
    time.sleep(1.2)
    r2 = mod.TOOLS["track"](t2["task_id"])
    assert "42" in r2.get("stdout", ""), r2
    refused = mod.TOOLS["dispatch"](kind="bash", command="rm -rf /")
    assert "error" in refused, refused
    print(f"[ok] task-router-mcp    bash+python dispatch, denylist refuses rm -rf /")

    # ffmpeg: lavfi test clip -> probe -> cut -> thumbnail
    mod = load("ffmpeg-mcp")
    tmp = Path(tempfile.mkdtemp(prefix="ae-smoke-"))
    clip = tmp / "src.mp4"
    gen = mod._run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "testsrc=duration=3:size=320x240:rate=10",
                    "-pix_fmt", "yuv420p", str(clip)])
    assert gen.get("ok"), gen
    info = mod.TOOLS["probe"](str(clip))
    assert 2.5 < info["duration_s"] <= 3.0, info
    cut = mod.TOOLS["cut"](str(clip), 0.0, 1.0, str(tmp / "cut.mp4"))
    assert cut.get("ok"), cut
    thumb = mod.TOOLS["thumbnail"](str(clip), 0.5, str(tmp / "thumb.jpg"))
    assert thumb.get("ok") and (tmp / "thumb.jpg").stat().st_size > 0, thumb
    print(f"[ok] ffmpeg-mcp         probe={info['duration_s']}s cut+thumbnail ok")

    # vision: compare + ocr + describe(basic_metadata)
    mod = load("vision-mcp")
    from PIL import Image, ImageDraw
    img1, img2 = tmp / "a.png", tmp / "b.png"
    Image.new("RGB", (120, 60), (200, 30, 30)).save(img1)
    canvas = Image.new("RGB", (120, 60), (200, 30, 30))
    ImageDraw.Draw(canvas).text((10, 20), "AE", fill=(255, 255, 255))
    canvas.save(img2)
    same = mod.TOOLS["compare"](str(img1), str(img1))["similarity"]
    diff = mod.TOOLS["compare"](str(img1), str(img2))["similarity"]
    assert same > 0.95 and diff < same, (same, diff)
    ocr = mod.TOOLS["ocr"](str(img2))
    desc = mod.TOOLS["describe"](str(img1))
    assert desc["mode"] == "basic_metadata", desc
    print(f"[ok] vision-mcp         compare same={same} diff={diff}; "
          f"describe mode={desc['mode']}; ocr chars={len(ocr.get('text', ''))}")

    # graphrag: index + query
    mod = load("graphrag-mcp")
    idx = mod.TOOLS["index"]("smoke", documents=[
        {"id": "d1", "text": "Alice works at Acme Corp. Acme Corp builds robots in Boston."},
        {"id": "d2", "text": "Bob joined Acme Corp last year. The robots ship to Boston hospitals."},
    ])
    assert idx["entities"] >= 3, idx
    ans = mod.TOOLS["query"]("smoke", "Where does Acme Corp build robots?")
    assert ans["answers"] and "Acme" in " ".join(
        e["sentence"] for e in ans["answers"]), ans
    print(f"[ok] graphrag-mcp       entities={idx['entities']} "
          f"relations={idx['relations']} top-answer-score={ans['answers'][0]['score']}")

    # style: score + rewrite
    mod = load("style-mcp")
    ai_text = ("It is important to note that, in the realm of AI, we must "
               "delve into the rich tapestry of options. Furthermore, it "
               "seems that this is a testament to progress.")
    plain = "We tested three options. The second one worked best and cost less."
    s_ai = mod.TOOLS["score"](ai_text)
    s_plain = mod.TOOLS["score"](plain)
    assert s_ai["score"] < s_plain["score"], (s_ai, s_plain)
    rw = mod.TOOLS["rewrite"](ai_text)
    assert rw["after_score"] > rw["before_score"], rw
    assert "It is important to note" not in rw["text"], rw
    print(f"[ok] style-mcp          ai={s_ai['score']} plain={s_plain['score']} "
          f"rewrite {rw['before_score']}->{rw['after_score']}")

    # video: timeline + edl + render (ffmpeg present)
    mod = load("video-mcp")
    tl = mod.TOOLS["timeline"]("smoke-reel", clips=[
        {"path": str(clip), "start": 0.0, "end": 1.0, "text": "Part One",
         "position": "bottom"},
        {"path": str(clip), "start": 1.0, "end": 2.0},
    ])
    assert tl["ok"], tl
    edl = mod.TOOLS["edl"]("smoke-reel")
    assert "EDL smoke-reel" in edl["edl"], edl
    rendered = mod.TOOLS["render"]("smoke-reel", str(tmp / "reel.mp4"))
    assert rendered.get("ok") and (tmp / "reel.mp4").stat().st_size > 0, rendered
    print(f"[ok] video-mcp          timeline+edl+render "
          f"({(tmp / 'reel.mp4').stat().st_size} bytes)")

    # arxiv / google-news: validation paths only (network optional)
    mod = load("arxiv-mcp")
    assert "error" in mod.TOOLS["fetch"]["__call__"]("not-an-id") if False else True
    bad = mod.TOOLS["fetch"]("not-an-id")
    assert "error" in bad, bad
    print("[ok] arxiv-mcp           id-format guard works (live calls in unit tests)")

    mod = load("google-news-mcp")
    bad = mod.TOOLS["top"](lang="xx")
    assert "error" in bad, bad
    print("[ok] google-news-mcp     lang guard works (live calls in unit tests)")

    print()
    if failures:
        print(f"SMOKE TEST FAILED: {failures}")
        return 1
    print("SMOKE TEST PASSED: 9/9 servers healthy, functional tools verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
