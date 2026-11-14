# task-router-mcp

Sub-agent task dispatch + progress tracking for orchestrator skills
(gsd, bmad-method, rea). Catalog entry: `plugin-catalog/mcp-servers.json`
→ `task-router-mcp` (P1, task).

## Tools

| Tool | Args | Returns |
|------|------|---------|
| `health` | — | executor stats |
| `dispatch` | `kind` ("bash"\|"python"), `command` \| `code`, `timeout?` (1..600s) | `{task_id, status}` |
| `track` | `task_id` | full entry: status, exit_code, stdout/stderr tails, duration |
| `cancel` | `task_id` | cancellation result |
| `list_tasks` | — | every known task id + status |

## Semantics

- Each task runs in its own temp workspace (`/tmp/ae-task-<id>-*/`) with a
  hard timeout (default 60 s, max 600 s).
- 4 worker threads; excess tasks stay `queued`.
- stdout/stderr are tail-truncated to 4,000 chars to bound context size.
- **Best-effort denylist guard** refuses obviously destructive bash
  commands (`rm -rf /`, `mkfs`, `dd if=`, fork bombs, raw disk writes,
  shutdown/reboot). This is a guardrail, not a sandbox.

## Env vars

None required.

## Run

```bash
python3 unified-integration/mcp-servers/task-router-mcp/server.py   # stdio
```

## Test

Covered by `unified-integration/tests/test_mcp_servers.py`
(dispatch → done with stdout; python kind; denylist refusal;
unknown-id tracking; timeout path).
