---
slug: gis
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [gis, arcgis, maplibre, spatial data, bim]
---

# The Agency — GIS Division

13 persona gis dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: 3D & Scene Developer, GIS Analyst, BIM/GIS Specialist, Cartography Designer, Drone/Reality Mapping Specialist, GeoAI/ML Engineer, Geoprocessing Specialist, GIS QA Engineer.

## Kapan dipakai

- Task yang cocok dengan gis butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/gis/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **3D & Scene Developer** — lihat `agency-agents/skills/gis/gis-3d-scene-developer/SKILL.md`
2. **GIS Analyst** — lihat `agency-agents/skills/gis/gis-analyst/SKILL.md`
3. **BIM/GIS Specialist** — lihat `agency-agents/skills/gis/gis-bim-specialist/SKILL.md`
4. **Cartography Designer** — lihat `agency-agents/skills/gis/gis-cartography-designer/SKILL.md`
5. **Drone/Reality Mapping Specialist** — lihat `agency-agents/skills/gis/gis-drone-reality-mapping/SKILL.md`
6. **GeoAI/ML Engineer** — lihat `agency-agents/skills/gis/gis-geoai-ml-engineer/SKILL.md`
7. **Geoprocessing Specialist** — lihat `agency-agents/skills/gis/gis-geoprocessing-specialist/SKILL.md`
8. **GIS QA Engineer** — lihat `agency-agents/skills/gis/gis-qa-engineer/SKILL.md`
9. **Solution Engineer** — lihat `agency-agents/skills/gis/gis-solution-engineer/SKILL.md`
10. **Spatial Data Engineer** — lihat `agency-agents/skills/gis/gis-spatial-data-engineer/SKILL.md`
11. **Spatial Data Scientist** — lihat `agency-agents/skills/gis/gis-spatial-data-scientist/SKILL.md`
12. **Technical Consultant** — lihat `agency-agents/skills/gis/gis-technical-consultant/SKILL.md`
13. ... dan 1 persona lainnya (lihat manifest.json)

## Workflow

1. Pilih persona dari `agency-agents/skills/gis/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
