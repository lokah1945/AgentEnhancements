---
slug: diagram-design
category: design
version: 1.0.0
status: integrated-ready
mcp_servers: [mermaid-mcp, excalidraw-mcp]
trigger_keywords: [diagram, mermaid, d2, flowchart, erd]
---

# Diagram Design

Skill diagram: mermaid, d2, plantuml, excalidraw. Pemilihan tool berbasis intent (sequence vs flowchart vs ERD), dengan template dan palette konsisten.

## Kapan dipakai

- User minta "diagram", "flowchart", "ERD", "sequence", "architecture"
- Dokumentasi API butuh visual sequence
- RFC / ADR perlu diagram arsitektur

## Prasyarat

- MCP: `mermaid-mcp`, `excalidraw-mcp`
- Tools: `mmdc` (mermaid CLI), `d2` (D2 CLI), `read_file`, `write_file`

## Capabilities

1. Intent-based diagram tool selection — flowchart/ERD/sequence/architecture/mindmap.
2. Diagram authoring — mermaid (default), d2 (complex), plantuml (legacy), excalidraw (sketch).
3. Diagram refactoring & simplification — split, group, hapus node yang tidak perlu.
4. Diagram-to-text round-trip — generate text → render → edit text → re-render.

## Workflow

1. Identifikasi intent user:
   - "alur proses" → flowchart
   - "interaksi sistem" → sequence
   - "skema DB" → ERD
   - "deployment" → architecture (C4)
   - "brainstorm" → mindmap
2. Pilih tool:
   - simple & portable → mermaid
   - kompleks, banyak koneksi → d2
   - whiteboard sketch → excalidraw
3. Generate code diagram dari description.
4. Render ke PNG/SVG via CLI.
5. Persist source code + image ke `docs/diagrams/<slug>.{mmd,d2,svg,png}`.
6. Embed di README/docs bila diminta.

## Inputs

- Deskripsi diagram (narasi atau bullet)
- Opsional: tool target (auto bila tidak)
- Opsional: format output (svg default, png, atau eksport ke draw.io)
- Opsional: palette (default pakai `tokens.json`)

## Outputs

- `<slug>.mmd` / `.d2` / `.puml` — source code
- `<slug>.svg` / `.png` — render
- Embed snippet markdown bila diminta

## Contoh

### Contoh 1 — Auth flow

Prompt: "Buat sequence diagram: user login dengan OAuth2 PKCE."

```
tool: mermaid (sequence)
source docs/diagrams/auth-oauth.mmd:
sequenceDiagram
  participant U as User
  participant A as App
  participant P as Provider
  U->>A: click "Login with Google"
  A->>P: GET /auth?code_challenge=...
  P->>U: consent screen
  U->>P: approve
  P->>A: redirect ?code=...
  A->>P: POST /token (code + verifier)
  P->>A: access_token
  A->>U: dashboard

render: docs/diagrams/auth-oauth.svg
```

### Contoh 2 — Database ERD

Prompt: "ERD untuk schema SaaS subscription tracker."

```
tool: mermaid (erDiagram)
source docs/diagrams/schema-erd.mmd:
erDiagram
  USER ||--o{ SUBSCRIPTION : owns
  SUBSCRIPTION ||--|| SERVICE : tracks
  SUBSCRIPTION ||--o{ ALERT : has
  USER {
    bigint id PK
    string email
    timestamp created_at
  }
  ...

render: docs/diagrams/schema-erd.svg
```

### Contoh 3 — C4 architecture

Prompt: "Diagram arsitektur C4 Level 2 untuk microservice kami."

```
tool: d2 (lebih cocok untuk C4 kompleks)
source docs/diagrams/arch-c4.d2:
User -> Frontend: HTTPS
Frontend -> API Gateway: REST
API Gateway -> Auth Service: gRPC
API Gateway -> Order Service: gRPC
Order Service -> Postgres: SQL
Order Service -> Kafka: publish event
Auth Service -> Redis: cache

render: docs/diagrams/arch-c4.svg
```

## Batasan & Keamanan

- Diagram ≤ 30 node (di atas itu tidak readable).
- Tidak expose secret di diagram (token, password, internal URL).
- Mermaid di GitHub README: uji render di PR preview dulu.
- Untuk diagram rahasia, render lokal (jangan pakai mermaid.live).

## Catatan integrasi

- Diagram disimpan di `docs/diagrams/` agar bisa di-embed di README.
- Untuk diagram di PPT, gunakan `ppt-master` + embed image.
- Untuk arsitektur ADR, tautkan diagram di ADR (lihat `docs/adr/`).
- Palette konsisten dengan `tokens.json`.
