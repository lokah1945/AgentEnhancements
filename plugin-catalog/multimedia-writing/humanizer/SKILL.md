---
slug: humanizer
category: multimedia-writing
version: 1.0.0
status: integrated-ready
mcp_servers: [style-mcp, grammar-mcp]
trigger_keywords: [humanize, natural, ai-ism, tone, rewrite]
---

# Humanizer

Skill humanisasi teks AI: deteksi pola AI-ism ('delve', 'tapestry', 'in conclusion'), ganti dengan diksi natural, jaga tone, dan hindari over-explanation.

## Kapan dipakai

- Setelah skill lain (BMAD, PPT Master, Agent-Reach) selesai menulis draft
- User complaint "tulisan AI banget", "terlaku kaku", "baca kayak robot"
- Ingin menulis dalam voice spesifik (casual / formal / playful)
- Email / blog post / marketing copy perlu natural

## Prasyarat

- MCP: `style-mcp`, `grammar-mcp`
- Tools: `bash`, `read_file`, `write_file`

## Capabilities

1. AI-ism detection — identifikasi pola: "delve", "tapestry", "in conclusion", "It's important to note", "Moreover", struktur 5-paragraf stereotype.
2. Natural voice rewriting — ganti pola AI-ism dengan diksi natural sesuai tone.
3. Tone preservation — jaga tone asli (formal / casual / playful).
4. Verbosity reduction — hapus over-explanation yang tidak perlu.

## Workflow

1. Baca teks input.
2. Scan AI-ism (regex + fuzzy match): buat tabel {location, pattern, suggestion}.
3. Hitung "AI-ism score" (0-100, makin rendah makin natural).
4. Identifikasi tone asli (formal/casual/playful) via heuristic.
5. Rewrite per AI-ism dengan padanan natural sesuai tone.
6. Hapus over-explanation (paragraf > 5 kalimat yang hanya restate sebelumnya).
7. Re-scan: AI-ism score target ≤ 20.
8. Output diff + score before/after.

## Inputs

- Teks (markdown / txt / docx)
- Opsional: target tone (preserve asli default)
- Opsional: target audience (memengaruhi register)

## Outputs

- Teks humanized (replace original via `edit_file`)
- `humanize-report.json` — {before_score, after_score, replacements, removed_paragraphs}

## Contoh

### Contoh 1 — Blog post humanize

Prompt: "Humanize blog post ini."

```
scan AI-ism (12 found):
  L3   "In today's rapidly evolving..." -> hapus
  L7   "It's important to note that..." -> hapus
  L12  "delve into" -> "explore"
  L18  "tapestry of" -> "the mix of"
  L25  "In conclusion..." -> hapus (sudah implisit)
  L30  "Moreover..." -> "Plus," (more casual)
  ...
  
AI-ism score: 78 -> 14 (-82%)

diff:
  - In today's rapidly evolving landscape of AI tools, it's important to note 
    that we must delve into the tapestry of options...
  + Ada banyak pilihan AI tools sekarang. Mari kita lihat beberapa yang 
    paling berguna...

output: blog-humanized.md
```

### Contoh 2 — Email formal

Prompt: "Humanize email pengajuan proposal, jaga tone formal tapi natural."

```
scan (5 AI-ism):
  L1 "I hope this email finds you well" -> "Semoga sehat" (sudah formal Indonesia)
  L4 "It is imperative that we..." -> "Penting bagi kita untuk..."
  L8 "Furthermore, we would like to..."
  ...

score: 62 -> 12

tone: formal Indonesia, natural (tidak kaku)
output: email-proposal.md
```

### Contoh 3 — Marketing copy playful

Prompt: "Bikin ad copy Instagram playful, jangan AI banget."

```
input (AI-ish):
"Discover our revolutionary new product that will transform your daily 
routine with cutting-edge technology..."

humanized:
"Punya rutin yang bosenin? Coba ini — bukan iklan biasa, produk ini beneran 
ngubah hari kita jadi lebih gampang."

score: 71 -> 8
```

## Batasan & Keamanan

- Tidak mengubah fakta / angka / quote — hanya gaya bahasa.
- Tidak menambah klaim yang tidak ada di source.
- Untuk dokumen legal / compliance, tampilkan diff dulu — jangan auto-apply.
- Preserve citation reference (`[1]`, `[2]`) — jangan dihapus.

## Catatan integrasi

- Jalankan sebagai **post-processor** setelah skill:
  - `ppt-master` (speaker notes)
  - `bmad-method` (laporan persona)
  - `agent-reach` (riset report)
  - `hyperframes` (script)
- Bekerja baik bersama `gstack` (kompresi dulu, baru humanize).
- Untuk audit AI-ism score history, simpan ke `unified-integration/memory/humanizer/`.
