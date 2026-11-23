# Security Policy

## Supported versions

Only the current `master` branch of AgentEnhancements receives security
fixes. Older commits and archived branches (for example the
`archive/windows-2026-11` tag) are not maintained.

## Reporting a vulnerability

Please do **not** open a public issue for a suspected vulnerability.
Report it privately through GitHub's
[private vulnerability reporting](https://github.com/lokah1945/AgentEnhancements/security/advisories/new)
for this repository. Include:

- the affected file(s) and commit,
- steps to reproduce or a proof of concept,
- the impact you observed or expect.

You will receive an acknowledgement within 5 working days. Confirmed
issues are fixed on `master` with a regression test, and the fix is
recorded in [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Scope

In scope: the owned integration layer (`unified-integration/`, `scripts/`,
`mcp-servers/`, `.github/`, the root setup and update scripts) and the way
it handles credentials from `ui.api.json`, host configuration files and
hook payloads.

Vendored upstream projects (`ECC/`, `headroom/`, `claude-mem/`,
`agentic-awesome-skills/`, `anthropic-skills/`, `superpowers/`,
`agency-agents/`, `ponytail/` and the other directories listed in
[LICENSE](LICENSE)) should be reported upstream first; we re-vendor the
fixed release.

## Handling secrets

- Credentials live only in the private, git-ignored `ui.api.json`
  (see [docs/CONFIGURATION.md](docs/CONFIGURATION.md)). Never commit it.
- Dependencies are scanned by
  [dependency-audit.yml](.github/workflows/dependency-audit.yml) and kept
  current by Dependabot.
- Security design notes and past audits are indexed in
  [docs/audit/README.md](docs/audit/README.md) and
  [docs/SAFETY.md](docs/SAFETY.md).
