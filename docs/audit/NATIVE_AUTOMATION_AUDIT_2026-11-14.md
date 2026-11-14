---
title: Audit integrasi otomatis Claude Code, Codex, dan OpenCode
version: 1.0
last_updated: 2026-11-14
audience: owner, maintainers
---

# Hasil audit

Integrasi lokal telah dipasang untuk Claude Code 2.1.202, Codex CLI 0.167.2,
dan OpenCode 2.2.5. Pengujian CLI asli dengan model tiruan di localhost
berhasil pada ketiganya: hook menyimpan task dan ringkasan otomatis, tanpa
perintah skill/memori dan tanpa launcher. Pengujian ini memverifikasi jalur
integrasi, bukan kualitas model atau validitas akun layanan eksternal.

Agent: Codex. Session: `codex-audit-20261114`.

## Status repo

- Awal lokal: `master` pada `c6a31456`; GitHub `origin/master` pada
  `7b868327`. Lokal tertinggal **52 commit**, tidak mempunyai commit tambahan.
- Ada 14 file termodifikasi, satu penghapusan, dan 12.994 file untracked
  sebelum audit. Sebagian besar untracked adalah hasil agregasi skill.
- Keadaan awal disimpan melalui `git stash --include-untracked`, dengan
  penanda branch `backup/local-before-audit-20261114`. Stash tetap disimpan,
  termasuk parent untuk file untracked. Jangan menerapkan stash lama ke
  versi baru tanpa meninjau konflik/perbaikan yang sudah digantikan upstream.
- `master` lokal di-fast-forward ke GitHub; perbaikan audit dikerjakan pada
  `audit/native-auto-20261114`. Tidak ada push, force-push, atau publikasi.

Inventaris baseline terbaru: **39.476 file tracked**, sebelum file audit baru.
Review mendalam difokuskan pada kode integrasi milik proyek, konfigurasi
native, generator, utility, sembilan MCP, dan test. Inventaris seluruh vendor
sudah dipetakan; ini bukan klaim audit keamanan setiap baris seluruh vendor.

## Peta isi proyek

| Bagian | Fungsi dan kondisi nyata |
|--------|-------------------------|
| `unified-integration` | Installer, agregasi, adapter native, SQLite, kompresor, MCP dan test; jalur aktif utama |
| `agentic-awesome-skills` | Sumber besar skill; 2.729 nama unik masuk index setelah deduplikasi |
| `anthropic-skills` | 19 skill resmi; menang jika nama berbenturan dengan salinan lain |
| `ECC` | 314 skill masuk index; hooks/plugin lengkapnya tidak otomatis dipasang sebagai plugin ECC |
| `superpowers` | 15 skill pengembangan masuk index |
| `ponytail` | Enam skill masuk index; framework upstream tidak otomatis dijalankan |
| `replica-skill` | 11 skill alur rekonstruksi aplikasi masuk index |
| `claude-mem` | Source vendor; memori integrasi aktif memakai utility SQLite bersama, bukan daemon claude-mem |
| `headroom` | Source Rust/kompresor opsional; native compaction CLI tetap dikelola masing-masing aplikasi |
| `system-prompts-and-models-of-ai-tools` | Koleksi referensi; adapter tiga CLI tidak menimpa sistem prompt asli dengan prompt hasil salinan |
| `plugin-catalog`, `skills` | 21 panduan plugin dan tree modular; keberadaan panduan tidak sama dengan instalasi upstream beserta layanannya |

Index berisi **3.094 skill unik dari enam sumber**, dengan 30 skill kurasi
untuk penemuan native. Hook prompt mencari kandidat lain dari index penuh;
seluruh 3.094 deskripsi tidak dimasukkan ke setiap request.

## Bug dan remediasi

| Temuan | Dampak | Perbaikan |
|--------|--------|-----------|
| Hook Claude membaca variabel `TOOL_NAME`, `TOOL_INPUT`, `SESSION_SUMMARY` yang tidak dikirim dalam format itu | Catatan kosong; tidak ada pemulihan sesi | Event JSON stdin melalui `runtime.py`; startup, prompt, tool dan stop ditangani |
| Merge lama mengganti semua hooks pengguna | Hook milik pengguna hilang | Hanya handler milik integrasi yang diganti; event/handler pengguna dipertahankan |
| MCP ditulis ke `~/.claude/mcp.json`, `~/.codex/mcp.json`; OpenCode tidak dipasang | Konfigurasi ada tetapi CLI tidak memakainya | Claude user `~/.claude.json`, Codex `config.toml`, OpenCode `opencode.json(c)` |
| Klaim Codex tidak mendukung hook | Memori harus dipanggil manual | Pasang lifecycle hooks native; empat hook telah ditinjau dan dipercaya pada mesin ini |
| Config JSONC OpenCode dan array pengguna dapat tertimpa/terabaikan | Plugin/instruksi pribadi hilang atau instalasi tertutup file lain | Edit JSONC yang sudah ada; pertahankan provider, MCP, plugin dan instruksi |
| Belum ada jembatan lifecycle OpenCode | Memori/routing tidak otomatis | Plugin OpenCode 2 untuk prompt/context/idle; tanpa dependency npm runtime |
| Kompatibilitas/nilai prioritas diberi skor walau task tidak relevan | Rekomendasi skill/plugin/MCP palsu | Wajib ada relevansi; normalisasi alias agent dan bedakan prasyarat seperti `python` |
| Memori hanya memakai basename folder | Proyek berbeda bernama sama berbagi catatan | Gunakan path canonical penuh; namespace agent tetap dipertahankan |
| Pembacaan memori mengabaikan expiry, TTL memakai jam lokal | Catatan kedaluwarsa dipulihkan | Filter expiry saat baca/list; TTL baru memakai UTC; file DB privat |
| Fallback shell menghapus semua baris kode berulang; fallback JSON menghapus null/array kosong | Isi dan makna data rusak | Shell memakai utility Python; kode dipertahankan, JSON hanya dipadatkan |
| Updater mem-pipe setup ke `head -20` lalu menelan error | Setup bisa dihentikan SIGPIPE dan tetap dilaporkan sukses | Kuras output sepenuhnya dan teruskan kegagalan |
| Installer satu baris hanya mengambil satu script | Source/aset tidak tersedia di mesin baru | Bootstrap clone lengkap sebelum menjalankan setup |
| Rust selalu dibangun saat cargo tersedia | Instalasi lambat dan membawa build besar yang tidak diperlukan | Opt-in `AGENT_ENHANCEMENTS_BUILD_HEADROOM=1`; fallback tetap tersedia |
| `cancel` task router hanya mengubah metadata | Proses tetap bekerja setelah dibatalkan; status tertimpa menjadi selesai | Hentikan process group, jaga status cancelled, hentikan child pada timeout |
| Task router menampung seluruh output sebelum dipotong | Output besar bisa menghabiskan RAM | Drain stdout/stderr terus-menerus dengan tail terbatas |
| Corpus GraphRAG/timeline video berada di direktori `/tmp` bersama | Teks/path privat dapat terbaca pengguna lain dan bertabrakan | Penyimpanan privat di bawah `AGENT_MEMORY_ROOT`, dipisah menurut cwd, tulis atomik |
| Snapshot registry berisi path mesin pembangun dan status MCP lama | Hint tidak portabel dan server built masih dianggap belum dibuat | Snapshot memakai path relatif; status dan hint diregenerasi |
| Dua test baseline mengasumsikan checkout tidak di `/root` dan scaffold sudah dibuat | Test gagal pada clone/mesin yang valid | Assertion disesuaikan dengan kontrak perilaku |
| arXiv masih HTTP; API Pillow lama deprecated | Transport tidak terenkripsi dan risiko kompatibilitas mendatang | HTTPS; statistik gambar memakai API yang berlaku |

Tidak ada perubahan schema index skill atau schema SQLite. Generator dan
artefak hasilnya tetap diuji sinkron. Penulisan native config memakai backup
privat dan penggantian atomik; JSONC diserialisasi sebagai JSON, sementara
komentar aslinya tetap tersedia di backup.

## Verifikasi

- Installer lengkap berhasil di HOME sementara, lalu berhasil di HOME asli.
  Rerun mempertahankan konfigurasi pengguna dan tidak menduplikasi handler.
- **173/173 test integrasi lulus**, termasuk test jaringan arXiv/Google News,
  pembatalan proses, private state, preservasi config dan pemulihan memori.
- **43/43 test MCP** tercakup dalam suite lengkap tersebut; **9/9** server
  juga diperiksa melalui protokol stdio sesungguhnya.
- Smoke **3/3 CLI asli lulus** dengan fixture localhost dan task/ringkasan
  otomatis terbukti tersimpan di SQLite.
- `bash -n`/ShellCheck severity error, kompilasi **43 file Python owned**,
  pemeriksaan syntax JavaScript, JSON, `git diff --check`, dan validasi
  **21/21** manifest katalog lulus. Script reproduksi ada di bawah.
- Sembilan server lulus stdio `initialize`, `tools/list`, dan `health`.
- Claude Code native melaporkan sembilan MCP `Connected`.
- Codex app-server menemukan 39 skill di mesin ini, termasuk docx/pdf/pptx/xlsx,
  empat hook `trusted`, dan nol error discovery.
- OpenCode server melaporkan plugin `agentenhancements` berstatus `active`.
  Daftar plugin awal bisa kosong karena inisialisasi berlangsung asinkron.
- Smoke CLI lokal: Claude Messages, Codex Responses dan OpenCode Chat
  Completions masing-masing menerima satu respons fixture; setiap agent
  menyimpan dua catatan otomatis (task dan ringkasan). Tidak ada model
  berbayar yang diperlukan untuk test ini. Angka biaya yang dicetak CLI
  pada fixture adalah estimasi dari token tiruan.

```bash
runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
"$runtime_python" unified-integration/tests/run-tests.py
bash unified-integration/scripts/setup-mcp.sh --check
AE_MCP_NETWORK_TESTS=1 "$runtime_python" -m unittest discover \
  -s unified-integration/tests -p test_mcp_servers.py
python3 unified-integration/tests/smoke-native-clis.py
```

## Hal yang masih membatasi

1. **Akun layanan.** Claude Code pada mesin ini belum login. Credential
   OpenCode Console yang ada mengembalikan expired/401. Codex sudah login.
   Setup dan smoke lokal tidak mengganti credential akun. Pemakaian model
   asli memerlukan akun/provider yang valid, sekali dikonfigurasi oleh pemilik.
2. **ECC belum hijau.** Seluruh suite vendornya dijalankan: 8.246 lulus,
   **43 gagal pada 10 file** dari 8.289 test. Rerun terhadap sepuluh file tetap
   menghasilkan 43 kegagalan. Ada asumsi lingkungan yang terbukti gagal
   (`/node_modules` milik host), serta kegagalan Hookify, statusline, memory
   vault, pemeriksaan referensi dan batas waktu PowerShell. Belum semuanya
   dipastikan sebagai bug vendor versus ketidakcocokan lingkungan vendoring.
   Source ECC tidak diubah. Hooks tersebut bukan hooks otomatis yang dipasang
   adapter baru; jangan menganggap seluruh plugin ECC sudah tersertifikasi.
3. **Eksternal belum seluruhnya terpasang.** Sembilan MCP bawaan siap; 29
   server katalog lain tetap memerlukan instalasi/kredensial masing-masing.
   Dua puluh satu panduan plugin bukan bukti seluruh upstream sudah berjalan.
4. **Pemilihan skill memakai pencocokan lexical.** Aktivasi berjalan otomatis,
   tetapi pemilihan skill terbaik dan keberhasilan tugas tetap bergantung
   pada isi task, model, izin tool, serta dependency skill yang dipilih.
5. **MCP bukan sandbox.** Task router menjalankan perintah lokal; denylistnya
   hanya guard sederhana. Batas keamanan dan persetujuan tool tetap milik CLI.
   State MCP dipisah menurut working directory proses; host yang menjalankan
   semua server dari cwd sama akan berbagi namespace state itu.
6. **Memori lama.** Catatan lama yang memakai basename tidak dimigrasikan
   otomatis ke path canonical. Cache MCP lama di `/tmp` juga tidak diimpor
   otomatis karena kepemilikannya tidak dapat diasumsikan.
7. **Dokumentasi historis.** README utama dan laporan audit terdahulu masih
   memuat klaim lama seperti Codex tanpa hooks atau kompresi proxy otomatis.
   Panduan terkini ada di [AGENTS](../AGENTS.md),
   [CONFIGURATION](../CONFIGURATION.md) dan [API](../API.md).

## Credential yang ditemukan

Satu token GitHub ditemukan dalam permission command di file lokal yang
diabaikan Git: `.claude/settings.local.json`. Command tersebut sudah dihapus
dari konfigurasi aktif; salinan keadaan awal disimpan dengan mode 0600 pada
`~/.local/state/agentenhancements/backups/`. Nilai token tidak dimasukkan ke
laporan/commit. File temp yang dahulu tracked tidak mengandung token tersebut;
audit ini tidak membuktikan token itu pernah dipublikasikan di GitHub.
Pemilik perlu mencabut atau merotasi token tersebut. Audit tidak mencabut
credential akun atau menulis ulang sejarah Git.
