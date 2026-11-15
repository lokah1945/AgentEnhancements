---
slug: finance
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [bookkeeper, financial analyst, fpa, investment research, tax strategy]
---

# The Agency — Finance Division

5 persona finance dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Bookkeeper & Controller, Financial Analyst, FP&A Analyst, Investment Researcher, Tax Strategist.

## Kapan dipakai

- Task yang cocok dengan finance butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/finance/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Bookkeeper & Controller** — lihat `agency-agents/skills/finance/finance-bookkeeper-controller/SKILL.md`
2. **Financial Analyst** — lihat `agency-agents/skills/finance/finance-financial-analyst/SKILL.md`
3. **FP&A Analyst** — lihat `agency-agents/skills/finance/finance-fpa-analyst/SKILL.md`
4. **Investment Researcher** — lihat `agency-agents/skills/finance/finance-investment-researcher/SKILL.md`
5. **Tax Strategist** — lihat `agency-agents/skills/finance/finance-tax-strategist/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/finance/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
