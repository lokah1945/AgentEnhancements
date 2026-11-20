#!/usr/bin/env python3
"""Offline discovery benchmark against a checkout, with an isolated HOME.

Run against an unchanged checkout before changing ranking, then the same fixture
against the working tree. Quality measures acceptable-ID hits in the *skills*
section of the actual registry map, the loader, and rendered prompt-hook cards.
Unavailable MCP fixtures separately measure filtering and readiness, not skill
selection. This measures discovery suggestions, never model task completion.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stdout
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterator


FIXTURE = Path(__file__).with_name("fixtures") / "discovery-prompts.json"
CARD = re.compile(r"^- ([^:\n]+): (.*)$", re.MULTILINE)


def import_file(name: str, path: Path) -> Any:
    """Import the production module from the checkout being measured."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@contextmanager
def isolated_environment(repo: Path) -> Iterator[dict[str, str]]:
    """Make every runtime/config/state path disposable, without provider keys."""
    with tempfile.TemporaryDirectory(prefix="ae-discovery-home-") as directory:
        root = Path(directory)
        config = root / "config"
        config.mkdir()
        api_file = root / "ui.api.json"
        api_file.write_text(json.dumps({
            "version": 2, "api_keys": {}, "connections": {}, "mcp": {},
            "preflight": {"mode": 0},
        }), encoding="utf-8")
        overrides = {
            "HOME": str(root), "AGENT_MEMORY_ROOT": str(root / "memory"),
            "AGENT_ENHANCEMENTS_STATE_DIR": str(root / 'ae-state'),
            "XDG_CONFIG_HOME": str(config), "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_DATA_HOME": str(root / "data"), "XDG_STATE_HOME": str(root / "state"),
            "CODEX_HOME": str(root / "codex"),
            "CLAUDE_CONFIG_DIR": str(root / "claude"),
            "HERMES_HOME": str(root / "hermes"),
            "AGENT_ENHANCEMENTS_BASE_DIR": str(repo),
            "AGENT_SKILLS_DIR": str(repo / "unified-integration/skills"),
            "AGENT_ENHANCEMENTS_API_FILE": str(api_file),
            "AGENT_SKILLS_NATIVE_TARGETS": str(root / "native-skills"),
            "AE_MAX_SKILL_CARDS": "8", "PYTHONDONTWRITEBYTECODE": "1",
        }
        previous = {key: os.environ.get(key) for key in overrides}
        os.environ.update(overrides)
        try:
            yield dict(os.environ)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def percentiles(values: list[float]) -> dict[str, float]:
    """Report median and nearest-rank p95 without hiding warm/cold samples."""
    if not values:
        return {"p50": 0, "p95": 0, "max": 0}
    ordered = sorted(values)
    return {"p50": round(statistics.median(values), 3),
            "p95": round(ordered[math.ceil(len(ordered) * .95) - 1], 3),
            "max": round(ordered[-1], 3)}


def quality(rows: list[dict], surface: str) -> dict:
    """Use fixed acceptable sets; ambiguous cases are reported separately."""
    result = {}
    for group, selected in (
        ("all", [r for r in rows if r["acceptable_ids"]]),
        ("positive", [r for r in rows if r["kind"] == "positive"]),
        ("ambiguous", [r for r in rows if r["kind"] == "ambiguous"]),
        ("en", [r for r in rows if r["acceptable_ids"] and r["language"] == "en"]),
        ("id", [r for r in rows if r["acceptable_ids"] and r["language"] == "id"]),
    ):
        hits = {k: sum(bool(set(r[surface][:k]) & set(r["acceptable_ids"]))
                       for r in selected) for k in (1, 3)}
        result[group] = {"n": len(selected), "top1_hits": hits[1],
                         "top3_hits": hits[3]}
    negatives = [r for r in rows if r["kind"] == "negative"]
    result["negative"] = {"n": len(negatives),
                          "abstained": sum(not r[surface] for r in negatives)}
    return result


def benchmark(repo: Path, fixture: Path = FIXTURE) -> dict:
    """Exercise production map, loader and prompt-submit entry points offline."""
    repo = repo.resolve()
    document = json.loads(fixture.read_text(encoding="utf-8"))
    scripts = repo / "unified-integration/scripts"
    watched = ("registry.py", "load-skills.py", "runtime.py", "context_budget.py")
    source_hashes = {name: hashlib.sha256((scripts / name).read_bytes()).hexdigest()
                     for name in watched}
    sys.path.insert(0, str(scripts))
    with isolated_environment(repo) as environment:
        registry = import_file("discovery_registry", scripts / "registry.py")
        loader_module = import_file("discovery_loader", scripts / "load-skills.py")
        budget = import_file("discovery_budget", scripts / "context_budget.py")
        loader = loader_module.SkillsLoader("codex")
        known = {entry["id"] for entry in registry.load_all_entries()}
        rows = []
        for case in document["cases"]:
            missing = set(case["acceptable_ids"]) - known
            if case.get("unavailable_id") and case["unavailable_id"] not in known:
                missing.add(case["unavailable_id"])
            if missing:
                raise ValueError(f"Unknown expected IDs in {case['id']}: {sorted(missing)}")
            row = dict(case)
            prompt = case["prompt"]
            started = time.perf_counter()
            stream = io.StringIO()
            with redirect_stdout(stream):
                registry.cmd_map(prompt, as_json=True)
            row["registry_ms"] = (time.perf_counter() - started) * 1000
            map_text = stream.getvalue()
            row["registry_tokens"] = budget.approx_tokens(map_text)
            try:
                plan = json.loads(map_text)
                row["registry_map"] = [card["id"] for card in plan["skills"]]
                cards = [card for key in ("skills", "plugins", "mcp_servers")
                         for card in plan[key]]
                row["registry_complete_cards"] = sum(all(card.get(k) for k in
                    ("id", "type", "summary", "ready", "detail", "why")) for card in cards)
                row["registry_cards"] = len(cards)
                row["registry_parse_error"] = False
            except json.JSONDecodeError:
                plan = {}
                row.update(registry_map=[], registry_complete_cards=0,
                           registry_cards=0, registry_parse_error=True)
            started = time.perf_counter()
            matches = loader.find_skills(prompt, max_results=8)
            row["loader_ms"] = (time.perf_counter() - started) * 1000
            row["loader"] = ["skill:" + item["name"] for item in matches]
            event = {"hook_event_name": "UserPromptSubmit", "prompt": prompt,
                     "cwd": str(repo), "session_id": "discovery-" + case["id"]}
            started = time.perf_counter()
            process = subprocess.run(
                [sys.executable, str(scripts / "runtime.py"), "codex"],
                input=json.dumps(event), capture_output=True, text=True,
                env=environment, cwd=repo, timeout=20,
            )
            row["hook_ms"] = (time.perf_counter() - started) * 1000
            if process.returncode or process.stderr:
                raise RuntimeError(f"Hook failed for {case['id']}: {process.stderr[:200]}")
            payload = json.loads(process.stdout) if process.stdout.strip() else {}
            context = payload.get("hookSpecificOutput", {}).get("additionalContext", "")
            rendered = CARD.findall(context)
            row["hook"] = ["skill:" + name for name, _ in rendered]
            row["hook_tokens"] = budget.approx_tokens(context)
            row["hook_cards"] = len(rendered)
            summaries = {item["name"]: (item.get("description") or "").strip().split("\n")[0][:100]
                         for item in matches}
            row["hook_complete_summaries"] = sum(
                bool(summary) and summaries.get(name) == summary for name, summary in rendered)
            row["hook_detail_pointers"] = sum(
                bool(re.search(r"registry\.py show\s+\S+|\S+/SKILL\.md", line)) for line in context.splitlines()
                if line.startswith("- "))
            row["hook_readiness_labels"] = sum(
                bool(re.search(r"\bready\s*[:=]|\[(?:direct_read|loaded|callable)\]", line))
                for line in context.splitlines() if line.startswith("- "))
            if case.get("unavailable_id"):
                target = registry.find_entry(case["unavailable_id"])
                readiness = registry.entry_readiness(target) if target else {}
                row["unavailable_ready"] = readiness.get("ready", "missing")
                row["unavailable_blocker"] = readiness.get("blocker", "")
                row["unavailable_advertised"] = any(
                    card["id"] == case["unavailable_id"] for card in plan.get("mcp_servers", []))
            rows.append(row)
        tokenizer = "o200k_base" if importlib.util.find_spec("tiktoken") else "documented chars/4 fallback"
    return {
        "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "source_sha256": source_hashes,
        "source_changed_during_run": any(
            hashlib.sha256((scripts / name).read_bytes()).hexdigest() != source_hashes[name]
            for name in watched),
        "method": document["method"], "repo": str(repo), "cases": len(rows),
        "token_measurement": tokenizer,
        "quality": {surface: quality(rows, surface)
                    for surface in ("registry_map", "loader", "hook")},
        "latency_ms": {surface: percentiles([row[surface + "_ms"] for row in rows])
                       for surface in ("registry", "loader", "hook")},
        "tokens": {surface: percentiles([row[surface + "_tokens"] for row in rows])
                   for surface in ("registry", "hook")},
        "registry_invalid_json": sum(row["registry_parse_error"] for row in rows),
        "cards": {field: sum(row[field] for row in rows) for field in
                  ("registry_cards", "registry_complete_cards", "hook_cards",
                   "hook_complete_summaries", "hook_detail_pointers", "hook_readiness_labels")},
        "unavailable_mcp": {"n": sum(row["kind"] == "unavailable_mcp" for row in rows),
                            "advertised": sum(row.get("unavailable_advertised", False) for row in rows),
                            "ready": sum(row.get("unavailable_ready") == "yes" for row in rows)},
        "rows": rows,
    }


def main() -> None:
    """Write full reproducible results; print the compact summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true",
                        help="enforce the frozen corpus quality and availability gates")
    args = parser.parse_args()
    result = benchmark(args.repo, args.fixture)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    if args.check:
        failures = []
        for surface, measured in result["quality"].items():
            quality = measured["all"]
            if quality["n"] != 40 or quality["top1_hits"] < 25 or quality["top3_hits"] < 30:
                failures.append(f"{surface}: expected >=25/40 top-1 and >=30/40 top-3")
            negative = measured["negative"]
            if negative["n"] != 6 or negative["abstained"] != 6:
                failures.append(f"{surface}: ordinary-tool prompts must abstain")
        if result["source_changed_during_run"] or result["registry_invalid_json"]:
            failures.append("benchmark source changed or registry emitted invalid JSON")
        if result["unavailable_mcp"] != {"n": 4, "advertised": 0, "ready": 0}:
            failures.append("unavailable MCP must not be advertised callable")
        if result["tokens"]["hook"]["max"] > 400:
            failures.append("prompt-hook context exceeds 400 tokens")
        if failures:
            print("\n".join(failures), file=sys.stderr)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
