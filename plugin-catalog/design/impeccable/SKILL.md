---
slug: impeccable
category: design
version: 1.0.0
status: integrated-ready
mcp_servers: [browser-tools-mcp, figma-mcp]
trigger_keywords: [polish, impeccable, alignment, contrast, hierarchy]
---

# Impeccable

Skill polish UI: perbaikan micro-visual (alignment, contrast, hierarchy, motion timing) yang membedakan 'OK' dari 'impeccable'. Berbasis checklist Polaris/Material/Carbon.

## Kapan dipakai

- Sebelum ship: QA visual pass terakhir
- User complaint "UI kurang polished", "terasa murahan"
- Designer review dengan feedback micro

## Prasyarat

- MCP: `browser-tools-mcp`, `figma-mcp`
- Tools: `browser`, `read_file`, `edit_file`
- Akses URL staging atau file HTML

## Capabilities

1. Visual polish audit — alignment grid, spacing consistency, edge case.
2. Alignment grid check — verifikasi snap ke 4/8px grid.
3. Contrast & motion timing — WCAG + 200ms-400ms range for UI transitions.
4. Spec diff against design system — detect deviation from tokens.

## Workflow

1. Screenshot halaman target (per breakpoint).
2. Per breakdown (mobile/tablet/desktop), jalankan checklist:
   - Alignment: semua element snap ke grid 4/8px?
   - Spacing: konsisten dengan scale (tidak ada "12px" di tempat acak)?
   - Hierarchy: heading size ratio konsisten (1.25 / 1.333 / 1.5)?
   - Contrast: WCAG AA minimum?
   - Motion: hover/transition dalam 150-300ms?
   - Edge case: empty state, loading state, error state, long text overflow?
3. Identifikasi 5 isu prioritas tertinggi.
4. Tulis diff HTML/CSS per isu → apply → re-screenshot.
5. Output diff before/after + laporan.

## Inputs

- URL atau file HTML
- Opsional: design tokens path (untuk spec diff)
- Opsional: target breakpoint

## Outputs

- `polish-<timestamp>.md` di `download/audit/`
- Diff HTML/CSS (applied via `edit_file`)
- Screenshot before/after
- Tabel isu: {priority, location, before, after, rule}

## Contoh

### Contoh 1 — Polish dashboard

Prompt: "Audit polish dashboard kami, apa kurang?"

```
issues (5, urut by priority):
  P1: card title 14px, body 16px — hierarchy terbalik
  P1: spacing antar card 12px, bukan dari scale (harus 16px)
  P2: button hover 50ms terlalu cepat, harap 150ms ease-out
  P2: empty state "No data" — hanya teks, perlu icon + CTA
  P3: text-muted #999 di white = 2.8:1, fail WCAG AA (harus ≥ 4.5:1)

fix (apply):
  - card title 18px, body 14px
  - spacing gap -> 16px
  - button transition 150ms ease-out
  - empty state: add icon + "Try adding one" CTA
  - text-muted -> #64748b (4.6:1)
re-screenshot: PASS
output: download/audit/polish-2026-11-13.md
```

### Contoh 2 — Mobile audit

Prompt: "Audit halaman mobile saya — terasa cramped."

```
issues:
  P1: padding container 8px (terlalu sempit, harap 16px)
  P1: touch target button 32px (di bawah 44px iOS HIG)
  P2: font body 12px (di bawah 14px, susah baca)
  P3: status bar safe area tidak di-handle (notch tertutup)
fix: apply 4 fix
re-screenshot: PASS
```

### Contoh 3 — Spec diff vs design system

Prompt: "Cek konsistensi halaman ini vs tokens.json."

```
deviations (3):
  - card radius 6px (spec: 8px) — 3 lokasi
  - text-muted #888 (spec: #64748b) — 5 lokasi
  - button padding 6 12 (spec: 8 16) — 2 lokasi
fix: replace all ke spec
output: download/audit/spec-diff-2026-11-13.md
```

## Batasan & Keamanan

- Tidak auto-apply > 10 fix per sesi (overwhelm review); batch 5.
- Screenshot wajib before/after pair untuk audit trail.
- Tidak mengubah behavior JS, hanya visual (CSS + HTML structure).
- Untuk brand strict, eskalasi deviation > 10 ke designer.

## Catatan integrasi

- Jalankan setelah `ui-ux-pro-max` (untuk verify spec compliance).
- Sebelum `ppt-master` (konsistensi token).
- Output audit di-persist di `unified-integration/memory/audits/`.
