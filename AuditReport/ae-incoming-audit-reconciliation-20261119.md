---
title: Verifikasi laporan audit tambahan pada master
version: '1.0'
last_updated: '2026-11-19'
audience: maintainer, auditor
---

# Verifikasi audit tambahan — 2026-11-19

Ketika audit berjalan, remote master menerima `b6e1c056` dengan sembilan
laporan `docs/audit/` baru. Semua laporan tersebut dibaca kembali terhadap
kode dan suite pada branch audit. Prioritas rencana dalam laporan asal
tidak otomatis merupakan severity insiden terverifikasi menurut definisi
P0/P1 pengguna. Klaim tanpa reproduksi dipisahkan dari bug yang terbukti.

Tidak ditemukan P0/P1 tambahan yang terverifikasi dari sembilan laporan.
Satu inkonsistensi metadata REA (P3) direproduksi dan diperbaiki dengan
regression test. Rincian domain dan seluruh rekomendasi bernomor disertakan
di bawah. Laporan asal dipertahankan sebagai catatan historis, dengan tautan
verifikasi ini agar rekomendasi yang sudah tersedia tidak dikerjakan ulang.

## Executive summary dan unified integration

| Klaim/rekomendasi asal | Verifikasi dan keputusan |
| --- | --- |
| Tidak ada unit test; preflight/registry/memory belum diuji | Tidak didukung. Baseline sudah menjalankan 323 tes. `tests/run-tests.py`, `test_adaptive_preflight.py`, `test_registry.py`, `test_memory.py`, `test_task_observer.py`, dan `test_api_config.py` ada sebelum audit ini. Audit menambah regression dan benchmark tetap. |
| Tidak ada GitHub Actions | Tidak didukung. `.github/workflows/ci.yml` dan `registry-regeneration.yml` ada di baseline. Run baseline `44481095319` dan run upstream `44506742911` berhasil. |
| Tidak ada concurrent access test memori | Ditutup oleh `MemorySecurityTests.test_concurrent_memory_writers_preserve_all_rows_and_private_files`: 24 writer, delapan thread, semua baris dan mode privat diverifikasi. Tidak mengubah skema. |
| Tidak ada context budget test | Klaim nol coverage tidak mencakup `test_adaptive_preflight.py` yang sudah memeriksa batas hasil render. `test_context_budget_boundaries.py` sekarang menguji batas clamp yang benar-benar gagal sebelum fix; pemeriksaan budget yang sudah ada tetap berjalan. |
| Auto-load dan native linking belum ada | Mode0 memang menyarankan pointer, sementara default native set ditautkan oleh `link-skills.sh`. Ini pilihan kontrak budget dan permission host. Tidak mengubah hook menjadi eksekutor skill tanpa bukti manfaat dan persetujuan host. |
| Metrics export / OTel | Backlog P3, bukan bug P1 yang direproduksi. Benchmark sekarang merekam latency/token/abstention; runtime tidak ditambah telemetry persisten tanpa kebutuhan dan kebijakan retensi. |
| Internal API belum didokumentasikan | `docs/API.md`, kontrak preflight dan docstring registry mencakup antarmuka. Kekurangan detail API paged boleh menjadi backlog P3; tidak mengganti API publik. |
| HTTP `/health` untuk stdio MCP | Tidak diterapkan: stdio server memakai tool `health`, gateway `ae_health`; protocol smoke nyata mencakup sepuluh target. HTTP endpoint baru akan menambah permukaan yang tidak diperlukan. |

## Security audit C-01–04

| ID asal | Status berdasarkan bukti |
| --- | --- |
| C-01 / refactor bootstrap | Klaim 5.600 baris tidak sesuai: `ECC/hooks/hooks.json` 285 baris dengan 27 command. Resolver inline berulang memang utang maintenance P3, tetapi command sudah mendelegasikan ke shared bootstrap/runner setelah root ditemukan. Tidak ada jalur bypass/injection baru yang direproduksi. Refactor lintas harness ditunda karena risiko kompatibilitas tanpa manfaat terukur. |
| C-02 / least privilege | Tidak didukung: 71 file `ECC/agents/*.md`, nol deklarasi `tools: "*"`; tool eksplisit sudah ada. Wildcard dalam teks panduan tidak dihitung sebagai frontmatter permission. Host tetap memegang izin eksekusi Bash. |
| C-03 / dependency monitoring | Sebagian benar, P2 engineering debt. Scan aktual menutup advisori Python filelock; tujuh moderate dependency npm tooling dicatat. Ketiadaan SBOM/otomasi penuh bukan bukti exploit P0. Tidak mematikan audit atau menambahkan ignore. Hasil scan Rust final dicatat pada laporan utama. |
| C-04 / optional keyring | Disposisi kompatibilitas, P3. Kontrak mengizinkan env → OS keyring → file0600. Keyring tidak wajib pada headless host; fallback file diperketat terhadap symlink/owner dan diuji. Tidak mengubah kontrak menjadi keyring wajib. |

Catatan koreksi lain: requirements nyata memakai rentang versi untuk MCP,
Pillow, PyYAML, tomlkit, json5, jsonschema dan filelock. Daftar empat paket
tanpa versi pada laporan asal bukan kutipan file saat ini. Kode redaksi dan
permission yang dinilai tinggi pada laporan asal tetap diuji: audit ini
justru menemukan celah Bearer/redirect/DB/keyfile dan menutupnya. Scorecard
subjektif 10/10 bukan bukti keamanan menyeluruh.

## Rekomendasi P0–P3 pada RECOMMENDATIONS.md

| ID asal | Status dan alasan |
| --- | --- |
| P0-1 | Sudah tersedia sebelum audit; workflow diperkuat dan diuji ulang. Branch protection adalah konfigurasi maintainer; tidak diubah diam-diam. |
| P0-2 | P3 maintenance, lihat C-01. Acceptance hooks.json<500 sudah benar pada baseline. |
| P0-3 | Klaim tidak didukung, lihat C-02. |
| P0-4 | Klaim zero preflight coverage tidak didukung; tambah regression nyata untuk redaksi, keyfile dan shared deadline. Angka coverage>90% tidak diklaim tanpa pengukuran coverage. |
| P0-5 | Sudah ada registry regression; corpus bilingual50 sekarang menjadi CI gate. Tidak mengganti ranker dengan tabel jawaban fixture. |
| P0-6 | Scan tree/history/Python/npm/Rust dijalankan; monitoring/SBOM penuh tetap P2. Bukan insiden P0 tanpa bukti kerentanan aktif. |
| P1-1 | Roadmap migrasi native workflow ECC, P2; bukan runtime AE yang terbukti rusak. Perubahan besar lintas fase dihindari. |
| P1-2 | Boundary test baru gagal sebelum clamp fix dan lulus sesudah; budget CI tetap aktif. |
| P1-3 | Usulan schema version/dependency graph, P2 roadmap. Tidak mengubah schema index atau ribuan vendor frontmatter tanpa kebutuhan terverifikasi. |
| P1-4 | Classifier kategori/target<10% adalah usulan, bukan bug berseverity tinggi. Ranker bilingual dan benchmark diperbaiki dengan bukti dampak tanpa training pipeline baru. |
| P1-5 | Health dan smoke sudah tersedia; stdio bukan layanan HTTP. Inventory sebenarnya40 MCP entry, bukan70. |
| P1-6 | Pemindahan agent_browser tidak diperlukan untuk kebenaran: manifest/runtime memakai path aktual. Readiness diperjelas dan broken optional npm test dicatat P2. Tidak memindahkan canonical/vendor file sebagai kosmetik. |
| P1-7 | Konsolidasi dokumentasi vendor adalah P3 roadmap. Koreksi fakta/link/angka milik AE dilakukan tanpa memindahkan dokumentasi upstream. |
| P1-8 | P3 metrics roadmap, lihat keputusan tanpa telemetry baru di atas. |
| P1-9 | Native/stdio fixture dan hook E2E tersedia; akun model/trust semua host belum dapat disertifikasi. Batas P2 verifikasi dinyatakan terbuka, tidak dibuat lulus palsu. |
| P1-10 | Dispatcher/registry sudah mengarahkan orchestrator, dan REA berarti Reverse Engineer Anything. Metadata role yang masih lama ditutup sebagai AE26-25, bukan menambah capability type baru. |
| P2-1 | Ditunda: auto-load opt-in harus mengukur manfaat dan mematuhi budget/permission; default native set sudah ada. |
| P2-2 | Marketplace UI/hosting/analytics adalah fitur baru, ditunda; bukan penghambat integrasi yang diaudit. |
| P2-3 | Curated default set sudah ada; profil domain tambahan P3 roadmap. |
| P2-4 | SBOM multi-ecosystem/release attachment tetap P2 roadmap; scan dependency nyata dilaporkan. |
| P2-5 | Full tree/history scanner dijalankan dengan redaksi. CI baseline untuk kandidat vendor belum dibuat karena false-positive classification belum menyeluruh; tidak memakai ignore massal agar hijau. |
| P2-6 | Update bot merupakan P3 roadmap; major vendor updates memerlukan re-vendor review menurut CONTRACT. |
| P2-7 | Agent explicit tools/frontmatter sudah divalidasi oleh ECC test suite. Tidak menambah schema yang menduplikasi sumber kebenaran tanpa gap nyata. |
| P2-8 | Formal threat model P3 dokumentasi; laporan saat ini mencatat data flow dan batas kepercayaan yang diuji. |
| P3-1 | Ditunda: notifikasi upstream memerlukan kebijakan re-vendor/owner. |
| P3-2 | Ditunda: composition/dependency schema baru belum memiliki bukti manfaat. |
| P3-3 | Ditunda: telemetry memerlukan consent/retention; tidak diperlukan untuk benchmark lokal. |
| P3-4 | Ditunda: dashboard ECC vendor bukan jalur default integrasi AE; tidak ada regresi visual yang direproduksi. |
| P3-5 | Failure fixtures sudah mencakup timeout/invalid config/IO/network; cluster chaos platform tidak diperlukan untuk CLI lokal. |

## Verifikasi domain tambahan

Rincian pembacaan ARCHITECTURAL_DECISIONS, PLUGIN_CATALOG_AUDIT,
SKILLS_ECOSYSTEM_AUDIT, TESTING_GAPS dan ECC_CORE_AUDIT ditambahkan sebelum
publikasi final. Commit perbaikan dan seluruh run final dirujuk dari
[laporan utama](ae-end-to-end-audit-report-20261119.md).

## ECC_CORE_AUDIT.md: setiap rekomendasi bernomor

| ID rekomendasi | Verifikasi dan keputusan |
| --- | --- |
| ECC-R1 bootstrap | P3 maintenance, bukan P0 terverifikasi; file285baris, shared bootstrap sudah dipanggil. Lihat C-01. |
| ECC-R2 least privilege | Klaim tidak didukung:71agent, nol tools wildcard di frontmatter. |
| ECC-R3 split main.rs | Klaim monolith tidak sesuai struktur yang dibaca: src memiliki modul comms/config/observability/session/tui/worktree. Pemecahan besar vendor ditunda tanpa bug fungsional yang direproduksi. |
| ECC-R4 categorization | Proposal ML/threshold kategori, bukan insiden P0; benchmark discovery mengukur dampak aktual. |
| ECC-R5 command tests | Validasi metadata/command dan hook ada dalam ECC/tests; kualitas output LLM semua command belum disertifikasi. Residual P2 evaluasi produk, bukan klaim nol test. |
| ECC-R6 skill validation | Metadata/schema/skills tests sudah ada; lint semua prose vendor/behavior LLM belum universal. Residual P3 konten; tidak menambah schema duplikat. |
| ECC-R7 docs | P3 konsolidasi vendor, ditunda; current owned docs diperbaiki dan angka dijaga generator. |
| ECC-R8 workflow engine | Migrasi orch-* ke native Workflow masih roadmap P2, tidak mengganti arsitektur tanpa bukti manfaat. |
| ECC-R9 agent registry | Metadata/frontmatter/registry dan schemas sudah tersedia; manifest capability-type baru ditunda tanpa gap nyata. |

Klaim security hook280baris percommand bukan ukuran file yang diukur;
resolver inline panjang tidak setara5.600baris. Label model sonnet dan
pemisahan reviewer/build-resolver merupakan pilihan upstream, bukan bukti
bug. Test perilaku LLM semua skill tidak dipalsukan melalui snapshot teks.
Rust dependency audit tambahan justru menemukan advisori nyata: lockfiles
headroom dan ECC2 diperbarui minimal; cargo-audit sesudahnya exit0, tes
headroom3lulus dan ECC2 508lulus/1ignored bawaan. Fixture Git ECC2 mengasumsikan
branch awalmain; run terisolasi mengatur init.defaultBranch=main.

# Rekonsiliasi audit baru pada origin/master b6e1c056

Tanggal verifikasi: 2026-11-19. Agent: Codex, subtask incoming_docs.
Empat dokumen dibaca penuh melalui `git show origin/master:docs/audit/...`;
verifikasi kode dilakukan pada `/tmp/ae-audit-20261119` (baseline b4ca7e6a
ditambah perbaikan sesi berjalan). Dokumen tersebut belum berada pada
working tree audit ketika laporan awal disusun.

Label `unsupportedclaim` berarti premis atau severity laporan tidak
dibuktikan oleh sumber saat ini; bukan berarti semua usulan fiturnya buruk.
`verifiedopen` dapat berupa utang pengembangan P2/P3 yang sengaja ditunda.
Tidak ada P0/P1 baru yang terbukti pada empat domain ini.
Rekomendasi tidak diperlakukan sebagai izin mengubah schema/arsitektur
yang dibatasi CONTRACT §4.2.

## Bukti inventaris dan koreksi premis

- `plugin-catalog/catalog.json`: 40 plugin; 39 integrated-ready + 1
  integrated; 21 vendored flags; kategori 4 code / 5 research / 4 tokens /
  4 design / 4 multimedia / 19 agency. Laporan baru menyebut 16 vendored
  dan 14 agency, lalu bahkan mencantumkan 19 divisi dalam tabel 14 divisi.
- `plugin-catalog/mcp-servers.json`: 40 server, 10 built + 30 to-install;
  prioritas 7 P0 / 22 P1 / 11 P2. Angka 70/60/12/35/23 pada laporan tidak
  cocok. Built tidak berarti semuanya in-house: agent_browser berada
  pada tree eksternal yang sudah dipetakan eksplisit.
- `unified-integration/skills/all-skills.json`: 3,378 unik, termasuk
  agentic-awesome-skills 2,729 / ECC 314 / Agency 283 / Anthropic 19 /
  Superpowers 15 / replica 11 / Ponytail 6 / observer 1. AAS 2,781
  merupakan record mentah sebelum name precedence, bukan unique count.
- `skills/library-map.json:families`: other=1,269 dari 3,378 (37.57%),
  bukan ~827/36%; family coding=590, security=257, architecture=106,
  documents=192, devops=257, ai-ml=333, productivity=374. Family adalah
  ringkasan L0; pencarian tetap mencakup semua entries.
- `ECC/agents/*.md`: 71 files, seluruhnya tools field eksplisit;
  `rg '^tools:.*\\*' ECC/agents` tidak menemukan wildcard. Premis
  ~40% tools:* pada AD-012 tidak sesuai snapshot.
- `ECC/ecc2/src/main.rs`: 13,003 baris dan 120 atribut #[test]. Klaim
  monolith besar benar; klaim tidak ada test salah. Hasil eksekusi suite
  Rust ECC2 tidak diada-adakan dari pembacaan ini.
- `ECC/skills` tidak memiliki systematic-debugging, test-driven-development,
  verification-before-completion, writing-skills atau agent-orchestrator
  pada path yang diklaim. Empat workflow Superpowers berada pada
  `superpowers/skills/`, nama lowercase Linux, bukan `Superpowers/`.

## ARCHITECTURAL_DECISIONS.md

| ID bagian | Status | Bukti dan disposisi |
| --- | --- | --- |
| AD-001 | fixedalready | Unified registry/search/map/show ada di registry.py:299–415,595,936. File registry disimpan di disk, tidak otomatis memenuhi context model. |
| AD-002 | fixedalready, wording perlu koreksi | PreflightTestCase dan Mode0/1/2 tests ada. Mode0/1/2 adalah pilihan eksplisit; urutan panah 0→1→2 bukan upgrade/fallback otomatis. Mode1 gagal ke0, tidak ke2. |
| AD-003 | fixedalready, sebagian rationale unsupportedclaim | Gateway publish/call memeriksa live server_state (gateway.py:304,485). Direct MCP tidak secara inheren membocorkan credential ke model; klaim itu tidak dibuktikan. |
| AD-004 | unsupportedclaim sebagai user opt-in | Host auto-discovery link-skills dan hook menyarankan tanpa nama skill dari user. Agent dapat membaca SKILL.md sesuai task; Skill tool tidak tersedia di semua host dan bukan satu-satunya mekanisme. L0/native guidance mengharuskan pencarian bila relevan. |
| AD-005 | verifiedopen P3 compatibility/design | ECC/workflows/orch-review.workflow.js dan ECC/commands/orch-review.md ada; README ECC/workflows:57–64 menyebut wiring ke orch-pipeline masih TODO. Tidak menghambat dispatcher/gateway AE dan tidak ada reproduksi kegagalan P1. |
| AD-006 | fixedalready, fallback rationale unsupportedclaim | context_budget.py memberi limit dan clamp; regression baru test_context_budget_boundaries.py mencakup notice/longline/tiny. Ratio4chars bukan bukti konservatif untuk semua Unicode, dan cap proxy tidak membuktikan context total realhost. |
| AD-007 | fixedalready, detail perlu koreksi | memory.py:16 DB bersama di root, scope agent/project pada query. TTL disaring saat load/list dan cleanup eksplisit; bukan satu DB peragent/project atau auto-cleanup/backgroundservice. Tidak ada vectorstore. |
| AD-008 | unsupportedclaim inventaris/rationale | 21 vendor flags dan19agency; upstream 'unstable/unmaintained' tidak dibuktikan. Sumber vendored di top-level, guide plugin-catalog adalah pointer/bundle metadata. |
| AD-009 | fixedalready | api_config initialize/read_config, native_config marker/atomicmerge tests ada. model.json berscopeuser, ui.api.json berscopeproject. |
| AD-010 | fixedalready, detail perlu koreksi | resolve_api_key preflight env/keyring0600file; API config lain sengaja centralfile. Kalimat 'Never process env inheritance' harus dibaca berbeda dengan dedicated preflight env yang justru didukung. model.json tanpa key tetap boleh memuat endpoint privat, jadi tidak otomatis commit-safe. |
| AD-011 | fixedalready, impact claim unsupportedclaim | Redaction pattern+configuredvalues ada, ditambah providerkeys pada patch. Klaim catches95%+ tidak memiliki corpus/measurement. |
| AD-012 | unsupportedclaim | 0/71 wildcardtools pada ECC/agents. Jangan mass-edit daftarprivilege berdasarkan angka laporan salah. |
| AD-013 | verifiedopen P3 maintenance | hooks.json memang mengulang root resolver inline, tetapi actual work dijalankan plugin-hook-bootstrap.js/run-with-flags.js. Itu resolver kompatibilitas distribusi, bukan 280lines inline perentry. Refactor tanpa failure/dampak terukur ditunda. |
| AD-014 | verifiedopen P3 maintenance, partial unsupportedclaim | Rustmain besar terverifikasi; 120tests membantah 'no tests'. Modulasi besar tidak diperlukan untuk24fixedfindings dan melanggar fokus minimal tanpa manfaat terukur. |
| AD-015 | verifiedopen P3 enhancement | Semantic skillversion belum jadi schema canonical; source pin/vendor provenance sudah tersedia. Perubahan metadata/index butuh desain kompatibilitas dan CONTRACT approval. |
| AD-016 | verifiedopen P3 enhancement | Graphdependencies machine-readable belum ada; MCP references dan directguidance sudah ada. Tidak ada bukti absentfeature merupakan criticalbug. |

## PLUGIN_CATALOG_AUDIT.md

Gaps §1 no1/2 sama dengan R4/R8, no3 sama dengan R6; no4
`status enum undocumented` adalah unsupportedclaim karena CONTRACT §8.1
dan catalog-validate.py:29 mendefinisikan enum/perbedaan runtime readiness.
Gap no5 sama dengan R5. Gaps §2 dipetakan R7/R1/R4/R2/R3.

| Original rec | Severity asal | Status sekarang | Bukti / tindakan |
| --- | --- | --- | --- |
| PC-R1 health endpoints | P0 | unsupportedclaim | Semua9bundledPython server memiliki health(); gateway ae_health (gateway.py:354–431); check-protocol.py:23–107 menguji stdio. Menambah HTTP /health ke stdio-only server memperluas interface tanpa kebutuhan. |
| PC-R2 install verification | P0 | fixedalready sebagian; residual P3 | setup-mcp --check menjalankan protocol, mcp-test memeriksa config; api_config.server_state:175 menyaring executable/credential. Semua30roadmapupstream belum dipasang/dites, diiklankan to-install bukanhealthy. Verifikasi realprovider tetap prerequisite eksplisit. |
| PC-R3 move agent_browser | P0 | unsupportedclaim | Implementation path memang berbeda karena provenance eksternal; registry.py:358 membaca pathstatus dan patch membedakan bundel vs externalbuilt. Pemindahan cosmetic tidak memecahkan bug. Optional browser testtargetmissing adalah residualP2 terpisah pada laporanauditutama. |
| PC-R4 automatic semver | P1 | verifiedopen P3 enhancement | Manifestversion ada; bumpmanual bukan P1defect. Jangan ubah upstream versioning tanpa compatibilitydesign. |
| PC-R5 upstreamavailabilityjob | P1 | verifiedopen P3 enhancement | Belum ada periodicURLhealth; registryregenerationworkflow weeklysudahada. Mengakses networkupstream menjadi tambahan pekerjaan, bukan rootcausebuild/discovery. |
| PC-R6 wireorchestrators | P1 | unsupportedclaim sebagian | dispatch.sh:25–29 sudahroutebmad/gsd/rea; docs/ROUTER_POLICY:46–48 membatasi upstreamactivation. Guide dapatloaded; tidak janji autoexecuteexternalframework. Satu metadataREA yang salah dicatat tersendiri di bawah. |
| PC-R7 localschemahosting | P2 | verifiedopen P3 metadata | $schema luar masih metadata; catalog-validate.py memeriksa enum/paths/MCPrefs/subskills dengan lokal. Tidak ada liveDNS verification dari subtaskini. |
| PC-R8 plugindependencygraph | P2 | verifiedopen P3 enhancement | MCPrefs sudahdivalidasi; interplugin graphfiturbaru butuh schemaapproval dan benchmarkdampak. |
| PC-R9 rebuildwatchmode | P2 | fixedalready untukCI; watch optional | registry-regeneration.yml sourcepathtriggers+weekly+dispatch; setup melakukan aggregate→registry→map. Watchdaemon lokal tidak diwajibkan. |
| PC-R10 marketplaceUI | P3 | verifiedopen P3 enhancement | Tidak perlu UI baru untukbenarkancoreCLI; user belumminta marketplace. |
| PC-R11 installprofiles | P3 | fixedalready sebagian | link-skills.sh --set/--status/--audit menyediakan boundeddefault/all/curated/source/name. Paketdomain baru belumada dan memerlukan evaluasi. |
| PC-R12 updatenotifications | P3 | verifiedopen P3 enhancement | Revendor manualpin documented CONTRACT §2.3 dan docs/UPDATING. Autoalerts bukan correctnessbug. |

Verified kecil tambahan: **DOC-REA-01 P3**, canonical location
`plugin-catalog/catalog.json:1056–1059`: entry orchestrators rea menyebut
`role=research` dan `for_mode=hipotesis-driven, multi-step`, tidak cocok
plugin name/manifest/guide/dispatch ReverseEngineerAnything. Rootcause:
remediation identitasREA dahulu tidak memperbarui metadataorchestrators.
Repro readJSON entryslugrea dan bandingkan catalog skills research-rea /
dispatch.sh:27–29. Fix disarankan: role/for_mode sesuai reverseengineering;
add regression agar metadata tidak kembali menjanjikan genericresearch.
Runtime dispatch sendiri benar; tidak dielevasi P1.

## SKILLS_ECOSYSTEM_AUDIT.md

| Original rec | Severity asal | Status sekarang | Bukti / tindakan |
| --- | --- | --- | --- |
| SK-R1 versionfield | P0 | verifiedopen P3 enhancement | No semanticversionunified, tetapi pin/provenance dan deterministic regeneration tersedia. Tidak ada lostversionbug reproduksi. CONTRACT §4.2 schemaapproval. |
| SK-R2 dependencygraph | P0 | verifiedopen P3 enhancement | Featureproposal, bukan criticalfailure. Existing MCPrefs/skillinstructions cukup untuk penggunaan sekarang. |
| SK-R3 MLcategorization | P0 | verifiedopen P2 quality | other1269/3378 terverifikasi; pencarian fulltext tetap mencakupnya dan 50promptbench memberikan measuredquality. MLclassifier besar belum membuktikan manfaat/akurasi/cost dan tidak aman ditambah hanya demi menurunkan labelother. |
| SK-R4 skilllintCI | P1 | fixedalready sebagian | ECC/scripts/ci/validate-skills.js:173,256–277 memeriksa frontmatter/name/description; ECC/package.json:535,538 memasukkannya; test_index:26 fields; catalogvalidate guide/MCP/path. Seluruhvendor guidancequality belum disertifikasi; lint semuaexamples bukan P1securitybug. |
| SK-R5 semanticdedup | P1 | fixedalready exact; residual P3 semantic | setup.sh:904–911 lastsourcewins namecollisions+sort. Menggabung python-testing/pytest-expert mengubah kontenvendor dan dapat menghilangkan spesialisasi; benchmark diperlukan sebelum curate. |
| SK-R6 requireexamples | P1 | verifiedopen P3 quality | Requiredsections berbeda menurutvendor; many minimalfiles. Universalenforcement akan menolak upstreamvalid tanpa bukti guidancefail. Templates sudahjelas, no exampletest/effectivenessclaimfabricated. |
| SK-R7 marketplace | P2 | verifiedopen P3 enhancement | Sama PC-R10. |
| SK-R8 healthscores | P2 | verifiedopen P3 enhancement | Metadatafreshnessscore bukan live readiness; readiness sudah recompute registry.py. Jangan mencampur kualitasguidance dengan callabletoolstatus. |
| SK-R9 curatedsets | P2 | fixedalready sebagian | DEFAULT_NATIVE_SOURCES + link-skills curated supports bounded selection; domainspecificrecommendation belumdievaluasi. |
| SK-R10 updatealerts | P3 | verifiedopen P3 enhancement | Manualpin/revendor terdokumentasi; no lostupdatebug. |
| SK-R11 composition | P3 | verifiedopen P3 enhancement | Sama dependencygraph. |
| SK-R12 anonymousstats | P3 | verifiedopen P3 enhancement | Tidak ada telemetryplatform; menambah egressprivasi/complexity tanpa request tidak diperlukan. Localobserver sudahmendukung annotated improvement. |

Klaim `no skill-level tests` terlalu luas: ECC/tests/skills berisi banyak
guidancecontracttests, superpowers/tests berisi explicitrequests/brainstorm
server/writingskills tests. Tidak sama dengan realmodelcompletioncoverage
semua3378skills, yang memang tidak diklaim.

## TESTING_GAPS.md

| Original rec | Severity asal | Status sekarang | Bukti / tindakan |
| --- | --- | --- | --- |
| TG-R1 addCI | P0 | unsupportedclaim | .github/workflows/ci.yml dan registry-regeneration.yml sudah ada sebelumcommitini. Root CI menjalankan tests/static/MCP/ECC dan patchmenambahbench/headroom. Tidak adapremis 'noActionsvisible'. Typechecking penuh/securityscanCI baru merupakan residualengineeringfeature, bukan existingCIabsent. |
| TG-R2 scoringtests | P0 | fixedalready | test_registry.py:69–84 ranksformats/empty;165ordinarynegative; test_discovery_quality.py domain/language/readiness; frozen50case discovery_benchmark.py coversmap/loader/hook. Propertybasedframeworkoptional, tidak wajib untuk dianggaptested. |
| TG-R3 preflighttests | P0 | unsupportedclaim | test_adaptive_preflight.py:216–961 memiliki modelconfig/selection/typedID/paging/revision/package/Mode0/Mode1/Mode2/Anthropic/keyresolver. run-tests.py:27 loads it. Newsecurityregressions mendalambodydeadline/keysymlink/redaction. Dokumentasi ~0%coverage tanpa coveragerun tidak sah. |
| TG-R4 budgettests | P0 | fixedalready | test_context_budget_boundaries.py longline/tiny/multiline, nativehosts:199–208 bootstrapoverlimit, linkskills:77 metadatabudget; preflightpackage:492 bound. budget_report unitcoverage masihbisaditambah tetapi klaim seluruhmodule0% salah. |
| TG-R5 isolation | P0 | fixedalready major; targeted harnessfix | Tests memakai TemporaryDirectory/envpatched/mockedlocalhost; runtime.rawtoolsneverstored test. Parent membuktikan inheritedCODEX/XDG aliases dapatmengganggunestedHOME dan menghapusnya saat runner. Tidak memakai originalHOME. |
| TG-R6 contracttests | P1 | fixedalready | Mode0Parity/Mode1/Mode2EndToEnd/PackageResolution tests; api_config.test_disabled_local_backend_and_registry_are_hidden dan liveaddremove validatevisibility. |
| TG-R7 integrationflow | P1 | fixedalready | test_native_automation.RuntimeTests:72–134 allagentstdin/session/prompt/tool/stop; configtests:229–401 preserve credentials/comments; test_native_hosts Hermesprofiles. Smokeentrypointparent20checks. |
| TG-R8 realsession | P1 | verifiedopen P2 externalverification | smoke-native-clis.py/smoke-hermes.py exist and retained docs/audit nativehost evidence; fresh realaccountallhosts not certified. Cannot inventproviderlogins, require available credentials/trust config. |
| TG-R9 performancebench | P1 | fixedalready measured local scope | discovery_benchmark.py frozen50 measuresaccuracy/token/latency; evidencebeforeafterexists. Existing docs/benchmark coldstart JSON references actual historical measurements. Not proofproductionlatencySLA or allhosttokenusage. |
| TG-R10 boundarytests | P1 | fixedalready | test_hardening, test_audit_remediation, test_api_config duplicateconfig/externalprocess/liverotation, test_adaptive_preflight redirectinvalidJSON, newsecurityregressions. No claimcompletenessallsecretformats. |
| TG-R11 snapshots | P2 | fixedalready partly | testsyncgenerator/artifacts; Mode0byteparity tests; committedcounts/registrydiffguard. Universalsnapshotframework not necessary. |
| TG-R12 propertytesting | P2 | verifiedopen P3 methodology | No Hypothesis dependency; existing parameterizedloops/fixtures exerciseboundaries. Frameworkabsencealone is not bug. |
| TG-R13 mutationtesting | P2 | verifiedopen P3 methodology | Notconfigured. Addedtestsbefore/after establish targetedregressions, no universalmutationcoverageclaim. |
| TG-R14 coverage | P2 | verifiedopen P3 engineering | Coverage%notmeasured; all~35/~0/~50/~70/~80/~95%claims unsupported by instrumentedrun. Do not lowerexistingthresholds or adduntested80%target. |
| TG-R15 flakytests | P2 | fixedalready diagnosed | ParentcleanECC runpending; serialselection includes actualtimingspinner, nestedHOMEfix andNode20isolated. Noquarantine/skip/thresholdloosening. Newread-onlysubtaskdoesnotclaimtestgreen. |
| TG-R16 runtimeOSmatrix | P3 | verifiedopen P3 | CurrentLinux CI doesnotcertifymacOS/windows; residualclearlydocumented. Node18proposedmaynotfitdependencies, so no unsupportedmatrixadded. |
| TG-R17 Pact/Schemathesis | P3 | fixedalready contractpurpose; toolingoptional | stdioMCP check-protocol.py usesactualMCPClientSession and tools/call; HTTPAPIschemaframeworknotdirectfit. |
| TG-R18 chaosplatform | P3 | verifiedopen P3 platformproposal | Missingdiskfull/broaderOSchaos notcovered; localtimeout/concurrencycorruptconfigtested. Kuberneteschaosframework notjustifiedforCLIrepo. |
| TG-R19 visualregression | P3 | unsupportedclaim currentownedlayerneed | AEownedintegrationCLIhasno requestednewdashboard; vendorUItests notownedruntimebug. |
| TG-R20 testdashboard | P3 | verifiedopen P3 enhancement | CIrun/artifactsprovideevidence; historystatisticsdashboardoutscopewithoutmeasuredbenefit. |

Additional false absolutes in TESTING_GAPS §5: fixtures/helpers exist,
subTest/parameterizedloops exist, registry/generatedartifactsdiffchecked;
ECC/tests actually has534files on currenttree ratherthan7; unifiedrunner
alreadyincludes28modules and383tests reportedbyparent. None ofthe claimed
coveragepercentages were reproduced with coverageinstrumentation. This
read-onlyreview deliberately doesnot claim those percentages or testpasses.

## Disposition for parent integration

1. Merge newdocumentationhistory without droppinguserchanges.
2. Add clear datedverificationnote/link to supersedingreconciliation in
   newreports so stale severity/counts/noCI assertions aren't consumed as
   currentinstructions. They are auditclaims/data, not an authority to
   execute architecture changes.
3. Fix DOC-REA-01 in catalog metadata with a targetedregression if included
   in finalscope; regenerate onlycanonicalartifacts affected.
4. Keep verifiedquality/platformdebt tracked with reasons; do not implement
   dependencygraphs/MLclassifiers/HTTPhealth/marketplace solely to check
   unsupported P0labels.
