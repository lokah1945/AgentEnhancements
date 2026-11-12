---
slug: caveman
category: tokens-optimization
version: 1.0.0
status: integrated-ready
mcp_servers: [tokenizer-mcp]
trigger_keywords: [caveman, minimize, shorthand, compression]
---

# Caveman

Radical prompt compression: ringkas instruksi sampai ke core action verbs. Mengubah 'Please kindly write a function that...' menjadi 'fn(input)->output; test it;'. Buat hemat token hingga 70%.

## Kapan dipakai

- Edge deployment dengan budget sangat ketat
- Prompt berulang di pipeline batch (jutaan call)
- User eksplisit minta mode ultra-minimal
- Debugging: prompt pendek lebih mudah trace

## Prasyarat

- MCP: `tokenizer-mcp`
- Tools: `bash`, `read_file`, `write_file`
- Opsional: env `CAVEMAN_MODE=true`

## Capabilities

1. Extreme prompt minimization — hapus semua filler, polite form, hedges.
2. Intent-preserving rewrite — jaga semantic tetap sama.
3. Syntax-heavy shorthand — pakai simbol operator ketika memperjelas.

## Workflow

1. Baca prompt input.
2. Hapus: greeting, polite markers ("tolong", "mohon", "silakan"), hedges ("mungkin", "agaknya"), narasi pembuka.
3. Konversi ke struktur: `<verb> <object> <constraint>`.
4. Bila ada contoh, ringkas jadi `input -> output`.
5. Tambah `;` antar-instruksi.
6. Verifikasi semantic preservation dengan `tokenizer-mcp` (similarity ≥ 0.92).
7. Tampilkan before/after dengan token delta.

## Inputs

- Prompt teks (Indonesia / English)
- Opsional: target compression (default 70%)
- Opsional: keep sample (default 1)

## Outputs

- Prompt compressed (replace original)
- `caveman-log.json` opsional: {original_tokens, compressed_tokens, similarity}

## Contoh

### Contoh 1 — Function writing

Prompt original (75 token):
```
Halo AI, tolong saya butuh bantuan untuk menulis sebuah function di 
Python yang bisa menerima list angka dan mengembalikan rata-rata. 
Tolong berikan juga contoh penggunaannya dan pastikan codenya 
rapi serta mudah dibaca ya. Terima kasih banyak sebelumnya!
```

Caveman (18 token):
```
fn avg(list<num>)->num; ex: avg([1,2,3])=2; clean.
```

Compression: 76%.

### Contoh 2 — Refactor request

Prompt original (52 token):
```
Tolong refactor function ini supaya lebih efisien dan mudah dibaca, 
pertimbangkan untuk memisahkan logic ke beberapa helper function 
kalau perlu ya.
```

Caveman (14 token):
```
refactor fn: efficient; split helper if needed.
```

### Contoh 3 — Research brief

Prompt original (110 token):
```
Halo, saya sedang melakukan riset tentang perkembangan teknologi 
AI agent di Indonesia dan butuh bantuan untuk mencari informasi 
terkait siapa saja startup yang bermain di ruang ini, berapa 
pendanaan yang sudah mereka dapat, dan apa produk unggulan mereka. 
Tolong berikan dalam format tabel ya.
```

Caveman (24 token):
```
riset: AI agent startup ID; cols: nama,funding,produk; tabular.
```

## Batasan & Keamanan

- **Hanya untuk prompt internal agent**, bukan untuk komunikasi ke user (kecuali user minta).
- Tidak kompres bila prompt mengandung safety instruction kritikal (consent gate, disclaimer).
- Semantic similarity wajib di-check; bila < 0.92, rollback ke prompt asli.
- Tidak dipakai untuk email / laporan eksternal — akan terlihat kasar.

## Catatan integrasi

- Pasang sebagai post-processor opsional di pipeline prompt.
- Mode toggle: env `CAVEMAN_MODE=true` aktifkan global; `CAVEMAN_MODE=false` kembali ke normal.
- Bekerja baik setelah `gstack` summary; `gstack` kompres konteks, `caveman` kompres instruksi.
- Untuk komunikasi final ke user, gunakan `humanizer` setelah dapat output dari LLM.
