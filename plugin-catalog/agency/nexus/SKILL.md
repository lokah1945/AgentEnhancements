---
slug: nexus
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [nexus, multi-agent pipeline, orchestrator, quality gates, startup mvp]
---

# The Agency — NEXUS Orchestration Playbooks

Playbook orkestrasi multi-agen NEXUS dari The Agency: siapa mengerjakan apa, kapan, dan bagaimana kualitas diverifikasi di setiap fase.

## Kapan dipakai

- Mengorkestrasi beberapa persona Agency dalam satu pipeline produk
- Proyek end-to-end: discovery sampai operate dengan quality gate
- Skenario siap pakai: startup MVP, kampanye marketing, fitur enterprise, incident response

## Prasyarat

- Vendored: `agency-agents/strategy/` di root repo (MIT)
- Persona pendukung: pack divisi lain di kategori `agency`
- Docs: `agency-agents/strategy/QUICKSTART.md` (mulai 5 menit)

## Capabilities

1. NEXUS-Full — pipeline lengkap 12-24 minggu (semua divisi)
2. NEXUS-Sprint — MVP/fitur 2-6 minggu (15-25 agen)
3. NEXUS-Micro — tugas spesifik 1-5 hari (5-10 agen)
4. Playbook fase 0-6 dengan quality gate antar fase
5. Runbook skenario + roster agen per runbook (strategy/runbooks.json)

## Workflow

1. Baca `agency-agents/strategy/QUICKSTART.md` untuk memilih mode (Full/Sprint/Micro).
2. Aktifkan Agents Orchestrator (pack specialized) sebagai koordinator.
3. Ikuti playbook fase di `agency-agents/strategy/playbooks/phase-*.md` berurutan.
4. Lewati quality gate antar fase: bukti wajib untuk semua assessment.
5. Untuk skenario spesifik, mulai dari `strategy/runbooks/` dan roster JSON-nya.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
