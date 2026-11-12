---
title: Changelog
version: 1.1
last_updated: 2026-11-13
audience: all
---

# Changelog

All notable changes to the owned integration layer of this repository.
Vendored projects change upstream; see their own histories.

## [Unreleased] — 2026-11-13 — anthropic-skills all-in-one integration

### Added
- **anthropic-skills vendored** (19 official Anthropic skills: docx, pdf,
  pptx, xlsx, skill-creator, mcp-builder, webapp-testing, claude-api,
  design & comms; Apache-2.0 per-skill LICENSE.txt). Aggregated through
  the standard pipeline, processed last so official copies win the 13
  name collisions with third-party versions in agentic-awesome-skills.
- **Capability registry** (`scripts/registry.py` + committed
  `skills/agent-registry.json`): one queryable index across skills,
  21 catalog plugins, 38 MCP roadmap servers and 7 built-in capabilities.
  `map "<task>"` returns an activation plan; scoring handles EN/ID stop
  words and format-family aliases (word->docx, excel->xlsx,
  powerpoint->pptx). Rebuilt automatically by `setup.sh`.
- **Native runtime activation** (`scripts/link-skills.sh`): `setup.sh`
  now symlinks the curated set (anthropic-skills 19 + replica-skill 11)
  into `~/.claude/skills/` and `~/.agents/skills/`, so every Agent Skills
  compatible harness discovers them automatically after ONE install.
  Ownership-safe (`--set`/`--all`/names/`--status`/`--unlink`); user data
  is never touched.
- **Dispatch routing** for the official skills: mcp server, skill
  creation, webapp testing, claude api and document formats (docx, pdf,
  pptx, xlsx incl. Indonesian phrasings) resolve to the vendored SKILL.md.
- 28 new tests (77 total): registry unit+CLI, native linking in an
  isolated HOME, dispatch routing table.

### Fixed
- **Index frontmatter parsing**: YAML block scalars (`>-`) left 64 skills
  with a literal marker as their description (and one empty). The index
  builder now re-parses frontmatter from the file (PyYAML or built-in
  parser): 0 placeholders, 0 empty descriptions.
- **Index duplicates**: the index kept one entry per (source, name) - the
  13 colliding Anthropic names appeared twice and agentic-awesome-skills
  carried 39 internal duplicates. The index is now keyed by name (later
  source wins, mirroring the directory overwrite): 3,146 raw records
  collapse to 3,094 unique skills.
- **Catalog accuracy**: the anthropic-skills manifest described an
  abstract "structured output / tool use / multimodal" set that never
  matched upstream; rewritten for the real content, status `integrated`,
  `vendored: true` with `vendored_path`.

### Changed
- Index schema (additive, v1.0 -> v1.1): new `path` and `source_path`
  fields per skill for capability mapping; `sources` list derived from
  records instead of hardcoded.
- `AGENT_SKILLS_NATIVE_TARGETS` env var (colon-separated link targets).
- Agent instruction files now advertise native activation and the
  registry mapper.

## [Unreleased] — 2026-11-13 — Production readiness

### Fixed
- **Merge**: `audit/deep-review` remediation (13 commits) merged into the
  master line; master had continued on the broken pipeline (all 21 findings
  of the 2026-11-01 audit were still live). Conflicts resolved to keep both
  the fixes and the plugin-catalog/replica-skill features.
- **Codex activation was a no-op**: setup wrote `~/.codex/config.yaml`,
  which Codex never reads. Setup now writes a marker-guarded integration
  section into `~/.codex/AGENTS.md` (Codex's real instruction channel) and
  removes the stale YAML (signature-checked).
- **OpenCode activation was a no-op**: setup wrote `config.json` with
  fictional keys; OpenCode only reads `opencode.json` per its official
  schema. Setup now merges a schema-valid `opencode.json`
  (`instructions` + `skills` arrays) plus a marker-guarded `AGENTS.md`.
- **Cursor**: no longer pollutes the real `~/.cursor/settings.json` with
  fictional keys; writes `~/.cursor/rules/agent-enhancements.mdc` instead.
- **Windsurf**: writes `~/.codeium/windsurf/rules/agent-enhancements.md`
  (Windsurf never read `~/.windsurf/config.yaml`).
- **Gemini CLI**: activation now also writes `~/.gemini/GEMINI.md` (the
  hierarchical global context file), not just the reference YAML.
- **README install instructions**: one-liner now points at
  `AgentEnhancements/master` (was `agent-enhancements/main` - 404).

### Changed
- **Plugin catalog URLs**: 13 manifests + `catalog.json` + category READMEs
  updated with verified repository URLs (12 org-root-only placeholders, 3
  typos: `heygen-con`→`heygen-com`, `Egomex-AI`→`Egonex-AI`,
  `marloto/REA`→`morluto/rea`).
- **Unified index regenerated**: 3,127 skills from 5 sources
  (replica-skill now included); prompt files refreshed from the vendored
  collection; memory-hook files synced with the generator (trailing
  newline).
- **`.gitignore`**: generated registry trees (`by-agent/`,
  `by-category/*` except the committed flat samples) ignored so a setup
  run no longer dirties `git status`.

### Added
- `docs/audit/PRODUCTION_READINESS_AUDIT.md` - end-to-end audit report
  (19 findings: 3 critical, 5 high, 6 medium, 5 low; all fixable ones
  remediated).
- `merge_agents_md` helper in `setup.sh`: marker-guarded, idempotent
  merging of instruction files (user content preserved across re-runs).

## [Unreleased] — 2026-11-13 — Plugin Catalog + Replica Skill

### Added

- **replica-skill/** (vendored, MIT, by Jake Schincariol): 11 skill clone-app
  clean-room — recon, architect, design, build, backend, test, diff,
  entrepreneur, brand, launch, deploy. Terdaftar di pipeline agregasi
  `setup.sh` (source "replica-skill") dan `update-skills.sh`.
- **plugin-catalog/**: katalog 21 plugin sources (5 kategori):
  - code (4): mattpocock-skills, karpathy-skills, agent-skills-addyosmani,
    replica-skill
  - research (5): graphify, agent-reach, understand-anything, last-30-days, rea
  - tokens-optimization (4): gstack, caveman, gsd, bmad-method
  - design (4): ui-ux-pro-max, impeccable, ppt-master, diagram-design
  - multimedia-writing (4): anthropic-skills, openmontage, hyperframes,
    humanizer
  - `catalog.json` — index katalog (terpisah dari unified index, patuh R304)
  - `mcp-servers.json` — roadmap 38 MCP server (4 P0, 20 P1, 14 P2)
  - 21 manifest JSON + 21 SKILL.md panduan integrasi
- **unified-integration/scripts/** (7 script baru):
  - `catalog-validate.py` — validasi manifest + guide + path reference
  - `catalog-wire.sh` — symlink guide katalog ke skills/by-category/
  - `catalog-test.sh` — smoke test per plugin
  - `mcp-test.sh` — smoke test MCP per priority/plugin/server
  - `consent-gate.sh` — consent gate voice clone (UU PDP 22-23, GDPR Art 9)
  - `audit-trail.sh` — audit log (mcp-call / video / decision)
  - `dispatch.sh` — orchestrator dispatcher (heuristic + override)
- **unified-integration/prompts/consolidated-system-prompt.txt**: filosofi
  Karpathy (minimal) + Anthropic (safe) + GSD (atomic).
- **docs/**: QUICKSTART.md, COOKBOOK.md (11 resep), SAFETY.md, ADR.md (8 ADR),
  MCP_SERVERS.md, LICENSE_AUDIT.md, ROUTER_POLICY.md, INTEGRATION_CHECKLIST.md.

### Changed

- `unified-integration/setup.sh`: aggregate_skills menambahkan source
  "replica-skill" (11 sub-skill masuk unified index otomatis).
- `unified-integration/update-skills.sh`: replica-skill ditambahkan ke daftar
  repo update.
- `README.md`: section Plugin Catalog + Replica Skill + diagram arsitektur
  diperbarui.

### Compliance (CONTRACT.md v2.1)

- R001: tidak ada file *-fixed/*-new/*-v2 (patch di-rename: consolidated-system-prompt.txt)
- R002: semua dokumentasi di docs/ dengan frontmatter (title, version,
  last_updated, audience)
- 2.1: single setup script dipertahankan (wiring via catalog-wire.sh, bukan setup.sh baru)
- R304: unified index all-skills.json TIDAK diedit manual — hanya via pipeline
- 2.2: .cursorrules manual TIDAK ditambahkan — rules masuk shared prompt source
- R201/R202: conventional commits, satu perubahan logis per commit
- R205/R206: setiap commit menyertakan Agent/Session/Task/Context metadata
- ECC tests: 819/819 pass saat integrasi

### Verified

- replica-skill LICENSE (MIT) terverifikasi dan ter-vendor utuh
- catalog-validate.py: 21/21 plugin valid
- catalog-wire.sh: 21 guide ter-wire
- catalog-test.sh replica-skill: PASS
- dispatch.sh --dry-run: classify benar (clone app → replica-skill)


All notable changes to the owned integration layer of this repository.
Vendored projects change upstream; see their own histories.

## [2.1.1] - 2026-11-01 - Audit remediation

### Fixed
- **setup.sh aborts on the first aggregated skill** - bash arithmetic
  post-increment from zero returns exit status 1 under `set -e`, so
  skills aggregation could never complete (audit F-25).
- **setup.sh only worked from `/root/agent-enhancements`** - the install
  root is now derived from the script location; `AGENT_ENHANCEMENTS_BASE_DIR`
  still overrides it (F-24). `update-skills.sh` behaves the same.
- **setup.sh aborts when `cargo` is missing** - headroom build failures now
  degrade to the fallback compression instead of killing the script (F-27).
- **Per-agent prompts were never found** - prompt globs require
  `shopt -s globstar` (now enabled with `nullglob`); added the missing Kiro
  prompt case (F-05).
- **Skills aggregation duplicated/nested directories on every re-run** -
  targets are now removed before copying; re-running `setup.sh` is
  idempotent (F-04).
- **Code injection via SKILL.md metadata** - frontmatter values were spliced
  into `python3 -c` source; they now travel through a record file, and the
  index is built in a single pass (F-02, F-19).
- **SQL injection in memory hooks** - all eight bash hooks built SQL by
  string interpolation (R101 violation). They are now thin wrappers over
  the Python hooks (parameterized SQL); Python hooks added for the agents
  that lacked them (F-01).
- **Wrong argument mapping in Claude Code hook commands** - tool input was
  stored as the memory *type*; commands now pass key/value/type correctly
  and produce valid JSON (no invalid `\$` escapes) (F-10).
- **`compress.py` NameError** - `re` was used but never imported (F-03).
- **`compress.sh` consumed stdin during content detection** - stdin is
  captured once into a temp file; script is self-locating and honors
  `AGENT_ENHANCEMENTS_BASE_DIR` (F-08).
- **`launch-agent.sh` ignored environment overrides** - stale committed
  copy replaced with the generator version: `set -euo pipefail`, self-locating
  paths, env overrides (F-06).
- **`load-skills.py` hardcoded the skills directory** - honors
  `AGENT_SKILLS_DIR`, defaults inside the repo, and loads both directory
  and flat skill layouts; missing PyYAML degrades gracefully (F-09, F-21).
- **`memory.py` exited 0 for missing memories on load** - now exits 1,
  matching the hooks (F-12).
- **Expired memories were cleaned up ~a day late** - `expires_at` now uses
  the SQLite timestamp format so comparisons against `datetime('now')`
  work (F-26).
- **`update-skills.sh` always reported "Already up to date"** - compares
  against `FETCH_HEAD` instead of the usually-unset `origin/HEAD`; one
  failing source no longer aborts the whole update (F-15, F-16).
- **Corrupted glyph in the generated skills README** (F-11).
- **README install instructions** - one-line installer pointed at the wrong
  repository name and branch (`agent-enhancements/main`); `cd` path fixed;
  skill counts aligned with the index (F-13).

### Changed
- `all-skills.json` regenerated with the fixed pipeline (2,884 → 3,116
  skills; schema now includes `agent_skill_counts`).
- `by-agent/` is populated only for the eight canonical agents; unknown
  `tools:` values remain in the index but no longer create directories.
- `memory/config.yaml` plugin paths use `${AGENT_ENHANCEMENTS_BASE_DIR}`
  references instead of hardcoded `/root` paths (R003).
- `merge_json_config`/`merge_yaml_config` pass payloads via environment
  variables instead of Python string literals (escapes and paths with
  quotes now survive).

### Added
- Regression test suite: `unified-integration/tests/` (49 tests) covering
  compression, memory, the loader, hooks, index invariants, generator/artifact
  sync and setup policy checks.
- CI workflow (`.github/workflows/ci.yml`) implementing CONTRACT §9.1:
  syntax checks, JSON validity, filename policy, commit policy (advisory),
  both test suites and advisory markdownlint.
- Documentation set completed per CONTRACT §7.2: ARCHITECTURE, API,
  CONFIGURATION, SKILLS, AGENTS, TROUBLESHOOTING, CONTRIBUTING, CHANGELOG.
- `.gitignore` for machine-local state and temp artifacts.

### Removed
- Committed temp file `.claude/settings.local.json.tmp.898491.d5c14c07c983`.

## [2.1.0] - 2026-11-01

- Agent traceability rules R205-R208 added to the contract; project renamed
  to AgentEnhancements.

## [2.0.0] - 2026-11-01

- Initial contract, replaces ad-hoc rules.

## [1.0.0] - 2026-10-15

- Implicit conventions, later formalized.
