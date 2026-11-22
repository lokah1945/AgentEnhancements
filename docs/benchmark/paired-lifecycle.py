"""Measure local AE surfaces and grade repeatable workflow fixture reachability."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import shlex
import statistics
import subprocess
import sys
import tempfile
import time
import tomllib

import yaml
try:
    import tiktoken
except ImportError:
    tiktoken = None

ENCODING = tiktoken.get_encoding("o200k_base") if tiktoken else None


CASES = (
    ("typescript-refactor", "Refactor our TypeScript module for readability without changing the public API. Preserve behavior with existing tests.",
     {"code-refactoring-refactor-clean", "code-refactoring", "refactoring", "typescript-expert", "typescript", "test-driven-development"}),
    ("python-debug", "The Python service crashes while parsing its JSON config. Reproduce the bug and find its root cause before editing.",
     {"systematic-debugging", "debugger", "debugging-strategies", "debugging-toolkit", "python-pro", "python-development"}),
    ("defensive-review", "Model security threats for this payment service using STRIDE.",
     {"threat-modeling", "threat-modeling-expert", "stride-analysis-patterns"}),
    ("documentation", "Prepare a formal offer letter as a Word document.", {"docx"}),
    ("research-permissions", "Research competing approaches to retrieval augmented generation and write a cited report.",
     {"deep-research", "deep-research-framework", "agency-research-synthesist", "research-ops"}),
    ("local-video", "Edit this interview footage into short video clips with subtitles.",
     {"video-editing", "agency-marketing-short-video-editing-coach", "video-content-extractor"}),
    ("abstain", "Berapa hasil 17 dikali 23?", set()),
)
HOOK_CARD = re.compile(r"^- ([\w-]+): ", re.M)
SEARCH_CARD = re.compile(r"^- .*\[skill\] skill:([\w-]+)$", re.M)
MEMORY_HEADER = "AgentEnhancements: previous local session notes"


def tokens(text: str) -> int:
    """Count the synthetic evidence with the preloaded o200k_base encoding."""
    if ENCODING:
        return len(ENCODING.encode(text, disallowed_special=()))
    return len(text) // 4 + 1 if text else 0


def summary(values: list[float]) -> dict:
    """Report median and nearest-rank p95 with count."""
    return {"n": len(values), "p50": round(statistics.median(values), 3),
            "p95": round(sorted(values)[math.ceil(len(values) * .95) - 1], 3),
            "max": round(max(values), 3)}


def command(args: list[str], env: dict, cwd: Path, data: str | None = None) -> tuple[str, float, int]:
    start = time.perf_counter()
    result = subprocess.run(args, input=data, env=env, cwd=cwd, capture_output=True,
                            text=True, check=False, timeout=25)
    return result.stdout, (time.perf_counter() - start) * 1000, result.returncode


def run_hook(repo: Path, project: Path, env: dict, event: str, prompt: str = "") -> tuple[str, float]:
    result, elapsed, status = command([sys.executable, str(repo / "unified-integration/scripts/runtime.py"), "codex"],
                                      env, project, json.dumps({"hook_event_name": event,
                                     "cwd": str(project), "session_id": "ae-workflow-fixture", "prompt": prompt}))
    if status:
        raise ValueError(f"{event} exited {status}")
    context = json.loads(result or "{}").get("hookSpecificOutput", {}).get("additionalContext", "")
    return context, elapsed


def payload_has(value: object, key: str, expected: object) -> bool:
    """Find a known value in a fixture-generated MCP result envelope."""
    if isinstance(value, dict):
        return value.get(key) == expected or any(payload_has(child, key, expected) for child in value.values())
    if isinstance(value, list):
        return any(payload_has(child, key, expected) for child in value)
    return False


def native_description(path: Path) -> str:
    """Read the native skill frontmatter without including its body."""
    with path.open() as file:
        if file.readline().strip() != "---":
            raise ValueError(f"Missing skill frontmatter: {path.name}")
        lines = []
        for line in file:
            if line.strip() == "---":
                break
            lines.append(line)
    return str(yaml.safe_load("".join(lines))["description"])


def installed_bootstrap(marker: str, repo: Path) -> list[str]:
    """Read the installed command and restrict execution to the checkout's map."""
    script = str(repo / "unified-integration/scripts/build-library-map.py")
    published = str(repo / "skills/library-map.json")
    for inline in re.findall(r"`([^`\n]+)`", marker):
        args = shlex.split(inline)
        if args in (["python3", script, "--print"], ["cat", published]):
            return args
    # Older installs pointed at the JSON file instead of supplying a command.
    if f"`{published}`" in marker:
        return ["cat", published]
    raise ValueError("Installed Codex instructions do not point at this checkout's L0 map")


async def wire_probe(settings: dict, env: dict, clip: Path, sample: bool) -> dict:
    """Read one real stdio response byte-for-byte, with a local optional tool call."""
    start = time.perf_counter()
    child = await asyncio.create_subprocess_exec(settings["command"], *settings["args"],
                                                env=env, stdin=asyncio.subprocess.PIPE,
                                                stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.DEVNULL)
    elapsed = {}

    async def rpc(method: str, params: dict, sequence: int | None = None) -> tuple[dict, int]:
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        if sequence is not None:
            message["id"] = sequence
        child.stdin.write(json.dumps(message).encode() + b"\n")
        await child.stdin.drain()
        if sequence is None:
            return {}, 0
        while record := await child.stdout.readline():
            parsed = json.loads(record)
            if parsed.get("id") == sequence:
                return parsed.get("result", {"isError": True}), len(record)
        raise ValueError(f"MCP exited before {method} response")

    try:
        async with asyncio.timeout(25):
            initialized, _ = await rpc("initialize", {"protocolVersion": "2025-11-25",
                "capabilities": {}, "clientInfo": {"name": "ae-paired-fixture", "version": "1"}}, 1)
            await rpc("notifications/initialized", {})
            listing, size = await rpc("tools/list", {}, 2)
            elapsed["initialize_and_list_ms"] = (time.perf_counter() - start) * 1000
            listed = listing["tools"]
            names = {item["name"] for item in listed}
            data = {"wire_bytes": size, "protocol": initialized["protocolVersion"],
                    "schema_projection": [{field: tool[field] for field in ("name", "description", "inputSchema")
                                           if tool.get(field) is not None} for tool in listed],
                    "search_shape_visible_without_key": any(name.startswith("search_") for name in names),
                    **elapsed}
            if sample:
                embedded, _ = await rpc("tools/call", {"name": "embeddings_embed",
                      "arguments": {"text": "AE local test", "backend": "local"}}, 3)
                video, _ = await rpc("tools/call", {"name": "ffmpeg_probe", "arguments": {"path": str(clip)}}, 4)
                data["embedding_256"] = not embedded.get("isError", False) and payload_has(embedded, "dim", 256)
                data["video_width_32"] = not video.get("isError", False) and payload_has(video, "width", 32)
                data["video_tool_result_proxy"] = tokens(json.dumps(video.get("structuredContent") or video.get("content")))
            return data
    finally:
        child.stdin.close()
        try:
            await asyncio.wait_for(child.wait(), 4)
        except asyncio.TimeoutError:
            child.kill()
            await child.wait()


def collect(repo: Path, home: Path, repeats: int) -> dict:
    """Capture one checkout with isolated credential-free subprocesses and state."""
    ui = repo / "unified-integration"
    indices = json.loads((ui / "skills/all-skills.json").read_text())["skills"]
    by_name = {item["name"]: item for item in indices}
    hosts = [(link.name, link / "SKILL.md") for link in sorted((home / ".agents/skills").iterdir())
             if link.is_symlink() and link.resolve().is_relative_to(repo) and (link / "SKILL.md").is_file()]
    markdown = (home / ".codex/AGENTS.md").read_text()
    marker = re.search(r"<!-- agent-enhancements:begin -->.*?<!-- agent-enhancements:end -->", markdown, re.S).group()
    bootstrap_path = repo / "skills/library-map.json"
    bootstrap_rendered = json.loads(bootstrap_path.read_text())["rendered"]
    descriptions = "<available_skills>\n" + "\n".join(
        f"- {name}: {native_description(path)} (file: {path})" for name, path in hosts
    ) + "\n</available_skills>"
    settings = tomllib.loads((home / ".codex/config.toml").read_text())["mcp_servers"]["agent-enhancements"]
    with tempfile.TemporaryDirectory(prefix="ae-comparison-") as scratch:
        fixture = Path(scratch)
        project = fixture / "project"
        project.mkdir()
        keys = fixture / "ui.api.json"
        keys.write_text(json.dumps({"version": 2, "api_keys": {}, "connections": {}, "mcp": {}, "preflight": {"mode": 0}}))
        proxies = {name: "http://127.0.0.1:1" for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")}
        env = {"PATH": os.environ["PATH"], "HOME": str(fixture), "CODEX_HOME": str(home / ".codex"),
               "AGENT_ENHANCEMENTS_BASE_DIR": str(repo), "AGENT_ENHANCEMENTS_API_FILE": str(keys),
               "AGENT_ENHANCEMENTS_STATE_DIR": str(fixture / "ae-state"), "AGENT_MEMORY_ROOT": str(fixture / "memory"),
               "TASK_OBSERVER_WORKSPACE": str(fixture / "observer"), "AE_FFMPEG_ALLOWED_ROOTS": str(project),
               "PYTHONDONTWRITEBYTECODE": "1", **proxies}
        normalize = lambda text: text.replace(str(home), "/fixture/codex-home").replace(str(repo), "/checkout/ae").replace(scratch, "/fixture/run")
        l0_cmd = installed_bootstrap(marker, repo)
        bootstrap, bootstrap_ms, bootstrap_status = command(l0_cmd, env, project)
        if bootstrap_status:
            raise ValueError(f"Installed L0 command exited {bootstrap_status}")
        clip = project / "fixture.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=32x32:d=0.2",
                        "-c:v", "mpeg4", str(clip)], env=env, cwd=project, check=True, timeout=10)
        protocols = [asyncio.run(wire_probe(settings, env, clip, sample=index == 0)) for index in range(repeats)]
        protocol = protocols[0]
        catalog, version_start, status = command(["codex", "mcp", "list", "--json"], env, project)
        native_mcp = status == 0 and any(server["name"] == "agent-enhancements" and server["enabled"] for server in json.loads(catalog))
        cold, cold_ms = run_hook(repo, project, env, "SessionStart")
        seed = ("import sys; sys.path.insert(0, sys.argv[1]); from memory import AgentMemory; "
                "AgentMemory('codex', project=sys.argv[2]).save('fixture-summary', "
                "'Synthetic prior session. Preserve exported types and permit only local tools during fixture verification.')")
        subprocess.run([sys.executable, "-c", seed, str(ui / "scripts"), str(project)],
                        env=env, cwd=project, check=True, timeout=10)
        returning, return_ms = run_hook(repo, project, env, "SessionStart")
        memory_index = returning.index(MEMORY_HEADER)
        channels = {"native_marker": tokens(normalize(marker)), "l0": tokens(normalize(bootstrap)),
                    "observer_cold": tokens(normalize(cold)), "memory_recall": tokens(normalize(returning[memory_index:])),
                    "native_descriptions": tokens(normalize(descriptions)),
                    "tool_schema_eager_projection": tokens(normalize(json.dumps(protocol["schema_projection"], separators=(",", ":"))))}
        registry = [sys.executable, str(ui / "scripts/registry.py")]
        rows = []
        all_hook_ms = []
        for case, prompt, expected in CASES:
            timings = [run_hook(repo, project, env, "UserPromptSubmit", prompt) for _ in range(repeats)]
            context = timings[0][0]
            all_hook_ms.extend(item[1] for item in timings)
            candidates = HOOK_CARD.findall(context)
            search, search_ms, search_status = command([*registry, "search", prompt], env, project)
            search_names = SEARCH_CARD.findall(search)
            matching = next((name for name in [*candidates, *search_names] if name in expected), "")
            details, detail_ms, detail_status = command([*registry, "show", "skill:" + matching], env, project) if matching else ("", 0, 0)
            driver = repo / by_name[matching]["path"] if matching else None
            body = driver.read_bytes() if driver and driver.resolve().is_relative_to(repo) and driver.is_file() else b""
            passed = bool(matching and search_status == detail_status == 0 and body) if expected else not candidates
            if case == "research-permissions":
                passed = passed and not protocol["search_shape_visible_without_key"]
            if case == "local-video":
                passed = passed and protocol["video_width_32"]
            costs = {"prompt_slot": tokens(normalize(context)), "search_page": tokens(normalize(search)),
                     "detail_page": tokens(normalize(details)),
                     "skill_detail_body": tokens(normalize(body.decode("utf-8", errors="replace"))),
                     "local_tool_result": protocol["video_tool_result_proxy"] if case == "local-video" else 0}
            cold_total = sum(value for key, value in channels.items() if key != "memory_recall") + costs["prompt_slot"]
            rows.append({"case": case, "prompt": prompt, "passed": passed, "accepted_skill": matching or None,
                         "hook_rank": (candidates.index(matching) + 1) if matching in candidates else None,
                         "selected_skill_body_bytes": len(body), "hook_candidates": candidates,
                         "reached_via": "hook" if matching in candidates else "search" if matching else None,
                         "cost": costs, "hook_ms": summary([item[1] for item in timings]),
                         "search_cli_ms": round(search_ms, 3), "detail_cli_ms": round(detail_ms, 3),
                         "cold_start_proxy": cold_total, "cold_start_with_prior_note": cold_total + channels["memory_recall"],
                         "fixture_path_total_ae_proxy": cold_total + (costs["search_page"] if matching in search_names and matching not in candidates else 0)
                         + costs["detail_page"] + costs["skill_detail_body"] + costs["local_tool_result"]})
        setup_disk = subprocess.check_output(["du", "-sb", str(repo / ".agentenhancements")], text=True)
    return {"repo_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
            "sources_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (ui / "scripts/registry.py", ui / "scripts/runtime.py", ui / "mcp-servers/gateway.py", ui / "setup.sh")},
            "env": {"python": platform.python_version(), "os": platform.platform(),
                    "codex": subprocess.check_output(["codex", "--version"], text=True).strip()},
            "method": (("tiktoken o200k_base" if ENCODING else "chars/4")
                       + " proxy after normalizing fixture paths. Native descriptions reconstructed. "
                         "Tool schema projection assumes eager exposure. No model endpoint used."),
            "native_skill_descriptions": len(hosts), "native_marker_bytes": len(marker.encode()),
            "l0_bytes": len(bootstrap.encode()), "l0_rendered_only_proxy": tokens(normalize(bootstrap_rendered)),
            "l0_read": l0_cmd[0] if l0_cmd[0] == "cat" else "build-library-map.py --print",
            "l0_cli_ms": round(bootstrap_ms, 3),
            "channels": channels, "stdio_mcp": {**{key: value for key, value in protocol.items() if key != "schema_projection"},
                "tool_count": len(protocol["schema_projection"]), "startup_ms": summary([item["initialize_and_list_ms"] for item in protocols])},
            "codex_native_mcp_list": native_mcp, "codex_mcp_list_cli_ms": round(version_start, 3),
            "session_start_ms": {"cold": round(cold_ms, 3), "with_prior_note": round(return_ms, 3)},
            "prompt_submit_ms": summary(all_hook_ms),
            "checks_passed": sum(row["passed"] for row in rows), "checks_total": len(rows), "rows": rows,
            "prepared_checkout_state_bytes": int(setup_disk.split()[0]),
            "max_child_process_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}


def check_budgets(repo: Path, evidence: dict) -> list[str]:
    """Verify the measured credential-free default profile against the contract."""
    sys.path.insert(0, str(repo / "unified-integration/scripts"))
    import context_budget as limits

    channels = evidence["channels"]
    checks = {
        "L0": (channels["l0"], limits.MAX_BOOTSTRAP),
        "observer": (channels["observer_cold"], limits.MAX_OBSERVER_AMBIENT),
        "returning-session recall": (channels["memory_recall"], limits.MAX_MEMORY_RECALL),
        "native descriptions": (channels["native_descriptions"], limits.MAX_NATIVE_DESCRIPTION_TOTAL),
        "eager schema projection": (channels["tool_schema_eager_projection"], limits.MAX_TOOL_SCHEMA_TOTAL),
        "cold start with one fixture note": (
            max(row["cold_start_with_prior_note"] for row in evidence["rows"]), limits.MAX_COLD_START_TOTAL),
        "search page": (max(row["cost"]["search_page"] for row in evidence["rows"]), limits.MAX_SEARCH_PAGE),
        "detail page": (max(row["cost"]["detail_page"] for row in evidence["rows"]), limits.MAX_DETAIL_PAGE),
    }
    failures = [f"{name} measured {actual} tokens (limit {limit})"
                for name, (actual, limit) in checks.items() if actual > limit]
    stdio = evidence["stdio_mcp"]
    if stdio["search_shape_visible_without_key"] or not (
        stdio["embedding_256"] and stdio["video_width_32"] and evidence["codex_native_mcp_list"]
    ):
        failures.append("Credential-free MCP discovery or local calls failed")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--home", type=Path, required=True, help="Read-only path to generated isolated HOME")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--check", action="store_true",
                        help="fail on a default-profile budget or MCP check failure")
    args = parser.parse_args()
    if args.check and ENCODING is None:
        parser.error("--check requires the tiktoken o200k_base benchmark encoder")
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    repo = args.repo.resolve()
    evidence = collect(repo, args.home.resolve(), args.repeats)
    if args.check:
        evidence["budget_failures"] = check_budgets(repo, evidence)
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if args.check and evidence["budget_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
