---
title: MCP Server Roadmap
version: 2.0
last_updated: 2026-11-19
audience: all agents and maintainers
---


The canonical roadmap is `plugin-catalog/mcp-servers.json`. Its `status`,
`priority`, `for_plugins` and credential-reference fields describe the catalog.
[Generated counts](CAPABILITY_COUNTS.md) distinguish catalog implementation
status from bundled Python backends and default enablement. Plugin dependency
suggestions live in `plugin-catalog/catalog.json` and each plugin manifest;
they are guidance, not proof an upstream is installed.

Setup configures one native `agent-enhancements` gateway for selected hosts.
The gateway loads bundled backends and configured external subprocesses.
Claude uses its native user-scope `.claude.json`; Codex uses `config.toml`;
OpenCode uses `opencode.json(c)`; selected Hermes profiles use `config.yaml`.
Existing host configuration and tool approvals are preserved.

## Availability

The private root `ui.api.json` controls MCP credentials, command arrays and
reference mappings. Missing or malformed configuration disables cloud access;
empty values do not inherit API credentials from the shell. Local tools can
remain available with keys empty. Runtime status is recomputed and every call
rechecks current configuration, including after a credential is revoked.

External candidates require an installed executable, the correct arguments,
credentials and completed authorization. `agent_browser` is cataloged as built
but remains an external runtime. Package names in the roadmap are not a
certification that the package exists or is safe to install.

Task router is hidden until explicitly enabled in `ui.api.json`. Its command
execution has the user's privileges. Host permissions remain the execution
boundary. Vision semantic description sends image data to its configured
provider; comparison and OCR are local. See [safety](SAFETY.md).

## Verify an installation

```bash
python3 unified-integration/scripts/api_config.py status
bash unified-integration/scripts/setup-mcp.sh --check
bash unified-integration/scripts/mcp-test.sh --priority P0
bash unified-integration/scripts/mcp-test.sh --for-plugin replica-skill
```

The protocol check exercises bundled backends and the gateway. External
readiness and successful upstream calls need separate checks. The audit-trail
utility is available explicitly; memory hooks record tool names, not complete
MCP payloads or an automatic audit of every SDK call.

See [configuration](CONFIGURATION.md), [deployment
checklist](MCP_INTEGRATION_CHECKLIST.md)
and [credential references](ENV_VARS.md).

### Browser profile storage

The optional agent-browser backend is disabled in a fresh configuration
until its Node dependencies and Chromium are installed deliberately.
Its default profiles are under `.agentenhancements/cache/browser/profiles`
in the checkout. Each custom profile root owns its session index; directories
are0700 and index files0600. Session identifiers cannot traverse outside
the profile directory. `npm --prefix mcp-servers/agent_browser test` runs
offline storage and boundary regressions; live browser flows still need
Chromium and a separately configured runtime.
