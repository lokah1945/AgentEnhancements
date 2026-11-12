---
title: License Audit
version: 1.0
last_updated: 2026-11-13
audience: maintainers
---

# License Audit — 21 Plugin Upstream

Wajib sebelum redistribute ulang (CONTRACT + ADR). replica-skill (MIT) dan
anthropic-skills (Apache-2.0) sudah terverifikasi dan di-vendor.

## Tabel audit

| # | Plugin | Upstream | License | Status | Action |
|---|--------|----------|---------|--------|--------|
| 1 | replica-skill | github.com/Jakeschincariol/replica-skill | MIT | **VERIFIED** (LICENSE vendored) | OK — vendored dengan LICENSE asli |
| 2 | mattpocock-skills | github.com/mattpocock/ | MIT (assumed) | TODO verify | Cek LICENSE repo utama |
| 3 | karpathy-skills | github.com/multica-ai/andrej-karpathy-skills | MIT (assumed) | TODO verify | Cek LICENSE |
| 4 | agent-skills-addyosmani | github.com/addyosmani/ | Apache-2.0 (assumed) | TODO verify | Cek LICENSE |
| 5 | graphify | github.com/Graphify-Labs/ | Apache-2.0 (assumed) | TODO verify | Cek LICENSE |
| 6 | agent-reach | github.com/Panniantong/Agent-Reach | MIT (assumed) | TODO verify | Cek LICENSE |
| 7 | understand-anything | github.com/Egonex-AI/Understand-Anything | MIT (assumed) | TODO verify | Cek LICENSE |
| 8 | last-30-days | github.com/mvanhorn/ | MIT (assumed) | TODO verify | Cek LICENSE |
| 9 | rea | github.com/morluto/rea | MIT (assumed) | TODO verify | Cek LICENSE |
| 10 | gstack | github.com/garrytan/gstack | MIT (assumed) | TODO verify | Cek LICENSE |
| 11 | caveman | github.com/JuliusBrussee/Caveman | MIT (assumed) | TODO verify | Cek LICENSE |
| 12 | gsd | github.com/gsd-build/get-shit-done | MIT (assumed) | TODO verify | Cek LICENSE |
| 13 | bmad-method | github.com/bmad-code-org/ | MIT (assumed) | TODO verify | Cek LICENSE |
| 14 | ui-ux-pro-max | github.com/nextlevelbuilder/ | MIT (assumed) | TODO verify | Cek LICENSE |
| 15 | impeccable | github.com/pbakaus/ | MIT (assumed) | TODO verify | Cek LICENSE |
| 16 | ppt-master | github.com/hugohe3/ppt-master | MIT (assumed) | TODO verify | Cek LICENSE |
| 17 | diagram-design | github.com/cathrynlavery/ | MIT (assumed) | TODO verify | Cek LICENSE |
| 18 | anthropic-skills | github.com/anthropics/skills | Apache-2.0 | **VERIFIED** (vendored: 18 skill bawa LICENSE.txt Apache-2.0 + THIRD_PARTY_NOTICES.md) | OK — vendored; `doc-coauthoring` tidak membawa LICENSE.txt eksplisit (perlakukan sebagai Apache-2.0 repo-wide, catat pengecualian) |
| 19 | openmontage | github.com/calesthio/OpenMontage | MIT (assumed) | TODO verify | Cek LICENSE |
| 20 | hyperframes | github.com/heygen-com/hyperframes | MIT (assumed) | TODO verify | Cek LICENSE + TOS HeyGen |
| 21 | humanizer | github.com/blader/humanizer | MIT (assumed) | TODO verify | Cek LICENSE |

## Cara verifikasi

```bash
curl -s https://raw.githubusercontent.com/<org>/<repo>/main/LICENSE | head -20
# atau branch master:
curl -s https://raw.githubusercontent.com/<org>/<repo>/master/LICENSE | head -20
```

## Klasifikasi risk

| License | Risk (repo ini MIT) | Action |
|---------|---------------------|--------|
| MIT / Apache-2.0 / BSD | Low | Vendor + sertakan LICENSE |
| GPL-3.0 | Medium (copyleft) | Pertimbangkan rewrite |
| AGPL-3.0 | High (network copyleft) | DROP / rewrite |
| Proprietary | Very high | DROP |
| Unknown | High (default All Rights Reserved) | Eskalasi ke upstream |

## Catatan penting

- **replica-skill sudah aman**: MIT terverifikasi, LICENSE asli ikut
  ter-vendor di `replica-skill/LICENSE`, sub-skill tidak dimodifikasi.
- **anthropic-skills sudah aman**: Apache-2.0 terverifikasi per skill
  (`anthropic-skills/skills/*/LICENSE.txt`, 18 dari 19; `doc-coauthoring`
  tanpa LICENSE.txt — repo-wide Apache-2.0, pengecualian dicatat),
  `THIRD_PARTY_NOTICES.md` ikut ter-vendor. Marketplace manifest
  (`.claude-plugin/marketplace.json`) milik upstream tetap utuh.
- 19 plugin lain **belum di-vendor** — hanya manifest + panduan integrasi
  (teks original kami), sehingga belum ada redistribusi kode upstream.
  License audit menjadi wajib SAAT vendor/wiring kode upstream dimulai.
- Manifest katalog menyimpan `source.license` sebagai referensi cepat.
