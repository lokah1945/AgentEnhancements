---
slug: hyperframes
category: multimedia-writing
version: 1.0.0
status: integrated-ready
mcp_servers: [heygen-mcp, elevenlabs-mcp, voice-clone-mcp]
trigger_keywords: [avatar, hyperframes, talking head, personalized video]
---

# Hyperframes

Skill avatar/video personalized: generate hyper-personalized talking-head clips dengan template variables, voice cloning safety guardrails, dan multi-lingual lip-sync.

## Kapan dipakai

- User minta "personalized video", "talking head", "voice clone"
- Outbound sales dengan nama prospect
- Training video dengan persona custom
- Multi-bahasa lip-sync untuk regional reach

## Prasyarat

- MCP: `heygen-mcp`, `elevenlabs-mcp`, `voice-clone-mcp`
- Tools: `bash`, `web_fetch`
- **WAJIB**: consent gate sebelum voice cloning

## Capabilities

1. Talking-head video generation — avatar custom atau template.
2. Variable personalization — nama, perusahaan, angka spesifik.
3. Voice-clone safety gates — explicit consent + audit.
4. Multi-lingual lip-sync — dubbing ke 30+ bahasa.

## Workflow

1. **Consent gate** (WAJIB pertama):
   - Tampilkan prompt: "Voice cloning requested for `<purpose>`. Approved? (y/n)"
   - Bila tidak y: refuse, log refusal.
   - Bila ya: log approval ke `audit/consent.jsonl`.
2. **Voice clone** (jika perlu):
   - Upload voice sample ke elevenlabs-mcp.
   - Dapatkan voice ID.
3. **Avatar setup**:
   - Pilih template atau upload custom avatar.
4. **Script generation**:
   - Personalize template dengan variabel (nama, angka).
5. **Generate**:
   - Kirim script + voice ID ke heygen-mcp.
   - Tunggu render (estimasi 30-90 detik).
6. **Multi-bahasa** (opsional):
   - Translate script + lip-sync ulang.
7. **Audit**:
   - Log: timestamp, plugin, intent, input_hash, output_path, approved_by.
8. **Output**: video disimpan di `download/videos/`.

## Inputs

- Script template (dengan placeholder `{{name}}`, `{{company}}`)
- Variabel {name, company, ...}
- Voice sample (untuk clone) atau voice ID existing
- Avatar template ID atau custom avatar path
- Opsional: target bahasa untuk dubbing

## Outputs

- `personalized-<id>.mp4` di `download/videos/`
- `audit/consent.jsonl` entry
- `audit/video.jsonl` entry
- `voice-id.json` (bila clone baru)

## Contoh

### Contoh 1 — Sales outbound 100 prospect

Prompt: "Personalized video untuk 100 prospect: 'Hi {{name}}, saya lihat {{company}} pakai {{tool}}, mungkin saya bisa bantu.' Use my voice."

```
CONSENT GATE:
  "Voice cloning requested for: sales outreach to 100 prospects.
   Voice source: my_voice_sample.wav (3 minutes).
   Approve? (y/n)" -> y (user confirmed)

approval logged: audit/consent.jsonl {ts, purpose, sample_hash, approved_by}
voice clone: elevenlabs-mcp -> voice_id 'v_xxx_001'
script: 100 personalized variant

batch generate (100 video):
  v1: 'Hi John, saya lihat Acme pakai Salesforce...'
  v2: 'Hi Sarah, saya lihat Globex pakai HubSpot...'
  ...

output: download/videos/personalized-001.mp4 ... 100.mp4
audit: audit/video.jsonl +100 entries
total time: ~90 menit (parallel 5)
```

### Contoh 2 — Multi-bahasa training video

Prompt: "Buat training video dalam 5 bahasa (id, en, ja, ko, es) dari script Inggris."

```
CONSENT GATE:
  "Voice cloning requested for: training video localization to 5 languages.
   Voice source: trainer_voice.wav.
   Approve? (y/n)" -> y

voice clone: 5 voice ID (1 per language)
script translate: en -> {id, ja, ko, es} via deep translate
generate: 5 video, lip-sync masing-masing
output: download/videos/training-{id,en,ja,ko,es}.mp4
```

### Contoh 3 — Single personalized video (no clone)

Prompt: "Buat video ucapan selamat ke Budi, pakai template avatar 'professional-man-1', voice default."

```
NO CONSENT GATE NEEDED (no voice clone, default voice)
script: 'Hi Budi, selamat ulang tahun! Semoga sehat selalu.'
avatar: template professional-man-1
voice: default 'id-male-1'
generate: download/videos/budi-birthday.mp4
audit: video.jsonl +1
```

## Batasan & Keamanan

- **Consent gate WAJIB** sebelum voice cloning (UU PDP Indonesia pasal 22-23, GDPR Art 9).
- Voice sample wajib milik user atau dengan izin tertulis.
- Tidak clone voice selebritas / tokoh publik tanpa izin tertulis.
- Audit trail wajib: timestamp, purpose, sample hash, approver, output path.
- Retention: video disimpan 30 hari default, lalu dihapus bila tidak dipakai.
- Untuk minor (< 18), consent wajib dari wali.

## Catatan integrasi

- Setelah `openmontage` selesai master cut, gunakan Hyperframes untuk personalized variant.
- Untuk script writing, gunakan `humanizer` agar natural (bukan AI-sounding).
- Untuk compliance review, gunakan `anthropic-skills` baseline.
- Audit log di `unified-integration/memory/audit/` — wajib dipertahankan ≥ 12 bulan.
