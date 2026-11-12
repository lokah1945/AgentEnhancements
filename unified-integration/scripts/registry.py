#!/usr/bin/env python3
"""Unified capability registry for AgentEnhancements.

Builds and queries ONE mapping across everything the project ships:

  - skills       (the aggregated unified index, all sources)
  - plugins      (the curated external plugin catalog)
  - mcp          (the MCP server roadmap)
  - capability   (built-ins: memory, compression, dispatch, launcher, linking)

After a single install, any agent can map a natural-language task to the
exact skills, plugins and MCP servers it needs through this tool - no
per-component installation or discovery required.

Usage:
  python3 registry.py build [--out PATH] [--quiet]
  python3 registry.py search "<query>" [--type skill|plugin|mcp|capability]
                                         [--limit N] [--json]
  python3 registry.py map "<task description>" [--limit N] [--json]
  python3 registry.py show <name-or-id> [--json]
  python3 registry.py stats [--json]
  python3 registry.py list [--type T] [--source S] [--json]

The generated registry is committed at
unified-integration/skills/agent-registry.json and rebuilt by setup.sh.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
UNIFIED_DIR = SCRIPT_DIR.parent
REPO_ROOT = UNIFIED_DIR.parent

SKILLS_INDEX = UNIFIED_DIR / "skills" / "all-skills.json"
REGISTRY_OUT = UNIFIED_DIR / "skills" / "agent-registry.json"
CATALOG_JSON = REPO_ROOT / "plugin-catalog" / "catalog.json"
MCP_JSON = REPO_ROOT / "plugin-catalog" / "mcp-servers.json"

# Common English/Indonesian function words that pollute keyword scoring.
STOP_WORDS = frozenset("""
a an the and or but if then for with without from this that these those of
to in on at by as is are was were be been being it its i me my we you your
he she they them do does did have has had will would can could should shall
may might must not no yes into over under about after before when where
which who whom what how why all any some more most other such only own same
so than too very just also please want wants need needs
yang dan atau dari untuk ini itu dengan agar saat ketika
tolong buatkan saya kamu kita
""".split())

# Format-family aliases: queries name the format colloquially ("make a word
# document"), while skills are named after the extension (docx). Mapping the
# colloquial token onto the canonical one makes the official document skills
# rank where they should. Keep this list small and unambiguous.
FORMAT_ALIASES = {
    "word": "docx",
    "excel": "xlsx",
    "spreadsheet": "xlsx",
    "workbook": "xlsx",
    "powerpoint": "pptx",
    "slides": "pptx",
    "deck": "pptx",
    "slide": "pptx",
}

# Sources that link-skills.sh activates natively by default. Keep in sync
# with DEFAULT_SOURCES in link-skills.sh.
DEFAULT_NATIVE_SOURCES = ("anthropic-skills", "replica-skill")

BUILT_IN_CAPABILITIES = [
    {
        "id": "capability:memory",
        "type": "capability",
        "name": "memory",
        "description": "Persistent cross-session memory backed by SQLite "
                       "(parameterized queries). Save, load and list memories "
                       "for any agent.",
        "keywords": ["memory", "remember", "preference", "recall", "persist",
                     "session", "context"],
        "usage": 'python3 {unified}/scripts/memory.py <agent> save|load|list ["key" ["value"]]',
        "automatic": "Claude Code (hooks in ~/.claude/settings.json)",
    },
    {
        "id": "capability:compression",
        "type": "capability",
        "name": "compression",
        "description": "Context compression for long transcripts (headroom "
                       "binary or pure-Python fallback).",
        "keywords": ["compress", "token", "budget", "context", "long",
                     "transcript", "summarize"],
        "usage": "{unified}/compression/compress.sh <file> <auto|code|logs|json|markdown|generic>",
        "automatic": "none (invoke explicitly)",
    },
    {
        "id": "capability:skills-loader",
        "type": "capability",
        "name": "skills-loader",
        "description": "Keyword search over the full skills index and on-demand "
                       "loading of any SKILL.md.",
        "keywords": ["find", "search", "skill", "load", "catalog", "match"],
        "usage": 'python3 {unified}/scripts/load-skills.py <agent> "<task description>"',
        "automatic": "referenced from every agent instruction file",
    },
    {
        "id": "capability:dispatcher",
        "type": "capability",
        "name": "dispatch",
        "description": "Natural-language routing to a catalog plugin or "
                       "orchestrator tier (docs/ROUTER_POLICY.md).",
        "keywords": ["route", "dispatch", "orchestrate", "choose", "plan"],
        "usage": 'bash {unified}/scripts/dispatch.sh --dry-run "<task>"',
        "automatic": "none (invoke explicitly)",
    },
    {
        "id": "capability:native-linking",
        "type": "capability",
        "name": "link-skills",
        "description": "Symlink registry skills into ~/.claude/skills/ and "
                       "~/.agents/skills/ so Agent Skills compatible harnesses "
                       "discover them automatically at runtime.",
        "keywords": ["link", "activate", "native", "symlink", "discover",
                     "auto", "install"],
        "usage": "bash {unified}/scripts/link-skills.sh [--set <source>|all|<name>] [--status] [--unlink]",
        "automatic": "default curated set linked by setup.sh",
    },
    {
        "id": "capability:launcher",
        "type": "capability",
        "name": "launch-agent",
        "description": "Launch any detected agent with the enhancement "
                       "environment (memory init, standard env vars).",
        "keywords": ["launch", "start", "run", "agent", "cli"],
        "usage": "{unified}/launch-agent.sh <agent> [args...]",
        "automatic": "agent-enhanced <agent> when /usr/local/bin is writable",
    },
    {
        "id": "capability:registry",
        "type": "capability",
        "name": "registry",
        "description": "This tool: map a task to skills, plugins, MCP servers "
                       "and built-in capabilities in one query.",
        "keywords": ["map", "mapping", "registry", "index", "capability",
                     "what", "which"],
        "usage": 'python3 {unified}/scripts/registry.py map "<task description>"',
        "automatic": "referenced from every agent instruction file",
    },
]


def _tokenize(text: str) -> List[str]:
    """Lowercase word tokens for scoring, minus stop words."""
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if t not in STOP_WORDS]


def _read_json(path: Path, default: Any) -> Any:
    """Read a JSON file, returning default when missing or invalid."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def load_skill_entries() -> List[Dict[str, Any]]:
    """Skill entries derived from the unified skills index."""
    index = _read_json(SKILLS_INDEX, {})
    entries: List[Dict[str, Any]] = []
    for skill in index.get("skills", []):
        name = skill.get("name") or ""
        if not name:
            continue
        source = skill.get("source") or ""
        entries.append({
            "id": f"skill:{name}",
            "type": "skill",
            "name": name,
            "source": source,
            "category": skill.get("category", "general"),
            "description": skill.get("description", ""),
            "tags": skill.get("tags", []),
            "path": skill.get("path", ""),
            "source_path": skill.get("source_path", ""),
            "natively_linked_by_default": source in DEFAULT_NATIVE_SOURCES,
            "activation": (
                "natively linked into ~/.claude/skills and ~/.agents/skills "
                "by setup.sh / link-skills.sh"
                if source in DEFAULT_NATIVE_SOURCES
                else "on-demand via the skills loader"
            ),
        })
    return entries


def load_plugin_entries() -> List[Dict[str, Any]]:
    """Plugin entries derived from the curated plugin catalog."""
    catalog = _read_json(CATALOG_JSON, {})
    entries: List[Dict[str, Any]] = []
    for plugin in catalog.get("skills", []):
        name = plugin.get("name") or plugin.get("slug") or ""
        if not name:
            continue
        entries.append({
            "id": f"plugin:{plugin.get('slug', name)}",
            "type": "plugin",
            "name": name,
            "slug": plugin.get("slug", ""),
            "source": "plugin-catalog",
            "category": plugin.get("category", ""),
            "status": plugin.get("status", ""),
            "description": ", ".join(plugin.get("trigger_keywords", [])),
            "trigger_keywords": plugin.get("trigger_keywords", []),
            "best_for": plugin.get("best_for", []),
            "path": plugin.get("guide_path", ""),
            "source_url": plugin.get("source_url", ""),
            "vendored": plugin.get("vendored", False),
            "mcp_servers": plugin.get("mcp_servers", []),
            "activation": "load the SKILL.md integration guide on demand",
        })
    return entries


def load_mcp_entries() -> List[Dict[str, Any]]:
    """MCP server entries derived from the roadmap file."""
    roadmap = _read_json(MCP_JSON, {})
    entries: List[Dict[str, Any]] = []
    for server in roadmap.get("servers", []):
        sid = server.get("id") or ""
        if not sid:
            continue
        entries.append({
            "id": f"mcp:{sid}",
            "type": "mcp",
            "name": sid,
            "source": "plugin-catalog/mcp-servers.json",
            "priority": server.get("priority", ""),
            "category": server.get("category", ""),
            "description": server.get("purpose", ""),
            "command": " ".join([server.get("command", "")] + server.get("args", [])),
            "env_required": server.get("env_required", []),
            "for_plugins": server.get("for_plugins", []),
            "status": server.get("status", "roadmap"),
            "path": "plugin-catalog/mcp-servers.json",
            "activation": "add to the tool's MCP config (e.g. .claude/mcp.json), then mcp-test.sh",
        })
    return entries


def load_capability_entries() -> List[Dict[str, Any]]:
    """Built-in capability entries (static descriptors)."""
    entries = []
    for cap in BUILT_IN_CAPABILITIES:
        entry = dict(cap)
        entry["usage"] = entry["usage"].format(unified=str(UNIFIED_DIR))
        entries.append(entry)
    return entries


def load_all_entries() -> List[Dict[str, Any]]:
    """Every registry entry, skills first (primary surface)."""
    return (
        load_skill_entries()
        + load_plugin_entries()
        + load_mcp_entries()
        + load_capability_entries()
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_skill(entry: Dict[str, Any], tokens: List[str]) -> int:
    score = 0
    name = (entry.get("name") or "").lower()
    desc_tokens = set(_tokenize(entry.get("description", "")))
    tags = {t.lower() for t in entry.get("tags", [])}
    name_matched = False
    for token in tokens:
        alias_target = FORMAT_ALIASES.get(token)
        if not name_matched and (token == name or
                                 (alias_target and alias_target == name)):
            score += 8
            name_matched = True
        elif not name_matched and name.startswith(token):
            score += 4
        elif not name_matched and token in name:
            score += 3
        if token in tags:
            score += 2
        if token in desc_tokens:
            score += 1
        if alias_target and alias_target in desc_tokens:
            score += 1
    # Natively linked skills are already active in every harness: prefer
    # the zero-friction capability when relevance is otherwise equal.
    if entry.get("natively_linked_by_default"):
        score += 3
    return score


def score_plugin(entry: Dict[str, Any], tokens: List[str], query_lower: str) -> int:
    score = 0
    name = (entry.get("name") or "").lower()
    for kw in entry.get("trigger_keywords", []):
        kw_lower = kw.lower()
        if kw_lower and (kw_lower in query_lower or kw_lower in name):
            score += 6
    fields = set(_tokenize(entry.get("description", "")))
    for phrase in entry.get("best_for", []):
        if isinstance(phrase, str):
            fields.update(_tokenize(phrase))
    for token in tokens:
        if token in name:
            score += 3
        if token in fields:
            score += 1
    return score


def score_mcp(entry: Dict[str, Any], tokens: List[str]) -> int:
    score = 0
    name = (entry.get("name") or "").lower()
    fields = set(_tokenize(entry.get("description", "")))
    fields |= set(_tokenize(entry.get("category", "")))
    fields |= set(_tokenize(" ".join(entry.get("for_plugins", []))))
    for token in tokens:
        if token in name:
            score += 4
        if token in fields:
            score += 2
    if entry.get("priority") == "P0":
        score += 1
    return score


def score_capability(entry: Dict[str, Any], tokens: List[str]) -> int:
    score = 0
    name = (entry.get("name") or "").lower()
    fields = set(_tokenize(entry.get("description", "")))
    fields |= {k.lower() for k in entry.get("keywords", [])}
    for token in tokens:
        if token in name:
            score += 5
        if token in fields:
            score += 2
    return score


def rank_entries(entries: List[Dict[str, Any]], query: str,
                 limit: int = 8) -> List[Tuple[int, Dict[str, Any]]]:
    """Score and rank entries against a natural-language query."""
    tokens = _tokenize(query)
    query_lower = (query or "").lower()
    if not tokens:
        return []
    scored = []
    for entry in entries:
        if entry["type"] == "skill":
            score = score_skill(entry, tokens)
        elif entry["type"] == "plugin":
            score = score_plugin(entry, tokens, query_lower)
        elif entry["type"] == "mcp":
            score = score_mcp(entry, tokens)
        else:
            score = score_capability(entry, tokens)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda pair: (-pair[0], pair[1].get("name", "")))
    return scored[:limit]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_build(out_path: Optional[str] = None, quiet: bool = False) -> int:
    """Build agent-registry.json from the index, catalog and MCP roadmap."""
    entries = load_all_entries()
    by_type: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    for entry in entries:
        by_type[entry["type"]] = by_type.get(entry["type"], 0) + 1
        src = entry.get("source") or "built-in"
        by_source[src] = by_source.get(src, 0) + 1
    registry = {
        "version": "1.0",
        "description": "Unified capability registry: skills, plugins, MCP "
                       "servers and built-in capabilities in one index.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total": len(entries),
            "by_type": by_type,
            "by_source": by_source,
        },
        "default_native_sources": list(DEFAULT_NATIVE_SOURCES),
        "entries": entries,
    }
    target = Path(out_path) if out_path else REGISTRY_OUT
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    if not quiet:
        print(f"Registry built: {len(entries)} entries -> {target}")
        print(f"  skills={by_type.get('skill', 0)} plugins={by_type.get('plugin', 0)} "
              f"mcp={by_type.get('mcp', 0)} capabilities={by_type.get('capability', 0)}")
    return 0


def _format_entry(entry: Dict[str, Any], score: Optional[int] = None) -> str:
    lines = []
    header = entry.get("name", "?")
    meta = entry.get("type", "?")
    if entry.get("source"):
        meta += f", {entry['source']}"
    if entry.get("priority"):
        meta += f", {entry['priority']}"
    if score is not None:
        lines.append(f"  {header} [{meta}] (score {score})")
    else:
        lines.append(f"  {header} [{meta}]")
    desc = entry.get("description") or ""
    if desc:
        lines.append(f"    {desc[:160]}{'...' if len(desc) > 160 else ''}")
    if entry.get("path"):
        lines.append(f"    path: {entry['path']}")
    if entry.get("usage"):
        lines.append(f"    usage: {entry['usage']}")
    if entry.get("command"):
        lines.append(f"    run: {entry['command']}")
    if entry.get("env_required"):
        lines.append(f"    env: {', '.join(entry['env_required'])}")
    if entry.get("natively_linked_by_default"):
        lines.append("    natively linked by default: yes")
    return "\n".join(lines)


def cmd_search(query: str, entry_type: str = "", limit: int = 8,
               as_json: bool = False) -> int:
    """Search every capability type for a query."""
    entries = load_all_entries()
    if entry_type:
        entries = [e for e in entries if e["type"] == entry_type]
    ranked = rank_entries(entries, query, limit)
    results = [
        {"score": score, **{k: v for k, v in entry.items()}}
        for score, entry in ranked
    ]
    if as_json:
        print(json.dumps({"query": query, "results": results}, indent=2))
        return 0
    print(f"=== Registry search: {query!r} ({len(results)} match(es)) ===")
    for result in results:
        print(_format_entry(result, result.get("score")))
    if not results:
        print("  (no matches - try broader terms, or: registry.py list)")
    return 0


def cmd_map(task: str, limit: int = 8, as_json: bool = False) -> int:
    """Map a task description to skills, plugins, MCP servers and built-ins."""
    entries = load_all_entries()
    skills = [e for e in entries if e["type"] == "skill"]
    plugins = [e for e in entries if e["type"] == "plugin"]
    mcps = [e for e in entries if e["type"] == "mcp"]
    capabilities = [e for e in entries if e["type"] == "capability"]

    ranked_skills = rank_entries(skills, task, limit)
    ranked_plugins = rank_entries(plugins, task, 5)
    ranked_caps = rank_entries(capabilities, task, 4)

    matched_plugin_slugs = {e.get("slug") or e.get("name", "") for _, e in ranked_plugins}
    mcp_scored = []
    tokens = _tokenize(task)
    for entry in mcps:
        score = score_mcp(entry, tokens)
        if any(slug in entry.get("for_plugins", []) for slug in matched_plugin_slugs):
            score += 6
        if score > 0:
            mcp_scored.append((score, entry))
    mcp_scored.sort(key=lambda pair: (-pair[0], pair[1].get("name", "")))
    ranked_mcp = mcp_scored[:5]

    plan = {
        "task": task,
        "skills": [{"score": s, **e} for s, e in ranked_skills],
        "plugins": [{"score": s, **e} for s, e in ranked_plugins],
        "mcp_servers": [{"score": s, **e} for s, e in ranked_mcp],
        "always_available": [
            {"score": s, **e} for s, e in ranked_caps
        ] or capabilities[:2],
        "hints": [
            "Skills marked 'natively linked by default' are already active in "
            "~/.claude/skills and ~/.agents/skills after setup.sh.",
            "Other skills load on demand: python3 "
            f"{UNIFIED_DIR}/scripts/load-skills.py <agent> \"{task}\"",
            "MCP servers are a roadmap: add them to your tool's MCP config "
            "(e.g. .claude/mcp.json) to enable.",
        ],
    }

    if as_json:
        print(json.dumps(plan, indent=2))
        return 0

    print("=== Capability Map ===")
    print(f"Task: {task}")
    print()
    print(f"Skills ({len(plan['skills'])}):")
    if plan["skills"]:
        for item in plan["skills"]:
            print(_format_entry(item, item.get("score")))
    else:
        print("  (none matched - browse with: registry.py list --type skill)")
    print()
    print(f"Catalog plugins ({len(plan['plugins'])}):")
    if plan["plugins"]:
        for item in plan["plugins"]:
            print(_format_entry(item, item.get("score")))
    else:
        print("  (none matched)")
    print()
    print(f"MCP servers ({len(plan['mcp_servers'])}):")
    if plan["mcp_servers"]:
        for item in plan["mcp_servers"]:
            print(_format_entry(item, item.get("score")))
    else:
        print("  (none matched for this task)")
    print()
    print("Built-in capabilities (always available):")
    for item in plan["always_available"]:
        print(_format_entry(item, item.get("score")))
    print()
    print("Hints:")
    for hint in plan["hints"]:
        print(f"  - {hint}")
    return 0


def cmd_show(identifier: str, as_json: bool = False) -> int:
    """Show one entry by id or name."""
    entries = load_all_entries()
    needle = identifier.lower()
    for prefix in ("skill:", "plugin:", "mcp:", "capability:"):
        if needle.startswith(prefix):
            needle = needle[len(prefix):]
            break
    for entry in entries:
        if entry["id"].lower() == identifier.lower() or \
                entry.get("name", "").lower() == needle or \
                entry.get("slug", "").lower() == needle:
            if as_json:
                print(json.dumps(entry, indent=2))
            else:
                print(_format_entry(entry))
                if entry.get("activation"):
                    print(f"    activation: {entry['activation']}")
            return 0
    print(f"not found: {identifier}", file=sys.stderr)
    return 1


def cmd_stats(as_json: bool = False) -> int:
    """Entry counts by type and source."""
    entries = load_all_entries()
    by_type: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    for entry in entries:
        by_type[entry["type"]] = by_type.get(entry["type"], 0) + 1
        src = entry.get("source") or "built-in"
        by_source[src] = by_source.get(src, 0) + 1
    if as_json:
        print(json.dumps({"total": len(entries), "by_type": by_type,
                          "by_source": by_source}, indent=2))
        return 0
    print(f"Registry: {len(entries)} entries")
    for key in sorted(by_type):
        print(f"  {key:12s} {by_type[key]}")
    print("By source:")
    for key in sorted(by_source):
        print(f"  {key:40s} {by_source[key]}")
    return 0


def cmd_list(entry_type: str = "", source: str = "",
             as_json: bool = False) -> int:
    """List entries, optionally filtered by type and source."""
    entries = load_all_entries()
    if entry_type:
        entries = [e for e in entries if e["type"] == entry_type]
    if source:
        entries = [e for e in entries if (e.get("source") or "built-in") == source]
    if as_json:
        print(json.dumps({"count": len(entries), "entries": entries}, indent=2))
        return 0
    for entry in entries:
        print(f"{entry['id']:40s} {entry.get('description', '')[:90]}")
    print(f"({len(entries)} entries)")
    return 0


def main(argv: List[str]) -> int:
    args = list(argv[1:])
    if not args:
        print(__doc__)
        return 2

    command, rest = args[0], args[1:]

    def has_flag(flag: str) -> bool:
        return flag in rest

    def flag_value(flag: str, default: str) -> str:
        try:
            i = rest.index(flag)
            return rest[i + 1]
        except (ValueError, IndexError):
            return default

    if command == "build":
        return cmd_build(
            out_path=flag_value("--out", "") or None,
            quiet=has_flag("--quiet"),
        )
    if command == "search":
        query = " ".join(a for a in rest if not a.startswith("--"))
        if not query:
            print("usage: registry.py search \"<query>\"", file=sys.stderr)
            return 2
        return cmd_search(
            query,
            entry_type=flag_value("--type", ""),
            limit=int(flag_value("--limit", "8")),
            as_json=has_flag("--json"),
        )
    if command == "map":
        task = " ".join(a for a in rest if not a.startswith("--"))
        if not task:
            print("usage: registry.py map \"<task description>\"", file=sys.stderr)
            return 2
        return cmd_map(task, limit=int(flag_value("--limit", "8")),
                       as_json=has_flag("--json"))
    if command == "show":
        ident = " ".join(a for a in rest if not a.startswith("--"))
        if not ident:
            print("usage: registry.py show <name-or-id>", file=sys.stderr)
            return 2
        return cmd_show(ident, as_json=has_flag("--json"))
    if command == "stats":
        return cmd_stats(as_json=has_flag("--json"))
    if command == "list":
        return cmd_list(
            entry_type=flag_value("--type", ""),
            source=flag_value("--source", ""),
            as_json=has_flag("--json"),
        )
    print(f"unknown command: {command}", file=sys.stderr)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
