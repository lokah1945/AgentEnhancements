---
title: License Audit
version: 2.0
last_updated: 2026-11-15
audience: maintainers
---

# License Audit — Vendored Directories + Plugin Upstreams

Wajib sebelum redistribute ulang (CONTRACT + ADR). Dua bagian: (A) direktori
yang benar-benar di-vendor ke dalam repo ini — lisensi terverifikasi dari
file di dalam tree; (B) entry katalog eksternal yang hanya didistribusikan
sebagai manifest + panduan (teks milik kami), belum ada redistribusi kode
upstream.

## A. Direktori vendored — terverifikasi dari file in-tree (2026-11-15)

| # | Direktori | Upstream (dari metadata vendor) | License (dari file LICENSE in-tree) | NOTICE/attribution wajib |
|---|-----------|----------------------------------|--------------------------------------|--------------------------|
| 1 | `agentic-awesome-skills/` | github.com/sickn33/agentic-awesome-skills (package.json) | **MIT** (LICENSE) + **CC-BY-4.0** untuk konten non-kode (LICENSE-CONTENT) | Pertahankan kedua file LICENSE |
| 2 | `anthropic-skills/` | github.com/anthropics/skills | **Apache-2.0** per skill (LICENSE.txt per skill; `doc-coauthoring` tanpa LICENSE.txt → repo-wide Apache-2.0) | THIRD_PARTY_NOTICES.md ikut ter-vendor |
| 3 | `claude-mem/` | github.com/thedotmack/claude-mem (package.json) | **Apache-2.0** (LICENSE + NOTICE) | NOTICE wajib saat redistribute |
| 4 | `ECC/` | github.com/affaan-m/ECC (package.json) | **MIT** (LICENSE) | — |
| 5 | `headroom/` | github.com/headroomlabs-ai/headroom (Cargo.toml) | **Apache-2.0** (LICENSE + NOTICE; MIT hanya milik dependensi pihak ketiga di NOTICE) | NOTICE wajib saat redistribute |
| 6 | `ponytail/` | github.com/DietrichGebert/ponytail (package.json) | **MIT** (LICENSE) | — |
| 7 | `superpowers/` | github.com/obra/superpowers (README) | **MIT** (LICENSE) | — |
| 8 | `system-prompts-and-models-of-ai-tools/` | github.com/x1xhlol/system-prompts-and-models-of-ai-tools | **GPL-3.0** (LICENSE.md) | Copyleft: redistribusi direktori ini jatuh di bawah GPL-3.0; isi prompt juga bisa tunduk ToS vendor asal — lihat docs/audit/AGENTENHANCEMENTS_E2E_AUDIT_2026-11-15.md (AE-03) |
| 9 | `replica-skill/` | github.com/Jakeschincariol/replica-skill | **MIT** (LICENSE) | — |
| 10 | `agency-agents/` | github.com/msitarzewski/agency-agents | **MIT** (LICENSE) | — |
| 11 | `task-observer/` | github.com/rebelytics/one-skill-to-rule-them-all | **CC-BY-4.0** (LICENSE; pinned dengan checksum di task-observer/VENDORED.json) | Atribusi upstream (Eoghan Henn dkk.) |

Catatan: tabel README lama yang menyebut claude-mem "MIT" dan
system-prompts "CC-BY-4.0" adalah keliru dan telah dikoreksi (audit
AE-02); sumber kebenaran adalah file LICENSE di dalam tiap direktori.

## B. Entry katalog eksternal (manifest + panduan saja; belum ada redistribusi kode upstream)

| # | Plugin | Upstream | License (metadata katalog) | Status |
|---|--------|----------|-----------------------------|--------|
| 1 | replica-skill | github.com/Jakeschincariol/replica-skill | MIT | **VERIFIED** — vendored (lihat bagian A) |
| 2 | anthropic-skills | github.com/anthropics/skills | Apache-2.0 | **VERIFIED** — vendored (lihat bagian A) |
| 3 | agency 19 pack | github.com/msitarzewski/agency-agents | MIT | **VERIFIED** — vendored (lihat bagian A) |
| 4 | mattpocock-skills | github.com/mattpocock/skills | MIT (assumed) | TODO verify saat vendor dimulai |
| 5 | karpathy-skills | github.com/multica-ai/andrej-karpathy-skills | MIT (assumed) | TODO verify |
| 6 | agent-skills-addyosmani | github.com/addyosmani/agent-skills | Apache-2.0 (assumed) | TODO verify |
| 7 | graphify | github.com/Graphify-Labs/graphify | Apache-2.0 (assumed) | TODO verify |
| 8 | agent-reach | github.com/Panniantong/Agent-Reach | MIT (assumed) | TODO verify |
| 9 | understand-anything | github.com/Egonex-AI/Understand-Anything | MIT (assumed) | TODO verify |
| 10 | last-30-days | github.com/mvanhorn/last30days-skill | MIT (assumed) | TODO verify |
| 11 | rea | github.com/morluto/rea | **MIT VERIFIED** (upstream, 2026-11-15) | Panduan + routing saja; server upstream dipasang user |
| 12 | gstack | github.com/garrytan/gstack | MIT (assumed) | TODO verify |
| 13 | caveman | github.com/JuliusBrussee/Caveman | MIT (assumed) | TODO verify |
| 14 | gsd | github.com/gsd-build/get-shit-done | MIT (assumed) | TODO verify |
| 15 | bmad-method | github.com/bmad-code-org/BMAD-METHOD | MIT (assumed) | TODO verify |
| 16 | ui-ux-pro-max | github.com/nextlevelbuilder/ui-ux-pro-max-skill | MIT (assumed) | TODO verify |
| 17 | impeccable | github.com/pbakaus/impeccable | MIT (assumed) | TODO verify |
| 18 | ppt-master | github.com/hugohe3/ppt-master | MIT (assumed) | TODO verify |
| 19 | diagram-design | github.com/cathrynlavery/diagram-design | MIT (assumed) | TODO verify |
| 20 | openmontage | github.com/calesthio/OpenMontage | MIT (assumed) | TODO verify |
| 21 | hyperframes | github.com/heygen-com/hyperframes | MIT (assumed) + TOS HeyGen | TODO verify |
| 22 | humanizer | github.com/blader/humanizer | MIT (assumed) | TODO verify |

## Cara verifikasi

```bash
curl -s https://raw.githubusercontent.com/<org>/<repo>/main/LICENSE | head -20
# atau branch master:
curl -s https://raw.githubusercontent.com/<org>/<repo>/master/LICENSE | head -20
```

## Klasifikasi risk

| License | Risk (lapisan milik repo: MIT) | Action |
|---------|-------------------------------|--------|
| MIT / Apache-2.0 / BSD | Low | Vendor + sertakan LICENSE (+ NOTICE bila ada) |
| CC-BY-4.0 (konten) | Low | Atribusi + tautan license |
| GPL-3.0 | Medium (copyleft kuat) | Sudah ada di tree (system-prompts): redistribusi direktori itu tunduk pada GPL-3.0; jangan dicampur ke kode MIT |
| AGPL-3.0 | High (network copyleft) | DROP / rewrite |
| Proprietary | Very high | DROP |
| Unknown | High (default All Rights Reserved) | Eskalasi ke upstream |

## Catatan penting

- **Lapisan milik repo** (unified-integration/, plugin-catalog/, scripts/,
  docs/, skills index) dirilis MIT; direktori vendored mempertahankan
  lisensi upstreamnya (lihat NOTICE di file LICENSE root).
- **Koreksi 2026-11-15 (audit AE-02)**: README lama menyebut claude-mem
  "MIT" (benar: Apache-2.0), system-prompts "CC-BY-4.0" (benar: GPL-3.0),
  headroom "MIT/Apache-2.0" (benar: Apache-2.0), dan 7/10 URL upstream
  salah — semuanya telah dikoreksi dari metadata vendor in-tree.
- **claude-mem NOTICE** dan **headroom NOTICE** wajib dibawa saat
  redistribute direktori tersebut.
- Entry katalog eksternal (bagian B) **belum di-vendor** — hanya manifest +
  panduan integrasi (teks original kami), sehingga belum ada redistribusi
  kode upstream. License audit per-entry menjadi wajib SAAT vendoring
  kode upstream dimulai.
- Manifest katalog menyimpan `source.license` sebagai referensi cepat;
  diverifikasi ulang oleh maintainer, bukan diwarisi dari panduan.
