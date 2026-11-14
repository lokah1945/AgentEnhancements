# style-mcp

AI-ism detection + de-clichéing for the humanizer skill. Catalog entry:
`plugin-catalog/mcp-servers.json` → `style-mcp` (P2, writing).

Pure Python, offline, deterministic. 18 weighted patterns across four
families: cliches (`delve into`, `tapestry`, `a testament to`…), fillers
(`it is important to note that`, `in conclusion`…), hedges
(`it seems that`, `arguably`) and tells (rule-of-three overuse, em-dash
overflow, adverb boosters, `as an AI`).

## Tools

| Tool | Args | Returns |
|------|------|---------|
| `health` | — | pattern count + mode |
| `score` | `text` | `{score 0-100, verdict, findings[]}` with concrete suggestions |
| `rewrite` | `text` | mechanically de-clichéed text + before/after scores + `remaining_findings` |
| `patterns` | — | the full pattern catalogue (weights, auto-rewritability) |

`rewrite()` only applies substitutions that are provably safe; anything
still flagged in `remaining_findings` needs human judgment - by design,
no regex silently rewrites your argument.

## Env vars

None required.

## Run

```bash
python3 unified-integration/mcp-servers/style-mcp/server.py   # stdio
```

## Test

Covered by `unified-integration/tests/test_mcp_servers.py`
(score an AI-flavored paragraph < score a plain one; rewrite removes
fillers; patterns listing consistent).
