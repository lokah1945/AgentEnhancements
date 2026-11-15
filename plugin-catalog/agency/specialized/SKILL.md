---
slug: specialized
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [mcp builder, orchestrator, translation, customer service, legal review]
---

# The Agency — Specialized Division

59 persona specialized dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Accounts Payable Agent, Agentic Identity & Trust Architect, Agents Orchestrator, Automation Governance Architect, Business Strategist, Change Management Consultant, Chief Financial Officer, Corporate Training Designer.

## Kapan dipakai

- Task yang cocok dengan specialized butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/specialized/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Accounts Payable Agent** — lihat `agency-agents/skills/specialized/accounts-payable-agent/SKILL.md`
2. **Agentic Identity & Trust Architect** — lihat `agency-agents/skills/specialized/agentic-identity-trust/SKILL.md`
3. **Agents Orchestrator** — lihat `agency-agents/skills/specialized/agents-orchestrator/SKILL.md`
4. **Automation Governance Architect** — lihat `agency-agents/skills/specialized/automation-governance-architect/SKILL.md`
5. **Business Strategist** — lihat `agency-agents/skills/specialized/business-strategist/SKILL.md`
6. **Change Management Consultant** — lihat `agency-agents/skills/specialized/change-management-consultant/SKILL.md`
7. **Chief Financial Officer** — lihat `agency-agents/skills/specialized/chief-financial-officer/SKILL.md`
8. **Corporate Training Designer** — lihat `agency-agents/skills/specialized/corporate-training-designer/SKILL.md`
9. **Customer Service** — lihat `agency-agents/skills/specialized/customer-service/SKILL.md`
10. **Customer Success Manager** — lihat `agency-agents/skills/specialized/customer-success-manager/SKILL.md`
11. **Data Consolidation Agent** — lihat `agency-agents/skills/specialized/data-consolidation-agent/SKILL.md`
12. **Data Privacy Officer** — lihat `agency-agents/skills/specialized/data-privacy-officer/SKILL.md`
13. ... dan 47 persona lainnya (lihat manifest.json)

## Workflow

1. Pilih persona dari `agency-agents/skills/specialized/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
