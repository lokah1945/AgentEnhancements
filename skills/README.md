# AgentEnhancements — Modular Skills Tree

Self-contained skill directory consumed by `unified-integration/setup.sh`
and any MCP-compatible agent (Claude Code, Codex, Cursor, etc.).

## Layout

```
skills/
├── manifest.json                    # aggregator index (read this first)
├── README.md                        # this file
├── code/
│   ├── README.md                    # Code category overview
│   └── agent-skills-addyosmani/                # Agent Skills (Addy Osmani)
│   └── karpathy-skills/                # Andrej Karpathy Skills
│   └── mattpocock-skills/                # Matt Pocock Skills
│   └── replica-skill/                # Replica Skill (11 sub-skills) (vendored)
├── research/
│   ├── README.md                    # Research category overview
│   └── agent-reach/                # Agent-Reach
│   └── graphify/                # Graphify
│   └── last-30-days/                # Last 30 Days
│   └── rea/                # REA (Reverse Engineer Anything)
│   └── understand-anything/                # Understand Anything
├── tokens-optimization/
│   ├── README.md                    # Tokens / Optimization category overview
│   └── bmad-method/                # BMAD Method
│   └── caveman/                # Caveman
│   └── gsd/                # Get Shit Done (GSD)
│   └── gstack/                # GStack
├── design/
│   ├── README.md                    # Design category overview
│   └── diagram-design/                # Diagram Design
│   └── impeccable/                # Impeccable
│   └── ppt-master/                # PPT Master
│   └── ui-ux-pro-max/                # UI UX Pro Max
├── multimedia-writing/
│   ├── README.md                    # Multimedia / Writing category overview
│   └── anthropic-skills/                # Anthropic Skills (vendored)
│   └── humanizer/                # Humanizer
│   └── hyperframes/                # Hyperframes
│   └── openmontage/                # OpenMontage
├── agency/
│   ├── README.md                    # Agency Personas category overview
│   └── academic/                # The Agency — Academic Division (6 personas) (vendored)
│   └── design/                # The Agency — Design Division (10 personas) (vendored)
│   └── engineering/                # The Agency — Engineering Division (66 personas) (vendored)
│   └── finance/                # The Agency — Finance Division (5 personas) (vendored)
│   └── game-development/                # The Agency — Game Development Division (21 personas) (vendored)
│   └── gis/                # The Agency — GIS Division (13 personas) (vendored)
│   └── healthcare/                # The Agency — Healthcare Division (3 personas) (vendored)
│   └── marketing/                # The Agency — Marketing Division (37 personas) (vendored)
│   └── paid-media/                # The Agency — Paid Media Division (7 personas) (vendored)
│   └── product/                # The Agency — Product Division (6 personas) (vendored)
│   └── project-management/                # The Agency — Project Management Division (7 personas) (vendored)
│   └── research/                # The Agency — Research Division (1 personas) (vendored)
│   └── sales/                # The Agency — Sales Division (9 personas) (vendored)
│   └── security/                # The Agency — Security Division (12 personas) (vendored)
│   └── spatial-computing/                # The Agency — Spatial Computing Division (6 personas) (vendored)
│   └── specialized/                # The Agency — Specialized Division (59 personas) (vendored)
│   └── support/                # The Agency — Support Division (6 personas) (vendored)
│   └── testing/                # The Agency — Testing Division (9 personas) (vendored)
│   └── nexus/                # The Agency — NEXUS Orchestration Playbooks (vendored)
```

Every `skills/<cat>/<slug>/` directory is self-contained:

| File             | Purpose                                                              |
|------------------|----------------------------------------------------------------------|
| `SKILL.md`       | Agent-readable skill spec (YAML frontmatter + capabilities + workflow) |
| `manifest.json`  | Machine-readable plugin manifest (id, version, MCP deps, triggers)  |

The per-plugin directories are generated at install time (symlinks into
`plugin-catalog/`, built by `bash scripts/scaffold_modular_skills.sh`);
only this manifest, the READMEs, and the committed index are tracked in
git. Refresh the index with `python3 scripts/generate_skills_index.py`.

## Coverage

- **40 plugins** across **6 categories**.
- **21 vendored** (source code copied into repo): replica-skill, anthropic-skills, academic, design, engineering, finance, game-development, gis, healthcare, marketing, paid-media, product, project-management, research, sales, security, spatial-computing, specialized, support, testing, nexus.
- **19 integrated-ready** (manifest + SKILL.md only; upstream pulled on demand).

## Categories

### Code  ·  `skills/code/`

Code-craft skills: TypeScript rigor, minimal-first ML, frontend perf, reverse-engineering clones.

Plugins (4):

- **Agent Skills (Addy Osmani)** (`agent-skills-addyosmani`) — integrated-ready — MCP: browser-tools-mcp, lighthouse-mcp, pa11y-mcp
- **Andrej Karpathy Skills** (`karpathy-skills`) — integrated-ready — MCP: jupyter-mcp, python-repl-mcp
- **Matt Pocock Skills** (`mattpocock-skills`) — integrated-ready — MCP: typescript-language-server-mcp, eslint-mcp
- **Replica Skill (11 sub-skills)** (`replica-skill`) — vendored — MCP: browser-tools-mcp, vision-mcp

### Research  ·  `skills/research/`

Deep-research skills: knowledge graphs, multi-step reasoning, fresh-trend monitoring, Feynman-style explanation.

Plugins (5):

- **Agent-Reach** (`agent-reach`) — integrated-ready — MCP: brave-search-mcp, tavily-mcp, exa-mcp, firecrawl-mcp
- **Graphify** (`graphify`) — integrated-ready — MCP: neo4j-mcp, graphrag-mcp, embeddings-mcp
- **Last 30 Days** (`last-30-days`) — integrated-ready — MCP: brave-search-mcp, newsapi-mcp, google-news-mcp
- **REA (Reverse Engineer Anything)** (`rea`) — integrated-ready — MCP: (none)
- **Understand Anything** (`understand-anything`) — integrated-ready — MCP: wikipedia-mcp, arxiv-mcp, embeddings-mcp

### Tokens / Optimization  ·  `skills/tokens-optimization/`

Token / context budget skills: compression, agile persona dispatch, atomic parallel execution.

Plugins (4):

- **BMAD Method** (`bmad-method`) — integrated-ready — MCP: linear-mcp, github-issues-mcp, memory-mcp
- **Caveman** (`caveman`) — integrated-ready — MCP: (none)
- **Get Shit Done (GSD)** (`gsd`) — integrated-ready — MCP: task-router-mcp, memory-mcp
- **GStack** (`gstack`) — integrated-ready — MCP: (none)

### Design  ·  `skills/design/`

Design skills: UI/UX tokens, visual polish, slide narrative, diagramming.

Plugins (4):

- **Diagram Design** (`diagram-design`) — integrated-ready — MCP: mermaid-mcp, excalidraw-mcp
- **Impeccable** (`impeccable`) — integrated-ready — MCP: browser-tools-mcp, figma-mcp
- **PPT Master** (`ppt-master`) — integrated-ready — MCP: google-slides-mcp, office-mcp, image-search-mcp
- **UI UX Pro Max** (`ui-ux-pro-max`) — integrated-ready — MCP: figma-mcp, browser-tools-mcp, storybook-mcp

### Multimedia / Writing  ·  `skills/multimedia-writing/`

Multimedia + writing skills: office docs, video montage, talking-head avatars, AI-ism removal.

Plugins (4):

- **Anthropic Skills** (`anthropic-skills`) — vendored — MCP: filesystem-mcp, pdf-mcp, vision-mcp
- **Humanizer** (`humanizer`) — integrated-ready — MCP: style-mcp, grammar-mcp
- **Hyperframes** (`hyperframes`) — integrated-ready — MCP: heygen-mcp, elevenlabs-mcp
- **OpenMontage** (`openmontage`) — integrated-ready — MCP: ffmpeg-mcp, video-mcp

### Agency Personas  ·  `skills/agency/`

AI-persona packs from The Agency (agency-agents): 283 specialist personas across 18 divisions plus the NEXUS orchestration playbooks.

Plugins (19):

- **The Agency — Academic Division (6 personas)** (`academic`) — vendored — MCP: (none)
- **The Agency — Design Division (10 personas)** (`design`) — vendored — MCP: (none)
- **The Agency — Engineering Division (66 personas)** (`engineering`) — vendored — MCP: (none)
- **The Agency — Finance Division (5 personas)** (`finance`) — vendored — MCP: (none)
- **The Agency — Game Development Division (21 personas)** (`game-development`) — vendored — MCP: (none)
- **The Agency — GIS Division (13 personas)** (`gis`) — vendored — MCP: (none)
- **The Agency — Healthcare Division (3 personas)** (`healthcare`) — vendored — MCP: (none)
- **The Agency — Marketing Division (37 personas)** (`marketing`) — vendored — MCP: (none)
- **The Agency — Paid Media Division (7 personas)** (`paid-media`) — vendored — MCP: (none)
- **The Agency — Product Division (6 personas)** (`product`) — vendored — MCP: (none)
- **The Agency — Project Management Division (7 personas)** (`project-management`) — vendored — MCP: (none)
- **The Agency — Research Division (1 personas)** (`research`) — vendored — MCP: (none)
- **The Agency — Sales Division (9 personas)** (`sales`) — vendored — MCP: (none)
- **The Agency — Security Division (12 personas)** (`security`) — vendored — MCP: (none)
- **The Agency — Spatial Computing Division (6 personas)** (`spatial-computing`) — vendored — MCP: (none)
- **The Agency — Specialized Division (59 personas)** (`specialized`) — vendored — MCP: (none)
- **The Agency — Support Division (6 personas)** (`support`) — vendored — MCP: (none)
- **The Agency — Testing Division (9 personas)** (`testing`) — vendored — MCP: (none)
- **The Agency — NEXUS Orchestration Playbooks** (`nexus`) — vendored — MCP: (none)

## Integration with unified-integration

`unified-integration/setup.sh` aggregates every `SKILL.md` in this tree into
`unified-integration/skills/all-skills.json` (the registry that gets installed
into each agent CLI). The modular tree is the **source of truth for plugin
content**; `unified-integration/skills/` is the **installed view**.

## See also

- `plugin-catalog/catalog.json` — canonical catalog with upstream URLs
- `plugin-catalog/mcp-servers.json` — MCP server roadmap (P0/P1/P2)
- `unified-integration/skills/all-skills.json` — installed skill registry
- `docs/MCP_INTEGRATION_CHECKLIST.md` — step-by-step MCP build plan
- `README_INTEGRATION.md` — full architecture + merger narrative
