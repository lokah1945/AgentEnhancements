---
slug: healthcare
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [clinical evidence, healthcare compliance, sovereign health]
---

# The Agency — Healthcare Division

3 persona healthcare dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Clinical Evidence Agent, Healthcare Innovation Strategist, Sovereign Health Systems Agent.

## Kapan dipakai

- Task yang cocok dengan healthcare butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/healthcare/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Clinical Evidence Agent** — lihat `agency-agents/skills/healthcare/healthcare-clinical-evidence-agent/SKILL.md`
2. **Healthcare Innovation Strategist** — lihat `agency-agents/skills/healthcare/healthcare-innovation-strategist/SKILL.md`
3. **Sovereign Health Systems Agent** — lihat `agency-agents/skills/healthcare/healthcare-sovereign-health-systems-agent/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/healthcare/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
