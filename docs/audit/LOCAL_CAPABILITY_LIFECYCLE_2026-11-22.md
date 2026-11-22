---
title: Audit provisioning lokal dan konteks AgentEnhancements
version: '1.0'
last_updated: '2026-11-22'
audience: maintainer dan reviewer
---

## Audit provisioning lokal dan konteks AgentEnhancements

Baseline `373eaaf6ff6c635820cbbc3117ba5fe32199c7e0` pada `master`.
Implementasi lokal yang diukur `8ecf036f8be13a458645397deb46b58fafa553b8`.
Tiga reviewer meninjau arsitektur, upstream dan pengujian host. Semua
setup dan pengujian memakai checkout serta HOME terisolasi.

### Keputusan per acceptance gate

| Gate | Status | Bukti dan batas |
| --- | --- | --- |
| Satu setup mempersiapkan bundel lokal | PASS | Debian 13 x86-64. Setup menyusun 3.378 skill, menyiapkan 34 distribusi Python dengan hash, dan memverifikasi 10 backend Python serta satu gateway melalui stdio. Pemakaian ulang, upgrade gagal, rollback, relokasi dan provisioning paralel diperiksa. |
| Katalog dapat dicari dan dibaca sesuai kebutuhan | PASS | Semua 3.467 ID unik termasuk plugin, MCP dan fitur bawaan terinventarisasi. Bridge membaca teks L0. `search --catalog` menampilkan kandidat yang terblokir beserta diagnosis dalam hasil terbatas. |
| Pemilihan dan panggilan otomatis dalam sesi host | PARTIAL | Hook, aset skill dan panggilan MCP lokal teruji. Codex terpasang mengenali gateway. Sandbox Codex menolak namespace jaringan sebelum request model fixture. Host Claude Code, OpenCode dan Hermes belum tersedia untuk uji sesi pada lingkungan ini. |
| Diagnostik readiness dan pencabutan akses | PASS | Fixture stdio menguji handshake, panggilan, pencabutan key, stale command dan pemisahan key. Pengujian prasyarat media melindungi daftar schema dan panggilan lama. Kandidat eksternal dilaporkan berdasarkan konfigurasi dan pemeriksaan upstream. |
| Efisiensi token dan kualitas tugas | PARTIAL | Teks L0 lebih kecil pada proksi `o200k_base`. Corpus 50 kasus mempertahankan hasil discovery. Uji tambahan meraih 5/7 pada kedua revisi. Telemetry model dan keberhasilan penyelesaian tugas pada host tetap diperlukan. |
| Provisioning kandidat eksternal | PARTIAL | Audit mencakup semua kandidat. Kandidat yang butuh instalasi tambahan, persetujuan lisensi atau OAuth tercatat di matriks upstream. Paket yang meragukan tetap berupa entri katalog. |

### Diagnosis dan perubahan

| Prioritas | Baseline dan bukti | Hasil |
| --- | --- | --- |
| P1 | `setup-mcp.sh` menjalankan instal sebelum memilih mode. Requirements berupa rentang dan proses upgrade menulis langsung ke venv aktif. | Setup memakai lock wheel, memverifikasi runtime baru di path generasi final, lalu mengganti pointer stabil. `--check` memeriksa stdio bundel dengan config fixture kosong. |
| P1 | `server_state()` menggunakan executable pertama sebagai cek. `npx` dan package runner lain bisa muncul di jalur runtime. Registry menandai command tersebut siap. | Launcher yang dikenali diblokir. Status eksternal menunggu bukti handshake. Gateway hanya menayangkan tool dari koneksi yang cocok dengan konfigurasi terbaru. |
| P1 | Perubahan command atau mapping credential bisa meninggalkan tool worker historis hingga watcher berikutnya. | Daftar dan panggilan cocokkan fingerprint konfigurasi dan credential aktif setiap kali. |
| P2 | Prompt Claude/Codex/Hermes mengarahkan pembacaan JSON L0 lengkap. OpenCode sudah mengambil field `rendered`. | Bridge memakai `build-library-map.py --print` dengan path absolut yang dikutip aman. Deskripsi 16 skill native tetap bagian dari pengukuran. |
| P2 | FFmpeg, render video dan OCR menawarkan schema walau executable tidak tersedia. Pencarian membuka banyak hasil pada kueri panjang. | Gateway memeriksa executable per tool. Registry membatasi hasil teks dan JSON ke maksimal lima kartu utuh dengan budget 800 token proksi runtime. |
| P2 | Mode 1 membutuhkan payload yang harus disediakan adapter. Penerimaan list-change dan tool deferral bergantung host. | Fallback Mode 0 dipertahankan. Perubahan profil native, pemilihan tool lintas host dan provisioning eksternal tercatat di [ADR-009](../ADR.md#adr-009--penyajian-tool-dan-provisioning-lintas-host). |

`ui.api.json` tetap satu konfigurasi AE. Mode 0 memakai ranking lokal dan
Mode 2 memakai adapter HTTPS yang sudah tersedia. Uji regresi mencakup
selected, lookup, abstain, deadline, fallback dan redaksi. Mode 1 fallback
karena belum ada payload native yang terbukti pada host pengujian.

### Matriks kesiapan

[CSV tiap kapabilitas](CAPABILITY_READINESS_2026-11-22.csv) berasal dari
registry yang sama. File sumber, version pin, kebutuhan credential, host,
status lokal, visibilitas gateway, penggunaan fixture dan blocker ada di
kolom terpisah. Ukuran file adalah byte dari path yang dicatat. Runtime
Python dan cache dipakai bersama sehingga biaya RAM dan startup dihitung
untuk profil gateway. SHA baseline mencakup sumber vendored yang dipakai
untuk skill. Daftar ini merekam keadaan pengujian dengan key kosong.

| Permukaan | Ada di disk | Dipersiapkan dan siap | Terlihat atau dimuat | Bukti panggilan |
| --- | --- | --- | --- | --- |
| 3.378 skill | Sumber vendored lolos resolusi file | Setup mengagregasi indeks | 16 symlink bawaan. Detail tersedia on demand | Fixture membuka skill yang dipilih untuk empat kasus |
| 40 panduan plugin | Seluruh panduan ada | Panduan dapat dibaca, termasuk 39 entri `integrated-ready` | Registry dan pemilihan opsional | Runtime plugin upstream memerlukan pembuktian sendiri |
| 10 MCP Python bundled | Backend dan lock lokal | Stdio dan health diperiksa per backend | 24 tool termasuk `ae_health` pada default key kosong | Probe video dan embedding lokal dipanggil lewat stdio |
| 1 companion `agent_browser` | Sumber Node dan lock ada | Konfigurasi contoh mematok disabled | Di luar tool list default | Lingkungan browser belum diverifikasi |
| 30 MCP `to-install` | Entri roadmap | Status per kandidat di audit upstream | `search --catalog` atau `show` memberi diagnosis | Instalasi, persetujuan dan panggilan provider perlu bukti terpisah |
| 8 kapabilitas bawaan | Kode dan konfigurasi ada | Setup menyiapkan yang berlaku untuk host | Lifecycle hooks, CLI atau lookup | Suite integrasi meliputi entry point yang tersedia |

### Pengukuran sebelum dan sesudah

Lingkungan memakai Debian 13.7 x86-64, Python 3.12.14, Node 24.22.3,
Codex CLI 0.172.0-alpha.2, uv 0.13.9, FFmpeg serta Tesseract sistem.
Tokenizer pengujian `tiktoken` 0.14.0 `o200k_base` dipakai di luar runtime.
Kedua sisi memakai HOME fixture, konfigurasi key kosong, Mode 0 dan
sampel prompt yang sama. Path checkout dan fixture dinormalisasi.

[Data mentah yang disanitasi](../benchmark/ae-lifecycle-evidence.json)
memuat SHA file sumber, nama kasus, hasil retrieval, latency dan pemakaian
per kanal. Proksi cold start menghitung marker native, pembacaan L0,
observer, deskripsi linked, schema eager yang diproyeksikan dari MCP
stdio, dan prompt hook. Catatan recall dihitung terpisah. Pengukuran ini
mengasumsikan model membaca L0 dan host menyertakan semua schema yang
tersedia. Host dapat melakukan penundaan native atau memilih subset.

| Kanal atau metrik | Baseline | Patch |
| --- | ---: | ---: |
| L0 dibaca dari bridge, token `o200k_base` | 942 | 486 |
| L0 dibaca dari bridge, bytes | 3.601 | 2.154 |
| Marker native, token | 213 | 196 |
| Deskripsi native, token proyeksi | 1.065 | 1.065 |
| Tool schema eager, token proyeksi | 1.468 | 1.468 |
| `tools/list` stdio, tool dan bytes | 24 / 6.326 | 24 / 6.326 |
| Observer pada HOME kosong, token | 122 | 122 |
| Recall fixture, token | 39 | 39 |
| Cold start tanpa recall, maksimum 7 kasus | 4.061 | 3.588 |
| Cold start termasuk recall, maksimum 7 kasus | 4.100 | 3.627 |
| Initialize dan tools/list p50 / p95, ms dari 5 startup | 435,2 / 581,8 | 441,9 / 578,8 |
| Prompt hook p50 / p95, ms dari 35 panggilan | 150,1 / 327,8 | 159,0 / 293,1 |

Corpus bilingual tetap di top-1 25/40, top-3 30/40, abstain 6/6 dan
MCP tidak tersedia yang ditawarkan 0/4 untuk kedua revisi. Maksimum hook
corpus adalah 311 token dengan fallback lokal karakter dibagi empat.
Uji tambahan membuka skill defensif, DOCX, riset dan video, serta
abstain untuk aritmetika sederhana. Dua prompt panjang belum menemukan
skill TypeScript atau Python yang diharapkan pada lintasan pertama.
Pencarian `TypeScript refactor` dan `Python debugging` mencapai skill
relevan dalam tiga hasil pada pemeriksaan terfokus.

Fixture video menjalankan probe lokal pada clip 32×32. Fixture embeddings
mendapat vektor 256 dimensi dan fixture riset memverifikasi bahwa tool
pencarian key kosong tetap tersembunyi. Biaya model selector Mode 0 nol
karena selector tidak dipanggil. Estimasi inferensi Mode 2 live masih
memerlukan akun uji. Data path total per kasus mencakup pembacaan skill
terpilih dan hasil tool, dengan jumlah token yang mengikuti panjang
instruksi skill. Skill yang panjang tetap menambah konteks saat benar-benar
dibaca.

Ukuran state bersih sekitar 72,0 MB pada kedua checkout. RSS maksimum
proses anak pada pengukuran fixture dicatat di JSON. Angka tersebut
mencakup CLI dan proses pembantu. Venv lama yang disimpan untuk rollback
menambah biaya disk sebesar satu generasi per lingkungan yang disimpan.

### Gate pengujian dan runbook

| Pemeriksaan | Hasil |
| --- | --- |
| `run-tests.py` baseline dan fitur | 471 tes termasuk 4 skip pada baseline. 475 tes termasuk 4 skip pada fitur. |
| ECC `node tests/run-all.js` | 8.292 pass, 456 file, dengan XDG dibersihkan, dependencies Node tersedia dan mode npm offline. |
| Protokol MCP | 11/11 dan panggilan lokal nyata ke gateway. |
| Setup paralel | Dua `setup.sh` berhasil dengan lock yang sama. Pembaruan runtime mempertahankan satu generasi valid per lock dalam uji paralel. |
| Upgrade dan rollback | Venv fisik lama dipertahankan. Gagal memasang lock fixture mempertahankan pointer aktif. Lock sebelumnya memakai ulang env yang sudah lolos tes. |
| Relokasi | Path absolut baru memicu persiapan ulang dengan wheel cache. Protokol tetap lulus. |
| Codex | `mcp list --json` mengenali gateway stdio. `doctor.py --agents codex --json` lulus 1/1 termasuk panggilan tool lokal. |
| Integrasi host lain | Fixture adapter OpenCode dan tes wiring Hermes/Claude lulus. Pengujian live CLI dan model belum tersedia. |
| Provider live | Empat skip resmi mencakup Mode 2 live, arXiv, Google News dan search provider live. Fixture lokal menjalankan pengujian kontrak. |

Jalankan dari checkout yang aktif. Setup memakai HOME host tujuan.
Jika mengevaluasi patch, jalankan kedua revisi pada HOME berbeda.

```bash
bash unified-integration/setup.sh
bash unified-integration/scripts/setup-mcp.sh --check
bash unified-integration/scripts/link-skills.sh --audit
python3 unified-integration/scripts/api_config.py status
runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
"$runtime_python" unified-integration/tests/run-tests.py
"$runtime_python" unified-integration/tests/discovery_benchmark.py --check
"$runtime_python" unified-integration/scripts/doctor.py --agents codex --json
```

[Runbook sistem](../RUNBOOK.md) dan [panduan upgrade](../UPDATING.md)
menjelaskan persyaratan platform, offline, pemulihan dan rollback.
Perintah benchmark yang mengumpulkan byte stdio, proksi konteks dan
hasil prompt tersedia di [runner paired](../benchmark/paired-lifecycle.py).
Untuk `o200k_base`, siapkan tiktoken 0.14.0 pada environment benchmark
terpisah dengan encoding cache yang tersedia dan masukkan site-packages
tersebut pada `PYTHONPATH` sesi benchmark. Runner dapat dipanggil dengan
interpreter AE dari masing-masing checkout serta argumen `REPO --home HOME`
dan `--repeats 5`. Hook yang diperiksa tetap memakai tokenizer runtime
lokal dan konfigurasi fixture sendiri.

### Bukti lifecycle host

- Claude Code mendokumentasikan dynamic tool updates dan Tool Search.
  Dampak schema pada model bergantung pengaturan dan model.
  `https://code.claude.com/docs/en/mcp#dynamic-tool-updates`
- OpenCode menyediakan `mcp.servers` dan Code Mode. Setup AE menggunakan
  direct tools pada konfigurasi baru dan mempertahankan pilihan yang ada.
  `https://opencode.ai/docs/mcp-servers/`
- Codex mempunyai `enabled_tools` dan `disabled_tools` serta lifecycle hooks.
  CLI yang tersedia melaporkan `mcp_tool_list_changed` sebagai fitur dalam
  pengembangan yang default-nya nonaktif.
  `https://learn.chatgpt.com/docs/extend/mcp?surface=cli`
- Hasil stdio bernegosiasi pada MCP 2025-11-25. MCP 2026-07-28 menambahkan
  pembatasan untuk daftar yang bervariasi karena koneksi atau efek request
  lain. Audit mempertahankan kontrol izin host di jalur panggilan.
  `https://modelcontextprotocol.io/specification/2026-07-28/server/tools`
- Dokumentasi resmi `npm exec` menerangkan pemasangan ke cache bila paket
  belum tersedia lokal. AE memeriksa launcher sebelum proses external.
  `https://docs.npmjs.com/cli/v11/commands/npm-exec/`

Review rilis perlu menyelesaikan bukti host live, pembatasan schema dalam
profil credential yang mengaktifkan lebih banyak tool, serta verifikasi
rilis eksternal. Batas lisensi, OAuth dan scope instalasi ditelusuri pada
audit upstream berikut.

### Verifikasi upstream dan dependensi MCP

Snapshot `373eaaf6ff6c635820cbbc3117ba5fe32199c7e0`, diperiksa 22 November
2026 WIB. Roadmap memiliki 30 entri `to-install` dan 11 entri `built`. Audit
ini memeriksa identitas, metode distribusi, lisensi yang tersedia dan
dependensi utama. Nomor versi dari manifest sumber membuktikan versi yang
ditampilkan upstream. Status siap dipasang otomatis memerlukan artefak rilis
yang dipin, pemeriksaan integritas dan dependensi transitif, platform yang
didukung, serta uji stdio dan panggilan dengan izin yang sesuai. Tidak ada
paket eksternal dipasang dalam pemeriksaan ini.

| ID `to-install` | Bukti upstream dan keputusan persiapan | Sumber |
| --- | --- | --- |
| `you-mcp` | Paket resmi `@youdotcom-oss/mcp` 4.2.0 pada manifest, MIT, Node ≥18. Paket lokal adalah bridge stdio ke layanan You.com. Fitur berbayar membutuhkan key atau OAuth. AE sudah punya adapter pencarian You.com dengan `YOU_API_KEY`. | Dokumentasi You.com `https://you.com/docs/agents/mcp-server`, manifest `https://github.com/youdotcom-oss/mcp/blob/main/package.json` |
| `serper-mcp` | Serper mendokumentasikan API. Asal dan distribusi paket roadmap belum terbukti. `search-mcp` sudah punya adapter Serper dengan `SERPER_API_KEY`. | Serper `https://serper.dev/` |
| `tavily-mcp` | Nama paket sesuai sumber vendor. Manifest menampilkan 0.2.23 dan MIT. Membutuhkan Node, jaringan dan `TAVILY_API_KEY` untuk fitur layanan. Adapter pencarian AE sudah mencakup Tavily. | Repo Tavily `https://github.com/tavily-ai/tavily-mcp`, manifest `https://github.com/tavily-ai/tavily-mcp/blob/main/package.json` |
| `exa-mcp` | Paket `exa-mcp-server` 3.5.1 tersedia di npm dan sesuai manifest MIT, Node ≥20. Key dan jaringan tetap dibutuhkan untuk adapter lokal. Pencarian dasar sudah tersedia melalui adapter Exa AE. | Manifest Exa `https://github.com/exa-labs/exa-mcp-server/blob/main/package.json`, npm `https://www.npmjs.com/package/exa-mcp-server` |
| `firecrawl-mcp` | Paket `firecrawl-mcp` 3.41.0 tersedia di npm dan sesuai manifest MIT, Node ≥22. Layanan resmi butuh jaringan dan key. Pencarian dasar sudah tersedia melalui adapter Firecrawl AE. Instalasi server self-hosted punya prasyarat sendiri. | Manifest Firecrawl `https://github.com/firecrawl/firecrawl-mcp-server/blob/main/package.json`, npm `https://www.npmjs.com/package/firecrawl-mcp` |
| `neo4j-mcp` | Distribusi resmi melalui PyPI, Homebrew atau arsip sesuai OS. Upstream mencantumkan GPL-3.0 dan ketentuan untuk produk komersial. Dibutuhkan pemeriksaan lisensi, akses basis data dan izin yang sesuai sebelum mengemasnya. | Instalasi `https://neo4j.com/docs/mcp/current/installation/`, lisensi `https://github.com/neo4j/mcp/blob/main/LICENSE.txt`, notice `https://github.com/neo4j/mcp/blob/main/NOTICE.txt` |
| `browser-tools-mcp` | Paket yang didokumentasikan oleh Agent Infra adalah `@agent-infra/mcp-server-browser` 1.2.29 pada manifest. Paket menyatakan MIT, root monorepo Apache-2.0. Nama roadmap belum terbukti. Browser dan izin jaringan perlu ditetapkan sesuai lingkup, serta cakupan lisensi artefak diperiksa. | Dokumentasi Agent Infra `https://github.com/bytedance/UI-TARS-desktop/blob/main/packages/agent-infra/mcp-servers/browser/README.md`, manifest `https://github.com/bytedance/UI-TARS-desktop/blob/main/packages/agent-infra/mcp-servers/browser/package.json`, lisensi root `https://github.com/bytedance/UI-TARS-desktop/blob/main/LICENSE` |
| `lighthouse-mcp` | Paket dengan nama roadmap terdaftar. Publisher, kepemilikan upstream, Chromium dan dependensi paket belum diaudit. Lighthouse resmi menyediakan CLI tersendiri. | Listing paket `https://www.npmjs.com/package/lighthouse-mcp`, GoogleChrome Lighthouse `https://github.com/GoogleChrome/lighthouse` |
| `pa11y-mcp` | Listing publik menunjukkan paket 0.0.1 dengan ISC. Hubungan dengan proyek Pa11y, distribusi dan dependensi browser belum terbukti. | Listing `https://www.jsdelivr.com/package/npm/pa11y-mcp`, Pa11y `https://github.com/pa11y/pa11y` |
| `figma-mcp` | Figma mendukung HTTP jarak jauh dengan autentikasi dan HTTP desktop melalui aplikasi Figma dengan syarat akun. Nama paket roadmap belum terbukti sebagai distribusi vendor. Gateway eksternal AE saat ini menggunakan stdio. | Panduan Figma `https://help.figma.com/hc/en-us/articles/39216419318551-Get-started-with-the-Figma-MCP-server` |
| `storybook-mcp` | `@storybook/addon-mcp` 0.7.0 pada manifest, MIT. Ini addon yang dipasang pada proyek Storybook dan mengikuti kompatibilitas proyek. Nama dan instalasi langsung roadmap belum terbukti. | Addon resmi `https://storybook.js.org/addons/%40storybook/addon-mcp`, manifest `https://github.com/storybookjs/mcp/blob/main/packages/addon-mcp/package.json` |
| `mermaid-mcp` | Mermaid Chart mendokumentasikan layanan MCP jarak jauh dan akun Mermaid melalui OAuth atau token. CLI Mermaid berlisensi MIT adalah distribusi lokal terpisah. Identitas paket roadmap belum terbukti. | MCP Mermaid Chart `https://mermaid.ai/docs/ai/mcp-server`, CLI Mermaid `https://github.com/mermaid-js/mermaid-cli` |
| `excalidraw-mcp` | Repo organisasi Excalidraw menyediakan build stdio dan bundle. Manifest menampilkan `@mcp-demos/excalidraw-server` 0.3.2, MIT, dengan postinstall penyiapan Bun. Butuh pemeriksaan artefak dan script sebelum provisioning. | Repo Excalidraw `https://github.com/excalidraw/excalidraw-mcp`, manifest `https://github.com/excalidraw/excalidraw-mcp/blob/main/package.json` |
| `google-slides-mcp` | Endpoint resmi jarak jauh dalam Developer Preview membutuhkan proyek Google Cloud dan OAuth berstatus AI-agent. OAuth client ID dan secret saja belum membuktikan akses akun. Paket npm roadmap belum terbukti. | Google for Developers `https://developers.google.com/workspace/slides/api/guides/configure-mcp-server`, catatan rilis `https://developers.google.com/workspace/slides/release-notes` |
| `office-mcp` | Microsoft mendokumentasikan MCP dalam Microsoft 365, tetapi paket `office-mcp` di roadmap dan dukungan Word/Excel/PowerPoint yang disebut AE belum terverifikasi. Perlu sumber pengembang yang jelas serta izin tenant dan pengguna. | Microsoft Learn `https://learn.microsoft.com/en-us/microsoft-365/admin/manage/manage-byo-mcp-server?view=o365-worldwide` |
| `image-search-mcp` | Microsoft menghentikan Bing Search APIs 11 Agustus 2025. Dependensi `BING_IMAGE_API_KEY` dalam roadmap memerlukan penggantian yang ditinjau sebelum entri bisa dibuktikan. | Microsoft Lifecycle `https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement` |
| `heygen-mcp` | Integrasi resmi sekarang menggunakan HTTP dan OAuth HeyGen serta kuota akun. Paket npm roadmap belum terbukti. | Konfigurasi resmi HeyGen `https://github.com/heygen-com/skills/blob/master/mcp.json` |
| `elevenlabs-mcp` | Paket resmi adalah Python `elevenlabs-mcp`, MIT, manifest 0.12.2. Membutuhkan `ELEVENLABS_API_KEY` dan jaringan. Nama paket npm roadmap belum terbukti. | Repo ElevenLabs `https://github.com/elevenlabs/elevenlabs-mcp`, manifest `https://github.com/elevenlabs/elevenlabs-mcp/blob/main/pyproject.toml` |
| `typescript-language-server-mcp` | Proyek TypeScript Language Server resmi menyediakan LSP. Paket MCP dengan identitas persis seperti roadmap dan pemelihara yang dapat diverifikasi belum ditemukan. | TypeScript Language Server `https://github.com/typescript-language-server/typescript-language-server` |
| `eslint-mcp` | Paket resmi `@eslint/mcp` 0.3.17 pada manifest, Apache-2.0, Node 20.19+, 22.13+ atau 24+ menurut rentang upstream. Konfigurasi dan plugin proyek perlu dipercaya, terutama saat memuat konfigurasi TypeScript. | Dokumentasi ESLint `https://eslint.org/docs/latest/use/mcp`, manifest `https://github.com/eslint/rewrite/blob/main/packages/mcp/package.json` |
| `jupyter-mcp` | Datalayer menyediakan `jupyter-mcp-server`, BSD-3-Clause, dengan lingkungan Jupyter atau sandbox terkait. `python -m jupyter_mcp` di roadmap belum terbukti sebagai entry point paket itu. Eksekusi kernel perlu otorisasi dan isolasi eksplisit. | Repo Datalayer `https://github.com/datalayer/jupyter-mcp-server`, rilis `https://jupyter-mcp-server.datalayer.tech/releases/` |
| `python-repl-mcp` | Ada beberapa proyek pihak ketiga dengan nama serupa. Asal modul roadmap belum ditentukan dan REPL dapat menjalankan Python atau memasang paket. Pertahankan sebagai kandidat yang memerlukan tinjauan izin. | Katalog proyek pihak ketiga `https://glama.ai/mcp/servers/miloira/python-repl-mcp` |
| `memory-mcp` | Server referensi resmi `@modelcontextprotocol/server-memory` 2.2.1 pada manifest, Node ≥24. Lisensi proyek sedang beralih dari MIT ke Apache-2.0. Graf persisten perlu cakupan tersendiri dan persetujuan arsitektur sebelum menambah penyimpanan di luar memori kanonis AE. | Manifest `https://github.com/modelcontextprotocol/servers/blob/main/src/memory/package.json`, lisensi `https://github.com/modelcontextprotocol/servers/blob/main/LICENSE` |
| `github-issues-mcp` | GitHub mendistribusikan `github-mcp-server`, MIT, dengan mode lokal dan server jarak jauh. Iterasi lokal memerlukan token dengan cakupan terbatas dan pemilihan toolset. Paket npm roadmap belum terbukti. | GitHub MCP Server `https://github.com/github/github-mcp-server`, konfigurasi `https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md` |
| `linear-mcp` | Linear mendokumentasikan HTTP jarak jauh dengan OAuth atau skema autentikasi yang didukung. Paket npm roadmap belum terbukti. | Linear Docs `https://linear.app/docs/mcp` |
| `wikipedia-mcp` | Wikimedia Enterprise menyediakan MCP untuk dokumentasi API. Cakupannya berbeda dari pencarian artikel dalam roadmap. Sumber paket dan izin konten harus diverifikasi untuk server artikel. | Wikimedia Enterprise `https://enterprise.wikimedia.com/docs/agents/` |
| `newsapi-mcp` | News API mendokumentasikan API berkey. `search-mcp` sudah memiliki adapter dengan `NEWSAPI_KEY`. Sumber dan rilis paket npm terpisah belum terbukti. | News API `https://newsapi.org/docs` |
| `filesystem-mcp` | Server referensi resmi `@modelcontextprotocol/server-filesystem` 2.4.0 pada manifest, Node ≥24. Lisensi rilis dan direktori yang diizinkan perlu ditinjau, termasuk mode baca-saja dan integrasi izin host. | Manifest `https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/package.json`, batas direktori `https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/README.md`, lisensi `https://github.com/modelcontextprotocol/servers/blob/main/LICENSE` |
| `pdf-mcp` | Proyek PDF MCP pihak ketiga memiliki beberapa nama yang mirip. Pemetaan nama roadmap, maintainer, lisensi dan dependensi parser belum terbukti. | Contoh proyek publik `https://github.com/angshuman/pdf-mcp` |
| `grammar-mcp` | LanguageTool mendokumentasikan API HTTP. `LANGUAGE_TOOL_URL` sendiri belum membuktikan executable MCP terpasang, endpoint sehat atau izin data. Identitas paket roadmap belum terbukti. | LanguageTool API `https://languagetool.org/http-api/` |

### Roadmap `built`

| ID | Ketersediaan runtime dasar |
| --- | --- |
| `graphrag-mcp` | Backend Python di checkout menggunakan penyimpanan lokal dan input yang diizinkan. |
| `embeddings-mcp` | Backend Python dengan vektor lokal deterministik. Alur OpenAI opsional membutuhkan key dan jaringan. |
| `agent_browser` | Sumber Node 1.0.0 dan lockfile tersedia, tetapi Node, dependensi dan Chromium adalah runtime eksternal. Contoh konfigurasi `agent-browser-mcp` tetap nonaktif. Provisioning dan pengujian langsung dikecualikan karena backend juga memiliki fitur penghindaran deteksi otomatisasi. |
| `ffmpeg-mcp` | Backend Python membutuhkan `ffmpeg` dan `ffprobe` sistem untuk operasi media yang didukung. |
| `video-mcp` | Penyusunan timeline dan EDL lokal. Rendering bergantung pada `ffmpeg` sistem. |
| `task-router-mcp` | Backend ada dan nonaktif secara default. Eksekusi perintah memerlukan opt-in dan izin host. |
| `arxiv-mcp` | Backend Python lokal, panggilan pencarian membutuhkan jaringan ke arXiv. |
| `google-news-mcp` | Backend Python lokal, pencarian membutuhkan jaringan ke feed Google News. |
| `search-mcp` | Backend Python lokal untuk enam adapter pencarian. Setidaknya satu key provider dibutuhkan, beserta jaringan. |
| `vision-mcp` | Perbandingan gambar memakai Pillow lokal, OCR memerlukan `tesseract` sistem, deskripsi semantik membutuhkan key dan jaringan. |
| `style-mcp` | Backend Python lokal untuk aturan gaya dan pemeriksaan teks. |

### Provenance plugin yang perlu dikoreksi atau diverifikasi

- Repo Addy Osmani memakai MIT. Metadata katalog yang mencatat Apache-2.0
  perlu diperbarui.
  `https://github.com/addyosmani/agent-skills/blob/main/LICENSE`
- Caveman, Impeccable dan HyperFrames memakai Apache-2.0 pada upstream saat
  audit. Metadata katalog mencatat MIT. Caveman
  `https://github.com/JuliusBrussee/caveman/blob/main/LICENSE`, Impeccable
  `https://github.com/pbakaus/impeccable/blob/main/LICENSE`, HyperFrames
  `https://github.com/heygen-com/hyperframes/blob/main/LICENSE`
- OpenMontage berpindah ke `OpenMontageInc/OpenMontage` dan memakai AGPL-3.0.
  Metadata katalog mencatat asumsi MIT. Vendoring memerlukan review versi dan
  lisensi. Lisensi OpenMontage
  `https://github.com/OpenMontageInc/OpenMontage/blob/main/LICENSE`
- URL GSD saat ini mengarah ke repo yang diarsipkan dengan lisensi MIT. Pindah
  ke fork atau distribusi lain membutuhkan verifikasi provenance baru. Repo
  GSD `https://github.com/gsd-build/get-shit-done`
- README dan metadata plugin Karpathy menyatakan MIT. Teks lisensi penuh pada
  root dengan nama standar belum ditemukan. README
  `https://github.com/multica-ai/andrej-karpathy-skills/blob/main/README.md#license`,
  manifest
  `https://github.com/multica-ai/andrej-karpathy-skills/blob/main/.claude-plugin/plugin.json`
- Anthropic menggunakan lisensi per skill. Audit AE melaporkan 18 dari 19
  direktori memiliki `LICENSE.txt`, dengan cakupan `doc-coauthoring` belum
  terbukti. Pertahankan pemeriksaan per direktori. [Audit lisensi
  AE](../LICENSE_AUDIT.md).
- Pemeriksaan file lisensi root memberi kecocokan MIT untuk Matt Pocock,
  Replica Skill, Agent Reach, Last 30 Days, REA, Understand Anything, BMAD,
  GSD, GStack, Diagram Design, PPT Master, UI/UX Pro Max, Humanizer dan Agency
  Agents. Graphify cocok dengan Apache-2.0. Status plugin `integrated-ready`
  tetap menjelaskan guide/routing AE. Lisensi branch default tidak
  memverifikasi binari, distribusi tambahan atau runtime plugin yang dipasang.
  [Katalog AE](../../plugin-catalog/catalog.json).
