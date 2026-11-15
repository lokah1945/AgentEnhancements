---
slug: support
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [customer support, analytics, finance tracker, legal compliance, executive summary]
---

# The Agency — Support Division

6 persona support dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Analytics Reporter, Executive Summary Generator, Finance Tracker, Infrastructure Maintainer, Legal Compliance Checker, Support Responder.

## Kapan dipakai

- Task yang cocok dengan support butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/support/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Analytics Reporter** — lihat `agency-agents/skills/support/support-analytics-reporter/SKILL.md`
2. **Executive Summary Generator** — lihat `agency-agents/skills/support/support-executive-summary-generator/SKILL.md`
3. **Finance Tracker** — lihat `agency-agents/skills/support/support-finance-tracker/SKILL.md`
4. **Infrastructure Maintainer** — lihat `agency-agents/skills/support/support-infrastructure-maintainer/SKILL.md`
5. **Legal Compliance Checker** — lihat `agency-agents/skills/support/support-legal-compliance-checker/SKILL.md`
6. **Support Responder** — lihat `agency-agents/skills/support/support-support-responder/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/support/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
