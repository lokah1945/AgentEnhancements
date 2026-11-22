---
title: Audit records index
version: 1.0
last_updated: 2026-11-23
audience: maintainers, release reviewers
---

## Audit records index

### Current status

[ENTERPRISE_RELEASE_2026-11-23.md](ENTERPRISE_RELEASE_2026-11-23.md) is the
only current release-status document. Its list of open gates (live-model
evidence, Mode 2 timeouts, coverage, vendored licenses and maintainer
approval) takes precedence over any readiness claim elsewhere.

### Historical records

Every other file in this directory is a dated historical record. These
files are kept for traceability and are not updated after the fact.
Reports that claimed production readiness carry a "superseded" banner.

The same applies to:

- [`AuditReport/`](../../AuditReport/), the dated benchmark, remediation
  and reconciliation reports from 2026-11-17 to 2026-11-20, plus their
  `evidence/` JSON.
- [`mcp-servers/agent_browser/AUDIT_REPORT.md`](../../mcp-servers/agent_browser/AUDIT_REPORT.md),
  the 2026-11-19 audit of the agent_browser server.

When a historical report contradicts the current documentation or code,
the current documentation and code are correct.
