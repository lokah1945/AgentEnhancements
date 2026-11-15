---
slug: game-development
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [game designer, unity, unreal engine, godot, roblox]
---

# The Agency — Game Development Division

21 persona game development dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Blender Add-on Engineer, Economy Designer, Game Audio Engineer, Game Designer, Godot Gameplay Scripter, Godot Multiplayer Engineer, Godot Shader Developer, Level Designer.

## Kapan dipakai

- Task yang cocok dengan game development butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/game-development/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Blender Add-on Engineer** — lihat `agency-agents/skills/game-development/blender-addon-engineer/SKILL.md`
2. **Economy Designer** — lihat `agency-agents/skills/game-development/economy-designer/SKILL.md`
3. **Game Audio Engineer** — lihat `agency-agents/skills/game-development/game-audio-engineer/SKILL.md`
4. **Game Designer** — lihat `agency-agents/skills/game-development/game-designer/SKILL.md`
5. **Godot Gameplay Scripter** — lihat `agency-agents/skills/game-development/godot-gameplay-scripter/SKILL.md`
6. **Godot Multiplayer Engineer** — lihat `agency-agents/skills/game-development/godot-multiplayer-engineer/SKILL.md`
7. **Godot Shader Developer** — lihat `agency-agents/skills/game-development/godot-shader-developer/SKILL.md`
8. **Level Designer** — lihat `agency-agents/skills/game-development/level-designer/SKILL.md`
9. **Narrative Designer** — lihat `agency-agents/skills/game-development/narrative-designer/SKILL.md`
10. **Roblox Avatar Creator** — lihat `agency-agents/skills/game-development/roblox-avatar-creator/SKILL.md`
11. **Roblox Experience Designer** — lihat `agency-agents/skills/game-development/roblox-experience-designer/SKILL.md`
12. **Roblox Systems Scripter** — lihat `agency-agents/skills/game-development/roblox-systems-scripter/SKILL.md`
13. ... dan 9 persona lainnya (lihat manifest.json)

## Workflow

1. Pilih persona dari `agency-agents/skills/game-development/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
