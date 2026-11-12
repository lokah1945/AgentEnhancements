---
slug: ppt-master
category: design
version: 1.0.0
status: integrated-ready
mcp_servers: [google-slides-mcp, office-mcp, image-search-mcp]
trigger_keywords: [ppt, slides, presentation, keynote, narrative]
---

# PPT Master

Skill presentasi profesional: struktur naratif, slide design tokens, chart palette, dan speaker notes. Output ke PPTX / Google Slides / PDF.

## Kapan dipakai

- User minta "buat deck", "presentation", "slides"
- Pitch deck, internal review, materi kuliah
- Konversi dokumen panjang jadi slide

## Prasyarat

- MCP: `google-slides-mcp`, `office-mcp`, `image-search-mcp`
- Tools: `python-pptx` (untuk PPTX), `marp` (untuk markdown→PPT)
- Akses ke `read_file`, `write_file`

## Capabilities

1. Narrative arc generation — Hero's Journey / problem-solution / data-driven.
2. Slide-layout authoring — title-content, two-column, quote, stat, image-bg.
3. Chart palette mapping — konsisten dengan design tokens.
4. Speaker notes drafting — narasi 1 slide = 1 paragraf.

## Workflow

1. Brief user → identifikasi audience, goal, duration, tone.
2. Pilih narrative arc (problem-solution default; pitch deck: hero's journey).
3. Outline: 1 slide per beat (target 1 slide per 2 menit talk).
4. Draft per slide:
   - title (≤ 6 kata)
   - body (≤ 30 kata, atau 1 chart/image)
   - speaker notes (1 paragraf 100-150 kata)
5. Mapping chart palette: pakai `tokens.json` primary/secondary.
6. Render: PPTX via python-pptx, atau Google Slides via MCP, atau MD+marp.
7. Tampilkan preview (render PDF + thumbnail).

## Inputs

- Brief (audience / goal / duration / tone)
- Opsional: source content (markdown / docx / pdf)
- Opsional: design tokens (link ke `tokens.json`)
- Opsional: target format (pptx / google-slides / pdf)
- Opsional: brand assets (logo path)

## Outputs

- `deck-<slug>.pptx` di `download/decks/`
- `deck-<slug>.md` (source marp) bila mode markdown
- `deck-<slug>.pdf` (preview)
- `speaker-notes.md` — kumpulan notes per slide

## Contoh

### Contoh 1 — Pitch deck 10 slide

Prompt: "Buat pitch deck untuk startup AI agent kami, 10 menit, audience investor."

```
arc: hero's journey (problem → solution → traction → ask)
outline (10 slide):
  1. Hook: "Hari ini 87% dev jam bekerja di boilerplate, bukan inovasi"
  2. Problem: vis ini boros, langkah manual
  3. Solution: agent super-suite kami
  4. Demo: screenshot + GIF
  5. Traction: 5K dev, 12% MoM
  6. Market: TAM $4B
  7. Business model: SaaS $29/dev/month
  8. Team: founder bios
  9. Roadmap: 12 bulan
  10. Ask: $2M seed, 18 months runway

render: download/decks/pitch.pptx (10 slide, palette konsisten tokens.json)
notes: speaker-notes.md (10 paragraf, 120 kata rata-rata)
```

### Contoh 2 — Lecture 25 slide

Prompt: "Buat materi kuliah 'Intro ke LLM' 50 menit, 25 slide."

```
arc: data-driven (concept → math → code → example)
outline (25):
  section 1 (1-5): motivation + history
  section 2 (6-12): transformer architecture
  section 3 (13-20): training + fine-tuning
  section 4 (21-25): use case + limit
render: deck-llm-intro.pptx + speaker-notes.md
```

### Contoh 3 — Konversi docx jadi slide

Prompt: "Konversi `report.pdf` 30 halaman jadi deck 12 slide."

```
parse PDF: 30 hal -> extract section + key point per section
compress: 1 slide per 2-3 section (12 slide total)
render: deck-from-report.pptx
notes: 12 paragraf, ringkasan section yang di-represent
```

## Batasan & Keamanan

- Max 30 slide default; bila lebih, pecah jadi 2 deck.
- Tidak auto-include gambar dari internet tanpa cek lisensi (CC0/Creative Commons).
- Speaker notes wajib, bukan opsional — untuk self-running mode.
- Tidak auto-publish ke Google Slides public; selalu private dulu.

## Catatan integrasi

- Pakai `tokens.json` dari `ui-ux-pro-max` untuk palette konsisten.
- Untuk diagram di slide, gunakan `diagram-design` (mermaid/d2) lalu embed sebagai image.
- Setelah draft, jalankan `humanizer` ke speaker notes agar natural.
- Untuk audit visual sebelum kirim, jalankan `impeccable` di slide PDF preview.
