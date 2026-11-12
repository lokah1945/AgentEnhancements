---
slug: openmontage
category: multimedia-writing
version: 1.0.0
status: integrated-ready
mcp_servers: [ffmpeg-mcp, video-mcp]
trigger_keywords: [video, montage, edit, ffmpeg, shorts]
---

# OpenMontage

Skill video editing & montage: shot list, transition map, beat-synced cut, dan export presets untuk short-form (Reels/TikTok/Shorts). Mendukung storyboard ke timeline.

## Kapan dipakai

- User minta "edit video", "montage", "Reels", "shorts"
- Konversi rekaman mentah jadi cut pendek
- Beat-synced cut untuk musik-driven content
- Storyboard → timeline

## Prasyarat

- MCP: `ffmpeg-mcp`, `video-mcp`
- Tools: `ffmpeg`, `ffprobe`, opsional `yt-dlp` untuk ingest
- Wajib: explicit duration budget sebelum editing

## Capabilities

1. Shot list generation — pecah video jadi shot atomic (3-5s).
2. Transition planning — cut, dissolve, whip pan, dengan timing.
3. Beat-synced cutting — align cut ke BPM musik.
4. Export preset selection — Reels 1080×1920 H.264 30fps, YouTube 1920×1080, dst.

## Workflow

1. Ingest source (file / URL via yt-dlp).
2. Probe duration + codec dengan ffprobe.
3. Generate shot list: shot ID, in/out timestamp, intent (hook/b-roll/cta).
4. Bila ada musik: load audio → detect beat → align shot to beat.
5. Build timeline via `ffmpeg concat` + filter (transition).
6. Render preview low-res → tampilkan ke user.
7. Bila approve, render high-res + export preset.
8. Audit log: `unified-integration/memory/audit/video.jsonl` entry.

## Inputs

- Source video (file path atau URL)
- Opsional: audio track (untuk beat sync)
- Opsional: target platform (reels/shorts/youtube/tiktok)
- Opsional: target duration (default 60s)
- Opsional: tone (energetic / calm / dramatic)

## Outputs

- `montage-<slug>.mp4` di `download/videos/`
- `shot-list-<slug>.json` — shot metadata
- `timeline-<slug>.json` — ffmpeg command script
- `preview-<slug>.mp4` (low-res, sebelum final render)

## Contoh

### Contoh 1 — Reels 60s dari raw 5 menit

Prompt: "Edit 5 menit raw saya jadi Reels 60s, energetic."

```
ingest: raw.mp4 (5:00, 1080p, H.264)
shot list (10 shot):
  S1  00:00-00:03  hook: 'Check this out!'
  S2  00:08-00:11  b-roll: product closeup
  ...
  S10 04:55-04:58  cta: 'Follow for more'

beat sync: audio 'energetic.mp3' BPM 128 → cut setiap 0.47s
transition: cut (no dissolve) + 2 whip pan
render preview: download/videos/preview.mp4 (low-res)
approve → render final: download/videos/reels-60s.mp4 (1080×1920 H.264)
audit: audit/video.jsonl +1
```

### Contoh 2 — YouTube intro 15s

Prompt: "Buat intro YouTube 15s, calm tone."

```
ingest: branding assets (logo.mp4 + bg-music-calm.mp3)
shot list (3 shot):
  S1  0-3  logo fade in
  S2  3-9  tagline + b-roll
  S3  9-15 subscribe CTA
transition: cross-dissolve 500ms
render: download/videos/intro-15s.mp4 (1920×1080 60fps)
```

### Contoh 3 — Beat-sync cut dari concert footage

Prompt: "Sync cut footage 8 menit ke lagu 90 BPM."

```
beat detect: 90 BPM → 0.667s per beat
strategy: cut every 2 beats (1.33s)
shot list: 36 shot × 1.33s = 48s output
align S1 di beat 1, S2 di beat 3, dst
render: download/videos/concert-48s.mp4
```

## Batasan & Keamanan

- **Wajib budget duration**: bila user tidak kasih, tanya dulu.
- Bukan generate video baru dari nol — editing existing footage.
- Tidak auto-upload ke YouTube/TikTok; user upload manual.
- Tidak edit video dengan watermark copyrighted music (DMCA risk).

## Catatan integrasi

- Untuk personalized video (talking head), gunakan `hyperframes` (setelah OpenMontage selesai master cut).
- Untuk voice over, gunakan `elevenlabs-mcp` (via Hyperframes pipeline).
- Audit wajib (lihat `.cursorrules` rule 7).
- Output disimpan di `download/videos/` dengan slug unik.
