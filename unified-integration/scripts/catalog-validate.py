#!/usr/bin/env python3
"""Validate the plugin-catalog manifests and integration guides.

Checks that every plugin category contains the expected manifests, that each
manifest carries the required fields, that a SKILL.md guide exists next to it,
and that referenced paths actually resolve inside the repository.

Usage:
    python3 unified-integration/scripts/catalog-validate.py [--root <repo-root>] [--strict]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

EXPECTED_FIELDS: Set[str] = {
    "id", "name", "slug", "category", "version", "status", "source",
    "description", "capabilities", "tools_required", "mcp_servers_suggested",
    "trigger_keywords", "best_for", "integration_notes",
}
VALID_CATEGORIES: List[str] = [
    "code", "research", "tokens-optimization", "design", "multimedia-writing",
    "agency",
]
VALID_STATUS: Set[str] = {"to-integrate", "integrated", "integrated-ready", "deprecated"}
EXPECTED_PLUGINS: Dict[str, Set[str]] = {
    "code": {"mattpocock-skills", "karpathy-skills", "agent-skills-addyosmani", "replica-skill"},
    "research": {"graphify", "agent-reach", "understand-anything", "last-30-days", "rea"},
    "tokens-optimization": {"gstack", "caveman", "gsd", "bmad-method"},
    "design": {"ui-ux-pro-max", "impeccable", "ppt-master", "diagram-design"},
    "multimedia-writing": {"anthropic-skills", "openmontage", "hyperframes", "humanizer"},
    "agency": {
        "academic", "design", "engineering", "finance", "game-development",
        "gis", "healthcare", "marketing", "paid-media", "product",
        "project-management", "research", "sales", "security",
        "spatial-computing", "specialized", "support", "testing", "nexus",
    },
}


def load_roadmap_ids(root: Path) -> Set[str]:
    """Read the canonical MCP server ids from plugin-catalog/mcp-servers.json."""
    roadmap = root / "plugin-catalog" / "mcp-servers.json"
    if not roadmap.is_file():
        return set()
    try:
        data = json.loads(roadmap.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {server.get("id") for server in data.get("servers", []) if server.get("id")}


def validate_category(
    root: Path, category: str, errors: List[str], warnings: List[str],
    roadmap_ids: Set[str] = frozenset(),
) -> Set[str]:
    """Validate one catalog category directory; return slugs found."""
    found: Set[str] = set()
    cat_dir = root / "plugin-catalog" / category
    if not cat_dir.is_dir():
        errors.append(f"Kategori hilang: plugin-catalog/{category}/")
        return found
    for json_path in sorted(cat_dir.glob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON error di {json_path}: {exc}")
            continue
        missing = EXPECTED_FIELDS - data.keys()
        if missing:
            errors.append(f"{json_path.name}: field hilang {sorted(missing)}")
        if data.get("category") != category:
            errors.append(
                f"{json_path.name}: category mismatch "
                f"(got {data.get('category')}, expect {category})"
            )
        if data.get("status") not in VALID_STATUS:
            errors.append(f"{json_path.name}: status '{data.get('status')}' tidak valid")
        if not data.get("capabilities"):
            warnings.append(f"{json_path.name}: capabilities kosong")
        if not data.get("mcp_servers_suggested"):
            warnings.append(f"{json_path.name}: mcp_servers_suggested kosong")
        # Suggested MCP servers must exist in the roadmap catalog
        for server_id in data.get("mcp_servers_suggested", []):
            if roadmap_ids and server_id not in roadmap_ids:
                errors.append(
                    f"{json_path.name}: mcp_servers_suggested '{server_id}' "
                    f"tidak ada di plugin-catalog/mcp-servers.json"
                )
        slug = data.get("slug", json_path.stem)
        found.add(slug)
        guide = cat_dir / slug / "SKILL.md"
        if not guide.is_file():
            warnings.append(f"SKILL.md hilang: plugin-catalog/{category}/{slug}/SKILL.md")
        # Validate referenced paths exist
        for sf in data.get("skill_files", []):
            ref = root / sf["path"]
            if not ref.exists():
                errors.append(f"{json_path.name}: referensi path tidak ada: {sf['path']}")
        # sub_skills with an explicit path must point at a real file
        for sub in data.get("sub_skills", []):
            sub_path = sub.get("path")
            if sub_path and not (root / sub_path).is_file():
                errors.append(
                    f"{json_path.name}: sub_skill '{sub.get('slug')}' "
                    f"path tidak ada: {sub_path}"
                )
    return found


def validate_catalog_index(root: Path, errors: List[str],
                           roadmap_ids: Set[str] = frozenset(),
                           index_keys: Optional[Set[Tuple[str, str]]] = None) -> int:
    """Validate plugin-catalog/catalog.json consistency with manifests.

    Returns the number of index entries. When ``index_keys`` is given it
    is filled with the ``(category, slug)`` pair of every index entry so
    the caller can check the manifest -> index direction as well.
    """
    index_path = root / "plugin-catalog" / "catalog.json"
    if not index_path.is_file():
        errors.append("catalog.json hilang: plugin-catalog/catalog.json")
        return 0
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"catalog.json tidak valid: {exc}")
        return 0
    total = 0
    skills = data.get("skills", [])
    if data.get("total_plugins") != len(skills):
        errors.append(
            f"catalog.json: total_plugins {data.get('total_plugins')} "
            f"!= {len(skills)} entries"
        )
    for entry in skills:
        total += 1
        if index_keys is not None:
            index_keys.add((entry.get("category"), entry.get("slug")))
        manifest = root / entry["manifest_path"]
        if not manifest.is_file():
            errors.append(f"catalog.json: manifest tidak ada: {entry['manifest_path']}")
            continue
        # Index MCP refs must match the roadmap and the source manifest
        for server_id in entry.get("mcp_servers", []):
            if roadmap_ids and server_id not in roadmap_ids:
                errors.append(
                    f"catalog.json[{entry.get('id')}]: mcp_servers "
                    f"'{server_id}' tidak ada di mcp-servers.json"
                )
        try:
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if set(entry.get("mcp_servers", [])) != set(
            manifest_data.get("mcp_servers_suggested", [])
        ):
            errors.append(
                f"catalog.json[{entry.get('id')}]: mcp_servers tidak sinkron "
                f"dengan manifest {entry['manifest_path']}"
            )
    return total


def main() -> int:
    """Entry point: parse args, run validation, print report."""
    parser = argparse.ArgumentParser(description="Validate plugin-catalog")
    parser.add_argument("--root", default=".", help="repo root")
    parser.add_argument("--strict", action="store_true", help="fail on warnings")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    errors: List[str] = []
    warnings: List[str] = []
    roadmap_ids = load_roadmap_ids(root)
    found_total = 0
    all_found: Set[Tuple[str, str]] = set()
    for category in VALID_CATEGORIES:
        found = validate_category(root, category, errors, warnings, roadmap_ids)
        found_total += len(found)
        all_found.update((category, slug) for slug in found)
        missing = EXPECTED_PLUGINS[category] - found
        if missing:
            errors.append(f"Plugin hilang di {category}/: {sorted(missing)}")

    index_keys: Set[Tuple[str, str]] = set()
    index_total = validate_catalog_index(root, errors, roadmap_ids, index_keys)
    expected_total = sum(len(v) for v in EXPECTED_PLUGINS.values())
    # registry.load_plugin_entries reads only catalog.json, so a manifest
    # absent from the index silently vanishes from search/map/preflight.
    for category, slug in sorted(all_found - index_keys):
        errors.append(f"catalog.json: manifest {category}/{slug} tidak terdaftar di index")
    for category, slug in sorted(index_keys - all_found, key=str):
        errors.append(f"catalog.json: entry {category}/{slug} tanpa manifest kategori")
    if index_total != expected_total:
        errors.append(f"catalog.json: {index_total} entries, expect {expected_total}")

    print("=" * 60)
    print("VALIDATION REPORT - AgentEnhancements plugin-catalog")
    print("=" * 60)
    print(f"Plugin manifests found : {found_total}/{expected_total}")
    print(f"Catalog index entries  : {index_total}/{expected_total}")
    print(f"Errors                 : {len(errors)}")
    print(f"Warnings               : {len(warnings)}")
    if errors:
        print("\n--- ERRORS ---")
        for err in errors:
            print(f"  {err}")
    if warnings:
        print("\n--- WARNINGS ---")
        for warn in warnings:
            print(f"  {warn}")
    if not errors and not warnings:
        print("\nALL CHECKS PASSED")
    elif not errors and warnings and not args.strict:
        print("\nPASS (with warnings - not strict)")
    print("=" * 60)
    return 0 if not errors and (not args.strict or not warnings) else 1


if __name__ == "__main__":
    sys.exit(main())
