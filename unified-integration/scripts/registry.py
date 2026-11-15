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
sys.path.insert(0, str(SCRIPT_DIR))

from context_budget import (  # noqa: E402
    MAX_DETAIL_PAGE,
    MAX_SEARCH_CARDS,
    MAX_SEARCH_PAGE,
    approx_tokens,
    clamp_to_budget,
)

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
    "letter": "docx",
    "surat": "docx",
    "mcp server": "mcp-builder",
    "mcp": "mcp-builder",
}

# Intent synonyms (EN<->EN, ID->EN, EN->ID-neutral): users describe goals,
# skill descriptions use domain vocabulary. Each group expands a query
# token to the others so intent-language finds domain-language. Groups are
# small and manually curated - determinism beats an embedding here.
INTENT_SYNONYM_GROUPS = [
    {"threat", "ancaman", "menace", "risk", "risiko"},
    {"paper", "papers", "literature", "literatur", "makalah", "jurnal",
     "publikasi", "publication"},
    {"launch", "launching", "luncurkan", "peluncuran", "rilis", "release",
     "people", "saying", "buzz", "sentiment", "orang", "bicarakan"},
    {"injection", "sqli", "xss", "exploit", "eksploitasi", "vulnerability",
     "celah"},
    {"clip", "highlight", "montage", "video", "rekaman", "footage"},
    {"deck", "presentation", "presentasi", "slide", "slides"},
    {"letter", "surat", "offer", "penawaran", "formal"},
    {"dashboard", "visual", "spacing", "spasi", "polish", "rapikan"},
    {"fail", "fails", "failing", "broken", "crash", "crashes", "error",
     "errors", "bug", "bugs", "debug", "debugging", "gagal", "rusak",
     "macet", "akarnya", "kerusakan"},
    {"review", "reviewing", "audit", "inspect", "examine", "periksa",
     "telaah", "review"},
    {"test", "testing", "tests", "uji", "pengujian", "tes"},
    {"refactor", "restructure", "rewrite", "rapikan", "susun"},
    {"transcribe", "transcription", "subtitle", "transkrip", "transkripsi"},
    {"summarize", "summary", "summarise", "rangkum", "ringkas"},
    {"translate", "translation", "terjemah"},
    {"design", "visual", "ui", "ux", "desain", "tampilan"},
    {"deploy", "deployment", "release", "ship", "publish", "rilis",
     "deploy"},
    {"optimize", "performance", "perf", "cepat", "optimasi"},
    {"secure", "security", "harden", "hardening", "keamanan", "aman"},
    {"document", "documentation", "docs", "dokumentasi", "dokumen"},
    {"learn", "study", "understand", "explain", "pelajari", "paham",
     "jelaskan"},
    {"plan", "planning", "roadmap", "rencana", "perencanaan"},
    {"note", "remember", "recall", "catat", "ingat", "catatan"},
    {"decide", "decided", "decision", "decisions", "keputusan", "putuskan"},
    {"model", "modeling", "modelling", "pemodelan", "modeling"},
    {"compress", "shrink", "reduce", "kecilkan", "kompres"},
    {"cut", "trim", "clip", "potong", "segment", "segmen", "rekaman",
     "recording", "video"},
    {"product", "produk", "spec", "spesifikasi", "greenfield", "scratch",
     "dari nol"},
    {"backlog", "issue", "issues", "tiket", "tickets", "github"},
    {"compare", "diff", "comparison", "bandingkan", "perbandingan"},
    {"build", "create", "make", "generate", "buat", "buatkan", "bangun"},
    {"fix", "repair", "patch", "perbaiki", "perbaikan"},
]

_INTENT_SYNONYMS: Dict[str, frozenset] = {}
for _group in INTENT_SYNONYM_GROUPS:
    for _word in _group:
        _INTENT_SYNONYMS[_word] = frozenset(_group)

# Minimum score for a card to be worth showing. Below this, the search
# abstains (honest no-match) instead of surfacing noise - the difference
# between discovery and keyword spam (mandate §12: at least 90% of
# negative intents must not load detail).
CARD_MIN_SCORE = 5

# Verbs that appear in thousands of skill descriptions. Alone, they name
# generic actions, not capabilities ("write a haiku", "translate good
# morning"); a query whose original tokens are all in this set abstains
# rather than emitting a noise card. With any domain noun present, the
# query searches normally.
GENERIC_ACTION_WORDS = frozenset("""
write writing writes summarize summarise summary translate translation
create creating make making build building generate generating learn
learning explain explaining recommend recommending suggest name naming
say saying tell telling ask asking know knowing find finding get getting
buat buatkan bangun tulis rangkum terjemah jelaskan sarankan cari tahu
sebut mengapa kenapa apa siapa kapan dimana berapa banyak sedikit
""".split())

# Formatting/layout nouns name document anatomy, not domains: alone they
# cannot trigger the hyphenated-name phrase bonus ("paragraph"-optimizer
# for "summarize the plot of Hamlet in one paragraph").
LAYOUT_NOUNS = frozenset("""
paragraph paragraphs page pages line lines word words sentence sentences
chapter chapters plot story text file folder list item table row column
halaman paragraf baris kata kalimat bab teks berkas folder daftar tabel
""".split())

# Sources that link-skills.sh activates natively by default. Keep in sync
# with DEFAULT_SOURCES in link-skills.sh.
DEFAULT_NATIVE_SOURCES = ("anthropic-skills", "replica-skill", "task-observer")

BUILT_IN_CAPABILITIES = [
    {
        "id": "capability:memory",
        "type": "capability",
        "name": "memory",
        "description": "Persistent cross-session memory backed by SQLite "
                       "(parameterized queries). Save, load and list memories "
                       "for any agent.",
        "keywords": ["memory", "remember", "preference", "recall", "persist",
                     "session", "context", "decided", "decision", "keputusan",
                     "catat", "note"],
        "usage": 'python3 {unified}/scripts/memory.py <agent> save|load|list ["key" ["value"]]',
        "automatic": "Claude Code and Codex lifecycle hooks; OpenCode 2 server plugin",
    },
    {
        "id": "capability:compression",
        "type": "capability",
        "name": "compression",
        "description": "Context compression for long transcripts (headroom "
                       "binary or pure-Python fallback).",
        "keywords": ["compress", "token", "budget", "context", "long",
                     "transcript", "summarize", "log", "logs", "dump",
                     "huge", "shrink", "kecilkan", "terlalu", "besar"],
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
    {
        "id": "capability:task-observer",
        "type": "capability",
        "name": "task-observer",
        "description": "Ambient skill-usage observation (vendored "
                       "rebelytics/one-skill-to-rule-them-all, CC-BY-4.0): "
                       "logs user corrections and methodology evidence to a "
                       "persistent workspace, reviews them, and stages skill "
                       "updates for explicit approval. Observations are "
                       "semantic and agent-authored; raw tool payloads are "
                       "never recorded.",
        "keywords": ["observe", "observation", "improve", "skill", "correction",
                     "feedback", "review", "learn", "note", "noted", "catat",
                     "koreksi", "perbaiki"],
        "usage": 'python3 {unified}/scripts/task-observer.py '
                 "status|log|lookup|review|stage|promote|rollback|disable|enable",
        "automatic": "SessionStart bootstrap via the shared lifecycle runtime; "
                     "bundle natively linked by default",
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
            "when_to_use": skill.get("when_to_use", ""),
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
            "env_optional": server.get("env_optional", []),
            "for_plugins": server.get("for_plugins", []),
            "status": server.get("status", "roadmap"),
            "path": "plugin-catalog/mcp-servers.json",
            "activation": ("loaded automatically by the native agent-enhancements gateway; ui.api.json controls cloud availability"
                           if server.get("status") == "built" else
                           "hidden until an installed command and required references are configured in ui.api.json"),
        })
    return entries


def usable_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Hide unconfigured MCPs from agent-facing search/map/list results."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ae_registry_api", UNIFIED_DIR / "scripts/api_config.py")
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    config, _ = api.read_config()
    return [entry for entry in entries if entry["type"] != "mcp"
            or api.server_state(entry["name"], config)["visible"]]


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

def score_skill(entry: Dict[str, Any], weights: Dict[str, float]) -> float:
    score = 0.0
    name = (entry.get("name") or "").lower()
    desc_tokens = set(_tokenize(entry.get("description", "")))
    desc_tokens |= set(_tokenize(entry.get("when_to_use", "")))
    tags = {t.lower() for t in entry.get("tags", [])}
    name_matched = False
    name_hits = 0
    generic_confirmed = False
    for token, weight in weights.items():
        # Generic action verbs never graze a name: "write" must not rank
        # write-design-md, "translate" must not rank visa-doc-translate.
        # They confirm a domain match at most ONCE total (desc and
        # when_to_use are one field set), never accumulate synonyms.
        if token in GENERIC_ACTION_WORDS:
            if not generic_confirmed and token in desc_tokens:
                score += 0.5 * weight
                generic_confirmed = True
            continue
        alias_target = FORMAT_ALIASES.get(token)
        if not name_matched and (token == name or
                                 (alias_target and alias_target == name)):
            # Full-name/alias match: the entry IS this capability family;
            # never let multi-token grazers outrank it.
            score = max(score, 20) if weight >= 1.0 else score + 8 * weight
            name_matched = True
        elif not name_matched and name.startswith(token):
            score += 4 * weight
        elif not name_matched and token in name:
            # Word-boundary only: "rain" must not graze "constraint".
            parts = name.split("-")
            if any(token == part or token in part.split() for part in parts):
                score += 3 * weight
                name_hits += 1
        if token in tags:
            score += 2 * weight
        if token in desc_tokens:
            score += 1.5 * weight
        if alias_target and alias_target in desc_tokens:
            score += weight
    # A name carrying several query tokens (offer+letter, threat+model)
    # is a stronger signal than one grazing token in the description.
    if name_hits >= 2:
        score += 3 * name_hits
    # Domain-technical hyphenated names (protocol-reverse): one domain
    # word in the name plus the SAME domain confirmed in the entry's
    # description is a phrase match, not a graze. The confirming token
    # must differ from the name-grazing token (agency-customer-service
    # grazing "service" must not qualify via an unrelated desc word).
    elif name_hits == 1 and "-" in name:
        grazing = next(
            (t for t, w in weights.items()
             if w >= 1.0 and t in name and t not in LAYOUT_NOUNS), None
        )
        if grazing and any(
            token in desc_tokens
            for token, weight in weights.items()
            if weight >= 1.0 and token != grazing
        ):
            score += 4
    # A single grazing token in the name (write->write-design-md,
    # api->claude-api) is noise unless a description/tag field confirms
    # the domain or the match is the full name.
    if name_hits == 1 and not name_matched and score < 8:
        # Domain-technical names (protocol-reverse, firmware-analyst)
        # carry two domain words: a graze counts only when a description
        # field confirms the domain too.
        if not (re.search(r"[a-z]+-[a-z]+", name) and desc_tokens):
            score = 0
    # Natively linked skills are already active in every harness: prefer
    # the zero-friction capability when relevance is otherwise equal.
    if score > 0 and entry.get("natively_linked_by_default"):
        score += 3
    return score


def score_plugin(entry: Dict[str, Any], weights: Dict[str, float],
                 query_lower: str) -> float:
    score = 0.0
    name = (entry.get("name") or "").lower()
    # Expanded vocabulary: synonym tokens joined as words let a keyword
    # like "binary analysis" match a query that only said "firmware",
    # and Indonesian intents reach English keywords.
    expanded_text = query_lower + " " + " ".join(weights)
    for kw in entry.get("trigger_keywords", []):
        kw_lower = kw.lower()
        if kw_lower and re.search(r"\b" + re.escape(kw_lower) + r"\b", expanded_text):
            score += 6 if kw_lower in query_lower.split() or kw_lower in query_lower else 4
    fields = set(_tokenize(entry.get("description", "")))
    for phrase in entry.get("best_for", []):
        if isinstance(phrase, str):
            fields.update(_tokenize(phrase))
    for token, weight in weights.items():
        if token in name:
            score += 3 * weight
        if token in fields:
            score += weight
    return score


def score_mcp(entry: Dict[str, Any], weights: Dict[str, float]) -> float:
    score = 0.0
    name = (entry.get("name") or "").lower()
    fields = set(_tokenize(entry.get("description", "")))
    fields |= set(_tokenize(entry.get("category", "")))
    fields |= set(_tokenize(" ".join(entry.get("for_plugins", []))))
    for token, weight in weights.items():
        if token in name:
            score += 4 * weight
        if token in fields:
            # MCP entries have short keyword fields; a synonym hit is a
            # strong enough signal to clear the card threshold.
            score += 4 * weight
    if score > 0 and entry.get("priority") == "P0":
        score += 1
    return score


def score_capability(entry: Dict[str, Any], weights: Dict[str, float]) -> float:
    score = 0.0
    name = (entry.get("name") or "").lower()
    fields = set(_tokenize(entry.get("description", "")))
    fields |= {k.lower() for k in entry.get("keywords", [])}
    for token, weight in weights.items():
        if token in name:
            score += 5 * weight
        if token in fields:
            score += 4 * weight
    return score


def token_weights(tokens: List[str]) -> Dict[str, float]:
    """Original query tokens weigh 1.0; intent-synonym expansions 0.5.

    Expansions exist to bridge user vocabulary and domain vocabulary
    ("fails" -> "debugging"), not to outrank the words the user actually
    said. A skill matching only expansion terms is a candidate; a skill
    matching the user's own words ranks above it.
    """
    weights: Dict[str, float] = {token: 1.0 for token in tokens}
    for token in tokens:
        for synonym in _INTENT_SYNONYMS.get(token, ()):  # noqa: SIM118
            if synonym not in weights:
                weights[synonym] = 0.5
    return weights


def expand_intent(tokens: List[str]) -> List[str]:
    """Expand query tokens with their intent-synonym group.

    "fails" carries the debug/debugging family, so a skill described as
    "debugging any bug" matches a user who said "the build fails".
    Originals keep their weight; expansions act as weaker matches via
    the existing field scoring (they are appended, not substituted).
    """
    expanded = list(tokens)
    seen = set(tokens)
    for token in tokens:
        for syn in _INTENT_SYNONYMS.get(token, ()):  # noqa: SIM118
            if syn not in seen:
                expanded.append(syn)
                seen.add(syn)
    return expanded


def rank_entries(entries: List[Dict[str, Any]], query: str,
                 limit: int = 8) -> List[Tuple[int, Dict[str, Any]]]:
    """Score and rank entries against a natural-language query.

    Query tokens are expanded with intent synonyms before scoring; weak
    keyword matches stay below CARD_MIN_SCORE and are dropped, so a
    no-relevance query returns nothing instead of noise.
    """
    tokens = _tokenize(query)
    query_lower = (query or "").lower()
    if not tokens:
        return []
    weights = token_weights(tokens)
    # Generic-only queries abstain: chit-chat and small talk must not
    # produce capability cards (negative suppression target >= 90%).
    originals = [t for t, w in weights.items() if w >= 1.0]
    if originals and all(t in GENERIC_ACTION_WORDS for t in originals):
        return []
    scored = []
    for entry in entries:
        if entry["type"] == "skill":
            score = score_skill(entry, weights)
        elif entry["type"] == "plugin":
            score = score_plugin(entry, weights, query_lower)
        elif entry["type"] == "mcp":
            score = score_mcp(entry, weights)
        else:
            score = score_capability(entry, weights)
        if score >= CARD_MIN_SCORE:
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
    # Committed snapshots must not contain the builder's home/checkout path.
    # Live CLI queries still resolve their own absolute installation path.
    for entry in entries:
        if "usage" in entry:
            entry["usage"] = entry["usage"].replace(str(UNIFIED_DIR), "unified-integration")
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
    # Audit AE-14: do not rewrite the committed registry when only the
    # generated_at timestamp would change - that dirties the working tree
    # on every setup run without altering any capability data.
    try:
        previous = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = None
    if isinstance(previous, dict):
        previous_core = {k: v for k, v in previous.items() if k != "generated_at"}
        registry_core = {k: v for k, v in registry.items() if k != "generated_at"}
        if previous_core == registry_core:
            if not quiet:
                print(f"Registry unchanged ({len(entries)} entries); timestamp preserved")
                print(f"  skills={by_type.get('skill', 0)} plugins={by_type.get('plugin', 0)} "
                      f"mcp={by_type.get('mcp', 0)} capabilities={by_type.get('capability', 0)}")
            return 0
    with open(target, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    if not quiet:
        print(f"Registry built: {len(entries)} entries -> {target}")
        print(f"  skills={by_type.get('skill', 0)} plugins={by_type.get('plugin', 0)} "
              f"mcp={by_type.get('mcp', 0)} capabilities={by_type.get('capability', 0)}")
    return 0


def _skill_readiness(entry: Dict[str, Any]) -> Dict[str, str]:
    """Live readiness for a skill entry: is it actually reachable now?

    Natively linked skills are checked against the link-skills targets;
    everything else is reachable on demand through the loader (the index
    is present by construction), which is the default profile's intended
    access path - on-demand is "ready", not a degraded state; "degraded"
    is reserved for skills whose native-link profile exists but whose
    link is missing on this host while the loader path is also unusable.
    Never inherited from a parent or manifest.
    """
    if entry.get("natively_linked_by_default"):
        targets = os.environ.get(
            "AGENT_SKILLS_NATIVE_TARGETS",
            f"{Path.home() / '.claude' / 'skills'}:{Path.home() / '.agents' / 'skills'}",
        ).split(":")
        for base in targets:
            if (Path(base) / str(entry.get("name", ""))).is_dir():
                return {"ready": "yes", "how": "natively linked"}
    # Not natively present: the on-demand loader is the default access
    # path for every catalog entry (context-frugal profile).
    return {"ready": "yes", "how": "on-demand via the skills loader"}


def _mcp_readiness(entry: Dict[str, Any]) -> Dict[str, str]:
    """Live readiness for an MCP entry via api_config.server_state."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ae_registry_api", UNIFIED_DIR / "scripts/api_config.py")
        api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(api)
        config, _ = api.read_config()
        state = api.server_state(entry.get("name", ""), config)
        if state.get("visible"):
            return {"ready": "yes", "how": state.get("reason", "visible")}
        return {"ready": "no", "blocker": state.get("reason", "not visible")}
    except Exception:  # noqa: BLE001 - readiness is advisory, never fatal
        return {"ready": "unknown", "blocker": "state unavailable"}


def entry_readiness(entry: Dict[str, Any]) -> Dict[str, str]:
    if entry.get("type") == "mcp":
        return _mcp_readiness(entry)
    if entry.get("type") == "skill":
        return _skill_readiness(entry)
    return {"ready": "yes", "how": "built-in"}


def _card(entry: Dict[str, Any], score: Optional[int] = None) -> Dict[str, Any]:
    """A level-1 catalog card: id, type, one-line summary, why-relevant,
    readiness with a short blocker, and a detail pointer. Long fields
    (full descriptions, triggers, schemas, dependency lists, audit
    history) stay on disk and are fetched via `show`."""
    ready = entry_readiness(entry)
    card: Dict[str, Any] = {
        "id": entry.get("id", ""),
        "type": entry.get("type", ""),
        "name": entry.get("name", ""),
        "summary": (entry.get("description") or "").strip()[:140],
        "ready": ready.get("ready", "unknown"),
        "detail": f"registry.py show {entry.get('name') or entry.get('id')}",
    }
    if ready.get("ready") != "yes" and ready.get("blocker"):
        card["blocker"] = ready["blocker"][:80]
    if score is not None:
        card["why"] = f"matched {score} query term(s)"
    return card


def _format_card(card: Dict[str, Any]) -> str:
    lines = [f"- {card['name']} [{card['type']}] {card['id']}"]
    if card.get("summary"):
        lines.append(f"  {card['summary']}")
    why = card.get("why")
    if why:
        lines.append(f"  why: {why}")
    if card.get("ready") == "yes":
        lines.append(f"  ready: yes ({card.get('how', '')})".rstrip())
    else:
        lines.append(f"  ready: {card.get('ready', '?')}"
                     + (f" - {card['blocker']}" if card.get("blocker") else ""))
    lines.append(f"  detail: {card['detail']}")
    return "\n".join(lines)


def _page_meta(total_matched: int, shown: int, limit: int) -> Dict[str, Any]:
    return {
        "matched": total_matched,
        "shown": shown,
        "page_limit": min(limit, MAX_SEARCH_CARDS),
        "continuation": (
            "narrow the query or raise --limit to see more; every card "
            "above links to its full detail"
            if total_matched > shown
            else ""
        ),
    }


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
    if entry.get("source_path"):
        lines.append(f"    source: {entry['source_path']}")
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
    """Search every capability type; returns a bounded card page (L1).

    Output is capped at MAX_SEARCH_CARDS cards and MAX_SEARCH_PAGE tokens
    (context contract §8.4): a search result is a pointer surface, not a
    catalog dump. Detail for any card is one `show` away.
    """
    entries = usable_entries(load_all_entries())
    if entry_type:
        entries = [e for e in entries if e["type"] == entry_type]
    # Rank the full match set once so `matched` (the page's continuation
    # signal) is the true count, not just the page slice.
    ranked_all = rank_entries(entries, query, limit=len(entries) or 1)
    page_size = min(limit, MAX_SEARCH_CARDS)
    ranked = ranked_all[:page_size]
    cards = [_card(entry, score) for score, entry in ranked]
    meta = _page_meta(len(ranked_all), len(cards), limit)
    if as_json:
        print(json.dumps({"query": query, **meta, "cards": cards}, indent=2))
        return 0
    print(f"=== Registry search: {query!r} ({meta['matched']} match(es), "
          f"showing {meta['shown']}) ===")
    for card in cards:
        print(_format_card(card))
    if not cards:
        print("  (no matches - try broader terms, or: registry.py list)")
    elif meta["continuation"]:
        print(f"  ({meta['continuation']})")
    return 0


def cmd_map(task: str, limit: int = 8, as_json: bool = False) -> int:
    """Map a task description to skills, plugins, MCP servers and built-ins."""
    entries = usable_entries(load_all_entries())
    skills = [e for e in entries if e["type"] == "skill"]
    plugins = [e for e in entries if e["type"] == "plugin"]
    mcps = [e for e in entries if e["type"] == "mcp"]
    capabilities = [e for e in entries if e["type"] == "capability"]

    ranked_skills = rank_entries(skills, task, min(limit, MAX_SEARCH_CARDS))
    ranked_plugins = rank_entries(plugins, task, 5)
    ranked_caps = rank_entries(capabilities, task, 4)

    matched_plugin_slugs = {e.get("slug") or e.get("name", "") for _, e in ranked_plugins}
    mcp_scored = []
    weights_map = token_weights(_tokenize(task))
    for entry in mcps:
        score = score_mcp(entry, weights_map)
        if any(slug in entry.get("for_plugins", []) for slug in matched_plugin_slugs):
            score += 6
        if score > 0:
            mcp_scored.append((score, entry))
    mcp_scored.sort(key=lambda pair: (-pair[0], pair[1].get("name", "")))
    ranked_mcp = mcp_scored[:5]

    plan = {
        "task": task,
        "skills": [_card(e, s) for s, e in ranked_skills],
        "plugins": [_card(e, s) for s, e in ranked_plugins],
        "mcp_servers": [_card(e, s) for s, e in ranked_mcp],
        "always_available": [
            _card(e, s) for s, e in ranked_caps
        ] or [_card(c) for c in capabilities[:2]],
        "hints": [
            "Cards are pointers: run 'registry.py show <name>' for a "
            "candidate's usage contract before loading its SKILL.md.",
            "Only configured MCP servers are shown; edit ui.api.json for "
            "credentials and external runtimes.",
        ],
    }

    if as_json:
        print(clamp_to_budget(json.dumps(plan, indent=2),
                              MAX_SEARCH_PAGE * 2, label="registry map"))
        return 0

    print("=== Capability Map ===")
    print(f"Task: {task}")
    print()
    for section in ("skills", "plugins", "mcp_servers"):
        labels = {"skills": "Skills", "plugins": "Catalog plugins",
                  "mcp_servers": "MCP servers"}
        print(f"{labels[section]} ({len(plan[section])}):")
        if plan[section]:
            for card in plan[section]:
                print(_format_card(card))
        else:
            print("  (none matched)")
        print()
    print("Built-in capabilities (always available):")
    for card in plan["always_available"]:
        print(_format_card(card))
    print()
    print("Hints:")
    for hint in plan["hints"]:
        print(f"  - {hint}")
    return 0


def cmd_show(identifier: str, as_json: bool = False) -> int:
    """Show one entry by id or name (L2 detail, bounded).

    The detail page carries the usage contract, dependencies, pointers and
    live readiness. Output is clamped to MAX_DETAIL_PAGE tokens with an
    explicit truncation note pointing at the on-disk source; nothing is
    silently cut.
    """
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
            detail = dict(entry)
            detail["readiness"] = entry_readiness(entry)
            if as_json:
                print(clamp_to_budget(
                    json.dumps(detail, indent=2), MAX_DETAIL_PAGE,
                    label="registry detail"))
                return 0
            text = _format_entry(entry)
            if entry.get("activation"):
                text += f"\n    activation: {entry['activation']}"
            ready = detail["readiness"]
            text += (f"\n    readiness: {ready.get('ready', '?')}"
                     + (f" ({ready.get('how')})" if ready.get("how") else "")
                     + (f" - {ready['blocker']}" if ready.get("blocker") else ""))
            print(clamp_to_budget(text, MAX_DETAIL_PAGE,
                                  label="registry detail"))
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
    entries = usable_entries(load_all_entries())
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

    def positional_text() -> str:
        """Keep filter/limit values out of the natural-language relevance query."""
        values = {"--type", "--limit", "--out", "--source"}
        parts = []
        skip = False
        for item in rest:
            if skip:
                skip = False
            elif item in values:
                skip = True
            elif not item.startswith("--"):
                parts.append(item)
        return " ".join(parts)

    if command == "build":
        return cmd_build(
            out_path=flag_value("--out", "") or None,
            quiet=has_flag("--quiet"),
        )
    if command == "search":
        query = positional_text()
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
        task = positional_text()
        if not task:
            print("usage: registry.py map \"<task description>\"", file=sys.stderr)
            return 2
        return cmd_map(task, limit=int(flag_value("--limit", "8")),
                       as_json=has_flag("--json"))
    if command == "show":
        ident = positional_text()
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
