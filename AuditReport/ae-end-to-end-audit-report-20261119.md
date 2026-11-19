---
title: Audit end-to-end AgentEnhancements
version: '1.0'
last_updated: '2026-11-20'
audience: maintainer, auditor
---

# Audit end-to-end AgentEnhancements — 2026-11-19–20

Audit dimulai19November dan verifikasi berlanjut20November2026.
Baseline: `master b4ca7e6a`; branch kerja `audit/ae-2026-11-19`.
Agent: Codex; session: `ae-audit-20261119`. Seluruh perubahan kode dapat
ditelusuri melalui conventional commit dengan Agent/Session/Task/Context.

## Hasil dan batas keyakinan

Audit ini memverifikasi integrasi milik AE, generator, batas data runtime,
CLI headroom, registry/discovery, konfigurasi native dan seluruh suite CI.
Tree tracked/history dipindai, tetapi ini bukan sertifikasi setiap baris
semua proyek vendor atau akun/provider eksternal. Eksekusi setup, hook,
fixture dan CLI AE menggunakan HOME/memory/config sementara. Pengecualian
isolasi tool audit dan batas pembandingan HOME dicatat di bawah.

Temuan baru terverifikasi: **30**, P0 **0**, P1 **13**, P2 **16**, P3 **1**. Seluruh temuan baru pada daftar berikut ditangani dengan regression test.
Risiko P2/P3 yang ditunda dipisahkan dari temuan yang sudah diperbaiki.

## Ringkasan sebelum dan sesudah

| Ukuran | Sebelum | Sesudah |
| --- | --- | --- |
| Integration baseline | 323 tes, OK, 3 live opsional skip | 394 tes OK,3 opsional skip pada clone baru |
| Default setup | exit0 tetapi build Rust E0432, fallback | binary headroom dibangun; run2 memakai binary yang ada |
| Filelock | 13 advisori, resolver3.32.7 | >=4.2.1; pip-audit tidak menemukan advisori |
| Loader/hook top-1 | 15/40 (37.5%) | 25/40 (62.5%) |
| Loader/hook top-3 | 20/40 (50%) | 30/40 (75%) |
| Registry top-1 / top-3 | 23/40;28/40 | 25/40;30/40 |
| Abstain ordinary tools | loader/hook2/6 | semua surface6/6 |
| MCP unavailable advertised/ready | 0/4;0/4 | 0/4;0/4 |
| Hook token p50/p95/max | 236.5/258/262 | 276/298/304 |
| Hook ms p50/p95 | 1129.898/1310.251 | 929.655/988.655 |

Benchmark memakai 50 prompt tetap (25EN/25ID): 32 positif,8 ambigu,
6 negatif,4 MCP unavailable. Akurasi adalah hit pada acceptable guide IDs
untuk40 intent positif/ambigu, bukan keberhasilan agent menyelesaikan tugas.
Corpus dibekukan sebelum perubahan ranker; ID MCP typo pada validasi awal
diperbaiki sebelum baseline resmi dan tidak dipakai untuk menaikkan skor.
Fixture SHA-256: `d54bc497947ef5b2b1970c52011d27ff454dd34528ed23db839a4410aea4adb0`.

Token diukur dengan tiktoken0.12.0/o200k_base. Median CPU loader meningkat
135.965→216.435ms; perubahan ini tidak diklaim sebagai percepatan. Kartu hook
menyusut356→309 kartu, semua summary utuh, tanpa label bahwa panduan sudah
dimuat. Mode0 mempertahankan format suggestion; actual host permissions
dan keputusan membaca skill tetap milik agent. Token overhead final meningkat dari baseline namun tetap di bawah400;
fallback lokal menghindari download tokenizer saat hook. Tidak ada klaim
penurunan token untuk versi final. Latensi diukur pada host
bersama dengan subprocess/tokenizer, bukan SLA provider produksi.

Jalankan ulang: `python3 unified-integration/tests/discovery_benchmark.py --check`.
CI memeriksa tiap surface >=25/40 top1 dan >=30/40 top3, semua6 abstain,
nol unavailable advertised/ready, JSON valid, sumber stabil dan <=400 token.

## Temuan terverifikasi dan reproduksi

Lokasi berikut menunjuk working tree final. Perintah regression umum memakai
`.agentenhancements/runtime/venv/bin/python -m unittest discover`
dengan `-s unified-integration/tests -p <module>.py -v`. Fixture yang membuat
HOME sendiri membersihkan host aliases seperti pada langkah CI.
Semua credential dan endpoint dalam test adalah fixture sintetis/localhost;
nilai credential nyata tidak dicetak, disimpan di laporan atau commit.

### AE26-01 — P1 — Kredensial otomatis belum disamarkan utuh

- Lokasi: `unified-integration/scripts/api_config.py:45`.
- Bukti/reproduksi: Authorization: Bearer meninggalkan nilai token pada catatan; adapter observer dan key provider sekunder memiliki celah redaksi yang sama.
- Akar masalah: Pattern lama hanya menangkap awalan Authorization/Bearer dan nilai configured tidak dicakup konsisten.
- Perbaikan: Redaktor bersama menangani Bearer/Basic, quoted fields, central keys dan semua rotated provider keys sebelum penyimpanan.
- Regresi: `test_security_regressions.MemorySecurityTests.test_bearer_credentials_are_not_saved_by_lifecycle_events; ObserverSecurityTests; CredentialRedactionTests`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-02 — P1 — Preflight mengirim kredensial prompt dan mencetak detail model

- Lokasi: `unified-integration/scripts/adaptive_preflight.py:974`.
- Bukti/reproduksi: Fixture selector menangkap configured/preflight/Bearer key dari prompt; alasan unresolved dapat menyisipkan token dan baris log.
- Akar masalah: Intent dibatasi ukurannya tetapi tidak disamarkan; detail model diperlakukan sebagai diagnosis aman.
- Perbaikan: Samarkan intent dan key selector; stderr hanya reason code satu baris.
- Regresi: `test_security_regressions.PreflightSecurityTests.test_selector_never_receives_configured_or_bearer_credentials; test_selector_response_details_cannot_leak_credentials_into_stderr`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-03 — P2 — Deadline dapat dilampaui oleh body lambat dan hasil terlambat

- Lokasi: `unified-integration/scripts/adaptive_preflight.py:744`.
- Bukti/reproduksi: Server fixture mengirim body perlahan; adapter mengembalikan abstain sesudah deadline; HTTP400 kompatibilitas dapat memulai request kedua terlambat. File non-UTF8 juga memicu exception.
- Akar masalah: Timeout socket per-read bukan deadline seluruh fase; pemeriksaan setelah inferensi dan error Unicode belum lengkap.
- Perbaikan: Periksa sisa deadline saat membaca body, sebelum request lanjutan dan setelah inferensi; tolak hasil terlambat dan fallback konfigurasi rusak.
- Regresi: `test_security_regressions.PreflightSecurityTests: slow_response_body, late_abstain, expired_deadline, non_utf8`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-04 — P1 — Symlink preflight.key lolos sebagai file privat

- Lokasi: `unified-integration/scripts/adaptive_preflight.py:686`.
- Bukti/reproduksi: Symlink ke file fixture mode0600 diterima resolver sebelumnya.
- Akar masalah: stat mengikuti symlink; pemeriksaan identitas file/owner belum memadai.
- Perbaikan: Gunakan pemeriksaan file regular, owner, ukuran dan mode serta penolakan symlink sebelum menerima key.
- Regresi: `test_security_regressions.PreflightSecurityTests.test_key_file_symlink_is_not_treated_as_a_private_key_file`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-05 — P1 — Batas path ffmpeg dan file concat tidak aman

- Lokasi: `unified-integration/mcp-servers/ffmpeg-mcp/server.py:48`.
- Bukti/reproduksi: Path saudara yang memiliki prefix sama lolos; nama berisi newline menyisipkan directive concat; scratch predictable dapat menimpa target symlink.
- Akar masalah: Validasi menggunakan string.startswith dan scratch/list concat tidak diklaim secara unik.
- Perbaikan: Periksa ancestry path resolved, tolak nama pembentuk directive dan buat scratch unik yang dibersihkan.
- Regresi: `test_security_regressions.FfmpegSecurityTests (3 kasus)`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-06 — P1 — SQLite dibuka sebelum klaim file privat dan menuruti symlink

- Lokasi: `unified-integration/scripts/memory.py:26`.
- Bukti/reproduksi: DB symlink memodifikasi database fixture lain; direktori lama0755 tidak diperketat. Initializer/legacy hooks memiliki jalur serupa.
- Akar masalah: chmod dilakukan setelah sqlite.connect; initializer bergantung pada umask pemanggil.
- Perbaikan: Klaim regular file0600 dengan O_NOFOLLOW/fstat sebelum SQLite; root0700; initializer dan semua generator hook disamakan.
- Regresi: `test_security_regressions.MemorySecurityTests; test_setup_safety initializer/legacy hook tests`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-07 — P1 — Redirect HTTP meneruskan Authorization ke origin lain

- Lokasi: `unified-integration/mcp-servers/embeddings-mcp/server.py:1`.
- Bukti/reproduksi: Dua server localhost membuktikan header dapat mengikuti302 pada embeddings/vision.
- Akar masalah: Handler urllib default mengikuti redirect authenticated request.
- Perbaikan: Tolak redirect request authenticated; endpoint eksplisit tetap mengikuti konfigurasi pengguna.
- Regresi: `test_security_regressions.CredentialRedirectTests`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-08 — P1 — ae_health membocorkan nilai sebelum redaksi/truncation

- Lokasi: `unified-integration/mcp-servers/gateway.py:115`.
- Bukti/reproduksi: Health fixture mengembalikan credential panjang dalam status/reason/metadata; prefix tetap terlihat bila dipotong dahulu.
- Akar masalah: Jalur health berbeda dari hasil tool biasa dan membersihkan field secara parsial.
- Perbaikan: Redaksi rekursif payload lengkap sebelum pembatasan field/string.
- Regresi: `test_security_regressions.GatewayHealthSecurityTests`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-09 — P2 — Cache arXiv/news memakai namespace /tmp bersama

- Lokasi: `unified-integration/mcp-servers/arxiv-mcp/server.py:33`.
- Bukti/reproduksi: Dua konfigurasi memory root lama berbagi cache; file mode mengikuti umask.
- Akar masalah: Lokasi cache global predictable, bukan state user privat.
- Perbaikan: Cache di AGENT_MEMORY_ROOT/mcp, direktori0700 dan penggantian atomik file0600; cache lama tidak diimpor.
- Regresi: `test_security_regressions.SearchCacheSecurityTests`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-10 — P1 — Consent/audit log mengikuti symlink dan mencetak credential

- Lokasi: `unified-integration/scripts/consent-gate.sh:22`.
- Bukti/reproduksi: Symlink log fixture mengubah file personal; purpose configured key muncul pada layar consent dan log lama.
- Akar masalah: touch/chmod/append mempercayai tujuan; tampilan dan log tidak memakai redaktor bersama.
- Perbaikan: Tolak parent/file symlink, private0700/0600, samarkan tampilan dan JSON. Helper tetap eksplisit, bukan gateway enforcement otomatis.
- Regresi: `test_security_regressions.AuditLogSecurityTests (4 kasus)`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-11 — P1 — Agregasi menghapus data melalui direktori symlink

- Lokasi: `unified-integration/setup.sh:432`.
- Bukti/reproduksi: Fixture by-category/general mengarah ke direktori personal; rm-rf target menghapus marker. Stub cp gagal tetapi setup lama tetap exit0 dan mengindeks file hilang.
- Akar masalah: Parent destination tidak diperiksa; error copy ditelan dengan || true.
- Perbaikan: Periksa setiap direktori registry sebelum mkdir/copy; hentikan proses bila penyalinan gagal.
- Regresi: `test_setup_safety aggregation symlink/copy failure cases`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-12 — P2 — Nama skill registry keluar dari direktori tautan

- Lokasi: `unified-integration/scripts/link-skills.sh:87`.
- Bukti/reproduksi: Nama ../escape menghasilkan symlink di luar native target fixture.
- Akar masalah: Nama/category dipakai sebagai komponen path tanpa validasi.
- Perbaikan: Validasi komponen, karakter kontrol dan source containment; guard unlink juga menolak traversal.
- Regresi: `test_setup_safety.test_linker_rejects_registry_name_traversal`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-13 — P1 — Pin instalasi gagal tetapi default branch tetap dieksekusi

- Lokasi: `unified-integration/setup.sh:19`.
- Bukti/reproduksi: Git fixture menggagalkan checkout; bootstrap lama tetap menjalankan script default dengan exit0.
- Akar masalah: Kegagalan explicit revision dianggap warning dan fallback aman.
- Perbaikan: Fetch/checkout pin harus sukses; batalkan tanpa mengeksekusi default/stale checkout dan pertahankan perubahan lokal.
- Regresi: `test_setup_safety.test_piped_installer_refuses_missing_pin`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-14 — P2 — Build headroom bawaan tidak pernah menghasilkan CLI yang dipakai

- Lokasi: `headroom/crates/headroom-cli/src/main.rs:55`.
- Bukti/reproduksi: Setup baseline752.630s menemukan E0432 PipelineMode yang tidak ada; package juga menamai output headroom-cli sementara installer mencari headroom.
- Akar masalah: CLI vendor tertinggal dari core API dan nama binary tidak diselaraskan.
- Perbaikan: Gunakan enum CLI yang ada; tetapkan binary headroom; build hanya package CLI dengan --locked; tambah job CI wajib.
- Regresi: `cargo test --manifest-path headroom/Cargo.toml --locked -p headroom-cli; explicit_modes/json tests`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-15 — P1 — CLI standalone membuang data ke cache yang hilang saat exit

- Lokasi: `headroom/crates/headroom-cli/src/main.rs:159`.
- Bukti/reproduksi: Seribu record JSON menghasilkan cache_keys dan output tidak mandiri setelah compile diperbaiki.
- Akar masalah: Pipeline offload memakai InMemoryCcrStore tanpa retrieval service yang bertahan.
- Perbaikan: CLI hanya memakai reformats mandiri; offload tetap tersedia untuk host/proxy yang memiliki retrieval store.
- Regresi: `Rust standalone_json_keeps_every_row_without_transient_offloads: RED lalu GREEN`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-16 — P2 — Dependency rentan/stale dianggap siap hanya karena dapat diimport

- Lokasi: `unified-integration/scripts/setup-mcp.sh:13`.
- Bukti/reproduksi: pip-audit pada requirements lama menemukan13 advisori pada filelock3.32.7; fixture environment importable tidak memanggil installer setelah constraint berubah.
- Akar masalah: Rentang <4 menolak versi patched; prepare tidak mengecek perubahan requirements.
- Perbaikan: Floor filelock4.2.1,<5 dan digest requirements memperbarui venv sekali saat kontrak dependency berubah.
- Regresi: `test_runtime_dependencies; pip-audit setelah perbaikan exit0`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-17 — P2 — Keluaran clamp melebihi batas token

- Lokasi: `unified-integration/scripts/context_budget.py:94`.
- Bukti/reproduksi: Satu baris panjang menghasilkan421 token untuk batas400; limit kecil juga overflow.
- Akar masalah: Slice karakter tidak menyisihkan biaya notice dan rasio Unicode.
- Perbaikan: Ukur output+notice bersama dan cari prefix yang muat; limit tak cukup menghasilkan string kosong.
- Regresi: `test_context_budget_boundaries (3 kasus)`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-18 — P2 — Registry, loader dan hook memilih panduan berbeda

- Lokasi: `unified-integration/scripts/load-skills.py:40`.
- Bukti/reproduksi: Corpus dibekukan50 prompt: loader/hook top1=15/40, top3=20/40 dan abstain2/6, berbeda dari registry23/40 dan28/40.
- Akar masalah: Dua ranker terpisah, alias host tidak dinormalisasi, terjemahan domain terbatas dan loader tidak memiliki floor relevansi.
- Perbaikan: Loader memakai ranker registry setelah filter host; alias dan istilah teknis Indonesia dinormalisasi tanpa tabel prompt→ID.
- Regresi: `test_discovery_quality; discovery_benchmark.py --check, fixture hash d54bc497947ef5b2b1970c52011d27ff454dd34528ed23db839a4410aea4adb0`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-19 — P2 — Readiness skill dan built MCP memberi petunjuk aktivasi palsu

- Lokasi: `unified-integration/scripts/registry.py:687`.
- Bukti/reproduksi: File hilang/outside-root atau native name milik pengguna tetap dilabel ready/loaded; built external agent_browser disebut auto-loaded.
- Akar masalah: Readiness memakai metadata/name saja dan menganggap semua status built adalah bundled.
- Perbaikan: Cek file/root/link exact; bedakan guide direct-read dari native-loaded; gunakan daftar BUILTINS untuk hint gateway otomatis.
- Regresi: `test_discovery_quality missing/foreign/symlink/native revocation/external built tests`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-20 — P2 — Angka dan klaim publik mengalami drift berulang

- Lokasi: `scripts/generate_capability_counts.py:48`.
- Bukti/reproduksi: About GitHub7proyek/2788+, README9proyek dan AAS2781 vs2729 tanpa label raw/unique; status plugin diwarisi dari boolean vendored.
- Akar masalah: Angka/teks diulang tanpa generator dan status implementasi dicampur dengan provenance/readiness.
- Perbaikan: Hasilkan inventory JSON/Markdown, dua README blocks dan deskripsi repo dari data canonical; CI menjaga drift lokal+remote.
- Regresi: `test_capability_counts; test_modular_docs; generate_capability_counts.py --check`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-21 — P2 — CI registry tidak mengagregasi perubahan vendor

- Lokasi: `.github/workflows/registry-regeneration.yml:74`.
- Bukti/reproduksi: Fixture sumber baru tetap menghasilkan index/registry lama dari step workflow yang diekstrak.
- Akar masalah: Workflow hanya membangun consumer dari snapshot index committed.
- Perbaikan: Jalankan setup canonical terisolasi sebelum registry/map dan perluas path triggers; pin official actions dan gunakan npm ci.
- Regresi: `test_registry_workflow RED→GREEN; test_ci`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-22 — P2 — Direktori source headroom dipilih sebagai executable

- Lokasi: `unified-integration/scripts/compress.py:30`.
- Bukti/reproduksi: Di cwd repo, exists("headroom") benar untuk direktori; utility gagal menjalankan command dan memakai fallback walau binary sudah dibangun.
- Akar masalah: exists dipakai untuk menilai executable dan which eksternal tidak memeriksa pilihan awal.
- Perbaikan: Wajib regular executable, resolusi path absolut, lalu shutil.which dan fallback binary; smoke menolak fallback tersembunyi.
- Regresi: `test_compress.test_binary_detection_skips_directories_and_uses_executable_fallback`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-23 — P2 — Reference YAML menyimpan path mesin pembangun

- Lokasi: `unified-integration/setup.sh:1408`.
- Bukti/reproduksi: Setup setelah build menghasilkan path/tmp checkout pada file tracked sehingga clone lain drift.
- Akar masalah: Heredoc memperluas HEADROOM_CMD ke artifact reference.
- Perbaikan: Quoted heredoc menyimpan referensi literal HEADROOM_BIN; artifact ditambahkan ke test_sync.
- Regresi: `test_setup_safety compression reference config; test_sync`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-24 — P2 — MCP smoke mengabaikan XDG_DATA_HOME

- Lokasi: `unified-integration/scripts/mcp-test.sh:29`.
- Bukti/reproduksi: Venv valid pada data root custom tidak dipilih; script mencoba Python default tanpa json5.
- Akar masalah: Lookup hardcoded ke HOME/.local, berbeda dari setup-mcp canonical.
- Perbaikan: Gunakan fallback XDG_DATA_HOME yang sama; fixture interpreter membuktikan runtime custom dipilih.
- Regresi: `test_runtime_dependencies.test_mcp_smoke_uses_the_prepared_project_runtime`. Kegagalan sebelum perbaikan dan keberhasilan sesudahnya
  dicatat pada evidence lokal; status final/CI tercantum di penutupan.

### AE26-25 — P3 — Metadata orchestrator REA masih mendeskripsikan riset hipotesis

- Lokasi: `plugin-catalog/catalog.json:194`.
- Bukti/reproduksi: test_rea_catalog_role_matches_reverse_engineering_guide gagal: research != reverse-engineering; guide dan dispatcher sudah benar.
- Akar masalah: Metadata ringkas tertinggal dari perubahan identitas upstream.
- Perbaikan/regresi: Selaraskan role dan for_mode dengan binary/APK/application analysis; targeted test lulus.
- Status: ditutup; commit `0e1de429`.

### AE26-26 — P1 — Rust lockfiles membawa dependency dengan advisori terpublikasi

- Lokasi: `headroom/crates/headroom-core/Cargo.toml:129`.
- Bukti/reproduksi: cargo-audit0.23.0 mencatat2 vulnerability records headroom dan5 ECC2; SQLite disclosure muncul di kedua lockfile. Ada pula rustix/tokio unsound warnings.
- Akar masalah: Lockfiles vendor belum memperbarui dependency patched; rusqlite0.40 menahan SQLite lama.
- Perbaikan/regresi: Naikkan rusqlite0.41 dan minimal lock updates SQLite/quinn-udp/libz/webpki/roots/rustix/tokio. Kedua audit sesudah exit0 tanpa ignore; headroom3tes danECC2 508tes lulus.
- Status: ditutup; commit `2c051703`.

### AE26-27 — P1 — Checkout baru masih memakai gateway/plugin/skill milik checkout lama

- Lokasi: `unified-integration/scripts/native-integration.py:122`.
- Bukti/reproduksi: Empat fixture relocation gagal sebelum fix: gatewaylama dipertahankan, pluginOpenCode ganda, symlinkHermes dan skill tetap ke checkout yang dihapus.
- Akar masalah: Pengenalan kepemilikan membandingkan prefix root saat ini, sehingga milik AE dari lokasi lama dianggap milik pengguna.
- Perbaikan/regresi: Kenali suffix entry point canonical, refresh hanya path milik AE, pertahankan foreign entries/approvals. Module native16tes lulus; clone final memakai root baru.
- Status: ditutup; commit `fc74ce70`.

### AE26-28 — P2 — Profil browser dan indeks sesi keluar dari root terpilih

- Lokasi: `mcp-servers/agent_browser/src/session-manager.js:18`.
- Bukti/reproduksi: Default profil berada di HOME; custom profileRoot tetap membaca/menulis SESSIONS_INDEX global sehingga reload/per-root isolation gagal. Tes storage gagal sebelum fix.
- Akar masalah: Konstanta indeks dihitung dari default global alih-alih instance profileRoot.
- Perbaikan/regresi: Default profil checkout-local, indeks per-instance,0700direktori,0600atomicfile, tolak symlinkprofil. npm test kini memiliki regression nyata dan lulus.
- Status: ditutup; commit `88211d7e`.

### AE26-29 — P2 — ID sesi tidak dibatasi sebagai komponen direktori

- Lokasi: `mcp-servers/agent_browser/src/session-manager.js:60`.
- Bukti/reproduksi: Fixture getProfilePath untuk ../outside dan path absolut tidak ditolak; assert.throws gagal sebelum guard. Eksploitabilitas seluruh wrapperMCP tidak diasumsikan.
- Akar masalah: path.join dipakai tanpa validasi ID pada API SessionManager.
- Perbaikan/regresi: Batasi ID string128karakter, karakter komponen aman, tolak dot/dotdot/separator; dua offline browser tests lulus.
- Status: ditutup; commit `88211d7e`.

### AE26-30 — P2 — Tokenizer opsional dapat mengunduh data saat Mode0

- Lokasi: `unified-integration/scripts/context_budget.py:80`.
- Bukti/reproduksi: cache encoding kosong/rusak menyebabkan pemanggilan
  get_encoding mencoba pemuatan yang dapat mengakses jaringan. Dua subcase
  mockdownload gagal sebelum fix; ukuran awal opsional coldcache melebihi8detik.
- Akar masalah: fungsi perkiraan token menginisialisasi dependency/data
  opsional pada jalur hook, di luar deadline selector.
- Perbaikan: hanya gunakan encoder yang sudah diinisialisasi host; selain
  itu gunakan math lokal terdokumentasi. Hook tidak memulai IOtokenizer.
  Empat boundary/offline tests lulus; benchmark exact tetap menginisialisasi
  proxy encoder secara eksplisit di alat pengukuran terpisah.
- Status: ditutup; commit`cba4e255`.

## Kebutuhan tambahan: semua state milik AE di checkout

RQ26-01 disetujui pengguna secara eksplisit pada2026-11-19. Default lama
user-scope merupakan desain lama, bukan insiden baru. Commit`37acee88`
memusatkan venv/cache/model/preferences/memory ke `.agentenhancements/`
private0700 yang diabaikan git. Bridge konfigurasi host tetap mengarah ke
kode checkout; installer menolak override state/memory/API/model/headroom
di luar checkout. Empat fixture scope dan empat fixture relocation
memverifikasi kebutuhan ini. Tidak ada migrasi atau penghapusan data
global otomatis. Explicit override untuk low-level fixture tetap didukung;
layout ini bukan sandbox OS untuk semua perintah shell pengguna.

## Inventaris dan status temuan lama

Sumber hitungan: all-skills.json, catalog.json, mcp-servers.json, constants
built-in/defaults dan notice LICENSE; generator tidak mengimpor credential.
Hasil saat audit:3378 skill unik dari3430 record/8 sumber,40 plugin dari22
upstream,40 MCP entry (10 built/30to-install),9 backend Python bundel,
8 default-enabled,8 capability,16 skill native default,11 proyek vendor.
Status implementasi, provenance vendor dan readiness host tetap terpisah.

Sembilan laporan tambahan dari upstream`b6e1c056` juga dibaca dan diverifikasi:
[rekonsiliasi audit tambahan](ae-incoming-audit-reconciliation-20261119.md).
Klaim noCI/noTests/toolswildcard pada laporan baru tidak sesuai bukti.

Rekonsiliasi lengkap seluruh `docs/audit/`, `AuditReport/` dan ledger SDD:
[status audit terdahulu](ae-prior-audit-reconciliation-20261119.md).
Poin penting: billing/CI AE-01 historis sudah selesai sebelum audit ini;
SQL/TTL/merge/native-path lama tetap tertutup; S4 health terbukti regresi
dan diperbaiki sekarang; klaim Task4 headroom sebelumnya tidak cukup karena
build nyata masih gagal. Ledger SDD yang belum dicentang tidak dianggap
bukti tugas belum dikerjakan. DOC-06/07/08 dan runtime-XDG yang ditemukan
pada rekonsiliasi tambahan sudah ditangani pada dokumen/kode final.

## Secret, dependency dan data-flow audit

Gitleaks8.30.1 diunduh dari rilis resmi dan checksum diverifikasi. Scan
tracked tree baseline:498 kandidat/231 file; semua Git refs/history:
766 kandidat/285 file (exit1 berarti kandidat terdeteksi). Temuan banyak
berupa tutorial auth, key/JWT fixtures, pattern private-key dan ID dataset;
hasil mentah disimpan hanya dengan redaksi100%. Ini bukan hasil scanner
"zero alerts" dan tidak dipromosikan menjadi jaminan zero-secret.

AWS/Stripe/GCP kandidat yang ditinjau berada di test redaksi/commit-quality;
marker private-key berada di fixtures/pattern docs. Kandidat code non-doc
ditinjau tanpa mencetak literal. Tidak ada credential produksi penuh yang
dikonfirmasi. Snapshot/data vendor besar belum mendapat validasi kredensial
ke provider, karena audit tidak boleh menguji token yang ditemukan.
Preview credential di laporan produksi lama dihapus dari tree; history
tidak ditulis ulang. Jika preview berasal dari key aktif, pemilik sebaiknya
merotasinya. PAT yang diberikan dalam percakapan hanya dipakai untuk
operasi GitHub melalui file sementara0600; tidak masuk repository.

Read-only original memory: DB0600, root0755,191 baris,0 empty type,
177 baris dengan TTL,0 expired. Ini snapshot awal sebelum kebutuhan
checkout-local; runtime baru tidak mengimpor DB global. Tidak ada payload
atau isi note dibuka ke log.
Patch memperketat root saat initializer dipakai; audit tidak mereinstall
ke HOME asli. Hash snapshot HOME berubah selama proses host aktif; audit tidak
menjalankan installer ke HOME asli dan tidak menimpa data host yang berubah.
Perbandingan terarah19konfigurasi mendapati satu file profilHermes berubah
bersamaan; atribusi tidak dapat dipastikan dari hash. Tidak ada klaim
HOME byte-identik. Path proyek canonical disimpan untuk scope memori;
raw tool input/output tidak disimpan. Automatic notes disamarkan dan TTL7
hari; manual API memory.save tetap menyimpan data eksplisit pemanggil.

Satu pemanggilan awal npx markdownlint memakai cache npm HOME host.
Pemanggilan berikutnya mengarahkan HOME/cache ke lokasi terisolasi, lalu
ke dalam checkout. Ini kesalahan isolasi tool audit; isi cache awal tidak
tersedia untuk pemulihan yang aman, sehingga cache host tidak dihapus
atau ditimpa. Karena itu tidak ada klaim bahwa seluruh HOME tidak berubah.

Mode0 preflight tetap lokal; Mode2 opt-in mengirim bounded redacted prompt
dan metadata publik ke endpoint HTTPS yang dipilih pengguna. Ini bukan
classifier semua data privat; pengguna tetap menentukan kelayakan egress.
model.json tidak memuat key. Redirect authenticated request ditolak.
Claude credentials/hooks/provider fields tetap dipertahankan oleh adapter
native dan regression preservation tests; AE tidak mengimpor login host.

pip-audit baseline menemukan13 advisori pada filelock<4; rentang sekarang
memungkinkan versi patched4.2.1 dan install baru terverifikasi bersih.
Contoh advisori resmi: [GHSA-v4x8-3wr5-3wq8](https://github.com/advisories/GHSA-v4x8-3wr5-3wq8),
[GHSA-9vhv-jxww-xfm5](https://github.com/advisories/GHSA-9vhv-jxww-xfm5).
Npm audit ECC menemukan7 moderate pada dependency tooling/transitif,
0high/0critical; bukan bukti kerentanan semua jalur runtime AE. Perubahan
major overrides tidak dipaksakan tanpa validasi kompatibilitas upstream.

## Risiko tersisa, dugaan dan batas verifikasi

- P2 lisensi: cakupan doc-coauthoring tanpa LICENSE.txt/root license belum
  terbukti.18/19 license skill Anthropic terverifikasi in-tree. Hak arsip
  prompt komersial/GPL (AE-03) tetap keputusan maintainer. Salinan prompt
  mempertahankan lisensi sumber; notice MIT bukan relicense konten vendor.
- P2 dependency:7 advisori moderate tooling npm dan Python version ranges
  tetap dicatat. Tidak ada threshold audit diturunkan atau audit ignore
  ditambahkan untuk memperoleh exit0.
- P2 effectivity:15/40 strict top1 dan10/40 top3 masih miss; intent ambigu
  memerlukan query lanjutan. Belum ada uji kualitas selector model eksternal
  atau bukti model benar-benar memakai tiap suggestion pada produk akhir.
- P2 browser live: target npm test kini benar-benar menjalankan dua
  regression storage/boundary, tetapi dua script browser live di root masih
  memerlukan Chromium/jaringan. Fresh config menonaktifkan backend sampai
  instalasi eksplisit. Flow browser nyata tidak diklaim telah lulus.
- P2 consent/audit: helper benar menolak EOF dan mencatat keputusan, tetapi
  gateway tidak memaksa caller eksternal menjalankannya; host approval tetap
  berlaku. Kebijakan retensi/PII bukan mekanisme auto-enforcement.
- Lint warisan ditutup:1108diagnostik baseline →816review awal →0final
  pada aturan default yang sama. CI sekarang wajib lulus; advisory dan
  continue-on-error markdownlint dihapus, bukan ditambahkan.
- Linux diuji; macOS/Bash3.2, Windows native/WSL dan akun model/cloud riil
  tidak disertifikasi dari fixture Linux. UI hook trust Codex tidak dilewati.
- Native fixtures Hermes2profil dan OpenCode berhasil; baseline smoke all
  masih gagal pada discovery Codex/Claude dalam state fixture yang terpapar
  config overrides. Protocol gateway10/10 dan adapter preservation teruji;
  ini tidak diklaim sebagai login/provider account verification.
- Review tambahan sub-agent keamanan ditolak filter risiko siber; tidak ada
  persetujuan independen yang diklaim dari langkah tersebut. Review kode
  utama dan seluruh regression tetap menjadi bukti yang dapat diperiksa.

Dugaan yang tidak direproduksi (misalnya seluruh input prompt bebas rahasia
yang tidak dikenali, jaminan semua metadata vendor bermutu, semua OS/native
host otomatis memakai skill) tidak dicatat sebagai temuan terverifikasi.

## Register risiko yang masih terbuka

Semua ID berikut merupakan residual dengan severity di bawahP1, terpisah
dari30perbaikan baru. Tidak ada P0/P1 terverifikasi yang dibiarkan terbuka.

| ID | Severity | Lokasi | Bukti/akar masalah | Keputusan dan rencana |
| --- | --- | --- | --- | --- |
| AE26-R01 | P2 | `docs/LICENSE_AUDIT.md:1`; `anthropic-skills/skills/doc-coauthoring/` | Tidak ada LICENSE.txt pada satu bundle dan tidak ada root LICENSE vendor; hak arsip promptGPL/komersial belum menjadi keputusan hukum auditor. | Terbuka; notice dibetulkan,18/19license diperiksa; maintainer perlu klarifikasi upstream/hak redistribusi. |
| AE26-R02 | P2 | `ECC/package-lock.json:1` | npm audit:7moderate,0high/critical; tooling transitive memerlukan beberapa perubahan major menurut resolver. | Terbuka; hindari major override tanpa suite upstream; target perbaikan dependency upstream, tanpa audit ignore/thresholdlonggar. |
| AE26-R03 | P2 | `unified-integration/tests/fixtures/discovery-prompts.json:1` | Ranker leksikal masih miss15/40top1 dan10/40top3 meski peningkatan terukur. | Terbuka; evaluasi corpus dan domain lebih luas sebelum perubahanmodel/classifier; jangan overfit jawaban fixture. |
| AE26-R04 | P2 | `unified-integration/tests/test_adaptive_preflight.py:1`; `docs/AGENTS.md:1` | Tiga default live/network tests opt-in; dua arxiv/news sudah lulus secara eksplisit; semua OS/trust/account model tidak tersedia dari fixtureLinux. | Terbuka; butuh host/credential/trust native yang relevan untuk sertifikasi tambahan; tidak melewati approval CLI. |
| AE26-R05 | P2 | `unified-integration/scripts/consent-gate.sh:1`; `unified-integration/mcp-servers/gateway.py:1` | Helper eksplisit bukan enforcement universal semua MCPeksternal; hostapproval tetap batas otorisasi. | Terbuka; dokumentasi jujur, backend sensitif tidak aktif default; policy gateway universal memerlukan desain terpisah. |
| AE26-R06 | P2 | `.github/workflows/ci.yml:1`; `unified-integration/requirements.txt:1` | Scan manual tree/history/Python/npm/Rust ada, tetapi SCA/SBOM/secret baseline berkala belum lengkap. Kandidat vendor belum semuanya terklasifikasi. | Terbuka; tidak menambahkan ignore massal atau scan palsu. Tambah automation setelah baselinefalse-positive dan kebijakan re-vendor jelas. Recommendedcurlpipe dihapus. |
| AE26-R07 | P3 | `headroom/Cargo.lock:1`; `ECC/ecc2/Cargo.lock:1` | cargo-audit kini0vulnerability/0unsound; masih ada informasi unmaintainedchrono/humantime/paste/pin-utils tanpa patchedreplacementlangsung. | Terbuka; monitor upstream dan evaluasi pengganti kompatibel. Warning tidak disembunyikan. |
| AE26-R08 | P3 | `unified-integration/skills/all-skills.json:1`; `task-observer/SKILL.md:1` | Semua metadata/prose vendor dan resistansi prompt-injection belum disertifikasi universal; katalog diperlakukan sebagai data dan dibatasi budget. | Terbuka; review sumber sesuai task/permission, uji domain tambahan; tidak mengklaim seluruh vendor bebas masalah. |

## Keterlacakan perbaikan

| Commit | Temuan/kebutuhan | Status |
| --- | --- | --- |
| `b1e4fc23bf7e09638371f9419693aa5e1c41291c` | AE26-01–10 | Ditutup; hasil clone/CI di penutupan |
| `8c792325978295fff9585e3eadb41e8049443f81` | AE26-14,15,22,23 | Ditutup; hasil clone/CI di penutupan |
| `902da7e4d00a0fee13b7ca5000a0a0e1d9f7e87f` | AE26-17–19 | Ditutup; hasil clone/CI di penutupan |
| `a7f61f16fd28cc9c35fe4fcb2fc8f9a8d7ee5b9a` | AE26-11–13,16,24 | Ditutup; hasil clone/CI di penutupan |
| `fc74ce701e27df944fa76a9fdda12f08e40069ce` | AE26-27 | Ditutup; hasil clone/CI di penutupan |
| `2c051703d9f6c2cc1382897469bf47caa33ffd59` | AE26-26 | Ditutup; hasil clone/CI di penutupan |
| `0e1de42934b17f85e32a5c0fc3c39eb3b1108186` | AE26-25 | Ditutup; hasil clone/CI di penutupan |
| `37acee884c9c9d3602068c2275fdb3d1d5e4ae35` | RQ26-01; runtime lokal untuk AE26-24 | Ditutup; hasil clone/CI di penutupan |
| `88211d7e92b00e6c2798f4b1d5a29f063b6b8fd7` | AE26-28,29 | Ditutup; hasil clone/CI di penutupan |
| `026e1994b9b7c53ae481f8f8c7ddba614732d595` | AE26-20 dan koreksi dokumentasi/lisensi | Ditutup; hasil clone/CI di penutupan |
| `320c020564a374ec65da9cb51388c096f2f60548` | AE26-21; CI benchmark/build/drift/lint | Ditutup; hasil clone/CI di penutupan |
| `5842dc7dd4389a4d0d1ae8e3c387462a7f96cf95` | onboarding checkout; kurangi supply-chain pipe | Ditutup; hasil clone/CI di penutupan |
| `3948fe95` | AE26-27 lanjutan: model/observer envlama diganti | Ditutup;16native tests |
| `cba4e255` | AE26-30: tokenizer tidak mengunduh saat hook | Ditutup;4budget tests |

## Verifikasi final dan publikasi

Penutupan lokal 20 November 2026; full verification terbaru pada
`57b96a97` berhasil dalam 215.761 detik dengan Python venv checkout dan
lingkungan fixture yang sama dengan CI. Clone mandiri dibuat tanpa
alternates/hardlinks git.
Default setup pertama berhasil836.5detik dan benar-benar membangun
headroom dari source yang sama dengan versi final; tidak ada binary awal.
Dua setup berikut pada kode final berhasil154.232/151.262detik;19native
configuration hashes serta daftar backup tidak berubah pada pengulangan.

- Integration394tests: OK, tiga live/network opt-in yang sama dengan
  baseline tetap ditandai; tidak ada skip baru.
- ECC9422passed/0failed pada Node20container tanpa jaringan dan tanpa
  config alias global. Clone final tidak memount object/source repo lama.
- Catalog40/40, MCPstdio10/10,20entry-point smokes, browser2regressions,
  source syntax/JSON dan generatedcount drift semuanya lulus.
- Markdownlint seluruh owned scope: exit0 dengan aturan default; kini
  menjadi gate wajib CI, bukan advisory.
- Python/Rust dependency scans:0knownvulnerability; npm exit1 karena
  tujuh moderate tooling yang tetap terbuka. Warning Rustunmaintained
  tidak disembunyikan. ECC2 helper bertandaignore ternyata dijalankan
  oleh cross-process test; parent508tests dan childhelper1test lulus.
- Frozen50prompt benchmark:25/40top1,30/40top3 semua surface;6/6abstain;
  unavailableMCP0advertised/0ready; hookmax304tokens pada proxy exact.
  P95hook988.655ms adalah pengukuran host ini, bukan SLA umum.
- HOME asli tidak dipakai untuk setup.19managedconfig dibandingkan;
  satu profilHermes berubah selama host aktif, sehingga byte-identical
  HOME tidak diklaim dan data aktif pengguna tidak dipulihkan sepihak.

Ringkasan exit/timing/hash log sanitasi disimpan pada evidence. Scan akhir trackedtree498kandidat/231file danhistory766/285,
semua redaksi100%; PAT yang diberikan0match dalam file tracked.
Tidak ada kandidat baru yang dikonfirmasi sebagai credential produksi;
klasifikasi seluruh vendor/history tetap memiliki batas yang dicatat.
History tidak ditulis ulang. CI untuk source final `57b96a97` berhasil:

- [CI push](https://github.com/lokah1945/AgentEnhancements/actions/runs/44583836807):
  seluruh enam job berhasil.
- [CI PR](https://github.com/lokah1945/AgentEnhancements/actions/runs/44583850272):
  seluruh enam job berhasil.
- [Registry PR](https://github.com/lokah1945/AgentEnhancements/actions/runs/44583850092):
  regeneration dan drift gate berhasil.

[PR #9](https://github.com/lokah1945/AgentEnhancements/pull/9) memuat check
untuk report followup. Merge hanya dilakukan setelah check commit terbaru
berhasil, lalu CI master dan workflow registry terjadwal diverifikasi
kembali melalui workflow_dispatch. Hasil master dilaporkan pada respons
eksekusi akhir; link di atas membuktikan source yang sudah diperiksa.

## Iterasi publikasi CI

CI-F01(P2), `.github/workflows/ci.yml:111` dan
`.github/workflows/registry-regeneration.yml:57`: run push pertama
[CI44578871592](https://github.com/lokah1945/AgentEnhancements/actions/runs/44578871592)
dan registry44578874966 berhenti sebelum job/check-run dibuat. Perubahan
audit keliru memakai `runner.temp` pada job-levelenv. Sumber kebenaran
[context availability GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability)
menetapkan scope berbeda sebelum runnerdialokasikan.

Commit`8d2b1526` memakai github.workspace dan menyiapkan HOMEprivate
sesudah checkout. Regression konteks gagal pada enam subcase sebelum fix;
dua workflow tests kemudian lulus. Ini perbaikan iterasi audit, terpisah
dari30temuan baseline yang ditutup. Tidak ada job/test yang dinonaktifkan.

CI-F02(P2), integration job: run8d2b1526 menjalankan394tests tetapi
functional test serial-selection gagal karena `rg` belum dipasang. Delapan
media tests juga tidak dapat berjalan pada runner tanpa ffmpeg/tesseract.
Commit`6d3cc309` mendeklarasikan ripgrep/jq/ffmpeg/tesseract sebagai
prerequisite job, memakai existing functional regression sebagai bukti
sebelum/sesudah. Tidak ada test yang dihapus atau ditambahskip.

Tambahan bukti penutupan: dua public-network tests arxiv/news lulus dengan
opt-in eksplisit(5.33detik); hanya selector model riil tetap membutuhkan
model.json/key yang sesuai. Full suite clone terbaru394tests OK/3default
opt-in. Persyaratan checkout-local juga diuji terhadap global
CARGO_TARGET_DIR; normal preparation menormalkannya ke target milik
checkout dan menolak target/binarysymlink keluar.

RQ26-01 lanjutan `57b96a97`: scope test membuktikan bahwa inherited
CARGO_TARGET_DIR dapat menunjuk ke luar checkout. Runtime preparation kini
mengarahkan build ke target canonical dan memvalidasi symlink target/binary.
Empat scope tests lulus; kebijakan discovery dan source Rust tetap sama.
Kompresi standalone memakai reformating JSON/log yang mandiri; bentuk
input yang tidak didukung dapat diteruskan tanpa perubahan. Smoke CLI enam
mode tidak membuktikan rasio kompresi semua kode/Markdown.

Scan tambahan rentang `cba4e255..57b96a97` serta diff laporan/kontrak
menghasilkan nol kandidat baru, dengan redaksi 100%. Ini tidak menghapus
kandidat vendor/history yang sudah dicatat. Pengulangan uji tambahan yang
keliru memakai Python sistem (filelock 3.32.0) serta fixed host aliases
gagal 24 tests/1 error. Perintah verifikasi dikoreksi ke Python venv
checkout dan penghapusan aliases yang sama dengan langkah CI; hasil gagal
harness tetap disimpan pada evidence, bukan disembunyikan sebagai pass.
Pengulangan yang benar menghasilkan 394 tests OK dengan tiga opt-in
bawaan, exit 0, tanpa perubahan source atau pelonggaran assertion.
