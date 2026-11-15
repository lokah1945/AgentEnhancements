---
slug: product
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [product manager, prioritization, user feedback, dx engineer, roadmap]
---

# The Agency — Product Division

6 persona product dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Behavioral Nudge Engine, DX Engineer, Feedback Synthesizer, Product Manager, Sprint Prioritizer, Trend Researcher.

## Kapan dipakai

- Task yang cocok dengan product butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/product/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Behavioral Nudge Engine** — lihat `agency-agents/skills/product/product-behavioral-nudge-engine/SKILL.md`
2. **DX Engineer** — lihat `agency-agents/skills/product/product-dx-engineer/SKILL.md`
3. **Feedback Synthesizer** — lihat `agency-agents/skills/product/product-feedback-synthesizer/SKILL.md`
4. **Product Manager** — lihat `agency-agents/skills/product/product-manager/SKILL.md`
5. **Sprint Prioritizer** — lihat `agency-agents/skills/product/product-sprint-prioritizer/SKILL.md`
6. **Trend Researcher** — lihat `agency-agents/skills/product/product-trend-researcher/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/product/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
