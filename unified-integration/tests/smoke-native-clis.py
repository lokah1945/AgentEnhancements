#!/usr/bin/env python3
"""Exercise installed CLI hooks against a deterministic localhost model fixture.

Run after setup and Codex hook review: python3 tests/smoke-native-clis.py.
No real model is called. Remote HTTP proxies point to a closed local port;
only localhost is allowed through. CLI cost displays are simulated estimates.
The test creates temporary config/data and checks automatic task + summary notes.
"""

import argparse
import json, os, subprocess, tempfile, threading, time, sqlite3, shutil
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

counts = {}
tools_seen = {}
tool_catalogs = {}
health_outputs = {}
exercise_tools = False
api_config_path = None


def openai_health(payload):
    """Read the credential boolean from native or serialized MCP envelopes."""
    if isinstance(payload, str):
        try:
            payload, _ = json.JSONDecoder().raw_decode(payload[payload.index("{"):])
        except (ValueError, TypeError):
            return None
    if isinstance(payload, list):
        for item in payload:
            found = openai_health(item)
            if found is not None:
                return found
    if isinstance(payload, dict):
        backends = payload.get("backends")
        if isinstance(backends, dict) and isinstance(backends.get("openai"), bool):
            return backends["openai"]
        for key in ("structuredContent", "embeddings-mcp", "backends", "content", "text"):
            if key in payload:
                found = openai_health(payload[key])
                if found is not None:
                    return found
    return None


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
        if exercise_tools:

            def outputs(item):
                if isinstance(item, list):
                    for child in item:
                        outputs(child)
                elif isinstance(item, dict):
                    identity = (
                        item.get("call_id")
                        or item.get("tool_use_id")
                        or item.get("tool_call_id")
                    )
                    if (
                        identity
                        and identity.startswith("call_fixture_")
                        and (
                            item.get("type") in ("function_call_output", "tool_result")
                            or item.get("role") == "tool"
                        )
                    ):
                        raw = item.get("output", item.get("content", ""))
                        if isinstance(raw, list):
                            raw = "\n".join(
                                x.get("text", "") for x in raw if isinstance(x, dict)
                            )
                        if isinstance(raw, str):
                            try:
                                data, _ = json.JSONDecoder().raw_decode(
                                    raw[raw.index("{") :]
                                )
                                # Consolidated ae_health payload: one
                                # report per backend; embeddings carries the
                                # openai credential boolean. Older per-server
                                # payloads had it at the top level.
                                health_outputs.setdefault(self.path, {})[identity] = openai_health(data)
                            except (ValueError, KeyError):
                                pass
                    for child in item.values():
                        if isinstance(child, (dict, list)):
                            outputs(child)

            outputs(doc.get("input", doc.get("messages", [])))
        declared = []
        health = []

        def visit(items, namespace=None):
            for tool in items:
                name = tool.get("name") or tool.get("function", {}).get("name", "")
                if "embeddings" in name or "vision" in name:
                    declared.append(name)
                if name == "ae_health" or name.endswith(("__ae_health", "_ae_health")):
                    health.append((name, namespace))
                visit(
                    tool.get("tools", []),
                    tool.get("name") if tool.get("type") == "namespace" else namespace,
                )

        visit(doc.get("tools", []))
        if declared:
            tools_seen.setdefault(self.path, set()).update(declared)
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
                "phase": "final_answer",
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
        if exercise_tools and health:
            stage = len(tool_catalogs.setdefault(self.path, []))
            tool_catalogs[self.path].append(
                any("vision_describe" in name for name in declared)
            )
            if stage < 2:
                # A real CLI must consume the list-change notification while
                # handling a normal model-requested local health call.
                config = json.loads(api_config_path.read_text())
                config["api_keys"]["OPENAI_API_KEY"] = (
                    "local-fixture-unused-key" if stage == 0 else ""
                )
                api_config_path.write_text(json.dumps(config))
                time.sleep(1)
                name, namespace = health[0]
                call_id = f"call_fixture_{stage}"
                if "/messages" in self.path:
                    block = {
                        "type": "tool_use",
                        "id": call_id,
                        "name": name,
                        "input": {},
                    }
                    regular = {**regular, "content": [block], "stop_reason": "tool_use"}
                    events = [
                        (
                            "message_start",
                            {"type": "message_start", "message": message},
                        ),
                        (
                            "content_block_start",
                            {
                                "type": "content_block_start",
                                "index": 0,
                                "content_block": block,
                            },
                        ),
                        (
                            "content_block_stop",
                            {"type": "content_block_stop", "index": 0},
                        ),
                        (
                            "message_delta",
                            {
                                "type": "message_delta",
                                "delta": {
                                    "stop_reason": "tool_use",
                                    "stop_sequence": None,
                                },
                                "usage": {"output_tokens": 10},
                            },
                        ),
                        ("message_stop", {"type": "message_stop"}),
                    ]
                elif "/chat/completions" in self.path:
                    call = {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": "{}"},
                    }
                    regular["choices"] = [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [call],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                    events = [
                        (
                            "",
                            {
                                **chunk,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {
                                            "role": "assistant",
                                            "tool_calls": [{"index": 0, **call}],
                                        },
                                        "finish_reason": None,
                                    }
                                ],
                            },
                        ),
                        (
                            "",
                            {
                                **chunk,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {},
                                        "finish_reason": "tool_calls",
                                    }
                                ],
                            },
                        ),
                    ]
                else:
                    call = {
                        "id": f"fc_{stage}",
                        "type": "function_call",
                        "call_id": call_id,
                        "name": name,
                        "arguments": "{}",
                        "status": "completed",
                    }
                    if namespace:
                        call["namespace"] = namespace
                    regular = {**response, "output": [call]}
                    events = [
                        (
                            "response.created",
                            {
                                "type": "response.created",
                                "response": {
                                    **response,
                                    "status": "in_progress",
                                    "output": [],
                                },
                            },
                        ),
                        (
                            "response.output_item.added",
                            {
                                "type": "response.output_item.added",
                                "output_index": 0,
                                "item": {
                                    **call,
                                    "arguments": "",
                                    "status": "in_progress",
                                },
                            },
                        ),
                        (
                            "response.function_call_arguments.delta",
                            {
                                "type": "response.function_call_arguments.delta",
                                "item_id": call["id"],
                                "output_index": 0,
                                "delta": "{}",
                            },
                        ),
                        (
                            "response.function_call_arguments.done",
                            {
                                "type": "response.function_call_arguments.done",
                                "item_id": call["id"],
                                "output_index": 0,
                                "arguments": "{}",
                            },
                        ),
                        (
                            "response.output_item.done",
                            {
                                "type": "response.output_item.done",
                                "output_index": 0,
                                "item": call,
                            },
                        ),
                        (
                            "response.completed",
                            {"type": "response.completed", "response": regular},
                        ),
                    ]
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent", choices=["all", "claude-code", "codex", "opencode"], default="all"
    )
    parser.add_argument("--exercise-tools", action="store_true")
    options = parser.parse_args()
    selected = options.agent
    global exercise_tools, api_config_path
    exercise_tools = options.exercise_tools
    server = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    root = Path(tempfile.mkdtemp(prefix="ae-native-smoke-"))
    try:
        (root / "project").mkdir()
        env = dict(os.environ)
        api_file = root / "ui.api.json"
        api_config_path = api_file
        api_file.write_text((UNIFIED_DIR / "config/ui.api.example.json").read_text())
        env.update(
            AGENT_MEMORY_ROOT=str(root / "memory"),
            CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
            ANTHROPIC_BASE_URL=base,
            ANTHROPIC_AUTH_TOKEN="fixture-local-only",
            NO_PROXY="127.0.0.1,localhost",
            no_proxy="127.0.0.1,localhost",
            AGENT_ENHANCEMENTS_API_FILE=str(api_file),
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
            "mcp_servers.agent-enhancements.env.AGENT_ENHANCEMENTS_API_FILE="
            + json.dumps(str(api_file)),
            "-c",
            'mcp_servers.agent-enhancements.tools.ae_health.approval_mode="auto"',
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
            "--allowedTools",
            "mcp__agent-enhancements__ae_health",
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
        python = Path.home() / ".local/share/agentenhancements/venv/bin/python"
        claude_config = root / "claude"
        claude_config.mkdir()
        (claude_config / "settings.json").write_text(
            json.dumps(
                {
                    "env": {
                        "ANTHROPIC_BASE_URL": base,
                        "ANTHROPIC_AUTH_TOKEN": "fixture-local-only",
                    },
                }
            )
        )
        (claude_config / ".claude.json").write_text(
            json.dumps({"hasCompletedOnboarding": True})
        )
        subprocess.run(
            [
                str(python),
                str(UNIFIED_DIR / "scripts/native-integration.py"),
                "--agent",
                "claude-code",
            ],
            env={**env, "CLAUDE_CONFIG_DIR": str(claude_config)},
            capture_output=True,
            check=True,
            timeout=15,
        )
        subprocess.run(
            [
                str(python),
                str(UNIFIED_DIR / "scripts/native-integration.py"),
                "--agent",
                "opencode",
                "--mcp-only",
            ],
            env=env,
            capture_output=True,
            check=True,
            timeout=15,
        )

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
                    "--auto",
                    "--title",
                    "AE local fixture",
                    "--model",
                    "ae-fixture/fixture",
                ],
            ),
        ]:
            if selected != "all" and name != selected:
                continue
            try:
                empty = json.loads(api_file.read_text())
                empty["api_keys"]["OPENAI_API_KEY"] = ""
                api_file.write_text(json.dumps(empty))
                runenv = {**env}
                if name == "opencode":
                    runenv["OPENAI_API_KEY"] = "fixture-local-only"
                if name == "claude-code":
                    runenv["CLAUDE_CONFIG_DIR"] = str(claude_config)
                r = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env={**runenv, "PWD": str(root / "project")},
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
                if exercise_tools or not success or not tools_seen:
                    log_dir = Path(tempfile.gettempdir())
                    log = log_dir / f"agentenhancements-fixture-{name}.log"
                    log.touch(mode=0o600, exist_ok=True)
                    log.write_text(r.stderr)
            except subprocess.TimeoutExpired as timeout:
                print(name, "timeout", flush=True)
                log_dir = Path(tempfile.gettempdir())
                log = log_dir / f"agentenhancements-fixture-{name}.log"
                log.touch(mode=0o600, exist_ok=True)
                log.write_bytes(timeout.stderr or b"")
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
        print(
            "Automatically discovered MCP tools:",
            {p: sorted(names) for p, names in tools_seen.items()},
        )
        endpoints = {
            "codex": "/v1/responses",
            "claude-code": "/v1/messages",
            "opencode": "/v1/chat/completions",
        }
        for agent, _ in results:
            endpoint = endpoints[agent]
            candidates = set().union(
                *(
                    names
                    for path, names in tools_seen.items()
                    if endpoint.split("/v1")[-1] in path
                )
            )
            assert any(
                "embeddings_embed" in name for name in candidates
            ), f"{endpoint}: automatic gateway discovery missing"
            if not exercise_tools:
                assert not any(
                    "vision_describe" in name for name in candidates
                ), f"{endpoint}: empty-key cloud tool was exposed"
            else:
                stages = next(
                    (
                        stages
                        for p, stages in tool_catalogs.items()
                        if endpoint.split("/v1")[-1] in p
                    ),
                    [],
                )
                print(agent, "live cloud visibility stages:", stages)
                expected = (
                    ([False, True, False], [False, False, False])
                    if agent == "codex"
                    else ([False, True, False],)
                )
                assert stages in expected, f"{agent}: unexpected live tool visibility"
                observed = next(
                    (
                        values
                        for p, values in health_outputs.items()
                        if endpoint.split("/v1")[-1] in p
                    ),
                    {},
                )
                print(
                    agent,
                    "automatic health call credential states:",
                    list(observed.values()),
                )
                assert list(observed.values()) == [
                    True,
                    False,
                ], f"{agent}: automatic MCP calls did not observe current credentials"
                if agent == "codex" and stages == [False, False, False]:
                    print(
                        "Codex retains a tool catalog snapshot during one turn; revoked calls are still checked by the gateway."
                    )
        with sqlite3.connect(root / "memory/memory.db") as conn:
            rows = conn.execute("SELECT agent, value FROM memories").fetchall()
            for name, success in results:
                assert success, f"{name}: the localhost fixture did not complete"
                if not any(
                    agent == name and "AGENT_ENHANCEMENTS_FIXTURE_OK" in value
                    for agent, value in rows
                ):
                    print(
                        "Missing-summary diagnostic:",
                        conn.execute(
                            "SELECT agent,key,length(value) FROM memories WHERE agent=?",
                            (name,),
                        ).fetchall(),
                    )
                assert any(
                    agent == name and "AGENT_ENHANCEMENTS_FIXTURE_OK" in value
                    for agent, value in rows
                ), f"{name}: native summary hook did not run"
    finally:
        server.shutdown()
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
