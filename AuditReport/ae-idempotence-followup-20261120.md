---
title: AE first-reinstall YAML idempotence followup
version: '1.0'
last_updated: '2026-11-20'
audience: maintainers, auditors
---

# Idempotensi YAML pada instalasi kedua — 20 November 2026

Lanjutan dari [audit utama](ae-end-to-end-audit-report-20261119.md).
PR #9 sudah merge sebagai `115b65b3`; pengujian instalasi yang diperluas
menemukan satu P2 tambahan sebelum penutupan akhir. Total temuan yang
diperbaiki menjadi 31: P0 0, P1 13, P2 17, P3 1. Delapan residual pada
audit utama tetap dicatat; dua cacat iterasi publikasi CI terpisah dari
hitungan temuan awal ini.

## AE26-31 — P2 — Reinstall YAML mengubah format dan membuat backup

- Lokasi: `unified-integration/setup.sh:1580`, `merge_yaml_config`.
- Bukti: dua setup commit `2ea786cd` dengan HOME baru di dalam clone
  sama-sama exit 0 (150.340/150.384 detik), tetapi setup kedua mengubah
  `.gemini/config.yaml` dan membuat satu backup. Nilai YAML tetap sama;
  kutipan, komentar dan line wrapping berubah. Probe ini mencakup file
  yang belum tercakup perbandingan 19 konfigurasi sebelumnya.
- Reproduksi: jalankan setup dua kali pada HOME kosong dengan Gemini
  terdeteksi, atau jalankan helper merge dua kali pada reference YAML yang
  mengandung kutipan. Bandingkan byte konfigurasi dan daftar backup.
- Akar masalah: instalasi pertama menulis YAML asli; merge selanjutnya
  menserialisasikan ulang dengan PyYAML sebelum membandingkan byte.
  Perbaikan AE-17 sebelumnya hanya menghindari backup untuk hasil yang
  sudah byte-identik, sehingga kasus format awal belum tertangani.
- Perbaikan: bandingkan representasi YAML canonical sebelum/sesudah merge.
  Jika nilai sama, pertahankan teks asli beserta komentar/kutipannya.
  Perubahan nilai riil tetap diterapkan, field pengguna dipertahankan dan
  file asli tetap dibackup. Canonical YAML membedakan boolean dari integer.
- Status: diperbaiki oleh `1b3951edb80ff8cb7556f7339d6f4c53a453833c`.
- Regresi: dua tes baru pada `test_setup_safety.py` gagal sebelum fix;
  seluruh sembilan setup-safety tests kemudian lulus. Tes juga memastikan
  perubahan hook yang riil tidak terabaikan serta backup mempertahankan
  konfigurasi pengguna asli.

## Bukti dan gate publikasi

[Evidence terstruktur](evidence/ae-yaml-idempotence-20261120.json) memuat
exit/timing/hash log tanpa nilai credential. Full integration suite pada
clone mandiri, setup ulang dengan HOME baru, dan seluruh CI tetap menjadi
gate sebelum merge followup. Hasil master terakhir dicantumkan pada PR
followup dan respons eksekusi akhir; hasil yang masih berjalan saat
laporan ditulis tidak diberi label lulus.

Log diagnostik OpenCode juga berubah saat CLI diperiksa. Log operasi
dibedakan dari konfigurasi ketika mengevaluasi idempotensi; semua path
tersebut tetap berada di HOME terisolasi dalam checkout. Tidak ada test CI
yang dilewati atau threshold yang diubah.
