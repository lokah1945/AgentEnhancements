---
slug: agent-skills-addyosmani
category: code
version: 1.0.0
status: integrated-ready
mcp_servers: [browser-tools-mcp, lighthouse-mcp, pa11y-mcp]
trigger_keywords: [performance, a11y, lighthouse, core web vitals, frontend]
---

# Agent Skills (Addy Osmani)

Web performance, accessibility, dan modern frontend patterns dari koleksi Addy Osmani. Berfokus pada Core Web Vitals, bundle size, dan progressive enhancement.

## Kapan dipakai

- User minta "audit perf", "fix LCP/CLS/INP", "improve Core Web Vitals"
- Lighthouse score < 90 pada kategori performance atau accessibility
- Ingin audit a11y (WCAG 2.2 AA)
- Bundle size melebihi budget (mis. JS > 200 KB gzip)

## Prasyarat

- MCP: `browser-tools-mcp`, `lighthouse-mcp`, `pa11y-mcp`
- Tools: `lighthouse`, `pa11y`, `chrome-launcher`, akses browser headless
- URL target atau HTML file lokal

## Capabilities

1. Performance audit — jalankan Lighthouse 3x (median) untuk stabilitas.
2. Core Web Vitals fix — LCP, CLS, INP optimization dengan diff konkret.
3. Bundle analysis — parse webpack/vite bundle, identifikasi dead code.
4. A11y remediation — pa11y + axe rules, perbaiki dengan HTML/ARIA tepat.
5. Progressive enhancement — pastikan baseline no-JS tetap usable.

## Workflow

1. Verifikasi target (URL / file).
2. Snapshot awal: Lighthouse (perf + a11y), pa11y, ukuran bundle.
3. Identifikasi 3 isu prioritas tertinggi (terurut by impact).
4. Untuk tiap isu, tulis diff perbaikan → apply → re-snapshot.
5. Bandingkan before/after dalam tabel.
6. Tulis ringkasan: "LCP 2.4s -> 1.1s (-54%), CLS 0.21 -> 0.04 (-81%)."

## Inputs

- URL atau path HTML
- Opsional: lighthouse config (formFactor: mobile/desktop, throttle)
- Opsional: bundle stats (`stats.json` dari webpack-bundle-analyzer)

## Outputs

- Diff file (HTML/CSS/JS) yang dimodifikasi via `edit_file`
- Laporan `audit-<timestamp>.md` di `download/audit/`
- Diff visual before/after (screenshot)
- Tabel metrik:

| Metric    | Before | After  | Delta   |
|-----------|--------|--------|---------|
| LCP       | 2.4s   | 1.1s   | -54%    |
| CLS       | 0.21   | 0.04   | -81%    |
| INP       | 320ms  | 180ms  | -44%    |
| a11y      | 78     | 96     | +18     |

## Contoh

### Contoh 1 — Fix LCP tinggi

Prompt: "Audit https://example.com — LCP saya 3.8s, perbaiki."

```
root cause: hero image 1.2MB, no width/height, lazy loaded
fix:
  - tambah width/height eksplisit (CLS prevention)
  - preload hero image (LCP improvement)
  - convert ke AVIF + fallback WebP
  - hapus lazy-load untuk above-the-fold
re-snapshot: LCP 3.8s -> 1.4s
```

### Contoh 2 — A11y audit form

Prompt: "Audit a11y form login saya, pa11y banyak warning."

```
violations (5):
  - input tanpa label (<input type="email" id="email">)
  - button dengan icon tanpa aria-label
  - contrast ratio 3.2:1 (di bawah 4.5:1)
  - form group tanpa fieldset
  - error message tidak ter-link ke input via aria-describedby
fix: tulis diff HTML, re-test pa11y -> 0 violations
```

### Contoh 3 — Bundle slimming

Prompt: "Bundle JS saya 480KB gzip, terlalu besar."

```
analysis: 
  - momentjs (80KB) -> date-fns/esm (12KB)
  - lodash (70KB) -> lodash-es tree-shakeable (4KB used)
  - 3 dependencies unused -> hapus
new size: 180KB gzip (-62%)
```

## Batasan & Keamanan

- Jangan jalankan Lighthouse lebih dari 3x berturut — boros CPU server.
- Tidak auto-deploy fix; selalu tampilkan diff dulu.
- Untuk situs produksi, lakukan audit di staging mirror, bukan live.
- Kontras warna fix wajib pakai contrast ratio calculator, bukan tebakan.

## Catatan integrasi

- Pasang hook post-edit `ui-ux-pro-max` (design tokens konsisten).
- Untuk QA visual, lanjut ke skill `impeccable`.
- Hasil audit dipersist di `unified-integration/memory/audits/`.
