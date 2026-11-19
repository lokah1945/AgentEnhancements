---
title: MCP Integration Checklist
version: 2.0
last_updated: 2026-11-19
audience: platform engineers
---


Use the [generated capability inventory](CAPABILITY_COUNTS.md) for catalog,
implementation-status and bundled-backend counts. The canonical roadmap is
`plugin-catalog/mcp-servers.json`; it describes candidates and dependencies.
A `built` status is separate from installation, host permissions, working
authentication and connectivity. Suggested upstream package commands require
verification before installation.

## Prepare the shared runtime

- [ ] Run `bash unified-integration/scripts/setup-mcp.sh --prepare`.
- [ ] Run `bash unified-integration/setup.sh` for the selected native hosts.
- [ ] Run `bash unified-integration/scripts/setup-mcp.sh --check` to exercise
  the bundled backends and gateway through the actual stdio protocol.
- [ ] Inspect `python3 unified-integration/scripts/api_config.py status` for
  readiness reasons. The command reports presence, never credential values.

Use the prepared interpreter and `unified-integration/requirements.txt`.
An unconstrained installation of `mcp` or `fastmcp` can select an incompatible
SDK; avoid a separate global Python environment.

## Enable an external server when a task needs it

- [ ] Identify its exact catalog ID and the plugin's actual dependency.
- [ ] Verify the upstream implementation, license, install command, version,
  argument contract and required account authorization.
- [ ] Install the implementation deliberately. Setup does not automatically
  install every external candidate or execute commands from the roadmap.
- [ ] Add an installed `command` array and credential-reference `env` mapping
  under that ID in the private root `ui.api.json`.
- [ ] Complete OAuth where needed; client IDs/secrets alone are insufficient.
- [ ] Restrict filesystem roots and preserve the host's tool approvals.
- [ ] Verify `api_config.py status`, the host's tool list and a local fixture
  call. Clearing a required credential must revoke subsequent calls.

Search candidates include You.com, Serper, Tavily, Exa and Firecrawl. Brave
Search has been removed from the active catalog. Bundled Google News and
arXiv require network access for successful searches despite needing no key.
`agent_browser` is marked built in the catalog but is an external executable;
it is not an additional bundled Python backend.

## Check bundled implementation behavior

- [ ] Embeddings default to deterministic local vectors; cloud backend use
  requires its configured key and endpoint.
- [ ] Vision comparison/OCR remain local. Semantic description is hidden
  without the cloud key; review image-upload consent before enabling it.
- [ ] GraphRAG stores local evidence and does not require an OpenAI key.
- [ ] Task router remains hidden by default and requires explicit opt-in.
  It executes commands with the user's privileges; host permissions apply.
- [ ] Media tools need their installed local executables, such as ffmpeg or
  tesseract. Installation status is not proof every operation will succeed.

## Regenerate and verify the published inventory

```bash
bash scripts/scaffold_modular_skills.sh
python3 scripts/generate_skills_index.py
python3 unified-integration/scripts/catalog-validate.py --root .
python3 scripts/generate_capability_counts.py --write
python3 scripts/generate_capability_counts.py --check
runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
"$runtime_python" unified-integration/tests/run-tests.py
```

Keep static implementation status in manifests. Runtime readiness is computed
from the current installation and private configuration; do not change a
catalog status to `installed` as a substitute for that runtime check.

See [configuration](CONFIGURATION.md), [MCP overview](MCP_SERVERS.md),
[credential reference](ENV_VARS.md) and [safety guidance](SAFETY.md).
