# AgentEnhancements Contribution Contract

## 1. Purpose
This contract defines the standards for contributing to AgentEnhancements — a centralized system prompt / skill registry for AI-assisted development.

## 2. Scope
Applies to all contributions: skills, MCP servers, scripts, documentation, tests, configuration.

## 3. Skill Standards ( §3.1–3.5 )

### 3.1 Frontmatter Required
Every `SKILL.md` must begin with YAML frontmatter:
```yaml
---
slug: kebab-case-slug
category: code|multimedia-writing|research|tokens-optimization|design|agency
version: MAJOR.MINOR.PATCH
status: draft|stable|deprecated
mcp_servers: []  # list of MCP server slugs this skill needs
trigger_keywords: ["keyword1", "keyword2"]  # for registry discovery
---
```

### 3.2 Section Structure (7 sections, in order)
1. **Kapan dipakai** — when to load this skill (triggers, file patterns, phrases)
2. **Prasyarat** — prerequisites: tools, languages, env vars, prior knowledge
3. **Capabilities** — numbered list (max 7), each one testable
4. **Workflow** — step-by-step procedure
5. **Inputs** — what the skill consumes
6. **Outputs** — what the skill produces
7. **Contoh** — minimum 2 worked examples with runnable code/commands

### 3.3 Capability Limit
Max 7 capability bullets. If more needed → split into multiple skills.

### 3.4 Examples Mandatory
At least 2 examples per skill. Each must be:
- Runnable (code snippet or exact CLI commands)
- Realistic (not foo/bar)
- Verifiable (produces observable output)

### 3.5 Test Coverage
Every skill must have a regression test at:
`unified-integration/tests/test_<slug>.py`

Test must:
- Import/load the skill
- Verify frontmatter parses
- Invoke at least one capability (mocked if external deps)
- Assert expected output structure

## 4. MCP Server Standards ( §4.1–4.6 )

### 4.1 FastMCP Pattern Required
Use `fastmcp` or MCP SDK. Decorator-based tool registration.

### 4.2 Tool Declaration
Every tool must have:
- `name`: snake_case, descriptive
- `description`: one sentence, user-facing
- `input_schema`: valid JSON Schema (auto-generated from type hints preferred)

### 4.3 Idempotency
Tools should be idempotent where possible. Same input → same output. No side effects on failure.

### 4.4 Secret Handling
- **Never** log, print, or echo API keys, tokens, passwords
- **Never** commit credentials to git
- Use environment variables only
- Pass secrets to subprocesses via env, never CLI args

### 4.5 Health Tool Mandatory
Every MCP server must expose a `health` tool returning `{"status": "ok", "server": "<name>"}`.

### 4.6 Registry Entry
Document required env vars in `plugin-catalog/mcp-servers.json`.

## 5. Code Quality ( §5.1–5.4 )

### 5.1 Minimal by Default (Karpathy)
- Functions ≤ 30 lines
- Rule of Three: no abstraction until 3× duplication
- No dependency until stdlib insufficient
- Prefer 5 lines, 0 deps over 50 lines with framework
- Vectorize with NumPy/PyTorch; no Python `for` loops over data

### 5.2 No-Bullshit Review
- Point at abstractions/interfaces/config layers that don't earn their keep
- Prefer **deleting** over **refactoring**
- Never praise "clean code" — only praise shorter, faster, or more correct code

### 5.3 Verify by Execution
- Run the code; show the output
- Fail fast on missing prerequisites (env var, MCP server, file)
- Idempotent scripts: safe to re-run, use merge semantics
- Deterministic output: sort listings by name

### 5.4 Post-Coding Checklist
- Re-open and read back written files
- Static checks: `bash -n`, `py_compile`, `python3 -m json.tool`
- Search for placeholders: `XXX`, `TODO`, `FIXME`, `待补充`, `【…】`
- Visual check rendered documents (PDF/PNG)

## 6. Hygiene Rules (Non-Negotiable)

### 6.1 Secrets
Never print/log/echo credentials. Never commit to git. Use env vars or credential stores.

### 6.2 Filesystem
Write only under project root or user's explicit target. Never write to `~`, `/etc`, `/usr`, system dirs. Temp files → `/tmp/<namespace>/` with cleanup.

### 6.3 External Effects
- Browser automation: localhost/test fixtures only. No production without consent.
- Voice/video cloning: consent gate mandatory.
- Network calls: exponential backoff, no tight loops.
- Email/Slack/Linear/GitHub writes: dry-run by default, confirm before mutate.

### 6.4 Vendored Code
Never modify vendored upstream code in place (`anthropic-skills/`, `replica-skill/`, `ECC/`, etc.). File issues upstream; vendored copy stays pristine until documented re-vendor (see `docs/UPDATING.md`).

## 7. Communication Style

### 7.1 Replies
Concise, concrete (names, paths, numbers, commands), honest about uncertainty, cite sources.

### 7.2 Code Comments
Explain **why**, not **what**. Docstrings ≤3 lines. No commented-out code.

### 7.3 Documents
Paragraphs 3–5 sentences. Lists one item per line, left-aligned. No "End of Report". Placeholders only for genuinely missing info.

## 8. Quality Bar for Deliverables

| Artifact | Acceptance Criteria |
|----------|---------------------|
| Code script | Runs end-to-end with `set -euo pipefail` / `try-except`; static checks pass; non-empty output |
| Document (docx/pdf) | Re-opened with python-docx / pdfplumber; headings + tables + image counts printed; no placeholders |
| Spreadsheet | Re-opened with openpyxl; sheet count + chart count + formula sample printed |
| Slides | Slide count verified; speaker-notes presence checked |
| Chart | Non-blank verified (non-white pixel ratio > 0.05); Chinese fonts render |
| MCP server | `health` tool responds; idempotency test passes; no secret logging |

## 9. When Stuck
1. Re-read relevant `SKILL.md`
2. Check `docs/audit/E2E_AUDIT_2026-11.md` — known footguns documented
3. Run `registry.py map "<task>"` — maybe different skill fits
4. Ask user — one clarifying question beats one wrong deliverable

## 10. Pointers
- Modular skill tree: `skills/<category>/<slug>/SKILL.md`
- Catalog: `plugin-catalog/catalog.json`
- MCP roadmap: `plugin-catalog/mcp-servers.json`
- MCP build checklist: `docs/MCP_INTEGRATION_CHECKLIST.md`
- Setup pipeline: `unified-integration/setup.sh`
- Test suite: `unified-integration/tests/` (236 tests)
- Audit report: `docs/audit/E2E_AUDIT_2026-11.md`

## 11. Versioning
Skills use SemVer. Breaking changes → major bump. Catalog auto-rebuilds on `registry.py rebuild`.

## 12. Git Discipline

### 12.1 Branching
- `main` = stable, deployable
- Feature branches: `feat/<slug>`, `fix/<slug>`, `skill/<slug>`
- No direct pushes to `main`

### 12.2 Commits
Conventional Commits format:
```
<type>(<scope>): <subject>

<body>

<footer>
```
Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `skill`
Scope: skill slug or component (e.g., `skill/karpathy-skills`, `registry`)

### 12.3 Commit Message Format (Strict)
```
skill(karpathy-skills): add vectorization capability

- Add Capability 3: vectorization with NumPy/PyTorch
- Add Example 2: softmax implementation
- Update test_karpathy-skills.py

Closes #42
```
**Required**: type(scope), imperative subject, blank line, bullet body, footer with issue ref.

## 13. Review Process
All changes require review. Reviewer checks:
- Contract compliance (§3–§8)
- Tests pass (`python3 -m pytest unified-integration/tests/`)
- Catalog rebuilds (`registry.py rebuild`)
- No secrets, no vendored modifications

## 14. License
Contributions licensed under project license (MIT unless specified). Contributors retain copyright.

---

*End of Contract. Last updated: 2026-11-21*