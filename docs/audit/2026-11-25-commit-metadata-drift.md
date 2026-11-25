---
title: Commit metadata drift and template conflict
version: 1.0
last_updated: 2026-11-25
audience: maintainers, contributors
---

# Commit metadata drift and template conflict

## Finding

`CONTRACT.md` requires a session-id trailer on every agent commit, but the
recent history uses an email address. The contract also contains two
different body formats.

## Evidence

- `CONTRACT.md:121-124` (R205): `Co-Authored-By: <agent-name> <session-id>`.
- `CONTRACT.md:125-128` (R206): a single body line
  `Agent: <agent-name> | Session: <id> | Task: <description>`.
- `CONTRACT.md:511-522` (§12.3): four separate body lines
  `Agent:`, `Session:`, `Task:`, `Context:` plus the same trailer as R205.
- `git log --format=full` before this work (commits `312cb802`, `a6cf8720`,
  `c7647980`, `095fc19d`, `41d7eabb`): all five ended with
  `Co-Authored-By: Claude Code <noreply@anthropic.com>`, used separate
  `Agent:`/`Session:`/`Task:` lines, and omitted `Context:`. Commits created
  by this remediation use the contract form (`Agent: OpenCode`, `Context:`,
  `Co-Authored-By: OpenCode <ses_...>`).
- `docs/CONTRIBUTING.md:49-56` shows the pipe-delimited R206 body form with
  `Co-Authored-By: Claude Code <abc123>`.
- CI checks are advisory only (`.github/workflows/ci.yml:105-112`).

## Resolution applied

No binding text was edited and no history was rewritten: CONTRACT §End forbids
unapproved overrides and R204 forbids force-push to main. All new commits use
the format both R205 and §12.3 agree on — separate `Agent:` / `Session:` /
`Task:` / `Context:` lines and `Co-Authored-By: <agent-name> <session-id>` —
which satisfies the stricter reading without a CONTRACT amendment.

## Open item for maintainers

R206's pipe-delimited body and §12.3's four-line body disagree. Choose one as
canonical in a maintainer-approved §10 change, then align
`docs/CONTRIBUTING.md` and the advisory CI check. Until then, contributors
should use the §12.3 form (also used by recent history).

## Cost if wrong

If maintainers prefer the email-style trailer, the new commits differ from
past convention but still match CONTRACT; a mechanical trailer edit can fix
future commits without any history change. If maintainers prefer R206's body,
future commits need a one-line body change after the canonical decision.
