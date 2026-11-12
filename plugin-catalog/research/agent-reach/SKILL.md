---
slug: agent-reach
category: research
version: 1.0.0
status: integrated-ready
mcp_servers: [brave-search-mcp, tavily-mcp, exa-mcp, firecrawl-mcp]
trigger_keywords: [deep research, literature, sources, citation]
---

# Agent-Reach

Framework deep-research multi-step: query expansion, source triage, claim cross-check, citation graph, dan synthesized report. Mendukung parallel sub-agents dan budget token per sub-task.

## Kapan dipakai

- User minta "research <topik> secara mendalam", "compare X vs Y", "literature review"
- Riset membutuhkan > 10 sumber dengan cross-check klaim
- Ingin laporan dengan sitasi lengkap dan struktur akademik

## Prasyarat

- MCP: `brave-search-mcp`, `tavily-mcp`, `exa-mcp`, `firecrawl-mcp`
- Tools: `web_search`, `web_fetch`, `read_file`, `write_file`
- Opsional: `embeddings-mcp` untuk deduplikasi semantik sumber

## Capabilities

1. Query expansion — pecah pertanyaan jadi 5-10 sub-query paralel.
2. Source triage & ranking — skor kredibilitas (domain, author, recency).
3. Claim cross-check — bandingkan klaim lintas sumber, flag kontradiksi.
4. Citation-aware synthesis — tiap paragraf di laporan wajib sitasi `[1] [2]`.
5. Parallel sub-agents — eksekusi sub-query serentak, lalu aggregate.

## Workflow

1. Pisah pertanyaan user jadi 3-7 sub-pertanyaan (atomic).
2. Untuk tiap sub-pertanyaan, generate 2-3 keyword variant.
3. Dispatch sub-agent paralel untuk tiap sub-pertanyaan (max 3 source per agent).
4. Tiap agent: search → fetch top 3 → extract klaim → return JSON `{source, claim, evidence_quote, url}`.
5. Aggregate → deduplikasi semantik → cross-check klaim → flag kontradiksi.
6. Bangun citation graph (sumber mana yang mendukung klaim mana).
7. Draft laporan dengan struktur: Executive Summary → Findings (per sub-question) → Contradictions → Conclusion → References.
8. Persist ke `unified-integration/memory/research/<slug>.md`.

## Inputs

- Pertanyaan riset (1-3 kalimat)
- Opsional: target jumlah sumber (default 15)
- Opsional: domain whitelist/blacklist (mis. hanya `.edu`, `.gov`)
- Opsional: window waktu (mis. "last 12 months")

## Outputs

- `report-<slug>.md` di `download/research/` — laporan lengkap dengan sitasi
- `sources.json` — daftar sumber terurut {url, title, author, date, credibility, claim_count}
- `citations.graph.json` — citation graph untuk visualisasi
- `contradictions.md` — daftar kontradiksi yang ditemukan

## Contoh

### Contoh 1 — Kompetitor analysis

Prompt: "Bandingkan 3 LLM agent framework teratas untuk production use — LangGraph vs CrewAI vs AutoGen."

```
sub-questions (5):
  1. performance benchmark
  2. community & maintenance
  3. production case studies
  4. pricing / license
  5. integrasi MCP

sub-agents: 5 paralel, ~3 source per agent, total 14 sumber
cross-check: 2 kontradiksi (performa benchmark, satu sumber mengklaim CrewAI lebih cepat)
report: download/research/llm-framework-compare.md (3200 kata, 28 sitasi)
```

### Contoh 2 — Literature review medis

Prompt: "Literature review: efektivitas metformin untuk anti-aging, 5 tahun terakhir."

```
sub-questions (4):
  1. clinical trial human
  2. mechanism of action
  3. safety profile long-term
  4. meta-analysis

sub-agents: 4 paralel, total 18 sumber (12 PubMed, 4 bioRxiv, 2 review)
cross-check: 0 kontradiksi (konsensus "promising tapi belum conclusive")
report: download/research/metformin-aging.md (4100 kata, 18 sitasi)
```

### Contoh 3 — Trend alert teknologi

Prompt: "Apa tren edge AI chip 2024-2026? Buat laporan eksekutif."

```
sub-questions (5):
  1. vendor utama
  2. arsitektur baru
  3. use case production
  4. roadmap generasi berikutnya
  5. isu supply chain

sub-agents: 5 paralel, total 22 sumber
cross-check: 3 kontradiksi (roadmap NVIDIA, AMD, Intel)
report: download/research/edge-ai-chip.md (2800 kata, 22 sitasi, eksekutif)
```

## Batasan & Keamanan

- Token budget default 50K per sub-agent; batasi bila perlu.
- Tidak mengambil sumber dari domain yang di-blacklist user.
- Tidak mengutip > 200 kata dari satu sumber (copyright fair use).
- Untuk riset medis / hukum, wajib disclaimer "bukan nasihat profesional".

## Catatan integrasi

- Output graph (citation graph) bisa diteruskan ke `graphify` untuk visualisasi.
- Untuk window temporal, gunakan bersama `last-30-days`.
- Untuk explain konsep dalam laporan, panggil `understand-anything`.
- Default orchestrator untuk mode "research": REA bisa invoke skill ini.
