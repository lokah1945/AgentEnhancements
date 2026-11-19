---
title: Search Provider Integration
version: 2.0
last_updated: 2026-11-19
audience: users, maintainers
---


AE configures external MCP subprocesses and credential references. It does
not implement the providers' public HTTP search APIs. Authentication headers,
query fields, result shapes, quotas and pricing belong to the installed MCP
implementation and its upstream API version. Verify those upstream contracts
when selecting or updating a server.

## Repository configuration

The active search candidates and their suggested commands are declared in
`plugin-catalog/mcp-servers.json`. Plugin suggestions are recorded in their
manifests. The catalog currently references You.com, Serper, Tavily, Exa,
Firecrawl and NewsAPI; bundled Google News uses RSS and arXiv queries its
own service. Network success is independent of local installation status.

The private ignored `ui.api.json` stores MCP credential slots and connection
fields. An external server also needs an installed `command` array and `env`
reference mapping. A nonempty key alone does not install a server, complete
OAuth or prove that an external command implements the expected protocol.
Empty central slots do not inherit API credentials from the shell.

The optional ignored `search_providers.json` provides multiple key slots for
supported search-provider rotation. `api_config.py` resolves these slots and
the gateway maps the chosen credential into the external subprocess environment.
Rotation state is local to a process; it is not a distributed load balancer,
provider quota manager, automatic retry policy or account failover guarantee.

Use the current schema/template and [configuration](CONFIGURATION.md) for
reference names. Both credential files are user data and must stay private.
The repository root is discovered from the script location; an absolute
`/root/credential/` path is not required.

## Verify safely

```bash
python3 unified-integration/scripts/api_config.py status
python3 unified-integration/scripts/registry.py search "web search" --type mcp
bash unified-integration/scripts/mcp-test.sh --priority P0
```

Status reports presence and readiness without printing keys. Use synthetic
keys and isolated fixtures to inspect rotation. Never print the return value
of `get_search_provider_key()` with real configuration. The gateway has no
`--help` diagnostic interface; starting it runs the stdio protocol server.

## Readiness failures

- `missing_credentials`: populate the required private reference.
- `runtime_not_configured`: configure the installed command.
- `executable_not_installed`: verify and install the chosen executable.
- `disabled`: review the user's explicit setting.

## Upstream API documentation

Consult the selected server's own documentation and provider reference:
[You.com](https://docs.you.com/), [Tavily](https://docs.tavily.com/),
[Serper](https://serper.dev/), [Exa](https://docs.exa.ai/),
[Firecrawl](https://docs.firecrawl.dev/) and
[NewsAPI](https://newsapi.org/docs).
These references are not an AE compatibility certification or a statement of
current plan quotas. See the [MCP deployment
checklist](MCP_INTEGRATION_CHECKLIST.md)
for installation and authorization checks.
