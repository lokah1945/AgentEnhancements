---
slug: rea
category: research
version: 1.0.0
status: integrated-ready
mcp_servers: [task-router-mcp, memory-mcp]
trigger_keywords: [rea, reasoning, reflection, multi-step]
---

# REA (Reason-Explain-Act)

Reason-Explain-Act loop untuk riset multi-step: tiap iterasi menyusun rencana, menjelaskan alasan, lalu memilih tool. Mendukung reflection dan backtracking ketika hasil divergen.

## Kapan dipakai

- User minta "investigasi", "telusuri", "cari tahu kenapa"
- Riset kompleks dengan banyak hipotesis yang perlu diuji
- Pertanyaan multi-hop (jawaban butuh beberapa langkah riset)

## Prasyarat

- MCP: `task-router-mcp`, `memory-mcp`
- Tools: `web_search`, `web_fetch`, `bash`, `read_file`, `write_file`
- Akses ke skill lain ( sebagai "Act" tools)

## Capabilities

1. Plan-reason-act loop — tiap iterasi: rencana, alasan, eksekusi.
2. Self-reflection — evaluasi hasil vs hipotesis; rollback bila divergen.
3. Backtracking — kembali ke langkah sebelumnya bila jalan buntu.
4. Tool selection policy — pilih tool terbaik berdasarkan tipe sub-task.

## Workflow

1. **Parse**: ekstrak pertanyaan utama + sub-pertanyaan implisit.
2. **Hypothesize**: 2-3 hipotesis awal (H1, H2, H3).
3. **Loop** (max 5 iterasi):
   - **Reason**: pilih hipotesis yang akan diuji, tentukan tool.
   - **Explain**: tulis 1 paragraf "Saya akan <tool> karena <alasan>, harapan <hasil>."
   - **Act**: jalankan tool (search / fetch / call skill lain).
   - **Reflect**: evaluasi hasil: apakah hipotesis didukung? tolak? perlu revisi?
   - **Update memory**: persist ke `unified-integration/memory/rea/<iteration>.md`.
4. **Synthesize**: bila ≥ 1 hipotesis didukung, sintesis laporan akhir.
5. **Audit trail**: log semua iterasi ke `unified-integration/memory/rea/<slug>/`.

## Inputs

- Pertanyaan investigasi (narasi)
- Opsional: max iteration (default 5)
- Opsional: hipotesis awal yang sudah user punya

## Outputs

- `investigation-<slug>.md` — laporan akhir dengan hipotesis yang didukung/ditolak
- `rea-trace-<slug>.json` — log iterasi {iter, hypothesis, tool, result, decision}
- `memory/rea/<slug>/iteration-*.md` — artifact per iterasi

## Contoh

### Contoh 1 — Investigasi outage

Prompt: "Kenapa API kami 502 dari jam 14:00 sampai 14:30 tadi?"

```
H1: database down
H2: rate limit hit
H3: deploy regression

iter 1 (Reason): test H1, cek db logs
  Explain: cek slow query log untuk anomali, harapan ada spike
  Act: tail /var/log/postgresql/slow.log
  Reflect: tidak ada spike, H1 tolak

iter 2 (Reason): test H2, cek rate limit metric
  Explain: cek grafana rate limit dashboard, harapan ada throttle event
  Act: curl https://grafana/api/datasources/proxy/...
  Reflect: spike di 14:05-14:15, H2 didukung sebagian

iter 3 (Reason): test H3, git log deploy window
  Explain: cek deploy commit 13:55, harapan ada breaking change
  Act: git log --since="13:00" --until="14:00"
  Reflect: deploy v2.1.4 13:58, ubah auth middleware
  H3 didukung kuat

Synthesize: root cause deploy v2.1.4 mengubah auth middleware 
yang melempar 502 bila token expired. Rollback v2.1.3 -> resolve.
```

### Contoh 2 — Hipotesis riset pasar

Prompt: "Apakah pasar Indonesia siap untuk subscription model SaaS B2C?"

```
H1: ya, karena genggam cashless naik
H2: tidak, karena behavior lokal suka free + iklan
H3: parsial, hanya niche ( produktivitas, kreatif)

[3 iterasi dengan search, fetch berita, ambil data Bank Indonesia,
 compare case study Zenius/Ruanguji yang gagal vs niche yang sukses]

Synthesize: H3 didukung — niche productivity/creative bisa, 
mass-market B2C belum ( perlu edukasi + pricing tier).
```

### Contoh 3 — Bug reproduce

Prompt: "Bug: 5% user lihat layar putih di Chrome 120. Reproduce dong."

```
H1: extension conflict
H2: service worker race
H3: CSS subgrid tidak support di 120

[2 iterasi: VM Chrome 120 fresh, disable extension, replay]

Synthesize: H2 didukung — race condition saat service worker 
register sebelum DOM ready, fix dengan defer register.
```

## Batasan & Keamanan

- Max 5 iterasi default; bila user minta lebih, tanya justifikasi.
- Tidak menjalankan tool destruktif tanpa konfirmasi user.
- Bila hipotesis semua ditolak setelah 5 iterasi, laporkan "tidak ada kesimpulan, perlu data tambahan".
- Audit trail wajib — tanpa log, REA kehilangan trace untuk debug.

## Catatan integrasi

- REA jadi orchestrator lapis atas untuk mode research.
- REA bisa invoke: `agent-reach`, `graphify`, `last-30-days`, `understand-anything`.
- Untuk mode "execute", lanjut ke `gsd` atau `bmad-method`.
- Memory shared dengan `memory-mcp` lintas sesi.
