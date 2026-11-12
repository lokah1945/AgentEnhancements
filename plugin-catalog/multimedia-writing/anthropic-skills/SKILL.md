---
slug: anthropic-skills
category: multimedia-writing
version: 1.1.0
status: integrated
mcp_servers: [filesystem-mcp, pdf-mcp, vision-mcp]
trigger_keywords: [anthropic, docx, word document, pdf, pptx, powerpoint, xlsx, excel, spreadsheet, mcp server, skill creator, webapp testing, claude api]
---

# Anthropic Skills (19 official skills, vendored)

Skill resmi dari Anthropic (https://github.com/anthropics/skills), di-vendor penuh di `anthropic-skills/` dan **sudah aktif otomatis** setelah satu kali install: ter-agregasi ke unified index, ter-link native ke `~/.claude/skills/` dan `~/.agents/skills/`, dan bisa dipetakan lewat `registry.py`.

## Isi (19 skill)

| Kelompok | Skill |
|----------|-------|
| **Document skills** (yang menyalakan document capabilities Claude) | `docx`, `pdf`, `pptx`, `xlsx` |
| **Skill engineering** | `skill-creator` |
| **MCP** | `mcp-builder` |
| **Testing** | `webapp-testing` (Playwright) |
| **API/SDK** | `claude-api` |
| **Desain & kreatif** | `frontend-design`, `brand-guidelines`, `canvas-design`, `theme-factory`, `algorithmic-art` |
| **Komunikasi & konten** | `internal-comms`, `doc-coauthoring`, `slack-gif-creator` |
| **Lainnya** | `web-artifacts-builder`, `academy-guide`, `discernment-nudge` |

## Kapan dipakai

- User menyebut file `.docx/.dotx`, `.pdf`, `.pptx/.potx`, `.xlsx/.xlsm/.csv/.tsv` — pakai skill format terkait (paling spesifik).
- Membuat/memperbaiki/evaluasi skill — `skill-creator`.
- Membangun MCP server — `mcp-builder`.
- Test web app lokal + screenshot + log browser — `webapp-testing`.
- Integrasi Claude API/SDK — `claude-api`.

## Prasyarat

- Sudah otomatis terpenuhi oleh `setup.sh` (skill ter-link native; lihat `link-skills.sh --status`).
- `webapp-testing` butuh Playwright ter-install di environment.
- Document skills memakai Python library (python-docx, openpyxl, pdfplumber, dll.) yang di-install on-demand oleh script skill.

## Aktivasi

```bash
# Semua sudah otomatis setelah setup.sh. Manual (bila perlu):
bash unified-integration/scripts/link-skills.sh --set anthropic-skills

# Pemetaan task -> skill/plugin/MCP:
python3 unified-integration/scripts/registry.py map "create a word document"

# Routing natural-language:
bash unified-integration/scripts/dispatch.sh --dry-run "extract pdf form fields"
```

Claude Code juga bisa memakai marketplace upstream: `/plugin marketplace add anthropics/skills`.

## Workflow (contoh)

1. **Dokumen**: deteksi format dari prompt → load `anthropic-skills/skills/<format>/SKILL.md` → ikuti instruksinya (script helper tersedia di folder skill).
2. **Skill baru**: `skill-creator` menuntun struktur SKILL.md, frontmatter, evaluasi, dan optimasi deskripsi.
3. **MCP server**: `mcp-builder` memberi pola FastMCP/MCP SDK untuk tools yang berkualitas.

## Batasan & Keamanan

- Document skills menjalankan script Python yang menulis file - jalankan di workspace user saja.
- `webapp-testing` menyalakan browser lokal; jangan arahkan ke situs produksi.
- Skill edukasi/demo dari upstream: selalu uji di environment sendiri sebelum dipakai kritikal (disclaimer upstream).

## Catatan integrasi

- Vendored verbatim (Apache-2.0, `LICENSE.txt` per skill; `THIRD_PARTY_NOTICES.md` di root vendor).
- Diagregasi **terakhir** sehingga menang name collision atas salinan pihak ketiga di agentic-awesome-skills.
- Diindeks di `all-skills.json` (source `anthropic-skills`) + `agent-registry.json`.
- Update: re-vendor dari upstream (lihat `docs/UPDATING.md`).
