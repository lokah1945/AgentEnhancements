---
title: Changelog
version: 1.1
last_updated: 2026-11-13
audience: all
---

# Changelog

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
