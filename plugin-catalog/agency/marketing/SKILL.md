---
slug: marketing
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [growth, content creator, seo, social media, tiktok]
---

# The Agency — Marketing Division

37 persona marketing dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: AEO Foundations Architect, Agentic Search Optimizer, AI Citation Strategist, App Store Optimizer, Baidu SEO Specialist, Bilibili Content Strategist, Book Co-Author, Carousel Growth Engine.

## Kapan dipakai

- Task yang cocok dengan marketing butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/marketing/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **AEO Foundations Architect** — lihat `agency-agents/skills/marketing/marketing-aeo-foundations/SKILL.md`
2. **Agentic Search Optimizer** — lihat `agency-agents/skills/marketing/marketing-agentic-search-optimizer/SKILL.md`
3. **AI Citation Strategist** — lihat `agency-agents/skills/marketing/marketing-ai-citation-strategist/SKILL.md`
4. **App Store Optimizer** — lihat `agency-agents/skills/marketing/marketing-app-store-optimizer/SKILL.md`
5. **Baidu SEO Specialist** — lihat `agency-agents/skills/marketing/marketing-baidu-seo-specialist/SKILL.md`
6. **Bilibili Content Strategist** — lihat `agency-agents/skills/marketing/marketing-bilibili-content-strategist/SKILL.md`
7. **Book Co-Author** — lihat `agency-agents/skills/marketing/marketing-book-co-author/SKILL.md`
8. **Carousel Growth Engine** — lihat `agency-agents/skills/marketing/marketing-carousel-growth-engine/SKILL.md`
9. **China E-Commerce Operator** — lihat `agency-agents/skills/marketing/marketing-china-ecommerce-operator/SKILL.md`
10. **China Market Localization Strategist** — lihat `agency-agents/skills/marketing/marketing-china-market-localization-strategist/SKILL.md`
11. **Content Creator** — lihat `agency-agents/skills/marketing/marketing-content-creator/SKILL.md`
12. **Cross-Border E-Commerce Specialist** — lihat `agency-agents/skills/marketing/marketing-cross-border-ecommerce/SKILL.md`
13. ... dan 25 persona lainnya (lihat manifest.json)

## Workflow

1. Pilih persona dari `agency-agents/skills/marketing/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
