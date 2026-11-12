---
slug: last-30-days
category: research
version: 1.0.0
status: integrated-ready
mcp_servers: [brave-search-mcp, newsapi-mcp, google-news-mcp]
trigger_keywords: [recent, last 30 days, news, trends, fresh]
---

# Last 30 Days

Window temporal research: ambil hanya sumber 30 hari terakhir untuk topik tertentu. Cocok untuk trend tracking, news monitoring, dan competitive intel time-sensitive.

## Kapan dipakai

- User minta "update terbaru", "apa yang terjadi bulan ini", "trend X 30 hari terakhir"
- Weekly digest otomatis
- Monitoring rilis competitor atau regulator

## Prasyarat

- MCP: `brave-search-mcp`, `newsapi-mcp`, `google-news-mcp`
- Tools: `web_search`, `web_fetch`
- Opsional: cron job untuk auto-run

## Capabilities

1. Date-windowed search — filter hasil dengan timestamp 30 hari terakhir.
2. Freshness scoring — skor sumber berdasarkan recency + engagement.
3. Delta detection vs prior window — bandingkan dengan window 30 hari sebelumnya.
4. Trend digest generation — ringkasan 1 halaman per minggu.

## Workflow

1. Tentukan topik + tanggal hari ini (UTC).
2. Window: `[today-30d, today]`.
3. Untuk tiap MCP search, pakai parameter date filter bila ada (NewsAPI `from`/`to`, Brave `freshness=pm`).
4. Filter manual: parse `publishedAt` / `lastmod` di hasil.
5. Deduplikasi berbasis URL + judul fuzzy match.
6. Skor freshness: `score = recency * 0.5 + engagement * 0.3 + authority * 0.2`.
7. Cluster berbasis topik (similarity embed) → identifikasi 3-5 sub-trend.
8. Untuk delta: ambil juga window sebelumnya (`[today-60d, today-30d]`), bandingkan topik yang muncul/hilang.
9. Draft digest: executive summary → 3-5 trend → sumber utama → delta highlights.

## Inputs

- Topik (teks)
- Opsional: window custom (default 30 hari)
- Opsional: bahasa (default `id` untuk Indonesia, atau `en`)
- Opsional: domain whitelist

## Outputs

- `digest-<slug>-<date>.md` di `download/digests/`
- `sources-<slug>-<date>.json` — daftar sumber dengan freshness score
- `delta-<slug>-<date>.md` — perubahan vs window sebelumnya

## Contoh

### Contoh 1 — Weekly digest AI agent

Prompt: "Buat digest minggu ini untuk topik 'AI agent framework'."

```
window: 2026-10-14 s/d 2026-11-13
sumber: 47 (filter 30 hari) -> 32 setelah dedup
trend (5):
  1. MCP adoption di production (12 sumber, score 0.84)
  2. LangGraph v0.3 release (8 sumber, score 0.78)
  3. OpenAI Agents SDK update (6 sumber, score 0.75)
  4. CrewAI enterprise license (4 sumber, score 0.62)
  5. Anthropic skill SDK beta (2 sumber, score 0.55)
delta vs 30 hari sebelumnya:
  + MCP adoption (new, 0 -> 12 sumber)
  + LangGraph v0.3 (new release)
  - AutoGen (turun 8 -> 2 sumber, indicative of stagnation)
output: download/digests/ai-agent-2026-11-13.md
```

### Contoh 2 — Competitor release tracker

Prompt: "Apa yang OpenAI rilis 30 hari terakhir?"

```
window: 2026-10-14 s/d 2026-11-13
sumber: 28 (filter official blog + tech press)
release:
  - 2026-10-22: GPT-5 mini
  - 2026-10-30: Realtime API v2
  - 2026-11-05: Agents SDK 1.0
  - 2026-11-10: Codex CLI open source
output: download/digests/openai-2026-11-13.md
```

### Contoh 3 — Regulator watch

Prompt: "Update regulasi AI di Indonesia 30 hari terakhir."

```
window: 2026-10-14 s/d 2026-11-13
sumber: 18 (kominfo.go.id, buu.ac.th, Hukumonline)
update:
  - Draft PP AI (kominfo, 2026-10-25)
  - Pedoman SE 9/2023 revisi (2026-11-02)
  - EU AI Act effect cross-ref (2026-11-08)
output: download/digests/ai-regulation-id-2026-11-13.md
```

## Batasan & Keamanan

- Beberapa API punya limit rate (NewsAPI 100 req/day tier free); throttle.
- Untuk topik niche, mungkin sumber < 5 — flag `LOW_DATA` di output.
- Tidak mengambil dari situs berbayar / paywall.
- Untuk digest terjadwal, simpan di `unified-integration/memory/digests/` agar tidak regenerate.

## Catatan integrasi

- Pasang sebagai cron job harian (`cron` tool) untuk auto-update memory.
- Bekerja baik bersama `agent-reach` (deep research) dan `graphify` (visualisasi trend).
- Untuk follow-up spesifik trend, panggil `agent-reach` dengan sub-query per trend.
