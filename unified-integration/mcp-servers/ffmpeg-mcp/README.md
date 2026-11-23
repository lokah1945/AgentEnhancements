# ffmpeg-mcp

Non-linear video editing via ffmpeg for the openmontage skill. Catalog
entry: `plugin-catalog/mcp-servers.json` → `ffmpeg-mcp` (P1, media).

## Tools

| Tool | Args | Notes |
|------|------|-------|
| `health` | — | ffmpeg/ffprobe availability + allowed roots |
| `probe` | `path` | duration, codec, resolution, audio streams |
| `cut` | `path`, `start`, `end`, `out` | stream copy (fast, lossless) |
| `concat` | `paths[]`, `out` | concat demuxer (same codec clips) |
| `transcode` | `path`, `codec?=libx264`, `out?` | re-encode video, copy audio |
| `extract_audio` | `path`, `out` | AAC audio track |
| `thumbnail` | `path`, `t?=0.0`, `out?` | single frame .jpg |

## Path policy

Inputs/outputs must resolve inside an **allowed root**: the process cwd and
`/tmp` by default. Extend with `AE_FFMPEG_ALLOWED_ROOTS="/data/videos:/mnt"`.
All writes use `ffmpeg -y` → re-running the same call is idempotent.
ffmpeg writes into a private staging directory next to `out`; only a
fresh, non-empty result replaces `out` (atomic `os.replace`). A failed run
(bad codec, no audio stream, timeout, or no output at all, e.g.
`cut`/`thumbnail` past the end of the media) reports an error, not `ok`,
and leaves any existing file at `out` untouched, so a stale file is never
mistaken for the new result. `out` must differ from the input file(s) and
must not be a directory.

## Env vars

| Var | Required | Purpose |
|-----|----------|---------|
| `AE_FFMPEG_ALLOWED_ROOTS` | no | extra allowed roots (`:`-separated) |

## Run

```bash
python3 unified-integration/mcp-servers/ffmpeg-mcp/server.py   # stdio
```

## Test

Covered by `unified-integration/tests/test_mcp_servers.py` (generates a
real test clip with ffmpeg lavfi, then probes/cuts/concats/extracts —
skipped automatically when the ffmpeg binary is absent).
