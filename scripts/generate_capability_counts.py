#!/usr/bin/env python3
"""Derive public capability counts from canonical data without loading runtime state.

Run --write after source/index updates, then --check in CI. Only marked blocks
and the generated JSON are written; dated audit and benchmark evidence stays
unchanged. Python constants are parsed as literals, never imported/executed.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
import textwrap
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SUMMARY_PATHS = ("README.md", "README_INTEGRATION.md")
INVENTORY_PATH = "docs/CAPABILITY_COUNTS.md"
JSON_PATH = "docs/capability-counts.json"
DESCRIPTION_PATH = "docs/repository-description.txt"


def literal(path: Path, name: str) -> Any:
    """Read a named constant from source without importing its module."""
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            value = node.value
            if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                    and value.func.id == "frozenset" and len(value.args) == 1):
                value = value.args[0]
            return ast.literal_eval(value)
    raise ValueError(f"{path.name}: missing literal {name}")


def read_json(root: Path, name: str) -> dict[str, Any]:
    """Read one canonical JSON object; malformed inputs fail the check."""
    return json.loads((root / name).read_text(encoding="utf-8"))


def inventory(root: Path) -> dict[str, Any]:
    """Count distinct surfaces, keeping implementation and runtime concepts apart."""
    index = read_json(root, "unified-integration/skills/all-skills.json")
    skills = index["skills"]
    names = [entry["name"] for entry in skills]
    if len(set(names)) != len(names) or index["total_skills"] != len(skills):
        raise ValueError("all-skills.json: duplicate names or inconsistent total_skills")
    by_source = Counter(entry["source"] for entry in skills)
    if set(index["sources"]) != set(by_source):
        raise ValueError("all-skills.json: sources disagree with indexed records")
    source_paths: dict[str, set[Path]] = defaultdict(set)
    for entry in skills:
        path = Path(entry["source_path"])
        if path.is_absolute() or ".." in path.parts or not (root / path).is_file():
            raise ValueError(f"invalid or absent source_path for {entry['name']}")
        if not (root / path).resolve().is_relative_to(root.resolve()):
            raise ValueError(f"source_path escapes repository for {entry['name']}")
        source_paths[entry["source"]].add(path)
    raw: dict[str, int] = {}
    for source, paths in source_paths.items():
        vendor_roots = {path.parts[0] for path in paths}
        if len(vendor_roots) != 1:
            raise ValueError(f"source {source}: multiple vendor roots")
        # Index source_path depth records the aggregation layout. Exclude nested
        # helper/meta-skill documents that setup does not aggregate individually.
        depths = {len(path.parts) for path in paths}
        source_root = root / next(iter(vendor_roots))
        raw[source] = sum(
            1 for depth in depths
            for path in source_root.glob("/".join(["*"] * (depth - 2) + ["SKILL.md"]))
            if path.is_file()
        )
    catalog = read_json(root, "plugin-catalog/catalog.json")
    plugins = catalog["skills"]
    if catalog["total_plugins"] != len(plugins):
        raise ValueError("catalog.json: inconsistent total_plugins")
    servers = read_json(root, "plugin-catalog/mcp-servers.json")["servers"]
    server_ids = [server["id"] for server in servers]
    if len(server_ids) != len(set(server_ids)):
        raise ValueError("mcp-servers.json: duplicate server IDs")
    scripts = root / "unified-integration/scripts"
    capabilities = literal(scripts / "registry.py", "BUILT_IN_CAPABILITIES")
    native_sources = set(literal(scripts / "registry.py", "DEFAULT_NATIVE_SOURCES"))
    bundled = set(literal(scripts / "api_config.py", "BUILTINS"))
    disabled = set(literal(scripts / "api_config.py", "DEFAULT_DISABLED"))
    link_source = (scripts / "link-skills.sh").read_text(encoding="utf-8")
    sets = {}
    for name in ("DEFAULT_SOURCES", "CURATED_SOURCES"):
        match = re.search(rf'^{name}="([^"\n]*)"$', link_source, flags=re.M)
        if not match:
            raise ValueError(f"link-skills.sh: missing literal {name}")
        sets[name] = set(match[1].split())
    if native_sources != sets["DEFAULT_SOURCES"]:
        raise ValueError("native default sources disagree between registry.py and link-skills.sh")
    if not bundled <= set(server_ids) or not disabled <= bundled:
        raise ValueError("bundled backend/default-disabled IDs disagree with MCP catalog")
    vendor_directories = re.findall(r"^\| ([\w.-]+)/ \|", (root / "LICENSE").read_text(), re.M)
    by_status = Counter(server["status"] for server in servers)
    return {
        "skills": {"total": len(skills), "sources": len(by_source),
                   "raw_records": sum(raw.values()),
                   "collapsed_records": sum(raw.values()) - len(skills),
                   "by_source": dict(sorted(by_source.items())), "raw_by_source": dict(sorted(raw.items()))},
        "plugins": {"total": len(plugins),
                    "unique_upstreams": len({entry["source_url"].removesuffix("/").removesuffix(".git").lower()
                                             for entry in plugins}),
                    "by_category": dict(sorted(Counter(entry["category"] for entry in plugins).items())),
                    "by_status": dict(sorted(Counter(entry["status"] for entry in plugins).items())),
                    "vendored_entries": sum(bool(entry.get("vendored")) for entry in plugins)},
        "mcp": {"total": len(servers), "by_status": dict(sorted(by_status.items())),
                "by_priority": dict(sorted(Counter(entry["priority"] for entry in servers).items())),
                "bundled_backends": len(bundled), "default_enabled_backends": len(bundled - disabled),
                "default_disabled": sorted(disabled),
                "external_built": sorted(entry["id"] for entry in servers
                                         if entry["status"] == "built" and entry["id"] not in bundled)},
        "built_in_capabilities": len(capabilities),
        "registry_entries": len(skills) + len(plugins) + len(servers) + len(capabilities),
        "native": {"default_sources": sorted(native_sources),
                   "default_skills": sum(by_source[source] for source in native_sources),
                   "curated_sources": sorted(sets["CURATED_SOURCES"]),
                   "curated_skills": sum(by_source[source] for source in sets["CURATED_SOURCES"])},
        "vendored_projects": len(vendor_directories),
    }


def summary(data: dict[str, Any]) -> str:
    """Render the common concise counts shown by both READMEs."""
    skills, plugins, mcp, native = (data[name] for name in ("skills", "plugins", "mcp", "native"))
    statuses = ", ".join(f"`{name}`: {count}" for name, count in plugins["by_status"].items())
    mcp_statuses = ", ".join(f"`{name}`: {count}" for name, count in mcp["by_status"].items())
    lines = [
        f"- **{skills['total']:,} specialized skills/agents** from **{skills['sources']} skill sources**; "
        f"{skills['raw_records']:,} source records before name collisions are resolved.",
        f"- **{plugins['total']} catalog plugins** from **{plugins['unique_upstreams']} unique upstream repositories** "
        f"({statuses}); {plugins['vendored_entries']} entries have vendored source.",
        f"- **{mcp['total']} MCP servers** ({mcp_statuses}); **{mcp['bundled_backends']} bundled Python backends**, "
        f"{mcp['default_enabled_backends']} enabled by default before host configuration.",
        f"- **{data['built_in_capabilities']} built-in capabilities**; "
        f"**{native['default_skills']} default native skills**; "
        f"{native['curated_skills']} skills in the optional curated set.",
        f"- **{data['registry_entries']:,} registry entries** in total; "
        f"**{data['vendored_projects']} vendored projects** listed in the root license notice.",
    ]
    return "\n".join(textwrap.fill(line, width=78, subsequent_indent="  ",
                                   break_long_words=False, break_on_hyphens=False) for line in lines)


def repository_description(data: dict[str, Any]) -> str:
    """Canonical public GitHub description, derived from the same inventory."""
    return (
        f"Automatic capability integration for AI agents: {data['skills']['total']:,} skills, "
        f"{data['plugins']['total']} plugins and {data['mcp']['total']} MCP catalog entries; "
        "shared memory and context utilities."
    )


def full_inventory(data: dict[str, Any]) -> str:
    """Render the detailed generated source and status tables."""
    lines = [summary(data), "", "## Skill records by source", "",
             "| Source | Raw records | Unique indexed skills |", "| --- | ---: | ---: |"]
    for source, count in data["skills"]["by_source"].items():
        lines.append(f"| {source} | {data['skills']['raw_by_source'][source]:,} | {count:,} |")
    lines += ["", f"Name collisions collapse {data['skills']['collapsed_records']} records. "
              "The index keeps one winner per skill name; raw records are not additional usable skills.",
              "", "## Plugin implementation status", "", "| Status | Entries |", "| --- | ---: |"]
    lines += [f"| {status} | {count} |" for status, count in data["plugins"]["by_status"].items()]
    lines += ["", "## Plugin categories", "", "| Category | Entries |", "| --- | ---: |"]
    lines += [f"| {category} | {count} |" for category, count in data["plugins"]["by_category"].items()]
    lines += ["", "## MCP implementation status", "", "| Status | Entries |", "| --- | ---: |"]
    lines += [f"| {status} | {count} |" for status, count in data["mcp"]["by_status"].items()]
    lines += ["", "## MCP priorities", "", "| Priority | Entries |", "| --- | ---: |"]
    lines += [f"| {priority} | {count} |" for priority, count in data["mcp"]["by_priority"].items()]
    external = ", ".join(f"`{name}`" for name in data["mcp"]["external_built"]) or "none"
    disabled = ", ".join(f"`{name}`" for name in data["mcp"]["default_disabled"]) or "none"
    lines += ["", f"Built catalog entries outside the bundled Python backend set: {external}.",
              f"Bundled backends requiring explicit opt-in: {disabled}.", "",
              "Implementation status does not certify runtime readiness. An external built entry still needs "
              "its executable/configuration; enabled bundled servers still need a prepared runtime. "
              "Host permissions, credentials and connectivity are checked separately."]
    return "\n".join(line if line.startswith("|") or "\n" in line else
                     textwrap.fill(line, width=78, break_long_words=False, break_on_hyphens=False)
                     for line in lines)


def replace_block(text: str, kind: str, body: str) -> str:
    """Replace exactly one marked region, refusing missing or ambiguous markers."""
    begin, end = f"<!-- ae:counts:{kind}:begin -->", f"<!-- ae:counts:{kind}:end -->"
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) >= text.index(end):
        raise ValueError(f"missing or ambiguous {kind} generated block")
    start, stop = text.index(begin) + len(begin), text.index(end)
    return text[:start] + "\n\n" + body + "\n\n" + text[stop:]


def current_claim_errors(root: Path, data: dict[str, Any]) -> list[str]:
    """Check common current prose totals; dated audit/plan evidence is excluded."""
    errors = []
    patterns = [
        (r"(\d[\d,]*) (?:unique skills|specialized skills/agents|skills total)", data["skills"]["total"]),
        (r"(\d[\d,]*)[ -]skill catalog", data["skills"]["total"]),
        (r"(\d[\d,]*) (?:candidate MCP servers|MCP servers|MCP entries|MCP roadmap servers)", data["mcp"]["total"]),
        (r"(\d[\d,]*) (?:catalog plugins|cataloged plugins|curated external plugin (?:entries|sources))", data["plugins"]["total"]),
        (r"(\d[\d,]*) (?:built-in capabilities|built-in capability entries)", data["built_in_capabilities"]),
        (r"(\d[\d,]*) (?:skill sources)", data["skills"]["sources"]),
    ]
    paths = [root / name for name in SUMMARY_PATHS] + sorted((root / "docs").glob("*.md"))
    for path in paths:
        if path.name in ("CHANGELOG.md", "ADR.md") or path.as_posix().endswith(INVENTORY_PATH):
            continue
        text = re.sub(r"<!-- ae:counts:\w+:begin -->.*?<!-- ae:counts:\w+:end -->", "", path.read_text(), flags=re.S)
        for number, line in enumerate(text.splitlines(), 1):
            plain = re.sub(r"[*`]", "", line)
            for pattern, expected in patterns:
                for match in re.finditer(pattern, plain, flags=re.I):
                    if int(match[1].replace(",", "")) != expected:
                        errors.append(f"{path.relative_to(root)}:{number}: count claim differs from canonical {expected}")
            if re.search(r"\b\d+ integration tests\b|\b\d+ tests \(\d+ regression modules\)", plain):
                errors.append(f"{path.relative_to(root)}:{number}: use verification evidence instead of a permanent test-count claim")
    return errors


def main() -> int:
    """Print inventory, regenerate docs, or fail CI on stale generated counts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--json", action="store_true")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--description", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        data = inventory(root)
        serialized = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if args.json:
            print(serialized, end="")
            return 0
        if args.description:
            print(repository_description(data))
            return 0
        expected = {JSON_PATH: serialized,
                    DESCRIPTION_PATH: repository_description(data) + "\n"}
        for name in SUMMARY_PATHS + (INVENTORY_PATH,):
            path = root / name
            kind = "inventory" if name == INVENTORY_PATH else "summary"
            expected[name] = replace_block(path.read_text(), kind,
                                           full_inventory(data) if kind == "inventory" else summary(data))
        errors = []
        for name, content in expected.items():
            path = root / name
            if path.exists() and path.read_text() == content:
                continue
            if args.write:
                path.write_text(content, encoding="utf-8")
            else:
                errors.append(f"{name}: generated counts drifted; run scripts/generate_capability_counts.py --write")
        if args.check:
            errors.extend(current_claim_errors(root, data))
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print("Capability counts regenerated." if args.write else "Capability counts match canonical inputs.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as error:
        print(f"Capability count check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
