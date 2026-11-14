---
title: Audit kredensial terpusat dan MCP otomatis
version: 1.1
last_updated: 2026-11-15
audience: owner, maintainers
---

# Hasil implementasi dan audit lanjutan

Agent: Codex. Session koreksi: `codex-mcp-scope-20261115`.
Branch koreksi: `fix/mcp-credential-boundary`.

## Keadaan yang benar-benar berjalan

Credential layanan MCP berada di satu file privat root `ui.api.json`, mode 0600,
diabaikan git. Template kosong dan schema editor dilacak di
[config](../../unified-integration/config/ui.api.example.json). Pemetaan mencakup
38 MCP katalog: 15 slot secret, beserta endpoint/client ID/model layanan MCP.
Credential login/provider model milik agent tidak termasuk di dalamnya.

Satu gateway native memuat sembilan backend bawaan. Dengan seluruh key MCP
kosong, tersedia 36 tool lokal; `vision_describe` tidak ditawarkan dan
embeddings hanya mengizinkan backend lokal. GraphRAG sepenuhnya lokal.
Sebanyak 29 server eksternal tetap tersembunyi sampai runtime dan credential
yang dibutuhkan dikonfigurasi. Keberadaan dalam katalog tidak berarti paket
upstream sudah dipasang atau OAuth sudah selesai.

Perubahan file dipantau tiap 0,5 detik. Tool diperiksa kembali saat dipanggil;
nama/schema yang tersimpan pada client tidak melewati pencabutan credential.
Server eksternal yang kehilangan key dihentikan, termasuk penyelesaian request
yang sedang menunggu. Rotasi key menyambung ulang backend. Kegagalan koneksi
dicoba ulang setelah 30 detik. Secret tidak disalin ke config MCP native atau
status diagnostik; catatan sesi menyamarkan nilai secret yang terkonfigurasi.
File JSON yang hilang/rusak menonaktifkan akses cloud dan tetap menyediakan
subset tool lokal.

## Batas proyek dan koreksi

Pemindahan credential Claude pada implementasi sebelumnya melampaui scope
MCP dan sudah dibatalkan. Credential dikembalikan ke konfigurasi native;
helper/TTL yang ditambahkan proyek dihapus, dengan pengaturan lain dipertahankan.
Entri auth/endpoint/model agent dihapus dari file pusat dan template.

Loader MCP tidak membaca atau mengimpor settings/provider/login milik
Claude Code, Codex, OpenCode maupun agent lain. Tidak ada lagi perintah
helper untuk mengeluarkan credential agent. Koordinasi proses Linux melalui
file readiness juga dihapus; MCP memakai lifecycle native client.

Contohnya, `TAVILY_API_KEY` adalah credential layanan MCP proyek. Sebaliknya,
token untuk menjalankan model Claude/Codex/OpenCode tetap menjadi urusan host.
Keduanya tidak saling mengisi otomatis, sekalipun memakai nama environment
yang sama, seperti `OPENAI_API_KEY`.

## Bug tambahan yang diperbaiki

| Temuan | Perubahan |
|--------|-----------|
| Penghapusan entry MCP tidak mencabut tool yang sudah di-cache | Gateway memfilter katalog dan memeriksa key/schema pada setiap panggilan |
| Environment shell dapat mengaktifkan cloud walau file pusat kosong | File pusat menjadi sumber credential; tidak ada fallback API env untuk MCP proyek |
| GraphRAG ditandai membutuhkan API key | Metadata dikoreksi; tool lokal tetap aktif |
| Embeddings memakai cloud secara default saat menemukan key dan menerima backend sembarang | Default lokal; enum backend dinamis dan validasi pilihan |
| Error provider dapat membawa response body berisi data sensitif | Pesan error aman dan redaksi secret terkonfigurasi |
| Adapter OpenCode menulis format V1 yang diabaikan V2 | Migrasi ke `mcp.servers`, `disabled`, `environment`; tool gateway diekspos langsung |
| Shared runtime mengandung koordinasi proses CLI khusus Linux | Dihapus; loader/gateway MCP tidak bergantung pada jenis agent |
| `CLAUDE_CONFIG_DIR` memakai lokasi MCP yang keliru | Gunakan `<config-dir>/.claude.json`; diverifikasi melalui CLI asli |
| Penutupan external MCP saat request berjalan dapat meninggalkan future menunggu | Semua request tertunda diselesaikan dengan error saat disconnect/revokasi |
| Cache GraphRAG tidak melihat pembaruan dari proses CLI lain | Snapshot atomik di disk menjadi sumber pembacaan |
| Dua penulisan timeline bersamaan dapat saling menimpa | Lock proses melindungi keseluruhan read/update/replace |
| `same_size` gambar selalu true setelah resize | Simpan perbandingan ukuran asli sebelum resize |
| Nilai flag `--type mcp` masuk ke query dan menghasilkan kecocokan palsu | Pisahkan nilai opsi dari teks relevansi |

## Bukti pengujian

- Suite setelah koreksi scope: **190 test, 188 lulus dan dua uji jaringan
  opsional dilewati**. Termasuk regresi yang memastikan credential/helper
  native agent tidak berubah dan tidak masuk ke file MCP.
- Transport MCP nyata: **10/10** (sembilan backend + gateway), initialize,
  list tools dan health.
- Pengujian CLI audit sebelumnya memakai model tiruan localhost: Claude Code 2.1.202,
  Codex 0.167.2 dan OpenCode 2.2.5. Model meminta health tool secara otomatis,
  tanpa perintah skill/memori/MCP dari pengguna. Task dan ringkasan otomatis
  tersimpan; perubahan credential terlihat oleh panggilan backend.
- Pada audit sebelumnya empat hook Codex ditinjau setelah perubahan source dan dipercaya
  melalui kontrol native; tidak memakai flag bypass trust. Perubahan source
  hook pada update berikutnya dapat memerlukan review native kembali.
- Claude/OpenCode: katalog tool berubah **false → true → false** untuk cloud
  saat key kosong, diisi dummy lokal, lalu dikosongkan. Tidak ada panggilan
  cloud vision/embedding berbayar dalam test tersebut.
- Codex 0.169.0 dipasang dan diuji terpisah di direktori data proyek.
  Versi default tetap 0.167.2 karena versi baru masih mempunyai batasan katalog
  yang sama; provider/model/config pengguna tidak diganti.
- Pengujian HTTP localhost menguji endpoint/model/key terpusat serta rotasi
  credential pada embeddings dan vision tanpa biaya model nyata.
- Pengujian state: klien GraphRAG melihat update klien lain; 16 update timeline
  paralel tidak kehilangan entry; file/lock privat.
- ECC vendor: dijalankan ulang seluruh **8.289 test**, hasil **8.246 lulus,
  43 gagal pada 10 file**, sama dengan baseline audit sebelumnya.
  Source ECC tidak dimodifikasi; hook vendor tersebut bukan lifecycle adapter
  native yang dipasang proyek.

Log lokal privat/diagnostik tidak berisi nilai key dalam laporan ini. Perintah
reproduksi (untuk maintainer; agent/pengguna sehari-hari tidak perlu menjalankannya):

```bash
runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
AE_MCP_NETWORK_TESTS=1 "$runtime_python" unified-integration/tests/run-tests.py
bash unified-integration/scripts/setup-mcp.sh --check
python3 unified-integration/tests/smoke-native-clis.py --exercise-tools
```

## Batasan yang tetap perlu diketahui

**Codex menyimpan snapshot katalog selama satu giliran.** Baik 0.167.2 maupun
0.169.0 tidak memperbarui daftar tool di request model berikutnya dalam giliran
yang sama, walaupun backend sudah membaca key baru. Gateway langsung menolak
credential yang dicabut; tool cloud yang baru tersedia dapat memerlukan sesi
baru agar muncul. Tidak dilakukan patch/bypass pada keamanan atau client Codex.

Eksternal memerlukan implementasi yang benar-benar terpasang dan auth valid.
Command katalog tidak otomatis diunduh/dijalankan. Client ID/secret Google
atau Microsoft saja bukan OAuth grant. Proxy eksternal saat ini meneruskan
tool, bukan resource/prompt/OAuth. Hasil CLI sebelumnya berlaku untuk mesin
Linux dan versi yang disebutkan; koordinasi readiness khusus CLI sudah dihapus.

Pemilihan skill tetap menggunakan relevansi lexical dan keputusan model.
Penemuan native/routing/memori berjalan otomatis, tetapi tidak berarti setiap
task memerlukan setiap skill atau bahwa seluruh dependency 3.094 skill vendor
sudah dipasang. Lihat [audit sebelumnya](NATIVE_AUTOMATION_AUDIT_2026-11-14.md).

## Peta credential MCP

Nama di kolom required/optional merujuk `api_keys` atau `connections` pada
file pusat; tabel tidak menyimpan nilai credential. Untuk 29 entry eksternal,
nama requirement mengikuti katalog dan belum merupakan sertifikasi kontrak
upstream. Mapping `env` dapat menunjuk nama environment implementasi yang
benar ke slot credential pusat yang sama.

| MCP | Implementasi | Required | Optional |
|-----|--------------|----------|----------|
| `brave-search-mcp` | Eksternal | `BRAVE_API_KEY` | — |
| `tavily-mcp` | Eksternal | `TAVILY_API_KEY` | — |
| `exa-mcp` | Eksternal | `EXA_API_KEY` | — |
| `firecrawl-mcp` | Eksternal | `FIRECRAWL_API_KEY` | — |
| `neo4j-mcp` | Eksternal | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | — |
| `graphrag-mcp` | Bawaan | — | — |
| `embeddings-mcp` | Bawaan | — | `OPENAI_API_KEY` |
| `browser-tools-mcp` | Eksternal | — | — |
| `lighthouse-mcp` | Eksternal | — | — |
| `pa11y-mcp` | Eksternal | — | — |
| `figma-mcp` | Eksternal | `FIGMA_TOKEN` | — |
| `storybook-mcp` | Eksternal | — | — |
| `mermaid-mcp` | Eksternal | — | — |
| `excalidraw-mcp` | Eksternal | — | — |
| `google-slides-mcp` | Eksternal | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | — |
| `office-mcp` | Eksternal | `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` | — |
| `image-search-mcp` | Eksternal | `BING_IMAGE_API_KEY` | — |
| `ffmpeg-mcp` | Bawaan | — | — |
| `video-mcp` | Bawaan | — | — |
| `heygen-mcp` | Eksternal | `HEYGEN_API_KEY` | — |
| `elevenlabs-mcp` | Eksternal | `ELEVENLABS_API_KEY` | — |
| `typescript-language-server-mcp` | Eksternal | — | — |
| `eslint-mcp` | Eksternal | — | — |
| `jupyter-mcp` | Eksternal | — | — |
| `python-repl-mcp` | Eksternal | — | — |
| `memory-mcp` | Eksternal | — | — |
| `task-router-mcp` | Bawaan | — | — |
| `github-issues-mcp` | Eksternal | `GITHUB_TOKEN` | — |
| `linear-mcp` | Eksternal | `LINEAR_API_KEY` | — |
| `wikipedia-mcp` | Eksternal | — | — |
| `arxiv-mcp` | Bawaan | — | — |
| `newsapi-mcp` | Eksternal | `NEWSAPI_KEY` | — |
| `google-news-mcp` | Bawaan | — | — |
| `filesystem-mcp` | Eksternal | — | — |
| `pdf-mcp` | Eksternal | — | — |
| `vision-mcp` | Bawaan | — | `OPENAI_API_KEY` |
| `style-mcp` | Bawaan | — | — |
| `grammar-mcp` | Eksternal | `LANGUAGE_TOOL_URL` | — |

## Status repository

Fetch ulang mengonfirmasi `origin/master` tetap `7b868327`.
Branch audit memuat tiga commit audit native sebelumnya, lalu perubahan sesi ini.
Implementasi awal tercatat pada commit `5652e78d`; koreksi scope tercatat pada
branch `fix/mcp-credential-boundary`.
Tidak ada push atau publikasi ke GitHub. Stash dan branch backup sebelum audit
tetap disimpan. Detail kondisi awal lokal tertinggal 52 commit tersedia pada
[audit sebelumnya](NATIVE_AUTOMATION_AUDIT_2026-11-14.md).

