---
slug: ui-ux-pro-max
category: design
version: 1.0.0
status: integrated-ready
mcp_servers: [figma-mcp, browser-tools-mcp, storybook-mcp]
trigger_keywords: [ui, ux, design tokens, color, spacing]
---

# UI UX Pro Max

Skill desain UI/UX holistik: design tokens, spacing rhythm, color theory, micro-interactions, dan accessibility. Menghasilkan spesifikasi siap pakai untuk React/Vue/Svelte.

## Kapan dipakai

- User minta "design system", "design tokens", "spec UI"
- Membangun / redesign component library
- Butuh palette a11y-aware + spacing rhythm

## Prasyarat

- MCP: `figma-mcp`, `browser-tools-mcp`, `storybook-mcp`
- Tools: `bash`, `read_file`, `write_file`
- Opsional: akses Figma file ID

## Capabilities

1. Design-token generation — color, spacing, typography, radius, shadow tokens.
2. Component spec authoring — props, variants, states, a11y requirement.
3. Micro-interaction scripting — transition timing, easing curve.
4. A11y-aware palette — kontras ≥ 4.5:1 untuk AA, 7:1 untuk AAA.

## Workflow

1. Brief → identifikasi brand mood (modern/playful/serious/calm).
2. Generate color palette: primary, secondary, surface, background, error/warn/success (semua dengan AAA pair).
3. Generate spacing scale: base 4px / 8px rhythm (4/8/12/16/24/32/48/64).
4. Generate typography: heading 6 level + body + caption + code.
5. Generate radius + shadow scale.
6. Output `tokens.json` (W3C design token format) + `tokens.css` + `tokens.ts`.
7. Bila komponen diminta, spec per komponen: props, variant, state, a11y role.

## Inputs

- Brief (mood / brand / use case)
- Opsional: Figma file ID untuk pull existing tokens
- Opsional: framework target (React / Vue / Svelte / vanilla CSS)
- Opsional: a11y level (AA default, AAA strict)

## Outputs

- `tokens.json` — W3C format
- `tokens.css` — CSS variable
- `tokens.ts` — typed export untuk TS
- `<component>.spec.md` — per komponen
- `palette-preview.html` — visual preview

## Contoh

### Contoh 1 — SaaS dashboard

Prompt: "Design tokens untuk SaaS dashboard, mood modern + serious, React."

```
palette:
  primary:    #2563eb (AA contrast 4.6:1 di white)
  primary-hover: #1d4ed8
  success:    #16a34a (4.5:1)
  warning:    #d97706 (4.5:1)
  danger:     #dc2626 (4.5:1)
  surface:    #ffffff
  background: #f8fafc
  text:       #0f172a
  text-muted: #64748b

spacing (8px rhythm):
  xs 4, sm 8, md 16, lg 24, xl 32, 2xl 48, 3xl 64

typography:
  h1: 32/40/700 Inter
  h2: 24/32/600 Inter
  h3: 20/28/600 Inter
  body: 16/24/400 Inter
  caption: 14/20/400 Inter
  code: 14/20/400 JetBrains Mono

radius: sm 4, md 8, lg 12, pill 9999
shadow: sm 0 1px 2px rgba(0,0,0,0.05)
        md 0 4px 6px rgba(0,0,0,0.07)
        lg 0 10px 15px rgba(0,0,0,0.1)

output: download/design/tokens.json, tokens.css, tokens.ts
```

### Contoh 2 — Button component spec

Prompt: "Spec button untuk design system di atas."

```
<Button> spec:
  props:
    variant: primary | secondary | ghost | danger
    size: sm | md | lg
    loading: boolean
    icon: ReactNode?
    disabled: boolean
  variants (matrix variant × size × state):
    primary/md/default: bg=primary, text=white, radius=md, padding=8 16
    primary/md/hover: bg=primary-hover
    primary/md/disabled: opacity 0.5, cursor not-allowed
    ... (12 variant)
  a11y:
    role: button
    focus: outline 2px primary offset 2px
    keyboard: Enter/Space activate
  micro-interaction:
    hover: bg 150ms ease-out
    active: scale 0.97 100ms ease-out
output: download/design/Button.spec.md
```

### Contoh 3 — A11y palette fix

Prompt: "Palette saya kontras 3.2:1, fix dong."

```
analyze: primary #FF6B35 di white = 3.2:1 (di bawah AA)
fix: darkening primary ke #C44218 = 4.7:1 (pass AA)
trade-off: sedikit kurang vibrant, lebih professional
output: tokens.css updated, diff preview
```

## Batasan & Keamanan

- Tidak generate > 60 token per kategori (overload kognitif).
- Palette wajib verifikasi kontras dengan `wcag-contrast` calculator.
- Untuk brand global, pertimbangkan light + dark mode sejak awal.
- Tidak auto-apply ke Figma; tampilkan diff dulu.

## Catatan integrasi

- Token disimpan di `download/design/tokens.json` (single source of truth).
- Untuk QA visual, lanjut ke `impeccable` (polish audit).
- Untuk output presentasi, gunakan `ppt-master` (konsisten pakai tokens yang sama).
- Untuk dokumentasi visual, gunakan `diagram-design` (mermaid/d2).
