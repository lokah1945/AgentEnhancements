---
slug: replica-skill
category: code
version: 1.0.0
status: integrated-ready
mcp_servers: [browser-tools-mcp, vision-mcp]
trigger_keywords: [clone app, replica, reverse engineer, rebuild app, build my own version]
---

# Replica Skill (11 sub-skills)

Sebelas skill yang meng-clone aplikasi apa pun secara clean-room: dari
reverse-engineering sampai deploy. Di-vendor penuh di `replica-skill/` (MIT,
by Jake Schincariol). Terverifikasi 8.7k stars.

## Kapan dipakai

- User minta "clone app X", "bangun versi saya sendiri dari X"
- Ingin tahu "bagaimana X bekerja" (recon saja)
- Analisis kompetitor berbasis fitur + keluhan user
- Ingin rebuild MVP dari aplikasi existing tanpa menyalin asetnya

## Prasyarat

- Vendored: `replica-skill/` di root repo (sudah termasuk LICENSE MIT)
- Tools: Python 3.8+ (stdlib only, tidak ada pip install), `read_file`, `write_file`, `edit_file`
- MCP opsional: `browser-tools-mcp` (recon), `vision-mcp` (analisis screenshot)

## Capabilities

1. **replica-recon** — reverse-engineer app: screens, flows, components, data model, features.csv
2. **replica-architect** — plan stack, database schema, API
3. **replica-design** — rebuild design system sebagai tokens (WCAG contrast check)
4. **replica-build** — rebuild app screen-by-screen dari recon map
5. **replica-backend** — auth, database, payments, integrations
6. **replica-test** — test plan + Playwright specs + bug report by severity
7. **replica-diff** — parity score vs original (imgdiff edge-map, features parity)
8. **replica-entrepreneur** — mine keluhan user dari review asli (linked quotes only)
9. **replica-brand** — naming, rebrand, sweep codebase dari sisa original
10. **replica-launch** — landing page, pricing, store listing (dengan limit checks)
11. **replica-deploy** — preflight (tests, parity, sweep, listing) + production deploy

## Workflow

Jalankan berurutan; tiap skill membaca output skill sebelumnya di `replica/` folder project:

```
recon -> architect -> design -> build -> backend -> test -> diff
      -> entrepreneur -> brand -> launch -> deploy
```

1. **recon** dengan URL app: baca help center, pricing, store listing, walkthrough
   public + akun sendiri. Output: `replica/recon.md` (screens, flows, data model)
   + `replica/features.csv`.
2. **architect**: pilih stack, tulis schema, urutkan build (flow kritis dulu).
3. **design**: ukur screenshot jadi tokens: color roles, type scale, spacing, spec komponen.
4. **build**: bangun shell, lalu flow utama, lalu semua screen + states, centang features.csv.
5. **backend**: signup, integrasi (Google API dengan key user), Stripe, email.
6. **test**: test plan dari flows, Playwright specs happy path + edge cases, bug by severity
   sampai tidak ada S1/S2 open.
7. **diff**: parity score (must/should/could weighting, partial = setengah).
8. **entrepreneur**: baca review asli (App Store, G2, Capterra, Reddit); tiap keluhan
   dengan count + link. Fix plan + positioning angle.
9. **brand**: nama baru + cek trademark, palette baru, logo brief, voice, lalu sweep
   codebase sampai bersih dari original.
10. **launch**: landing page di sekitar angle, pricing vs original, store listing lint.
11. **deploy**: preflight (tests pass, parity, sweep clean, listing OK), production setup,
    DNS records, ship saat user bilang go.

## Inputs

- URL aplikasi target (atau App Store link)
- Screenshot opsional
- Akun sendiri (untuk flows yang butuh login — hanya akun milik sendiri)

## Outputs

Di folder `replica/` project user:
- `replica/recon.md` + `replica/features.csv`
- `replica/architecture.md`
- `replica/design/tokens.json`
- Source code clone
- `replica/test-plan.md`, `replica/bug-report.md`
- Parity score + missing list
- `replica/reviews.csv` + themes + fix plan
- Brand assets + sweep report
- `replica/launch/listing.json` + landing page
- Deployment + DNS records

## Contoh

### Contoh 1 — Clone scheduling app

Prompt: "Clone Calendly-like scheduling app."

```
recon: 18 screens, 7 flows, data model (users, event types, availability,
  bookings), features.csv 86 fitur. Partner marketplace: out of scope.
architect: Next.js + Postgres + Stripe + Resend; constraint anti double-book.
design: tokens dari screenshot; 8px spacing; date picker + slot button spec.
build: shell -> booking flow -> semua screen + states.
backend: signup, Google Calendar (key user), Stripe, reminder email.
test: 7 flow test plan, Playwright specs, 0 S1/S2 open.
diff: features 86 (semua must-have done), booking layout 91.
  Missing: round-robin teams, website embed.
entrepreneur: 140 review (App Store/G2/Capterra/Reddit). Top: per-seat price,
  no SMS reminder, timezone confusion. Fix: flat pricing, SMS, tz confirm step.
brand: nama baru + trademark check + sweep clean.
launch: landing page + pricing vs original + listing lint.
deploy: preflight pass -> production + DNS -> live.
```

### Contoh 2 — Hanya recon untuk analisis kompetitor

Prompt: "How does Notion's permission system work? Map it out."

```
recon saja: screen inventory permission-related, flows (invite, share,
  member role change), component list, inferred data model.
Output: replica/recon.md (partial scope: permissions).
Tidak lanjut build — user hanya butuh peta.
```

### Contoh 3 — Cek ide sebelum build

Prompt: "Should I clone a per-seat-priced SaaS? What do users hate?"

```
entrepreneur saja pada target app: baca review, keluhan per-seat pricing
  (count + link), fix plan flat pricing.
Angle: "untuk tim kecil yang benci per-seat".
Keputusan: layak build (keluhan kuat + angle jelas).
```

## Batasan & Keamanan (enforced by skills)

- **Clean-room only**: rebuild fungsi dan UX pattern. TIDAK PERNAH menyalin
  source code, aset proprietary, logo, trademark, copy, atau private API target.
- **Hanya baca yang boleh dibaca**: halaman public + akun sendiri. Tidak scrape
  di balik login orang lain, tidak melanggar ToS, tidak menembus paywall.
- **Wajib rebrand sebelum launch**: `/replica-deploy` menolak ship selama
  `sweep.py` masih menemukan nama/domain/warna original.
- **Entrepreneur tidak mengarang**: semua review/quote punya link; sample size
  dinyatakan; tema dengan < 3 review atau 1 sumber ditandai "thin".
- **Cek legal sebelum jualan**: jalankan trademark check yang `/replica-brand`
  daftar; konsultasi lawyer bila ada uang di atas meja.

## Catatan integrasi

- Vendored di `replica-skill/` — ikut pipeline agregasi `setup.sh`
  (source "replica-skill"), jadi 11 sub-skill otomatis masuk
  `unified-integration/skills/by-category/` dan unified index.
- Skill upstream bisa dipanggil langsung (`/replica-recon` dst.) atau via
  dispatcher dengan trigger "clone app" / "reverse engineer".
- Kompatibel dengan orchestrator: BMAD (build mode) bisa memakai recon/architect
  sebagai input Analyst/Architect persona.
- Tools lokal (imgdiff.py, parity.py, reviews.py, contrast.py, sweep.py,
  listing.py) stdlib-only, tidak menyentuh network.
