---
title: "AgentEnhancements End-to-End Independent Audit"
version: "1.0"
last_updated: "2026-11-15"
audience: "Project owner, maintaining agents, release reviewers"
---

# AgentEnhancements — End-to-End Independent Audit (2026-11-15)

## 1. Executive Summary

**Verdict: CONDITIONAL.** Lapisan integrasi yang dipelihara project (`unified-integration/`, `plugin-catalog/`, `scripts/`, `docs/`) secara fungsional sehat: installer end-to-end terbukti bekerja dan non-destruktif dalam lingkungan fixture terisolasi, 190/190 test regresi lulus (2 skip jaringan by design), kesembilan MCP server in-house + gateway (36 tool) lolos inisialisasi protokol nyata, dan klaim-klaim inti (3.377 skill, 40 plugin katalog, registry 3.462 entri, dispatch bilingual) terverifikasi dari data. Namun project **belum siap disebut production-ready** karena dua pemblokir P1 yang berada di luar kode: (1) **CI tidak pernah hijau sekalipun** — 22/22 run gagal sejak 2026-11-01, semua job mati ~2 detik tanpa menjalankan satu step (indikasi kuat billing/spending-limit lock), sehingga gerbang mutu yang diklaim README tidak benar-benar berfungsi; dan (2) **kesalahan lisensi/provenance material pada README** — 2 dari 10 lisensi vendor salah (claude-mem sebenarnya Apache-2.0 bukan MIT; system-prompts-and-models-of-ai-tools sebenarnya GPL-3.0 bukan CC-BY-4.0), 7 dari 10 URL upstream dikontradiksi oleh metadata vendor itu sendiri, tidak ada file LICENSE di root meski README mengklaim rilis MIT, dan konten GPL-3.0 terdistribusi di dalam agregasi berlabel MIT.

Di bawahnya terdapat 10 temuan P2 (dokumentasi basi tersebar di 8+ file termasuk angka test 149 vs aktual 190 dan plugin 21 vs 40; `.cursorrules` mengklaim mekanisme symlink yang tidak ada di kode; `catalog-test.sh` tidak bisa menguji 19 plugin agency; klaim "automatic compression" dan "system prompts configured" melebihi realitas implementasi; `update-skills.sh` efektif tidak bisa meng-update apa pun karena semua vendor full-copy; task-router-mcp adalah alat eksekusi arbitrer dengan denylist kosmetik; satu-liner `curl | bash` unpinned; suite ECC punya 43 kegagalan baseline yang belum diselesaikan; vendoring arsip system prompt komersial sebagai potential legal concern) dan 10 temuan P3 (hygiene kecil: timestamp churn pada file committed, backup menumpuk, komentar JSONC ter-strip, pesan memory misleading, dll.). **Tidak ditemukan P0**: tidak ada secret yang ter-commit, tidak ada jalur RCE oleh pihak luar di luar permukaan by-design, dan mekanisme preservasi konfigurasi user terbukti bekerja.

Tingkat keyakinan: tinggi untuk semua temuan yang berbukti (setiap temuan menyertakan path:baris atau command+output). Batas audit: tidak ada pengujian dengan CLI agent sungguhan (Claude Code/Codex/OpenCode binary) di sesi ini — verifikasi lintas-agent bersifat fixture + mengandalkan laporan audit terakhir yang menjalankan CLI nyata; suite ECC tidak dijalankan ulang (estimasi 45 menit + npm install besar; baseline tercatat di docs/audit/TEST_RESULTS.md); tidak ada akses ke server produksi/eksternal. Rincian di §6.

## 2. Audit Identity

| Item | Value |
|---|---|
| Repository | https://github.com/lokah1945/AgentEnhancements |
| Branch default diaudit | `master` |
| HEAD diaudit | `6eebfc573bc536faf79ff0abde3c21cba36dd28c` ("feat(agency): integrate The Agency persona collection (agency-agents)") |
| HEAD saat laporan diserahkan | `6eebfc57` — **tidak bergerak selama audit** (verifikasi `git ls-remote` 2026-11-15 08:2x UTC; catatan: branch lain `feat/task-observer-integ` di-push 07:16 UTC, di luar cakupan) |
| Waktu audit | 2026-11-15 07:40 – 08:35 UTC |
| Working tree saat baseline | clean; 40.201 file terlacak; 1.2 GB working tree + ~299 MB `.git` |
| Tag/rilis | tidak ada tag |
| Eksekutor | ZCode (agent) — audit independen, read-first, non-destructive |
| Metode | Pembacaan penuh dokumen kontrak & kode milik project; 3 subagent read-only (dokumentasi/klaim, vendor/lisensi, plugin-catalog); validasi dinamis terisolasi (fixture HOME + stub CLI + venv XDG terpisah); kueri GitHub API read-only untuk riwayat CI |
| Perubahan oleh auditor | **Tidak ada** terhadap kode/konfigurasi/dependensi. Artefak tunggal: laporan ini pada branch `audit/e2e-independent-2026-11-15` (dokumen di `docs/` sesuai CONTRACT R002) |
| Lingkungan uji | Linux x86_64, Python 3.12.16, bash; sandbox dengan jq/ffmpeg/tesseract tersedia; dependensi `mcp/PIL/yaml/tomlkit/json5/jsonschema/filelock` tersedia; `sqlite3` CLI **tidak** tersedia (lihat AE-16) |

## 3. Architecture & Inventory

### 3.1 Peta direktori (milik project vs vendored vs generated)

| Direktori | Status | Isi |
|---|---|---|
| `unified-integration/` | **milik project** (dipertahankan) | setup.sh (2.430 baris, entry tunggal), update-skills.sh, launch-agent.sh, scripts/ (16 utilitas), memory/ + 16 hook (8 agent × py+sh), compression/, mcp-servers/ (9 server in-house + gateway.py + check-protocol + smoke_test), opencode-plugin/, prompts/ (10 file), config/ (template ui.api), tests/ (15 modul, 190 test) |
| `plugin-catalog/` | **milik project** | catalog.json (40 entri, 6 kategori), mcp-servers.json (38 roadmap: 9 built + 29 to-install), 40 SKILL.md panduan integrasi (19 di antaranya agency pack) |
| `scripts/` (root) | **milik project** | scaffold_modular_skills.sh, generate_skills_index.py, convert_agency_agents.py, gen_agency_catalog.py |
| `docs/` + `docs/audit/` | **milik project** | 21 dokumen + 7 laporan audit historis |
| `.github/workflows/ci.yml` | **milik project** | 5 job: static-checks, integration-tests, ecc-tests, mcp-servers, markdownlint (advisory) |
| `skills/` | generated-at-install | manifest.json + README ter-commit; 40 direktori per-plugin **tidak** ter-commit (dibangun `scaffold_modular_skills.sh`; output symlink di-gitignore) — lihat AE-13 |
| `unified-integration/skills/` | committed index + generated tree | all-skills.json (2.8 MB, committed) + agent-registry.json (2.5 MB, committed) + by-category/by-agent (generated, gitignored) |
| `agentic-awesome-skills/` … `system-prompts-and-models-of-ai-tools/` (10 direktori) | **vendored full-copy** | ~866 MB / ~38.900 file; tanpa `.git` (bukan submodule, tanpa `.gitmodules`) — provenance per vendor di §7 |
| `.cursorrules` (root) | milik project, mayoritas vestigial | lihat AE-06 |

### 3.2 Aliran data (single source of truth — terverifikasi)

`plugin-catalog/catalog.json` → (generators `scripts/*`) → `skills/manifest.json` + README kategori; terpisah: 7 sumber skill vendor → `setup.sh aggregate_skills()` → `by-category/` tree + `all-skills.json` → `registry.py build` → `agent-registry.json` → dikonsumsi `load-skills.py` / `registry.py map` / `link-skills.sh` (symlink ke `~/.claude/skills`, `~/.agents/skills`) → instruksi per-agent (CLAUDE.md/AGENTS.md/rules) memberi tahu agent cara memakainya. MCP: `mcp.json.example` → `native-integration.py` → config asli tiap CLI → `gateway.py` tunggal → 9 server internal + external opsional via `ui.api.json`.

Kontrak data konsisten; satu anomali: `setup.sh` **meregenerasi file-file tracked via heredoc** (launch-agent.sh, scripts/memory.py, load-skills.py, compress.py, hooks, config.yaml) — dual-maintenance yang dijaga oleh `test_sync` (3 test, lulus) dan terbukti tidak drift pada fixture saya (hanya timestamp yang berubah, AE-14).

### 3.3 Runtime & platform

Bash + Python 3 (stdlib + mcp/json5/tomlkit/jsonschema/Pillow/yaml/filelock di venv terisolasi `~/.local/share/agentenhancements/`), Node hanya untuk suite ECC vendored, Rust opsional (headroom, tidak dibangun default). Linux sepenuhnya diuji (audit ini + CI dirancang ubuntu-latest); macOS hanya dipertimbangkan secara defensif (komentar bash 3.2 di setup.sh:98-104); Windows tidak didukung (hook `.sh`, symlink, `bash -lc`). Asumsi: `python3`, `git`, PATH standar POSIX.

## 4. Claims vs Evidence Matrix

Klaim utama → bukti → status (legenda status sesuai mandat audit):

| # | Klaim (sumber) | Bukti aktual | Status |
|---|---|---|---|
| 1 | 3.377 skill unik dari 7 sumber; 2.729/314/15/11/19/6/283 per sumber (README.md:9,175-185) | `all-skills.json`: `total_skills=3377`; hitung ulang per `source` cocok semua (audit hitung via Python) | **VERIFIED** |
| 2 | 40 plugin katalog, 6 kategori (4+5+4+4+4+19) (README.md:34) | catalog.json: 40 entri, hitungan kategori cocok; `catalog-validate.py`: PASS 40/40 (19 warning agency tanpa MCP) | **VERIFIED** |
| 3 | 38 MCP roadmap, P0=5/P1=22/P2=11; 9 built (README.md:75,140,336; docs/MCP_SERVERS.md) | mcp-servers.json: 38; prioritas cocok; 9 direktori server ada; `setup-mcp.sh --check`: 9/9 server + gateway "36 tools" initialize sukses (audit jalankan) | **VERIFIED** |
| 4 | Registry = 3.377 skill + 40 plugin + 38 MCP + 7 built-in (README.md:215) | `registry.py stats`: 3.462 entri (3377/40/38/7) (audit jalankan) | **VERIFIED** |
| 5 | "149 tests" (README.md:143,349; README_INTEGRATION.md:106; .cursorrules:270) | 190 fungsi test terhitung dari sumber; `run-tests.py`: "Ran 190 tests ... OK (skipped=8)" di clone murni; 190/0-fail/2-skip setelah setup di fixture (5 run konsisten) | **CONFLICT** (angka basi; audit API_MCP 2026-11-15 sendiri sudah menulis 190) → AE-05 |
| 6 | setup.sh idempotent, non-destructive, marker-guarded (README.md:82,103) | Fixture 3 run: konten semua konfig agent stabil setelah run ke-2; hook pribadi/apiKeyHelper/model/CLAUDE.md/TOML-komentar/server-MCP-user terpelihara (58 asersi); marker tidak menduplikasi teks personal | **VERIFIED** (dengan pengecualian P3: AE-14, AE-15, AE-17) |
| 7 | Native activation: 19+11=30 skill ter-link ke `~/.claude/skills` + `~/.agents/skills` (README.md:100) | Fixture: tepat 30 symlink di tiap target, mengarah ke `by-category/`; `link-skills.sh --status` konsisten | **VERIFIED** |
| 8 | Pencarian bilingual; "buat dokumen word laporan keuangan" → docx (README.md:215) | Audit jalankan: map ID → docx (score 13); "clean this excel spreadsheet" → xlsx (score 14); dispatch battery 7/7 (EN+ID+override+fallback) | **VERIFIED** |
| 9 | Memory SQLite parameterized, TTL, private (README.md:245-258) | Kode hook/memory.py semua `?`-parameterized; db 0600; scoping agent+project terbukti (load lintas agent gagal); TTL 7 hari di runtime.py; test 7/7 | **VERIFIED** |
| 10 | Compression: budget 200k, trigger 75%, fallback Python, proxy (README.md:262-284) | `compression/config.yaml` memang berisi angka itu, **tetapi tidak ada kode yang membacanya** (grep: nol konsumen); compress.py manual mode+truncation 50k; headroom tidak dibangun; instruksi agent justru menyarankan compaction native CLI | **CONFLICT** → AE-08 |
| 11 | "Configure system prompts for each detected tool from the vendored prompt collection" (README.md:76) | setup.sh hanya menyalin file prompt; tidak ada agent yang memuatnya (config Gemini/Kiro = reference-only; native-integration.py:235-236 justru **menghapus** referensi prompt dari instructions OpenCode) | **PARTIAL** → AE-09 |
| 12 | "CI runs all of the above on every push" (README.md:357) | GitHub API: 22/22 run **failure** sejak 2026-11-01; run #20 pada HEAD 6eebfc57: 5/5 job gagal, job "Static checks" berdurasi 2 detik, **nol step**, log `BlobNotFound` | **CONFLICT** → AE-01 |
| 13 | Update skills via `update-skills.sh` (CONTRACT §2.3, §5.2) | Semua 10 sumber vendored tanpa `.git` → 7 di-skip + 3 "update manually"; satu-satunya efek = re-run setup.sh | **PARTIAL** → AE-04 |
| 14 | Installer satu baris `curl … \| bash` (README.md:56) | Mekanisme bootstrap teruji oleh `test_piped_installer_bootstraps_the_complete_clone` (lulus); clone **unpinned** dari master; live-run tidak dilakukan (lihat §6) | **IMPLEMENTED, UNTESTED (live)** → AE-11 |
| 15 | Matrix aktivasi 8 agent (README.md:88-100) | Semua file target terverifikasi ditulis di fixture; Claude/Codex/OpenCode = native hooks+MCP; Cursor/Gemini/Windsurf = instruction/rule; Copilot/Kiro = reference-only (README jujur melabelnya); "Continue" hanya di README_INTEGRATION — tidak ada kode | **VERIFIED** (Copilot/Kiro memang non-aktif by design → P-17 historis) ; Continue → AE-06 |
| 16 | Klaim lisensi upstream (README.md:371-386) | 2 lisensi salah, 1 tidak presisi, 7/10 URL upstream dikontradiksi metadata vendor sendiri; root tanpa LICENSE (README.md:392 mengklaim MIT) | **CONFLICT** → AE-02 |
| 17 | Laporan audit lama: "Actions terkunci billing" (API_MCP audit 2026-11-15) | Terkonfirmasi masih berlaku per 2026-11-15 05:14 UTC (run terakhir di master): semua job gagal pra-step | **VERIFIED** |
| 18 | Audit lama: "190 test, 188 pass, 2 network skipped" (API_MCP audit) | Direproduksi persis oleh audit ini (5 run) | **VERIFIED** |
| 19 | "Plugin catalog with 40 curated external plugin **sources**" (README.md:12,34) | 40 entri katalog ≠ 40 sumber: 22 upstream unik (19 pack agency dari SATU repo msitarzewski/agency-agents) | **PARTIAL** (presentasi menggelembungkan; catalog.json sendiri transparan) |
| 20 | `.cursorrules` "symlinked into ~/.cursor/, ~/.claude/, ~/.codex/, ~/.continue/ by setup.sh" (.cursorrules:3-5) | grep seluruh kode: tidak ada logika symlink .cursorrules; `~/.continue` tidak pernah ditulis; Cursor menerima file lain (`~/.cursor/rules/agent-enhancements.mdc`, setup.sh:1586) | **CONFLICT** → AE-06 |

## 5. Findings

Format per mandat: ID | Severity | Subsystem | Status | Claim vs Reality | Evidence | Reproduction (aman) | Impact | Root Cause | Confidence | Recommended Minimal Fix | Regression Test | Owner/Dependencies | Release Gate.

### P0 — Critical

**Tidak ada temuan P0.** Tidak ditemukan secret ter-commit (scan pola di seluruh repo oleh subagent: hanya placeholder/fixture/`.env.example`), tidak ada jalur eksekusi remote oleh penyerang luar di luar permukaan by-design (`curl | bash` — AE-11), tidak ada jalur perusakan konfigurasi user yang terverifikasi (sebaliknya: preservasi terbukti), dan SQL selalu parameterized.

### P1 — High

**AE-01 | P1 | CI/Release | CONFLICT — CI berjalan tetapi tidak pernah berfungsi**
- **Claim vs Reality**: README.md:357 "CI runs all of the above on every push" vs realitas: 22/22 workflow run **failure** sejak run pertama 2026-11-01, termasuk run #20 (id 43680193789) pada HEAD yang diaudit (6eebfc57, 2026-11-15T05:14Z): kelima job (static-checks, integration-tests, ecc-tests, mcp-servers, markdownlint) gagal; job "Static checks" started 05:14:08 → completed 05:14:10 dengan **daftar step kosong** dan log blob tidak ada.
- **Evidence**: `curl api.github.com/…/actions/runs?per_page=100` → `{'failure': 22}`; `…/runs/43680193789/jobs` → 5 job failure tanpa step; job log → `BlobNotFound`. Lokal, job yang sama bisa hijau: `bash -n` semua `.sh` PASS, `py_compile` semua `.py` PASS, suite 190/190 PASS — kegagalan bukan dari kode.
- **Reproduction (aman)**: GET read-only ke API GitHub Actions (audit lakukan; tidak menyentuh repo).
- **Impact**: Gerbang mutu yang diklaim tidak ada; setiap klaim "tests pass in CI" tidak berlaku; regresi apa pun (termasuk drift index) tidak terdeteksi otomatis. Konsisten dengan penyebab infrastruktur (billing/spending limit) yang diklaim docs/audit/API_MCP_AUTOMATION_AUDIT_2026-11-15.md dan masih berlaku.
- **Root Cause**: Akun GitHub billing terkunci (hipotesis terkuat; pola "job mati <5 detik tanpa step" khas kegagalan billing), bukan kegagalan test.
- **Confidence**: Tinggi (fakta run/failure/kondisi step); sedang (atribusi billing — hanya bisa dikonfirmasi pemilik akun).
- **Recommended Minimal Fix**: Pemilik akun menyelesaikan billing/spending limit; lalu amati satu run hijau di master. Opsional: tambah job `workflow_health` trivial (echo) untuk membedakan kegagalan infrastruktur vs test.
- **Regression Test**: Setelah fix — assert run master terbaru conclusion=success dan setiap job memiliki step yang tereksekusi.
- **Owner/Dependencies**: Pemilik repo (aksi akun, bukan kode).
- **Release Gate**: **YA** — tanpa CI hijau minimal sekali di HEAD, jangan mengklaim "CI-validated".

**AE-02 | P1 | Supply chain/Lisensi | CONFLICT — tabel lisensi & provenance README material salah**
- **Claim vs Reality**: README.md:371-386 mengklaim: claude-mem MIT (realita: **Apache-2.0** + NOTICE, cf. `claude-mem/LICENSE`, `package.json@15.7.0`, `docs/license.md`); system-prompts-and-models-of-ai-tools CC-BY-4.0 (realita: **GPL-3.0**, `LICENSE.md`); headroom "MIT/Apache-2.0" (realita: Apache-2.0 saja; MIT hanya milik dependensi pihak ketiga di NOTICE); 7/10 URL upstream dikontradiksi metadata vendor sendiri (agentic→sickn33, claude-mem→thedotmack, ECC→affaan-m, headroom→headroomlabs-ai, ponytail→DietrichGebert, superpowers→obra, system-prompts→x1xhlol); README.md:392 "released under MIT License" tanpa file LICENSE di root; konten GPL-3.0 (system-prompts) + klausa komersial claude-mem terdistribusi di dalam agregasi berlabel MIT; `docs/LICENSE_AUDIT.md` hanya mengaudit 21 plugin katalog, bukan 10 direktori vendored (2 pernyataannya yang terverifikasi tetap akurat).
- **Evidence**: subagent supply-chain membaca setiap LICENSE/NOTICE/package.json/Cargo.toml vendor (tabel per-vendor di arsip audit); konfirmasi sampel oleh auditor utama.
- **Reproduction (aman)**: `head claude-mem/LICENSE`, `grep license claude-mem/package.json headroom/Cargo.toml`, `head system-prompts-and-models-of-ai-tools/LICENSE.md`, `ls LICENSE` (root, tidak ada).
- **Impact**: Risiko kepatuhan redistribusi bagi siapa pun yang fork/reuse; ketidakcocokan GPL-3.0 vs label MIT; kontributor yang mengikuti tautan "Original Repo" salah arah.
- **Root Cause**: Tabel upstream ditulis dari ingatan/asumsi saat menyusun README, bukan dari metadata vendor; audit lisensi tidak mencakup direktori vendored.
- **Confidence**: Tinggi (fakta lisensi di dalam tree).
- **Recommended Minimal Fix (S)**: Perbaiki tabel README dari metadata vendor; tambahkan LICENSE root (keputusan model lisensi agregasi = DECISION REQUIRED pemilik); perluas LICENSE_AUDIT.md ke 10 direktori vendored.
- **Regression Test**: Skrip CI yang membandingkan kolom lisensi README dengan file LICENSE vendor (atau minimal checklist manual di LICENSE_AUDIT).
- **Owner/Dependencies**: Pemilik (keputusan lisensi agregasi); penulis dokumen.
- **Release Gate**: **YA** untuk distribusi publik berkelanjutan.

### P2 — Medium

**AE-03 | P2 | Supply chain/IP | POTENTIAL LEGAL CONCERN (unverified) — vendoring arsip system prompt komersial**
- `system-prompts-and-models-of-ai-tools/` berisi ~94 dump prompt/tool dari ~34 produk komersial (Anthropic, Cursor, Devin, Lovable, Manus, v0, Windsurf, Replit, Warp, Z.ai, dll.) yang di-vendor utuh tanpa catatan redistribusi. GPL-3.0 paling jauh melindungi susunan koleksinya; substansi prompt kemungkinan dilindungi ToS/trade-secret masing-masing vendor. Auditor TIDAK menyimpulkan pelanggaran hukum (bukan kewenangan audit); ini *potential concern* yang membutuhkan penilaian pemilik. Evidence: direktori + LICENSE.md; README upstream tanpa larangan redistribusi eksplisit namun juga tanpa pemberian hak. Reproduction: `ls system-prompts-and-models-of-ai-tools/`. Fix minimal: DECISION REQUIRED — (a) keluarkan dari repo, (b) jadikan remote terdokumentasi tanpa copy, atau (c) dokumentasikan analisis risiko. Gate: ikut AE-02. Confidence: tinggi (fakta konten), rendah (konsekuensi hukum).

**AE-04 | P2 | Arsitektur update | PARTIAL — "Updateability First" nominal**
- CONTRACT §2.3/§5.2 menjadikan `update-skills.sh` satu-satunya jalur refresh skill ("submodule atau remote terdokumentasi"), tetapi tidak ada `.gitmodules` dan 10/10 vendor full-copy tanpa `.git`: eksekusi di fixture menghasilkan 7× "Not a git repository … skipping" + 3× "update manually via re-vendor" lalu hanya re-run setup.sh. Evidence: log eksekusi fixture (`update-exit=0`, 7 skip). Impact: prosedur "Skill Update Flow (Monthly)" di CONTRACT menyesatkan; refresh upstream sepenuhnya manual tanpa mekanisme versi/pin. Root cause: pilihan vendoring langsung (commit `54ad7ab7`) tanpa mengubah kontrak/dokumen. Fix minimal (S): ubah CONTRACT/UPDATING agar mendeskripsikan realitas re-vendor (dengan SHA pin di CHANGELOG), atau pasang remote + versi per vendor. Regression: doc-check jumlah vendor yang bisa di-update. Gate: tidak (dokumen + proses). Confidence: tinggi.

**AE-05 | P2 | Dokumentasi | CONFLICT — cluster angka & prosedur basi di 8+ dokumen**
- Butir terverifikasi: (a) "149 tests" vs 190 aktual (README.md:143,349; README_INTEGRATION.md:106; .cursorrules:270); (b) "21 plugin" pasca-integrasi agency (QUICKSTART.md:24,105; ROUTER_POLICY.md:25; ARCHITECTURE.md:79 vs :143 di file yang sama; MCP_INTEGRATION_CHECKLIST.md:4; INTEGRATION_CHECKLIST.md:24; LICENSE_AUDIT.md judul); (c) README_INTEGRATION.md: "36 MCP servers" (:86) vs 38 (:318), "3,094 skills" (:148) vs 3,377 (:94), "8 AI-agent CLIs" dengan 9 nama termasuk Continue yang tidak didukung (:12-13), aritmetika "~3,356 + 40 → 3,377" (:255-257), "2,542 lines" setup.sh (:90) vs 2,430; (d) CHANGELOG.md:222 "ECC 819/819 pass" yang oleh TEST_RESULTS.md:98-104 sendiri disebut artefak run terpotong (realita saat itu 8.207/17); (e) UPDATING.md + FIXES_AND_USAGE.md + CONTRACT.md:114,211 masih mengajarkan config pra-2026-11-13 yang no-op (`~/.codex/config.yaml`, `~/.config/opencode/config.json`, `~/.cursor/settings.json`, `~/.windsurf/config.yaml`) dan default `/root/agent-enhancements` (kontradiksi TROUBLESHOOTING.md:12-17 dan R003); (f) ADR-006 ("tidak menambah root .cursorrules") dikontradiksi keberadaan `.cursorrules`; (g) QUICKSTART "5 kategori" vs 6; plugin-catalog/README.md:3 "20 remote + 21 vendored" (=41; realita 19+21); (h) 4 dokumen tanpa frontmatter wajib CONTRACT §7.3 (ENV_VARS, FIXES_AND_USAGE, MCP_INTEGRATION_CHECKLIST, UPDATING); (i) catalog.json `last_updated` 2026-11-12 padahal agency ditambahkan 11-15.
- Impact: pengguna/agent baru mengikuti prosedur salah (config no-op, angka tidakcocok saat verifikasi); menurunkan kepercayaan pada dokumen lain yang akurat. Root cause: gelombang integrasi (agency, native automation) tidak disertai sapuan konsistensi lintas-dokumen; CHANGELOG historis tidak dikoreksi. Fix minimal (M): satu PR penyapuan angka + path; jangan ubah isi historis CHANGELOG, tambahkan koreksi bersegel "corrected". Regression: tambah test dokumen (mis. hitung test fungsi vs angka di README; grep path no-op). Gate: tidak, tapi wajib sebelum "siap pakai". Confidence: tinggi (semua item diaudit ulang oleh subagent dokumen + spot-check auditor).

**AE-06 | P2 | .cursorrules | CONFLICT — klaim mekanisme yang tidak ada**
- .cursorrules:3-5 mengklaim disimpan-simbol oleh setup.sh ke `~/.cursor/`, `~/.claude/`, `~/.codex/`, `~/.continue/` — tidak ada kode itu (grep nol); :206 merujuk `docs/PATCHES.md` dan `unified-integration/patches/` yang tidak ada; tabel routing §1.4 menunjuk path `skills/<cat>/<slug>/` yang tidak ada di fresh clone (generated, AE-13); `~/.continue` = Continue yang tidak didukung (README_INTEGRATION:12-13 memasukkannya sebagai "8 CLIs" — 9 nama); ADR-006 melarang file ini. File 12 KB ini tetap diuji oleh `test_modular_tree.py` T-7 (coverage katalog) sehingga tampak "resmi". Fix minimal (S): hapus atau tulis-ulang sesuai realitas (Cursor memakai `~/.cursor/rules/agent-enhancements.mdc`); hapus Continue dari README_INTEGRATION. Regression: grep CI bahwa tidak ada klaim symlink/.continue. Gate: tidak. Confidence: tinggi.

**AE-07 | P2 | QA tooling | VERIFIED BUG — catalog-test.sh buta terhadap kategori agency**
- `catalog-test.sh:27` loop kategori `code research tokens-optimization design multimedia-writing` tanpa `agency` → semua 19 pack agency gagal "Manifest tidak ditemukan". Evidence: `bash unified-integration/scripts/catalog-test.sh nexus` → `[FAIL] Manifest tidak ditemukan untuk slug: nexus`, exit 1 (audit jalankan). Sementara `catalog-validate.py` 40/40 PASS. Impact: smoke test terdokumentasi (README:47, QUICKSTART) hanya menjangkau 21/40 plugin. Fix minimal (S): tambah "agency" ke loop; refactor agar daftar kategori dibaca dari catalog.json. Regression: test yang memanggil catalog-test untuk satu slug agency. Gate: tidak. Confidence: tinggi.

**AE-08 | P2 | Compression | CONFLICT — klaim otomatis vs utilitas manual + config dekoratif**
- README.md:262-268 mengklaim "Automatic token budget management … Budget 200k, Trigger 75% … Proxy Mode" vs realita: (a) tidak ada konsumen `compression/config.yaml` (grep `trigger_at_percent|budget` di kode = nol); (b) `compress.py` = utilitas manual per-file (mode + truncation 50.000 char) tanpa logika budget/trigger; (c) headroom binary tidak dibangun default dan hanya dipanggil `headroom compress --mode`; (d) instruksi agent yang ditulis setup justru menyuruh memakai "CLI's native automatic context compaction" (setup.sh:1517-1519). Proxy headroom (README:278-284) tidak diaktifkan oleh project. Fix minimal (S): tulis-ulang bagian README menjadi "manual utility + native compaction"; tandai config.yaml sebagai referensi atau buat konsumennya. Regression: doc-check. Gate: tidak. Confidence: tinggi.

**AE-09 | P2 | System prompts | PARTIAL — fitur "configured" tetapi tidak pernah diaktifkan**
- README.md:76 "Configure system prompts for each detected tool" → setup hanya `cp` file prompt (setup.sh:108-284); tidak ada agent yang memuatnya: Gemini/Kiro `config.yaml` berisi `system_prompt: "@…"` tetapi file itu sendiri berlabel reference-only; untuk OpenCode, native-integration.py:235-236 justru menghapus referensi prompt dari `instructions` dan menggantinya dengan AGENTS.md. Effectively dead feature + memperbesar permukaan redistribusi AE-03 (prompt komersial tersalin ke instalasi user). Fix minimal (S): ubah README menjadi "prompt referensi tersedia di prompts/ (tidak di-inject)"; atau wire-kan ke satu agent jika memang dimaksudkan (DECISION REQUIRED). Gate: tidak. Confidence: tinggi.

**AE-10 | P2 | MCP security | IMPLEMENTED (by design) — task-router = eksekusi arbitrer dengan denylist kosmetik**
- `task-router-mcp/server.py` `dispatch(kind="bash")` menjalankan `bash -lc <command>` (login shell, hak penuh user, jaringan penuh) di workspace temp; denylist 6 pattern hanya menangkap `rm -rf /` persis, mkfs, `dd if=`, fork bomb, `>/dev/sdX`, shutdown/reboot — mudah dilewati (`rm -rf ~`, `… ; echo x`, base64) dan `kind="python"` **tanpa denylist sama sekali**; tool diekspos ke LLM via gateway sehingga prompt-injection dari konten skill pihak ketiga dapat mengarahkan agent memanggilnya. Mitigasi nyata: approval tool-level di CLI (Claude Code/Codex) dan framing runtime.py ("subject to the user's instructions and normal tool permissions"); dokumentasi jujur "bukan sandbox" (server.py:12-13, smoke_test menolak `rm -rf /`). Fix minimal (M, tanpa meredesain): (1) samakan denylist minimal utk kind=python; (2) opt-in eksplisit di ui.api.json (`task-router.enabled=false` default); (3) dokumentasikan di SAFETY.md bahwa tool ini setara shell agent. Regression: test dispatch python berbahaya ditolak; test default-off. Gate: **YA** untuk rilis yang menargetkan pengguna non-ahli (default-on arbitrary execution via MCP perlu persetujuan eksplisit). Confidence: tinggi.

**AE-11 | P2 | Supply chain installer | IMPLEMENTED, UNTESTED (live) — eksekusi remote unpinned**
- README.md:56 satu-liner `curl … master/setup.sh | bash` men-clone **master tanpa pin SHA/tag/checksum**; branch piped (setup.sh:8-14) juga: jika `$INSTALL_DIR` sudah ada, menjalankan salinan lama tanpa update (stale-code), jika belum, men-clone master saat itu; langkah pertama setup selalu `setup-mcp.sh --prepare` = `pip install -r requirements.txt` dari PyPI tanpa pin versi (requirements.txt tanpa `==`), yang jika gagal (tanpa jaringan) **membatalkan seluruh setup** (set -e di main). Fix minimal (M): pin versi requirements; dukung `AGENT_ENHANCEMENTS_REF` untuk install ter-pin; buat failure venv menjadi peringatan dengan jalur stdlib-only bila memungkinkan. Regression: test instalasi offline. Gate: tidak (dengan catatan README:59 sudah ada peringatan review). Confidence: tinggi.

**AE-12 | P2 | Testing debt | KNOWN-BROKEN — suite ECC 43 kegagalan baseline + wajib oleh CONTRACT**
- CONTRACT §5.1/§6.1 mewajibkan `cd ECC && node tests/run-all.js` sebelum commit; audit historis mencatat 8.207-8.246 pass / 17-43 fail (angka bervariasi per lingkungan; TEST_RESULTS.md:98-104). Audit ini **NOT RUN** (lihat §6). Dengan CI mati (AE-01), tidak ada pemeriksaan otomatis ECC sama sekali. Fix minimal: putuskan (DECISION REQUIRED) — perbaiki 43, atau scoping ulang mandat kontrak ke owned layer, atau downgrade menjadi advisory. Gate: tidak untuk rilis agregasi, ya untuk klaim "ECC tests green". Confidence: sedang (mengandalkan laporan historis; tidak direproduksi).

### P3 — Low

- **AE-13 | P3 | skills/ tree** — `skills/manifest.json:3` mengklaim tiap entri "self-contained directory … backed by symlinks", tetapi 0/40 direktori ter-commit (generated saat install, gitignored); README.md:191-196 mendeskripsikan seolah sudah ada. Fix: satu kalimat README "(generated at install)" + samakan klaim manifest. Regression: —. Confidence: tinggi.
- **AE-14 | P3 | git hygiene** — setiap run `setup.sh` membuat working tree kotor: `all-skills.json` (`last_updated`) dan `agent-registry.json` (`generated_at`) berubah timestamp saja; drift-gate CI hanya menjaga `skills/` root (ci.yml:103), bukan kedua file ini. Fix (S): jangan tulis ulang bila konten selain timestamp identik, atau tambahkan keduanya ke drift-gate. Regression: run setup 2× → `git status` bersih. Confidence: tinggi (direproduksi).
- **AE-15 | P3 | OpenCode UX** — komentar JSONC user ter-strip dari `opencode.jsonc` saat setup (json dump menimpa; backup 0600 disimpan; docstring mengakui). Fix (S/M): tulis ulang memakai serialisasi yang mempertahankan komentar, atau beri tahu user eksplisit di output setup. Confidence: tinggi (direproduksi fixture).
- **AE-16 | P3 | Memory init** — `init-memory.sh` mencetak "Memory system initialized" walau DB tidak dibuat ketika CLI `sqlite3` absen (kondisi `command -v sqlite3`; hook Python membuat DB on-demand). Fix (S): cek keberadaan DB dan sesuaikan pesan. Confidence: tinggi (direproduksi).
- **AE-17 | P3 | Backup churn** — `merge_yaml_config` (setup.sh:1442-1455) membuat backup baru **setiap** run untuk `~/.gemini/config.yaml`, `~/.config/github-copilot/config.yaml`, `~/.kiro/config.yaml` meski konten akhir identik (fixture: 2 backup per file setelah 3 run); kebijakan berbeda dari merge marker/`native-integration.write()` yang backup-on-change. Fix (S): backup hanya bila hasil merge ≠ input. Regression: 2× run → jumlah backup konstan. Confidence: tinggi.
- **AE-18 | P3 | Hardening installer** — `ln -sf … /usr/local/bin/agent-enhanced` diam-diam ketika direktori writable (terjadi di sandbox audit; di mesin biasa gagal senyap). Menulis di luar $HOME tanpa opt-in. Fix (S): jadikan opt-in (`--install-launcher`) atau tanyakan. Confidence: tinggi.
- **AE-19 | P3 | Data hygiene katalog** — 4 id `mcp_servers` di catalog.json tanpa entri roadmap (`llm-cache-mcp`, `tokenizer-mcp`, `typescript-language-server`, `voice-clone-mcp`) + 1 mismatch nama (`typescript-language-server` vs `typescript-language-server-mcp`, mcp-servers.json:395); `plugin-catalog/agency/nexus.json` memuat 12 `sub_skills` yang path-nya tidak ada (beruntun ke `strategy/`); status `to-build` di legenda roadmap tak pernah terpakai. Fix (S): validator lintang catalog↔roadmap + perbaiki nexus. Confidence: tinggi.
- **AE-20 | P3 | Dead code** — `merge_json_config` (setup.sh:1329) tanpa pemanggil; cabang `npm run build` claude-mem di update-skills.sh:133-137 mustahil (vendor tanpa `.git`); referensi "Continue" (AE-06). Fix (S): hapus saat menyentuh file terkait (hindari churn terpisah). Confidence: tinggi.
- **AE-21 | P3 | Privasi data** — `vision-mcp describe` mengirim gambar (base64) ke api.openai.com saat `OPENAI_API_KEY` diisi (vision-mcp/server.py:144-172); consent-gate tidak mencakup kasus ini (hanya voice/video). Fix (S): sebutkan eksfiltrasi gambar di SAFETY.md/ENV_VARS.md; opsional minta consent. Confidence: tinggi.
- **AE-22 | P3 | Tooling ergonomi** — `mcp-test.sh:14` memicu `setup-mcp.sh --prepare` (membuat venv + pip install jaringan) sebagai efek samping tak terdokumentasi dari perintah "test"; dependensi `jq`/`json5` tidak dicek di awal (hanya tertangkap `set -e`). Fix (S): pisahkan `--prepare` ke flag eksplisit + precheck binari. Confidence: tinggi.

## 6. Test Execution

Lingkungan: sandbox Linux, Python 3.12.16, dependensi lengkap; fixture terisolasi `$HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `PATH` berisi 8 stub CLI (claude/codex/opencode/cursor/gemini/windsurf/kiro/gh-copilot) — **tidak menyentuh home/host nyata**. Semua artefak log di `/home/z/my-project/audit-evidence/`.

| # | Pengujian | Command (ringkas) | Hasil | Exit |
|---|---|---|---|---|
| T1 | Suite regresi (clone murni) | `python3 tests/run-tests.py` (unified-integration) | **190 ran / 190 pass / 0 fail / 8 skip** (6 link-skills: registry belum dibangun — by design; 2: guard `AE_MCP_NETWORK_TESTS`) | 0 |
| T2 | Suite regresi (fixture pasca-setup, 4× run) | idem, HOME fixture | **190 ran / 0 fail / 2 skip (network)** di 4 run beruntun | 0 |
| T2-anomali | 1 run awal menunjukkan `failures=2` | — | Tidak terreproduksi pada 4 run ulang; terjadi saat auditor menjalankan `registry.py` paralel di tree yang sama (interferensi tooling audit sendiri); nama test tidak sempat terekam karena output di-pipe | dicatat sebagai anomali tanpa atribusi |
| T3 | bash -n seluruh `.sh` owned layer | mirror ci.yml static-checks | **PASS semua** | 0 |
| T4 | py_compile seluruh `.py` owned layer | idem | **PASS semua** | 0 |
| T5 | Fresh install fixture (8 stub agent) | `bash setup.sh` (env fixture) | **exit 0, ~60 s**; 8/8 agent terdeteksi; agregasi 3.377 skill; registry dibangun; prompts tersalin; launcher+util diregenerasi | 0 |
| T6 | Verifikasi pasca-install (60 asersi) | skrip auditor | **58 PASS** (2 observasi: JSONC strip AE-15; symlink /usr/local AE-18) — termasuk: hook pribadi/apiKeyHelper/model/numStartups terpelihara; CLAUDE.md/GEMINI.md marker tanpa duplikasi; server MCP user (`my-own-server`) terpelihara di 3 CLI; komentar TOML terpelihara; gateway terpasang via venv python di `$CLAUDE_CONFIG_DIR/.claude.json`; 30+30 symlink curated; ui.api.json 0600 kosong | — |
| T7 | Idempotency (run-2, run-3) | `bash setup.sh` ulang | **exit 0**; konten konfig stabil (diff hanya 3 file YAML pada normalisasi pertama; run-3 nol diff); marker tidak menduplikasi; backup baru hanya dari AE-17 | 0 |
| T8 | Drift working tree pasca-setup | `git status --porcelain` | 2 file tracked berubah **hanya timestamp** (AE-14) | — |
| T9 | `setup-mcp.sh --check` (protokol MCP) | via venv fixture | **9/9 server + gateway (36 tools) stdio initialize + health OK** | 0 |
| T10 | `catalog-validate.py --root .` | audit-repo | **PASS 40/40** (19 warning agency tanpa MCP — wajar) | 0 |
| T11 | `catalog-test.sh nexus` | fixture | **FAIL "Manifest tidak ditemukan"** (AE-07) | 1 |
| T12 | dispatch battery (7 prompt EN/ID/override/fallback) | `dispatch.sh --dry-run` | **7/7 routing masuk akal** (replica-skill, docx, webapp-testing, ui-ux-pro-max, nexus, rea, rea) | 0 |
| T13 | registry map bilingual | `registry.py map "buat dokumen word laporan keuangan"` / `"clean this excel spreadsheet"` | docx #1 (13), xlsx #1 (14) | 0 |
| T14 | memory terisolasi | save/load/list/cleanup + lintas agent | nilai benar; load lintas agent gagal (terisolasi); db 0600 | 0/1 (sesuai desain) |
| T15 | launch-agent | stub claude + agent tak dikenal | exec stub + env diekspor; unknown ditolak dengan pesan | 0/1 |
| T16 | consent-gate EOF / "y" | `echo \| consent-gate.sh …` | **EOF → Refused exit 1** (dengan log); y → Approved exit 0 | 1/0 |
| T17 | audit-trail.sh mcp-call | args benar | JSONL tertulis sesuai skema | 0 |
| T18 | update-skills.sh | fixture | exit 0; 7 skip + 3 manual-warn; re-agregasi ulang (AE-04) | 0 |
| T19 | CI riil (GitHub Actions) | GET API (read-only) | **22/22 failure**; run HEAD: 5 job gagal pra-step (AE-01) | n/a |
| T20 | HEAD stability | `git ls-remote` master | tetap `6eebfc57` selama audit | 0 |
| T21 | Live `curl \| bash` bootstrap | **NOT RUN** | Mekanisme tercakup `test_piped_installer_bootstraps_the_complete_clone` (lulus di T1); live run akan menarik master tak-terpin, di luar HEAD diaudit | — |
| T22 | Suite ECC (CONTRACT §5.1) | **NOT RUN** | Estimasi 45 menit + npm install besar; baseline historis 8.246/43 (AE-12); CI pun tak menjalankannya (AE-01) | — |
| T23 | smoke-native-clis.py (CLI nyata) | **NOT RUN** | Tidak ada binary agent sungguhan di sandbox; laporan NATIVE_AUTOMATION (2026-11-14) telah menjalankannya terhadap Claude Code 2.1.202 / Codex 0.167.2 / OpenCode 2.2.5 — hasil itu dikutip sebagai bukti pihak ketiga, bukan milik audit ini | — |
| T24 | Network MCP (arxiv/news live) | **SKIP by design** | guard `AE_MCP_NETWORK_TESTS` (2 test) | — |

Ringkasan terukur: **PASS: T1-T10, T12-T18, T20 (16 baterai, 190+60+9+7+2 unit perilaku). FAIL: T11 (bug terdokumentasi AE-07), T19 (CI merah, non-kode). NOT RUN: T21-T23 (dengan alasan). SKIP: T24.**

## 7. Security & Supply-Chain Assessment

**Threat model ringkas** (user workstation → installer/config → registry skill → hooks/memory → MCP/tools → provider/upstream):

1. **User workstation → installer**: `curl | bash` unpinned (AE-11) adalah permukaan RCE by-design terbesar; mitigasi: HTTPS + repositori sendiri; ancaman nyata = kompromi akun GitHub pemilik. `setup-mcp.sh --prepare` pip-install unpinned dari PyPI (AE-11). `/usr/local/bin` write senyap (AE-18). Tidak ada eskalasi privilege (tanpa sudo); `rm -rf` internal hanya pada path dalam `by-category/` dengan nama yang disanitasi (setup.sh:494-511 — traversal dicegah; terverifikasi baca kode).
2. **Installer → konfigurasi user**: Preservasi terbukti (T6): hook user, kredensial (`apiKeyHelper`), server MCP user, komentar TOML, array instructions — semua bertahan; backup dibuat; atomic replace; JSONC komentar hilang (AE-15). Tidak ada uninstaller: penghapusan manual (hapus marker block, `link-skills.sh --unlink`, hapus entri hooks/server) — layak didokumentasikan (masuk Roadmap R3).
3. **Registry/skill → agent**: 3.377 SKILL.md pihak ketiga = permukaan prompt-injection inheren; mitigasi berlapis yang nyata: runtime.py hanya menyugestikan **path** (bukan isi), membingkai skill sebagai "task guidance, subject to the user's instructions and normal tool permissions", tidak pernah mengeksekusi konten skill, tidak menyimpan input/output tool; `load-skills.skill_path` menolak traversal. Sisa risiko: agent yang membaca SKILL.md lalu mengikuti instruksi berbahaya di dalamnya — bergantung pada gerbang approval CLI (sama dengan AE-10).
4. **Memory/hooks**: SQL parameterized penuh (R101 dipenuhi); DB 0600; redaksi kredensial ganda (regex + nilai terkonfigurasi via `api_config.redact`); TTL 7 hari; scoping agent+canonical-path; input dibatasi 2 MB; kegagalan hook advisory (tidak memblokir CLI); tidak ada kebocoran prompt ke provider luar.
5. **MCP/tools**: Gateway tunggal memvalidasi ulang snapshot kredensial **per panggilan** (rotasi tercegat), namespacing anti tool-collision, redaksi respons, stderr eksternal ke devnull, subprocess eksternal hanya menerima env yang dipetakan. `ui.api.json` 0600 + gitignored + fail-closed + status boolean-only (terverifikasi T6 + test api_config 9/9). Kelemahan desain yang disadari project: task-router (AE-10) dan eksfiltrasi gambar vision (AE-21). Tidak ada consent-gate per-tool untuk tool berisiko selain voice/video.
6. **Provider/upstream**: 10 vendor full-copy ~866 MB tanpa pin/SHA/submodule (AE-04); lisensi salah-label (AE-02); arsip prompt komersial (AE-03); tidak ada secret ter-commit; hook/vendor executable (superpowers `hooks/session-start`, ponytail hooks) tidak diaktifkan oleh project — hanya ikut terdistribusi sebagai file (permukaan hanya jika user menjalankannya sendiri).

**Audit trail & insiden**: consent.jsonl/mcp-calls/video/decisions diimplementasi (T16-T17); `incidents.jsonl` tanpa writer (manual by design); retensi 12 bulan terdokumentasi. Kemampuan rollback = backup per-file + `--unlink`; tidak ada rollback agregat.

## 8. Compatibility Matrix

Bukti: F = ditulis terverifikasi di fixture audit ini; A = diklaim + diverifikasi oleh audit historis dengan CLI nyata (NATIVE_AUTOMATION 2026-11-14, versi dicantumkan); — = tidak ada.

| Agent | Deteksi | Lokasi konfig (aktual) | Native hooks | MCP | Skills otomatis | Bukti | Status |
|---|---|---|---|---|---|---|---|
| Claude Code | `command -v claude` | `~/.claude/settings.json` (merge, credential dipertahankan); `CLAUDE_CONFIG_DIR` dihormati; MCP user-scope di `.claude.json` (inner bila config-dir custom) | Ya (SessionStart/UserPromptSubmit/PostToolUse/Stop → runtime.py, timeout 10s) | Ya (gateway di mcpServers) | Ya (30 symlink `~/.claude/skills`) | F + A (v2.1.202) | **VERIFIED WORKING** |
| Codex CLI | `command -v codex` | `~/.codex/AGENTS.md` (marker), `config.toml` (MCP, komentar TOML dipertahankan via tomlkit), `hooks.json` (percaya via `/hooks`); `CODEX_HOME` dihormati | Ya (4 event) | Ya | Ya (`~/.agents/skills`) | F + A (v0.167.2, 0.169.0; keterbatasan snapshot katalog per-turn terdokumentasi) | **VERIFIED WORKING** |
| OpenCode | `command -v opencode` | `opencode.jsonc`→`opencode.json`; marker `AGENTS.md`; plugin async `opencode-plugin` (tanpa deps npm) | Ya (via plugin) | Ya (`mcp.servers`, migrasi v1→v2) | Ya (`skills` array → by-category; curated via `~/.agents/skills`) | F + A (v2.2.5) | **VERIFIED WORKING** |
| Cursor | `command -v cursor` | `~/.cursor/rules/agent-enhancements.mdc` (frontmatter, alwaysApply:false) | Tidak | Tidak (manual) | Ya (`~/.agents/skills`) | F | **IMPLEMENTED** (instruction-level; aktivasi bergantung relevansi rule Cursor) |
| Gemini CLI | `command -v gemini` | `~/.gemini/GEMINI.md` (marker) + `config.yaml` reference-only | Tidak | Tidak (manual) | Ya (`~/.agents/skills`) | F | **IMPLEMENTED** (hierarchical context) |
| Windsurf | `command -v windsurf` | `~/.codeium/windsurf/rules/agent-enhancements.md` | Tidak | Tidak | Ya (`~/.agents/skills`) | F | **IMPLEMENTED** |
| GitHub Copilot | `gh extension list` ∋ copilot | `~/.config/github-copilot/config.yaml` **reference-only** | Tidak | Tidak | Ya (`~/.agents/skills`) | F | **DOCUMENTED ONLY** (dilabeli reference di README — jujur) |
| Kiro | `command -v kiro` | `~/.kiro/config.yaml` **reference-only** | Tidak | Tidak | Ya (`~/.agents/skills`) | F | **DOCUMENTED ONLY** |
| Continue | — (tidak ada kode) | — | — | — | — | klaim README_INTEGRATION:12-13 | **NOT IMPLEMENTED** (AE-06) |
| Harness Agent-Skills lain | — | `~/.agents/skills` | — | — | Ya | F | **VERIFIED** (standar lintas-agent) |

Catatan versi: dukungan native hooks terverifikasi pada versi CLI yang dicantumkan audit historis; perilaku CLI lain/lebih baru tidak diklaim.

## 9. Remediation Roadmap

Urutan = keamanan/credential → integritas installer/runtime → interoperabilitas → ergonomi. Effort: S (<½ hari), M (½-2 hari), L (>2 hari).

**Blokir rilis (release gates):**
1. **[AE-01, M, PEMILIK]** Selesaikan billing GitHub Actions → satu run hijau di master. *Acceptance*: run terbaru master `conclusion=success`, kelima job mengeksekusi step-nya.
2. **[AE-02, S, penulis dokumen + KEPUTUSAN PEMILIK model lisensi agregasi]** Koreksi tabel lisensi/provenance README dari metadata vendor; tambahkan LICENSE root; perluas LICENSE_AUDIT ke 10 vendor. *Acceptance*: setiap baris tabel cocok dengan LICENSE/NOTICE vendor; `ls LICENSE` ada.
3. **[AE-03, KEPUTUSAN PEMILIK]** Pilih: keluarkan system-prompts vendor / jadikan remote terdokumentasi / analisis risiko tertulis. *Acceptance*: keputusan tercatat di ADR baru; repo konsisten dengannya.
4. **[AE-10, M]** task-router: denylist utk python + default disabled (opt-in di ui.api.json) + dokumentasi SAFETY. *Acceptance*: test "python berbahaya ditolak" + "default off" lulus.

**Perbaikan awal berikutnya (quick wins):**
5. **[AE-07, S]** tambah `agency` ke loop catalog-test.sh (atau baca dari catalog.json). *Acceptance*: `catalog-test.sh nexus` exit 0.
6. **[AE-05, M]** satu PR penyapuan angka/path basi (149→190; 21→40; 36→38; 3.094→3.377; hapus Continue; koreksi bersegel 819/819; path UPDATING/FIXES/CONTRACT §4.3-8.1; QUICKSTART 5→6). *Acceptance*: grep hitung "149 tests|21 plugin|config.yaml ~/.codex" = 0 di owned docs.
7. **[AE-06, S]** hapus/tulis-ulang `.cursorrules` sesuai realitas. *Acceptance*: tidak ada klaim symlink/.continue/patches.
8. **[AE-14+AE-17, S]** setup tidak menulis ulang file bila hanya timestamp berubah; backup hanya on-change. *Acceptance*: 2× setup → `git status` bersih; jumlah backup konstan.

**Peningkatan (opsional, tidak memblokir):**
9. **[AE-08, S]** README compression jujur; **[AE-09, S]** README prompts jujur; **[AE-11, M]** pin requirements + `AGENT_ENHANCEMENTS_REF`; **[AE-12, KEPUTUSAN]** mandat ECC di CONTRACT; **[AE-13, AE-19, AE-20, S]** hygiene data/dead-code; **[AE-15/16/18/21/22, S]** UX kecil; **[R-baru]** dokumentasikan prosedur uninstall/rollback manual.

Setiap perubahan CONTRACT/schema/arsitektur (termasuk item 3, 12, dan model lisensi) masuk kategori **DECISION REQUIRED** dan tidak dieksekusi agent tanpa persetujuan pemilik (CONTRACT §4.2).

## 10. Readiness Decision

**CONDITIONAL.** Kondisi minimum agar **READY** (semua dapat diuji objektif):
1. CI hijau sekali di HEAD (AE-01).
2. Tabel lisensi README benar + LICENSE root ada (AE-02) + keputusan AE-03 tercatat.
3. task-router default-off atau disetujui eksplisit (AE-10).
4. Sapuan dokumen AE-05/AE-06/AE-08/AE-09 selesai (tidak ada lagi prosedur no-op yang diajarkan ke pengguna baru).

Fungsional inti (install → aktivasi → memory → MCP → dispatch) **sudah layak dipakai** di lingkungan yang memahami batasannya; yang belum layak adalah klaim "CI-validated" dan kepatuhan lisensi redistribusi.

## 11. Independent Review & Disagreements

- Tiga subagent read-only benar-benar dijalankan (dokumentasi/klaim; vendor/lisensi; plugin-catalog) + auditor utama membaca sendiri seluruh jalur kritis (setup.sh 2.430 baris penuh, native-integration, runtime, api_config, gateway, task-router, registry, dispatch, launcher, updater, tests, CI) dan menjalankan seluruh validasi dinamis. Tidak ada reviewer yang dipalsukan.
- Rekonsiliasi: temuan subagent vendor (lisensi) dan catalog (agency test bug, skills-tree) direproduksi/diverifikasi sebelum masuk laporan; klaim subagent docs tentang "ECC 8.211/13 vs 8.246/43" dicatat sebagai inkonsistensi historis tanpa direproduksi (T22 NOT RUN).
- Ketidaksesuaian internal hasil audit ini: run test tunggal dengan `failures=2` (T2-anomali) yang tidak terreproduksi pada 4 run ulang — dilaporkan apa adanya tanpa atribusi pasti (kemungkinan interferensi tooling auditor paralel).
- Ketidakpastian yang diwariskan: atribusi billing untuk CI (pola bukti kuat, konfirmasi hanya pemilik akun); konsekuensi hukum AE-03 (di luar kewenangan audit).

## 12. Open Questions & Handoff

**Keputusan untuk pemilik project (DECISION REQUIRED):**
1. Model lisensi agregasi (MIT + NOTICE per-vendor? hanya metadata?) dan nasib direktori system-prompts vendored (AE-02/AE-03).
2. Default task-router-mcp: tetap on (dengan documentation) atau off (opt-in)? (AE-10).
3. Mandat ECC dalam CONTRACT §5.1: perbaiki 43 failure, scope ulang, atau advisory? (AE-12).
4. Apakah fitur system-prompt dan compression-config dimaksudkan aktif (maka implementasikan konsumen) atau dijadikan referensi (maka rapikan klaim)? (AE-08/AE-09).
5. Strategi pembaruan vendor: tetap manual re-vendor dengan SHA tercatat, atau restore remote/submodule? (AE-04).

**Handoff untuk agent eksekutor berikutnya (dapat langsung dikerjakan tanpa konteks tambahan):**
1. AE-07: satu baris di `unified-integration/scripts/catalog-test.sh:27` (tambah `agency`) + test regresi kecil. Acceptance: `catalog-test.sh nexus` exit 0.
2. AE-14: di `setup.sh` index builder (sekitar baris 793) dan `registry.py cmd_build` (baris 411-427): skip penulisan bila hanya field timestamp berubah. Acceptance: 2× setup → `git status` bersih.
3. AE-17: `merge_yaml_config` (setup.sh:1442-1455): backup hanya bila hasil ≠ input. Acceptance: jumlah backup stabil antar-run.
4. AE-05 sweep: kerjakan per butir §9.6 dengan grep-list acceptance yang sudah didefinisikan.
5. AE-02: salin tabel dari §temuan ini (data sudah terverifikasi) → README + LICENSE_AUDIT.md baru.
6. Setelah billing selesai: verifikasi run CI master hijau; jika gagal, ambil log job pertama yang gagal (API: `/actions/runs/{id}/jobs`) dan lanjutkan diagnosis — jangan asumsikan penyebab kode.
7. Jalankan ulang `python3 unified-integration/tests/run-tests.py` (harus 190/190) dan `setup-mcp.sh --check` (9/9+36) setelah setiap perubahan di atas.

**Arsip bukti audit** (di luar repo, milik sesi auditor): log fixture `/home/z/my-project/audit-evidence/fixture_install_run{1,2}.log`, `update_skills.log`, skrip `scripts/audit_fixture_run.sh`, `audit_fixture_verify.py`, `audit_battery2.sh` — dapat direproduksi dengan `bash scripts/audit_fixture_run.sh init && bash scripts/audit_fixture_run.sh install && bash scripts/audit_fixture_run.sh verify`.
