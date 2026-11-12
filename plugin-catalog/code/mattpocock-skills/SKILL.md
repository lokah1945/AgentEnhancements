---
slug: mattpocock-skills
category: code
version: 1.0.0
status: integrated-ready
mcp_servers: [typescript-language-server-mcp, eslint-mcp]
trigger_keywords: [typescript, refactor, types, zod, generics]
---

# Matt Pocock Skills

TypeScript mastery: type narrowing, generics simplification, Zod schema authoring, dan refactoring berbasis tipe.

## Kapan dipakai

- User minta "refactor TS", "ketatkan types", "simplify generics"
- Kode TS gagal compile karena type error kompleks
- Akan tulis schema validasi input (Zod) atau API contract
- Konversi JavaScript ke TypeScript dengan inferensi maksimal

## Prasyarat

- MCP: `typescript-language-server-mcp`, `eslint-mcp`
- Tools: `tsc`, `eslint`, ripgrep, `read_file`, `edit_file`
- Repo target punya `tsconfig.json` (atau siap dibuatkan)

## Capabilities

1. Type narrowing — ganti `any` / `unknown` jadi union discriminated yang aman.
2. Generics simplification — turunkan parameter generic dari inferensi pemanggil.
3. Zod schema authoring — schema-first, derive type via `z.infer`.
4. Refactor patterns — extract type ke `types.ts`, pisah runtime vs type-only import.
5. Conditional types & mapped types — ketika helper type lebih ringan dari runtime code.

## Workflow

1. Baca file target → identifikasi `any`, `unknown`, type-cast yang tidak aman, generic eksplisit berlebihan.
2. Tampilkan ringkasan: tabel smell (`line`, `type`, `code`).
3. Pilih 1-3 smell paling kritis, refactor satu per satu.
4. Jalankan `tsc --noEmit` setelah tiap refactor untuk validasi.
5. Bila schema-driven, buat `schema.ts` dulu, derive type dengan `z.infer`.
6. Tampilkan diff akhir + ringkasan "Type safety: N any removed, M generics inferred."

## Inputs

- File `.ts` / `.tsx` target (path absolut)
- Opsional: `tsconfig.json` bila custom paths
- Opsional: daftar aturan ESLint yang ingin ditegakkan

## Outputs

- File target (modified via `edit_file`)
- `schema.ts` baru bila schema-driven (di direktori yang sama dengan target)
- Diff ringkas ke console / chat
- Laporan JSON opsional: `{file, before_complexity, after_complexity, any_count_delta}`

## Contoh

### Contoh 1 — Hapus `any` di handler Express

Prompt: "Refactor `src/handlers/user.ts` — ketatkan types, hapus `any`."

```
smell list:
  L12  any            user: any
  L45  any            req.body: any
  L67  type-cast      user as User

refactor 1/3: user: any -> User (import dari types.ts)
refactor 2/3: req.body: any -> z.infer<typeof CreateUserSchema>
refactor 3/3: hapus cast `as User` (sudah ter-infer)

tsc --noEmit: OK
Type safety: 3 any removed, 1 cast removed.
```

### Contoh 2 — Simplify generics

Prompt: "Function `groupBy<T, K extends keyof T>(arr: T[], key: K)` terlalu ribet — sederhanakan."

```typescript
// before
function groupBy<T, K extends keyof T>(arr: T[], key: K): Record<T[K], T[]>

// after — infer K dari argumen, key bisa computed
function groupBy<T, K extends string | number>(
  arr: readonly T[],
  key: (item: T) => K
): Record<K, T[]>
```

### Contoh 3 — Zod schema untuk API

Prompt: "Buat validasi input untuk POST /users — body { email, name, age? }."

```typescript
// src/schemas/user.ts
import { z } from "zod";
export const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
  age: z.number().int().positive().optional(),
});
export type CreateUser = z.infer<typeof CreateUserSchema>;
```

## Batasan & Keamanan

- Tidak hapus `any` di file test bila eksplisit di-comment "intentional any for mock".
- Tidak ganti generic bila ada downstream consumer yang masih pakai signature lama.
- Selalu jalankan `tsc --noEmit` setelah refactor; bila gagal, rollback `edit_file`.
- Tidak auto-install dependency baru; tanya user sebelum `npm install zod`.

## Catatan integrasi

- Output SKILL.md ini siap symlink ke `unified-integration/skills/by-category/code/`.
- Bekerja baik bersama `agent-skills-addyosmani` (perf audit) dan `karpathy-skills` (minimal code).
- Untuk repo monorepo, jalankan per-package; jangan cross-package refactor dalam satu sesi.
