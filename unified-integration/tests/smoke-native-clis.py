#!/usr/bin/env python3
"""Exercise installed CLI hooks against a deterministic localhost model fixture.

Run after setup and Codex hook review: python3 tests/smoke-native-clis.py.
No real model is called. Remote HTTP proxies point to a closed local port;
only localhost is allowed through. CLI cost displays are simulated estimates.
The test creates temporary config/data and checks automatic task + summary notes.
"""

import json, os, subprocess, tempfile, threading, time, sqlite3, shutil
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

counts = {}


class Mock(BaseHTTPRequestHandler):
    """Minimal Anthropic Messages and OpenAI Responses/Chat SSE fixture."""

    def log_message(self, *args: object) -> None:
        pass

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(
            json.dumps({"data": [{"id": "gpt-5.4", "object": "model"}]}).encode()
        )

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            doc = json.loads(body)
        except:
            doc = {}
        counts[self.path] = counts.get(self.path, 0) + 1
        if "count_tokens" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"input_tokens":100}')
            return
        text = "AGENT_ENHANCEMENTS_FIXTURE_OK"
        if "/messages" in self.path:
            message = {
                "id": "msg_fixture",
                "type": "message",
                "role": "assistant",
                "model": doc.get("model", "fixture"),
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 100, "output_tokens": 0},
            }
            events = [
                ("message_start", {"type": "message_start", "message": message}),
                (
                    "content_block_start",
                    {
                        "type": "content_block_start",
                        "index": 0,
                        "content_block": {"type": "text", "text": ""},
                    },
                ),
                (
                    "content_block_delta",
                    {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {"type": "text_delta", "text": text},
                    },
                ),
                ("content_block_stop", {"type": "content_block_stop", "index": 0}),
                (
                    "message_delta",
                    {
                        "type": "message_delta",
                        "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                        "usage": {"output_tokens": 10},
                    },
                ),
                ("message_stop", {"type": "message_stop"}),
            ]
            regular = {
                **message,
                "content": [{"type": "text", "text": text}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 100, "output_tokens": 10},
            }
        elif "/chat/completions" in self.path:
            chunk = {
                "id": "chatcmpl-fixture",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": doc.get("model", "fixture"),
            }
            events = [
                (
                    "",
                    {
                        **chunk,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"role": "assistant", "content": text},
                                "finish_reason": None,
                            }
                        ],
                    },
                ),
                (
                    "",
                    {
                        **chunk,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                        "usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 10,
                            "total_tokens": 110,
                        },
                    },
                ),
            ]
            regular = {
                **chunk,
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text},
                        "finish_reason": "stop",
                    }
                ],
            }
        else:
            item = {
                "id": "msg_fixture",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
            response = {
                "id": "resp_fixture",
                "object": "response",
                "created_at": int(time.time()),
                "status": "completed",
                "model": doc.get("model", "fixture"),
                "output": [item],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 10,
                    "total_tokens": 110,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            }
            events = [
                (
                    "response.created",
                    {
                        "type": "response.created",
                        "response": {**response, "status": "in_progress", "output": []},
                    },
                ),
                (
                    "response.output_item.added",
                    {
                        "type": "response.output_item.added",
                        "output_index": 0,
                        "item": {**item, "status": "in_progress", "content": []},
                    },
                ),
                (
                    "response.content_part.added",
                    {
                        "type": "response.content_part.added",
                        "item_id": item["id"],
                        "output_index": 0,
                        "content_index": 0,
                        "part": {"type": "output_text", "text": "", "annotations": []},
                    },
                ),
                (
                    "response.output_text.delta",
                    {
                        "type": "response.output_text.delta",
                        "item_id": item["id"],
                        "output_index": 0,
                        "content_index": 0,
                        "delta": text,
                    },
                ),
                (
                    "response.output_text.done",
                    {
                        "type": "response.output_text.done",
                        "item_id": item["id"],
                        "output_index": 0,
                        "content_index": 0,
                        "text": text,
                    },
                ),
                (
                    "response.output_item.done",
                    {
                        "type": "response.output_item.done",
                        "output_index": 0,
                        "item": item,
                    },
                ),
                (
                    "response.completed",
                    {"type": "response.completed", "response": response},
                ),
            ]
            regular = response
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/event-stream" if doc.get("stream") else "application/json",
        )
        self.end_headers()
        try:
            if doc.get("stream"):
                for name, value in events:
                    self.wfile.write(
                        (
                            (("event: " + name + "\n") if name else "")
                            + "data: "
                            + json.dumps(value)
                            + "\n\n"
                        ).encode()
                    )
                    self.wfile.flush()
                if "/chat/completions" in self.path:
                    self.wfile.write(b"data: [DONE]\n\n")
            else:
                self.wfile.write(json.dumps(regular).encode())
        except (BrokenPipeError, ConnectionResetError):
            pass


UNIFIED_DIR = Path(__file__).resolve().parent.parent


def main() -> None:
    """Run three installed clients and assert automatic notes were persisted."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    root = Path(tempfile.mkdtemp(prefix="ae-native-smoke-"))
    try:
        (root / "project").mkdir()
        env = dict(os.environ)
        env.update(
            AGENT_MEMORY_ROOT=str(root / "memory"),
            CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
            ANTHROPIC_BASE_URL=base,
            ANTHROPIC_AUTH_TOKEN="fixture-local-only",
            NO_PROXY="127.0.0.1,localhost",
        )
        env.update(
            HTTPS_PROXY="http://127.0.0.1:1",
            HTTP_PROXY="http://127.0.0.1:1",
            ALL_PROXY="http://127.0.0.1:1",
        )
        results = []
        codex = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--json",
            "-c",
            'model_provider="ae_fixture"',
            "-c",
            f'model_providers.ae_fixture={{name="local fixture",base_url="{base}/v1",wire_api="responses"}}',
            "-m",
            "fixture",
            "security audit fixture; respond briefly",
        ]
        claude = [
            "claude",
            "-p",
            "security audit fixture; respond briefly",
            "--output-format",
            "json",
            "--model",
            "claude-sonnet-4-6",
        ]
        opencfg = root / "project/opencode.json"
        fixture = root / "fixture-plugin"
        fixture.mkdir()
        fixture.joinpath("package.json").write_text(
            json.dumps(
                {
                    "name": "ae-local-model-fixture",
                    "type": "module",
                    "exports": {".": "./index.js"},
                }
            )
        )
        fixture.joinpath("index.js").write_text(
            """import { Model, Provider } from '@opencode/plugin';
        export default {id:'ae-local-fixture',async setup(ctx){
         await ctx.provider.transform(editor=>editor.add({
         info:{...Provider.Info.empty('ae-fixture'),name:'Local test fixture',activation:'enabled',package:'@opencode/ai/providers/openai-compatible',settings:{baseURL:'LOCAL_BASE_URL/v1',apiKey:'local-test-only'}},
         models:[{...Model.Info.default('ae-fixture','fixture'),name:'Local test fixture'}]
         }));
        }};
        """.replace("LOCAL_BASE_URL", base)
        )
        global_config = root / "config/opencode"
        global_config.mkdir(parents=True)
        (global_config / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "model": "ae-fixture/fixture",
                    "plugins": [str(UNIFIED_DIR / "opencode-plugin"), str(fixture)],
                }
            )
        )
        opencfg.write_text("{}")
        env["XDG_CONFIG_HOME"] = str(root / "config")

        for name, cmd in [
            ("codex", codex),
            ("claude-code", claude),
            (
                "opencode",
                [
                    "opencode",
                    "run",
                    "security audit fixture; respond briefly",
                    "--format",
                    "json",
                    "--standalone",
                    "--title",
                    "AE local fixture",
                    "--model",
                    "ae-fixture/fixture",
                ],
            ),
        ]:
            try:
                runenv = {**env}
                if name == "opencode":
                    runenv["OPENAI_API_KEY"] = "fixture-local-only"
                r = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=runenv,
                    cwd=root / "project",
                    timeout=65,
                )
                success = (
                    r.returncode == 0 and "AGENT_ENHANCEMENTS_FIXTURE_OK" in r.stdout
                )
                print(
                    name,
                    "exit",
                    r.returncode,
                    "fixture response",
                    success,
                    "output bytes",
                    len(r.stdout) + len(r.stderr),
                    flush=True,
                )
                results.append((name, success))
            except subprocess.TimeoutExpired:
                print(name, "timeout", flush=True)
                results.append((name, False))
        if (root / "memory/memory.db").exists():
            with sqlite3.connect(root / "memory/memory.db") as conn:
                print(
                    "Automatically stored native events:",
                    conn.execute(
                        "select agent,count(*) from memories group by agent"
                    ).fetchall(),
                )
        print("Local fixture requests:", counts)
        with sqlite3.connect(root / "memory/memory.db") as conn:
            rows = conn.execute("SELECT agent, value FROM memories").fetchall()
            for name, success in results:
                assert success, f"{name}: the localhost fixture did not complete"
                assert any(
                    agent == name and "AGENT_ENHANCEMENTS_FIXTURE_OK" in value
                    for agent, value in rows
                ), f"{name}: native summary hook did not run"
    finally:
        server.shutdown()
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
