---
slug: understand-anything
category: research
version: 1.0.0
status: integrated-ready
mcp_servers: [wikipedia-mcp, arxiv-mcp, embeddings-mcp]
trigger_keywords: [explain, understand, concept, Feynman, onboarding]
---

# Understand Anything

Skill "explain any concept" dengan pendekatan Feynman + layered depth: ringkasan 1 kalimat, 1 paragraf, 1 halaman, lalu deep dive. Mendeteksi knowledge gap dan prerequisite.

## Kapan dipakai

- User minta "jelasin X", "apa itu Y", "anak baru, bingung konsep Z"
- Skill lain gagal menjelaskan konsep yang user tanyakan
- Ingin onboarding topik baru secara terstruktur

## Prasyarat

- MCP: `wikipedia-mcp`, `arxiv-mcp`, `embeddings-mcp`
- Tools: `web_search`, `web_fetch`, `read_file`, `write_file`

## Capabilities

1. Concept explanation at multiple depths — 1 sentence, 1 paragraph, 1 page, deep dive.
2. Feynman-style analogy — analogi konkret yang bisa di-cek dengan common sense.
3. Prerequisite graph — konsep apa yang harus dipahami dulu.
4. Knowledge-gap detection — identifikasi apa yang user belum tahu dari pertanyaan.

## Workflow

1. Identifikasi konsep inti dari pertanyaan user (1 kata/frasa).
2. Cek prerequisite: konsep apa yang harus user pahami dulu (max 3).
3. Tulis 4 lapisan penjelasan:
   - **One-liner** — 1 kalimat, no jargon.
   - **Paragraph** — 3-5 kalimat, 1 analogi.
   - **Page** — 500-800 kata, struktur: definisi → mekanisme → contoh → batasan.
   - **Deep dive** — 2000+ kata, sejarah, variasi, kutipan, referensi.
4. Tambah "Prerequisite" section di atas, "Next" section di bawah.
5. Tampilkan ke user, mulai dari one-liner; user bisa minta layer lebih dalam.

## Inputs

- Konsep (teks bebas)
- Opsional: audience (beginner / intermediate / expert)
- Opsional: target depth (one-liner / paragraph / page / deep dive)

## Outputs

- `explain-<slug>.md` di `download/explain/` (default: full 4-layer)
- Print ke chat: minimal one-liner + paragraph + "want more? say 'deep'"

## Contoh

### Contoh 1 — Quantum entanglement untuk pemula

Prompt: "Jelasin quantum entanglement untuk anak SMA."

```
Prerequisite: superposition, photon, spin.

ONE-LINER:
Entanglement adalah ketika dua partikel terhubung sedemikian rupa
sehingga keadaan satu langsung menentukan keadaan lainnya, walau jauh.

PARAGRAPH (analogi):
Bayangkan dua koin ajaib: kalau kamu flip koin A di Jakarta dan koin B
di New York secara bersamaan, hasilnya selalu sama (kedua-kepala atau
kedua-ekor) tanpa komunikasi. Entanglement seperti itu — partikel
"berbagi takdir", tapi kita tidak bisa pakai untuk kirim pesan lebih
cepat dari cahaya.

PAGE:
[500 kata: definisi formal, mekanisme Bell state, eksperimen Aspect 1982,
 batasan no-signaling, aplikasi quantum cryptography]

NEXT: Bell inequality, no-cloning theorem, quantum teleportation.
```

### Contoh 2 — Apa itu "context window" di LLM

Prompt: "Apa itu context window? Saya baru dengar."

```
Prerequisite: token, attention mechanism.

ONE-LINER:
Context window adalah jumlah token maksimum yang bisa diproses LLM dalam
satu kali input+output.

PARAGRAPH:
[...]

NEXT: tokenization, chunking, long-context model (Claude 200K).
```

### Contoh 3 — Recursion untuk developer junior

Prompt: "Pusing recursion, jelasin dong."

```
Prerequisite: function, call stack.

ONE-LINER:
Recursion adalah function yang memanggil dirinya sendiri sampai base case.

PARAGRAPH + analogi:
Bayangkan kamu di peti matryoshka: buka satu, ada lagi di dalam, terus
buka sampai peti terakhir kosong. Function recursive = proses buka peti,
base case = peti kosong (stop).

PAGE:
[kode factorial + fibonacci + tree traversal, common pitfalls, 
 kapan PAKAI recursion vs loop]

NEXT: tail-call optimization, memoization, dynamic programming.
```

## Batasan & Keamanan

- Tidak halusinasi referensi; bila tidak yakin tanggal/nama, cek `wikipedia-mcp`.
- Untuk konsep sensitif (medis/hukum/keuangan), tambahkan disclaimer.
- Deep dive dibatasi 2500 kata; bila user minta lebih, pecah jadi 2 dokumen.

## Catatan integrasi

- Skill ini jadi "fallback" di orchestrator — ketika skill lain tidak menjelaskan konsep dengan baik.
- Output bisa jadi input untuk `graphify` (prerequisite graph) atau `ppt-master` (materi onboarding).
- Cache hasil di `unified-integration/memory/explanations/` agar tidak regenerate konsep yang sama.
