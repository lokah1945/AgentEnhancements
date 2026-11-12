---
slug: gstack
category: tokens-optimization
version: 1.0.0
status: integrated-ready
mcp_servers: [llm-cache-mcp, tokenizer-mcp]
trigger_keywords: [token, compress, budget, cache, context]
---

# GStack

Token-budget stack: prompt compressor, response cache, dan chain-of-density summarizer untuk memaksimalkan throughput LLM dalam context window kecil.

## Kapan dipakai

- Sesi agent sudah > 100K token, masih banyak task tersisa
- User complain "AI lambat / boros / mahal"
- Ingin cache response untuk query berulang
- Konteks panjang perlu di-summarize sebelum lanjut

## Prasyarat

- MCP: `llm-cache-mcp`, `tokenizer-mcp`
- Tools: `bash`, `node`, `read_file`, `write_file`
- Integrasi dengan `unified-integration/compression/` (headroom)

## Capabilities

1. Prompt compression — hapus wordiness, normalize ke shorthand padanan.
2. Response caching — semantik hash prompt → cache hit bypass LLM call.
3. Chain-of-density summarization — ringkas step-by-step tanpa kehilangan fakta.
4. Token usage telemetry — track per-skill, per-call.

## Workflow

1. Hitung token saat ini dengan `tokenizer-mcp` (model-aware: cl100k / llama).
2. Bila > budget threshold (default 75%):
   - Identifikasi blok konten yang tidak akan dipakai lagi.
   - Chain-of-density summary blok tersebut jadi 1/5 ukuran.
   - Ganti blok dengan summary + reference ke memory.
3. Untuk tiap prompt baru, hitung semantik hash → cek cache.
4. Bila hit, return cache; bila miss, jalankan LLM, simpan ke cache.
5. Telemetry: log `{skill, prompt_tokens, completion_tokens, cache_hit}`.

## Inputs

- Konten / prompt teks
- Opsional: budget target (default 100K)
- Opsional: cache TTL (default 24 jam)
- Opsional: model tokenizer (default `cl100k_base`)

## Outputs

- Konten kompresi (replace original di context)
- `cache-stats.json` di `unified-integration/memory/cache/`
- Telemetry line di `unified-integration/memory/telemetry.jsonl`

## Contoh

### Contoh 1 — Compress history sesi

Prompt: "Konteks saya 180K, mungkin too big. Compress dong."

```
analyze: 180K tokens, 92K masih relevan untuk task saat ini
strategy:
  - blok 0-30K (initial setup) -> summary 3K (chain-of-density 5 pass)
  - blok 60-90K (debug session) -> summary 2K
  - blok 120-180K (current) -> keep as-is
result: 180K -> 95K (-47%)
save: unified-integration/memory/compression/2026-11-13T19-30.md
```

### Contoh 2 — Cache hit untuk FAQ

Prompt: "User tanya 'apa beda v1 dan v2?' untuk ke-5 kalinya."

```
semantic hash: 0x3a8f9c2 (prompt: 'apa beda v1 dan v2')
cache hit: 0x3a8f9c2 (TTL 24h, hit count 5)
return cached response (0 token baru)
```

### Contoh 3 — Prompt shorthand

Prompt: "Prompt ini terlalu panjang, sederhanakan."

```
before (200 token):
"Tolong dengan sangat baik hati saya mohon untuk menjelaskan secara 
detail dan komprehensif bagaimana cara kerja sistem autentikasi OAuth2 
dengan flow authorization code PKCE dan apa saja perbedaan utama 
dibanding dengan implicit flow yang sudah deprecated."

after (40 token):
"Explain OAuth2 Auth Code PKCE flow; diff vs deprecated implicit flow."
compression: -80%
```

## Batasan & Keamanan

- Tidak kompres blok yang masih akan diakses dalam ≤ 5 turn ke depan.
- Cache key wajib hash semantik (embedding), bukan string match — sinonim harus hit.
- Telemetry wajib dipersist, tidak boleh ada leak PII ke log.
- Untuk data sensitif, disable cache (flag `NO_CACHE=true`).

## Catatan integrasi

- Layer kompresi utama, bekerja sama dengan `headroom` (sudah ada di repo).
- `caveman` adalah mode ekstrem dari skill ini (compression 70%+).
- Cache bisa di-share lintas sesi via `unified-integration/memory/cache/`.
- Telemetry dashboard bisa dibuat dari `telemetry.jsonl` (lihat `docs/cookbook.md`).
