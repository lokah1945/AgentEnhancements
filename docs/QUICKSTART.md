---
title: Quickstart Plugin Catalog
version: 1.0
last_updated: 2026-11-13
audience: all agents and contributors
---

# Quickstart — Plugin Catalog (5 menit)

Mulai pakai satu plugin dari katalog dalam 5 menit.

## 1. Verifikasi struktur (30 detik)

```bash
cd AgentEnhancements
ls plugin-catalog/     # 5 kategori + catalog.json + mcp-servers.json
ls plugin-catalog/code/  # 4 plugin (Matt Pocock, Karpathy, Addy Osmani, Replica)
```

## 2. Validasi katalog (1 menit)

```bash
python3 unified-integration/scripts/catalog-validate.py --root .
# harus: ALL CHECKS PASSED (21/21 plugin)
```

## 3. Wire katalog ke registry (30 detik)

```bash
bash unified-integration/scripts/catalog-wire.sh
# 21 plugin guide ter-symlink ke unified-integration/skills/by-category/
```

## 4. Test 1 plugin (1 menit)

```bash
bash unified-integration/scripts/catalog-test.sh replica-skill
# harus lulus semua cek: manifest + SKILL.md + MCP + wiring
```

Untuk test MCP roadmap:

```bash
bash unified-integration/scripts/mcp-test.sh --for-plugin replica-skill
bash unified-integration/scripts/mcp-test.sh --priority P0
```

## 5. Pakai dispatcher (2 menit)

```bash
# dry-run dulu untuk lihat rencana
bash unified-integration/scripts/dispatch.sh --dry-run "clone app seperti Calendly"
# output: Skill match : replica-skill

bash unified-integration/scripts/dispatch.sh --dry-run "buat deck 10 slide pitch"
# output: Skill match : ppt-master
```

## 6. Pakai replica-skill langsung (opsional)

Skill replica ter-vendor di `replica-skill/` dan ter-agregasi ke registry
via `setup.sh`. Di Claude Code:

```
/replica-recon https://target-app.example.com
```

Atau copy manual bila ingin project-local:

```bash
cp -r replica-skill/replica-* .claude/skills/
```

## 6b. Skill resmi Anthropic + pemetaan all-in-one (2 menit)

19 skill resmi Anthropic (docx, pdf, pptx, xlsx, skill-creator,
mcp-builder, webapp-testing, claude-api, ...) ter-vendor di
`anthropic-skills/` dan **sudah aktif otomatis** setelah `setup.sh`:
ter-link native ke `~/.claude/skills/` dan `~/.agents/skills/`.

```bash
# cek status link native
bash unified-integration/scripts/link-skills.sh --status

# dispatcher: intent dokumen langsung ke skill resmi
bash unified-integration/scripts/dispatch.sh --dry-run "extract pdf form fields"
# output: Skill match : pdf  (anthropic-skills/skills/pdf/SKILL.md)

# registry: petakan task apa pun ke skill + plugin + MCP sekaligus
python3 unified-integration/scripts/registry.py map "buat dokumen word laporan keuangan"
# output: docx (skill resmi, natively linked) + plugin terkait + MCP + hints
```

## 7. Operasi sensitif (voice clone / video personal)

WAJIB jalankan consent gate dulu:

```bash
bash unified-integration/scripts/consent-gate.sh "sales outreach" voice.wav user
# exit 0 = approved, exit 1 = refused (lihat docs/SAFETY.md)
```

## Selesai

Anda sudah: validasi 21 plugin, wire registry, test plugin, pakai dispatcher,
dan memverifikasi skill resmi Anthropic + pemetaan all-in-one.

**Langkah berikutnya**: `docs/COOKBOOK.md` (resep gabungan), `docs/INTEGRATION_CHECKLIST.md`
(wiring penuh), `docs/SAFETY.md` (compliance), `docs/MCP_SERVERS.md` (roadmap MCP).
