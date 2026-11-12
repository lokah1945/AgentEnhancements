---
slug: bmad-method
category: tokens-optimization
version: 1.0.0
status: integrated-ready
mcp_servers: [github-issues-mcp, linear-mcp, memory-mcp]
trigger_keywords: [bmad, persona, agile, story, scrum]
---

# BMAD Method

Breakthrough Method of Agile AI-Driven Developers: alur persona-driven (Analyst/Architect/PM/SM/Dev/QA) untuk membawa ide dari brief sampai kode siap-ship. Mengontrol token budget per persona.

## Kapan dipakai

- User minta "build product", "greenfield", "dari brief jadi kode"
- Epic kompleks butuh handoff PM → Dev → QA
- Ingin structure story dengan acceptance criteria eksplisit
- Multi-stakeholder: ada keputusan arsitektur, prioritas, dan eksekusi

## Prasyarat

- MCP: `github-issues-mcp`, `linear-mcp`, `memory-mcp`
- Tools: `bash`, `read_file`, `write_file`
- Akses ke skill lain sebagai "Act" per persona

## Capabilities

1. Persona orchestration — 6 persona (Analyst/Architect/PM/SM/Dev/QA) berurutan.
2. Story generation — user story + acceptance criteria + test plan.
3. Architecture-to-task mapping — pecah arsitektur jadi task list.
4. QA gate enforcement — QA persona bisa reject Dev output bila tidak sesuai acceptance.

## Workflow

1. **Analyst** — brief user → requirements doc (`docs/req/<slug>.md`).
2. **Architect** — requirements → architecture decision (`docs/adr/<slug>.md`).
3. **PM** — arsitektur → backlog stories (`docs/stories/<slug>.md`).
4. **SM** — backlog → sprint plan (prioritas + est).
5. **Dev** — sprint → kode + commit (per story).
6. **QA** — kode → test + verify acceptance criteria.
7. Setiap persona wajib log ke `unified-integration/memory/bmad/<run-id>/<persona>.md`.
8. Handoff persona wajib output artifact untuk persona berikutnya.

## Inputs

- Brief produk (narasi atau dokumen)
- Opsional: target sprint length (default 1 week)
- Opsional: tech stack constraint

## Outputs

- `requirements.md` — Analyst output
- `adr.md` — Architect output
- `stories.md` — PM output (list user story + AC)
- `sprint-plan.md` — SM output
- Source code (per story) — Dev output
- `qa-report.md` — QA output (pass/fail per AC)
- Audit trail di `unified-integration/memory/bmad/`

## Contoh

### Contoh 1 — Build SaaS MVP dari brief

Prompt: "Bangun MVP subscription tracker SaaS — React + Supabase."

```
Analyst:
  requirements: user can track subscription, get alert before renewal, 
  see monthly cost; MVP 3 fitur (track, alert, dashboard).
  
Architect:
  ADR: React 19 + Supabase + Vercel; cron via Vercel cron + edge fn;
  no Redis in MVP (pakai Supabase queue).
  
PM:
  stories:
    [S1] User can add subscription (AC: form nama+cost+ciclus, save to DB, list)
    [S2] User can see dashboard (AC: total monthly, breakdown per service)
    [S3] User get alert 3 days before renewal (AC: email + in-app notif)
    
SM:
  sprint plan: S1+ S2 sprint 1; S3 sprint 2 (dep: cron setup).
  
Dev:
  S1: implemented in 4 file (add-form.ts, save.ts, list.ts, schema.sql)
  S2: implemented (dashboard.ts, total.ts)
  
QA:
  S1: PASS — all AC verified (form save, list show)
  S2: PASS — total correct, breakdown render
  S3: pending (sprint 2)
```

### Contoh 2 — Refactor modul auth

Prompt: "Refactor auth: JWT → session-based, 3 sprint."

```
Analyst: security gap dengan JWT (revoke sulit); session lebih aman + scalable.
Architect: pakai Redis session store + httpOnly cookie; migration plan:
  - phase 1: dual-auth (JWT + session)
  - phase 2: migrate existing user
  - phase 3: drop JWT
PM: 3 story per phase (9 story total)
SM: 1 phase per sprint
Dev/QA: per story
```

### Contoh 3 — Onboarding bot baru

Prompt: "Bangun onboarding chatbot untuk karyawan baru, 2 minggu."

```
Analyst: bot jawab FAQ + onboarding checklist + integrasi HRIS.
Architect: GPT-4 + RAG handbook PDF + Slack bot via Bolt SDK.
PM: 5 story (faq- ingest, rag-query, checklist-track, hris-sync, slack-app).
SM: 2 sprint (3+2).
Dev/QA per story.
```

## Batasan & Keamanan

- Setiap persona punya token budget terpisah (default 30K per persona).
- Bila satu persona habis budget, eskalasi ke user (jangan silently truncate).
- QA bisa reject Dev output; Dev wajib fix sebelum lanjut.
- Tidak skip persona; bila user minta skip, tanya alasan (audit trail).

## Catatan integrasi

- BMAD jadi orchestrator default untuk mode "build".
- Setelah BMAD selesai decomposition, `gsd` eksekusi atomic task.
- Untuk greenfield kecil, BMAD bisa selesai 1 sesi; untuk besar, pecah per sprint.
- Memory lintas persona wajib shared via `memory-mcp` (satu project state).
