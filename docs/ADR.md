---
title: Architecture Decision Records
version: 1.0
last_updated: 2026-11-13
audience: maintainers and all agents
---

# ADR — Architecture Decision Records

Keputusan arsitektur untuk integrasi plugin catalog + replica-skill. Mengikuti
template Michael Nygard. ADR ini melengkapi CONTRACT.md (tidak menimpanya).

## ADR-001 — Struktur kategori 5 untuk plugin catalog

**Status**: Accepted (2026-11-13)

**Context**: 21 plugin sources lintas 5 kategori (code/research/tokens/design/
multimedia-writing) perlu diintegrasikan tanpa mengganggu registry agregasi
yang sudah ada.

**Decision**: Katalog eksternal di `plugin-catalog/` (root), terpisah dari
`unified-integration/skills/` (registry hasil agregasi). Keduanya berdampingan:
registry = skill yang ter-agregasi dari source; catalog = manifest plugin
eksternal + panduan integrasi.

**Rationale**: Tidak menyentuh pipeline agregasi (CONTRACT R304: index
di-regenerasi dari scratch); catalog punya siklus hidup sendiri.

**Consequences**: Dua "dunia" skill — ter-rekonsiliasi via `catalog-wire.sh`
(symlink guide ke by-category/) tanpa mengubah index.

## ADR-002 — Manifest format (skill-manifest.v1.json)

**Status**: Accepted (2026-11-13)

**Context**: Perlu metadata konsisten + machine-readable untuk 21 plugin.

**Decision**: 14 field wajib per manifest: id, name, slug, category, version,
status, source, description, capabilities, tools_required,
mcp_servers_suggested, trigger_keywords, best_for, integration_notes.

**Rationale**: Cukup untuk validasi otomatis (`catalog-validate.py`); field
`skill_files[].path` diverifikasi eksis di repo.

**Consequences**: Verifikasi path mencegah manifest basi saat file dipindah.

## ADR-003 — Catalog index terpisah dari unified index

**Status**: Accepted (2026-11-13)

**Context**: CONTRACT 2.1 menyatakan "One skills index: unified-integration/
skills/all-skills.json" dan R304 melarang edit manual index.

**Decision**: Katalog punya index sendiri: `plugin-catalog/catalog.json`.
Index unified TIDAK disentuh manual; replica-skill masuk ke unified index
secara natural via pipeline agregasi setup.sh (karena di-vendor dengan
SKILL.md frontmatter).

**Rationale**: Kepatuhan penuh kontrak; tidak ada dual-maintenance index.

**Consequences**: catalog.json di-generate oleh `scripts/gen-catalog-index.py`
(ada di scripts workspace); regenerasi ulang bila manifest berubah.

## ADR-004 — Vendor replica-skill vs submodule

**Status**: Accepted (2026-11-13)

**Context**: Repo mem-vendor semua modul langsung (bukan submodule, lihat
git history "Vendor all project files directly"). replica-skill (MIT) perlu
diintegrasikan.

**Decision**: Vendor penuh di `replica-skill/` (root, tanpa .git). Registrasi
di pipeline: `setup.sh` aggregate_skills menambahkan source "replica-skill";
`update-skills.sh` menambahkan repo ke daftar update.

**Rationale**: Konsisten dengan pola modul lain; pipeline otomatis menangkap
11 sub-skill (SKILL.md frontmatter kompatibel); MIT membolehkan redistribute.

**Consequences**: 11 skill replica masuk unified index dengan kategori
"general" (normalisasi kategori agregasi). Update upstream: `update-skills.sh`
tidak bisa git-pull (bukan repo git) — update manual via re-vendor; didokumentasikan.

## ADR-005 — Nama script menghindari pelanggaran CI filename

**Status**: Accepted (2026-11-13)

**Context**: CONTRACT 9.1 mem-block filename mengandung `fixed|new|v\d+|temp|backup`.
Patch awal punya `system-prompt-v2.md` dan `setup.sh` kedua (melanggar
single source of truth 2.1).

**Decision**:
- Prompt konsolidasi → `unified-integration/prompts/consolidated-system-prompt.txt`
  (mengikuti pola `*-system-prompt.txt` kanonik).
- Tidak ada setup.sh kedua → wiring via `unified-integration/scripts/catalog-wire.sh`.
- Semua nama script baru bebas token terlarang.

**Rationale**: Kepatuhan CI + single source of truth.

**Consequences**: Nama-nama di dokumentasi mengikuti nama final.

## ADR-006 — .cursorrules manual tidak ditambahkan

**Status**: Accepted (2026-11-13)

**Context**: Patch awal menyertakan root `.cursorrules`. CONTRACT 2.2 (Agent
Neutrality) menyatakan config agent di-generate FROM shared source, bukan
di-maintain terpisah. setup.sh sudah generate config Cursor dari prompts/.

**Decision**: Tidak menambah root .cursorrules. Aturan perilaku (Karpathy +
Anthropic + GSD) masuk ke `consolidated-system-prompt.txt` (shared source)
yang bisa di-generate ke config agent manapun oleh setup.sh.

**Rationale**: Agent neutrality; satu source, banyak target.

**Consequences**: User Cursor mendapat rules via jalur kanonik, bukan file manual.

## ADR-007 — Orchestrator tier berlapis

**Status**: Accepted (2026-11-13)

**Decision**: 3 orchestrator default: BMAD (build), GSD (execute), REA
(research). Plugin dipanggil sebagai sub-task. replica-skill adalah pipeline
orchestrator-nya sendiri untuk mode "clone app" (11 langkah berurutan) dan
bisa dikomposisi (recon saja, entrepreneur saja).

**Rationale**: Separation of concerns; replica punya urutan internal khusus.

## ADR-008 — Bahasa Indonesia default untuk docs baru

**Status**: Accepted (2026-11-13)

**Decision**: Dokumentasi integrasi ini ditulis dalam Bahasa Indonesia
(istilah teknis tetap Inggris). SKILL.md upstream (replica) tetap English
asli — tidak dimodifikasi (respect upstream).

**Rationale**: Konsisten preferensi maintainer; meminimalkan diff upstream.

## Template ADR

```markdown
## ADR-XXX — <Title>

**Status**: <Proposed|Accepted|Deprecated|Superseded> (YYYY-MM-DD)

**Context**: <masalah + force major>

**Decision**: <keputusan>

**Rationale**: <alasan>

**Consequences**: <dampak positif & negatif>
```
