# Research Skills

Skill untuk deep research, knowledge extraction, dan reasoning multi-step. Total **5 plugin sources**.

| Plugin | Source | Fokus utama |
|--------|--------|-------------|
| Graphify | github.com/Graphify-Labs/ | Text-to-knowledge-graph |
| Agent-Reach | github.com/Panniantong/Agent-Reach | Deep research orchestration |
| Understand Anything | github.com/Egonex-AI/Understand-Anything | Feynman-style layered explanation |
| Last 30 Days | github.com/mvanhorn/ | Date-windowed freshness search |
| REA | github.com/morluto/rea | Reason-Explain-Act loop |

Alur rekomendasi: REA → Agent-Reach → Graphify → Last 30 Days untuk windowing → Understand Anything sebagai fallback explanation.

Semua output research wajib dipersist di `unified-integration/memory/research/` agar lintas sesi.
