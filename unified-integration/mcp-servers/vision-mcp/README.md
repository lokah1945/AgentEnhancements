# vision-mcp

Multimodal image understanding for anthropic-skills, impeccable,
replica-skill. Catalog entry: `plugin-catalog/mcp-servers.json` →
`vision-mcp` (P1, core).

## Tools

| Tool | Args | Backend |
|------|------|---------|
| `health` | — | PIL / tesseract / key availability (booleans only) |
| `compare` | `a`, `b` | offline PIL (histogram + pixel diff) |
| `ocr` | `image_path`, `lang?=eng` | tesseract binary |
| `describe` | `image_path`, `detail?` | `gpt-4o-mini` vision with key; honest `basic_metadata` fallback without |

The `describe` response always carries a `mode` field (`openai` /
`basic_metadata`) so callers know exactly which path produced the result —
metadata mode never fabricates a semantic description.

## Env vars

| Var | Required | Purpose |
|-----|----------|---------|
| `OPENAI_API_KEY` | for semantic describe | OpenAI vision (read at call time, never logged) |

## Run

```bash
python3 unified-integration/mcp-servers/vision-mcp/server.py   # stdio
```

## Test

Covered by `unified-integration/tests/test_mcp_servers.py`
(compare between two generated images; ocr on a rendered text image;
describe basic_metadata mode; error envelopes).
