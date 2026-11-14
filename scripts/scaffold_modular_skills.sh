#!/usr/bin/env bash
# Scaffold modular /skills/{category}/{slug}/ tree that points at the existing
# plugin-catalog content (manifest.json + SKILL.md). No data is duplicated:
# every entry is a symlink to ../../plugin-catalog/<cat>/<slug>/.
#
# Idempotent: re-running cleans stale symlinks and re-creates the tree.
#
# Run from repo root:   bash scripts/scaffold_modular_skills.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CATALOG="plugin-catalog"
SKILLS="skills"

if [[ ! -d "$CATALOG" ]]; then
  echo "ERROR: $CATALOG not found in $REPO_ROOT" >&2
  exit 1
fi

# 1. Reset skills tree (keep README.md / manifest.json produced separately)
find "$SKILLS" -mindepth 2 -type l -delete 2>/dev/null || true
for cat_dir in "$SKILLS"/*/; do
  [[ -d "$cat_dir" ]] || continue
  find "$cat_dir" -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null || true
done

# 2. Re-create symlinked plugin entries from catalog.json
python3 - <<'PY'
import json, os, pathlib, sys

repo = pathlib.Path.cwd()
catalog_path = repo / 'plugin-catalog' / 'catalog.json'
if not catalog_path.is_file():
    print(f"ERROR: {catalog_path} not found", file=sys.stderr); sys.exit(2)

catalog = json.loads(catalog_path.read_text())
skills_root = repo / 'skills'
created = 0
for entry in catalog['skills']:
    cat = entry['category']
    slug = entry['slug']
    target = repo / 'plugin-catalog' / cat / slug
    link = skills_root / cat / slug
    if not target.exists():
        print(f"WARN: source missing for {cat}/{slug}: {target}", file=sys.stderr)
        continue
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        link.unlink()
    # Use a REAL directory per plugin, with two symlinks inside:
    #   SKILL.md        -> ../../../plugin-catalog/<cat>/<slug>/SKILL.md
    #   manifest.json   -> ../../../plugin-catalog/<cat>/<slug>.json
    # This keeps the skills tree self-contained without polluting the source.
    link.mkdir(parents=True, exist_ok=True)
    for child in link.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
    skill_md = target / 'SKILL.md'
    if skill_md.is_file():
        (link / 'SKILL.md').symlink_to(os.path.relpath(skill_md, link))
    manifest_src = repo / 'plugin-catalog' / cat / f'{slug}.json'
    if manifest_src.is_file():
        (link / 'manifest.json').symlink_to(os.path.relpath(manifest_src, link))
    created += 1
print(f"OK: {created}/{len(catalog['skills'])} plugin dirs created under skills/")
PY

echo "DONE"
ls -la "$SKILLS"
for cat in code research tokens-optimization design multimedia-writing; do
  printf '%-22s -> ' "$cat"
  ls "$SKILLS/$cat" 2>/dev/null | tr '\n' ' '
  echo
done
