---
slug: anthropic-skills
category: multimedia-writing
version: 1.0.0
status: integrated-ready
mcp_servers: [filesystem-mcp, pdf-mcp, vision-mcp]
trigger_keywords: [anthropic, structured, tool use, multimodal, safety]
---

# Anthropic Skills

Skill referensi dari Anthropic: structured outputs, tool use best practices, document QA, dan multimodal handling. Membentuk baseline 'responsible agent' untuk repo ini.

## Kapan dipakai

- Skill lain butuh baseline pattern untuk structured output / tool use
- Operasi multimodal (image / PDF) perlu safe handling
- Mode "safety-critical" diaktifkan user
- Compliance: butuh audit trail setiap tool call

## Prasyarat

- MCP: `filesystem-mcp`, `pdf-mcp`, `vision-mcp`
- Tools: `bash`, `read_file`, `write_file`, `web_search`
- Wajib jadi dependency default semua skill lain

## Capabilities

1. Structured output enforcement — JSON schema, validate before emit.
2. Safe tool-use patterns — preview before apply, consent gate for destructive.
3. Document QA — PDF/image → structured extraction.
4. Multimodal (image/PDF) handling — analyze, caption, OCR.

## Workflow

1. **Pattern enforcement**: sebelum skill lain balas data, validasi struktur output sesuai schema.
2. **Tool-use safety**:
   - Preview destructive action (file write, MCP call) sebelum eksekusi.
   - Log setiap tool call ke `audit/mcp-calls.jsonl`.
3. **Document QA**:
   - Buka PDF via `pdf-mcp` → extract text per page.
   - Bila image, kirim ke `vision-mcp` → structured response.
4. **Multimodal handling**:
   - Image di-prompt: caption + structured description.
   - PDF: text + layout + reference number.

## Inputs

- Tugas dari skill lain (untuk baseline pattern)
- Opsional: dokumen (PDF/image) untuk QA mode
- Opsional: JSON schema untuk validasi output

## Outputs

- Validated JSON output (kalau dipanggil untuk enforcement)
- Structured extraction (kalau mode QA)
- Audit entry di `unified-integration/memory/audit/`

## Contoh

### Contoh 1 — Enforce structured output

Skill lain ingin balas: `{status, data, error}`.

```
enforce schema:
  status: enum [ok, error]
  data: object
  error: string?

validate output skill lain:
  {status: "ok", data: {...}, error: null} -> PASS
  {status: "ok"} -> FAIL (data missing) -> reject
  {status: "ok", data: ..., extra: ...} -> WARN (extra field)
```

### Contoh 2 — Document QA: invoice

Prompt: "Ekstrak data dari `invoice-001.pdf`."

```
mode: QA
pdf-mcp extract: 3 page
page 1: header "INVOICE", nomor INV-2026-001
page 2: line items
page 3: total + signature

structured output:
{
  "invoice_number": "INV-2026-001",
  "date": "2026-11-01",
  "issuer": {"name": "...", "address": "..."},
  "items": [
    {"desc": "Server 16 core", "qty": 1, "price": 200},
    ...
  ],
  "total": 1200,
  "currency": "USD"
}
audit log: audit/mcp-calls.jsonl +1 entry
```

### Contoh 3 — Multimodal image analysis

Prompt: "Tolong caption gambar `screenshot.png`."

```
vision-mcp call:
  image: screenshot.png (base64)
  prompt: "Caption this screenshot. Extract visible UI elements."

response (structured):
{
  "caption": "Dashboard with sidebar navigation and main content area",
  "elements": [
    {"type": "sidebar", "items": ["Home", "Settings", "Logout"]},
    {"type": "card", "title": "Revenue", "value": "$42K"}
  ],
  "text_extracted": ["Revenue", "$42K", "+12% MoM"]
}
```

## Batasan & Keamanan

- Tidak mengakses file di luar workspace user.
- Tidak expose data PII ke log; mask sebelum audit.
- Untuk dokumen sensitif (medis, legal), jalankan dengan explicit user consent + retention policy.
- Tidak auto-share ke third-party; vision/PDF call via approved MCP only.

## Catatan integrasi

- Skill ini **wajib jadi baseline** semua skill lain (lihat `.cursorrules`).
- Untuk compliance enterprise, aktifkan `audit-mode: strict` (log full args, hash output).
- Untuk data sensitif, prefer local model (OCR via tesseract, vision via lokal VLM).
- Bersama `humanizer`: Anthropic jaga struktur, Humanizer jaga tone — output campuran.
