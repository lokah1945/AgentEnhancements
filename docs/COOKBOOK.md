---
title: Plugin Catalog Cookbook
version: 1.0
last_updated: 2026-11-13
audience: all agents
---

# Cookbook — 11 Resep Gabungan Plugin

Resep siap pakai untuk skenario umum. Setiap resep = 2-4 skill yang dirangkai.
Semua skill dirujuk via `plugin-catalog/` atau registry agregasi.

## Resep 1 — Research ke Deck

**Skenario**: "Riset kompetitor X lalu buat deck 8 slide."

1. `rea` — orchestrate (3 hipotesis)
2. `agent-reach` — deep research (sub-query paralel)
3. `last-30-days` — window 30 hari untuk update terbaru
4. `ppt-master` — render deck

Output: `download/research/competitor-*.md` + `download/decks/strategy-*.pptx`

## Resep 2 — Build SaaS MVP dari brief

**Skenario**: "Bangun MVP dari brief 1 paragraf."

1. `bmad-method` — 6 persona pipeline (Analyst ke QA)
2. `mattpocock-skills` — Dev persona untuk TS code
3. `agent-skills-addyosmani` — QA perf + a11y
4. `impeccable` — polish UI

## Resep 3 — Knowledge graph dari paper

**Skenario**: "Buat knowledge graph dari 5 paper AI agent terbaru."

1. `last-30-days` — find 5 recent paper
2. `agent-reach` — fetch full text
3. `graphify` — extract entities + relations
4. `diagram-design` — visualisasi graph

## Resep 4 — Personalized sales video (dengan consent)

**Skenario**: "Personalized video untuk 10 prospect."

1. `agent-reach` — riset tiap prospect
2. `humanizer` — naturalize script
3. `hyperframes` — generate video (WAJIB `consent-gate.sh` dulu)
4. `openmontage` — montase jadi demo reel

## Resep 5 — Token budget optimization

**Skenario**: "Sesi agent sudah 150K token."

1. `gstack` — kompres konteks history (target -50%)
2. `caveman` — kompres instruksi (target -70%)
3. `gstack` — enable response cache

## Resep 6 — A11y audit + fix

1. `agent-skills-addyosmani` — Lighthouse + pa11y
2. `ui-ux-pro-max` — palette a11y
3. `impeccable` — polish visual
4. `humanizer` — naturalize alt-text & ARIA label

## Resep 7 — Clone aplikasi end-to-end (BARU)

**Skenario**: "Clone aplikasi scheduling seperti Calendly, tapi flat pricing."

Pipeline replica-skill penuh (11 langkah berurutan):

```
replica-recon https://target-app.com       # screens, flows, data model
replica-architect                          # Next.js + Postgres + Stripe
replica-design                             # tokens dari screenshot
replica-build                              # screen-by-screen
replica-backend                            # auth + payments
replica-test                               # Playwright + bug report
replica-diff                               # parity score vs original
replica-entrepreneur                       # keluhan user -> fix plan
replica-brand                              # nama baru + sweep
replica-launch                             # landing + pricing + listing
replica-deploy                             # preflight + ship
```

Output: aplikasi clone lengkap di `replica/` + production deployment.
**Catatan**: hanya fitur & alur (clean-room); `sweep.py` memblokir deploy
selama masih ada jejak original.

## Resep 8 — Analisis kompetitor cepat (recon saja)

**Skenario**: "Bagaimana permission system Notion bekerja?"

1. `replica-recon` saja (scope: permissions) — screen inventory, flows, data model
2. `diagram-design` — visualisasi alur permission

Tidak lanjut build; output = peta analitis.

## Resep 9 — Validasi ide sebelum build

**Skenario**: "Should I clone per-seat SaaS ini?"

1. `replica-entrepreneur` pada target app — keluhan user dengan count + link
2. `last-30-days` — tren pricing kompetitor
3. Keputusan: layak / tidak layak, dengan angle positioning

## Resep 10 — Lecture materi dari PDF

1. `anthropic-skills` — document QA
2. `understand-anything` — prerequisite graph
3. `ppt-master` — render slide + notes
4. `humanizer` — naturalize notes

## Resep 11 — Backlog clearing

1. `gsd` — pecah ke atomic task (parallel 3)
2. per task: `mattpocock-skills` / `karpathy-skills` / `agent-skills-addyosmani`
3. `impeccable` — QA visual bila ada UI change
4. `humanizer` — naturalize commit message

## Tips

- Selalu `dispatch.sh --dry-run` dulu untuk lihat rencana.
- Operasi sensitif: `consent-gate.sh` sebelum invoke hyperframes.
- Sesi panjang: `gstack` tiap kali context > 75% budget.
- Greenfield: mulai dari `bmad-method`; clone app: mulai dari `replica-recon`.
- Investigasi bug: mulai dari `rea`.
