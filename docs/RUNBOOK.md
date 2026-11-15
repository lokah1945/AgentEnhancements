---
title: "Operations Runbook & Doctor"
version: "1.1"
last_updated: "2026-11-16"
audience: "Maintainers, on-call"
---

# Runbook — diagnosa & pemulihan AgentEnhancements

## Doctor: pemeriksaan berurutan

Jalankan dari root repo. Setiap langkah menyebut gejala, perintah, dan
tindakan bila gagal.

Pemeriksaan konfigurasi native seluruh host yang dipilih:

```bash
runtime_python="$(bash unified-integration/scripts/setup-mcp.sh --prepare)"
"$runtime_python" unified-integration/scripts/doctor.py --json
```

Doctor menghitung setiap target, termasuk profil Hermes yang hilang atau
gagal, dan keluar nonzero bila ada kegagalan. Pemeriksaan mencakup CLI,
konfigurasi MCP yang benar-benar terpasang, health, serta pemanggilan tool
lokal. Autentikasi model perlu diuji terpisah melalui CLI aslinya.

Uji integrasi CLI dengan model fixture lokal (tanpa akun berbayar):

```bash
"$runtime_python" unified-integration/tests/smoke-native-clis.py --exercise-tools
"$runtime_python" unified-integration/tests/smoke-hermes.py
```

Fixture Codex memberi persetujuan otomatis hanya untuk `ae_health` pada
subproses pengujian. Pengaturan persetujuan global tidak diubah. Uji Hermes
memverifikasi discovery MCP, injeksi skill, serta simpan ringkasan/tugas di
dua profil sementara.

### 1. Bundle vendored utuh?

```bash
python3 - <<'PY'
import json, hashlib
from pathlib import Path
m = json.loads(Path("task-observer/VENDORED.json").read_text())
bad = [r for r, w in m["files"].items()
       if hashlib.sha256((Path("task-observer")/r).read_bytes()).hexdigest() != w]
print("MISMATCH:", bad) if bad else print("OK: bundle pristine")
PY
```

Jika checksum gagal, periksa perubahan dengan `git diff -- task-observer/`.
Pulihkan hanya perubahan yang tidak diperlukan; bundle adalah pin kanonik.

### 2. MCP gateway hidup?

```bash
bash unified-integration/scripts/setup-mcp.sh --prepare   # cetak path venv
bash unified-integration/scripts/setup-mcp.sh --check     # 10/10 harus ok
```

`[FAIL] agent-enhancements` → jalankan gateway manual dengan stderr
terlihat: `python unified-integration/mcp-servers/gateway.py`; kunci
umum: dependensi venv (jalankan ulang --prepare), ui.api.json rusak
(hapus dan `api_config.py init`), backend eksternal tidak dikonfigurasi
(masih ok — hanya `status: unavailable`).

### 3. Konteks sesi dalam budget?

```bash
AGENT_MEMORY_ROOT="$(mktemp -d)" python3 \
  unified-integration/scripts/runtime.py claude-code <<'JSON'
{"hook_event_name":"SessionStart","session_id":"d","cwd":"/tmp"}
JSON
```

Output harus ≤ ~400 token (observer card). Bila membengkak: cek
`~/.claude/skills` → `bash unified-integration/scripts/link-skills.sh
--audit` (instalasi lama `--set all` = 132K+ token; `--migrate`
menurunkannya ke set default dengan aman).

### 4. Discovery routing sehat?

```bash
python3 unified-integration/scripts/registry.py search "buat laporan pdf"
```

5 kartu dengan `ready:` dan `detail:`. Kosong untuk chit-chat itu
benar (abstain by design). Benchmark penuh (recall@5 ≥ 95%,
neg-suppression ≥ 90%): lihat `docs/benchmark/REPORT_2026-11-15.md`.

### 5. Promote/rollback observer?

- Promote gagal `Invalid cross-device link` → versi lama; update.
  Versi sekarang copy-backup → verify → swap lokal (aman lintas-fs).
- Rollback: `task-observer.py rollback --workspace <ws> task-observer`.
  Refusal "verification failed" berarti backup rusak — source TIDAK
  disentuh; periksa `skill-updates/rollback/`.

## Ledger kanal host (siapa menyuntik apa)

| Kanal | Isi | Batas |
| --- | --- | ---: |
| CLAUDE.md/AGENTS.md section | pointer L0 + aturan | ~640 tok |
| SessionStart hook | observer card + memory recall | 250 + 600 |
| UserPromptSubmit hook | 3 kartu skill | 250 |
| Native skills (~/.claude/skills) | deskripsi skill tertaut | 2500 |
| MCP tools/list | skema tool yang diaktifkan | 1800 |

Cold start total ≤ 4.000 token (CONTRACT §8.4). Perubahan kanal baru
wajib mendaftar di `context_budget.COLD_START_CHANNELS` + test CI.

## Keputusan rilis (gates)

1. `run-tests.py` 100% (skip by design hanya untuk env-dependen).
2. `setup-mcp.sh --check` 10/10.
3. Routing benchmark ≥95%/≥90% (dataset 41+10 di docs/benchmark).
4. `git diff --exit-code -- skills/` setelah scaffold+generate (no drift).
5. Bundle checksum pristine.
