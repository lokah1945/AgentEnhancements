# Research Skills

Skill untuk deep research, knowledge extraction, dan analisis terbalik (reverse engineering). Total **5 plugin sources**.

| Plugin | Source | Fokus utama |
|--------|--------|-------------|
| Graphify | github.com/Graphify-Labs/ | Text-to-knowledge-graph |
| Agent-Reach | github.com/Panniantong/Agent-Reach | Deep research orchestration |
| Understand Anything | github.com/Egonex-AI/Understand-Anything | Feynman-style layered explanation |
| Last 30 Days | github.com/mvanhorn/ | Date-windowed freshness search |
| REA | github.com/morluto/rea | Reverse Engineer Anything - analisis binary/app dengan bukti |

Alur rekomendasi: Agent-Reach → Graphify → Last 30 Days untuk windowing → Understand Anything sebagai fallback explanation. REA dipakai terpisah saat targetnya adalah memahami cara kerja aplikasi/binary (bukan riset literatur).

Semua output research wajib dipersist di `unified-integration/memory/research/` agar lintas sesi.
