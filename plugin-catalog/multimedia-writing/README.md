# Multimedia & Writing Skills

Skill untuk output multimodal dan humanisasi teks. Total **4 plugin sources**.

| Plugin | Source | Fokus utama |
|--------|--------|-------------|
| Anthropic Skills | github.com/anthropics/ | Structured output, tool use, safety |
| OpenMontage | github.com/OpenMontageInc/ | Video editing + montage pipeline |
| Hyperframes | github.com/heygen-con/ | Personalized talking-head video |
| Humanizer | github.com/blader/humanizer | AI-ism detection + natural voice rewrite |

Aturan keamanan (wajib):
- Hyperframes wajib jalankan **consent gate** sebelum voice cloning.
- Setiap generate multimodal dicatat di audit trail (`unified-integration/memory/audit/`).
- Anthropic Skills jadi baseline behavior — semua skill lain wajib hormati prinsip structured output & tool-use safety-nya.
