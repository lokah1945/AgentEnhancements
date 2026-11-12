# AgentEnhancements — Skills Catalog v2

Katalog plugin eksternal yang terintegrasi dengan repo. Berdampingan dengan `unified-integration/skills/by-category/` (registry hasil agregasi). Total **21 plugin sources** — 20 berupa manifest remote + 1 di-vendor penuh (replica-skill, 11 sub-skill).

## Struktur

```
skills/
├── code/                  # 4 plugins: Matt Pocock, Karpathy, Addy Osmani, Replica
├── research/              # 5 plugins: Graphify, Agent-Reach, Understand Anything, Last 30 Days, REA
├── tokens-optimization/   # 4 plugins: GStack, Caveman, GSD, BMAD Method
├── design/                # 4 plugins: UI UX Pro Max, Impeccable, PPT Master, Diagram Design
└── multimedia-writing/    # 4 plugins: Anthropic, OpenMontage, Hyperframes, Humanizer

File pendukung: `catalog.json` (index katalog), `mcp-servers.json` (roadmap MCP per plugin).
```

Setiap folder kategori berisi:
- `README.md` — ringkasan kategori dan daftar plugin
- `<plugin-slug>.json` — manifest skill (metadata, source URL, tools, MCP suggestion)
- `<plugin-slug>/SKILL.md` — panduan integrasi (workflow, contoh, batasan)

## Konvensi manifest

Tiap manifest memakai schema `skill-manifest.v1.json` dengan field:
- `id`, `name`, `slug`, `category`, `version`
- `status`: `to-integrate` | `integrated` | `deprecated`
- `source`: GitHub URL asal
- `capabilities`: array string
- `tools_required`: tools agent yang dibutuhkan
- `mcp_servers_suggested`: MCP server yang perlu dibangun
- `trigger_keywords`: kata kunci yang memantik skill
- `best_for`: use-case ideal
- `integration_notes`: catatan teknis pemasangan

## Cara aktivasi

1. Pilih plugin → buka JSON manifest-nya.
2. Jalankan `bash unified-integration/scripts/catalog-wire.sh` untuk symlink katalog ke `unified-integration/skills/by-category/`.
3. Daftarkan MCP server di `.claude/mcp.json` sesuai `mcp_servers_suggested`.
4. Tandai `status: "integrated"` di manifest.

Lihat juga: [INTEGRATION_CHECKLIST.md](../docs/INTEGRATION_CHECKLIST.md)
