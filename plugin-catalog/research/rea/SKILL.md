---
slug: rea
category: research
version: 1.1.0
status: integrated-ready
mcp_servers: []
trigger_keywords: [rea, reverse engineer, decompile, disassemble, binary analysis]
---

# REA (Reverse Engineer Anything)

Upstream: [morluto/rea](https://github.com/morluto/rea) (MIT) - "Reverse engineer anything with agents, from app behavior down to native binaries." REA adalah MCP server yang membuat agen mampu menganalisis cara kerja aplikasi: JavaScript/Electron apps, assembly .NET, APK Android, website, hingga binary native. Analisis berjalan lokal di mesin Anda, dapat terhubung ke disassembler (Ghidra, IDA, Hopper, Binary Ninja), dan setiap kesimpulan disertai bukti pendukung (strings, struktur, perilaku yang teramati).

> Koreksi 2026-11-15: panduan lama mendeskripsikan REA sebagai "Reason-Explain-Act
> research loop". Itu keliru - deskripsi tersebut tidak berasal dari upstream.
> Entri ini kini mengikuti upstream yang sebenarnya.

## Kapan dipakai

- Memahami cara kerja aplikasi/binary yang tidak punya dokumentasi atau source code
- Inspeksi JavaScript/Electron app, .NET assembly, APK Android, atau website
- Riset keamanan yang **berizin** (aset milik sendiri atau memiliki otorisasi tertulis)
- Analisis interoperabilitas dan edukasi rekayasa balik

## Kapan TIDAK dipakai

- Membangun ulang (clone) aplikasi milik pihak lain secara clean-room - itu tugas `replica-skill` (recon → desain → build), dan tetap perlu memperhatikan legalitas
- Riset literatur/multi-sumber - pakai `agent-reach` atau `understand-anything`
- Menganalisis aset yang Anda tidak punya izin untuk dianalisis (ToS, trade secret, hukum setempat)

## Prasyarat

- Instal server upstream: `git clone https://github.com/morluto/rea` lalu ikuti README-nya (MCP server, bukan skill statis)
- Daftarkan server REA ke config MCP host Anda (mis. `~/.claude/mcp.json` atau via `unified-integration/scripts/setup-mcp.sh` bila sudah masuk roadmap)
- Disassembler opsional: Ghidra / IDA / Hopper untuk binary native
- `bash` dan akses baca ke file target

## Workflow

1. **Scope**: konfirmasi target analisis dan otorisasinya (milik sendiri / berizin).
2. **Triage**: minta REA mengidentifikasi jenis target (JS/Electron, .NET, APK, web, native).
3. **Analisis berlapis**: mulai dari perilaku teramati (strings, network, filesystem) turun ke struktur internal; untuk native binary, aktifkan integrasi disassembler.
4. **Kumpulkan bukti**: setiap kesimpulan harus merujuk bukti (alamat, string, call graph, snapshot perilaku).
5. **Laporkan**: ringkasan cara kerja target + daftar bukti + batas analisis (apa yang belum terjawab).

## Inputs

- Path/URL target aplikasi atau binary
- (Opsional) pertanyaan spesifik yang ingin dijawab
- (Opsional) tool eksternal yang tersedia (disassembler)

## Outputs

- Laporan analisis: arsitektur, komponen, alur data, perilaku yang relevan dengan pertanyaan
- Daftar bukti per kesimpulan (lokasi file/alamat/bukti teramati)
- Batas analisis: bagian yang belum bisa disimpulkan dan alasannya

## Contoh

Prompt: "Bagaimana app Electron ini menyimpan license key-nya? Filenya di ./dist/app.asar"

Agen (dengan server REA terpasang): unpack asar → identifikasi modul license → trace pemanggilan → laporkan mekanisme penyimpanan (mis. electron-store di userData) beserta bukti string/path yang ditemukan.

## Batasan & Keamanan

- Hanya untuk riset yang sah: kode/binary milik sendiri atau dengan otorisasi eksplisit
- Jangan menyalin implementasi pihak lain secara langsung untuk produk sendiri
- Hasil analisis bisa salah; verifikasi kesimpulan penting sebelum bertindak atas dasar itu
- REA menjalankan analisis lokal - perhatikan resource untuk binary besar

## Catatan integrasi

- AE tidak mem-vendor server upstream; status `integrated-ready` berarti panduan + routing siap, server dipasang user
- Routing natural-language: "reverse engineer", "decompile", "disassemble", "binary analysis" → skill ini (`dispatch.sh`)
- Untuk clone/rebuild clean-room, dispatcher mengarah ke `replica-skill`
