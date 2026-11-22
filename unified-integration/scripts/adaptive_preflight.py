#!/usr/bin/env python3
"""Adaptive preflight capability selection (CONTRACT 8.5).

One isolated selector role, two inference sources, one validated
package (architecture review 2026-11-19, "Adaptive Preflight"):

  Mode 0  disabled/missing config - the existing discovery cards
          (runtime.skill_context) run unchanged. No credentials are
          read, no SDK is imported, no network call is made.
  Mode 1  host-native selector - the host adapter supplies the native
          selection payload (event key ``ae_native_selection``) that it
          produced through its own sanctioned inference surface before
          the agent's first request. The runtime only validates.
  Mode 2  custom model - this module calls the user-configured
          endpoint (ui.api.json "preflight") with a bounded, structured
          request.

The selector never executes anything. It returns typed registry IDs;
AgentEnhancements resolves each ID to its canonical source, checks
live readiness, and renders a bounded package for the main agent.
Every failure path - timeout, invalid JSON, refusal, fictitious ID,
unavailable capability, missing key - falls back to Mode 0 for that
turn and reports a local diagnosis on stderr (never on stdout, which
OpenCode/Hermes use as the context channel). Mode 1 never switches to
Mode 2 automatically; the model source follows the user's explicit
choice.

Configuration: the "preflight" section of the private ui.api.json
(the single AE configuration file, api_config.config_path()):

    "preflight": {"mode": 0}                            # disabled
    "preflight": {"mode": 1}                            # native host
    "preflight": {"mode": 2,                            # custom model
                  "endpoint": "https://openrouter.ai/api/v1",
                  "sdk": "openai",                      # or anthropic
                  "model": "provider/model-id",
                  "api_key_ref": "PREFLIGHT_API_KEY"}

  The Mode 2 key is api_keys[api_key_ref] of the same file (first usable
  key in rotation order). No environment variable, keyring, key file or
  legacy model.json is consulted at runtime; `api_config.py migrate`
  imports a legacy model.json/preflight.key once.

Deadline: the whole preflight phase shares one monotonic deadline
(2.0s pilot default; AE_PREFLIGHT_DEADLINE_MS overrides) and at most
two inference rounds, leaving room for the Mode 0 fallback render
inside the host's 8-10s hook budget. Late results are discarded.

The rendered package shares the UserPromptSubmit injection slot with
the legacy cards (context_budget.MAX_SKILL_CARDS, 400 tokens): on a
successful preflight the candidate cards are replaced, never stacked.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

MODE_DISABLED = 0
MODE_NATIVE = 1
MODE_CUSTOM = 2
VALID_MODES = (MODE_DISABLED, MODE_NATIVE, MODE_CUSTOM)
VALID_SDKS = ("openai", "anthropic")

#: Pilot deadline for the whole preflight phase (review 12): the host
#: hooks allow 8-10s, the fallback render needs ~100ms, so 2s leaves
#: generous headroom while bounding added latency.
DEFAULT_DEADLINE_SECONDS = 2.0
MIN_DEADLINE_SECONDS = 0.1
MAX_DEADLINE_SECONDS = 8.0

MAX_INFERENCE_ROUNDS = 2
MAX_ITEMS = 12
MAX_LOOKUP_QUERIES = 4
MAX_QUERY_CHARS = 200
MAX_INTENT_CHARS = 2_000
MAX_OUTPUT_TOKENS = 500
MAX_SEARCH_HINTS = 8
HTTP_TIMEOUT_CAP_SECONDS = 10.0

ENV_DEADLINE_MS = "AE_PREFLIGHT_DEADLINE_MS"
DEFAULT_KEY_REF = "PREFLIGHT_API_KEY"

SELECTION_DECISIONS = ("selected", "abstain", "lookup", "unresolved")
DELIVERIES = ("loaded", "callable", "direct_read", "unavailable")

_SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": list(SELECTION_DECISIONS),
        },
        "items": {
            "type": "array",
            "maxItems": MAX_ITEMS,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "required": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["id"],
                "additionalProperties": False,
            },
        },
        "queries": {
            "type": "array",
            "maxItems": MAX_LOOKUP_QUERIES,
            "items": {"type": "string", "minLength": 1},
        },
        "reason": {"type": "string"},
    },
    "required": ["decision"],
    "additionalProperties": False,
}

SELECTOR_SYSTEM = (
    "You are the capability selector for AgentEnhancements. You cannot "
    "execute anything; you only choose capabilities. Given a task intent "
    "and catalog cards, pick the minimal set of registry capabilities the "
    "task actually needs, or abstain when ordinary tools are enough. "
    "Merge needs that one capability already covers; prefer fewer items. "
    "Respond with JSON only, no prose, matching this schema: "
    '{"decision":"selected|abstain|lookup|unresolved",'
    '"items":[{"id":"<registry id>","required":true,'
    '"reason":"<short>"}],"queries":["<focused query>"]}. '
    "Rules: items only with decision=selected (0-"
    f"{MAX_ITEMS} items, ordered by importance, typed registry ids only: "
    "skill:<name>, plugin:<slug>, mcp:<server>, capability:<name>, "
    "tool:<server>/<tool-name>); queries only with decision=lookup "
    f"(1-{MAX_LOOKUP_QUERIES} focused catalog queries when the cards shown "
    "are not enough); decision=abstain when no catalog capability is "
    "needed; decision=unresolved when the catalog cannot satisfy a stated "
    "requirement. Plugin catalog entries are integration guides, not proof "
    "of an installed runtime. Mark guide-only plugin suggestions optional; "
    "a required plugin runtime without host evidence must be unresolved."
)


class PreflightError(Exception):
    """Bounded, code-first failure that triggers the Mode 0 fallback.

    The code is safe for stderr diagnostics; ``detail`` must already
    be free of secrets (it is built from our own strings and HTTP
    status codes, never from response bodies).
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


# ---------------------------------------------------------------------------
# Sibling module loading (importlib, like runtime.py's loader usage)
# ---------------------------------------------------------------------------

_MODULE_CACHE: Dict[str, Any] = {}


def _sibling(name: str):
    """Load a scripts/ sibling by file path, cached per process.

    The module is registered in sys.modules while it executes so any
    future dataclass or annotation resolution in a sibling keeps
    working (same contract as tests/helpers.load_module)."""
    if name not in _MODULE_CACHE:
        spec = importlib.util.spec_from_file_location(
            f"ae_preflight_{name}", SCRIPT_DIR / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"ae_preflight_{name}"] = module
        spec.loader.exec_module(module)
        _MODULE_CACHE[name] = module
    return _MODULE_CACHE[name]


def _budget():
    return _sibling("context_budget")


def _registry():
    return _sibling("registry")


def _api_config():
    return _sibling("api_config")


# ---------------------------------------------------------------------------
# Preflight configuration contract: ui.api.json "preflight" (review 9)
# ---------------------------------------------------------------------------


def config_dir() -> Path:
    """Private configuration in the active checkout, independent of cwd/XDG."""
    from project_paths import config_root
    return config_root()


def model_config_path() -> Path:
    """The single AE configuration file that carries the preflight section."""
    return _api_config().config_path()


def _valid_endpoint(endpoint: str) -> bool:
    """HTTPS origin, no credentials, no fragment (review 14)."""
    try:
        parts = urlsplit(endpoint)
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and bool(parts.netloc)
        and parts.username is None
        and parts.password is None
        and not parts.fragment
    )


@dataclass
class ModelConfig:
    """One snapshot of ui.api.json "preflight", read fresh per prompt."""

    mode: int = MODE_DISABLED
    endpoint: str = ""
    sdk: str = ""
    model: str = ""
    api_key_ref: str = DEFAULT_KEY_REF
    #: non-empty when a requested mode was rejected and Mode 0 runs
    diagnosis: str = ""

    @property
    def requested_mode(self) -> int:
        return self.mode


def load_model_config(config: Optional[Dict[str, Any]] = None) -> ModelConfig:
    """Validate the preflight section; every rejection falls back to
    Mode 0 with a diagnosis code (review 12, fallback table)."""
    if config is None:
        return _read_model_snapshot()[0]
    doc = config.get("preflight", {})
    if not isinstance(doc, dict):
        return ModelConfig(diagnosis="preflight_invalid:not_an_object")
    if not doc:
        return ModelConfig()  # absent section == Mode 0, no diagnosis

    mode = doc.get("mode", MODE_DISABLED)
    # bool is an int subclass; the contract requires an exact integer.
    if type(mode) is not int or mode not in VALID_MODES:
        return ModelConfig(diagnosis="preflight_invalid:mode_not_0_1_or_2")

    endpoint = doc.get("endpoint", "")
    sdk = doc.get("sdk", "")
    model = doc.get("model", "")
    key_ref = doc.get("api_key_ref", DEFAULT_KEY_REF)
    if mode == MODE_CUSTOM:
        # Only Mode 2 reads the custom settings; on Mode 0/1 they are
        # stored but ignored (review 9, "Field tersebut diabaikan").
        if not isinstance(endpoint, str) or not _valid_endpoint(endpoint):
            return ModelConfig(diagnosis="mode2_settings_invalid:endpoint")
        if sdk not in VALID_SDKS:
            return ModelConfig(diagnosis="mode2_settings_invalid:sdk")
        if not isinstance(model, str) or not model.strip():
            return ModelConfig(diagnosis="mode2_settings_invalid:model")
        if not isinstance(key_ref, str) or not _api_config().REFERENCE_PATTERN.match(key_ref):
            return ModelConfig(diagnosis="mode2_settings_invalid:api_key_ref")
    return ModelConfig(
        mode=mode,
        endpoint=endpoint if isinstance(endpoint, str) else "",
        sdk=sdk if isinstance(sdk, str) else "",
        model=model.strip() if isinstance(model, str) else "",
        api_key_ref=key_ref if isinstance(key_ref, str) else DEFAULT_KEY_REF,
    )


def _read_model_snapshot() -> tuple[ModelConfig, Dict[str, Any]]:
    """Pair validated settings with the document that supplied them."""
    api = _api_config()
    snapshot, error = api.read_config()
    if error and api.config_path().exists():
        return ModelConfig(diagnosis="ui_api_json_invalid"), snapshot
    return load_model_config(snapshot), snapshot


def deadline_seconds() -> float:
    """Pilot deadline for one preflight phase (review 12)."""
    raw = os.environ.get(ENV_DEADLINE_MS, "")
    try:
        value = float(raw) / 1000.0 if raw else DEFAULT_DEADLINE_SECONDS
    except ValueError:
        value = DEFAULT_DEADLINE_SECONDS
    return min(max(value, MIN_DEADLINE_SECONDS), MAX_DEADLINE_SECONDS)


class Deadline:
    """One monotonic deadline shared by catalog reads, connection,
    inference and validation inside a preflight phase."""

    def __init__(self, seconds: float) -> None:
        self._end = time.monotonic() + seconds

    def remaining(self) -> float:
        return max(0.0, self._end - time.monotonic())

    @property
    def expired(self) -> bool:
        return self.remaining() <= 0.0

    def timeout(self) -> float:
        """Socket timeout for the next call, capped for safety."""
        remaining = self.remaining()
        if remaining <= 0:
            raise PreflightError("timeout")
        return min(remaining, HTTP_TIMEOUT_CAP_SECONDS)


# ---------------------------------------------------------------------------
# Selection output contract (review 11)
# ---------------------------------------------------------------------------


@dataclass
class SelectionItem:
    id: str
    required: bool = True
    reason: str = ""


@dataclass
class Selection:
    decision: str
    items: List[SelectionItem] = field(default_factory=list)
    queries: List[str] = field(default_factory=list)
    reason: str = ""


def parse_selection(payload: Any) -> Selection:
    """Validate a selector payload against the output contract.

    Raises PreflightError for anything malformed: the caller falls
    back to Mode 0 rather than guessing (review 12).
    """
    if not isinstance(payload, dict):
        raise PreflightError("selection_invalid:not_an_object")
    decision = payload.get("decision")
    if decision not in SELECTION_DECISIONS:
        raise PreflightError("selection_invalid:decision")

    items: List[SelectionItem] = []
    raw_items = payload.get("items", [])
    if raw_items is None:
        raw_items = []
    if not isinstance(raw_items, list):
        raise PreflightError("selection_invalid:items")
    if decision == "selected":
        if not raw_items:
            raise PreflightError("selection_invalid:selected_without_items")
        if len(raw_items) > MAX_ITEMS:
            raise PreflightError("selection_invalid:too_many_items")
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise PreflightError("selection_invalid:item")
        item_id = raw.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise PreflightError("selection_invalid:item_id")
        required = raw.get("required", True)
        if not isinstance(required, bool):
            raise PreflightError("selection_invalid:item_required")
        reason = raw.get("reason", "")
        if not isinstance(reason, str):
            reason = ""
        items.append(
            SelectionItem(id=item_id.strip(), required=required, reason=reason[:120])
        )

    queries: List[str] = []
    raw_queries = payload.get("queries", [])
    if raw_queries is None:
        raw_queries = []
    if not isinstance(raw_queries, list):
        raise PreflightError("selection_invalid:queries")
    if decision == "lookup":
        if not raw_queries:
            raise PreflightError("selection_invalid:lookup_without_queries")
        if len(raw_queries) > MAX_LOOKUP_QUERIES:
            raise PreflightError("selection_invalid:too_many_queries")
        for query in raw_queries:
            if not isinstance(query, str) or not query.strip():
                raise PreflightError("selection_invalid:query")
            queries.append(query.strip()[:MAX_QUERY_CHARS])

    reason = payload.get("reason", "")
    if not isinstance(reason, str):
        reason = ""
    return Selection(decision=decision, items=items, queries=queries,
                     reason=reason[:200])


# ---------------------------------------------------------------------------
# Registry revision + item resolution (review 11/12)
# ---------------------------------------------------------------------------

_REGISTRY_SOURCES = (
    SCRIPT_DIR.parent / "skills" / "all-skills.json",
    REPO_ROOT / "plugin-catalog" / "catalog.json",
    REPO_ROOT / "plugin-catalog" / "mcp-servers.json",
)


def registry_revision() -> str:
    """Content revision of the catalog sources (size+mtime digest) so a
    host can detect source changes between selection and dispatch."""
    parts = []
    for path in _REGISTRY_SOURCES:
        try:
            stat = path.stat()
            parts.append(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}")
        except OSError:
            parts.append(f"{path.name}:missing")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]


def _allowed_skill_roots() -> List[Path]:
    roots = [REPO_ROOT.resolve()]
    override = os.environ.get("AGENT_SKILLS_DIR")
    if override:
        roots.append(Path(override).expanduser().resolve())
    return roots


def _file_under_roots(candidate: Path, roots: List[Path]) -> bool:
    try:
        resolved = candidate.resolve()
    except OSError:
        return False
    return any(resolved.is_relative_to(root) for root in roots)


def api_revision() -> str:
    """Nonsecret file identity, shared with the private host bridge."""
    try:
        info = _api_config().config_path().stat()
        return f"{info.st_size}:{info.st_mtime_ns}"
    except OSError:
        return "missing"


def _host_tools(agent: str, event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Consume session-bound host observations, never a static tool catalog.

    OpenCode's supported tool.list surface is currently the only adapter
    supplying this private metadata. Other hosts fail closed for MCP delivery
    until their own session tool observation is demonstrated.
    """
    inventory = event.get("ae_host_inventory")
    if inventory is None:
        return []
    if (not isinstance(inventory, dict) or agent != "opencode"
            or inventory.get("host") != agent
            or not event.get("session_id")
            or inventory.get("session_id") != event["session_id"]
            or inventory.get("source") != "ctx.tool.list"
            or inventory.get("gateway") != "agent-enhancements"):
        raise PreflightError("host_inventory_invalid")
    observed = inventory.get("observed_at")
    if (type(observed) not in (float, int)
            or not 0 <= time.time() - observed <= MAX_DEADLINE_SECONDS + 1
            or inventory.get("api_revision") != api_revision()):
        raise PreflightError("host_inventory_stale")
    tools = inventory.get("tools")
    if not isinstance(tools, list):
        raise PreflightError("host_inventory_invalid")
    return [tool for tool in tools if isinstance(tool, dict)
            and isinstance(tool.get("name"), str)
            and tool.get("namespace") == "agent-enhancements"
            and tool.get("id") == f"agent-enhancements_{tool['name']}"
            and type(tool.get("codemode")) is bool
            and isinstance(tool.get("input_schema"), dict)]


def _server_tools(server: str, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Match observed tool names using the shared gateway naming policy."""
    if not tools:
        return []
    api = _api_config()
    public_name = api.public_name
    config, _ = api.read_config()
    prefix = public_name(server, "")
    return [tool for tool in tools if tool["name"].startswith(prefix)
            and tool["name"] == public_name(server, tool["name"][len(prefix):])
            and api.tool_available(server, tool["name"][len(prefix):], config)]


def _tool_ref(tool: Dict[str, Any]) -> str:
    """Preserve the host's direct name or Code Mode namespace exactly."""
    if not tool["codemode"]:
        return tool["id"]
    name = tool["name"]
    access = "." + name if name.isidentifier() else "[" + json.dumps(name) + "]"
    return 'tools["agent-enhancements"]' + access


@dataclass
class ResolvedItem:
    """One validated package item (review 11 field table)."""

    id: str
    type: str
    ref: str
    delivery: str
    purpose: str
    note: str = ""
    required: bool = True


def _resolve_entry(entry: Dict[str, Any], required: bool,
                   tools: Optional[List[Dict[str, Any]]] = None) -> ResolvedItem:
    registry = _registry()
    entry_type = entry.get("type", "")
    purpose = (entry.get("description") or "").strip().split("\n")[0][:100]

    if entry_type == "skill":
        roots = _allowed_skill_roots()
        for key in ("source_path", "path"):
            value = entry.get(key) or ""
            if not value:
                continue
            candidate = (REPO_ROOT / value) if not value.startswith("/") else Path(value)
            if candidate.is_file() and _file_under_roots(candidate, roots):
                return ResolvedItem(
                    id=entry["id"], type="skill", ref=str(candidate),
                    delivery="direct_read", purpose=purpose,
                    note="read the SKILL.md before the related work",
                    required=required,
                )
        return ResolvedItem(
            id=entry["id"], type="skill", ref="", delivery="unavailable",
            purpose=purpose, note="skill file missing from this installation",
            required=required,
        )

    if entry_type == "plugin":
        if required:
            return ResolvedItem(
                id=entry["id"], type="plugin", ref="", delivery="unavailable",
                purpose=purpose, required=True,
                note="required plugin runtime entry point is not proven in this host session",
            )
        guide = entry.get("path") or ""
        candidate = (REPO_ROOT / guide) if guide else None
        if candidate and candidate.is_file() and _file_under_roots(candidate, [REPO_ROOT.resolve()]):
            return ResolvedItem(
                id=entry["id"], type="plugin", ref=str(candidate),
                delivery="direct_read", purpose=purpose,
                note=f"guide only ({entry.get('status', 'unknown')}); runtime "
                     "entry points follow the guide and host permissions",
                required=required,
            )
        return ResolvedItem(
            id=entry["id"], type="plugin", ref="", delivery="unavailable",
            purpose=purpose, note="plugin guide missing from this installation",
            required=required,
        )

    if entry_type == "mcp":
        api = _api_config()
        config, _ = api.read_config()
        state = api.server_state(str(entry.get("name", "")), config)
        observed = _server_tools(str(entry.get("name", "")), tools or [])
        if state.get("visible") and observed:
            return ResolvedItem(
                id=entry["id"], type="mcp", ref=", ".join(_tool_ref(tool) for tool in observed),
                delivery="callable", purpose=purpose,
                note="exact tools observed in this host session; calls retain gateway permission checks",
                required=required,
            )
        return ResolvedItem(
            id=entry["id"], type="mcp", ref="", delivery="unavailable",
            purpose=purpose,
            note="no exact tools proven in this host session",
            required=required,
        )

    if entry_type == "capability":
        return ResolvedItem(
            id=entry["id"], type="capability",
            ref=str(entry.get("usage", "")),
            delivery="callable", purpose=purpose,
            note="built-in; invoke through the documented usage line",
            required=required,
        )
    return ResolvedItem(
        id=str(entry.get("id", "")), type=entry_type, ref="",
        delivery="unavailable", purpose=purpose, note="unknown type",
        required=required,
    )


def _resolve_tool_id(item: SelectionItem, tools: List[Dict[str, Any]]) -> ResolvedItem:
    """Resolve an exact gateway tool name against this host's current view."""
    server, _, tool = item.id[len("tool:"):].partition("/")
    server = server.strip()
    tool = tool.strip()
    if not server or not tool or "/" in tool:
        raise PreflightError("selection_invalid:tool_id", item.id[:80])
    entry = _registry().find_entry(f"mcp:{server}")
    if entry is None:
        return ResolvedItem(
            id=item.id, type="tool", ref="", delivery="unavailable",
            purpose=f"tool {tool} on {server}",
            note="unknown MCP server", required=item.required,
        )
    resolved = _resolve_entry(entry, item.required, tools)
    if resolved.delivery == "unavailable":
        return ResolvedItem(
            id=item.id, type="tool", ref="", delivery="unavailable",
            purpose=f"tool {tool} on {server}", note=resolved.note,
            required=item.required,
        )
    match = next((observed for observed in _server_tools(server, tools)
                  if observed["name"] == tool), None)
    if match is None:
        return ResolvedItem(
            id=item.id, type="tool", ref="", delivery="unavailable",
            purpose=f"tool {tool} on {server}",
            note="exact tool absent from this host session", required=item.required,
        )
    return ResolvedItem(
        id=item.id, type="tool", ref=_tool_ref(match),
        delivery="callable", purpose=f"tool {tool} on {server} "
        f"({resolved.purpose[:60]})",
        note=resolved.note, required=item.required,
    )


def build_package(selection: Selection, *, agent: str = "",
                  event: Optional[Dict[str, Any]] = None) -> Tuple[List[ResolvedItem], List[str]]:
    """Resolve every selected ID to a canonical, readiness-checked item.

    Returns (package_items, unmet) where unmet lists required items
    that could not be verified - the caller falls back to Mode 0 when
    unmet is non-empty (review 12: required vs optional distinction).
    Optional items that fail are simply dropped, with a note.
    """
    registry = _registry()
    tools = _host_tools(agent, event or {})
    package: List[ResolvedItem] = []
    unmet: List[str] = []
    for item in selection.items:
        if item.id.startswith("tool:"):
            resolved = _resolve_tool_id(item, tools)
        else:
            entry = registry.find_entry(item.id)
            # CONTRACT 8.5: typed IDs resolve exactly. find_entry also serves
            # the CLI name surface (case-insensitive, untyped, cross-type),
            # which must never turn a wrong selector ID into another entry.
            if entry is not None and entry.get("id") != item.id:
                entry = None
            if entry is None:
                resolved = ResolvedItem(
                    id=item.id, type="unknown", ref="",
                    delivery="unavailable", purpose="",
                    note="id not found in the registry",
                    required=item.required,
                )
            else:
                resolved = _resolve_entry(entry, item.required, tools)
        if resolved.delivery == "unavailable":
            if item.required:
                unmet.append(f"{item.id} ({resolved.note})")
            continue
        package.append(resolved)
    return package, unmet


# ---------------------------------------------------------------------------
# Package rendering (review 7C / 11)
# ---------------------------------------------------------------------------


def render_package(items: List[ResolvedItem], revision: str,
                   budget: Optional[int] = None) -> str:
    """One compact render for the main agent inside the shared
    UserPromptSubmit slot (MAX_SKILL_CARDS). Shrink structured items,
    never serialized text: every required ID and reference is atomic.
    An oversized minimum package must take the ordinary Mode 0 fallback.
    """
    ctx_budget = _budget()
    limit = budget if budget is not None else ctx_budget.MAX_SKILL_CARDS

    def render(all_items: List[ResolvedItem], with_notes: bool,
               compact: bool = False) -> str:
        lines = [
            "AgentEnhancements preflight: selected capability package "
            f"(validated locally; registry rev {revision})."
        ]
        if compact:
            lines = [f"AgentEnhancements preflight: registry rev {revision}. "
                     "Read files before related work; use exact callable names."]
        for item in all_items:
            tag = "" if item.required else " (optional)"
            if compact:
                verb = "read" if item.delivery == "direct_read" else "use"
                lines.append(f"- {item.id} [{item.delivery}] {verb}: {item.ref}")
                continue
            lines.append(f"- {item.id} [{item.type}]{tag}: {item.purpose}")
            if item.delivery == "direct_read":
                lines.append(f"  read before related work: {item.ref}")
            elif item.delivery == "loaded":
                lines.append("  already active (natively linked)")
            else:  # callable
                lines.append(f"  use: {item.ref}")
                if with_notes and item.note:
                    lines.append(f"  note: {item.note[:110]}")
        if not compact:
            lines.append(
                "Everything else: ordinary tools. Detail pages stay on disk; "
                "the registry (registry.py show <id>) is unchanged."
            )
        return "\n".join(lines)

    remaining = list(items)
    for with_notes in (True, False):
        text = render(remaining, with_notes)
        if ctx_budget.approx_tokens(text) <= limit:
            return text
    for item in reversed(items):
        if not item.required:
            remaining.remove(item)
            if not remaining:
                return ""
            text = render(remaining, with_notes=False)
            if ctx_budget.approx_tokens(text) <= limit:
                return text
    text = render(remaining, with_notes=False, compact=True)
    if ctx_budget.approx_tokens(text) <= limit:
        return text
    raise PreflightError("package_budget_exceeded")


# ---------------------------------------------------------------------------
# Credential resolution: ui.api.json api_keys only
# ---------------------------------------------------------------------------


def resolve_api_key(config: ModelConfig, snapshot: Optional[Dict[str, Any]] = None) -> str:
    """Mode 2 key from ui.api.json ``api_keys[config.api_key_ref]``.

    One key per prompt, chosen by the shared credential pool (round-robin
    across the reference's keys). Shell environment variables, keyrings,
    key files and model.json are never consulted; the key never enters
    the selector prompt or the main-agent context.
    """
    api = _api_config()
    if snapshot is None:
        snapshot, _ = api.read_config()
    return api.select_key_for_request(config.api_key_ref, {
        "api_keys": snapshot.get("api_keys", {}),
    })


# ---------------------------------------------------------------------------
# Mode 2 inference clients (stdlib HTTP, no SDK dependency, no retries)
# ---------------------------------------------------------------------------


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse redirects: the preflight origin was validated at config
    time and must not silently move (review 14, redirect bounds)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any],
               timeout: float) -> Dict[str, Any]:
    expires = time.monotonic() + timeout
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json",
                 **headers},
        method="POST",
    )
    opener = urllib.request.build_opener(_NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            # Socket timeouts are otherwise inactivity limits: a provider can
            # keep read(size) alive indefinitely by slowly streaming bytes.
            # read1 returns available chunks, letting the shared remaining
            # budget cap every subsequent socket read.
            chunks = []
            size = 0
            while True:
                remaining = expires - time.monotonic()
                if remaining <= 0:
                    raise PreflightError("timeout")
                transport = getattr(getattr(response.fp, "raw", None), "_sock", None)
                if transport is not None:
                    transport.settimeout(remaining)
                chunk = response.read1(min(65_536, 1_048_577 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > 1_048_576:
                    raise PreflightError("response_too_large")
            body = b"".join(chunks)
            return json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # A refused redirect surfaces here as a 30x code.
        raise PreflightError(f"http_{exc.code}") from None
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, TimeoutError) or (
                isinstance(reason, OSError) and "timed out" in str(reason)):
            raise PreflightError("timeout") from None
        raise PreflightError("network_error") from None
    except TimeoutError:
        raise PreflightError("timeout") from None
    except (ValueError, UnicodeError) as exc:
        raise PreflightError("invalid_response_json",
                             type(exc).__name__) from None


def _extract_json_text(payload: Dict[str, Any]) -> str:
    """OpenAI Chat Completions / Anthropic Messages text extraction with
    explicit refusal detection (review 9 provider table)."""
    if not isinstance(payload, dict):
        raise PreflightError("invalid_response_shape")
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict):
            refusal = message.get("refusal")
            if isinstance(refusal, str) and refusal.strip():
                raise PreflightError("refusal")
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content
    content = payload.get("content")
    if isinstance(content, list) and content:
        text = "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
        if payload.get("stop_reason") == "refusal":
            raise PreflightError("refusal")
        if text.strip():
            return text
    raise PreflightError("empty_response")


def parse_json_payload(text: str) -> Any:
    """Strict-ish local JSON validation: fenced or bare (review 9,
    'validasi lokal penuh')."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise PreflightError("invalid_json")
    try:
        return json.loads(cleaned[start:end + 1])
    except ValueError as exc:
        raise PreflightError("invalid_json", type(exc).__name__) from None


def call_openai_compatible(endpoint: str, api_key: str, model: str,
                           system: str, user: str,
                           deadline: Deadline) -> Any:
    """Chat Completions on the configured base URL. Requests a strict
    json_schema response_format; a 400 (unsupported parameter on many
    OpenAI-compatible endpoints) triggers exactly ONE immediate
    compatibility re-issue without response_format - a protocol
    fallback inside the same round, never an automatic retry of a
    failed request (review 12: SDK auto-retry stays off)."""
    url = endpoint.rstrip("/") + "/chat/completions"
    base_messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    payload: Dict[str, Any] = {
        "model": model,
        "messages": base_messages,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "capability_selection",
                "schema": _SELECTION_SCHEMA,
                "strict": True,
            },
        },
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = _post_json(url, headers, payload, deadline.timeout())
    except PreflightError as exc:
        if exc.code != "http_400":
            raise
        payload.pop("response_format")
        payload["messages"] = [
            {"role": "system", "content": system + " Output JSON only."},
            {"role": "user", "content": user},
        ]
        response = _post_json(url, headers, payload, deadline.timeout())
    return parse_json_payload(_extract_json_text(response))


def call_anthropic_compatible(endpoint: str, api_key: str, model: str,
                              system: str, user: str,
                              deadline: Deadline) -> Any:
    """Messages API on the configured base URL (append /v1/messages,
    mirroring the Anthropic SDK base-URL semantics). JSON is enforced
    through the prompt and validated locally in full (review 9)."""
    url = endpoint.rstrip("/") + "/v1/messages"
    payload = {
        "model": model,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0,
        "system": system + " Output JSON only.",
        "messages": [{"role": "user", "content": user}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    response = _post_json(url, headers, payload, deadline.timeout())
    return parse_json_payload(_extract_json_text(response))


def call_model(config: ModelConfig, system: str, user: str,
               deadline: Deadline, api_key: str) -> Any:
    if config.sdk == "openai":
        return call_openai_compatible(
            config.endpoint, api_key, config.model, system, user, deadline)
    if config.sdk == "anthropic":
        return call_anthropic_compatible(
            config.endpoint, api_key, config.model, system, user, deadline)
    raise PreflightError("mode2_settings_invalid:sdk")


# ---------------------------------------------------------------------------
# Catalog view for the selector (review 8: compact catalog, staged access)
# ---------------------------------------------------------------------------


def _catalog_overview() -> str:
    registry = _registry()
    counts: Dict[str, int] = {}
    for entry in registry.load_all_entries():
        counts[entry["type"]] = counts.get(entry["type"], 0) + 1
    parts = [f"{count} {kind}s" for kind, count in sorted(counts.items())]
    return "Catalog: " + ", ".join(parts) + "."


def _cards_text(cards: List[Dict[str, Any]]) -> str:
    lines = []
    for card in cards:
        ready = card.get("ready", "unknown")
        blocker = f" - {card['blocker']}" if card.get("blocker") else ""
        lines.append(
            f"- {card['id']} [{card['type']}] "
            f"{(card.get('summary') or '')[:90]} (ready: {ready}{blocker})"
        )
    return "\n".join(lines)


def _round_one_user(prompt: str, candidates: Dict[str, Any]) -> str:
    return (
        "Task intent (bounded excerpt):\n"
        f"{prompt[:MAX_INTENT_CHARS]}\n\n"
        f"{_catalog_overview()}\n"
        "Initial candidate cards (ranked locally):\n"
        f"{_cards_text(candidates['cards'])}\n"
        "Answer with the JSON selection. Use decision=lookup with focused "
        "queries if these cards are not enough to decide."
    )


def _round_two_user(prompt: str, lookups: List[Dict[str, Any]]) -> str:
    sections = []
    for lookup in lookups:
        header = (f"Query {lookup['query'][:MAX_QUERY_CHARS]!r}: "
                  f"{lookup['matched']} matched, showing {lookup['sent']}"
                  + (", more available" if lookup.get("has_more") else ""))
        sections.append(header + "\n" + _cards_text(lookup["cards"]))
    return (
        "Task intent (bounded excerpt):\n"
        f"{prompt[:MAX_INTENT_CHARS]}\n\n"
        "Additional catalog cards you requested:\n"
        + "\n\n".join(sections)
        + "\n\nAnswer with the JSON selection (lookup is no longer "
          "available in this round)."
    )


def run_custom_selection(prompt: str, config: ModelConfig,
                         deadline: Deadline, api_key: str, *,
                         snapshot: Optional[Dict[str, Any]] = None) -> Selection:
    """Mode 2: at most two inference rounds, bounded catalog reads,
    every failure mapped to a PreflightError code."""
    # The selector gets intent, never credentials embedded in a prompt. Redact
    # before ranking/truncation so a credential cannot survive as a prefix or
    # reappear on the optional lookup round.
    redact = _api_config().redact
    prompt = redact(prompt, snapshot)
    if api_key:
        prompt = prompt.replace(api_key, "[redacted]")
    registry = _registry()
    candidates = registry.paged_search(prompt, limit=MAX_SEARCH_HINTS)
    user = _round_one_user(prompt, candidates)
    for round_no in range(MAX_INFERENCE_ROUNDS):
        if deadline.expired:
            raise PreflightError("timeout")
        payload = call_model(config, SELECTOR_SYSTEM, user, deadline, api_key)
        if deadline.expired:
            raise PreflightError("timeout")
        selection = parse_selection(payload)
        if selection.decision != "lookup":
            return selection
        if round_no == MAX_INFERENCE_ROUNDS - 1:
            # A second lookup request cannot be served: unresolved.
            raise PreflightError("lookup_round_exceeded")
        lookups = [
            registry.paged_search(query, limit=5)
            for query in selection.queries
        ]
        user = _round_two_user(prompt, lookups)
    raise PreflightError("lookup_round_exceeded")  # unreachable guard


# ---------------------------------------------------------------------------
# Orchestration: the single handler shared by every mode (review 10/16)
# ---------------------------------------------------------------------------


@dataclass
class PreflightResult:
    context: str
    requested_mode: int
    effective_mode: int
    fallback_reason: str = ""


def _diagnose(message: str) -> None:
    """Bounded stderr diagnosis; stdout is the context channel on
    OpenCode/Hermes and must stay clean (review 12)."""
    message = " ".join(message.split())[:200]
    print(f"[AgentEnhancements] preflight: {message}", file=sys.stderr)


def preflight_context(
    agent: str,
    prompt: str,
    event: Dict[str, Any],
    fallback: Callable[[str, str], str],
) -> PreflightResult:
    """The one entry point runtime.py calls on UserPromptSubmit.

    Never raises: any failure returns the Mode 0 render (the caller's
    legacy ``skill_context``) with a diagnosis. Memory effects stay in
    runtime.py and run exactly once regardless of the mode.
    """
    config, snapshot = _read_model_snapshot()
    if config.diagnosis:
        _diagnose(f"preflight config rejected ({config.diagnosis}); running Mode 0")
    if config.mode == MODE_DISABLED:
        return PreflightResult(
            context=fallback(agent, prompt),
            requested_mode=MODE_DISABLED,
            effective_mode=MODE_DISABLED,
            fallback_reason=config.diagnosis,
        )

    deadline = Deadline(deadline_seconds())
    try:
        revision = registry_revision()
        if config.mode == MODE_NATIVE:
            if agent not in ("claude-code", "codex"):
                raise PreflightError("mode1_host_unsupported")
            # The adapter supplies the native selection through the
            # event (its own sanctioned inference surface). The
            # runtime itself never calls the host model.
            native = event.get("ae_native_selection")
            if not isinstance(native, dict):
                raise PreflightError("mode1_native_selection_unavailable")
            selection = parse_selection(native)
            if selection.decision == "lookup":
                raise PreflightError("mode1_selection_not_final")
        else:
            api_key = resolve_api_key(config, snapshot)
            if not api_key:
                raise PreflightError("api_key_unavailable")
            selection = run_custom_selection(prompt, config, deadline, api_key,
                                             snapshot=snapshot)

        if selection.decision == "abstain":
            return PreflightResult(
                context="", requested_mode=config.mode,
                effective_mode=config.mode,
            )
        if selection.decision == "unresolved":
            raise PreflightError("selection_unresolved", selection.reason[:80])

        items, unmet = build_package(selection, agent=agent, event=event)
        if unmet:
            raise PreflightError(
                "required_capability_unavailable",
                "; ".join(unmet)[:160],
            )
        if not items:
            # selected with zero usable items behaves like abstain
            return PreflightResult(
                context="", requested_mode=config.mode,
                effective_mode=config.mode,
            )
        if registry_revision() != revision:
            raise PreflightError("registry_changed")
        if deadline.expired:
            raise PreflightError("timeout")
        context = render_package(items, revision)
        _host_tools(agent, event)
        if registry_revision() != revision:
            raise PreflightError("registry_changed")
        if deadline.expired:
            raise PreflightError("timeout")
        return PreflightResult(
            context=context,
            requested_mode=config.mode,
            effective_mode=config.mode,
        )
    except PreflightError as exc:
        _diagnose(
            f"mode {config.mode} -> 0 fallback ({exc.code})"
        )
        return PreflightResult(
            context=fallback(agent, prompt),
            requested_mode=config.mode,
            effective_mode=MODE_DISABLED,
            fallback_reason=exc.code,
        )
    except Exception as exc:  # noqa: BLE001 - the hook must never fail
        _diagnose(f"mode {config.mode} -> 0 fallback "
                  f"({type(exc).__name__})")
        return PreflightResult(
            context=fallback(agent, prompt),
            requested_mode=config.mode,
            effective_mode=MODE_DISABLED,
            fallback_reason=type(exc).__name__,
        )


def status_report() -> Dict[str, Any]:
    """Redacted, doctor-friendly summary of the preflight config."""
    config, snapshot = _read_model_snapshot()
    report: Dict[str, Any] = {
        "config_file": str(model_config_path()),
        "requested_mode": config.mode,
        "effective_mode": config.mode if not config.diagnosis else MODE_DISABLED,
        "diagnosis": config.diagnosis,
    }
    if config.mode == MODE_NATIVE and not config.diagnosis:
        # No shipped adapter supplies ae_native_selection (no host offers a
        # pre-inference selection surface), so every prompt runs Mode 0.
        report["effective_mode"] = MODE_DISABLED
        report["diagnosis"] = "mode1_native_selection_unavailable"
    if config.mode == MODE_CUSTOM and not config.diagnosis:
        report["endpoint"] = config.endpoint
        report["sdk"] = config.sdk
        report["model"] = config.model
        report["api_key_ref"] = config.api_key_ref
        report["api_key_present"] = bool(snapshot.get("api_keys", {}).get(config.api_key_ref))
        if not report["api_key_present"]:
            report["effective_mode"] = MODE_DISABLED
            report["diagnosis"] = "api_key_unavailable"
    return report


if __name__ == "__main__":  # pragma: no cover - manual inspection
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent", choices=["claude-code", "codex", "opencode",
                                          "hermes"])
    parser.add_argument("prompt")
    args = parser.parse_args()
    result = preflight_context(
        args.agent, args.prompt, {},
        fallback=lambda a, p: "(mode 0 fallback not wired in manual mode)",
    )
    print(json.dumps({
        "context": result.context,
        "requested_mode": result.requested_mode,
        "effective_mode": result.effective_mode,
        "fallback_reason": result.fallback_reason,
    }, indent=2))
