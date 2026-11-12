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
from typing import Dict, List, Set, Tuple

EXPECTED_FIELDS: Set[str] = {
    "id", "name", "slug", "category", "version", "status", "source",
    "description", "capabilities", "tools_required", "mcp_servers_suggested",
    "trigger_keywords", "best_for", "integration_notes",
}
VALID_CATEGORIES: List[str] = [
    "code", "research", "tokens-optimization", "design", "multimedia-writing",
]
VALID_STATUS: Set[str] = {"to-integrate", "integrated", "integrated-ready", "deprecated"}
EXPECTED_PLUGINS: Dict[str, Set[str]] = {
    "code": {"mattpocock-skills", "karpathy-skills", "agent-skills-addyosmani", "replica-skill"},
    "research": {"graphify", "agent-reach", "understand-anything", "last-30-days", "rea"},
    "tokens-optimization": {"gstack", "caveman", "gsd", "bmad-method"},
    "design": {"ui-ux-pro-max", "impeccable", "ppt-master", "diagram-design"},
    "multimedia-writing": {"anthropic-skills", "openmontage", "hyperframes", "humanizer"},
}


def validate_category(
    root: Path, category: str, errors: List[str], warnings: List[str]
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
    return found


def validate_catalog_index(root: Path, errors: List[str]) -> int:
    """Validate plugin-catalog/catalog.json consistency with manifests."""
    index_path = root / "plugin-catalog" / "catalog.json"
    if not index_path.is_file():
        errors.append("catalog.json hilang: plugin-catalog/catalog.json")
        return 0
    data = json.loads(index_path.read_text(encoding="utf-8"))
    total = 0
    for entry in data.get("skills", []):
        total += 1
        manifest = root / entry["manifest_path"]
        if not manifest.is_file():
            errors.append(f"catalog.json: manifest tidak ada: {entry['manifest_path']}")
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
    found_total = 0
    for category in VALID_CATEGORIES:
        found = validate_category(root, category, errors, warnings)
        found_total += len(found)
        missing = EXPECTED_PLUGINS[category] - found
        if missing:
            errors.append(f"Plugin hilang di {category}/: {sorted(missing)}")

    index_total = validate_catalog_index(root, errors)
    expected_total = sum(len(v) for v in EXPECTED_PLUGINS.values())

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
