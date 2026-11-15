---
slug: spatial-computing
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [visionos, webxr, ar, vr, spatial ui]
---

# The Agency — Spatial Computing Division

6 persona spatial computing dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: macOS Spatial/Metal Engineer, Terminal Integration Specialist, visionOS Spatial Engineer, XR Cockpit Interaction Specialist, XR Immersive Developer, XR Interface Architect.

## Kapan dipakai

- Task yang cocok dengan spatial computing butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/spatial-computing/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **macOS Spatial/Metal Engineer** — lihat `agency-agents/skills/spatial-computing/macos-spatial-metal-engineer/SKILL.md`
2. **Terminal Integration Specialist** — lihat `agency-agents/skills/spatial-computing/terminal-integration-specialist/SKILL.md`
3. **visionOS Spatial Engineer** — lihat `agency-agents/skills/spatial-computing/visionos-spatial-engineer/SKILL.md`
4. **XR Cockpit Interaction Specialist** — lihat `agency-agents/skills/spatial-computing/xr-cockpit-interaction-specialist/SKILL.md`
5. **XR Immersive Developer** — lihat `agency-agents/skills/spatial-computing/xr-immersive-developer/SKILL.md`
6. **XR Interface Architect** — lihat `agency-agents/skills/spatial-computing/xr-interface-architect/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/spatial-computing/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
