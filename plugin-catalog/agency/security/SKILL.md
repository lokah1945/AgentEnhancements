---
slug: security
category: agency
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [threat model, penetration test, incident response, siem, appsec]
---

# The Agency — Security Division

12 persona security dari The Agency: spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: AI-Generated Code Security Auditor, Application Security Engineer, Security Architect, Blockchain Security Auditor, Cloud Security Architect, Compliance Auditor, Incident Responder, Penetration Tester.

## Kapan dipakai

- Task yang cocok dengan security butuh persona spesialis
- Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik
- Membangun tim AI lintas fungsi dengan persona yang saling melengkapi

## Prasyarat

- Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)
- Skills terkonversi: `agency-agents/skills/security/<agent-slug>/SKILL.md`
- Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit

## Capabilities

1. **AI-Generated Code Security Auditor** — lihat `agency-agents/skills/security/security-ai-generated-code-auditor/SKILL.md`
2. **Application Security Engineer** — lihat `agency-agents/skills/security/security-appsec-engineer/SKILL.md`
3. **Security Architect** — lihat `agency-agents/skills/security/security-architect/SKILL.md`
4. **Blockchain Security Auditor** — lihat `agency-agents/skills/security/security-blockchain-security-auditor/SKILL.md`
5. **Cloud Security Architect** — lihat `agency-agents/skills/security/security-cloud-security-architect/SKILL.md`
6. **Compliance Auditor** — lihat `agency-agents/skills/security/security-compliance-auditor/SKILL.md`
7. **Incident Responder** — lihat `agency-agents/skills/security/security-incident-responder/SKILL.md`
8. **Penetration Tester** — lihat `agency-agents/skills/security/security-penetration-tester/SKILL.md`
9. **Secrets & Credential Hygiene Engineer** — lihat `agency-agents/skills/security/security-secrets-credential-engineer/SKILL.md`
10. **Senior SecOps Engineer** — lihat `agency-agents/skills/security/security-senior-secops/SKILL.md`
11. **Threat Detection Engineer** — lihat `agency-agents/skills/security/security-threat-detection-engineer/SKILL.md`
12. **Threat Intelligence Analyst** — lihat `agency-agents/skills/security/security-threat-intelligence-analyst/SKILL.md`

## Workflow

1. Pilih persona dari `agency-agents/skills/security/` (index: manifest.json).
2. Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.
3. Sebutkan persona by name saat mendispatch sub-tugas (mis. "gunakan agency-engineering-code-reviewer").
4. Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search "<topik>"`.

## Sumber

Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).
Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).
