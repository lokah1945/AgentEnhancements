---
slug: testing
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [qa, test automation, performance testing, api testing, accessibility audit]
---

# The Agency — Testing Division

9 persona testing dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: Accessibility Auditor, API Tester, Evidence Collector, Performance Benchmarker, Reality Checker, Test Automation Engineer, Test Results Analyzer, Tool Evaluator.

## Kapan dipakai

- Task yang cocok dengan testing butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/testing/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **Accessibility Auditor** — lihat `agency-agents/skills/testing/testing-accessibility-auditor/SKILL.md`
2. **API Tester** — lihat `agency-agents/skills/testing/testing-api-tester/SKILL.md`
3. **Evidence Collector** — lihat `agency-agents/skills/testing/testing-evidence-collector/SKILL.md`
4. **Performance Benchmarker** — lihat `agency-agents/skills/testing/testing-performance-benchmarker/SKILL.md`
5. **Reality Checker** — lihat `agency-agents/skills/testing/testing-reality-checker/SKILL.md`
6. **Test Automation Engineer** — lihat `agency-agents/skills/testing/testing-test-automation-engineer/SKILL.md`
7. **Test Results Analyzer** — lihat `agency-agents/skills/testing/testing-test-results-analyzer/SKILL.md`
8. **Tool Evaluator** — lihat `agency-agents/skills/testing/testing-tool-evaluator/SKILL.md`
9. **Workflow Optimizer** — lihat `agency-agents/skills/testing/testing-workflow-optimizer/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/testing/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
