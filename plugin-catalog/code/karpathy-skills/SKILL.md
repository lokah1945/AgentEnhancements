---
slug: karpathy-skills
category: code
version: 1.0.0
status: integrated-ready
mcp_servers: [jupyter-mcp, python-repl-mcp]
trigger_keywords: [karpathy, minimal, first-principles, numpy, torch, prototype]
---

# Karpathy Skills

Filosofi Karpathy: minimal, first-principles, derivasi eksplisit, kode pendek yang readable. Cocok untuk ML/numerik, prototype cepat, dan code education.

## Kapan dipakai

- User minta "prototype", "sketch", "minimal implementation"
- Tugas ML/numerik: gradient, attention, MLP, tokenizer
- Ingin mengerti konsep via kode kecil, bukan library
- Ingin review kode untuk identifikasi over-engineering

## Prasyarat

- MCP: `jupyter-mcp`, `python-repl-mcp`
- Tools: `python3`, `numpy`, opsional `torch`
- Akses ke `read_file`, `write_file`, `edit_file`

## Capabilities

1. First-principles derivation — tulis 1-2 kalimat matematika sebelum kode.
2. Minimal Python — implementasi fungsi <= 30 baris tanpa abstraksi dulu.
3. Numpy/Torch codegen — vektorisasi eksplisit, no loop Python bila bisa.
4. No-bullshit code review — tunjukkan bagian over-engineered dan saran hapus.
5. Notebook drafting — susun cell markdown + code selang-seling untuk edukasi.

## Workflow

1. Baca pertanyaan user → saring ke: "apa input? apa output? apa fungsi matematisnya?"
2. Tulis 1-2 kalimat derivasi (mis. "softmax = exp(x_i) / sum_j exp(x_j), stabil dengan subtract max").
3. Tulis fungsi minimal Python dengan docstring <= 3 baris.
4. Jalankan di `python-repl-mcp` dengan 1 contoh input → tunjukkan output.
5. Bila perlu vektorisasi, rewrite dengan numpy; verifikasi output identik.
6. Tampilkan kode final + ringkasan "5 baris, 0 dependency (atau numpy only)".

## Inputs

- Deskripsi konsep / algoritma (teks)
- Opsional: dataset path atau input shape
- Opsional: target framework (numpy / torch / jax)

## Outputs

- File `.py` dengan fungsi minimal (di `scripts/` atau direktori user)
- Opsional: notebook `.ipynb` bila mode edukasi
- Cell output: hasil eksekusi + plot opsional (matplotlib)

## Contoh

### Contoh 1 — Softmax dari nol

Prompt: "Implementasi softmax, jangan pakai library."

```python
import numpy as np

def softmax(x: np.ndarray) -> np.ndarray:
    # stabil: subtract max untuk hindari overflow
    x = x - x.max(axis=-1, keepdims=True)
    exp = np.exp(x)
    return exp / exp.sum(axis=-1, keepdims=True)

# test
assert np.allclose(softmax([0, 0, 0]), [1/3, 1/3, 1/3])
assert np.allclose(softmax([1000, 0]), [1, 0])
```

5 baris, numpy only.

### Contoh 2 — MLP 1 hidden layer untuk XOR

Prompt: "Bikin MLP sederhana untuk XOR."

```python
import numpy as np

def xor_mlp(X, y, hidden=4, lr=0.1, epochs=2000, seed=0):
    rng = np.random.default_rng(seed)
    W1 = rng.normal(size=(2, hidden))
    b1 = np.zeros(hidden)
    W2 = rng.normal(size=(hidden, 1))
    b2 = np.zeros(1)
    for _ in range(epochs):
        h = np.tanh(X @ W1 + b1)
        out = 1 / (1 + np.exp(-(h @ W2 + b2)))
        d_out = (y - out) * out * (1 - out)
        W2 += lr * h.T @ d_out
        W1 += lr * X.T @ (d_out @ W2.T * (1 - h**2))
    return out
```

### Contoh 3 — Code review minimal

Prompt: "Review kode ini, apa bisa lebih minimal? <paste 50 baris>"

Hasil: tunjukkan 3 baris yang bisa dihapus (over-engineered), tunjukkan 1 fungsi yang bisa collapse jadi 5 baris.

## Batasan & Keamanan

- Tidak menulis kode > 50 baris dalam satu fungsi; bila harus, pecah.
- Tidak pakai library berat (transformers, sklearn) bila numpy cukup.
- Tidak tambahkan type hint kompleks bila mengganggu readability.
- Selalu jalankan di REPL sebelum claim "works".

## Catatan integrasi

- Filosofi ini jadi baseline `.cursorrules` global.
- Kombinasikan dengan `gstack` untuk kompresi prompt saat kode sudah panjang.
- Untuk production ML, lanjutkan ke library (torch/jax); SKILL ini hanya untuk prototype.
