---
title: Safety and Compliance Guide
version: 1.0
last_updated: 2026-11-13
audience: all agents and maintainers
---

# Safety & Compliance Guide

Panduan keamanan dan kepatuhan untuk operasi sensitif. **Wajib dibaca**
sebelum menggunakan skill: `hyperframes`, `openmontage`, `replica-skill`
(launch/deploy), atau operasi yang melibatkan data personal.

## 1. Consent Gate (Voice Cloning & Personalized Video)

### Kapan wajib

- `hyperframes` dengan voice clone
- `elevenlabs` voice clone
- `heygen` custom avatar
- Setiap operasi yang menghasilkan media berwajah/bersuara mirip orang nyata

### Mekanisme

```bash
bash unified-integration/scripts/consent-gate.sh "<purpose>" "<sample>" "<approver>"
```

- exit 0 = approved, lanjut; exit 1 = refused, hentikan
- log: `unified-integration/memory/audit/consent.jsonl`

### Aturan

1. Tidak pernah auto-approve; tiap session baru wajib re-confirm.
2. Voice sample wajib milik user atau dengan izin tertulis. Tidak boleh
   clone tokoh publik tanpa izin tertulis terverifikasi.
3. Minor (< 18): consent wajib dari wali.
4. Sample hash (SHA-256) dicatat sebagai evidence.
5. Retention media personal: 30 hari default, lalu purge.

## 2. Audit Trail

| Log | Isi |
|-----|-----|
| `memory/audit/mcp-calls.jsonl` | setiap MCP tool call (server, tool, args hash, result) |
| `memory/audit/consent.jsonl` | setiap consent decision |
| `memory/audit/video.jsonl` | setiap generate video/voice/avatar |
| `memory/audit/decisions.jsonl` | keputusan arsitektur/non-trivial |

```bash
bash unified-integration/scripts/audit-trail.sh mcp-call "brave-search" "search" "abc123" "5 results"
bash unified-integration/scripts/audit-trail.sh video "hyperframes" "sales outreach" "def456" "/path/out.mp4" "user"
bash unified-integration/scripts/audit-trail.sh decision "add-replica-skill" "Vendor replica-skill, MIT, registrasi di pipeline agregasi"
```

Retention audit: minimum 12 bulan. Tidak ada auto-purge audit.

## 3. Data Sensitif & PII

- Tidak pernah log PII (nama, email, NIK, no rek) ke audit; mask dulu.
- Tidak expose API key ke log; hanya hash argumen.
- Tidak share data ke third-party tanpa consent.
- Dokumen sensitif (medis/legal/keuangan): model lokal bila ada; jangan pakai
  MCP cloud public.

## 4. Clean-Room Discipline (replica-skill)

Replica-skill **enforce** clean-room secara bawaan:

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

## 5. License Compliance

Setiap manifest katalog punya field `source.license`. Status:

| Plugin | License | Verifikasi |
|--------|---------|------------|
| replica-skill | MIT | **VERIFIED** (LICENSE file upstream, vendored) |
| 20 plugin lain | bervariasi (assumed MIT/Apache) | TODO — lihat docs/LICENSE_AUDIT.md |

Vendor ulang hanya untuk license permissive (MIT/Apache/BSD). GPL/AGPL:
pertimbangkan rewrite. Proprietary: jangan distribute.

## 6. Regulasi

### UU PDP (UU No. 27/2022, Indonesia)

- Pasal 22-23: consent eksplisit untuk pemrosesan data personal.
- Pasal 35: hak hapus data (purge mechanism wajib).
- Pasal 51: accountability (audit log wajib).
- Pasal 56: cross-border transfer wajib disclosure (HeyGen/ElevenLabs = US).

### GDPR (bila user EU)

- Art. 9: biometrik/voice = special category, explicit consent.
- Art. 30: records of processing (audit log).
- Art. 17: right to erasure.

## 7. Red Flags — Hentikan Segera

1. Request clone tokoh publik / Deepfake deceptive.
2. Request voice clone tanpa izin tertulis.
3. Request akses data di luar workspace.
4. MCP return data tidak relate ke query (suspicious leak).
5. Audit log berubah/hilang tanpa eskalasi.
6. Consent gate dilewati (tidak ada flag bypass; jangan buat).

## 8. Incident Response

1. Hentikan operasi.
2. Catat timestamp + scope ke `memory/audit/incidents.jsonl`.
3. Eskalasi ke user: scope, cause preliminary, action, next.
4. Purge data bila di-approve.
5. Post-mortem ke `docs/` (file baru per insiden).

## 9. Checklist Sebelum Production

- [ ] .env management siap (tidak ada hardcoded API key)
- [ ] consent-gate.sh teruji untuk semua flow multimodal
- [ ] Audit log rotation configured (> 12 bulan)
- [ ] Retention policy aktif (purge 30 hari)
- [ ] License audit selesai (lihat docs/LICENSE_AUDIT.md)
- [ ] Cross-border disclosure siap (HeyGen/ElevenLabs)
- [ ] DSAR procedure documented
- [ ] Incident response drill minimal 1x
