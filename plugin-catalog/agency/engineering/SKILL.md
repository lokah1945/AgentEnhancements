---
slug: engineering
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [frontend developer, backend architect, devops, code review, sre]
---

# The Agency — Engineering Division

66 persona engineering dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: AI Data Remediation Engineer, AI Engineer, API Platform Engineer, ATS Validator Architect, Autonomous Optimization Architect, Backend Architect, China Network Engineer, CMS Developer.

## Kapan dipakai

- Task yang cocok dengan engineering butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/engineering/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **AI Data Remediation Engineer** — lihat `agency-agents/skills/engineering/engineering-ai-data-remediation-engineer/SKILL.md`
2. **AI Engineer** — lihat `agency-agents/skills/engineering/engineering-ai-engineer/SKILL.md`
3. **API Platform Engineer** — lihat `agency-agents/skills/engineering/engineering-api-platform-engineer/SKILL.md`
4. **ATS Validator Architect** — lihat `agency-agents/skills/engineering/engineering-ats-validator-architect/SKILL.md`
5. **Autonomous Optimization Architect** — lihat `agency-agents/skills/engineering/engineering-autonomous-optimization-architect/SKILL.md`
6. **Backend Architect** — lihat `agency-agents/skills/engineering/engineering-backend-architect/SKILL.md`
7. **China Network Engineer** — lihat `agency-agents/skills/engineering/engineering-china-network-engineer/SKILL.md`
8. **CMS Developer** — lihat `agency-agents/skills/engineering/engineering-cms-developer/SKILL.md`
9. **Code Reviewer** — lihat `agency-agents/skills/engineering/engineering-code-reviewer/SKILL.md`
10. **Codebase Onboarding Engineer** — lihat `agency-agents/skills/engineering/engineering-codebase-onboarding-engineer/SKILL.md`
11. **Data Engineer** — lihat `agency-agents/skills/engineering/engineering-data-engineer/SKILL.md`
12. **Data Visualization Engineer** — lihat `agency-agents/skills/engineering/engineering-data-visualization-engineer/SKILL.md`
13. ... dan 54 persona lainnya (lihat manifest.json)

## Workflow

1. Pilih persona dari `agency-agents/skills/engineering/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
