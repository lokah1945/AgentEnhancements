---
slug: graphify
category: research
version: 1.0.0
status: integrated-ready
mcp_servers: [neo4j-mcp, graphrag-mcp, embeddings-mcp]
trigger_keywords: [knowledge graph, graph, extract, entity, relation]
---

# Graphify

Ubah dokumen teks / paper / transcript menjadi knowledge graph (nodes-edges) yang bisa di-query. Entity extraction, relation mining, dan graph export ke JSON-LD / Neo4j / GraphML.

## Kapan dipakai

- User minta "buat knowledge graph dari <doc>", "extract entities & relations"
- Riset literatur ingin melihat jaringan sitasi / konsep
- Ingin visualisasi dependensi antar-konsep dari dokumen panjang
- Membangun GraphRAG untuk pertanyaan kompleks lintas dokumen

## Prasyarat

- MCP: `neo4j-mcp`, `graphrag-mcp`, `embeddings-mcp`
- Tools: `python3` dengan spaCy / transformers, `read_file`, `write_file`
- Opsional: instance Neo4j (local docker atau Aura)

## Capabilities

1. Entity & relation extraction — NER + coreference resolution + relation classifier.
2. Knowledge-graph construction — node types, edge types, attributes.
3. Graph export — JSON-LD, Cypher, GraphML, Neo4j dump.
4. Graph-based retrieval (G-RAG) — query multi-hop lewat graph.

## Workflow

1. Baca dokumen (PDF/TXT/MD) → split per paragraph atau per section.
2. Ekstrak entity per chunk → klasifikasi tipe (PERSON/ORG/CONCEPT/EVENT/...).
3. Ekstrak relation antar-entity di chunk yang sama → klasifikasi tipe (e.g. `WORKS_FOR`, `CITES`, `PART_OF`).
4. Resolve coreference (anaphora) lintas chunk.
5. Bangun graph: nodes + edges + attributes.
6. Hitung metrics: degree centrality, betweenness, community detection (Louvain).
7. Export ke format yang diminta + tampilkan visualisasi (Mermaid / D3) ringkas.

## Inputs

- Dokumen (path PDF / TXT / MD / URL)
- Opsional: schema entity type custom (mis. hanya ambil `GENE` dan `DISEASE`)
- Opsional: Neo4j URI bila ingin persist

## Outputs

- `graph.jsonld` di `download/graphs/`
- `graph.cypher` (Cypher statements) bila Neo4j
- `graph.graphml` bila visualisasi di Gephi/Cytoscape
- `graph-summary.md` — top 10 nodes by degree, top 5 communities, edge type distribution
- Visualisasi PNG/SVG (Mermaid atau D3) bila diminta

## Contoh

### Contoh 1 — Knowledge graph dari paper

Prompt: "Buat graph dari `paper.pdf` — entities: GEN, DISEASE, DRUG."

```
extracted:
  nodes: 142 (47 GEN, 38 DISEASE, 57 DRUG)
  edges: 287 (TREATS 89, INTERACTS_WITH 134, ASSOCIATED_WITH 64)
top nodes:
  - BRCA1 (degree 18)
  - TP53 (degree 16)
  - paclitaxel (degree 12)
communities: 5 cluster (Louvain modularity 0.62)
export: download/graphs/paper-graph.jsonld
```

### Contoh 2 — Citation network

Prompt: "Buat graph sitasi dari 10 paper ini <list>."

```
extracted:
  nodes: 10 paper + 247 refs
  edges: 247 CITES
  h-index proxy: paper#3 (cited 12x)
export: download/graphs/citation.cypher
```

### Contoh 3 — Concept map dari transcript meeting

Prompt: "Extract konsep dari `meeting.txt` 60 menit."

```
nodes: 38 (DECISION 7, ACTION 12, TOPIC 19)
edges: 51 (RESULTS_IN 8, ASSIGNED_TO 11, DISCUSSED_UNDER 32)
high-centrality: "Q3 roadmap" (degree 9)
export: download/graphs/meeting-graph.jsonld + visualisasi Mermaid
```

## Batasan & Keamanan

- NER sensitif bahasa; default English. Untuk Indonesia, perlu flag `lang=id`.
- Embedding API call butuh biaya; batasi chunk size ≤ 512 token.
- Tidak auto-import ke Neo4j production; selalu test di sandbox dulu.
- Untuk dokumen rahasia, jalankan dengan model lokal (spaCy) bila privacy strict.

## Catatan integrasi

- Graph disimpan persist di `unified-integration/memory/graphs/` agar lintas sesi.
- Bekerja baik bersama `agent-reach` (multi-source) dan `understand-anything` (explain graph).
- Untuk query graph, gunakan `graphrag-mcp`.
