# video-mcp

Shot-list / timeline semantics layered on ffmpeg for openmontage and
hyperframes. Catalog entry: `plugin-catalog/mcp-servers.json` →
`video-mcp` (P2, media).

## Tools

| Tool | Args | Notes |
|------|------|-------|
| `health` | — | ffmpeg availability + timeline count |
| `timeline` | `name`, `clips[] {path, start, end, text?, position?}` | create/replace; validates paths + in/out points offline |
| `edl` | `name` | export edit-decision-list (JSON + human-readable) |
| `render` | `name`, `out` (.mp4) | one ffmpeg invocation: trim → scale/pad 720p → drawtext → concat |

Timelines persist in `/tmp/ae-video-mcp/timelines.json`.
`timeline()` + `edl()` work offline; `render()` needs the ffmpeg binary.

## Env vars

None required.

## Run

```bash
python3 unified-integration/mcp-servers/video-mcp/server.py   # stdio
```

## Test

Covered by `unified-integration/tests/test_mcp_servers.py`
(timeline validation, EDL export; real render of a lavfi test clip
when ffmpeg is present).
