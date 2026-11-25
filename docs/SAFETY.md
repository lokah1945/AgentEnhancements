---
title: Safety and Compliance Guide
version: 1.2
last_updated: 2026-11-25
audience: all agents and maintainers
---

## Safety & Compliance Guide

Panduan keamanan dan kepatuhan untuk operasi sensitif. **Wajib dibaca**
sebelum menggunakan skill: `hyperframes`, `openmontage`, `replica-skill`
(launch/deploy), `rea` (rekayasa balik), atau operasi yang melibatkan data
personal.

### 0. task-router-mcp: eksekusi arbitrer (opt-in)

`task-router-mcp` menjalankan payload bash/python apa pun dengan hak dan
lingkungan user Anda (login shell, jaringan penuh). Ia setara dengan shell
agent itu sendiri — **bukan sandbox**. Denylist internal hanya menolak pola
destruktif yang jelas (`rm -rf /`, `mkfs`, dd ke disk, fork bomb, shutdown)
dan kini berlaku juga untuk payload python (termasuk `shutil.rmtree("/")`);
pola lain lolos. Karena tool ini diekspos ke model via gateway MCP,
prompt-injection dari konten pihak ketiga dapat mencoba memanggilnya.

Karena itu sejak 2026-11-15:

- **Default: disembunyikan** (`api_config.DEFAULT_DISABLED`). Gateway, registry
  discovery, dan `status()` tidak menawarkannya sampai user opt-in.
- **Opt-in eksplisit**: set `"task-router-mcp": {"enabled": true}` di
  `ui.api.json` (lihat template
  `unified-integration/config/ui.api.example.json`).
- Server tetap bisa diuji langsung via `setup-mcp.sh --check` (stdio) meski
  disembunyikan dari gateway.
- Mitigasi utama tetap approval per-tool di host CLI (Claude Code/Codex);
  jangan menonaktifkan kontrol izin host demi "memperlancar" tool ini.

### 1. Consent Gate (Voice Cloning & Personalized Video)

#### Kapan wajib

- `hyperframes` dengan voice clone
- `elevenlabs` voice clone
- `heygen` custom avatar
- Setiap operasi yang menghasilkan media berwajah/bersuara mirip orang nyata

#### Mekanisme

```bash
bash unified-integration/scripts/consent-gate.sh "<purpose>" "<sample>" "<approver>"
```

- exit 0 = approved, lanjut; exit 1 = refused, hentikan
- log: `unified-integration/memory/audit/consent.jsonl`

Ini helper eksplisit: pemanggil wajib menjalankan dan memeriksa exit code.
Gateway tidak otomatis membungkus tool MCP eksternal dengan helper ini.
Permission/approval host tetap berlaku; panduan tidak membuktikan bahwa
server eksternal menegakkan consent atau menulis audit trail.

#### Aturan

1. Tidak pernah auto-approve; tiap session baru wajib re-confirm.
2. Voice sample wajib milik user atau dengan izin tertulis. Tidak boleh
   clone tokoh publik tanpa izin tertulis terverifikasi.
3. Minor (< 18): consent wajib dari wali.
4. Sample hash (SHA-256) dicatat sebagai evidence.
5. Retention media personal: kebijakan operator 30 hari; tidak ada purge
   otomatis dalam helper ini.

### 2. Audit Trail

- **Log:** `memory/audit/mcp-calls.jsonl`
  - **Isi:** panggilan yang dicatat eksplisit lewat helper

- **Log:** `memory/audit/consent.jsonl`
  - **Isi:** setiap consent decision

- **Log:** `memory/audit/video.jsonl`
  - **Isi:** setiap generate video/voice/avatar

- **Log:** `memory/audit/decisions.jsonl`
  - **Isi:** keputusan arsitektur/non-trivial

```bash
bash unified-integration/scripts/audit-trail.sh mcp-call \
  "tavily-mcp" "search" "abc123" "5 results"
bash unified-integration/scripts/audit-trail.sh video \
  "hyperframes" "sales outreach" "def456" "/path/out.mp4" "user"
bash unified-integration/scripts/audit-trail.sh decision "add-replica-skill" \
  "Vendor replica-skill, MIT, registrasi di pipeline agregasi"
```

Retention audit: minimum 12 bulan. Tidak ada auto-purge audit.
Direktori `unified-integration/memory/audit/` diabaikan git (`.gitignore`),
sehingga log privat ini tidak ikut ter-commit.

### 3. Data Sensitif & PII

- Tidak pernah log PII (nama, email, NIK, no rek) ke audit; mask dulu.
- Tidak expose API key ke log; hanya hash argumen.
- Tidak share data ke third-party tanpa consent.
- Dokumen sensitif (medis/legal/keuangan): model lokal bila ada; jangan pakai
  MCP cloud public.
- **vision-mcp `describe` mengunggah gambar** (base64) ke
  `api.openai.com` (atau `OPENAI_BASE_URL`) saat `OPENAI_API_KEY` diisi di
  `ui.api.json`. Tanpa key, tool ini tersembunyi dari gateway. Jangan
  mengirim gambar sensitif (dokumen, wajah, layar berisi data pribadi) bila
  Anda tidak menyetujui pemrosesan di server OpenAI; gunakan alat lokal.
  vision-mcp hanya membaca file gambar (PNG, JPEG, GIF, BMP, TIFF, WebP) di
  dalam allowed roots media (cwd, `/tmp`, `AE_FFMPEG_ALLOWED_ROOTS`); video-mcp
  memakai roots yang sama untuk klip dan output, dan teks overlay dibaca dari
  file privat sehingga tidak pernah menjadi sintaks filtergraph ffmpeg.
- Redaksi kredensial (memory, observasi, input selector mode 1) mengenali
  kunci yang dikonfigurasi di `ui.api.json` serta bentuk token umum: GitHub,
  `sk-`, AWS `AKIA`, GitLab, Tavily, Firecrawl, Google, Slack, Hugging Face,
  Groq, xAI, npm, Stripe live, JWT, private key PEM, `user:password@` pada
  URI, dan header Bearer/Basic. Format lain bisa lolos: jangan menempelkan
  kredensial ke prompt.
- Kandidat skill dengan label upstream `risk: offensive` ditandai
  "needs explicit authorization" di kartu hook dan registry; konfirmasi
  otorisasi tertulis sebelum memakainya.

### 4. Clean-Room Discipline (replica-skill)

Panduan replica-skill mensyaratkan disiplin clean-room:

- Rebuild fungsi + UX pattern saja. TIDAK menyalin kode, aset, logo,
  trademark, copy, atau private API target.
- Hanya baca halaman public + akun sendiri; tidak scrape di balik login orang
  lain; tidak menembus paywall; tidak melanggar ToS.
- Wajib rebrand sebelum launch: `replica-deploy` menolak ship selama
  `sweep.py` masih menemukan nama/domain/warna original di codebase.
- Entrepreneur tidak mengarang: semua review/quote punya link; sample size
  dinyatakan.
- Sebelum jualan: jalankan trademark check dari `replica-brand`; konsultasi
  lawyer bila ada uang di atas meja.

### 5. License Compliance

Setup checks the Python wheel hashes against the repository lock and runs
the bundled MCP smoke checks with empty credentials. External MCP servers
require a deliberately installed entry point and authorized credentials.
The gateway rejects package runners such as `npx` and `uvx`. Review the
installed executable and its behavior before granting host permissions.
The entry point check covers launcher forms that AE recognizes. User-owned
scripts and executables still run with the permissions granted by the host.

Setiap manifest katalog punya field `source.license`. Status:

- **Plugin:** replica-skill
  - **License:** MIT
  - **Verifikasi:** **VERIFIED** (LICENSE file upstream, vendored)

- **Plugin:** 20 plugin lain
  - **License:** bervariasi (assumed MIT/Apache)
  - **Verifikasi:** TODO — lihat docs/LICENSE_AUDIT.md

Vendor ulang hanya untuk license permissive (MIT/Apache/BSD). GPL/AGPL:
pertimbangkan rewrite. Proprietary: jangan distribute.

### 6. Kebijakan dan batas implementasi

Kebijakan consent, retensi dan audit harus ditetapkan operator sesuai
konteks pemrosesan serta aturan yang berlaku. Helper ini mencatat keputusan
terminal; ia tidak memverifikasi identitas, izin pemilik suara, kewajiban
hukum, usia subjek, atau kelayakan transfer data. Tidak ada sertifikasi
kepatuhan yang dihasilkan oleh exit code sukses.

Direktori audit menggunakan 0700, file log 0600 dan menolak symlink tujuan.
Nilai kredensial yang dikenal disamarkan sebelum log dan tampilan consent.
Redaksi kredensial tidak menggantikan penyamaran PII oleh pemanggil.

### 7. Red Flags — Hentikan Segera

1. Request clone tokoh publik / Deepfake deceptive.
2. Request voice clone tanpa izin tertulis.
3. Request akses data di luar workspace.
4. MCP return data tidak relate ke query (suspicious leak).
5. Audit log berubah/hilang tanpa eskalasi.
6. Consent gate dilewati (tidak ada flag bypass; jangan buat).

### 8. Incident Response

1. Hentikan operasi.
2. Catat timestamp + scope ke `memory/audit/incidents.jsonl`.
3. Eskalasi ke user: scope, cause preliminary, action, next.
4. Purge data bila di-approve.
5. Post-mortem ke `docs/` (file baru per insiden).

### 9. Checklist Sebelum Production

- [ ] .env management siap (tidak ada hardcoded API key)
- [ ] consent-gate.sh teruji untuk semua flow multimodal
- [ ] Audit log rotation configured (> 12 bulan)
- [ ] Retention policy aktif (purge 30 hari)
- [ ] License audit selesai (lihat docs/LICENSE_AUDIT.md)
- [ ] Cross-border disclosure siap (HeyGen/ElevenLabs)
- [ ] DSAR procedure documented
- [ ] Incident response drill minimal 1x
