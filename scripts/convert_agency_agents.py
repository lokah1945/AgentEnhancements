#!/usr/bin/env python3
"""Convert vendored agency-agents personas into Agent Skills format.

Reads every frontmatter agent file from agency-agents/<division>/**/*.md and
writes a mirrored skill tree at agency-agents/skills/<division>/<agent-slug>/
with a SKILL.md whose frontmatter matches the unified-index schema
(docs/SKILLS.md): name, category (normalized to the 10 canonical buckets),
description, risk, tags, tools.

The generated tree is the aggregation input consumed by setup.sh
(process_skills_source "agency-agents"); the vendored persona files stay
untouched (R303: the source of truth remains the upstream copy).

Run from repo root:  python3 scripts/convert_agency_agents.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VENDOR = REPO / "agency-agents"
OUT = VENDOR / "skills"

# 10 canonical categories of the unified index (docs/SKILLS.md).
CANONICAL_CATEGORIES = (
    "security", "architecture", "testing", "refactoring", "code-review",
    "documentation", "devops", "ai-ml", "productivity", "general",
)

# Division -> canonical category mapping for index routing. Divisions whose
# personas are personality/process overlays rather than hard technical
# domains map to "productivity"; technical domains keep their bucket.
DIVISION_CATEGORY = {
    "academic": "productivity",
    "design": "productivity",
    "engineering": "general",
    "finance": "productivity",
    "game-development": "general",
    "gis": "general",
    "healthcare": "productivity",
    "marketing": "productivity",
    "paid-media": "productivity",
    "product": "productivity",
    "project-management": "productivity",
    "research": "productivity",
    "sales": "productivity",
    "security": "security",
    "spatial-computing": "general",
    "specialized": "productivity",
    "support": "productivity",
    "testing": "testing",
}

# Fallback: infer the category from an agent's own text when a division is
# unmapped (none today) so the converter never crashes on new divisions.
def infer_category(text: str, division: str) -> str:
    if division in DIVISION_CATEGORY:
        return DIVISION_CATEGORY[division]
    lowered = text.lower()
    for cat, markers in {
        "security": ("threat", "vulnerab", "pentest", "siem", "compliance"),
        "testing": ("test", "qa", "e2e", "regression"),
        "devops": ("ci/cd", "kubernetes", "terraform", "infrastructure"),
        "ai-ml": ("machine learning", "llm", "model", "embedding"),
        "documentation": ("documentation", "docs", "technical writer"),
    }.items():
        if any(m in lowered for m in markers):
            return cat
    return "general"


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Split an agent file into (frontmatter dict, body)."""
    lines = raw.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, raw
    fm_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    # Minimal parser: name:, description:, color:, emoji:, vibe: scalars
    # (agency-agents files use only these keys).
    data: dict = {}
    key = None
    buf: list = []
    mode = "scalar"

    def flush():
        if key is None:
            return
        if mode == "block":
            data[key] = " ".join(p.strip() for p in buf).strip()
        else:
            data[key] = buf[0] if buf else ""

    for line in fm_lines:
        indented = line[:1] in (" ", "\t")
        s = line.strip()
        if mode == "block" and indented and s:
            buf.append(s)
            continue
        if indented or ":" not in s:
            continue
        flush()
        k, _, v = s.partition(":")
        key = k.strip()
        v = v.strip()
        if v in (">", ">-", ">+", "|", "|-", "|+"):
            mode, buf = "block", []
        else:
            mode, buf = "scalar", [v.strip("'\"")]
    flush()
    body_start = len(fm_lines) + 2
    body = "\n".join(lines[body_start:]).strip("\n")
    return data, body


def main() -> int:
    if not VENDOR.is_dir():
        print(f"ERROR: {VENDOR} not found", file=sys.stderr)
        return 2

    divisions_file = VENDOR / "divisions.json"
    divisions = json.loads(divisions_file.read_text(encoding="utf-8"))
    division_names = list(divisions["divisions"].keys())

    # Fresh output tree on every run (R304: rebuild from scratch).
    if OUT.exists():
        for child in OUT.iterdir():
            if child.is_dir():
                import shutil
                shutil.rmtree(child)
            else:
                child.unlink()

    manifest: dict[str, list] = {}
    seen_names: set[str] = set()
    converted = 0
    skipped: list[str] = []

    for division in sorted(division_names):
        div_dir = VENDOR / division
        if not div_dir.is_dir():
            continue
        entries = []
        for agent_file in sorted(div_dir.rglob("*.md")):
            raw = agent_file.read_text(encoding="utf-8", errors="replace")
            if not raw.startswith("---"):
                continue  # not a persona (playbooks/notes live elsewhere)
            fm, body = parse_frontmatter(raw)
            name = str(fm.get("name") or "").strip()
            if not name:
                skipped.append(str(agent_file.relative_to(VENDOR)))
                continue

            slug = agent_file.stem  # e.g. engineering-frontend-developer
            rel_div = agent_file.parent.relative_to(VENDOR).as_posix()
            skill_name = f"agency-{slug}"
            if skill_name in seen_names:
                # Slugs are unique upstream (CI check-slug-collisions); a
                # collision here means a stray duplicate - keep the first.
                skipped.append(str(agent_file.relative_to(VENDOR)))
                continue
            seen_names.add(skill_name)

            description = str(fm.get("description") or "").strip()
            vibe = str(fm.get("vibe") or "").strip()
            when = description if description else vibe
            category = infer_category(body, division)

            # Frontmatter per docs/SKILLS.md (name/category/description/
            # risk/tags/tools) + an x-origin block for provenance.
            lines = [
                "---",
                f"name: {skill_name}",
                f"category: {category}",
                f"description: >-",
            ]
            for chunk in _wrap(when or f"{name} persona from The Agency ({division} division)."):
                lines.append(f"  {chunk}")
            lines += [
                "risk: safe",
                "tags:",
                f"  - agency-agents",
                f"  - {division}",
                "tools:",
                "  - claude-code",
                "  - codex",
                "  - cursor",
                "  - gemini-cli",
                "  - opencode",
                "  - copilot",
                "  - windsurf",
                "  - kiro",
                f"x-origin-division: {division}",
                f"x-origin-file: {rel_div}/{agent_file.name}",
                "x-upstream: https://github.com/msitarzewski/agency-agents",
                "---",
                "",
                f"# {name}",
                "",
            ]
            if vibe:
                lines += [f"> {vibe}", ""]
            lines.append(f"Source persona: `agency-agents/{rel_div}/{agent_file.name}` (The Agency, MIT).")
            lines.append("")
            lines.append(body)

            out_dir = OUT / division / slug
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "SKILL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
            entries.append({
                "name": skill_name,
                "slug": slug,
                "display_name": name,
                "origin": f"{rel_div}/{agent_file.name}",
                "category": category,
            })
            converted += 1
        manifest[division] = entries

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(
        json.dumps({
            "description": (
                "Generated by scripts/convert_agency_agents.py from the vendored "
                "agency-agents personas. Do not edit by hand - regenerate instead."
            ),
            "total_agents": converted,
            "divisions": manifest,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Converted {converted} personas across {len(manifest)} divisions -> {OUT}")
    for division, entries in sorted(manifest.items()):
        print(f"  {division:20s} {len(entries):3d}")
    if skipped:
        print(f"Skipped {len(skipped)} files without usable frontmatter:")
        for s in skipped[:10]:
            print(f"  - {s}")
    return 0


def _wrap(text: str, width: int = 88) -> list[str]:
    """Word-wrap a description into frontmatter continuation chunks."""
    words = text.split()
    if not words:
        return [""]
    out: list[str] = []
    cur = ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


if __name__ == "__main__":
    sys.exit(main())
