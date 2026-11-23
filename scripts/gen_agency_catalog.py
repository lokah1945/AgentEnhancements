#!/usr/bin/env python3
"""Generate the plugin-catalog entries for the vendored agency-agents source.

Creates plugin-catalog/agency/<division>.json (manifest) and
plugin-catalog/agency/<division>/SKILL.md (integration guide) for the 18
divisions plus one "nexus" pack covering strategy/ orchestration playbooks,
then registers all 19 packs in plugin-catalog/catalog.json under the new
"agency" category.

Follows the exact manifest schema of the existing catalog entries
(skill-manifest.v1.json: id, name, slug, category, version, status, source,
description, capabilities, tools_required, mcp_servers_suggested,
trigger_keywords, best_for, integration_notes, sub_skills, skill_files).

Run from repo root:  python3 scripts/gen_agency_catalog.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VENDOR = REPO / "agency-agents"
CATALOG_DIR = REPO / "plugin-catalog" / "agency"
CATALOG_INDEX = REPO / "plugin-catalog" / "catalog.json"

# (slug, name, blurb-id, trigger keywords, best_for) per division pack.
# Descriptions are written in Indonesian to match the existing catalog voice.
DIVISIONS = [
    ("academic", "Academic Division",
     ["worldbuilding", "narrative design", "story structure", "cultural systems", "statistical analysis"],
     ["desain dunia fiksi yang koheren", "analisis naratif berbasis teori", "riset akademik untuk konten"]),
    ("design", "Design Division",
     ["ui designer", "ux research", "design system", "brand identity", "visual storytelling"],
     ["desain UI/UX dan design system", "riset pengguna dan walkthrough persona", "branding dan konsistensi visual"]),
    ("engineering", "Engineering Division",
     ["frontend developer", "backend architect", "devops", "code review", "sre", "database"],
     ["implementasi fitur engineering end-to-end", "arsitektur sistem dan API", "review kode dan optimasi"]),
    ("finance", "Finance Division",
     ["bookkeeper", "financial analyst", "fpa", "investment research", "tax strategy"],
     ["pembukuan dan month-end close", "modeling keuangan dan forecast", "riset investasi dan strategi pajak"]),
    ("game-development", "Game Development Division",
     ["game designer", "unity", "unreal engine", "godot", "roblox", "blender"],
     ["desain sistem game dan ekonomi in-game", "implementasi Unity/Unreal/Godot", "tooling Blender dan Roblox"]),
    ("gis", "GIS Division",
     ["gis", "arcgis", "maplibre", "spatial data", "bim", "drone mapping"],
     ["pipeline data geospasial", "peta web dan dashboard interaktif", "digital twin dan reality capture"]),
    ("healthcare", "Healthcare Division",
     ["clinical evidence", "healthcare compliance", "sovereign health"],
     ["klaim klinis yang kredibel", "strategi health-tech teregulasi"]),
    ("marketing", "Marketing Division",
     ["growth", "content creator", "seo", "social media", "tiktok", "email marketing"],
     ["growth experiment dan akuisisi user", "strategi konten multi-platform", "SEO/AEO dan social media"]),
    ("paid-media", "Paid Media Division",
     ["ppc", "google ads", "paid social", "conversion tracking", "ad creative"],
     ["audit dan scaling akun iklan", "tracking konversi GTM/GA4", "creative testing iklan"]),
    ("product", "Product Division",
     ["product manager", "prioritization", "user feedback", "dx engineer", "roadmap"],
     ["discovery dan PRD", "prioritisasi backlog sprint", "analisis feedback pengguna"]),
    ("project-management", "Project Management Division",
     ["project manager", "sprint planning", "jira", "meeting notes", "scoping"],
     ["koordinasi proyek lintas fungsi", "konversi spesifikasi jadi tugas", "ringkasan rapat terstruktur"]),
    ("research", "Research Division",
     ["literature review", "research synthesist", "evidence synthesis", "citation"],
     ["sintesis literatur dengan evaluasi sumber", "peta bukti berbobot jujur"]),
    ("sales", "Sales Division",
     ["outbound", "discovery call", "meddpicc", "proposal", "pipeline"],
     ["prospeksi signal-based", "kualifikasi deal MEDDPICC", "respons RFP dan proposal"]),
    ("security", "Security Division",
     ["threat model", "penetration test", "incident response", "siem", "appsec"],
     ["arsitektur keamanan dan threat modeling", "pentest otorisasi dan DFIR", "audit kepatuhan SOC 2/ISO 27001"]),
    ("spatial-computing", "Spatial Computing Division",
     ["visionos", "webxr", "ar", "vr", "spatial ui", "metal"],
     ["aplikasi Apple Vision Pro", "pengalaman WebXR berbasis browser", "desain antarmuka spasial"]),
    ("specialized", "Specialized Division",
     ["mcp builder", "orchestrator", "translation", "customer service", "legal review", "recruitment"],
     ["kebutuhan lintas domain yang butuh spesialis", "persona operasional (HR, legal, dukungan)", "tooling MCP dan orkestrasi multi-agen"]),
    ("support", "Support Division",
     ["customer support", "analytics", "finance tracker", "legal compliance", "executive summary"],
     ["operasi dukungan pelanggan", "dashboard analitik dan KPI", "ringkasan eksekutif C-suite"]),
    ("testing", "Testing Division",
     ["qa", "test automation", "performance testing", "api testing", "accessibility audit"],
     ["QA berbasis bukti dan quality gate", "suite E2E Playwright/Cypress", "benchmarks dan analisis hasil test"]),
]

NEXUS = ("nexus", "NEXUS Orchestration Playbooks",
         ["nexus", "multi-agent pipeline", "orchestrator", "quality gates", "startup mvp"],
         ["orkestrasi tim multi-agen lintas divisi", "pipeline produk end-to-end dengan quality gate", "skenario MVP/startup/incident"])

# Division -> short Indonesian capability summary used in the manifest.
CAPABILITY_NOTES = {
    "academic": "worldbuilding akademik: antropologi, geografi, sejarah, narratologi, psikologi, statistika",
    "design": "desain produk: UI, riset UX, arsitektur UX, brand, storytelling visual, whimsy, persona walkthrough",
    "engineering": "rekayasa perangkat lunak: frontend, backend, mobile, AI/ML, DevOps, SRE, database, review, i18n, pembayaran",
    "finance": "keuangan: pembukuan GAAP, analisis keuangan, FP&A, riset investasi, strategi pajak",
    "game-development": "pengembangan game lintas engine: desain sistem, level, audio, narasi, ekonomi, Unity, Unreal, Godot, Blender, Roblox",
    "gis": "geospasial: konsultasi GIS, ETL spasial, geoprocessing, GeoAI, BIM, drone mapping, web GIS, kartografi",
    "healthcare": "kesehatan teregulasi: standar bukti klinis, sistem kesehatan kedaulatan, strategi inovasi",
    "marketing": "pertumbuhan dan pemasaran: growth hacking, konten, platform sosial (global + Tiongkok), SEO/AEO, podcast, PR",
    "paid-media": "media berbayar: PPC, audit akun 200+ poin, tracking & measurement, programmatic, paid social, creative",
    "product": "manajemen produk: prioritisasi sprint, riset tren, sintesis feedback, DX, nudge perilaku, PRD",
    "project-management": "manajemen proyek: producer, shepherd, operasional studio, tracker eksperimen, scoping, Jira, notulen",
    "research": "sintesis riset: literature review, evaluasi sumber, pelacakan sitasi",
    "sales": "penjualan: outbound strategis, discovery coaching, MEDDPICC, sales engineering, proposal, pipeline, coaching",
    "security": "keamanan: arsitektur security, appsec, pentest, cloud security, DFIR, threat intel/detection, SecOps, kepatuhan, blockchain, AI-code audit",
    "spatial-computing": "komputasi spasial: XR interface, visionOS, Metal, WebXR, kontrol kokpit, integrasi terminal",
    "specialized": "spesialis lintas domain: orkestrator multi-agen, MCP builder, generator dokumen, layanan legal/HR/medis/keuangan, penerjemah, dan 40+ lainnya",
    "support": "operasional pendukung: dukungan pelanggan, analitik, pelacakan keuangan, kepatuhan hukum, ringkasan eksekutif, infrastruktur",
    "testing": "pengujian: evidence collector, reality checker, analisis hasil test, benchmark performa, API tester, tool evaluator, a11y audit, otomasi",
    "nexus": "orkestrasi NEXUS: playbook fase 0-6, runbook skenario (startup MVP, kampanye marketing, fitur enterprise, incident), koordinasi multi-agen",
}

# Divisions routed to unified-index "security" / "testing" buckets upstream.
RISK_NOTE = (
    "Seluruh persona adalah panduan perilaku (prompt), bukan executable; "
    "tidak ada tool berbahaya. Persona keamanan tetap butuh otorisasi "
    "eksplisit untuk aktivitas ofensif (lihat docs/SAFETY.md)."
)

FRONTMATTER_DESC = {
    "academic": "6 persona worldbuilding akademik",
    "design": "10 persona desain produk",
    "engineering": "66 persona rekayasa perangkat lunak",
    "finance": "5 persona keuangan",
    "game-development": "21 persona pengembangan game",
    "gis": "13 persona geospasial",
    "healthcare": "3 persona kesehatan teregulasi",
    "marketing": "37 persona pemasaran & growth",
    "paid-media": "7 persona media berbayar",
    "product": "6 persona manajemen produk",
    "project-management": "7 persona manajemen proyek",
    "research": "1 persona sintesis riset",
    "sales": "9 persona penjualan",
    "security": "12 persona keamanan",
    "spatial-computing": "6 persona komputasi spasial",
    "specialized": "59 persona spesialis lintas domain",
    "support": "6 persona operasional pendukung",
    "testing": "9 persona pengujian",
    "nexus": "playbook orkestrasi multi-agen NEXUS",
}


def count_skills(division: str) -> int:
    manifest = json.loads((VENDOR / "skills" / "manifest.json").read_text(encoding="utf-8"))
    if division == "nexus":
        return 0
    return len(manifest["divisions"].get(division, []))


def manifest_for(slug: str, name: str, keywords: list, best_for: list) -> dict:
    n = count_skills(slug)
    sub_skills = []
    if slug == "nexus":
        sub_skills = [
            {"slug": "nexus-quickstart", "role": "panduan mulai cepat pipeline NEXUS"},
            {"slug": "phase-0-discovery", "role": "playbook fase discovery"},
            {"slug": "phase-1-strategy", "role": "playbook fase strategi"},
            {"slug": "phase-2-foundation", "role": "playbook fase fondasi"},
            {"slug": "phase-3-build", "role": "playbook fase build (dev<->qa loop)"},
            {"slug": "phase-4-hardening", "role": "playbook fase hardening"},
            {"slug": "phase-5-launch", "role": "playbook fase launch"},
            {"slug": "phase-6-operate", "role": "playbook fase operasi"},
            {"slug": "scenario-startup-mvp", "role": "runbook skenario startup MVP"},
            {"slug": "scenario-marketing-campaign", "role": "runbook skenario kampanye marketing"},
            {"slug": "scenario-enterprise-feature", "role": "runbook skenario fitur enterprise"},
            {"slug": "scenario-incident-response", "role": "runbook skenario respons insiden"},
        ]
    else:
        vendored_manifest = json.loads((VENDOR / "skills" / "manifest.json").read_text(encoding="utf-8"))
        for entry in vendored_manifest["divisions"].get(slug, []):
            sub_skills.append({"slug": entry["slug"], "role": entry["display_name"]})

    skill_files = [{"path": f"plugin-catalog/agency/{slug}/SKILL.md", "type": "integration-guide"}]
    if slug == "nexus":
        for pb in ["QUICKSTART.md", "nexus-strategy.md", "EXECUTIVE-BRIEF.md"]:
            skill_files.append({"path": f"agency-agents/strategy/{pb}", "type": "upstream-doc"})
        for pb in sorted((VENDOR / "strategy" / "playbooks").glob("*.md")):
            skill_files.append({"path": f"agency-agents/strategy/playbooks/{pb.name}", "type": "upstream-doc"})
    else:
        for entry in sub_skills:
            skill_files.append({
                "path": f"agency-agents/skills/{slug}/{entry['slug']}/SKILL.md",
                "type": "upstream-skill",
            })

    if slug == "nexus":
        description = ("Playbook orkestrasi NEXUS dari The Agency: pipeline multi-agen "
                       "fase 0-6 (discovery -> strategy -> foundation -> build -> hardening -> "
                       "launch -> operate) dengan quality gate antar fase, plus runbook skenario "
                       "startup MVP, kampanye marketing, fitur enterprise, dan respons insiden.")
        capabilities = [CAPABILITY_NOTES[slug]]
    else:
        description = (f"{FRONTMATTER_DESC[slug]} dari The Agency (agency-agents) — "
                       f"{CAPABILITY_NOTES[slug]}. Setiap persona membawa identitas, misi, "
                       "deliverable, dan success metrics yang siap dipakai.")
        capabilities = [CAPABILITY_NOTES[slug],
                        "persona ber-frontmatter (name, description, color, emoji, vibe)",
                        "workflow + deliverable + success metrics per persona"]

    return {
        "$schema": "https://agentenhancements.dev/schema/skill-manifest.v1.json",
        "id": f"agency-{slug}",
        "name": f"The Agency — {name} ({n} personas)" if n else f"The Agency — {name}",
        "slug": slug,
        "category": "agency",
        "version": "1.0.0",
        "status": "integrated-ready",
        "source": {
            "type": "github",
            "url": "https://github.com/msitarzewski/agency-agents",
            "license": "MIT",
            "license_verified": True,
            "vendored": True,
            "vendor_path": "agency-agents/",
        },
        "description": description,
        "capabilities": capabilities,
        "tools_required": [
            "read_file",
            "write_file",
            "edit_file",
            "bash (opsional)",
        ],
        "mcp_servers_suggested": [],
        "trigger_keywords": keywords,
        "best_for": best_for,
        "integration_notes": (
            "Di-vendor penuh di agency-agents/ (MIT, by msitarzewski). 283 persona dikonversi "
            "ke format Agent Skills oleh scripts/convert_agency_agents.py ke agency-agents/skills/ "
            "lalu diagregasi setup.sh ke unified index dengan prefix nama 'agency-'. NEXUS playbook "
            "ada di agency-agents/strategy/ (tidak dikonversi; dibaca langsung sebagai dokumen "
            "orkestrasi). " + RISK_NOTE
        ),
        "sub_skills": sub_skills,
        "skill_files": skill_files,
    }


def skill_md_for(slug: str, name: str, keywords: list) -> str:
    n = count_skills(slug)
    vendored = json.loads((VENDOR / "skills" / "manifest.json").read_text(encoding="utf-8"))
    if slug == "nexus":
        intro = ("Playbook orkestrasi multi-agen NEXUS dari The Agency: siapa mengerjakan apa, "
                 "kapan, dan bagaimana kualitas diverifikasi di setiap fase.")
        use = [
            "Mengorkestrasi beberapa persona Agency dalam satu pipeline produk",
            "Proyek end-to-end: discovery sampai operate dengan quality gate",
            "Skenario siap pakai: startup MVP, kampanye marketing, fitur enterprise, incident response",
        ]
        prereq = [
            "Vendored: `agency-agents/strategy/` di root repo (MIT)",
            "Persona pendukung: pack divisi lain di kategori `agency`",
            "Docs: `agency-agents/strategy/QUICKSTART.md` (mulai 5 menit)",
        ]
        caps = [
            "NEXUS-Full — pipeline lengkap 12-24 minggu (semua divisi)",
            "NEXUS-Sprint — MVP/fitur 2-6 minggu (15-25 agen)",
            "NEXUS-Micro — tugas spesifik 1-5 hari (5-10 agen)",
            "Playbook fase 0-6 dengan quality gate antar fase",
            "Runbook skenario + roster agen per runbook (strategy/runbooks.json)",
        ]
        workflow = [
            "Baca `agency-agents/strategy/QUICKSTART.md` untuk memilih mode (Full/Sprint/Micro).",
            "Aktifkan Agents Orchestrator (pack specialized) sebagai koordinator.",
            "Ikuti playbook fase di `agency-agents/strategy/playbooks/phase-*.md` berurutan.",
            "Lewati quality gate antar fase: bukti wajib untuk semua assessment.",
            "Untuk skenario spesifik, mulai dari `strategy/runbooks/` dan roster JSON-nya.",
        ]
    else:
        entries = vendored["divisions"].get(slug, [])
        sample = ", ".join(e["display_name"] for e in entries[:8])
        intro = (f"{n} persona {name.replace(' Division', '').lower()} dari The Agency: "
                 f"spesialis dengan kepribadian, proses, dan deliverable nyata. Contoh: {sample}.")
        use = [
            f"Task yang cocok dengan {name.replace(' Division', '').lower()} butuh persona spesialis",
            "Butuh panduan perilaku lengkap (identitas, workflow, metrics), bukan prompt generik",
            "Membangun tim AI lintas fungsi dengan persona yang saling melengkapi",
        ]
        prereq = [
            "Vendored: `agency-agents/` di root repo (MIT, oleh msitarzewski)",
            "Skills terkonversi: `agency-agents/skills/" + slug + "/<agent-slug>/SKILL.md`",
            "Semua persona aman (risk: safe); aktivitas ofensif tetap butuh otorisasi eksplisit",
        ]
        caps = [f"**{e['display_name']}** — lihat `agency-agents/skills/{slug}/{e['slug']}/SKILL.md`" for e in entries[:12]]
        if len(entries) > 12:
            caps.append(f"... dan {len(entries) - 12} persona lainnya (lihat manifest.json)")
        workflow = [
            f"Pilih persona dari `agency-agents/skills/{slug}/` (index: manifest.json).",
            "Muat SKILL.md persona tersebut sebagai panduan perilaku sesi ini.",
            "Sebutkan persona by name saat mendispatch sub-tugas (mis. \"gunakan agency-engineering-code-reviewer\").",
            "Kombinasikan lintas divisi lewat registry: `python3 unified-integration/scripts/registry.py search \"<topik>\"`.",
        ]

    lines = [
        "---",
        f"slug: {slug}",
        "category: agency",
        "version: 1.0.0",
        "status: integrated-ready",
        "mcp_servers: []",
        "trigger_keywords: [" + ", ".join(keywords[:5]) + "]",
        "---",
        "",
        f"# The Agency — {name}",
        "",
        intro,
        "",
        "## Kapan dipakai",
        "",
    ]
    lines += [f"- {u}" for u in use]
    lines += ["", "## Prasyarat", ""]
    lines += [f"- {p}" for p in prereq]
    lines += ["", "## Capabilities", ""]
    lines += [f"{i}. {c}" for i, c in enumerate(caps, 1)]
    lines += ["", "## Workflow", ""]
    lines += [f"{i}. {w}" for i, w in enumerate(workflow, 1)]
    lines += [
        "",
        "## Sumber",
        "",
        "Upstream: https://github.com/msitarzewski/agency-agents (MIT, vendored).",
        "Konversi: `python3 scripts/convert_agency_agents.py` (regenerasi `agency-agents/skills/`).",
        "",
    ]
    return "\n".join(lines)


def upsert_agency_entries(catalog: dict, index_entries: list) -> None:
    """Merge generated agency entries into ``catalog["skills"]`` in place.

    Existing entries keep their position and any extra hand-maintained keys,
    but every generated field (name, trigger_keywords, sub_skills_count, ...)
    is refreshed. New ids are appended. Agency entries this generator no
    longer produces (a division removed upstream) are dropped, so the index
    never points at a stale pack.
    """
    generated = {e["id"]: e for e in index_entries}
    skills = []
    seen = set()
    for existing in catalog["skills"]:
        entry_id = existing.get("id")
        if entry_id in generated:
            skills.append({**existing, **generated[entry_id]})
            seen.add(entry_id)
        elif existing.get("category") == "agency" and str(entry_id).startswith("agency-"):
            print(f"  dropped stale catalog entry {entry_id}")
        else:
            skills.append(existing)
    skills.extend(e for e in index_entries if e["id"] not in seen)
    catalog["skills"] = skills


def main() -> int:
    if not VENDOR.is_dir():
        print(f"ERROR: {VENDOR} not found", file=sys.stderr)
        return 2

    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    packs = DIVISIONS + [NEXUS]
    index_entries = []
    for slug, name, keywords, best_for in packs:
        m = manifest_for(slug, name, keywords, best_for)
        (CATALOG_DIR / f"{slug}.json").write_text(
            json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        guide_dir = CATALOG_DIR / slug
        guide_dir.mkdir(parents=True, exist_ok=True)
        (guide_dir / "SKILL.md").write_text(skill_md_for(slug, name, keywords), encoding="utf-8")
        index_entries.append({
            "id": f"agency-{slug}",
            "slug": slug,
            "name": m["name"],
            "category": "agency",
            "version": "1.0.0",
            "status": "integrated-ready",
            "manifest_path": f"plugin-catalog/agency/{slug}.json",
            "guide_path": f"plugin-catalog/agency/{slug}/SKILL.md",
            "trigger_keywords": keywords,
            "mcp_servers": [],
            "source_url": "https://github.com/msitarzewski/agency-agents",
            "source_license": "MIT",
            "vendored": True,
            "sub_skills_count": len(m["sub_skills"]),
        })
        print(f"  wrote plugin-catalog/agency/{slug}.json + {slug}/SKILL.md")

    # Register in catalog.json: upsert the agency entries in place so a
    # re-vendor that changes persona counts or keywords refreshes them.
    catalog = json.loads(CATALOG_INDEX.read_text(encoding="utf-8"))
    if "agency" not in catalog["categories"]:
        catalog["categories"] = catalog["categories"] + ["agency"]
    upsert_agency_entries(catalog, index_entries)
    catalog["total_plugins"] = len(catalog["skills"])
    CATALOG_INDEX.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"catalog.json: {catalog['total_plugins']} plugins, categories={catalog['categories']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
