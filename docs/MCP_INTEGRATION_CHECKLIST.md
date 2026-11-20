# MCP Integration Checklist

Use this checklist when building a new MCP server for AgentEnhancements.

## Pre-Development
- [ ] **Skill loaded**: Read `skills/multimedia-writing/anthropic-skills/skills/mcp-builder/SKILL.md`
- [ ] **Requirements clear**: List all tools, resources, prompts needed
- [ ] **Env vars documented**: Every secret/config as `${VAR_NAME}` in `mcp-servers.json`
- [ ] **Transport chosen**: stdio (default) or HTTP/SSE
- [ ] **Language/runtime selected**: Python (FastMCP) or TypeScript (MCP SDK)

## Implementation

### Server Structure
- [ ] `server.py` / `main.py` entrypoint
- [ ] `pyproject.toml` / `package.json` with deps
- [ ] `README.md` with usage, env vars, tool list
- [ ] `.gitignore` excluding `__pycache__`, `.venv`, `node_modules`

### Tools (each tool must have)
- [ ] **Name**: snake_case, descriptive (e.g., `get_repo`, `search_code`)
- [ ] **Description**: One sentence, user-facing, explains what it returns
- [ ] **Input Schema**: Valid JSON Schema (auto from type hints preferred)
- [ ] **Idempotency**: Safe to retry; no side effects on failure
- [ ] **Error Handling**: Structured errors, no secret leakage
- [ ] **Timeouts**: Network calls have reasonable timeouts (10–30s)
- [ ] **Retries**: Exponential backoff for transient failures

### Mandatory Health Tool
- [ ] `@mcp.tool()` def `health()` → `{"status": "ok", "server": "<name>"}`
- [ ] Responds in <100ms
- [ ] No auth/externals required

### Secrets & Config
- [ ] **No hardcoded secrets** — ever
- [ ] All secrets via `os.getenv("VAR_NAME")`
- [ ] Required vars documented in `plugin-catalog/mcp-servers.json`
- [ ] Optional vars have sensible defaults
- [ ] Validate required vars at startup, fail fast with clear message

### Logging
- [ ] Structured logging (JSON) to stderr
- [ ] **Never log secrets** — redact tokens, keys, passwords
- [ ] Log level configurable via `LOG_LEVEL` env var
- [ ] Request/response logging at DEBUG level only

## Testing

### Unit Tests
- [ ] Each tool tested in isolation (mock externals)
- [ ] Input schema validation tested
- [ ] Error paths tested
- [ ] Idempotency verified (call 2×, same result)

### Integration Tests
- [ ] `mcp dev server.py` starts without error
- [ ] `health` tool responds correctly
- [ ] All declared tools callable via MCP protocol
- [ ] Real external API calls work (with test credentials)
- [ ] Concurrent requests handled correctly

### Contract Tests
- [ ] `test_<slug>.py` in `unified-integration/tests/`
- [ ] Verifies server starts, health passes, tools listed
- [ ] Runs in CI pipeline

## Documentation

### plugin-catalog/mcp-servers.json Entry
- [ ] `command`, `args` correct for production install
- [ ] `env` object with all required/optional vars
- [ ] `description` clear and concise
- [ ] `tools` array matches actual tool names
- [ ] `status`: `available` | `planned` | `deprecated`

### User-Facing Docs
- [ ] `README.md` in server directory
- [ ] Quickstart: install, configure, run
- [ ] Tool reference table (name, description, params)
- [ ] Troubleshooting common issues
- [ ] Example `.env` file template

## Deployment

### Packaging
- [ ] Published to PyPI / npm (if public)
- [ ] Version pinned in `mcp-servers.json`
- [ ] Release notes for breaking changes
- [ ] SemVer followed

### Runtime
- [ ] Runs as non-root user
- [ ] Resource limits (memory, CPU) configured
- [ ] Health check endpoint exposed (if HTTP transport)
- [ ] Logs aggregated / rotated
- [ ] Graceful shutdown on SIGTERM

## Post-Deployment
- [ ] Monitor health tool success rate
- [ ] Alert on error rate >1%
- [ ] Track tool usage metrics
- [ ] Regular dependency updates (security)
- [ ] Deprecation timeline communicated

---

## Quick Reference: FastMCP Template

```python
# server.py
from fastmcp import FastMCP
import os
import httpx

mcp = FastMCP("my-server")

@mcp.tool()
def health() -> dict:
    return {"status": "ok", "server": "my-server"}

@mcp.tool()
def my_tool(param: str) -> dict:
    """Description of what this tool does."""
    api_key = os.getenv("MY_API_KEY")
    if not api_key:
        raise ValueError("MY_API_KEY not set")
    # ... implementation
    return {"result": "data"}

if __name__ == "__main__":
    mcp.run()
```

```toml
# pyproject.toml
[project]
name = "mcp-my-server"
version = "0.1.0"
dependencies = ["fastmcp", "httpx"]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

```json
// plugin-catalog/mcp-servers.json entry
{
  "my-server": {
    "command": "python",
    "args": ["-m", "mcp_my_server"],
    "env": {
      "MY_API_KEY": "${MY_API_KEY}"
    },
    "description": "One-line description",
    "tools": ["health", "my_tool"],
    "status": "available"
  }
}
```

---

## Review Gate
Before merging, ensure:
- [ ] All checklist items ✅
- [ ] `python3 -m pytest unified-integration/tests/test_<slug>.py` passes
- [ ] `registry.py rebuild` updates catalog correctly
- [ ] No secrets in code, logs, or config
- [ ] Peer review completed

*Checklist version: 2026-11-21*