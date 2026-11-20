#!/usr/bin/env python3
"""Opt-in actual OpenCode 2 proof with synthetic, localhost-only models.

Run with the checkout AE interpreter and --output <private evidence directory>.
No account credentials or real inference are used. Fixture outputs prove wiring,
not model relevance. Only synthetic request bodies and whitelisted host metadata
are retained; HTTP authorization headers are never saved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from test_adaptive_preflight import SelectorFixture

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "unified-integration"
sys.path.insert(0, str(UI / "scripts"))
import adaptive_preflight as preflight
from context_budget import approx_tokens, MAX_COLD_START_TOTAL, MAX_SKILL_CARDS


def write_json(path: Path, value: object) -> None:
    """Write private, synthetic fixture evidence."""
    path.write_text(json.dumps(value, indent=2) + "\n")
    path.chmod(0o600)


def sanitized(value: object) -> object:
    """Apply the existing redactor without consulting account configuration."""
    if isinstance(value, str):
        return preflight._api_config().redact(value, {})
    if isinstance(value, list):
        return [sanitized(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitized(item) for key, item in value.items()}
    return value


def context_ledger(context: str, tools: dict, discovery: list[str]) -> dict:
    """Count all AE channels in this actual host profile, including duplicates.

    Conservatively charge every native skill description and the complete shared
    execute declaration. Task-specific skill bodies arrive after selection and
    are outside the documented cold-start total.

    The library-map read is measured separately as a mandatory cold-start action.
    """
    native = re.search(r"<available_skills>.*?</available_skills>", context, re.S)
    library_map = json.loads((ROOT / "skills/library-map.json").read_text())["rendered"]
    assert context.count(library_map) == 1, "complete L0 bootstrap map was not delivered exactly once"
    bootstrap = "".join(re.findall(
        r"<!-- agent-enhancements:begin -->.*?<!-- agent-enhancements:end -->", context, re.S))
    assert not bootstrap, "duplicate bootstrap pointers remain after L0 delivery"
    start = context.index("\n- agent-enhancements (")
    end = context.find("\n- ", start + 1)
    catalog = context[start:end if end >= 0 else len(context)]
    hook_start = context.index("AgentEnhancements task-observer is active")
    bootstrap_start = context.index("AgentEnhancements bootstrap (L0):")
    # Library map starts after the bootstrap header
    library_map_start = bootstrap_start + len("AgentEnhancements bootstrap (L0):\n")
    library_map_end = library_map_start + len(library_map)
    # Workflow text follows the library map
    workflow_text = context[library_map_end:hook_start]
    submit_start = max(context.find("AgentEnhancements preflight", hook_start),
                       context.find("AgentEnhancements local skill candidates", hook_start))
    observer = context[hook_start:submit_start] if submit_start >= 0 else context[hook_start:]
    submit = context[submit_start:] if submit_start >= 0 else ""
    channels = {"library_map_read": approx_tokens(library_map),
                "bootstrap_workflow": approx_tokens(workflow_text),
                "instruction_source_headers": approx_tokens("\n".join(re.findall(r"Instructions from:[^\n]+", context))),
                "native_descriptions_all": approx_tokens(native.group() if native else ""),
                "ae_tool_catalog_and_shared_execute": approx_tokens(catalog + json.dumps(tools["execute"])),
                "observer_and_memory": approx_tokens(observer), "prompt_slot": approx_tokens(submit),
                "additional_catalog_results": sum(approx_tokens(text) for text in discovery)}
    assert channels["prompt_slot"] <= MAX_SKILL_CARDS, channels
    assert channels["observer_and_memory"] <= 250, channels
    assert channels["native_descriptions_all"] <= 2500, channels
    assert channels["ae_tool_catalog_and_shared_execute"] <= 1800, channels
    assert channels["library_map_read"] <= 500, channels  # documented bootstrap_tokens_approx: 491
    assert channels["bootstrap_workflow"] <= 100, channels
    assert all(approx_tokens(text) <= 800 for text in discovery), "discovery page budget exceeded"
    total = sum(channels.values())
    assert total <= MAX_COLD_START_TOTAL, channels
    return {"measurement": "documented chars/4 fallback (provider usage unavailable)",
            "channels": channels, "cold_start_total": total, "limit": MAX_COLD_START_TOTAL}


class MainFixture:
    """Scripted main model: read the selected skill, probe media, then finish."""

    def __init__(self, steps: list[tuple[str, dict]]):
        self.requests: list[dict] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: object) -> None:
                pass

            def do_POST(self) -> None:
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append({"received_at": time.monotonic(), "payload": payload})
                stage = len(outer.requests) - 1
                calls = []
                name, arguments = steps[stage] if stage < len(steps) else ("", {})
                if name:
                    calls = [{"index": 0, "id": f"ae_call_{stage}", "type": "function",
                              "function": {"name": name, "arguments": json.dumps(arguments)}}]
                delta = {"role": "assistant"}
                delta.update({"tool_calls": calls} if calls else {"content": "AE_PREFLIGHT_HOST_OK"})
                outer.requests[-1]["fixture_response"] = delta
                chunk = {"id": f"fixture-{stage}", "object": "chat.completion.chunk",
                         "created": 1, "model": "fixture-main",
                         "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for value in [chunk, {**chunk, "choices": [{"index": 0, "delta": {},
                        "finish_reason": "tool_calls" if calls else "stop"}]}]:
                    self.wfile.write(("data: " + json.dumps(value) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.httpd.server_port}/v1"

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def run_case(output: Path, mode: int, scenario: str = "selected") -> dict:
    """Run one real host session in isolated config/data with one AE gateway."""
    case = output / f"mode-{mode}-{scenario}"
    case.mkdir(mode=0o700)
    project = output / "project"
    project.mkdir(exist_ok=True)
    skill_entry = preflight._registry().find_entry("skill:video-content-extractor")
    skill = ROOT / skill_entry["source_path"]
    assert skill.is_file(), skill
    clip = project / "synthetic.mp4"
    if not clip.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                        "color=c=blue:s=32x32:d=0.2", "-y", str(clip)], check=True)
    prompt = (f"AE_SYNTHETIC_ONLY: inspect local video {clip}. "
              "Use the video-content-extractor skill before probing metadata with ffmpeg. "
              "Report the video dimensions. Keep this complete user prompt intact.")
    items = [
        {"id": "skill:video-content-extractor"},
        {"id": "tool:ffmpeg-mcp/ffmpeg_probe"},
    ]
    skill_paths = [skill]
    responses = [SelectorFixture.selection("selected", items=items)]
    if scenario == "abstain":
        prompt = "AE_SYNTHETIC_ONLY: Reply with the number 4."
        responses = [SelectorFixture.selection("abstain")]
    elif scenario == "unavailable":
        responses = [SelectorFixture.selection("selected", items=[
            {"id": "tool:ffmpeg-mcp/ae_missing_fixture_tool"}])]
    elif scenario == "guide":
        items.append({"id": "plugin:openmontage", "required": False})
        skill_paths.append(ROOT / preflight._registry().find_entry("plugin:openmontage")["path"])
        responses = [SelectorFixture.selection("selected", items=items)]
    elif scenario == "lookup":
        prompt = (f"AE_SYNTHETIC_ONLY: Inspect local video metadata for {clip} and troubleshoot "
                  "the slow relational metadata query planner. Read appropriate guidance "
                  "before probing the video and reviewing PostgreSQL query tuning.")
        # The focused lookup must add a genuinely absent initial candidate.
        initial = preflight._registry().paged_search(prompt, limit=8)
        target = "skill:postgresql-optimization"
        assert target not in [c["id"] for c in initial["cards"]], initial
        focused = preflight._registry().paged_search("PostgreSQL EXPLAIN ANALYZE planner indexing", limit=5)
        assert target in [c["id"] for c in focused["cards"]], focused
        items.insert(1, {"id": target})
        skill_paths.append(ROOT / preflight._registry().find_entry(target)["source_path"])
        responses = [SelectorFixture.selection("lookup", queries=["PostgreSQL EXPLAIN ANALYZE planner indexing"]),
                     SelectorFixture.selection("selected", items=items)]
    selector = SelectorFixture(responses)
    steps = []
    if mode == 0 or scenario in ("unavailable", "stale"):
        steps.append(("shell", {"command": shlex.join([sys.executable, str(UI / "scripts/registry.py"),
                                                     "search", "video metadata ffmpeg"])}))
    if scenario != "abstain":
        steps.extend(("read", {"path": str(path)}) for path in skill_paths)
        if scenario == "stale":
            steps.append(("shell", {"command": shlex.join(["ffprobe", "-v", "error", "-show_streams",
                                                          "-of", "json", str(clip)])}))
        else:
            steps.append(("execute", {"code": 'return await tools["agent-enhancements"]'
                                      f'.ffmpeg_probe({json.dumps({"path": str(clip)})})'}))
    main = MainFixture(steps)
    try:
        model_file, api_file = case / "model.json", case / "ui.api.json"
        write_json(model_file, {"adaptive_preflight_mode": mode, "endpoint": selector.endpoint,
                               "sdk": "openai", "model": "fixture-selector"})
        write_json(api_file, {})
        cfg = case / "config" / "opencode"
        cfg.mkdir(parents=True)
        diagnostics = case / "host.jsonl"
        fixture_plugin = case / "fixture-plugin"
        fixture_plugin.mkdir()
        write_json(fixture_plugin / "package.json", {"name": "ae-preflight-fixture",
                   "type": "module", "exports": {".": "./index.js"}})
        fixture_plugin.joinpath("index.js").write_text(
            'import { Model, Provider } from "@opencode/plugin";\n'
            'import { appendFileSync } from "node:fs";\n'
            'export default { id: "ae-preflight-fixture", async setup(ctx) {\n'
            'await ctx.provider.transform(editor => editor.add({\n'
            'info: {...Provider.Info.empty("ae-fixture"), name:"Local fixture", '
            'activation:"enabled", package:"@opencode/ai/providers/openai-compatible", '
            f'settings:{{baseURL:{json.dumps(main.endpoint)},apiKey:"synthetic-only"}}}},\n'
            'models:[{...Model.Info.default("ae-fixture","fixture"),name:"Local fixture"}] }));\n'
            'await ctx.session.hook("prompt", async input => {\n'
            f'appendFileSync({json.dumps(str(diagnostics))}, JSON.stringify({{event:"prompt", '
            'at:Number(process.hrtime.bigint())/1e9, session:input.sessionID, tools: await ctx.tool.list(), '
            'mcp: await ctx.mcp.list(), plugins: await ctx.plugin.list()})+"\\n", {mode:0o600}); });\n'
            + ('await ctx.session.hook("prompt", async () => { await ctx.tool.transform(editor => '
               'editor.remove("agent-enhancements_ffmpeg_probe")); });\n' if scenario == "stale" else '') +
            'await ctx.session.hook("context", input => {\n'
            f'appendFileSync({json.dumps(str(diagnostics))}, JSON.stringify({{event:"context", '
            'at:Number(process.hrtime.bigint())/1e9, session:input.sessionID, tools:input.tools})+"\\n", {mode:0o600}); });\n'
            '} };\n'
        )
        python = str(ROOT / ".agentenhancements/runtime/venv/bin/python")
        env = {**os.environ,
               "AGENT_ENHANCEMENTS_MODEL_FILE": str(model_file),
               "AGENT_ENHANCEMENTS_API_FILE": str(api_file),
               "AGENT_ENHANCEMENTS_PREFLIGHT_API_KEY": "synthetic-selector-only",
               "AGENT_MEMORY_ROOT": str(case / "memory"),
               "TASK_OBSERVER_WORKSPACE": str(case / "observer"),
               "SSL_CERT_FILE": str(selector.ca),
               "XDG_CONFIG_HOME": str(case / "config"),
               "XDG_DATA_HOME": str(case / "data"),
               "XDG_CACHE_HOME": str(case / "cache"),
               "HTTP_PROXY": "http://127.0.0.1:1", "HTTPS_PROXY": "http://127.0.0.1:1",
               "ALL_PROXY": "http://127.0.0.1:1", "NO_PROXY": "127.0.0.1,localhost",
               "http_proxy": "http://127.0.0.1:1", "https_proxy": "http://127.0.0.1:1",
               "all_proxy": "http://127.0.0.1:1", "no_proxy": "127.0.0.1,localhost"}
        env.pop("AGENT_ENHANCEMENTS_STATE_DIR", None)
        env.pop("AGENT_SKILLS_DIR", None)
        write_json(cfg / "opencode.json", {"$schema": "https://opencode.ai/config.json",
            "model": "ae-fixture/fixture", "plugins": [str(UI / "opencode-plugin"), str(fixture_plugin)],
            "mcp": {"agent-enhancements": {"type": "local", "command": [
                python, str(UI / "mcp-servers/gateway.py")], "environment": {
                "AGENT_ENHANCEMENTS_API_FILE": str(api_file)}}}})
        write_json(project / "opencode.json", {})
        # Instrument this disposable fixture DB only. Upserts would otherwise
        # hide a duplicate UserPromptSubmit behind one final task row.
        subprocess.run([python, "-c", "from memory import AgentMemory; AgentMemory('opencode')"],
                       env={**env, "PYTHONPATH": str(UI / "scripts")}, cwd=project, check=True)
        with sqlite3.connect(case / "memory/memory.db") as conn:
            conn.executescript("""
                CREATE TABLE ae_fixture_task_writes (operation TEXT);
                CREATE TRIGGER ae_fixture_task_insert AFTER INSERT ON memories
                WHEN NEW.key LIKE 'session:%:task'
                BEGIN INSERT INTO ae_fixture_task_writes VALUES ('insert'); END;
                CREATE TRIGGER ae_fixture_task_update AFTER UPDATE ON memories
                WHEN NEW.key LIKE 'session:%:task'
                BEGIN INSERT INTO ae_fixture_task_writes VALUES ('update'); END;
            """)
        started = time.monotonic()
        process = subprocess.run(["opencode", "run", prompt, "--format", "json", "--standalone",
            "--auto", "--title", "AE preflight fixture", "--model", "ae-fixture/fixture"],
            cwd=project, env=env, capture_output=True, text=True, timeout=50)
        write_json(case / "main-requests.json", sanitized(main.requests))
        write_json(case / "selector-requests.json", sanitized([
            {key: r[key] for key in ("path", "payload", "response", "status", "received_at", "completed_at") if key in r}
            for r in selector.requests]))
        stderr_path = case / "host-stderr.log"
        stderr_path.write_text(sanitized(process.stderr))
        stderr_path.chmod(0o600)
        assert process.returncode == 0, f"OpenCode exit {process.returncode}: {process.stderr[-1500:]}"
        assert "AE_PREFLIGHT_HOST_OK" in process.stdout, process.stdout[-1500:]
        assert len(main.requests) == len(steps) + 1, len(main.requests)
        first = main.requests[0]["payload"]
        user_texts = [m["content"] if isinstance(m["content"], str) else
                      "".join(p["text"] for p in m["content"] if p["type"] == "text")
                      for m in first["messages"] if m["role"] == "user"]
        assert user_texts == [prompt], "decoded user prompt changed"
        tools = {t["function"]["name"]: t["function"] for t in first["tools"]}
        context = "\n".join(m["content"] for m in first["messages"] if m["role"] == "system")
        probe = 'tools["agent-enhancements"].ffmpeg_probe'
        if scenario != "stale":
            assert "execute" in tools and probe in context, "Code Mode tool/schema missing"
            assert probe + "({\n  path: string," in context, "required path schema changed"
        selected = mode == 2 and scenario in ("selected", "lookup", "guide")
        if selected:
            assert len(selector.requests) == (2 if scenario == "lookup" else 1)
            assert "AgentEnhancements preflight" in context
            package = context[context.index("AgentEnhancements preflight"):]
            assert probe in package, f"exact exposed name {probe!r} absent from package"
            for path in skill_paths:
                assert str(path) in package
            if scenario == "guide":
                assert "plugin:openmontage" in package and "read before related work" in package
            assert "local skill candidates" not in context
        elif mode == 0:
            assert not selector.requests
            assert "local skill candidates" in context
        elif scenario == "abstain":
            assert len(selector.requests) == 1
            assert "AgentEnhancements preflight" not in context
            assert "local skill candidates" not in context
        else:
            assert len(selector.requests) == 1
            assert "AgentEnhancements preflight" not in context
            assert "local skill candidates" in context
        discovery_results = []
        for index, (name, arguments) in enumerate(steps):
            result = next(m["content"] for m in main.requests[index + 1]["payload"]["messages"]
                          if m.get("tool_call_id") == f"ae_call_{index}" and m["role"] == "tool")
            if name == "read":
                marker = "# Video Content Extractor" if arguments["path"] == str(skill) else (
                    "OpenMontage" if scenario == "guide" else "PostgreSQL")
                assert "tool.execution" not in result and marker in result, "skill read failed"
            if name == "shell" and "registry.py" in arguments["command"]:
                discovery_results.append(result)
            if name == "execute" or scenario == "stale" and index == len(steps) - 1:
                metadata = json.loads(result[result.index("{"):])
                streams = metadata["streams"] if scenario == "stale" else metadata["video_streams"]
                assert streams[0]["width"] == 32, "probe result did not return to main model"
        with sqlite3.connect(case / "memory/memory.db") as conn:
            tasks = conn.execute("select count(*) from memories where key like 'session:%:task'").fetchone()[0]
            writes = conn.execute("select count(*) from ae_fixture_task_writes").fetchone()[0]
        assert tasks == 1, tasks
        assert writes == 1, writes
        events = [json.loads(line) for line in diagnostics.read_text().splitlines()]
        assert [e["event"] for e in events].count("prompt") == 1
        active = next(p for p in events[0]["plugins"]["data"] if p["id"] == "agentenhancements")
        assert active["state"]["status"] == "active" and active["features"]["server"]
        assert events[0]["at"] < main.requests[0]["received_at"], "prompt hook ran too late"
        if selector.requests:
            assert selector.requests[-1]["completed_at"] < main.requests[0]["received_at"], "selector finished too late"
        ledger = context_ledger(context, tools, discovery_results)
        return {"mode": mode, "effective_mode": 2 if selected or scenario == "abstain" else 0,
                "scenario": scenario, "selector_requests": len(selector.requests), "main_requests": len(main.requests),
                "first_main_seconds": main.requests[0]["received_at"] - started,
                "exact_tool": probe, "skill_read": str(skill), "memory_task_rows": tasks,
                "memory_task_writes": writes, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "context_budget": ledger,
                "selector_round_trip_seconds": [r["completed_at"] - r["received_at"] for r in selector.requests],
                "token_proxies": {
                    "method": "chars/4 of serialized messages/tools and fixture output; not provider usage",
                    "selector": [{"input": approx_tokens(json.dumps(r["payload"]["messages"])),
                                  "output": approx_tokens(r["response"]["choices"][0]["message"]["content"])}
                                 for r in selector.requests],
                    "main": [{"input": approx_tokens(json.dumps({k: r["payload"][k] for k in ("messages", "tools")})),
                              "output": approx_tokens(json.dumps(r["fixture_response"]))} for r in main.requests],
                },
                "existing_plugin_entrypoint": {"id": active["id"], "source": active["source"],
                                               "hooks_used": ["prompt", "context"],
                                               "catalog_plugin_runtime_certified": False},
                "catalog_searches": sum(name == "shell" and "registry.py" in args["command"] for name, args in steps),
                "detail_reads": sum(name == "read" for name, _ in steps),
                "provider_usage": None, "cost": None, "synthetic_inference": True}
    finally:
        main.close()
        selector.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", type=int, choices=[0, 2], default=2)
    parser.add_argument("--scenario", choices=["selected", "abstain", "lookup", "stale", "unavailable", "guide"], default="selected")
    args = parser.parse_args()
    if args.scenario == "abstain" and args.mode != 2:
        # "abstain" models a selector that ran and declined; no selector exists in
        # Mode 0, so the combination is contradictory rather than a coverage gap.
        parser.error("the abstain scenario requires --mode 2 (it models a selector that declined)")
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    result = run_case(args.output.resolve(), args.mode, args.scenario)
    result["host_version"] = subprocess.check_output(["opencode", "--version"], text=True).strip()
    write_json(args.output / f"summary-mode-{args.mode}-{args.scenario}.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
