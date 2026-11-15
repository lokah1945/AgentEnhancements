---
slug: academic
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [worldbuilding, narrative design, story structure, cultural systems, statistical analysis]
---

# The Agency — Academic Division

6 persona academic dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Anthropologist, Geographer, Historian, Narratologist, Psychologist, Statistician.

## Kapan dipakai

- Task yang cocok dengan academic butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/academic/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Anthropologist** — lihat `agency-agents/skills/academic/academic-anthropologist/SKILL.md`
2. **Geographer** — lihat `agency-agents/skills/academic/academic-geographer/SKILL.md`
3. **Historian** — lihat `agency-agents/skills/academic/academic-historian/SKILL.md`
4. **Narratologist** — lihat `agency-agents/skills/academic/academic-narratologist/SKILL.md`
5. **Psychologist** — lihat `agency-agents/skills/academic/academic-psychologist/SKILL.md`
6. **Statistician** — lihat `agency-agents/skills/academic/academic-statistician/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/academic/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
