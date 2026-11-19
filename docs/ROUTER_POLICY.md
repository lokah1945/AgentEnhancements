---
title: Router Policy
version: 1.2
last_updated: 2026-11-15
audience: all agents
---

## Router Policy — Orchestrator Dispatcher

Mendefinisikan kapan setiap orchestrator / plugin / skill resmi Anthropic
dipanggil. Implementasi heuristic ada di
`unified-integration/scripts/dispatch.sh`.

### Hierarki Dispatch

Dispatch berlapis: **orchestrator** (BMAD / GSD untuk mode eksekusi besar, REA
untuk analisis rekayasa balik) lebih dulu, lalu **skill resmi Anthropic** untuk
intent yang sangat spesifik (format file, MCP, skill engineering, testing, API),
lalu **plugin spesifik** per sub-task. Prompt yang tidak cocok kategori mana pun
jatuh ke **ordinary tools** (abstain jujur), bukan dipaksakan ke satu skill.

```text
User prompt
   |
   +--[orchestrator tier]--> bmad / gsd / rea (reverse engineering)
   |                           |
   |                           +--[plugin tier]--> 40 plugin katalog
   |
   +--[anthropic skill tier]--> docx / pdf / pptx / xlsx / mcp-builder /
   |                           skill-creator / webapp-testing / claude-api
   |                           (vendored di anthropic-skills/, sudah
   |                           natively linked saat setup)
   |
   +--[plugin tier langsung]--> bila trigger keyword jelas
   |
   +--[fallback]--> none: ordinary agent tools (tidak ada skill yang dipaksa)
```

Skill tier Anthropic dievaluasi SETELAH orchestrator tapi SEBELUM plugin
karena intent format-file (`.docx`, `.pdf`, `powerpoint`, `excel`) adalah
sinyal paling spesifik.

### Tabel Policy

- **Pola prompt user:** "build product", "greenfield", "dari nol"
  - **Orchestrator:** bmad-method
  - **Plugin prioritas:** — (BMAD invoke sendiri)

- **Pola prompt user:** "kerjakan semua", "do all", "clear backlog"
  - **Orchestrator:** gsd
  - **Plugin prioritas:** — (GSD invoke per task)

- **Pola prompt user:** "reverse engineer", "decompile", "disassemble",
  "binary/APK analysis"
  - **Orchestrator:** rea (Reverse Engineer Anything)
  - **Plugin prioritas:** — (butuh server upstream morluto/rea)

- **Pola prompt user:** "build / integrate mcp server", "model context protocol"
  - **Orchestrator:** —
  - **Plugin prioritas:** mcp-builder (skill resmi)

- **Pola prompt user:** "create / improve / eval a skill", "buat skill"
  - **Orchestrator:** —
  - **Plugin prioritas:** skill-creator (skill resmi)

- **Pola prompt user:** "test webapp", "playwright", "browser screenshot"
  - **Orchestrator:** —
  - **Plugin prioritas:** webapp-testing (skill resmi)

- **Pola prompt user:** "claude api", "anthropic api", "claude sdk"
  - **Orchestrator:** —
  - **Plugin prioritas:** claude-api (skill resmi)

- **Pola prompt user:** sebut `.docx` / `.dotx` / "word document"
  - **Orchestrator:** —
  - **Plugin prioritas:** docx (skill resmi)

- **Pola prompt user:** sebut `.pdf` / "pdf"
  - **Orchestrator:** —
  - **Plugin prioritas:** pdf (skill resmi)

- **Pola prompt user:** sebut `.pptx` / `.potx` / "powerpoint"
  - **Orchestrator:** —
  - **Plugin prioritas:** pptx (skill resmi)

- **Pola prompt user:** sebut `.xlsx` / `.csv` / "excel" / "spreadsheet"
  - **Orchestrator:** —
  - **Plugin prioritas:** xlsx (skill resmi)

- **Pola prompt user:** "clone app X", "build my own version"
  - **Orchestrator:** —
  - **Plugin prioritas:** replica-skill (11 sub-skill berurutan; REA untuk
    analisis, replica untuk rebuild)

- **Pola prompt user:** `"research <topik>"`, "compare X vs Y"
  - **Orchestrator:** —
  - **Plugin prioritas:** agent-reach (deep research), graphify, last-30-days

- **Pola prompt user:** "refactor TS", "ketatkan types"
  - **Orchestrator:** —
  - **Plugin prioritas:** mattpocock-skills

- **Pola prompt user:** "prototype", "sketch", "numpy"
  - **Orchestrator:** —
  - **Plugin prioritas:** karpathy-skills

- **Pola prompt user:** "audit perf", "lighthouse", "a11y"
  - **Orchestrator:** —
  - **Plugin prioritas:** agent-skills-addyosmani

- **Pola prompt user:** "knowledge graph", "extract entity"
  - **Orchestrator:** —
  - **Plugin prioritas:** graphify

- **Pola prompt user:** "jelaskan", "apa itu", "investigate", "telusuri"
  - **Orchestrator:** —
  - **Plugin prioritas:** understand-anything

- **Pola prompt user:** "recent", "last 30 days", "trend"
  - **Orchestrator:** —
  - **Plugin prioritas:** last-30-days

- **Pola prompt user:** "compress prompt", "token budget"
  - **Orchestrator:** —
  - **Plugin prioritas:** gstack (lalu caveman bila ekstrem)

- **Pola prompt user:** "design system", "design tokens"
  - **Orchestrator:** —
  - **Plugin prioritas:** ui-ux-pro-max

- **Pola prompt user:** "polish UI", "alignment"
  - **Orchestrator:** —
  - **Plugin prioritas:** impeccable

- **Pola prompt user:** "slide", "deck", "presentation"
  - **Orchestrator:** —
  - **Plugin prioritas:** ppt-master

- **Pola prompt user:** "diagram", "flowchart"
  - **Orchestrator:** —
  - **Plugin prioritas:** diagram-design

- **Pola prompt user:** "video edit", "montage", "reels"
  - **Orchestrator:** —
  - **Plugin prioritas:** openmontage

- **Pola prompt user:** "talking head", "voice clone"
  - **Orchestrator:** —
  - **Plugin prioritas:** hyperframes (WAJIB consent gate)

- **Pola prompt user:** "humanize", "terlalu AI"
  - **Orchestrator:** —
  - **Plugin prioritas:** humanizer

### Aturan Konflik

1. **Orchestrator menang** bila pola orchestrator match. Plugin lain jadi
   sub-task.
2. **Skill resmi Anthropic menang** untuk intent format-file dan teknis
   spesifik (mis. "extract pdf form fields" pasti ke pdf, bukan plugin).
3. **Format file > plugin desain**: "make a beautiful deck/presentation"
   (tanpa sebut format) -> ppt-master; tapi begitu `.pptx`/"powerpoint"
   disebut -> pptx (skill resmi menangani file-nya).
4. **Plugin spesifik menang** bila trigger eksplisit (mis. "clone app" pasti ke
   replica-skill).
5. **Fallback default**: `none` — bila tidak ada pola yang cocok, gunakan
   ordinary agent tools. Jangan memaksakan skill katalog ke tugas yang tidak
   relevan (routing lama ke "rea" salah: REA adalah skill reverse engineering,
   bukan orchestrator riset umum).

Pemetaan menyeluruh lintas tier (skills + plugins + MCP sekaligus):
`python3 unified-integration/scripts/registry.py map "<task>"`.

### Aturan Komposisi

| Source | Target | Mekanisme |
| -------- | -------- | ----------- |
| bmad-method | mattpocock / addyosmani / replica-build | story ke code task |
| agent-reach | graphify | sources ke citation graph |
| replica-entrepreneur | replica-build | keluhan user ke fix plan |
| ui-ux-pro-max | impeccable | spec ke polish audit |
| ppt-master | humanizer | draft notes ke naturalize |
| gstack | caveman | context compress ke instruction compress |
| openmontage | hyperframes | master cut ke personalized variant |

### Mode Operasi

- `--dry-run` — hanya print rencana dispatch.
- default — cetak rencana dan path panduan; script tidak menjalankan agent
  atau mengaktifkan runtime plugin. Agent membaca panduan dan mengambil
  tindakan melalui izin host yang normal.

### Override Eksplisit

```text
[skill:replica-skill] clone aplikasi booking
```

Dispatcher deteksi prefix `[skill:X]` dan langsung pakai, skip heuristic.

### Audit

Setiap dispatch sebaiknya log via `scripts/audit-trail.sh decision` bila
menghasilkan keputusan non-trivial.
