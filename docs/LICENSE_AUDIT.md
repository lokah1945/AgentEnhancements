---
title: License Audit
version: 2.0
last_updated: 2026-11-15
audience: maintainers
---

License Audit — Vendored Directories + Plugin Upstreams
--------

Wajib sebelum redistribute ulang (CONTRACT + ADR). Dua bagian: (A) direktori
yang benar-benar di-vendor ke dalam repo ini — lisensi terverifikasi dari
file di dalam tree; (B) entry katalog eksternal yang hanya didistribusikan
sebagai manifest + panduan (teks milik kami), belum ada redistribusi kode
upstream.

A. Direktori vendored — terverifikasi dari file in-tree (2026-11-15)
--------

- **#:** 1
  - **Direktori:** `agentic-awesome-skills/`
  - **Upstream (dari metadata vendor):**
    github.com/sickn33/agentic-awesome-skills (package.json)
  - **License (dari file LICENSE in-tree):** **MIT** (LICENSE) + **CC-BY-4.0**
    untuk konten non-kode (LICENSE-CONTENT)
  - **NOTICE/attribution wajib:** Pertahankan kedua file LICENSE

- **#:** 2
  - **Direktori:** `anthropic-skills/`
  - **Upstream (dari metadata vendor):** github.com/anthropics/skills
  - **License (dari file LICENSE in-tree):** **Apache-2.0** per skill
    (LICENSE.txt per skill; 18 dari 19 skill memiliki LICENSE.txt; cakupan
    `doc-coauthoring` belum terverifikasi)
  - **NOTICE/attribution wajib:** THIRD_PARTY_NOTICES.md ikut ter-vendor

- **#:** 3
  - **Direktori:** `claude-mem/`
  - **Upstream (dari metadata vendor):** github.com/thedotmack/claude-mem
    (package.json)
  - **License (dari file LICENSE in-tree):** **Apache-2.0** (LICENSE + NOTICE)
  - **NOTICE/attribution wajib:** NOTICE wajib saat redistribute

- **#:** 4
  - **Direktori:** `ECC/`
  - **Upstream (dari metadata vendor):** github.com/affaan-m/ECC (package.json)
  - **License (dari file LICENSE in-tree):** **MIT** (LICENSE)
  - **NOTICE/attribution wajib:** —

- **#:** 5
  - **Direktori:** `headroom/`
  - **Upstream (dari metadata vendor):** github.com/headroomlabs-ai/headroom
    (Cargo.toml)
  - **License (dari file LICENSE in-tree):** **Apache-2.0** (LICENSE + NOTICE;
    MIT hanya milik dependensi pihak ketiga di NOTICE)
  - **NOTICE/attribution wajib:** NOTICE wajib saat redistribute

- **#:** 6
  - **Direktori:** `ponytail/`
  - **Upstream (dari metadata vendor):** github.com/DietrichGebert/ponytail
    (package.json)
  - **License (dari file LICENSE in-tree):** **MIT** (LICENSE)
  - **NOTICE/attribution wajib:** —

- **#:** 7
  - **Direktori:** `superpowers/`
  - **Upstream (dari metadata vendor):** github.com/obra/superpowers (README)
  - **License (dari file LICENSE in-tree):** **MIT** (LICENSE)
  - **NOTICE/attribution wajib:** —

- **#:** 8
  - **Direktori:** `system-prompts-and-models-of-ai-tools/`
  - **Upstream (dari metadata vendor):**
    github.com/x1xhlol/system-prompts-and-models-of-ai-tools
  - **License (dari file LICENSE in-tree):** **GPL-3.0** (LICENSE.md)
  - **NOTICE/attribution wajib:** Copyleft: redistribusi direktori ini jatuh di
    bawah GPL-3.0; isi prompt juga bisa tunduk ToS vendor asal — lihat
    docs/audit/AGENTENHANCEMENTS_E2E_AUDIT_2026-11-15.md (AE-03)

- **#:** 9
  - **Direktori:** `replica-skill/`
  - **Upstream (dari metadata vendor):**
    github.com/Jakeschincariol/replica-skill
  - **License (dari file LICENSE in-tree):** **MIT** (LICENSE)
  - **NOTICE/attribution wajib:** —

- **#:** 10
  - **Direktori:** `agency-agents/`
  - **Upstream (dari metadata vendor):** github.com/msitarzewski/agency-agents
  - **License (dari file LICENSE in-tree):** **MIT** (LICENSE)
  - **NOTICE/attribution wajib:** —

- **#:** 11
  - **Direktori:** `task-observer/`
  - **Upstream (dari metadata vendor):**
    github.com/rebelytics/one-skill-to-rule-them-all
  - **License (dari file LICENSE in-tree):** **CC-BY-4.0** (LICENSE; pinned
    dengan checksum di task-observer/VENDORED.json)
  - **NOTICE/attribution wajib:** Atribusi upstream (Eoghan Henn dkk.)

Catatan: tabel README lama yang menyebut claude-mem "MIT" dan
system-prompts "CC-BY-4.0" adalah keliru dan telah dikoreksi (audit
AE-02); sumber kebenaran adalah file LICENSE di dalam tiap direktori.

B. Entry katalog eksternal (manifest + panduan saja; belum ada redistribusi kode
upstream)
--------

- **#:** 1
  - **Plugin:** replica-skill
  - **Upstream:** github.com/Jakeschincariol/replica-skill
  - **License (metadata katalog):** MIT
  - **Status:** **VERIFIED** — vendored (lihat bagian A)

- **#:** 2
  - **Plugin:** anthropic-skills
  - **Upstream:** github.com/anthropics/skills
  - **License (metadata katalog):** Apache-2.0
  - **Status:** **VERIFIED** — vendored (lihat bagian A)

- **#:** 3
  - **Plugin:** agency 19 pack
  - **Upstream:** github.com/msitarzewski/agency-agents
  - **License (metadata katalog):** MIT
  - **Status:** **VERIFIED** — vendored (lihat bagian A)

- **#:** 4
  - **Plugin:** mattpocock-skills
  - **Upstream:** github.com/mattpocock/skills
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify saat vendor dimulai

- **#:** 5
  - **Plugin:** karpathy-skills
  - **Upstream:** github.com/multica-ai/andrej-karpathy-skills
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 6
  - **Plugin:** agent-skills-addyosmani
  - **Upstream:** github.com/addyosmani/agent-skills
  - **License (metadata katalog):** Apache-2.0 (assumed)
  - **Status:** TODO verify

- **#:** 7
  - **Plugin:** graphify
  - **Upstream:** github.com/Graphify-Labs/graphify
  - **License (metadata katalog):** Apache-2.0 (assumed)
  - **Status:** TODO verify

- **#:** 8
  - **Plugin:** agent-reach
  - **Upstream:** github.com/Panniantong/Agent-Reach
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 9
  - **Plugin:** understand-anything
  - **Upstream:** github.com/Egonex-AI/Understand-Anything
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 10
  - **Plugin:** last-30-days
  - **Upstream:** github.com/mvanhorn/last30days-skill
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 11
  - **Plugin:** rea
  - **Upstream:** github.com/morluto/rea
  - **License (metadata katalog):** **MIT VERIFIED** (upstream, 2026-11-15)
  - **Status:** Panduan + routing saja; server upstream dipasang user

- **#:** 12
  - **Plugin:** gstack
  - **Upstream:** github.com/garrytan/gstack
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 13
  - **Plugin:** caveman
  - **Upstream:** github.com/JuliusBrussee/Caveman
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 14
  - **Plugin:** gsd
  - **Upstream:** github.com/gsd-build/get-shit-done
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 15
  - **Plugin:** bmad-method
  - **Upstream:** github.com/bmad-code-org/BMAD-METHOD
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 16
  - **Plugin:** ui-ux-pro-max
  - **Upstream:** github.com/nextlevelbuilder/ui-ux-pro-max-skill
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 17
  - **Plugin:** impeccable
  - **Upstream:** github.com/pbakaus/impeccable
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 18
  - **Plugin:** ppt-master
  - **Upstream:** github.com/hugohe3/ppt-master
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 19
  - **Plugin:** diagram-design
  - **Upstream:** github.com/cathrynlavery/diagram-design
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 20
  - **Plugin:** openmontage
  - **Upstream:** github.com/calesthio/OpenMontage
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

- **#:** 21
  - **Plugin:** hyperframes
  - **Upstream:** github.com/heygen-com/hyperframes
  - **License (metadata katalog):** MIT (assumed) + TOS HeyGen
  - **Status:** TODO verify

- **#:** 22
  - **Plugin:** humanizer
  - **Upstream:** github.com/blader/humanizer
  - **License (metadata katalog):** MIT (assumed)
  - **Status:** TODO verify

Cara verifikasi
--------

```bash
curl -s https://raw.githubusercontent.com/<org>/<repo>/main/LICENSE | head -20
# atau branch master:
curl -s https://raw.githubusercontent.com/<org>/<repo>/master/LICENSE | head -20
```

Klasifikasi risk
--------

- **License:** MIT / Apache-2.0 / BSD
  - **Risk (lapisan milik repo: MIT):** Low
  - **Action:** Vendor + sertakan LICENSE (+ NOTICE bila ada)

- **License:** CC-BY-4.0 (konten)
  - **Risk (lapisan milik repo: MIT):** Low
  - **Action:** Atribusi + tautan license

- **License:** GPL-3.0
  - **Risk (lapisan milik repo: MIT):** Medium (copyleft kuat)
  - **Action:** Sudah ada di tree (system-prompts): redistribusi direktori itu
    tunduk pada GPL-3.0; jangan dicampur ke kode MIT

- **License:** AGPL-3.0
  - **Risk (lapisan milik repo: MIT):** High (network copyleft)
  - **Action:** DROP / rewrite

- **License:** Proprietary
  - **Risk (lapisan milik repo: MIT):** Very high
  - **Action:** DROP

- **License:** Unknown
  - **Risk (lapisan milik repo: MIT):** High (default All Rights Reserved)
  - **Action:** Eskalasi ke upstream

Catatan penting
--------

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

Pemeriksaan ulang in-tree — 2026-11-19
--------

Root `LICENSE` membatasi grant MIT pada integration layer milik AE dan
mencantumkan sebelas direktori vendor dengan lisensinya masing-masing.
Pemeriksaan file mengonfirmasi Apache-2.0 untuk `claude-mem/LICENSE` dan
`headroom/LICENSE`, beserta kedua `NOTICE`; GPL-3.0 untuk
`system-prompts-and-models-of-ai-tools/LICENSE.md`; MIT untuk direktori yang
tercantum pada tabel; serta CC-BY-4.0 untuk bundle task-observer. AAS juga
memiliki `LICENSE-CONTENT` dan pengecualian upstream per-file.

Pada `anthropic-skills/skills/`, 18 file `LICENSE.txt` menyebut Apache-2.0.
`doc-coauthoring` tidak memiliki file tersebut dan tidak ada LICENSE tingkat
root dalam salinan vendor ini. Pernyataan lama bahwa ada lisensi Apache
repo-wide untuk menutup gap itu tidak terbukti oleh file in-tree. Minta
klarifikasi upstream sebelum mengandalkan cakupan lisensi skill tersebut.
`THIRD_PARTY_NOTICES.md` tetap harus dipertahankan.

Ini adalah inventaris bukti file, bukan jaminan izin redistribusi setiap
konten. Batas MIT/GPL dan hak pihak ketiga pada arsip prompt tetap mengikuti
penilaian maintainer (AE-03 historis). Tidak ada lisensi atau NOTICE dihapus.

Salinan reference prompt di `unified-integration/prompts/` mempertahankan
lisensi sumber koleksi GPL-3.0; lokasinya tidak memberikan grant MIT baru.
Root LICENSE kini menyatakan aturan salinan generated secara eksplisit.
Patch AE pada CLI headroom (mode, nama binary, output tanpa cache transient)
ditandai pada file Rust/Cargo yang diubah; lisensi Apache-2.0 tetap berlaku.
