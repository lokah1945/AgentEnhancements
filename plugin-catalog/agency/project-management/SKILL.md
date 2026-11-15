---
slug: project-management
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [project manager, sprint planning, jira, meeting notes, scoping]
---

# The Agency — Project Management Division

7 persona project management dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Experiment Tracker, Jira Workflow Steward, Meeting Notes Specialist, Project Shepherd, Studio Operations, Studio Producer, Senior Project Manager.

## Kapan dipakai

- Task yang cocok dengan project management butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/project-management/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Experiment Tracker** — lihat `agency-agents/skills/project-management/project-management-experiment-tracker/SKILL.md`
2. **Jira Workflow Steward** — lihat `agency-agents/skills/project-management/project-management-jira-workflow-steward/SKILL.md`
3. **Meeting Notes Specialist** — lihat `agency-agents/skills/project-management/project-management-meeting-notes-specialist/SKILL.md`
4. **Project Shepherd** — lihat `agency-agents/skills/project-management/project-management-project-shepherd/SKILL.md`
5. **Studio Operations** — lihat `agency-agents/skills/project-management/project-management-studio-operations/SKILL.md`
6. **Studio Producer** — lihat `agency-agents/skills/project-management/project-management-studio-producer/SKILL.md`
7. **Senior Project Manager** — lihat `agency-agents/skills/project-management/project-manager-senior/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/project-management/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
