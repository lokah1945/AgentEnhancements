---
title: Router Policy
version: 1.2
last_updated: 2026-11-15
audience: all agents
---

# Router Policy — Orchestrator Dispatcher

Mendefinisikan kapan setiap orchestrator / plugin / skill resmi Anthropic
dipanggil. Implementasi heuristic ada di `unified-integration/scripts/dispatch.sh`.

## Hierarki Dispatch

Dispatch berlapis: **orchestrator** (BMAD / GSD untuk mode eksekusi besar, REA
untuk analisis rekayasa balik) lebih dulu, lalu **skill resmi Anthropic** untuk
intent yang sangat spesifik (format file, MCP, skill engineering, testing, API),
lalu **plugin spesifik** per sub-task. Prompt yang tidak cocok kategori mana pun
jatuh ke **ordinary tools** (abstain jujur), bukan dipaksakan ke satu skill.

```
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

## Tabel Policy

| Pola prompt user | Orchestrator | Plugin prioritas |
|------------------|--------------|-------------------|
| "build product", "greenfield", "dari nol" | bmad-method | — (BMAD invoke sendiri) |
| "kerjakan semua", "do all", "clear backlog" | gsd | — (GSD invoke per task) |
| "reverse engineer", "decompile", "disassemble", "binary/APK analysis" | rea (Reverse Engineer Anything) | — (butuh server upstream morluto/rea) |
| "build / integrate mcp server", "model context protocol" | — | mcp-builder (skill resmi) |
| "create / improve / eval a skill", "buat skill" | — | skill-creator (skill resmi) |
| "test webapp", "playwright", "browser screenshot" | — | webapp-testing (skill resmi) |
| "claude api", "anthropic api", "claude sdk" | — | claude-api (skill resmi) |
| sebut `.docx` / `.dotx` / "word document" | — | docx (skill resmi) |
| sebut `.pdf` / "pdf" | — | pdf (skill resmi) |
| sebut `.pptx` / `.potx` / "powerpoint" | — | pptx (skill resmi) |
| sebut `.xlsx` / `.csv` / "excel" / "spreadsheet" | — | xlsx (skill resmi) |
| "clone app X", "build my own version" | — | replica-skill (11 sub-skill berurutan; REA untuk analisis, replica untuk rebuild) |
| "research <topik>", "compare X vs Y" | — | agent-reach (deep research), graphify, last-30-days |
| "refactor TS", "ketatkan types" | — | mattpocock-skills |
| "prototype", "sketch", "numpy" | — | karpathy-skills |
| "audit perf", "lighthouse", "a11y" | — | agent-skills-addyosmani |
| "knowledge graph", "extract entity" | — | graphify |
| "jelaskan", "apa itu", "investigate", "telusuri" | — | understand-anything |
| "recent", "last 30 days", "trend" | — | last-30-days |
| "compress prompt", "token budget" | — | gstack (lalu caveman bila ekstrem) |
| "design system", "design tokens" | — | ui-ux-pro-max |
| "polish UI", "alignment" | — | impeccable |
| "slide", "deck", "presentation" | — | ppt-master |
| "diagram", "flowchart" | — | diagram-design |
| "video edit", "montage", "reels" | — | openmontage |
| "talking head", "voice clone" | — | hyperframes (WAJIB consent gate) |
| "humanize", "terlalu AI" | — | humanizer |

## Aturan Konflik

1. **Orchestrator menang** bila pola orchestrator match. Plugin lain jadi sub-task.
2. **Skill resmi Anthropic menang** untuk intent format-file dan teknis
   spesifik (mis. "extract pdf form fields" pasti ke pdf, bukan plugin).
3. **Format file > plugin desain**: "make a beautiful deck/presentation"
   (tanpa sebut format) -> ppt-master; tapi begitu `.pptx`/"powerpoint"
   disebut -> pptx (skill resmi menangani file-nya).
4. **Plugin spesifik menang** bila trigger eksplisit (mis. "clone app" pasti ke replica-skill).
5. **Fallback default**: `none` — bila tidak ada pola yang cocok, gunakan
   ordinary agent tools. Jangan memaksakan skill katalog ke tugas yang tidak
   relevan (routing lama ke "rea" salah: REA adalah skill reverse engineering,
   bukan orchestrator riset umum).

Pemetaan menyeluruh lintas tier (skills + plugins + MCP sekaligus):
`python3 unified-integration/scripts/registry.py map "<task>"`.

## Aturan Komposisi

| Source | Target | Mekanisme |
|--------|--------|-----------|
| bmad-method | mattpocock / addyosmani / replica-build | story ke code task |
| agent-reach | graphify | sources ke citation graph |
| replica-entrepreneur | replica-build | keluhan user ke fix plan |
| ui-ux-pro-max | impeccable | spec ke polish audit |
| ppt-master | humanizer | draft notes ke naturalize |
| gstack | caveman | context compress ke instruction compress |
| openmontage | hyperframes | master cut ke personalized variant |

## Mode Operasi

- `--dry-run` — hanya print rencana dispatch.
- default — baca SKILL.md target lalu invoke agent runtime.

## Override Eksplisit

```
[skill:replica-skill] clone aplikasi booking
```

Dispatcher deteksi prefix `[skill:X]` dan langsung pakai, skip heuristic.

## Audit

Setiap dispatch sebaiknya log via `scripts/audit-trail.sh decision` bila
menghasilkan keputusan non-trivial.
