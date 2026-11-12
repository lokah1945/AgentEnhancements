---
title: Integration Checklist
version: 1.1
last_updated: 2026-11-13
audience: all agents and contributors
---

# Integration Checklist — Plugin Catalog + Replica Skill

Checklist untuk wiring penuh. Centang tiap item sebelum lanjut fase berikut.

Legenda: [ ] belum · [x] selesai · [~] partial · [!] blocked

## FASE 0 — Bootstrap (SELESAI)

- [x] Struktur `plugin-catalog/{code,research,tokens-optimization,design,multimedia-writing}`
- [x] 21 manifest JSON (20 remote + 1 vendored replica-skill)
- [x] 21 SKILL.md panduan integrasi (replica-skill termasuk)
- [x] `plugin-catalog/catalog.json` index (21 plugin, terpisah dari unified index)
- [x] `plugin-catalog/mcp-servers.json` roadmap (38 server, replica-skill terdaftar)
- [x] `unified-integration/prompts/consolidated-system-prompt.txt`
- [x] Docs: QUICKSTART, COOKBOOK, SAFETY, ADR, MCP_SERVERS, LICENSE_AUDIT, ROUTER_POLICY, CHANGELOG
- [x] Scripts: catalog-validate.py, catalog-wire.sh, catalog-test.sh, mcp-test.sh, consent-gate.sh, audit-trail.sh, dispatch.sh
- [x] replica-skill vendored di `replica-skill/` (MIT, LICENSE asli)
- [x] replica-skill terdaftar di pipeline agregasi setup.sh + update-skills.sh
- [x] CONTRACT.md compliance: tanpa file *-v2/*-fixed, docs di docs/, tanpa setup.sh duplikat, unified index tidak disentuh manual

## FASE 1 — MCP Layer

- [ ] Install 4 MCP P0 (filesystem, memory, brave-search, browser-tools)
- [ ] Set env API key (BRAVE_API_KEY dll.)
- [ ] `bash unified-integration/scripts/mcp-test.sh --priority P0` semua hijau
- [ ] Build MCP custom bila diperlukan (task-router, embeddings, ffmpeg, dst.)

## FASE 2 — Registry & Wiring

- [x] `bash unified-integration/scripts/catalog-wire.sh` (21 guide ter-symlink)
- [ ] Jalankan `unified-integration/setup.sh` untuk agregasi penuh — verify:
  - [ ] 11 sub-skill replica muncul di `unified-integration/skills/by-category/general/`
  - [ ] unified index (all-skills.json) bertambah 11 entri source "replica-skill"
  - [ ] total_skills bertambah dari 2884 ke 2895
- [ ] `bash unified-integration/scripts/catalog-test.sh <slug>` pass untuk 21 plugin
- [ ] `python3 unified-integration/scripts/catalog-validate.py --root .` ALL PASSED

## FASE 3 — Orchestrator Activation

- [x] dispatch.sh jalan dengan heuristic + override `[skill:X]`
- [ ] Test end-to-end:
  - [ ] "clone app X" → replica-skill → replica-recon jalan
  - [ ] "riset kompetitor + deck" → rea → agent-reach → ppt-master
  - [ ] "build MVP" → bmad-method → plugin per persona
  - [ ] "clear backlog" → gsd → plugin per task

## FASE 4 — Memory & Compression

- [ ] Integrasi claude-mem hooks dengan audit-trail decisions
- [ ] headroom compression trigger 75% aktif
- [ ] gstack cache layer (saat plugin di-wire penuh)

## FASE 5 — Multimedia & Safety

- [x] consent-gate.sh jalan (exit code + audit log benar)
- [x] audit-trail.sh jalan (3 tipe log)
- [ ] Test consent gate dengan skenario real
- [ ] Cross-border disclosure untuk HeyGen/ElevenLabs

## FASE 6 — QA & Release

- [x] ECC tests pass (819/819 saat integrasi)
- [x] Docs lengkap + frontmatter (CONTRACT 7.3)
- [ ] License audit 20 plugin remote (TODO di docs/LICENSE_AUDIT.md)
- [ ] Tag release setelah Fase 1-3 selesai

## Blockers & Risiko

- [ ] 20 plugin remote belum diverifikasi license-nya (belum di-vendor, belum urgent)
- [ ] update-skills.sh tidak bisa git-pull replica-skill (bukan git repo setelah
      vendoring) — update manual via re-vendor; pertimbangkan konversi ke remote
      tracking bila upstream sering berubah
- [ ] API key budget untuk MCP P1 (estimasi $50-200/bln)

## Next Actions

1. Jalankan `unified-integration/setup.sh` untuk agregasi (verify 11 skill replica masuk).
2. Install MCP P0 + set API key.
3. Test dispatch: `bash unified-integration/scripts/dispatch.sh --dry-run "clone app X"`.
