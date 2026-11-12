---
slug: gsd
category: tokens-optimization
version: 1.0.0
status: integrated-ready
mcp_servers: [task-router-mcp, memory-mcp]
trigger_keywords: [gsd, get shit done, atomic, parallel, checklist]
---

# GSD (Get Shit Done)

Eksekusi cepat: pecah tugas besar menjadi checklist atomic, jalankan tiap item dengan sub-agent, lalu laporkan. Mengoptimalkan untuk throughput, bukan elaborasi.

## Kapan dipakai

- User minta "kerjakan semua", "selesaikan", "do X" tanpa banyak narasi
- Backlog clearing, migration tasks, batch refactor
- Tugas terstruktur dengan banyak item independen

## Prasyarat

- MCP: `task-router-mcp`, `memory-mcp`
- Tools: `task` tool (sub-agent dispatch), `bash`, `read_file`, `write_file`
- Akses ke skill lain sebagai "Act" handler

## Capabilities

1. Task decomposition — pecah ke item ≤ 5 menit per sub-agent.
2. Parallel sub-agent dispatch — item independen jalan serentak.
3. Atomic checklist generation — checklist dengan ID, dependency, est time.
4. Progress telemetry — track completion % dan ETA.

## Workflow

1. **Parse user intent** → output: 1 kalimat goal.
2. **Decompose** → tulis checklist: `[<id>] <desc> (est <min>min, dep: <id>)`.
3. **Topological sort** → identifikasi item yang bisa parallel.
4. **Dispatch** → panggil sub-agent per item (parallel bila independen).
5. **Monitor** → track progress, log ke `unified-integration/memory/gsd/<run-id>/`.
6. **Aggregate** → collect hasil sub-agent, integrasi ke deliverable.
7. **Report** → "DONE: <id> (X/Y)" per item; akhir "All done: Z items, N minutes."

## Inputs

- Tugas user (narasi)
- Opsional: max parallel (default 3)
- Opsional: budget total (default 50K token)

## Outputs

- Checklist `gsd-<run-id>.json` di `unified-integration/memory/gsd/`
- Artifact per item (file output sub-agent)
- Laporan akhir `gsd-<run-id>-report.md`

## Contoh

### Contoh 1 — Clear 10 TODO di codebase

Prompt: "Kerjakan 10 TODO di folder src/utils."

```
Goal: clear 10 TODO in src/utils

Checklist (10 items, est 30 min total):
  [1] TODO di date.ts: format timezone (3min, no dep)
  [2] TODO di string.ts: escape HTML (3min, no dep)
  [3] TODO in array.ts: chunk function (4min, no dep)
  ... (7 more)

Dispatch: 3 parallel (item 1,2,3 independent)
  item 1: DONE (2min) - format() updated
  item 2: DONE (3min) - escapeHtml added
  item 3: DONE (4min) - chunk() implemented

Wave 2 (item 4,5,6 parallel):
  ...
Report: 10/10 DONE, total 28 min, 0 fail.
```

### Contoh 2 — Migration 5 file ke TS

Prompt: "Convert 5 file JS ke TS di src/legacy."

```
Goal: convert 5 JS files to TS

Checklist (5 items, est 15 min):
  [1] convert auth.js -> auth.ts (3min, no dep)
  [2] convert user.js -> user.ts (3min, no dep)
  [3] convert session.js -> session.ts (3min, dep: [2])
  [4] convert token.js -> token.ts (4min, dep: [1])
  [5] tsconfig fix path alias (2min, dep: [1,2,3,4])

Wave 1 (parallel: 1,2):
  ...
Wave 2 (parallel: 3,4):
  ...
Wave 3 (5):
  ...
Report: 5/5 DONE, 14 min, 0 fail.
```

### Contoh 3 — Batch audit 3 halaman

Prompt: "Audit perf 3 landing page kami."

```
Goal: perf audit 3 LP

Checklist (9 items, est 21 min):
  [1] Lighthouse /home (3min, no dep)
  [2] Lighthouse /pricing (3min, no dep)
  [3] Lighthouse /signup (3min, no dep)
  [4-6] analyze + score per page (5min, dep: [1,2,3])
  [7-9] fix recommendation per page (5min, dep: [4-6])

Wave 1 (parallel: 1,2,3):
  ...
Report: 9/9 DONE, 18 min, 0 fail.
```

## Batasan & Keamanan

- Max 5 parallel default; bila lebih, tanya user (CPU limit).
- Sub-agent wajib return JSON `{"status", "artifact", "summary"}` — tidak boleh hang.
- Bila 1 item fail 2x, eskalasi ke user dengan diagnosis.
- Tidak dipakai untuk tugas kreatif (desain, narasi) — pakai BMAD.

## Catatan integrasi

- GSD jadi orchestrator default untuk mode "execute".
- Bekerja baik setelah `bmad-method` selesai decomposition; GSD eksekusi story per story.
- Untuk riset, gunakan `rea` sebagai orchestrator (bukan GSD).
- Memory shared lintas sub-agent via `memory-mcp`.
