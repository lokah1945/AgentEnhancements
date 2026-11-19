#!/usr/bin/env python3
"""Task Observer integration for the shared AgentEnhancements runtime.

This module is the host adapter for the vendored `task-observer` skill
(task-observer/SKILL.md, upstream rebelytics/one-skill-to-rule-them-all,
pinned commit in task-observer/VENDORED.json). It implements:

- status / enable / disable (persisted marker; survives setup re-runs)
- workspace bootstrapping (upstream "Workspace creation" layout, run by
  SessionStart so a session that never mentions the skill still finds it)
- structured observation logging that calls the upstream helper
  scripts/new-observation.sh with a validated body (the only write path;
  id derivation, collision guards and the id-floor stay upstream's)
- open-observation lookup for a skill name (the per-skill check)
- review: reads OPEN entries, prepares a staged copy + diff under
  skill-updates/ WITHOUT touching any installed skill
- promotion: applies an approved staged copy to the vendored source tree
  (the canonical source; setup re-aggregates the distribution copies) and
  rolls back on demand
- degraded, non-blocking diagnostics: an observer failure must never
  break the agent's work

Conventions:
- The observation workspace root defaults to $AGENT_MEMORY_ROOT/task-observer
  (persistent, outside any checkout and outside skill-discovery trees;
  AGENT_MEMORY_ROOT is the documented cross-agent memory root).
- User state is private: nothing here is committed by setup; the workspace
  contains user data only.
- No network. No LLM provider calls. Content of observations is redacted
  with the shared runtime redaction before it is written.
- Upstream script semantics are preserved: this adapter never writes an
  observation file directly - it goes through new-observation.sh --body,
  which refuses invalid headers, derives the id and guards collisions.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from api_config import redact as redact_credentials

UNIFIED_DIR = SCRIPT_DIR.parent
BASE_DIR = UNIFIED_DIR.parent

# Vendored bundle (canonical source of the skill itself)
BUNDLE_DIR = BASE_DIR / "task-observer"
BUNDLE_SCRIPTS = BUNDLE_DIR / "scripts"

DEFAULT_ROOT = "task-observer"  # under AGENT_MEMORY_ROOT

# Statuses understood by the upstream log (references/observation-log.md)
UPSTREAM_STATUSES = ("open", "actioned", "declined", "superseded", "parked")

MAX_OBSERVATION_BODY = 64_000  # bounded: observations are prose, not transcripts

def redact(value: str) -> str:
    """Redact recognizable credentials before anything is persisted."""
    return redact_credentials(value)


def _now_date() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def workspace_root(explicit: Optional[str] = None) -> Path:
    """Resolve the pinned observation workspace root (absolute, never cwd)."""
    if explicit:
        root = Path(explicit).expanduser()
    else:
        env = os.environ.get("TASK_OBSERVER_WORKSPACE")
        if env:
            root = Path(env).expanduser()
        else:
            memory = os.environ.get(
                "AGENT_MEMORY_ROOT", str(Path.home() / ".agent-memory")
            )
            root = Path(memory).expanduser() / DEFAULT_ROOT
    if not root.is_absolute():
        raise ValueError(f"workspace root must be absolute, got {root}")
    return root


def state_dir(root: Path) -> Path:
    """skill-observations/ inside the workspace root (upstream layout)."""
    return root / "skill-observations"


def log_dir(root: Path) -> Path:
    return state_dir(root) / "observation-log"


def updates_dir(root: Path) -> Path:
    """skill-updates/ sits BESIDE skill-observations/, never inside it."""
    return root / "skill-updates"


def disabled_marker(root: Path) -> Path:
    return root / ".task-observer-disabled"


# ---------------------------------------------------------------------------
# enable / disable / status
# ---------------------------------------------------------------------------

def set_disabled(root: Path, disabled: bool) -> str:
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    marker = disabled_marker(root)
    if disabled:
        marker.write_text(
            "Disabled by user; observations and checkpoints are preserved.\n"
            "Logging, bootstrap and skill staging/promotion are paused; the\n"
            "existing data and staged candidates are untouched. Remove this\n"
            "file (or run: enable) to re-enable.\n"
        )
        return "disabled"
    marker.unlink(missing_ok=True)
    return "enabled"


def is_disabled(root: Path) -> bool:
    return disabled_marker(root).exists()


def _read_frontmatter(path: Path) -> Dict[str, str]:
    """Best-effort single-level YAML frontmatter read (flat scalars only).

    Only the head of the file is read (frontmatter first, bounded) so a
    large unresolved backlog cannot turn SessionStart status into
    unbounded I/O inside a hook timeout.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        head = fh.read(8192)
    lines = head.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    out: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _open_entries(root: Path) -> List[Path]:
    d = log_dir(root)
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("[0-9]*.md") if p.is_file())


def status(root: Path) -> Dict[str, Any]:
    """Honest status: installed/disabled/ready/degraded + counts."""
    info: Dict[str, Any] = {
        "bundle_installed": (BUNDLE_DIR / "SKILL.md").is_file(),
        "workspace": str(root),
        "workspace_exists": state_dir(root).is_dir(),
        "disabled": is_disabled(root),
    }
    scripts = ("new-observation.sh", "session-start-scan.sh", "skill-load.sh")
    info["helpers_present"] = all(
        (BUNDLE_SCRIPTS / s).is_file() for s in scripts
    )
    entries = _open_entries(root)
    open_count = 0
    unreadable = 0
    for entry in entries:
        try:
            fm = _read_frontmatter(entry)
        except OSError:
            unreadable += 1
            continue
        if fm.get("status", "open") == "open":
            open_count += 1
    info["open_observations"] = open_count
    info["unreadable_entries"] = unreadable
    last_review = state_dir(root) / "last-review-date.txt"
    info["last_review"] = (
        last_review.read_text().strip()
        if last_review.is_file()
        else "never"
    )
    if not info["bundle_installed"]:
        info["state"] = "not installed"
    elif info["disabled"]:
        info["state"] = "disabled"
    elif unreadable:
        info["state"] = "degraded (unreadable log entries)"
    else:
        info["state"] = "ready"
    return info


# ---------------------------------------------------------------------------
# workspace bootstrap (upstream "Workspace creation", idempotent)
# ---------------------------------------------------------------------------

def _bundle_version() -> str:
    """Version string from the vendored bundle's frontmatter (never a fetch)."""
    try:
        fm = _read_frontmatter(BUNDLE_DIR / "SKILL.md")
        return fm.get("version", "unknown")
    except OSError:
        return "unknown"


def bootstrap_workspace(root: Path) -> str:
    """Create the upstream four-artefact workspace; idempotent, no network.

    Mirrors references/observation-log.md "Workspace creation": the four
    artefacts (observation-log/, observation-log/archive/,
    last-review-date.txt, cross-cutting-principles.md) are created and
    asserted. Legacy pre-3.0 log.md is refused with a pointer to the
    upstream migration procedure (not auto-migrated).
    """
    if is_disabled(root):
        return "disabled; workspace untouched"
    state = state_dir(root)
    if (state / "log.md").is_file() and not log_dir(root).is_dir():
        return (
            "degraded: legacy pre-3.0 log.md present; run the upstream "
            "migration (task-observer/references/migration.md) before "
            "observations can be logged"
        )
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        state.mkdir(parents=True, exist_ok=True)
        (log_dir(root) / "archive").mkdir(parents=True, exist_ok=True)
        last = state / "last-review-date.txt"
        if not last.exists():
            last.write_text("never\n")
        principles = state / "cross-cutting-principles.md"
        if not principles.exists():
            principles.write_text(
                "# Cross-Cutting Principles\n\n"
                "Principles that apply to all skills. Read as a mandatory "
                "checklist during\nany skill creation or regeneration.\n\n"
                "---\n\n## Active Principles\n"
            )
        checkpoints = state / "checkpoints.log"
        if not checkpoints.exists():
            checkpoints.write_text("")
        missing = [
            name
            for name in (
                "observation-log",
                "observation-log/archive",
                "last-review-date.txt",
                "cross-cutting-principles.md",
            )
            if not (state / name).exists()
        ]
        if missing:
            return f"degraded: workspace setup incomplete: {', '.join(missing)}"
    except OSError as exc:
        return f"degraded: workspace bootstrap failed: {exc}"
    return "ok"


def bootstrap_context(root: Path, agent: str) -> str:
    """Bounded session-start context (paths, state, checkpoints - not bodies).

    ``agent`` is accepted for provenance/logging symmetry with the other
    runtime hooks; the context itself is agent-neutral by design.
    """
    info = status(root)
    if not info["bundle_installed"]:
        return ""
    if info["disabled"]:
        return ""
    boot = bootstrap_workspace(root)
    if boot.startswith("degraded"):
        # Surface the diagnosis, never block the session.
        return (
            f"AgentEnhancements task-observer: {boot}. Observations will not "
            "be recorded until this is fixed; the agent's main work is "
            "unaffected."
        )
    lines = [
        "AgentEnhancements task-observer is active (v" + _bundle_version()
        + ", CC-BY-4.0, rebelytics/one-skill-to-rule-them-all).",
        f"Observation workspace: {root}",
        "Log observations when evidence exists, via:",
        f"python3 {Path(__file__)} log --workspace \"{root}\" "
        "--title <t> --issue <t> --principle <t>"
        " [--skill <name> ...] [--improvement <t>]",
        f"Open observations: {info['open_observations']}; "
        f"last review: {info['last_review']}.",
    ]
    # Surface a bounded list of open targets so a next session can find them.
    shown = 0
    for entry in _open_entries(root):
        if shown >= 5:
            lines.append("(older entries omitted; see the full log)")
            break
        try:
            fm = _read_frontmatter(entry)
        except OSError:
            continue
        if fm.get("status", "open") != "open":
            continue
        title = fm.get("title", "") or entry.name
        skill = fm.get("skill", "") or "-"
        lines.append(f"- {entry.stem}: {title} (skill: {skill})")
        shown += 1
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stop-event backstop (upstream "Deliverable-event flush")
# ---------------------------------------------------------------------------

def stop_backstop(root: Path, session_label: str) -> str:
    """Flush/checkpoint duty at session Stop, mirroring the upstream
    deliverable-event flush that the excluded experimental plugin
    (plugins/task-observer-flush) provided.

    Upstream semantics (SKILL.md "How to Log"): whenever a unit of work
    ends, pending observations are written and a checkpoint line is
    appended to skill-observations/checkpoints.log - a remembered
    "ask whether" is not enforcement. This adapter cannot know which
    observations the agent considered pending, so the backstop records an
    honest checkpoint line: session ended, pending-observation state
    unknown from the adapter's side, with the reminder to log any
    unwritten evidence. It never fabricates observations and never
    touches entry files.

    Bounded: one line per Stop, no bodies, no transcript content.
    """
    if is_disabled(root):
        return ""
    if not (BUNDLE_DIR / "SKILL.md").is_file():
        return ""
    state = state_dir(root)
    if not state.is_dir():
        return ""  # never started; nothing to checkpoint
    try:
        line = (
            f"{_now_date()} stop-flush session={session_label} "
            "pending-observations-unknown; log any unwritten evidence now "
            "(upstream: deliverable-event flush at work-unit end)\n"
        )
        with open(state / "checkpoints.log", "a", encoding="utf-8") as fh:
            fh.write(line[:500])
    except OSError:
        return ""  # advisory by contract
    return ""


# ---------------------------------------------------------------------------
# observation logging (write path = upstream helper, validated body)
# ---------------------------------------------------------------------------

def _yaml_quote(value: str) -> str:
    """Double-quote a prose value, escaping inner quotes and control
    characters (newlines would otherwise break line-based frontmatter
    readers, including this module's own)."""
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return '"' + escaped + '"'


def log_observation(
    root: Path,
    title: str,
    issue: str,
    improvement: str,
    principle: str,
    skill: Optional[List[str]] = None,
    proposes_skill: Optional[List[str]] = None,
    target_file: Optional[List[str]] = None,
    siblings_checked: str = "checked — no family registry; instance-specific",
    obs_type: str = "internal",
    area: str = "",
    session_context: str = "",
) -> str:
    """Write one observation through the upstream helper.

    The body is validated here first (status/type/siblings_checked are the
    fields the helper refuses on) and redacted; the helper then derives the
    id, sweeps resolved files, claims the number and creates the file.
    """
    if is_disabled(root):
        return "observer disabled; nothing written"
    if not (BUNDLE_SCRIPTS / "new-observation.sh").is_file():
        return "degraded: upstream helper missing (bundle incomplete)"
    if obs_type not in ("open-source", "internal"):
        return "refused: type must be open-source or internal"
    if not title.strip() or not issue.strip() or not principle.strip():
        return "refused: title, issue and principle are required"
    if not siblings_checked.strip():
        return "refused: siblings_checked must be non-empty"

    boot = bootstrap_workspace(root)
    if boot.startswith("degraded"):
        return f"not written: {boot}"

    # Every free-text field is redacted and length-bounded BEFORE it
    # reaches the file (a multi-megabyte title is a self-inflicted DoS).
    title = redact(title)[:300]
    area = redact(area)[:200]
    session_context = redact(session_context)[:500]
    siblings_checked = redact(siblings_checked)[:500]
    body_text = redact(
        f"**Issue:** {issue}\n\n"
        f"**Suggested improvement:** {improvement or '(see principle)'}\n\n"
        f"**Principle:** {principle}\n"
    )[:MAX_OBSERVATION_BODY]

    def _safe_list(items):
        # Redact each item, then keep only single-token names: a list
        # entry carrying ':' or quotes would produce invalid YAML that
        # the upstream scan flags (and the helper refuses).
        out = []
        for item in items or []:
            cleaned = redact(str(item).strip())
            if cleaned and _SAFE_NAME.fullmatch(cleaned):
                out.append(cleaned)
        return out

    fm_lines = [
        "---",
        "id: __ID__",
        f"title: {_yaml_quote(title)}",
        "status: open",
        f"type: {obs_type}",
        f"skill: [{', '.join(_safe_list(skill))}]",
        f"proposes_skill: [{', '.join(_safe_list(proposes_skill))}]",
        "target_file: " + json.dumps(
            [redact(str(item).strip())[:500] for item in (target_file or [])
             if str(item).strip()], ensure_ascii=False,
        ),
        f"siblings_checked: {_yaml_quote(siblings_checked)}",
        f"area: {_yaml_quote(area)}",
        "date: __DATE__",
        f"session_context: {_yaml_quote(session_context)}",
        "parked_until:",
        "resolved:",
        "resolution:",
        "reference:",
        "commands_verified:",
        "next_actor:",
        "use_evidence:",
        "escalated:",
        "---",
        "",
        body_text,
    ]
    body = "\n".join(fm_lines) + "\n"

    spec_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as spec:
            spec_path = spec.name
            spec.write(body)
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
        slug = slug or "observation"
        try:
            proc = subprocess.run(
                [
                    "bash",
                    str(BUNDLE_SCRIPTS / "new-observation.sh"),
                    "--body",
                    spec_path,
                    slug,
                    str(root),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return f"degraded: observation helper unavailable: {exc}"
        if proc.returncode != 0:
            return f"helper refused: {proc.stderr.strip()[:500]}"
        created = proc.stdout.strip()
        return f"observation written: {created}"
    finally:
        if spec_path:
            os.unlink(spec_path)


def lookup_skill(root: Path, skill_name: str) -> Dict[str, Any]:
    """Open observations naming a skill (the per-skill check, read-only)."""
    matches: List[Dict[str, str]] = []
    for entry in _open_entries(root):
        try:
            fm = _read_frontmatter(entry)
        except OSError:
            continue
        if fm.get("status", "open") != "open":
            continue
        targets = fm.get("skill", "") + " " + fm.get("target_file", "")
        if re.search(
            rf"(^|[,[]\s*){re.escape(skill_name)}(\s*[\],]|$)", targets
        ):
            matches.append(
                {
                    "id": fm.get("id", entry.stem.split("-")[0]),
                    "title": fm.get("title", ""),
                    "file": str(entry),
                }
            )
    return {"skill": skill_name, "open_observations": matches}


# ---------------------------------------------------------------------------
# review / staging / promotion (fixture-safe; nothing auto-applied)
# ---------------------------------------------------------------------------

def _tree_sha256(tree: Path, skip: str = "PROPOSAL.md") -> str:
    """Stable digest over a staged tree (content-addressed candidate)."""
    import hashlib

    h = hashlib.sha256()
    for p in sorted(
        q for q in tree.rglob("*") if q.is_file() and q.name != skip
    ):
        h.update(str(p.relative_to(tree)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def _source_base_commit(source: Path) -> str:
    """Best-effort provenance for a vendored source tree."""
    vendored = source / "VENDORED.json"
    if source == BUNDLE_DIR and vendored.is_file():
        try:
            return json.loads(vendored.read_text())["upstream_commit"]
        except (OSError, KeyError, ValueError):
            pass
    try:
        git = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return git.stdout.strip() if git.returncode == 0 else "unknown"


def _staged_is_stale(stage: Path, source: Path) -> Optional[str]:
    """Detect a candidate staged against an older source (stale base).

    The candidate's PROPOSAL.md records base_commit (repository HEAD at
    staging time) and candidate_sha256. A candidate is stale when the
    canonical source changed after staging: the recorded digest of the
    then-current source tree no longer matches what is live now.
    """
    proposal = stage / "PROPOSAL.md"
    if not proposal.is_file():
        return "staged copy has no PROPOSAL.md (created by an older version?)"
    fm = _read_frontmatter(proposal)
    # candidate_sha256 is provenance metadata only: editing the staged
    # copy before promotion is the documented workflow, so it is never
    # re-verified here. Staleness is decided by base_source_sha256 (the
    # digest of the SOURCE at staging time) against the live source.
    current_digest = _tree_sha256(source, skip="PROPOSAL.md")
    base_digest = fm.get("base_source_sha256", "")
    if not base_digest:
        return None  # older staging run without a digest; promote proceeds
    if base_digest and base_digest != current_digest:
        return (
            "source changed after staging (base_source_sha256 mismatch); "
            "refresh the candidate: re-stage from the current source and "
            "re-apply the proposed change"
        )
    return None


def _run_bundle_python(args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(BUNDLE_SCRIPTS / "validate-skill-bundle.py"), *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def stage_candidate(
    root: Path,
    skill_name: str,
    changes: str,
    source_observations: List[str],
) -> str:
    """Prepare a staged copy of a vendored skill + a reviewable diff.

    Reads the CURRENT canonical source (task-observer/<name>/ or the
    vendored bundle itself), copies it to
    skill-updates/<date>/<name>/, writes a PROPOSAL.md (reason, origin
    observations, how to test) and a diff. The installed/aggregated copies
    are never touched by staging.
    """
    # Non-bundle skills in this repository are vendored as sibling trees
    # (replica-skill/<name>/, anthropic-skills/skills/<name>/, ...); search
    # the known source roots before falling back to the observer bundle.
    if not _valid_skill_name(skill_name):
        return "refused: invalid skill name (single path component, no '..')"
    if is_disabled(root):
        return "observer disabled; staging is available again after 'enable'"
    source = None
    if skill_name != "task-observer":
        search_roots = [
            BUNDLE_DIR.parent / "replica-skill",
            BUNDLE_DIR.parent / "anthropic-skills" / "skills",
            BUNDLE_DIR.parent / "superpowers" / "skills",
            BUNDLE_DIR.parent / "ECC" / "skills",
            BUNDLE_DIR.parent / "ponytail" / "skills",
            BUNDLE_DIR.parent / "agentic-awesome-skills" / "skills",
        ]
        for base in search_roots:
            candidate = base / skill_name
            if (candidate / "SKILL.md").is_file():
                source = candidate
                break
        if source is None:
            # Unknown skill names are refused with the searched roots:
            # silently staging the observer bundle under another skill's
            # name would produce a candidate that promotes the wrong tree.
            return (
                f"refused: source skill '{skill_name}' not found in the "
                "vendored tree (searched: "
                + ", ".join(str(r.name) for r in search_roots)
                + "); only the task-observer bundle itself is stageable "
                "by that name"
            )
    else:
        source = BUNDLE_DIR if (BUNDLE_DIR / "SKILL.md").is_file() else None
    if source is None:
        return "refused: task-observer bundle not installed (no SKILL.md)"
    stage_root = updates_dir(root) / _now_date()
    stage = stage_root / skill_name
    if stage.exists():
        shutil.rmtree(stage)
    stage.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Preserve symlinks as links (a dangling one in the SOURCE tree
        # must not crash staging with an unhandled shutil.Error).
        _copy_tree(source, stage)
    except (OSError, RecursionError, shutil.Error) as exc:
        shutil.rmtree(stage, ignore_errors=True)
        return f"refused: could not copy the source tree: {exc}"
    (stage / "PROPOSAL.md").write_text(
        "---\n"
        f"status: staged\n"
        f"skill: {skill_name}\n"
        f"date: {_now_date()}\n"
        f"source_path: {source}\n"
        f"base_commit: "
        + _source_base_commit(source)
        + "\n"
        f"candidate_sha256: {_tree_sha256(stage)}\n"
        f"base_source_sha256: {_tree_sha256(source)}\n"
        f"observations: {', '.join(source_observations)}\n"
        "---\n\n"
        f"# Proposed change\n\n{changes}\n\n"
        "## Validation\n\n"
        "Run before promotion: `python3 "
        f"{BUNDLE_SCRIPTS / 'validate-skill-bundle.py'} {stage}`\n\n"
        "Promotion applies the staged copy to the canonical vendored source "
        "and re-aggregates; it never edits aggregated copies directly.\n"
    )
    diff_file = stage_root / f"{stage.name}.diff"
    try:
        diff = subprocess.run(
            ["diff", "-ruN", str(source), str(stage)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        diff_text = diff.stdout
    except (OSError, subprocess.SubprocessError):
        import difflib

        diff_text = "\n".join(
            difflib.unified_diff(
                [], [], fromfile=str(source), tofile=str(stage)
            )
        ) or "(diff unavailable; compare manually)"
    diff_file.write_text(diff_text if diff_text else "(no content diff)\n")
    ledger = updates_dir(root) / "PENDING.md"
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write(
            f"- {_now_date()} staged {stage.name} from {source} "
            f"(observations: {', '.join(source_observations) or 'none'})\n"
        )
    return f"staged: {stage} (diff: {diff_file}); nothing installed"


def review(root: Path) -> Dict[str, Any]:
    """Read-only review: open entries grouped by skill + staged candidates."""
    groups: Dict[str, List[Dict[str, str]]] = {}
    for entry in _open_entries(root):
        try:
            fm = _read_frontmatter(entry)
        except OSError:
            continue
        if fm.get("status", "open") != "open":
            continue
        for target in re.findall(r"[\w.-]+", fm.get("skill", "")):
            groups.setdefault(target, []).append(
                {"id": fm.get("id", ""), "title": fm.get("title", "")}
            )
    staged = []
    pending = updates_dir(root) / "PENDING.md"
    if pending.is_file():
        staged = [
            line.strip("- \n")
            for line in pending.read_text().splitlines()
            if line.strip()
        ]
    return {
        "open_by_skill": groups,
        "staged_candidates": staged,
        "note": "review is read-only; promotion is a separate explicit step",
    }


_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _valid_skill_name(name: str) -> bool:
    """A name that feeds rmtree/glob/join must be a single safe path
    component: no separators, no '..', no glob metacharacters."""
    return bool(_SAFE_NAME.fullmatch(name)) and ".." not in name.split("/")


def _canonical_source(skill_name: str) -> Optional[Path]:
    """The canonical (vendored) source tree for a skill, or None."""
    if skill_name == "task-observer":
        return BUNDLE_DIR if (BUNDLE_DIR / "SKILL.md").is_file() else None
    search_roots = [
        BUNDLE_DIR.parent / "replica-skill",
        BUNDLE_DIR.parent / "anthropic-skills" / "skills",
        BUNDLE_DIR.parent / "superpowers" / "skills",
        BUNDLE_DIR.parent / "ECC" / "skills",
        BUNDLE_DIR.parent / "ponytail" / "skills",
        BUNDLE_DIR.parent / "agentic-awesome-skills" / "skills",
    ]
    for base in search_roots:
        candidate = base / skill_name
        if (candidate / "SKILL.md").is_file():
            return candidate
    return None


def _same_filesystem(a: Path, b: Path) -> bool:
    """True when both existing parents sit on one device (rename is atomic)."""
    try:
        return os.stat(a).st_dev == os.stat(b).st_dev
    except OSError:
        return False


def _copy_tree(src: Path, dst: Path) -> None:
    """Copy a tree preserving symlinks as symlinks (never dereference).

    The staged copy lives in user-writable workspace data; dereferencing
    a tampered symlink would materialize out-of-tree content into the
    canonical repo tree, and a symlink loop would recurse unboundedly.
    ``symlinks=True`` copies the link itself. Callers treat OSError and
    RecursionError as refusals, so a hostile or broken stage never
    escapes the transaction.
    """
    shutil.copytree(src, dst, symlinks=True)


def promote(root: Path, staged_name: str) -> str:
    """Apply an approved staged copy to the canonical source tree.

    The canonical source is the vendored tree at the repository root
    (task-observer/..., replica-skill/<name>/, ...); re-running setup.sh
    regenerates the aggregated by-category copies from it.

    Transaction order (works within one filesystem AND across them):

    1. Backup: COPY the live source into the rollback slot (renames
       cannot cross devices; a copied backup is equally recoverable and
       is verified before the source is touched).
    2. Candidate: COPY the staged tree to a sibling ".new" directory on
       the SAME filesystem as the target, so the swap itself is a local
       rename (atomic on that filesystem).
    3. Swap: rename target -> ".old" sibling, rename ".new" -> target.
       Both renames are intra-filesystem by construction.
    4. On any failure: ".new" is removed and/or ".old" is renamed back,
       so the source is never left absent or half-replaced.

    The rollback record names the backup copy; a rollback restores from
    it. Nothing healthy is deleted before its replacement is in place.
    """
    if not _valid_skill_name(staged_name):
        return "refused: invalid staged name (single path component, no '..')"
    if is_disabled(root):
        return "observer disabled; promotion is available again after 'enable'"
    date_dirs = sorted(updates_dir(root).glob("*/"))
    stage = None
    for d in reversed(date_dirs):
        candidate = d / staged_name
        if candidate.is_dir():
            stage = candidate
            break
    if stage is None:
        return f"refused: no staged copy named '{staged_name}'"
    # Containment: the stage must live inside skill-updates/, not beside it.
    if updates_dir(root).resolve() not in stage.resolve().parents:
        return "refused: staged copy escapes the staging root"
    target = _canonical_source(staged_name)
    if target is None:
        return f"refused: canonical source for '{staged_name}' not found"
    stale = _staged_is_stale(stage, target)
    if stale:
        return f"refused: stale candidate — {stale}"
    try:
        check = _run_bundle_python([str(stage)])
    except (OSError, subprocess.SubprocessError) as exc:
        return f"degraded: validator unavailable: {exc}"
    if check.returncode != 0:
        return (
            "refused: staged copy failed the upstream validator:\n"
            + check.stdout[-800:]
            + check.stderr[-400:]
        )
    rollback_dir = updates_dir(root) / "rollback"
    rollback_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = rollback_dir / f"{staged_name}-{stamp}"
    if backup.exists():
        shutil.rmtree(backup)
    new_tree = target.with_name(target.name + ".new")
    old_tree = target.with_name(target.name + ".old")
    for scratch in (new_tree, old_tree):
        if scratch.exists():
            shutil.rmtree(scratch)
    # 1. Backup the live source FIRST (copy, device-safe), then verify the
    #    backup actually contains the source's SKILL.md before touching
    #    anything: an unverifiable backup aborts the promotion. A copy
    #    failure (permissions, symlink loop) is a refusal, never an
    #    uncaught traceback, and cleans up its partial artifacts.
    try:
        _copy_tree(target, backup)
    except (OSError, RecursionError) as exc:
        shutil.rmtree(backup, ignore_errors=True)
        return f"refused: backup copy failed: {exc}"
    if not (backup / "SKILL.md").is_file():
        shutil.rmtree(backup, ignore_errors=True)
        return "refused: backup verification failed (no SKILL.md in the copy)"
    # 2. Prepare the candidate beside the target (same filesystem).
    try:
        _copy_tree(stage, new_tree)
    except (OSError, RecursionError) as exc:
        shutil.rmtree(backup, ignore_errors=True)
        shutil.rmtree(new_tree, ignore_errors=True)
        return f"refused: staged copy failed: {exc}"
    (new_tree / "PROPOSAL.md").unlink(missing_ok=True)
    try:
        # 3. Swap via intra-filesystem renames only.
        os.rename(target, old_tree)
        try:
            os.rename(new_tree, target)
        except OSError:
            os.rename(old_tree, target)  # restore; never leave source absent
            return ("refused: promotion failed while installing the staged "
                    "copy; source restored")
    except OSError as exc:
        for scratch in (new_tree,):
            if scratch.exists():
                shutil.rmtree(scratch, ignore_errors=True)
        if not target.exists() and old_tree.exists():
            os.rename(old_tree, target)
        return f"degraded: promotion swap failed: {exc}"
    # 4. Swap done; the superseded tree is already preserved in `backup`,
    #    so the ".old" sibling is redundant and can be dropped.
    shutil.rmtree(old_tree, ignore_errors=True)
    with open(updates_dir(root) / "PENDING.md", "a", encoding="utf-8") as fh:
        fh.write(
            f"- {_now_date()} PROMOTED {staged_name} from {stage} "
            f"(rollback: {backup})\n"
        )
    return (
        f"promoted {staged_name} to {target}; rollback backup at {backup}; "
        "re-run setup.sh to re-aggregate the distribution copies"
    )


def rollback(root: Path, staged_name: str) -> str:
    """Restore the most recent rollback backup for a promoted skill.

    Same transaction discipline as promote(): the restore copy is staged
    and verified BESIDE the live source first; the live tree is only
    renamed away once the verified replacement exists, and any failure
    restores it. The source is never deleted before its replacement is
    in place.
    """
    if not _valid_skill_name(staged_name):
        return "refused: invalid staged name (single path component, no '..')"
    rollback_dir = updates_dir(root) / "rollback"
    if not rollback_dir.is_dir():
        return "refused: no rollback backups"
    backups = sorted(rollback_dir.glob(f"{staged_name}-*"))
    if not backups:
        return f"refused: no rollback backup for '{staged_name}'"
    backup = backups[-1]
    target = _canonical_source(staged_name)
    if target is None:
        return f"refused: canonical source for '{staged_name}' not found"
    staged_restore = target.with_name(target.name + ".restore")
    if staged_restore.exists():
        shutil.rmtree(staged_restore)
    try:
        _copy_tree(backup, staged_restore)
    except (OSError, RecursionError) as exc:
        shutil.rmtree(staged_restore, ignore_errors=True)
        return f"degraded: rollback staging failed: {exc}"
    if not (staged_restore / "SKILL.md").is_file():
        shutil.rmtree(staged_restore, ignore_errors=True)
        return "refused: rollback backup verification failed (no SKILL.md)"
    old_tree = target.with_name(target.name + ".old")
    if old_tree.exists():
        shutil.rmtree(old_tree)
    try:
        if target.exists():
            os.rename(target, old_tree)
        try:
            os.rename(staged_restore, target)
        except OSError:
            if old_tree.exists():
                os.rename(old_tree, target)  # never leave source absent
            return "refused: rollback swap failed; source restored"
    except OSError as exc:
        shutil.rmtree(staged_restore, ignore_errors=True)
        if not target.exists() and old_tree.exists():
            os.rename(old_tree, target)
        return f"degraded: rollback swap failed: {exc}"
    shutil.rmtree(old_tree, ignore_errors=True)
    with open(updates_dir(root) / "PENDING.md", "a", encoding="utf-8") as fh:
        fh.write(f"- {_now_date()} ROLLED BACK {staged_name} to {backup}\n")
    return f"rolled back {staged_name} from {backup}; re-run setup.sh"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_root(args: argparse.Namespace) -> Path:
    return workspace_root(getattr(args, "workspace", None))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def add_workspace(p):
        p.add_argument("--workspace", help="override the workspace root")
        return p

    add_workspace(sub.add_parser("status"))
    add_workspace(sub.add_parser("enable"))
    add_workspace(sub.add_parser("disable"))
    add_workspace(sub.add_parser("bootstrap"))
    p = add_workspace(sub.add_parser("log"))
    p.add_argument("--title", required=True)
    p.add_argument("--issue", required=True)
    p.add_argument("--principle", required=True)
    p.add_argument("--improvement", default="")
    p.add_argument("--skill", action="append", default=[])
    p.add_argument("--proposes-skill", action="append", default=[])
    p.add_argument("--target-file", action="append", default=[])
    p.add_argument("--siblings-checked",
                   default="checked — no family registry; instance-specific")
    p.add_argument("--type", choices=["open-source", "internal"],
                   default="internal")
    p.add_argument("--area", default="")
    p.add_argument("--session-context", default="")
    p = add_workspace(sub.add_parser("lookup"))
    p.add_argument("skill_name")
    p = add_workspace(sub.add_parser("stage"))
    p.add_argument("skill_name")
    p.add_argument("changes")
    p.add_argument("--observation", action="append", default=[])
    add_workspace(sub.add_parser("review"))
    p = add_workspace(sub.add_parser("promote"))
    p.add_argument("staged_name")
    p = add_workspace(sub.add_parser("rollback"))
    p.add_argument("staged_name")
    p = add_workspace(sub.add_parser("bootstrap-context"))
    p.add_argument("--agent", default="claude-code")

    args = parser.parse_args()
    root = _cli_root(args)

    def emit(message: str) -> int:
        """Print a result; refusal/degraded/failure messages exit non-zero.

        A promotion that fails (including the cross-filesystem swap) must
        surface a non-zero exit to scripts and hooks that chain commands.
        Advisory hook output stays zero-exit; only this CLI's own failed
        operations report failure.
        """
        print(message)
        return 1 if message.startswith(("refused", "observer disabled",
                                        "not written", "helper refused",
                                        "degraded")) else 0

    if args.command == "status":
        print(json.dumps(status(root), indent=2))
        return 0
    if args.command == "enable":
        print(set_disabled(root, False))
        return 0
    if args.command == "disable":
        print(set_disabled(root, True))
        return 0
    if args.command == "bootstrap":
        print(bootstrap_workspace(root))
        return 0
    if args.command == "bootstrap-context":
        print(bootstrap_context(root, args.agent))
        return 0
    if args.command == "log":
        return emit(
            log_observation(
                root,
                title=args.title,
                issue=args.issue,
                improvement=args.improvement,
                principle=args.principle,
                skill=args.skill,
                proposes_skill=args.proposes_skill,
                target_file=args.target_file,
                siblings_checked=args.siblings_checked,
                obs_type=args.type,
                area=args.area,
                session_context=args.session_context,
            )
        )
    if args.command == "lookup":
        print(json.dumps(lookup_skill(root, args.skill_name), indent=2))
        return 0
    if args.command == "stage":
        return emit(
            stage_candidate(
                root, args.skill_name, args.changes, args.observation
            )
        )
    if args.command == "review":
        print(json.dumps(review(root), indent=2))
        return 0
    if args.command == "promote":
        return emit(promote(root, args.staged_name))
    if args.command == "rollback":
        return emit(rollback(root, args.staged_name))
    return 2


if __name__ == "__main__":
    sys.exit(main())
