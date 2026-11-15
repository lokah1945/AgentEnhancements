---
slug: paid-media
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [ppc, google ads, paid social, conversion tracking, ad creative]
---

# The Agency — Paid Media Division

7 persona paid media dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Paid Media Auditor, Ad Creative Strategist, Paid Social Strategist, PPC Campaign Strategist, Programmatic & Display Buyer, Search Query Analyst, Tracking & Measurement Specialist.

## Kapan dipakai

- Task yang cocok dengan paid media butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/paid-media/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Paid Media Auditor** — lihat `agency-agents/skills/paid-media/paid-media-auditor/SKILL.md`
2. **Ad Creative Strategist** — lihat `agency-agents/skills/paid-media/paid-media-creative-strategist/SKILL.md`
3. **Paid Social Strategist** — lihat `agency-agents/skills/paid-media/paid-media-paid-social-strategist/SKILL.md`
4. **PPC Campaign Strategist** — lihat `agency-agents/skills/paid-media/paid-media-ppc-strategist/SKILL.md`
5. **Programmatic & Display Buyer** — lihat `agency-agents/skills/paid-media/paid-media-programmatic-buyer/SKILL.md`
6. **Search Query Analyst** — lihat `agency-agents/skills/paid-media/paid-media-search-query-analyst/SKILL.md`
7. **Tracking & Measurement Specialist** — lihat `agency-agents/skills/paid-media/paid-media-tracking-specialist/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/paid-media/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
