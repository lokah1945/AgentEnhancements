---
title: Validasi kandidat rilis AgentEnhancements
version: "1.0"
last_updated: "2026-11-23"
audience: maintainer dan reviewer
---

## Validasi kandidat rilis AgentEnhancements

Kandidat ini meneruskan PR #13 setelah merge ke `master` di
`244793238664fce36e4a942d272fdc172760705a`. Gate di bawah mengikuti
[kontrak proyek](../../CONTRACT.md). Master prompt
`AE_CODEX_MASTER_PROMPT_ENTERPRISE_PRODUCTION_READY_2026-11-22.md`
tidak ditemukan pada ref remote yang diperiksa. Persyaratan yang hanya
tercantum di berkas tersebut belum dapat diverifikasi.

### Perubahan untuk direview

- Selector Mode 2 memakai satu snapshot untuk endpoint, referensi
  `api_keys`, dan redaksi. Konfigurasi nonreguler atau di luar batas
  ukuran ditolak. Migrasi membaca berkas lama tanpa mengikuti symlink,
  menyimpan sumber yang benar-benar dipakai, dan membatalkan publikasi
  saat mendeteksi edit berikutnya.
- Gateway memeriksa ulang kesiapan, skema dan kredensial saat panggilan
  keluar dari antrean. `ae_health` memanggil tiap backend sekali. Definisi
  tool eksternal yang memuat teks kredensial tersaring sebelum ditawarkan.
- Setup membaca lock dependency setelah memperoleh lock runtime dan
  menguji generasi yang memakai snapshot tersebut sebelum aktivasi.
- `registry map` memangkas kartu utuh dan tetap menghasilkan JSON valid
  untuk kueri panjang. Ranking memakai nama dan ekstensi file dari path
  Linux dan Windows. Kartu mengarah ke ID bertipe.
- OpenCode memvalidasi referensi tool lengkap untuk direct tools dan Code
  Mode. Validasi nama dan kesiapan berbagi fungsi dengan gateway.

### Bukti verifikasi

Pengujian aplikasi memakai Debian 12 x86-64, Python 3.11.2, Node 24.22.2
dan Rust 1.99.1. Model fixture, selector dan pengujian kredensial berjalan
di namespace dengan akses jaringan loopback. Setup memakai HOME terisolasi
dan wheel cache dari lock repository.

- Suite integrasi menjalankan 486 tes dengan 482 lulus dan empat skip
  opt-in untuk layanan live.
- Fresh setup menghasilkan checkout bersih. Setup kedua memakai kembali
  generasi runtime. Relokasi ke direktori dengan spasi memulihkan path.
- Sebelas pemeriksaan MCP stdio lulus. Fixture gateway menguji aktivasi,
  pencabutan akses, panggilan antrean dan pemisahan kredensial.
- ECC lulus 8.289 tes. Tiga tes Rust lulus. Build rilis Headroom dan smoke
  kompresi auto, code dan JSON selesai.
- Companion browser lulus dua tes Node. Sesi interaktif belum diuji.
- Doctor Codex 0.171.0, Claude Code 2.1.329 dan OpenCode 2.3.2 membuka
  gateway dan memanggil tool lokal dari konfigurasi hasil setup.
- Hermes 0.17.0 menyimpan dua task dan dua summary di dua profil fixture.
  Claude Code menyelesaikan satu putaran dengan Tool Search dimatikan
  di fixture. OpenCode membaca skill dan mengembalikan lebar video 32 piksel.
- Scaffold dan manifest skill yang diregenerasi cocok dengan Git.

### Benchmark

[Data benchmark kandidat](../benchmark/enterprise-release-evidence.json)
memuat SHA sumber, ukuran payload dan hasil tiap skenario. Benchmark discovery
menggunakan corpus CI 50 kasus yang sama. Hasil top-1 25/40, top-3 30/40,
abstain 6/6 dan nol MCP yang ditawarkan dari empat kasus tanpa kredensial.
Proyeksi lintas kanal mengukur 3.627 token maksimum dengan satu catatan
fixture pada baseline dan kandidat. Lima dari tujuh probe workflow menemukan
skill yang dapat diterima. Dua kasus panjang masih perlu perbaikan ranking.

Ledger OpenCode memakai deklarasi yang benar-benar masuk ke payload model
fixture dan tokenizer `o200k_base`. Ia mencakup bootstrap, deskripsi skill
yang ditautkan oleh AE, skema tool, prompt hook dan hasil pencarian fixture.
Keempat kombinasi utama berada dalam batas 4.000 token.

| Profil OpenCode | Mode | Token AE cold start | Token skema tool AE |
| --- | ---: | ---: | ---: |
| Direct tools | 0 | 3.940 | 1.588 |
| Direct tools | 2 | 3.666 | 1.588 |
| Code Mode | 0 | 3.247 | 895 |
| Code Mode | 2 | 2.976 | 895 |

Smoke tambahan mencakup abstain, lookup dua putaran, perubahan toolset,
tool wajib yang tidak tersedia dan pembacaan panduan plugin. Hasil relevansi
selector live, penggunaan token provider dan biaya inferensi masih terbuka.

#### Coverage

Satu-satunya hasil coverage yang memiliki artefak tercatat di repository
adalah `docs/benchmark/enterprise-release-evidence.json` (field `coverage.files`,
coverage.py 7.13.5 dengan instrumentasi subproses Python). Itulah angka yang
dapat diverifikasi ulang. Tabel 100% / 100% / 100% / 87,5% pada revisi
sebelumnya tidak disertai output pengukuran, karena itu berstatus **NOT VERIFIED**
dan tidak dipakai sebagai bukti.

| Modul | Baris | Coverage | Target kontrak | Status |
| --- | --- | ---: | ---: | --- |
| Runtime lifecycle | 101/120 | 84,2% | 100% | PARTIAL |
| Skills loader | 54/72 | 75,0% | 90% | PARTIAL |
| Memory | 60/114 | 52,6% | 95% | PARTIAL |
| Compression | 57/71 | 80,3% | 80% | PASS |

Cakupan hook host legacy dan kode vendored berada di luar tabel. Target
runtime dan memory **belum** tercapai menurut artefak yang tersedia.

### Prosedur validasi dan rollback

Jalankan dari checkout kandidat dengan HOME terisolasi yang dipersiapkan
oleh operator. Pilih toolchain sesuai target deployment. Gunakan venv hasil
setup dan cache `o200k_base` yang sudah tersedia untuk pengukuran.

```bash
bash unified-integration/setup.sh
bash unified-integration/scripts/setup-mcp.sh --check
AE_PYTHON=".agentenhancements/runtime/venv/bin/python"
"$AE_PYTHON" unified-integration/tests/run-tests.py
"$AE_PYTHON" unified-integration/tests/discovery_benchmark.py --check
"$AE_PYTHON" docs/benchmark/paired-lifecycle.py "$PWD" \
  --home "$HOME" --check
AE_SMOKE_OUTPUT="$(mktemp -d)"
for profile in direct code; do
  for mode in 0 2; do
    "$AE_PYTHON" unified-integration/tests/smoke-adaptive-preflight.py \
      --output "$AE_SMOKE_OUTPUT/$profile" --tool-mode "$profile" \
      --mode "$mode" --exact-tokens
  done
done
```

Jika validasi instalasi gagal, pilih kembali revisi terverifikasi dan
jalankan setup serta doctor dari checkout tersebut. Simpan backup
konfigurasi dan generasi runtime selama verifikasi. Prosedur upgrade
menjelaskan kapan perlu menutup sesi host agar proses aktif memakai satu
generasi paket. [Panduan upgrade dan rollback](../UPDATING.md#updating-core-dependencies)

### Gate yang masih terbuka

- Model live dan Mode 1 native memerlukan akun uji dan bukti host. Smoke
  Codex dengan provider fixture belum membuktikan deklarasi MCP pada
  request model. Bukti doctor mencakup konfigurasi dan panggilan stdio.
- Batas waktu Mode 2 masih perlu dibuktikan untuk resolusi DNS, pembukaan
  TLS dan respons header lambat. Hook OpenCode juga memerlukan bukti
  inventaris segar ketika konfigurasi eksternal berubah saat reload.
- Profil perluasan OpenAI, search dan task-router pernah mengukur 1.928
  token skema pada baseline. Gate 1.800 token di laporan ini mengukur
  profil default. Perluasan provisioning dan perubahan exposure lintas
  host mengikuti [ADR-009](../ADR.md#adr-009--penyajian-tool-dan-provisioning-lintas-host).
- Coverage runtime, loader dan memory **belum** memenuhi target kontrak
  menurut artefak yang tersedia (lihat tabel Coverage). Bukti platform lain,
  lisensi vendored yang masih terbuka dan persetujuan maintainer juga
  diperlukan untuk rilis produksi. [Audit sebelumnya](FINAL_PRODUCTION_READINESS_2026-11-22.md)

### Verifikasi ulang 2026-11-25 (baseline `d775d553`)

Bukti remote: GitHub API melaporkan 11/11 check runs `success` untuk
`d775d553cd949fc9593bf5810e1e96cff57bf984` pada `master` (static checks,
unified-integration, ECC, headroom, MCP, markdownlint, CodeQL dan analisis
dependensi). Remote dan SHA lokal cocok; tidak ada branch sertifikasi yang
masih tertinggal (`merge-base master fix/production-certification` =
`ace90de9`, `git log master..fix/production-certification` kosong — pekerjaan
sudah masuk melalui `179ebcba`).

Lingkungan lokal: Debian 12, Python 3.11.2, ffmpeg 5.1.9. Baseline **sebelum**
perubahan di sesi ini menjalankan 777 test dengan 5 kegagalan yang sama
(sebagian hanya saat suite penuh; kelima test tersebut lulus bila dijalankan
sendiri). Jalankan ulang sesudah perubahan menghasilkan 5 kegagalan yang
identik, jadi bukan regresi dari perubahan di bawah. Karena lingkungan lokal
berbeda dari runner CI, kelima kasus itu ditandai **NOT VERIFIED secara lokal**;
keputusan CI tetap mengacu pada 11/11 check runs di remote.

Perubahan yang diverifikasi dengan test (TDD: test gagal lebih dulu):

- `api_config.external_launch_blocker` menolak shell dan interpreter inline.
  Sebelum perbaikan, `["/bin/bash","-c", ...]` dan `["python3","-c", ...]`
  dinyatakan `visible: true` dan dapat diluncurkan gateway dengan credential
  yang dipetakan. Sekarang keduanya menghasilkan alasan penolakan tertentu.
- `validate_document` menolak pemetaan `env` MCP yang mereferensikan credential
  di luar `required`/`optional`/`any_of` server tersebut.
- `_read_raw_bytes` menolak symlink saat membaca `ui.api.json` saat runtime,
  menyamakan perilaku dengan jalur migrasi.
- `runtime.observer_is_natively_linked` mendeteksi observer native memakai
  `source`, bukan field turunan yang tidak pernah ada di index mentah
  (0/3378 entri). Guard anti-duplikasi kini benar-benar dapat berjalan.
- Karpathy (§7): keempat prinsip upstream hadir di SKILL.md yang dirutekan, di
  prompt konsolidasi, dan di `.cursorrules`; prasyarat MCP/numerik dibuang;
  `catalog.json`, manifest, indeks, dan artefak generated disinkronkan.
  `registry map` berbasis nama prinsip kini menemukan `plugin:karpathy-skills`.

Gate yang masih terbuka (tidak diubah, jangan diklaim lulus): Mode 1 masih
belum memiliki adapter host yang memasok `ae_native_selection` (efektif Mode 0),
model live dan bukti host lain belum tersedia, agregat cold-start 4000 token
belum diukur di jalur hook, SBOM/attestation belum dihasilkan, lisensi vendored
dan persetujuan maintainer belum lengkap.

**Verdict:** **CONDITIONALLY PRODUCTION READY** untuk scope integrasi inti
(discovery, readiness fail-closed, workflow hook, dan CI otomatis) dengan
kondisi di atas. Klaim enterprise production readiness untuk seluruh ekosistem
tetap **NOT VERIFIED** sampai gate terbuka dipenuhi dan bukti platform/live
tersedia. Ringkasan di `IMPLEMENTATION_SUMMARY.md` bersifat self-reported
historis dan tidak menggantikan verdict ini.
