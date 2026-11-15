---
slug: research
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [literature review, research synthesist, evidence synthesis, citation]
---

# The Agency — Research Division

1 persona research dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Research Synthesist.

## Kapan dipakai

- Task yang cocok dengan research butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/research/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Research Synthesist** — lihat `agency-agents/skills/research/research-synthesist/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/research/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
