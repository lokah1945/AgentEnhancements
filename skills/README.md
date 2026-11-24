# AgentEnhancements — Modular Skills Tree

Generated catalog-guide view for humans and agents. Plugin manifests
and guides remain canonical under `plugin-catalog/`.

## Layout

```text
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
│   └── academic/                # The Agency — Academic Division (6 personas)
│ # (vendored)
│   └── design/                # The Agency — Design Division (10 personas)
│ # (vendored)
│   └── engineering/                # The Agency — Engineering Division (66
│ # personas) (vendored)
│   └── finance/                # The Agency — Finance Division (5 personas)
│ # (vendored)
│   └── game-development/                # The Agency — Game Development
│ # Division (21 personas) (vendored)
│   └── gis/                # The Agency — GIS Division (13 personas) (vendored)
│   └── healthcare/                # The Agency — Healthcare Division (3
│ # personas) (vendored)
│   └── marketing/                # The Agency — Marketing Division (37
│ # personas) (vendored)
│   └── paid-media/                # The Agency — Paid Media Division (7
│ # personas) (vendored)
│   └── product/                # The Agency — Product Division (6 personas)
│ # (vendored)
│   └── project-management/                # The Agency — Project Management
│ # Division (7 personas) (vendored)
│   └── research/                # The Agency — Research Division (1 personas)
│ # (vendored)
│   └── sales/                # The Agency — Sales Division (9 personas)
│ # (vendored)
│   └── security/                # The Agency — Security Division (12 personas)
│ # (vendored)
│   └── spatial-computing/                # The Agency — Spatial Computing
│ # Division (6 personas) (vendored)
│   └── specialized/                # The Agency — Specialized Division (59
│ # personas) (vendored)
│   └── support/                # The Agency — Support Division (6 personas)
│ # (vendored)
│   └── testing/                # The Agency — Testing Division (9 personas)
│ # (vendored)
│   └── nexus/                # The Agency — NEXUS Orchestration Playbooks
│ # (vendored)
```

Every `skills/<cat>/<slug>/` directory is self-contained:

- **File:** `SKILL.md`
  - **Purpose:** Agent-readable skill spec (YAML frontmatter + capabilities +
    workflow)

- **File:** `manifest.json`
  - **Purpose:** Machine-readable plugin manifest (id, version, MCP deps,
    triggers)

The per-plugin directories are generated at install time (symlinks into
`plugin-catalog/`, built by `bash scripts/scaffold_modular_skills.sh`);
only this manifest, the READMEs, and the committed index are tracked in
git. Refresh the index with `python3 scripts/generate_skills_index.py`.

## Coverage

- **40 plugins** across **6 categories**.
- **21 vendored** (source code copied into repo): replica-skill,
  anthropic-skills, academic, design, engineering, finance, game-development,
  gis, healthcare, marketing, paid-media, product, project-management, research,
  sales, security, spatial-computing, specialized, support, testing, nexus.
- Implementation status (independent of vendored source): integrated: 1,
  integrated-ready: 39.
- External runtimes require deliberate user installation and configuration.

## Categories

### Code  ·  `skills/code/`

Code-craft skills: TypeScript rigor, minimal-first ML, frontend perf,
reverse-engineering clones.

Plugins (4):

- **Agent Skills (Addy Osmani)** (`agent-skills-addyosmani`) — integrated-ready;
  external source — MCP: browser-tools-mcp, lighthouse-mcp, pa11y-mcp
- **Andrej Karpathy Skills** (`karpathy-skills`) — integrated-ready; external
  source — MCP: jupyter-mcp, python-repl-mcp
- **Matt Pocock Skills** (`mattpocock-skills`) — integrated-ready; external
  source — MCP: typescript-language-server-mcp, eslint-mcp
- **Replica Skill (11 sub-skills)** (`replica-skill`) — integrated-ready;
  vendored source — MCP: browser-tools-mcp, vision-mcp

### Research  ·  `skills/research/`

Deep-research skills: knowledge graphs, multi-step reasoning, fresh-trend
monitoring, Feynman-style explanation.

Plugins (5):

- **Agent-Reach** (`agent-reach`) — integrated-ready; external source — MCP:
  tavily-mcp, exa-mcp, firecrawl-mcp
- **Graphify** (`graphify`) — integrated-ready; external source — MCP:
  neo4j-mcp, graphrag-mcp, embeddings-mcp
- **Last 30 Days** (`last-30-days`) — integrated-ready; external source — MCP:
  exa-mcp, newsapi-mcp, google-news-mcp
- **REA (Reverse Engineer Anything)** (`rea`) — integrated-ready; external
  source — MCP: tavily-mcp, memory-mcp, task-router-mcp
- **Understand Anything** (`understand-anything`) — integrated-ready; external
  source — MCP: wikipedia-mcp, arxiv-mcp, embeddings-mcp

### Tokens / Optimization  ·  `skills/tokens-optimization/`

Token / context budget skills: compression, agile persona dispatch, atomic
parallel execution.

Plugins (4):

- **BMAD Method** (`bmad-method`) — integrated-ready; external source — MCP:
  linear-mcp, github-issues-mcp, memory-mcp
- **Caveman** (`caveman`) — integrated-ready; external source — MCP: (none)
- **Get Shit Done (GSD)** (`gsd`) — integrated-ready; external source — MCP:
  task-router-mcp, memory-mcp
- **GStack** (`gstack`) — integrated-ready; external source — MCP:
  filesystem-mcp

### Design  ·  `skills/design/`

Design skills: UI/UX tokens, visual polish, slide narrative, diagramming.

Plugins (4):

- **Diagram Design** (`diagram-design`) — integrated-ready; external source —
  MCP: mermaid-mcp, excalidraw-mcp
- **Impeccable** (`impeccable`) — integrated-ready; external source — MCP:
  browser-tools-mcp, figma-mcp
- **PPT Master** (`ppt-master`) — integrated-ready; external source — MCP:
  google-slides-mcp, office-mcp, image-search-mcp
- **UI UX Pro Max** (`ui-ux-pro-max`) — integrated-ready; external source — MCP:
  figma-mcp, browser-tools-mcp, storybook-mcp

### Multimedia / Writing  ·  `skills/multimedia-writing/`

Multimedia + writing skills: office docs, video montage, talking-head avatars,
AI-ism removal.

Plugins (4):

- **Anthropic Skills** (`anthropic-skills`) — integrated; vendored source — MCP:
  filesystem-mcp, pdf-mcp, vision-mcp
- **Humanizer** (`humanizer`) — integrated-ready; external source — MCP:
  style-mcp, grammar-mcp
- **Hyperframes** (`hyperframes`) — integrated-ready; external source — MCP:
  heygen-mcp, elevenlabs-mcp
- **OpenMontage** (`openmontage`) — integrated-ready; external source — MCP:
  ffmpeg-mcp, video-mcp

### Agency Personas  ·  `skills/agency/`

AI-persona packs from The Agency (agency-agents): 283 specialist personas across
18 divisions plus the NEXUS orchestration playbooks.

Plugins (19):

- **The Agency — Academic Division (6 personas)** (`academic`) —
  integrated-ready; vendored source — MCP: filesystem-mcp, memory-mcp,
  task-router-mcp
- **The Agency — Design Division (10 personas)** (`design`) — integrated-ready;
  vendored source — MCP: filesystem-mcp, memory-mcp, task-router-mcp
- **The Agency — Engineering Division (66 personas)** (`engineering`) —
  integrated-ready; vendored source — MCP: filesystem-mcp, memory-mcp,
  task-router-mcp
- **The Agency — Finance Division (5 personas)** (`finance`) — integrated-ready;
  vendored source — MCP: filesystem-mcp, memory-mcp, task-router-mcp
- **The Agency — Game Development Division (21 personas)** (`game-development`)
  — integrated-ready; vendored source — MCP: filesystem-mcp, memory-mcp,
  task-router-mcp
- **The Agency — GIS Division (13 personas)** (`gis`) — integrated-ready;
  vendored source — MCP: filesystem-mcp, memory-mcp, task-router-mcp
- **The Agency — Healthcare Division (3 personas)** (`healthcare`) —
  integrated-ready; vendored source — MCP: filesystem-mcp, memory-mcp,
  task-router-mcp
- **The Agency — Marketing Division (37 personas)** (`marketing`) —
  integrated-ready; vendored source — MCP: filesystem-mcp, memory-mcp,
  task-router-mcp
- **The Agency — Paid Media Division (7 personas)** (`paid-media`) —
  integrated-ready; vendored source — MCP: filesystem-mcp, memory-mcp,
  task-router-mcp
- **The Agency — Product Division (6 personas)** (`product`) — integrated-ready;
  vendored source — MCP: filesystem-mcp, memory-mcp, task-router-mcp
- **The Agency — Project Management Division (7 personas)**
  (`project-management`) — integrated-ready; vendored source — MCP:
  filesystem-mcp, memory-mcp, task-router-mcp
- **The Agency — Research Division (1 personas)** (`research`) —
  integrated-ready; vendored source — MCP: filesystem-mcp, memory-mcp,
  task-router-mcp
- **The Agency — Sales Division (9 personas)** (`sales`) — integrated-ready;
  vendored source — MCP: filesystem-mcp, memory-mcp, task-router-mcp
- **The Agency — Security Division (12 personas)** (`security`) —
  integrated-ready; vendored source — MCP: filesystem-mcp, memory-mcp,
  task-router-mcp
- **The Agency — Spatial Computing Division (6 personas)** (`spatial-computing`)
  — integrated-ready; vendored source — MCP: filesystem-mcp, memory-mcp,
  task-router-mcp
- **The Agency — Specialized Division (59 personas)** (`specialized`) —
  integrated-ready; vendored source — MCP: filesystem-mcp, memory-mcp,
  task-router-mcp
- **The Agency — Support Division (6 personas)** (`support`) — integrated-ready;
  vendored source — MCP: filesystem-mcp, memory-mcp, task-router-mcp
- **The Agency — Testing Division (9 personas)** (`testing`) — integrated-ready;
  vendored source — MCP: filesystem-mcp, memory-mcp, task-router-mcp
- **The Agency — NEXUS Orchestration Playbooks** (`nexus`) — integrated-ready;
  vendored source — MCP: filesystem-mcp, memory-mcp, task-router-mcp

## Integration with unified-integration

`unified-integration/setup.sh` aggregates the vendored skill sources into
`unified-integration/skills/all-skills.json`. Catalog guides are a separate
surface in `agent-registry.json`; this modular tree does not install the
external upstream runtimes. Implementation status and runtime readiness
are separate dimensions (CONTRACT section 8.1).

## See also

- `plugin-catalog/catalog.json` — canonical catalog with upstream URLs
- `plugin-catalog/mcp-servers.json` — MCP server roadmap (P0/P1/P2)
- `unified-integration/skills/all-skills.json` — installed skill registry
- `docs/MCP_INTEGRATION_CHECKLIST.md` — step-by-step MCP build plan
- `README_INTEGRATION.md` — full architecture + merger narrative
