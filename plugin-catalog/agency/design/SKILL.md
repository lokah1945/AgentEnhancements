---
slug: design
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [ui designer, ux research, design system, brand identity, visual storytelling]
---

# The Agency — Design Division

10 persona design dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Brand Guardian, Image Prompt Engineer, Inclusive Visuals Specialist, Persona Walkthrough Specialist, UI Designer, UI Finish-Gate Reviewer, UX Architect, UX Researcher.

## Kapan dipakai

- Task yang cocok dengan design butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/design/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Brand Guardian** — lihat `agency-agents/skills/design/design-brand-guardian/SKILL.md`
2. **Image Prompt Engineer** — lihat `agency-agents/skills/design/design-image-prompt-engineer/SKILL.md`
3. **Inclusive Visuals Specialist** — lihat `agency-agents/skills/design/design-inclusive-visuals-specialist/SKILL.md`
4. **Persona Walkthrough Specialist** — lihat `agency-agents/skills/design/design-persona-walkthrough/SKILL.md`
5. **UI Designer** — lihat `agency-agents/skills/design/design-ui-designer/SKILL.md`
6. **UI Finish-Gate Reviewer** — lihat `agency-agents/skills/design/design-ui-finish-gate-reviewer/SKILL.md`
7. **UX Architect** — lihat `agency-agents/skills/design/design-ux-architect/SKILL.md`
8. **UX Researcher** — lihat `agency-agents/skills/design/design-ux-researcher/SKILL.md`
9. **Visual Storyteller** — lihat `agency-agents/skills/design/design-visual-storyteller/SKILL.md`
10. **Whimsy Injector** — lihat `agency-agents/skills/design/design-whimsy-injector/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/design/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
