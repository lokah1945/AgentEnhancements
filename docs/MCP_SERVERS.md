---
title: MCP Server Roadmap
version: 1.1
last_updated: 2026-11-14
audience: all agents and maintainers
---

# MCP Servers Roadmap & Matrix

Konfigurasi mesin terbaca: `plugin-catalog/mcp-servers.json` (38 server,
prioritas P0/P1/P2). File ini adalah dokumentasi + matriks relasi plugin ke MCP.

## Distribusi prioritas

| Prioritas | Jumlah | Arti |
|-----------|--------|------|
| P0 | 5 | Wajib sebelum plugin dasar jalan (filesystem, memory, brave-search, browser-tools) |
| P1 | 22 | Mengaktifkan plugin utuh |
| P2 | 11 | Nice-to-have / cadangan |

## Matriks: Plugin ke MCP

| Plugin | MCP wajib | MCP opsional |
|--------|-----------|--------------|
| replica-skill | — (stdlib Python) | browser-tools-mcp, vision-mcp |
| mattpocock-skills | typescript-language-server-mcp, eslint-mcp | — |
| karpathy-skills | jupyter-mcp, python-repl-mcp | embeddings-mcp |
| agent-skills-addyosmani | browser-tools-mcp, lighthouse-mcp | pa11y-mcp |
| graphify | neo4j-mcp | graphrag-mcp, embeddings-mcp |
| agent-reach | brave-search-mcp | tavily-mcp, exa-mcp, firecrawl-mcp |
| understand-anything | wikipedia-mcp | arxiv-mcp, embeddings-mcp |
| last-30-days | brave-search-mcp | newsapi-mcp, google-news-mcp |
| rea | task-router-mcp, memory-mcp | — |
| gstack | llm-cache-mcp | tokenizer-mcp |
| caveman | tokenizer-mcp | — |
| gsd | task-router-mcp, memory-mcp | github-issues-mcp |
| bmad-method | memory-mcp | github-issues-mcp, linear-mcp |
| ui-ux-pro-max | figma-mcp | browser-tools-mcp, storybook-mcp |
| impeccable | browser-tools-mcp | figma-mcp |
| ppt-master | google-slides-mcp atau office-mcp | image-search-mcp |
| diagram-design | mermaid-mcp | excalidraw-mcp |
| anthropic-skills | filesystem-mcp | pdf-mcp, vision-mcp |
| openmontage | ffmpeg-mcp | video-mcp |
| hyperframes | heygen-mcp, elevenlabs-mcp | voice-clone-mcp |
| humanizer | style-mcp | grammar-mcp |

## Matriks: MCP ke Plugin (reverse)

| MCP server | Dipakai oleh |
|------------|--------------|
| filesystem-mcp | anthropic-skills + semua (baseline) |
| memory-mcp | rea, gsd, bmad-method, anthropic-skills |
| brave-search-mcp | agent-reach, last-30-days, rea, understand-anything |
| browser-tools-mcp | agent-skills-addyosmani, impeccable, ui-ux-pro-max, replica-skill |
| vision-mcp | anthropic-skills, impeccable, replica-skill |
| typescript-language-server-mcp | mattpocock-skills, agent-skills-addyosmani |
| eslint-mcp | mattpocock-skills, agent-skills-addyosmani |
| jupyter-mcp / python-repl-mcp | karpathy-skills |
| neo4j-mcp | graphify |
| figma-mcp | ui-ux-pro-max, impeccable |
| lighthouse-mcp / pa11y-mcp | agent-skills-addyosmani |
| mermaid-mcp / excalidraw-mcp | diagram-design |
| google-slides-mcp / office-mcp / image-search-mcp | ppt-master, diagram-design |
| ffmpeg-mcp / video-mcp | openmontage |
| heygen-mcp / elevenlabs-mcp / voice-clone-mcp | hyperframes, openmontage |
| style-mcp / grammar-mcp | humanizer |

## Instalasi native

`setup.sh` memasang sembilan MCP bawaan secara otomatis. Claude Code memakai
`~/.claude.json` untuk user scope; Codex memakai `~/.codex/config.toml`;
OpenCode memakai `~/.config/opencode/opencode.json(c)`. Config pribadi dan
server pengguna dipertahankan. `.claude/mcp.json` bukan lokasi native Claude.

Server P0 eksternal dan server katalog lain memerlukan paket, akun, kredensial
serta argumen masing-masing. Gunakan ID dari `mcp-servers.json` dan batasi root
filesystem yang boleh diakses. Panduan/plugin dalam katalog tidak otomatis
memasang 29 server eksternal itu. Lihat [ENV_VARS](ENV_VARS.md) dan
[MCP_INTEGRATION_CHECKLIST](MCP_INTEGRATION_CHECKLIST.md).

## Keamanan MCP

1. API key via env variable, tidak hardcoded (CONTRACT R003).
2. MCP media personal (heygen, elevenlabs) wajib consent gate.
3. `scripts/audit-trail.sh mcp-call` tersedia untuk workflow katalog.
   Seluruh panggilan SDK belum otomatis diarahkan ke utility audit tersebut;
   hook memori hanya menyimpan nama tool, bukan payload lengkap.

## Test pasca-install

```bash
bash unified-integration/scripts/setup-mcp.sh --check
bash unified-integration/scripts/mcp-test.sh --priority P0
bash unified-integration/scripts/mcp-test.sh --for-plugin replica-skill
```
