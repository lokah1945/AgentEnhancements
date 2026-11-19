#!/usr/bin/env python3
"""Generate skills/manifest.json (aggregator index) + skills/README.md +
skills/<cat>/README.md (one per category) by reading plugin-catalog/catalog.json.

Run from repo root:  python3 scripts/generate_skills_index.py
"""
from __future__ import annotations
import json
import pathlib
import re
import textwrap
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
CATALOG = REPO / "plugin-catalog" / "catalog.json"
SKILLS = REPO / "skills"

CAT_LABELS = {
    "code": "Code",
    "research": "Research",
    "tokens-optimization": "Tokens / Optimization",
    "design": "Design",
    "multimedia-writing": "Multimedia / Writing",
    "agency": "Agency Personas",
}

CAT_BLURBS = {
    "code": "Code-craft skills: TypeScript rigor, minimal-first ML, frontend perf, reverse-engineering clones.",
    "research": "Deep-research skills: knowledge graphs, multi-step reasoning, fresh-trend monitoring, Feynman-style explanation.",
    "tokens-optimization": "Token / context budget skills: compression, agile persona dispatch, atomic parallel execution.",
    "design": "Design skills: UI/UX tokens, visual polish, slide narrative, diagramming.",
    "multimedia-writing": "Multimedia + writing skills: office docs, video montage, talking-head avatars, AI-ism removal.",
    "agency": "AI-persona packs from The Agency (agency-agents): 283 specialist personas across 18 divisions plus the NEXUS orchestration playbooks.",
}


def _wrap_readme_line(line: str) -> list[str]:
    """Wrap prose while preserving Markdown list indentation and inline text."""
    marker = re.match(r"^(\s*(?:[-+*]|\d+\.)\s+)", line)
    prefix = marker[1] if marker else ""
    return textwrap.wrap(
        line[len(prefix):], width=80, initial_indent=prefix,
        subsequent_indent=" " * len(prefix), break_long_words=False,
        break_on_hyphens=False,
    ) or [""]


def _format_readme(lines: list[str]) -> str:
    """Keep concise tables; format wide rows as lossless labeled lists."""
    output: list[str] = []
    in_fence = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            in_fence = not in_fence
            output.append(line)
            index += 1
            continue
        if in_fence:
            if len(line) > 80 and "#" in line:
                prefix, comment = line.split("#", 1)
                continuation = ("│ " if "│" in prefix else "") + "# "
                output.extend(textwrap.wrap(
                    comment.strip(), width=80, initial_indent=prefix + "# ",
                    subsequent_indent=continuation, break_long_words=False,
                    break_on_hyphens=False,
                ))
            else:
                output.append(line)
            index += 1
            continue
        if (line.startswith("|") and index + 1 < len(lines)
                and re.fullmatch(r"[| :\-]+", lines[index + 1])):
            rows = [line, lines[index + 1]]
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                rows.append(lines[index])
                index += 1
            cells = [[cell.strip() for cell in row.strip("|").split("|")]
                     for row in rows]
            compact = ["| " + " | ".join(row) + " |" for row in cells]
            if max(map(len, compact)) <= 80:
                output.extend(compact)
            else:
                for row in cells[2:]:
                    if len(row) != len(cells[0]):
                        raise ValueError("generated README table column mismatch")
                    for column, (label, value) in enumerate(zip(cells[0], row)):
                        prefix = "- " if column == 0 else "  - "
                        output.extend(_wrap_readme_line(
                            f"{prefix}**{label}:** {value}"
                        ))
                    output.append("")
            continue
        if line or not output or output[-1]:
            output.extend(_wrap_readme_line(line))
        index += 1
    return "\n".join(output).rstrip() + "\n"


def main() -> None:
    catalog = json.loads(CATALOG.read_text())
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for entry in catalog["skills"]:
        by_cat[entry["category"]].append(entry)

    # --- skills/manifest.json ---
    agg = {
        "version": "1.0.0",
        "description": (
            "Modular skill tree index. Each entry is a self-contained "
            "directory under skills/<category>/<slug>/ containing SKILL.md + "
            "manifest.json. The tree is generated at install time "
            "(scripts/scaffold_modular_skills.sh) and is not committed."
        ),
        "total_plugins": len(catalog["skills"]),
        "categories": list(CAT_LABELS.keys()),
        "plugins": [
            {
                "id": e["id"],
                "slug": e["slug"],
                "name": e["name"],
                "category": e["category"],
                "status": e["status"],
                "vendored": e.get("vendored", False),
                "source_url": e["source_url"],
                "source_license": e.get("source_license", "UNKNOWN"),
                "path": f"skills/{e['category']}/{e['slug']}",
                "skill_md": f"skills/{e['category']}/{e['slug']}/SKILL.md",
                "manifest": f"skills/{e['category']}/{e['slug']}/manifest.json",
                "mcp_servers": e.get("mcp_servers", []),
                "trigger_keywords": e.get("trigger_keywords", []),
            }
            for e in catalog["skills"]
        ],
    }
    (SKILLS / "manifest.json").write_text(json.dumps(agg, indent=2, ensure_ascii=False) + "\n")

    # --- skills/README.md (top-level architecture index) ---
    lines = [
        "# AgentEnhancements — Modular Skills Tree",
        "",
        "Generated catalog-guide view for humans and agents. Plugin manifests",
        "and guides remain canonical under `plugin-catalog/`.",
        "",
        "## Layout",
        "",
        "```text",
        "skills/",
        "├── manifest.json                    # aggregator index (read this first)",
        f"├── README.md                        # this file",
    ]
    for cat in CAT_LABELS:
        lines.append(f"├── {cat}/")
        lines.append(f"│   ├── README.md                    # {CAT_LABELS[cat]} category overview")
        for e in by_cat[cat]:
            mark = " (vendored)" if e.get("vendored") else ""
            lines.append(f"│   └── {e['slug']}/                # {e['name']}{mark}")
    lines += [
        "```",
        "",
        "Every `skills/<cat>/<slug>/` directory is self-contained:",
        "",
        "| File             | Purpose                                                              |",
        "| ---------------- | -------------------------------------------------------------------- |",
        "| `SKILL.md`       | Agent-readable skill spec (YAML frontmatter + capabilities + workflow) |",
        "| `manifest.json`  | Machine-readable plugin manifest (id, version, MCP deps, triggers)  |",
        "",
        "The per-plugin directories are generated at install time (symlinks into",
        "`plugin-catalog/`, built by `bash scripts/scaffold_modular_skills.sh`);",
        "only this manifest, the READMEs, and the committed index are tracked in",
        "git. Refresh the index with `python3 scripts/generate_skills_index.py`.",
        "",
        "## Coverage",
        "",
        f"- **{len(catalog['skills'])} plugins** across **{len(CAT_LABELS)} categories**.",
        f"- **{sum(1 for e in catalog['skills'] if e.get('vendored'))} vendored** (source code copied into repo): "
        + ", ".join(e["slug"] for e in catalog["skills"] if e.get("vendored")) + ".",
        "- Implementation status (independent of vendored source): "
        + ", ".join(f"{status}: {count}" for status, count in
                    sorted(Counter(e["status"] for e in catalog["skills"]).items())) + ".",
        "- External runtimes require deliberate user installation and configuration.",
        "",
        "## Categories",
        "",
    ]
    for cat, label in CAT_LABELS.items():
        lines.append(f"### {label}  ·  `skills/{cat}/`")
        lines.append("")
        lines.append(CAT_BLURBS[cat])
        lines.append("")
        lines.append(f"Plugins ({len(by_cat[cat])}):")
        lines.append("")
        for e in by_cat[cat]:
            tag = e["status"] + ("; vendored source" if e.get("vendored") else "; external source")
            lines.append(
                f"- **{e['name']}** (`{e['slug']}`) — {tag} — "
                f"MCP: {', '.join(e.get('mcp_servers', []) or ['(none)'])}"
            )
        lines.append("")
    lines += [
        "## Integration with unified-integration",
        "",
        "`unified-integration/setup.sh` aggregates the vendored skill sources into",
        "`unified-integration/skills/all-skills.json`. Catalog guides are a separate",
        "surface in `agent-registry.json`; this modular tree does not install the",
        "external upstream runtimes. Implementation status and runtime readiness",
        "are separate dimensions (CONTRACT section 8.1).",
        "",
        "## See also",
        "",
        "- `plugin-catalog/catalog.json` — canonical catalog with upstream URLs",
        "- `plugin-catalog/mcp-servers.json` — MCP server roadmap (P0/P1/P2)",
        "- `unified-integration/skills/all-skills.json` — installed skill registry",
        "- `docs/MCP_INTEGRATION_CHECKLIST.md` — step-by-step MCP build plan",
        "- `README_INTEGRATION.md` — full architecture + merger narrative",
        "",
    ]
    (SKILLS / "README.md").write_text(_format_readme(lines))

    # --- skills/<cat>/README.md ---
    for cat, label in CAT_LABELS.items():
        entries = by_cat[cat]
        cat_lines = [
            f"# {label} Skills",
            "",
            CAT_BLURBS[cat],
            "",
            f"Plugins: **{len(entries)}**",
            "",
            "| Slug | Name | Status | MCP servers | Source |",
            "| --- | --- | --- | --- | --- |",
        ]
        for e in entries:
            status = e["status"]
            mcps = ", ".join(e.get("mcp_servers", []) or ["—"])
            src = e["source_url"].replace("https://github.com/", "")
            cat_lines.append(
                f"| [`{e['slug']}`](./{e['slug']}/) | {e['name']} | {status} | {mcps} | `{src}` |"
            )
        cat_lines += [
            "",
            "## Files in each plugin directory",
            "",
            "- `SKILL.md` — agent-readable skill spec",
            "- `manifest.json` — machine-readable manifest",
            "",
        ]
        (SKILLS / cat / "README.md").write_text(_format_readme(cat_lines))

    print(
        f"Wrote {SKILLS / 'manifest.json'} ({agg['total_plugins']} plugins), "
        f"{SKILLS / 'README.md'}, and {len(CAT_LABELS)} category READMEs."
    )


if __name__ == "__main__":
    main()
