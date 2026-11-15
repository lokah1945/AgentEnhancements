---
title: "Library Model Implementation Closure 2026-11-15"
version: "1.0"
last_updated: "2026-11-15"
audience: "Project owner, maintainers, release reviewers"
---

# Library Model Closure — 2026-11-15 (lanjutan PR #7)

## 1. Ringkasan eksekusi

Sesi ini menuntaskan sisa mandat master prompt di atas baseline `e0821097`
(branch `feat/library-model-2026-11-15`): perbaikan CI, pencapaian target
routing, review independen dua peran dengan perbaikan temuan must-fix,
regresi baru, dan runbook operasional.

## 2. Perbaikan CI (job MCP failure)

**Root cause ganda** (reproduksi lokal + log run 43727788805):
1. `check-protocol.py` memanggil `embeddings_health` — nama tool lama yang
   dikonsolidasi menjadi `ae_health` (gagal di 9/10).
2. `_run_health` salah mem-parsing hasil FastMCP (list TextContent
   dianggap dict) sehingga semua backend `status: unknown`.
3. Validasi health tidak membaca `structuredContent` (payload verdict
   sebenarnya) — cabang degraded mati (H1 dari review).

**Fix**: fan-out memakai bentuk hasil yang terbukti dari path `call_tool`
(tuple/list/dict, parse text), verdict keseluruhan dihitung jujur
(`degraded` bila ada backend bermasalah), validator membaca
`structuredContent` dulu. **Verifikasi**: check-protocol 10/10 lokal;
unit negatif: payload degraded terdeteksi di kedua bentuk (structured
dan text-only).

## 3. Target routing TERCAPAI

| Metrik | Target | Hasil |
|---|---:|---:|
| recall@5 (41 intent EN/ID) | ≥ 95% | **97,6%** (holdout 8: 100%) |
| negative suppression (10 chit-chat) | ≥ 90% | **90%** |

Stabil 2 run penuh. Perbaikan yang menutup gap (semua di `registry.py`,
tanpa embedding, deterministik penuh):
- Sinonim intent dwibahasa dengan bobot (original 1.0, ekspansi 0.5)
- `when_to_use` ikut discoring (field kuat dari frontmatter)
- Format-alias floor: kecocokan nama penuh/alias tak terkalahkan graze
- **Word-boundary name graze**: `'rain'` tidak lagi cocok dengan
  `constraint` (ini juga yang menaikkan recall 92,7→97,6)
- `GENERIC_ACTION_WORDS`: kata kerja umum (write/translate/…/buat/
  terjemah) tak bisa men-graze nama; konfirmasi desc maksimal 1 kali
- `LAYOUT_NOUNS`: kata format (paragraph/halaman) tak memicu phrase bonus

## 4. Review independen (2 peran) — temuan & disposisi

Reviewer eksternal (threat/security + host-integration) memeriksa working
tree penuh dengan reproduksi eksekusi. Disposisi:

| ID | Temuan | Severity | Disposisi |
|---|---|---|---|
| S1 | rollback bisa hapus source tanpa restore | MEDIUM must-fix | **FIXED**: rollback transaksional (stage+verify di sibling, rename swap, restore saat gagal); test regresi |
| S2 | symlink stage didereference; RecursionError lolos dari transaksi | MEDIUM must-fix | **FIXED**: `_copy_tree(symlinks=True)`; semua salinan pra-transaksi dibungkus refusal; `stage_candidate` ikut diharden (bug dangling-link ditemukan test baru, juga fixed) |
| H1 | check-protocol tak mendeteksi gateway degraded (dead branch) | MEDIUM must-fix | **FIXED** + unit negatif kedua bentuk payload |
| H2 | fixture smoke ae_health tidak bisa lolos | MEDIUM (jika gate) | **DEFERRED**: `--exercise-tools` bukan bagian CI (butuh binary host + kredensial); dicatat sebagai utang dengan catatan di file |
| H4 | teks L0 "yang dibaca agen" tidak dipersist; CLI options phantom | MEDIUM | **FIXED**: `rendered` kini di dalam library-map.json + `--text-out`; argparse nyata |
| H6a | keep-step migrate bisa kehilangan skill default secara diam | MEDIUM | **FIXED**: parkir per-baris TAB, deteksi konflik slot, mv gagal = tetap di tempat + warning; restore anti-clobber; diverifikasi 3.378→1 |
| S4/S5/S6/S8/S9/S10/S11/H5/H8 | LOW / recommended | LOW | **ACCEPTED-AS-IS**: dicatat di bawah; tidak memblokir rilis |

Catatan residual yang diterima (dengan alasan): S4 (redaksi `reason`
eksternal di ae_health — hanya field whitelist, risiko rendah), S5
(parameter bernama `title` akan hilang dari skema — tidak ada server
bundled yang memakainya; regex dibatasi nanti bila ada kasus), S8/S9
(konten vendor & karakter kontrol — sudah dibatasi 250 tok + disclaimer
data-bukan-instruksi), H5 (duplikasi event Stop di OpenCode — idempoten
via kunci memori).

## 5. Bukti akhir

- `run-tests.py`: **251/251 OK** (2 skip by design; +2 regresi review)
- `setup-mcp.sh --check`: **10/10** (sebelumnya 9/10 di CI)
- Routing: 97,6% / 90% (2 run stabil)
- Bundle task-observer: 25/25 checksum pristine setelah seluruh sesi
- Statis: bash -n, py_compile, json tool, filename & drift check bersih
- Cold start (dari baseline report): 7.852 → 2.892 tok (budget 4.000)

## 6. Sisa terbuka (jujur)

1. **H2**: fixture `--exercise-tools` perlu adaptasi payload `ae_health`
   saat jalur itu diaktifkan kembali (butuh binary host nyata).
2. **REAL SESSION VERIFIED** belum: sandbox tanpa claude/codex/opencode
   binary — label host tetap ADAPTER TESTED.
3. S5 (slim_schema `title`) — tidak ada pemicu hari ini; pantau saat
   menambah server eksternal berparameter `title`.
