---
slug: sales
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [outbound, discovery call, meddpicc, proposal, pipeline]
---

# The Agency — Sales Division

9 persona sales dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Account Strategist, Sales Coach, Deal Strategist, Discovery Coach, Sales Engineer, Offer & Lead Gen Strategist, Outbound Strategist, Pipeline Analyst.

## Kapan dipakai

- Task yang cocok dengan sales butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/sales/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Account Strategist** — lihat `agency-agents/skills/sales/sales-account-strategist/SKILL.md`
2. **Sales Coach** — lihat `agency-agents/skills/sales/sales-coach/SKILL.md`
3. **Deal Strategist** — lihat `agency-agents/skills/sales/sales-deal-strategist/SKILL.md`
4. **Discovery Coach** — lihat `agency-agents/skills/sales/sales-discovery-coach/SKILL.md`
5. **Sales Engineer** — lihat `agency-agents/skills/sales/sales-engineer/SKILL.md`
6. **Offer & Lead Gen Strategist** — lihat `agency-agents/skills/sales/sales-offer-lead-gen-strategist/SKILL.md`
7. **Outbound Strategist** — lihat `agency-agents/skills/sales/sales-outbound-strategist/SKILL.md`
8. **Pipeline Analyst** — lihat `agency-agents/skills/sales/sales-pipeline-analyst/SKILL.md`
9. **Proposal Strategist** — lihat `agency-agents/skills/sales/sales-proposal-strategist/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/sales/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
