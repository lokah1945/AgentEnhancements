---
slug: karpathy-skills
category: code
version: 1.0.0
status: integrated-ready
mcp_servers: []
trigger_keywords:
  - karpathy
  - minimal
  - first-principles
  - think before coding
  - simplicity first
  - surgical changes
  - goal-driven execution
  - code review
  - refactor
---

# Karpathy Skills

Behavioral guidance for **any coding task** — writing, fixing, refactoring,
reviewing, or debugging. Adapted from
`multica-ai/andrej-karpathy-skills`; the four principles below are the upstream
contract. ML/numerical work is one optional application, not a prerequisite.

## Kapan dipakai

- Menulis, memperbaiki, me-refactor, me-review, atau debugging kode
- Kode menjadi berlebih kompleks dan perlu disederhanakan
- Asumsi atau kriteria keberhasilan belum dinyatakan dengan jelas
- (Opsional) Prototipe numerik/ML bila memang dibutuhkan tugas

## Prasyarat

Tidak ada. Tidak ada MCP server, `numpy`, atau `torch` yang wajib dipasang.
Gunakan pustaka hanya bila stdlib terbukti tidak cukup untuk tugas tersebut.

## 1. Think Before Coding

Jangan berasumsi dan jangan menyembunyikan ketidakpastian. Sebelum mengubah
kode, nyatakan asumsi, input, output, serta fungsi logis/matematis yang
menghubungkannya. Bila ada beberapa interpretasi, sampaikan — jangan memilih
secara diam-diam. Bila belum jelas, berhenti dan bertanya.

## 2. Simplicity First

Tulis kode minimal yang menyelesaikan masalah. Tidak ada fitur di luar permintaan,
abstraksi untuk kode sekali pakai, atau konfigurasi yang tidak diminta. Jika 50
baris bisa menjadi 10, tulis ulang.

## 3. Surgical Changes

Sentuh hanya apa yang harus disentuh, dan bersihkan hanya kekacauan yang dibuat
sendiri. Jangan "memperbaiki" komentar atau formatting di sekitar, jangan
me-refactor kode yang tidak rusak, dan ikuti gaya yang ada. Hapus import atau
variabel yang menjadi orphan karena perubahan Anda — bukan dead code bawaan.
Setiap baris yang berubah harus dapat ditelusur ke permintaan pengguna.

## 4. Goal-Driven Execution

Ubah tugas menjadi kriteria yang dapat diverifikasi: "tulis test yang mereproduksi
bug, lalu buat lulus", "pastikan test lulus sebelum dan sesudah refactor". Untuk
tugas bertahap, sebutkan rencana singkat dengan langkah dan cara verifikasinya.
Kriteria yang lemah ("biar jalan") memerlukan klarifikasi berulang.

## Contoh numerik (opsional)

Ketika tugas memang numerik, derivasi dahulu lalu implementasi minimal:

```python
import numpy as np

def softmax(x: np.ndarray) -> np.ndarray:
    # softmax(x_i) = exp(x_i) / sum_j exp(x_j); kurangi max agar stabil
    x = x - x.max(axis=-1, keepdims=True)
    exp = np.exp(x)
    return exp / exp.sum(axis=-1, keepdims=True)
```

Verifikasi dengan input konkret; jangan klaim "works" hanya karena kode terbaca.

## Batasan & Keamanan

- Prinsip ini adalah pedoman perilaku, bukan pengganti `CONTRACT.md`, arsitektur
  proyek, atau aturan gaya setempat.
- Untuk perbaikan darurat, utamakan koreksi terkecil yang terverifikasi.
- Jangan menumpuk instruksi ganda: Ponytail, Superpowers, dan ECC clean-code
  membahas domain yang beririsan. Ikuti aturan prioritas proyek; gunakan satu
  suara, bukan replikasi prinsip yang sama di banyak tempat.

## Catatan integrasi

Keempat prinsip juga tersedia di
`unified-integration/prompts/consolidated-system-prompt.txt` dan `.cursorrules`,
sehingga berlaku tanpa menyebut nama plugin ini secara eksplisit.
