# Phase 1 — Mobile Quick-Log (Progress) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Progress claim stream of `/log` — mobile-first, ≤3 taps cold-launch-to-saved, offline-first via `idb-keyval`, fires the "Logged!" confirmation off the IndexedDB write so 4G latency doesn't bleed into UX.

**Architecture:** Client-heavy Next.js 16 App Router. Pure-logic libraries (`money`, `queue`, `unit-type`) carry the load-bearing invariants and are TDD-tested. React components are verified on the dev server against the real Supabase. An offline queue with four-state status (`pending | in_flight | failed | dead`) guarantees append-only writes with client-generated UUIDv4 as the idempotency key; duplicate-PK (`23505`) at drain means "server already accepted" → remove from queue.

**Tech Stack:** Next.js 16.2.3, React 19.2.4, TypeScript strict, Tailwind v4, Supabase JS 2.103, `idb-keyval` 6.2.1, `vitest` + `fake-indexeddb` (added in Task 0), `@vitest/coverage-v8`.

**Spec:** [`docs/superpowers/specs/2026-04-20-phase1-mobile-quick-log-design.md`](../specs/2026-04-20-phase1-mobile-quick-log-design.md)

**Schema precondition:** Commit `b5628f5` applied migration `sql/03-phase1-claim-kind.sql`. New columns (`claim_kind`, `over_budget`, `captured_at`, `captured_lat`, `captured_lng`, `captured_accuracy_m`) are live and enforced on new inserts via `claim_kind_shape` CHECK.

---

## File structure

```
src/
  lib/
    money.ts              Money branded type, parse/format/math helpers (pure)
    money.test.ts
    unit-type.ts          unitTypeToInputMode() mapping (pure)
    unit-type.test.ts
    claim-payload.ts      DollarClaim/PercentClaim/HoursClaim/QtyClaim discriminated union + build helpers
    claim-payload.test.ts
    queue.ts              QueuedClaim type, enqueue, loadAll, remove, classifyResponse, computeNextRetry (pure + idb-keyval IO)
    queue.test.ts         uses fake-indexeddb
    queue-drain.ts        drain() — orchestrates queue + Supabase client
    queue-drain.test.ts   mocked supabase client
    use-offline-queue.ts  React hook: wires drain triggers, exposes queue state
    use-job-state.ts      React hook: localStorage sticky last job
    use-recent-items.ts   React hook: queries install_claims for this job/week/user
  app/
    log/
      page.tsx                          Progress stream page, composes components
      components/
        JobHeader.tsx                   job name + Change chip + pending chip
        ItemPicker.tsx                  recents + search + category chips
        ClaimInput.tsx                  smart single-field input
        SaveConfirmation.tsx            slide-down banner + haptic
        PendingChip.tsx                 queue count + red-dot
        TodaysClaimsList.tsx            session-only append list
      pick-job/
        page.tsx                        recent jobs + search sheet
    dashboard/
      page.tsx                          MODIFY: add "Log a claim" button
vitest.config.ts                        NEW
vitest.setup.ts                         NEW (fake-indexeddb, jest-dom-free — we only unit-test logic)
```

---

### Task 0: Test infrastructure scaffold

**Files:**
- Create: `vitest.config.ts`
- Create: `vitest.setup.ts`
- Modify: `package.json` (add scripts + dev deps)

- [ ] **Step 1: Install test deps**

```bash
cd "C:/Users/ScottTextor/CLAUDE CODE/hytek-budget" && npm install --save-dev vitest@^2 @vitest/coverage-v8@^2 fake-indexeddb@^6
```

- [ ] **Step 2: Create `vitest.config.ts`**

```ts
import { defineConfig } from 'vitest/config'
import { resolve } from 'node:path'

export default defineConfig({
  resolve: {
    alias: { '@': resolve(__dirname, './src') },
  },
  test: {
    environment: 'node',
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.test.ts'],
    coverage: { reporter: ['text'] },
  },
})
```

- [ ] **Step 3: Create `vitest.setup.ts`**

```ts
// Provide an in-memory IndexedDB so idb-keyval works in Node test env.
import 'fake-indexeddb/auto'
```

- [ ] **Step 4: Add test scripts to `package.json`**

Modify `scripts` block:

```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "eslint",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

- [ ] **Step 5: Write a smoke test**

Create `src/lib/smoke.test.ts`:

```ts
import { describe, it, expect } from 'vitest'

describe('smoke', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2)
  })
})
```

- [ ] **Step 6: Run the smoke test**

Run: `npm test`
Expected: 1 passed. If vitest complains about module resolution, re-check `vitest.config.ts` alias and `include` glob.

- [ ] **Step 7: Delete smoke test, commit**

```bash
rm src/lib/smoke.test.ts
git add vitest.config.ts vitest.setup.ts package.json package-lock.json
git commit -m "chore: add vitest + fake-indexeddb for pure-logic unit tests"
```

---

### Task 1: Live-DB probe — confirm unit_type values and rate-card seeding

**Goal:** Before writing `unit-type.ts` or the rate-card lookup, query the live Supabase to know what actual values exist. No code in this task — produces a findings note that informs Tasks 3 and 8.

**Files:**
- Create: `docs/superpowers/notes/2026-04-20-phase1-db-probe.md`

- [ ] **Step 1: Probe distinct unit_types**

Open Supabase SQL Editor (same project as before) and run:

```sql
SELECT unit_type, COUNT(*) AS item_count
FROM public.install_budget_items
WHERE unit_type IS NOT NULL
GROUP BY unit_type
ORDER BY item_count DESC;
```

Record all distinct values + counts.

- [ ] **Step 2: Probe install_company_services structure**

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'install_company_services'
ORDER BY ordinal_position;

SELECT COUNT(*) AS total_services,
       COUNT(DISTINCT company_id) AS companies,
       COUNT(DISTINCT category) AS categories
FROM public.install_company_services;

SELECT category, unit, rate
FROM public.install_company_services
WHERE effective_to IS NULL
LIMIT 20;
```

Record the shape so Task 8 can join correctly.

- [ ] **Step 3: Probe claim_kind distribution of legacy rows**

```sql
SELECT claim_kind, COUNT(*) FROM install_claims GROUP BY claim_kind;
```

- [ ] **Step 4: Write findings to notes file**

Create `docs/superpowers/notes/2026-04-20-phase1-db-probe.md` with sections:
1. Distinct `install_budget_items.unit_type` values and counts (copy from Step 1)
2. `install_company_services` columns + sample (copy from Step 2)
3. `install_claims.claim_kind` distribution (copy from Step 3)
4. Any surprises — values you didn't expect, NULLs you have to handle

- [ ] **Step 5: Commit findings**

```bash
git add docs/superpowers/notes/2026-04-20-phase1-db-probe.md
git commit -m "docs(notes): Phase 1 live DB probe — unit_types, rate cards, legacy claim_kinds"
```

---

### Task 2: Money utility library

**Files:**
- Create: `src/lib/money.ts`
- Test: `src/lib/money.test.ts`

- [ ] **Step 1: Write failing tests**

Create `src/lib/money.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import {
  parseAudCentsFromString,
  parseAudCentsFromNumeric,
  formatAud,
  type Money,
} from './money'

describe('parseAudCentsFromString', () => {
  it('parses plain number', () => {
    expect(parseAudCentsFromString('100')).toBe(10000)
  })
  it('parses with dollar sign', () => {
    expect(parseAudCentsFromString('$100')).toBe(10000)
  })
  it('parses with commas', () => {
    expect(parseAudCentsFromString('$1,000.50')).toBe(100050)
  })
  it('parses negative', () => {
    expect(parseAudCentsFromString('-$50.25')).toBe(-5025)
  })
  it('rejects NaN', () => {
    expect(() => parseAudCentsFromString('abc')).toThrow(/Invalid amount/)
  })
  it('rejects >2 decimals', () => {
    expect(() => parseAudCentsFromString('1.234')).toThrow(/Invalid amount/)
  })
  it('rejects empty', () => {
    expect(() => parseAudCentsFromString('   ')).toThrow(/Invalid amount/)
  })
  it('rejects overflow', () => {
    expect(() => parseAudCentsFromString('1e20')).toThrow(/Invalid amount/)
  })
})

describe('parseAudCentsFromNumeric', () => {
  it('converts Supabase numeric to cents', () => {
    expect(parseAudCentsFromNumeric(1234.56)).toBe(123456)
  })
  it('handles zero', () => {
    expect(parseAudCentsFromNumeric(0)).toBe(0)
  })
  it('handles null as null', () => {
    expect(parseAudCentsFromNumeric(null)).toBeNull()
  })
  it('rounds half-away-from-zero on third decimal', () => {
    expect(parseAudCentsFromNumeric(0.125)).toBe(13)
    expect(parseAudCentsFromNumeric(-0.125)).toBe(-13)
  })
})

describe('formatAud', () => {
  it('formats cents to AUD string', () => {
    expect(formatAud(123456 as Money)).toBe('$1,234.56')
  })
  it('formats zero', () => {
    expect(formatAud(0 as Money)).toBe('$0.00')
  })
  it('formats negative', () => {
    expect(formatAud(-5025 as Money)).toBe('-$50.25')
  })
})
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `npm test`
Expected: all tests fail with "module not found" for `./money`.

- [ ] **Step 3: Implement `src/lib/money.ts`**

```ts
// AUD money arithmetic — stored as integer cents to avoid IEEE 754 errors.
// Panel #2 Mathematician §8: single source of truth for currency parsing,
// formatting, and addition across the app.

export type Money = number & { readonly __brand: 'AUD_cents' }

const DECIMAL_PATTERN = /^-?\d+(\.\d{1,2})?$/
const AUD_FORMATTER = new Intl.NumberFormat('en-AU', {
  style: 'currency',
  currency: 'AUD',
})

export function parseAudCentsFromString(input: string): Money {
  const trimmed = input.trim()
  if (!trimmed) throw new Error('Invalid amount')
  const sanitized = trimmed.replace(/[,$\s]/g, '')
  if (!DECIMAL_PATTERN.test(sanitized)) throw new Error('Invalid amount')
  const dollars = Number.parseFloat(sanitized)
  if (!Number.isFinite(dollars)) throw new Error('Invalid amount')
  const cents = Math.round(dollars * 100)
  if (!Number.isSafeInteger(cents)) throw new Error('Invalid amount')
  return cents as Money
}

export function parseAudCentsFromNumeric(input: number | null): Money | null {
  if (input === null || input === undefined) return null
  if (!Number.isFinite(input)) return null
  // Half-away-from-zero rounding (documented policy).
  const sign = input < 0 ? -1 : 1
  const cents = sign * Math.round(Math.abs(input) * 100)
  return cents as Money
}

export function formatAud(cents: Money | number): string {
  const dollars = Number(cents) / 100
  return AUD_FORMATTER.format(dollars)
}

export function addMoney(a: Money, b: Money): Money {
  return ((a as number) + (b as number)) as Money
}

export function multiplyMoney(a: Money, scalar: number): Money {
  return Math.round((a as number) * scalar) as Money
}
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `npm test`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/lib/money.ts src/lib/money.test.ts
git commit -m "feat(money): AUD cents-native Money type + parse/format/math helpers

Single source of truth for currency arithmetic. Panel #2 Mathematician §8
decision: store as integer cents in TS, convert at Supabase boundary.
Round half-away-from-zero, reject >2 decimals, reject overflow."
```

---

### Task 3: Unit-type → input-mode mapping

**Files:**
- Create: `src/lib/unit-type.ts`
- Test: `src/lib/unit-type.test.ts`

**Prerequisite:** Task 1 DB probe findings, specifically the distinct `unit_type` values. If probe reveals different values than the spec assumed, update the mapping below to match reality.

- [ ] **Step 1: Write failing tests**

Create `src/lib/unit-type.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { unitTypeToInputMode } from './unit-type'

describe('unitTypeToInputMode', () => {
  it('maps hours-like', () => {
    for (const ut of ['hours', 'hrs', 'h', 'HOURS']) {
      expect(unitTypeToInputMode(ut).mode).toBe('hours')
    }
  })
  it('maps area-like to percent when budget_amount known', () => {
    const m = unitTypeToInputMode('m2', { budgetAmountCents: 100000 })
    expect(m.mode).toBe('percent')
  })
  it('maps area-like to qty when no budget', () => {
    const m = unitTypeToInputMode('m2', { budgetAmountCents: null })
    expect(m.mode).toBe('qty')
  })
  it('maps lift-like to qty', () => {
    expect(unitTypeToInputMode('lifts').mode).toBe('qty')
    expect(unitTypeToInputMode('each').mode).toBe('qty')
  })
  it('maps percent-like to percent', () => {
    expect(unitTypeToInputMode('%').mode).toBe('percent')
    expect(unitTypeToInputMode('pct').mode).toBe('percent')
  })
  it('defaults to dollar for null', () => {
    expect(unitTypeToInputMode(null).mode).toBe('dollar')
  })
  it('defaults to dollar for unknown', () => {
    expect(unitTypeToInputMode('somethingweird').mode).toBe('dollar')
  })
  it('hours mode label + keyboard', () => {
    const m = unitTypeToInputMode('hours')
    expect(m.label).toMatch(/hours/i)
    expect(m.inputMode).toBe('decimal')
  })
  it('percent mode caps at 100', () => {
    const m = unitTypeToInputMode('%')
    expect(m.max).toBe(100)
    expect(m.min).toBe(0)
  })
})
```

- [ ] **Step 2: Run tests — verify fail**

Run: `npm test -- unit-type`
Expected: fail.

- [ ] **Step 3: Implement `src/lib/unit-type.ts`**

```ts
// Map install_budget_items.unit_type → the input field shape installer sees.
// Panel #2 UX decision: one smart field, not a $/%/hrs/qty toggle — the data
// model already knows which mode applies.

import type { ClaimKind } from './types'

export interface InputMode {
  mode: ClaimKind
  label: string
  inputMode: 'numeric' | 'decimal'
  step: number
  min?: number
  max?: number
}

interface Context {
  budgetAmountCents?: number | null
}

const normalize = (ut: string): string => ut.trim().toLowerCase()

const HOURS_TOKENS = new Set(['hours', 'hrs', 'h', 'hour'])
const AREA_TOKENS = new Set(['m2', 'sqm', 'm²', 'area'])
const QTY_TOKENS = new Set(['lift', 'lifts', 'qty', 'each', 'unit', 'units', 'ea'])
const PERCENT_TOKENS = new Set(['%', 'pct', 'percent'])

export function unitTypeToInputMode(
  unitType: string | null,
  ctx: Context = {}
): InputMode {
  if (!unitType) return dollarMode()
  const t = normalize(unitType)

  if (HOURS_TOKENS.has(t)) {
    return { mode: 'hours', label: 'Hours worked today', inputMode: 'decimal', step: 0.25, min: 0 }
  }
  if (AREA_TOKENS.has(t)) {
    if (ctx.budgetAmountCents != null && ctx.budgetAmountCents > 0) {
      return { mode: 'percent', label: '% complete', inputMode: 'numeric', step: 1, min: 0, max: 100 }
    }
    return { mode: 'qty', label: 'm² today', inputMode: 'decimal', step: 0.5, min: 0 }
  }
  if (QTY_TOKENS.has(t)) {
    return { mode: 'qty', label: 'Units today', inputMode: 'numeric', step: 1, min: 0 }
  }
  if (PERCENT_TOKENS.has(t)) {
    return { mode: 'percent', label: '% complete', inputMode: 'numeric', step: 1, min: 0, max: 100 }
  }
  return dollarMode()
}

function dollarMode(): InputMode {
  return { mode: 'dollar', label: '$ claimed', inputMode: 'decimal', step: 0.01, min: 0 }
}
```

- [ ] **Step 4: Run tests — verify pass**

Run: `npm test -- unit-type`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/lib/unit-type.ts src/lib/unit-type.test.ts
git commit -m "feat(unit-type): map install_budget_items.unit_type to smart input mode

No $/%/hrs/qty toggle — unit_type drives label + keyboard. Unknown values
fall back to dollar input. Mapping verified against live DB probe values."
```

---

### Task 4: Claim payload types + build helpers

**Files:**
- Create: `src/lib/claim-payload.ts`
- Test: `src/lib/claim-payload.test.ts`

- [ ] **Step 1: Write failing tests**

Create `src/lib/claim-payload.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { buildClaimRow, type ClaimPayload } from './claim-payload'

const base = {
  userId: 'user-uuid',
  jobId: 'job-uuid',
  budgetItemId: 'item-uuid',
  claimDate: '2026-04-20',
}

describe('buildClaimRow', () => {
  it('builds dollar claim', () => {
    const p: ClaimPayload = { kind: 'dollar', amountCents: 10050, notes: 'ok' }
    const row = buildClaimRow(p, base)
    expect(row.claim_kind).toBe('dollar')
    expect(row.claim_amount).toBe(100.5)
    expect(row.percent_complete).toBeNull()
    expect(row.hours).toBeNull()
    expect(row.qty).toBeNull()
    expect(row.notes).toBe('ok')
    expect(typeof row.id).toBe('string')
    expect(row.id.length).toBeGreaterThan(30) // uuid
    expect(row.captured_at).toBeTruthy()
  })

  it('builds percent claim — app computes claim_amount from budget', () => {
    const p: ClaimPayload = { kind: 'percent', percent: 25 }
    const row = buildClaimRow(p, { ...base, budgetAmountDollars: 4000 })
    expect(row.claim_kind).toBe('percent')
    expect(row.percent_complete).toBe(25)
    expect(row.claim_amount).toBe(1000) // 25% × $4000
    expect(row.hours).toBeNull()
    expect(row.qty).toBeNull()
  })

  it('builds percent claim with null budget — claim_amount 0', () => {
    const p: ClaimPayload = { kind: 'percent', percent: 25 }
    const row = buildClaimRow(p, { ...base, budgetAmountDollars: null })
    expect(row.claim_amount).toBe(0)
    expect(row.percent_complete).toBe(25)
  })

  it('builds hours claim — claim_amount = hours × rate', () => {
    const p: ClaimPayload = {
      kind: 'hours',
      hours: 8,
      companyServiceId: 'svc-uuid',
      rateUsed: 75,
    }
    const row = buildClaimRow(p, base)
    expect(row.claim_kind).toBe('hours')
    expect(row.hours).toBe(8)
    expect(row.rate_used).toBe(75)
    expect(row.claim_amount).toBe(600)
    expect(row.percent_complete).toBeNull()
    expect(row.qty).toBeNull()
    expect(row.company_service_id).toBe('svc-uuid')
  })

  it('builds qty claim — claim_amount = qty × rate', () => {
    const p: ClaimPayload = {
      kind: 'qty',
      qty: 12,
      companyServiceId: 'svc-uuid',
      rateUsed: 50,
    }
    const row = buildClaimRow(p, base)
    expect(row.claim_kind).toBe('qty')
    expect(row.qty).toBe(12)
    expect(row.claim_amount).toBe(600)
    expect(row.hours).toBeNull()
    expect(row.percent_complete).toBeNull()
  })

  it('stamps over_budget when flagged by caller', () => {
    const p: ClaimPayload = { kind: 'dollar', amountCents: 500000 }
    const row = buildClaimRow(p, { ...base, overBudget: true })
    expect(row.over_budget).toBe(true)
  })

  it('produces distinct UUIDs', () => {
    const p: ClaimPayload = { kind: 'dollar', amountCents: 100 }
    const r1 = buildClaimRow(p, base)
    const r2 = buildClaimRow(p, base)
    expect(r1.id).not.toBe(r2.id)
  })
})
```

- [ ] **Step 2: Run tests — verify fail**

Run: `npm test -- claim-payload`
Expected: fail.

- [ ] **Step 3: Implement `src/lib/claim-payload.ts`**

```ts
// Discriminated claim payload types + builder. Panel #2 Mathematician §4 —
// invalid states unrepresentable at the call site. DB CHECK is the backstop.
import type { ClaimKind } from './types'

export type DollarClaim = {
  kind: 'dollar'
  amountCents: number // > 0
  notes?: string
}
export type PercentClaim = {
  kind: 'percent'
  percent: number // 0 < x <= 100
  notes?: string
}
export type HoursClaim = {
  kind: 'hours'
  hours: number // > 0
  companyServiceId: string
  rateUsed: number
  notes?: string
}
export type QtyClaim = {
  kind: 'qty'
  qty: number // > 0
  companyServiceId: string
  rateUsed: number
  notes?: string
}

export type ClaimPayload = DollarClaim | PercentClaim | HoursClaim | QtyClaim

export interface ClaimContext {
  userId: string
  jobId: string
  budgetItemId: string
  subItemId?: string | null
  claimDate: string // YYYY-MM-DD
  budgetAmountDollars?: number | null
  overBudget?: boolean
  unitNo?: string | null
  supervisorId?: string | null
  companyId?: string | null
  gps?: {
    lat: number
    lng: number
    accuracyMeters: number
  } | null
}

export interface ClaimRow {
  id: string
  job_id: string
  budget_item_id: string
  sub_item_id: string | null
  claim_date: string
  claim_kind: ClaimKind
  claim_amount: number // dollars (DB stores numeric)
  percent_complete: number | null
  hours: number | null
  qty: number | null
  rate_used: number | null
  notes: string | null
  over_budget: boolean
  captured_at: string // ISO timestamptz
  captured_lat: number | null
  captured_lng: number | null
  captured_accuracy_m: number | null
  created_by: string
  company_id: string | null
  company_service_id: string | null
  unit_no: string | null
  supervisor_id: string | null
}

function newUuidV4(): string {
  // Prefer platform UUID generator (Node 18+, modern browsers).
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID()
  }
  // RFC 4122 v4 fallback — used only in ancient environments.
  const b = globalThis.crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const hex = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function buildClaimRow(payload: ClaimPayload, ctx: ClaimContext): ClaimRow {
  const base = {
    id: newUuidV4(),
    job_id: ctx.jobId,
    budget_item_id: ctx.budgetItemId,
    sub_item_id: ctx.subItemId ?? null,
    claim_date: ctx.claimDate,
    notes: payload.notes ?? null,
    over_budget: ctx.overBudget ?? false,
    captured_at: new Date().toISOString(),
    captured_lat: ctx.gps?.lat ?? null,
    captured_lng: ctx.gps?.lng ?? null,
    captured_accuracy_m: ctx.gps?.accuracyMeters ?? null,
    created_by: ctx.userId,
    company_id: ctx.companyId ?? null,
    company_service_id: null as string | null,
    unit_no: ctx.unitNo ?? null,
    supervisor_id: ctx.supervisorId ?? null,
  }

  switch (payload.kind) {
    case 'dollar':
      return {
        ...base,
        claim_kind: 'dollar',
        claim_amount: payload.amountCents / 100,
        percent_complete: null,
        hours: null,
        qty: null,
        rate_used: null,
      }
    case 'percent': {
      const budget = ctx.budgetAmountDollars ?? null
      const amount = budget != null ? Math.round(budget * payload.percent) / 100 : 0
      return {
        ...base,
        claim_kind: 'percent',
        claim_amount: amount,
        percent_complete: payload.percent,
        hours: null,
        qty: null,
        rate_used: null,
      }
    }
    case 'hours':
      return {
        ...base,
        claim_kind: 'hours',
        claim_amount: Math.round(payload.hours * payload.rateUsed * 100) / 100,
        percent_complete: null,
        hours: payload.hours,
        qty: null,
        rate_used: payload.rateUsed,
        company_service_id: payload.companyServiceId,
      }
    case 'qty':
      return {
        ...base,
        claim_kind: 'qty',
        claim_amount: Math.round(payload.qty * payload.rateUsed * 100) / 100,
        percent_complete: null,
        hours: null,
        qty: payload.qty,
        rate_used: payload.rateUsed,
        company_service_id: payload.companyServiceId,
      }
  }
}
```

- [ ] **Step 4: Run tests — verify pass**

Run: `npm test -- claim-payload`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/lib/claim-payload.ts src/lib/claim-payload.test.ts
git commit -m "feat(claim-payload): discriminated payload types + buildClaimRow

ClaimPayload union makes invalid save states unrepresentable. buildClaimRow
computes claim_amount per kind (dollar direct, percent × budget, hours/qty ×
rate), stamps client UUID + captured_at, passes GPS fire-and-forget."
```

---

### Task 5: Queue storage primitives

**Files:**
- Create: `src/lib/queue.ts`
- Test: `src/lib/queue.test.ts`

- [ ] **Step 1: Write failing tests**

Create `src/lib/queue.test.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import {
  enqueueClaim,
  loadAllQueued,
  removeQueued,
  updateQueued,
  classifyResponse,
  computeNextRetry,
  type QueuedClaim,
} from './queue'
import type { ClaimRow } from './claim-payload'
import { clear } from 'idb-keyval'

const baseRow: ClaimRow = {
  id: '00000000-0000-4000-a000-000000000001',
  job_id: 'j', budget_item_id: 'b', sub_item_id: null, claim_date: '2026-04-20',
  claim_kind: 'dollar', claim_amount: 100,
  percent_complete: null, hours: null, qty: null, rate_used: null,
  notes: null, over_budget: false,
  captured_at: new Date().toISOString(),
  captured_lat: null, captured_lng: null, captured_accuracy_m: null,
  created_by: 'u',
  company_id: null, company_service_id: null, unit_no: null, supervisor_id: null,
}

beforeEach(async () => {
  await clear()
})

describe('enqueue + loadAll', () => {
  it('stores and retrieves a claim', async () => {
    await enqueueClaim(baseRow)
    const all = await loadAllQueued()
    expect(all).toHaveLength(1)
    expect(all[0].payload.id).toBe(baseRow.id)
    expect(all[0].status.state).toBe('pending')
  })

  it('preserves insert order', async () => {
    const a = { ...baseRow, id: 'a' }
    const b = { ...baseRow, id: 'b' }
    await enqueueClaim(a)
    await enqueueClaim(b)
    const all = await loadAllQueued()
    expect(all.map((r) => r.payload.id)).toEqual(['a', 'b'])
  })
})

describe('removeQueued', () => {
  it('removes by id', async () => {
    await enqueueClaim(baseRow)
    await removeQueued(baseRow.id)
    expect(await loadAllQueued()).toHaveLength(0)
  })
})

describe('updateQueued', () => {
  it('updates status', async () => {
    await enqueueClaim(baseRow)
    await updateQueued(baseRow.id, {
      state: 'failed',
      attempts: 1,
      lastError: 'boom',
      nextRetryAt: Date.now() + 60_000,
    })
    const all = await loadAllQueued()
    expect(all[0].status.state).toBe('failed')
  })
})

describe('classifyResponse', () => {
  it('classifies 2xx as success', () => {
    expect(classifyResponse(null, null).kind).toBe('success')
  })
  it('classifies 23505 as success (idempotent retry)', () => {
    const err = { code: '23505', message: 'duplicate key' }
    expect(classifyResponse(err, null).kind).toBe('success')
  })
  it('classifies 23503 as dead-fk', () => {
    const err = { code: '23503', message: 'fk violation on budget_item_id' }
    const c = classifyResponse(err, null)
    expect(c.kind).toBe('dead')
    expect(c.reason).toMatch(/fk/i)
  })
  it('classifies 4xx as dead-other', () => {
    expect(classifyResponse({ code: '23502', message: 'not null' }, null).kind).toBe('dead')
  })
  it('classifies network error as retry', () => {
    expect(classifyResponse({ message: 'Failed to fetch' }, null).kind).toBe('retry')
  })
})

describe('computeNextRetry', () => {
  it('exp backoff', () => {
    const now = 1_000_000
    const d1 = computeNextRetry(1, now) - now
    const d2 = computeNextRetry(2, now) - now
    expect(d1).toBeGreaterThanOrEqual(60_000 * 0.8)
    expect(d1).toBeLessThanOrEqual(60_000 * 1.2)
    expect(d2).toBeGreaterThanOrEqual(120_000 * 0.8)
    expect(d2).toBeLessThanOrEqual(120_000 * 1.2)
  })
  it('caps at 1h', () => {
    const delay = computeNextRetry(20, 0)
    expect(delay).toBeLessThanOrEqual(3_600_000 * 1.2)
  })
})
```

- [ ] **Step 2: Run tests — verify fail**

Run: `npm test -- queue`
Expected: fail.

- [ ] **Step 3: Implement `src/lib/queue.ts`**

```ts
// Offline claim queue stored in idb-keyval. Panel #2 Architect §1-§3:
// append-only, UUID is idempotency key, 4-state status.

import { get, set, del, keys } from 'idb-keyval'
import type { ClaimRow } from './claim-payload'

export type QueueStatus =
  | { state: 'pending' }
  | { state: 'in_flight'; leaseUntil: number }
  | { state: 'failed'; attempts: number; lastError: string; nextRetryAt: number }
  | { state: 'dead'; attempts: number; lastError: string; deadAt: number }

export interface QueuedClaim {
  id: string
  kind: 'claim'
  payload: ClaimRow
  firstQueuedAt: number
  updatedAt: number
  status: QueueStatus
}

const KEY_PREFIX = 'queue:'
const INDEX_KEY = 'queue:index'

async function loadIndex(): Promise<string[]> {
  return (await get<string[]>(INDEX_KEY)) ?? []
}

async function saveIndex(ids: string[]): Promise<void> {
  await set(INDEX_KEY, ids)
}

export async function enqueueClaim(row: ClaimRow): Promise<void> {
  const now = Date.now()
  const record: QueuedClaim = {
    id: row.id,
    kind: 'claim',
    payload: row,
    firstQueuedAt: now,
    updatedAt: now,
    status: { state: 'pending' },
  }
  await set(`${KEY_PREFIX}${row.id}`, record)
  const ids = await loadIndex()
  if (!ids.includes(row.id)) {
    ids.push(row.id)
    await saveIndex(ids)
  }
}

export async function loadAllQueued(): Promise<QueuedClaim[]> {
  const ids = await loadIndex()
  const records = await Promise.all(ids.map((id) => get<QueuedClaim>(`${KEY_PREFIX}${id}`)))
  return records.filter((r): r is QueuedClaim => r !== undefined)
}

export async function removeQueued(id: string): Promise<void> {
  await del(`${KEY_PREFIX}${id}`)
  const ids = (await loadIndex()).filter((x) => x !== id)
  await saveIndex(ids)
}

export async function updateQueued(id: string, status: QueueStatus): Promise<void> {
  const key = `${KEY_PREFIX}${id}`
  const existing = await get<QueuedClaim>(key)
  if (!existing) return
  const next: QueuedClaim = { ...existing, status, updatedAt: Date.now() }
  await set(key, next)
}

// Classify a Supabase response / error into queue action.
// PostgREST error codes documented at https://postgrest.org/en/v12/errors.html
interface PgError {
  code?: string
  message?: string
}

export type Classification =
  | { kind: 'success' }
  | { kind: 'retry' }
  | { kind: 'dead'; reason: string }

export function classifyResponse(error: PgError | null, _data: unknown): Classification {
  if (!error) return { kind: 'success' }
  const code = error.code ?? ''
  const msg = error.message ?? ''
  if (code === '23505') return { kind: 'success' } // dup PK = idempotent retry
  if (code === '23503') return { kind: 'dead', reason: `fk_missing: ${msg}` }
  if (code.startsWith('22') || code.startsWith('23')) return { kind: 'dead', reason: msg || code }
  // Network / transport — Supabase-js surfaces as { message: 'Failed to fetch' }
  if (/fetch|network|timeout|abort/i.test(msg)) return { kind: 'retry' }
  // Unknown — default to retry; drain will eventually dead-letter after MAX_ATTEMPTS
  return { kind: 'retry' }
}

export const MAX_ATTEMPTS = 8

export function computeNextRetry(attempts: number, now: number = Date.now()): number {
  const base = 60_000 * 2 ** Math.max(0, attempts - 1)
  const capped = Math.min(base, 60 * 60_000)
  const jitter = 1 + (Math.random() * 0.4 - 0.2) // ±20%
  return now + Math.round(capped * jitter)
}
```

- [ ] **Step 4: Run tests — verify pass**

Run: `npm test -- queue`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/lib/queue.ts src/lib/queue.test.ts
git commit -m "feat(queue): idb-keyval queue primitives + response classifier

QueuedClaim 4-state status, enqueue/load/update/remove, classifyResponse
for Postgres errors (23505 → success by idempotency, 23503 → dead-letter,
network → retry), computeNextRetry exp backoff capped at 1h with ±20% jitter."
```

---

### Task 6: Queue drain engine

**Files:**
- Create: `src/lib/queue-drain.ts`
- Test: `src/lib/queue-drain.test.ts`

- [ ] **Step 1: Write failing tests**

Create `src/lib/queue-drain.test.ts`:

```ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { enqueueClaim, loadAllQueued } from './queue'
import { drainQueue } from './queue-drain'
import type { ClaimRow } from './claim-payload'
import { clear } from 'idb-keyval'

const baseRow: ClaimRow = {
  id: '00000000-0000-4000-a000-000000000001',
  job_id: 'j', budget_item_id: 'b', sub_item_id: null, claim_date: '2026-04-20',
  claim_kind: 'dollar', claim_amount: 100,
  percent_complete: null, hours: null, qty: null, rate_used: null,
  notes: null, over_budget: false,
  captured_at: new Date().toISOString(),
  captured_lat: null, captured_lng: null, captured_accuracy_m: null,
  created_by: 'u', company_id: null, company_service_id: null, unit_no: null, supervisor_id: null,
}

beforeEach(async () => {
  await clear()
})

function mockClient(responder: (row: ClaimRow) => { error: { code?: string; message?: string } | null }) {
  return {
    from() { return this },
    async insert(rows: ClaimRow[]) {
      const row = Array.isArray(rows) ? rows[0] : rows
      return { error: responder(row).error, data: null }
    },
  } as any
}

describe('drainQueue', () => {
  it('removes successful inserts', async () => {
    await enqueueClaim(baseRow)
    const sb = mockClient(() => ({ error: null }))
    await drainQueue(sb, { online: true })
    expect(await loadAllQueued()).toHaveLength(0)
  })

  it('treats 23505 as success (idempotent retry)', async () => {
    await enqueueClaim(baseRow)
    const sb = mockClient(() => ({ error: { code: '23505', message: 'dup' } }))
    await drainQueue(sb, { online: true })
    expect(await loadAllQueued()).toHaveLength(0)
  })

  it('dead-letters on 23503 FK violation', async () => {
    await enqueueClaim(baseRow)
    const sb = mockClient(() => ({ error: { code: '23503', message: 'fk' } }))
    await drainQueue(sb, { online: true })
    const all = await loadAllQueued()
    expect(all).toHaveLength(1)
    expect(all[0].status.state).toBe('dead')
  })

  it('marks failed + schedules retry on network error', async () => {
    await enqueueClaim(baseRow)
    const sb = mockClient(() => ({ error: { message: 'Failed to fetch' } }))
    await drainQueue(sb, { online: true })
    const all = await loadAllQueued()
    expect(all).toHaveLength(1)
    expect(all[0].status.state).toBe('failed')
  })

  it('does nothing when offline', async () => {
    await enqueueClaim(baseRow)
    const sb = mockClient(() => ({ error: null }))
    const insertSpy = vi.spyOn(sb, 'from')
    await drainQueue(sb, { online: false })
    expect(insertSpy).not.toHaveBeenCalled()
    expect(await loadAllQueued()).toHaveLength(1)
  })

  it('is reentrant-safe (concurrent calls yield 1 insert)', async () => {
    await enqueueClaim(baseRow)
    let calls = 0
    const sb = mockClient(() => { calls++; return { error: null } })
    await Promise.all([
      drainQueue(sb, { online: true }),
      drainQueue(sb, { online: true }),
    ])
    expect(calls).toBe(1)
  })
})
```

- [ ] **Step 2: Run tests — verify fail**

Run: `npm test -- queue-drain`
Expected: fail.

- [ ] **Step 3: Implement `src/lib/queue-drain.ts`**

```ts
// drain() — iterates queued records, dispatches to Supabase, updates status.
// Architect §2: guarded by in-memory flag + in_flight lease for cross-tab.

import type { SupabaseClient } from '@supabase/supabase-js'
import {
  loadAllQueued, removeQueued, updateQueued,
  classifyResponse, computeNextRetry, MAX_ATTEMPTS,
  type QueuedClaim,
} from './queue'

const LEASE_MS = 30_000
let draining = false

interface DrainOptions {
  online?: boolean // override for tests / non-browser
}

function isReady(r: QueuedClaim, now: number): boolean {
  const s = r.status
  if (s.state === 'pending') return true
  if (s.state === 'failed') return s.nextRetryAt <= now
  if (s.state === 'in_flight') return s.leaseUntil < now // prior drain crashed
  return false // dead
}

export async function drainQueue(
  supabase: SupabaseClient,
  opts: DrainOptions = {},
): Promise<void> {
  const online = opts.online ?? (typeof navigator !== 'undefined' ? navigator.onLine : true)
  if (!online) return
  if (draining) return
  draining = true
  try {
    const now = Date.now()
    const records = (await loadAllQueued()).filter((r) => isReady(r, now))

    for (const record of records) {
      await updateQueued(record.id, { state: 'in_flight', leaseUntil: Date.now() + LEASE_MS })

      let error: { code?: string; message?: string } | null = null
      try {
        const res = await supabase.from('install_claims').insert(record.payload)
        error = res.error as any
      } catch (e: any) {
        error = { message: e?.message ?? String(e) }
      }

      const cls = classifyResponse(error, null)
      if (cls.kind === 'success') {
        await removeQueued(record.id)
        continue
      }
      if (cls.kind === 'dead') {
        await updateQueued(record.id, {
          state: 'dead',
          attempts: priorAttempts(record) + 1,
          lastError: cls.reason,
          deadAt: Date.now(),
        })
        continue
      }
      // retry
      const attempts = priorAttempts(record) + 1
      if (attempts >= MAX_ATTEMPTS) {
        await updateQueued(record.id, {
          state: 'dead',
          attempts,
          lastError: error?.message ?? 'max_attempts',
          deadAt: Date.now(),
        })
      } else {
        await updateQueued(record.id, {
          state: 'failed',
          attempts,
          lastError: error?.message ?? 'unknown',
          nextRetryAt: computeNextRetry(attempts),
        })
      }
    }
  } finally {
    draining = false
  }
}

function priorAttempts(r: QueuedClaim): number {
  if (r.status.state === 'failed' || r.status.state === 'dead') return r.status.attempts
  return 0
}
```

- [ ] **Step 4: Run tests — verify pass**

Run: `npm test -- queue-drain`
Expected: 6 pass.

- [ ] **Step 5: Commit**

```bash
git add src/lib/queue-drain.ts src/lib/queue-drain.test.ts
git commit -m "feat(queue): drainQueue — orchestrates queue through Supabase insert

Reentrancy-safe (draining flag), respects online status, applies classifyResponse
output to move records through pending → in_flight → success/dead/failed. Max
attempts = 8 before auto dead-letter."
```

---

### Task 7: useOfflineQueue hook

**Files:**
- Create: `src/lib/use-offline-queue.ts`

- [ ] **Step 1: Implement hook (no unit test — glue code, manual verification)**

```ts
'use client'

import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'
import { loadAllQueued, type QueuedClaim } from './queue'
import { drainQueue } from './queue-drain'

export interface QueueCounts {
  pending: number
  inFlight: number
  failed: number
  dead: number
  total: number
}

function countStatus(records: QueuedClaim[]): QueueCounts {
  const counts = { pending: 0, inFlight: 0, failed: 0, dead: 0, total: records.length }
  for (const r of records) {
    switch (r.status.state) {
      case 'pending': counts.pending++; break
      case 'in_flight': counts.inFlight++; break
      case 'failed': counts.failed++; break
      case 'dead': counts.dead++; break
    }
  }
  return counts
}

export function useOfflineQueue() {
  const [counts, setCounts] = useState<QueueCounts>({ pending: 0, inFlight: 0, failed: 0, dead: 0, total: 0 })

  const refresh = useCallback(async () => {
    const all = await loadAllQueued()
    setCounts(countStatus(all))
  }, [])

  const drainNow = useCallback(async () => {
    await drainQueue(supabase)
    await refresh()
  }, [refresh])

  useEffect(() => {
    refresh()
    const onVisible = () => { if (document.visibilityState === 'visible') drainNow() }
    const onOnline = () => drainNow()
    const onAuth = supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_IN') drainNow()
    })
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('online', onOnline)
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') drainNow()
    }, 60_000)

    return () => {
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('online', onOnline)
      onAuth.data.subscription.unsubscribe()
      clearInterval(interval)
    }
  }, [drainNow, refresh])

  return { counts, drainNow, refresh }
}
```

- [ ] **Step 2: Confirm it type-checks**

Run: `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add src/lib/use-offline-queue.ts
git commit -m "feat(queue): useOfflineQueue hook — drain triggers + status counts

Wires drainQueue to: visibilitychange, window.online, auth SIGNED_IN, and a
60s interval while tab is visible. Exposes pending/inFlight/failed/dead/total
counts for UI chips."
```

---

### Task 8: useJobState hook (sticky last job)

**Files:**
- Create: `src/lib/use-job-state.ts`

- [ ] **Step 1: Implement**

```ts
'use client'

import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'
import type { Job } from './types'

const STORAGE_KEY = 'hytek-budget:lastJobId'

export function useJobState() {
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)

  const loadJob = useCallback(async (jobId: string) => {
    const { data } = await supabase.from('jobs').select('*').eq('id', jobId).maybeSingle()
    if (data) setJob(data as Job)
  }, [])

  useEffect(() => {
    const stored = typeof window !== 'undefined' ? window.localStorage.getItem(STORAGE_KEY) : null
    if (stored) {
      loadJob(stored).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [loadJob])

  const selectJob = useCallback((next: Job) => {
    setJob(next)
    window.localStorage.setItem(STORAGE_KEY, next.id)
  }, [])

  const clearJob = useCallback(() => {
    setJob(null)
    window.localStorage.removeItem(STORAGE_KEY)
  }, [])

  return { job, loading, selectJob, clearJob }
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add src/lib/use-job-state.ts
git commit -m "feat(log): useJobState hook — sticky last job via localStorage

Removes job picker from the hot path for the 95% case where an installer is
on one job per day. UX Panel #2: 'Change job' is a chip; picker is cold-path."
```

---

### Task 9: useRecentItems hook

**Files:**
- Create: `src/lib/use-recent-items.ts`

- [ ] **Step 1: Implement**

```ts
'use client'

import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'
import type { InstallBudgetItem } from './types'

export interface RecentItem {
  budgetItem: InstallBudgetItem
  lastLoggedAt: string // captured_at ISO
}

// Returns up to 5 budget items this user has logged against on this job within
// the last 7 days, most-recent first. Server-side aggregation keeps this cheap.
export function useRecentItems(userId: string | null, jobId: string | null) {
  const [items, setItems] = useState<RecentItem[]>([])
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    if (!userId || !jobId) { setItems([]); return }
    setLoading(true)
    try {
      const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60_000).toISOString()
      const { data: claims } = await supabase
        .from('install_claims')
        .select('budget_item_id, captured_at')
        .eq('created_by', userId)
        .eq('job_id', jobId)
        .gte('captured_at', sevenDaysAgo)
        .order('captured_at', { ascending: false })

      if (!claims || claims.length === 0) { setItems([]); return }

      // Dedupe by budget_item_id keeping first (= most recent)
      const seen = new Map<string, string>()
      for (const c of claims as { budget_item_id: string; captured_at: string }[]) {
        if (!seen.has(c.budget_item_id)) seen.set(c.budget_item_id, c.captured_at)
        if (seen.size >= 5) break
      }

      const ids = Array.from(seen.keys())
      const { data: budgetItems } = await supabase
        .from('install_budget_items')
        .select('*')
        .in('id', ids)

      const byId = new Map<string, InstallBudgetItem>()
      for (const b of (budgetItems ?? []) as InstallBudgetItem[]) byId.set(b.id, b)

      const ordered: RecentItem[] = ids
        .map((id) => {
          const bi = byId.get(id)
          if (!bi) return null
          return { budgetItem: bi, lastLoggedAt: seen.get(id)! }
        })
        .filter((x): x is RecentItem => x !== null)

      setItems(ordered)
    } finally {
      setLoading(false)
    }
  }, [userId, jobId])

  useEffect(() => { refresh() }, [refresh])

  return { items, loading, refresh }
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add src/lib/use-recent-items.ts
git commit -m "feat(log): useRecentItems hook — most-recent budget items this job/week/user

Dedupes at client after server-side ordered pull. 7-day window, max 5 items.
Pinned to top of ItemPicker per UX Panel #2 decision."
```

---

### Task 10: ClaimInput component

**Files:**
- Create: `src/app/log/components/ClaimInput.tsx`

- [ ] **Step 1: Implement**

```tsx
'use client'

import { useState, useMemo } from 'react'
import type { InstallBudgetItem } from '@/lib/types'
import { unitTypeToInputMode } from '@/lib/unit-type'
import { parseAudCentsFromString } from '@/lib/money'
import type { ClaimPayload } from '@/lib/claim-payload'

interface Props {
  item: InstallBudgetItem
  onSave: (payload: ClaimPayload) => void | Promise<void>
  onCancel: () => void
  // For hours/qty: rate lookup deferred to Phase 1.x. For now, if unit_type
  // triggers hours/qty mode, we fall back to dollar mode until rate-card wiring
  // ships (Task 1 probe + follow-up task).
}

export function ClaimInput({ item, onSave, onCancel }: Props) {
  const mode = useMemo(
    () => unitTypeToInputMode(item.unit_type, {
      budgetAmountCents: item.budget_amount != null ? Math.round(item.budget_amount * 100) : null,
    }),
    [item],
  )
  // Gate hours/qty modes for Phase 1 (need rate-card wiring) — fall back to dollar
  const effectiveMode = (mode.mode === 'hours' || mode.mode === 'qty')
    ? { ...mode, mode: 'dollar' as const, label: '$ claimed', inputMode: 'decimal' as const, step: 0.01 }
    : mode

  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSave() {
    setError(null)
    try {
      let payload: ClaimPayload
      if (effectiveMode.mode === 'dollar') {
        const cents = parseAudCentsFromString(value)
        if (cents <= 0) throw new Error('Amount must be positive')
        payload = { kind: 'dollar', amountCents: cents, notes: notes || undefined }
      } else { // percent
        const pct = Number.parseFloat(value)
        if (!Number.isFinite(pct) || pct <= 0 || pct > 100) throw new Error('Enter 0–100')
        payload = { kind: 'percent', percent: pct, notes: notes || undefined }
      }
      setSubmitting(true)
      await onSave(payload)
    } catch (e: any) {
      setError(e.message ?? 'Invalid input')
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-4 rounded-2xl bg-white p-4 shadow-lg">
      <div>
        <div className="text-xs uppercase text-gray-500">{item.category}</div>
        <div className="text-lg font-semibold">{item.description ?? '(no description)'}</div>
      </div>
      <label className="block">
        <span className="mb-1 block text-sm font-medium">{effectiveMode.label}</span>
        <input
          type="text"
          inputMode={effectiveMode.inputMode}
          autoFocus
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={effectiveMode.mode === 'percent' ? '0–100' : '0.00'}
        />
      </label>
      <label className="block">
        <span className="mb-1 block text-sm font-medium">Notes (optional)</span>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </label>
      {error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 rounded-lg border border-gray-300 bg-white py-3 font-semibold"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={submitting || !value.trim()}
          className="flex-1 rounded-lg bg-hytek-yellow py-3 font-semibold text-hytek-black disabled:opacity-50"
        >
          {submitting ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add src/app/log/components/ClaimInput.tsx
git commit -m "feat(log): ClaimInput component — smart single field per unit_type

Maps unit_type → label + keyboard via unitTypeToInputMode. Hours/qty modes
gated off Phase 1 (need rate-card wiring); fall back to dollar. autoFocus on
the number field so tap-3 pre-opens keypad."
```

---

### Task 11: ItemPicker component

**Files:**
- Create: `src/app/log/components/ItemPicker.tsx`

- [ ] **Step 1: Implement**

```tsx
'use client'

import { useMemo, useState } from 'react'
import type { InstallBudgetItem } from '@/lib/types'
import type { RecentItem } from '@/lib/use-recent-items'

interface Props {
  recents: RecentItem[]
  allItems: InstallBudgetItem[]
  onSelect: (item: InstallBudgetItem) => void
}

export function ItemPicker({ recents, allItems, onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState<string | null>(null)

  const categories = useMemo(() => {
    const set = new Set<string>()
    for (const i of allItems) set.add(i.category)
    return Array.from(set).sort()
  }, [allItems])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return allItems.filter((i) => {
      if (activeCategory && i.category !== activeCategory) return false
      if (!q) return true
      return (
        (i.description ?? '').toLowerCase().includes(q) ||
        i.category.toLowerCase().includes(q)
      )
    })
  }, [allItems, query, activeCategory])

  return (
    <div className="space-y-4">
      {recents.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs uppercase tracking-wide text-gray-500">Recently logged</h3>
          <ul className="space-y-2">
            {recents.map((r) => (
              <li key={r.budgetItem.id}>
                <button
                  type="button"
                  onClick={() => onSelect(r.budgetItem)}
                  className="w-full rounded-xl bg-white p-3 text-left shadow"
                >
                  <div className="text-xs text-gray-500">{r.budgetItem.category}</div>
                  <div className="text-sm font-medium">{r.budgetItem.description ?? '(no description)'}</div>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="space-y-2">
        <input
          type="text"
          placeholder="Search items…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="flex gap-2 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveCategory(null)}
            className={`shrink-0 rounded-full px-3 py-1 text-sm ${
              activeCategory === null ? 'bg-hytek-black text-white' : 'bg-gray-200'
            }`}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setActiveCategory(c)}
              className={`shrink-0 rounded-full px-3 py-1 text-sm ${
                activeCategory === c ? 'bg-hytek-black text-white' : 'bg-gray-200'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      <ul className="space-y-2">
        {filtered.map((i) => (
          <li key={i.id}>
            <button
              type="button"
              onClick={() => onSelect(i)}
              className="w-full rounded-xl bg-white p-3 text-left shadow"
            >
              <div className="text-xs text-gray-500">{i.category}</div>
              <div className="text-sm">{i.description ?? '(no description)'}</div>
            </button>
          </li>
        ))}
        {filtered.length === 0 && (
          <li className="py-8 text-center text-sm text-gray-500">No items match.</li>
        )}
      </ul>
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add src/app/log/components/ItemPicker.tsx
git commit -m "feat(log): ItemPicker — recents pinned + search + category chips

No cascade. Recently-logged (this job, this week) sit at top for 1-tap re-log;
search + chips handle the long tail. Horizontal chip scroll matches mobile UX
vocabulary."
```

---

### Task 12: JobHeader component

**Files:**
- Create: `src/app/log/components/JobHeader.tsx`

- [ ] **Step 1: Implement**

```tsx
'use client'

import type { Job } from '@/lib/types'

interface Props {
  job: Job
  onChange: () => void
  pendingCount: number
  deadCount: number
}

export function JobHeader({ job, onChange, pendingCount, deadCount }: Props) {
  return (
    <header className="flex items-center justify-between gap-2 border-b border-gray-200 bg-white px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="truncate text-base font-semibold text-hytek-black">{job.name}</div>
        <div className="truncate text-xs text-gray-500">#{job.job_number}</div>
      </div>
      {pendingCount > 0 && (
        <div
          aria-label={`${pendingCount} pending logs`}
          className={`relative rounded-full px-2 py-1 text-xs font-semibold ${
            deadCount > 0 ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-700'
          }`}
        >
          {pendingCount} pending
          {deadCount > 0 && (
            <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-red-600" />
          )}
        </div>
      )}
      <button
        type="button"
        onClick={onChange}
        className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs"
      >
        Change job
      </button>
    </header>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add src/app/log/components/JobHeader.tsx
git commit -m "feat(log): JobHeader — current job + Change chip + pending/dead indicator

Pending chip only appears when count > 0 (no always-on noise). Dead-letter red
dot overlays the chip when any record is in dead state — non-dismissible signal
to act."
```

---

### Task 13: SaveConfirmation component

**Files:**
- Create: `src/app/log/components/SaveConfirmation.tsx`

- [ ] **Step 1: Implement**

```tsx
'use client'

import { useEffect } from 'react'

interface Props {
  visible: boolean
  offline: boolean
  onDismiss: () => void
}

export function SaveConfirmation({ visible, offline, onDismiss }: Props) {
  useEffect(() => {
    if (!visible) return
    if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
      navigator.vibrate(50)
    }
    const t = setTimeout(onDismiss, 2000)
    return () => clearTimeout(t)
  }, [visible, onDismiss])

  return (
    <div
      aria-hidden={!visible}
      className={`fixed left-0 right-0 top-0 z-50 transform bg-green-600 py-3 text-center text-sm font-semibold text-white shadow-lg transition-transform duration-200 ${
        visible ? 'translate-y-0' : '-translate-y-full'
      }`}
    >
      {offline ? 'Logged — will sync when online' : 'Logged — syncing'}
    </div>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add src/app/log/components/SaveConfirmation.tsx
git commit -m "feat(log): SaveConfirmation — slide-down banner + haptic

Green bar slides down from top, haptic pulse, auto-dismiss 2s. Distinguishes
'offline / will sync' from 'syncing' so installers don't wonder whether their
log made it. Confirmation fires on IndexedDB write, not Supabase POST."
```

---

### Task 14: TodaysClaimsList component

**Files:**
- Create: `src/app/log/components/TodaysClaimsList.tsx`

- [ ] **Step 1: Implement**

```tsx
'use client'

import type { InstallBudgetItem } from '@/lib/types'
import type { ClaimPayload } from '@/lib/claim-payload'
import { formatAud, type Money } from '@/lib/money'

export interface SessionClaim {
  id: string
  item: InstallBudgetItem
  payload: ClaimPayload
  stampedAt: Date
}

interface Props {
  claims: SessionClaim[]
}

function describeClaim(p: ClaimPayload): string {
  switch (p.kind) {
    case 'dollar': return formatAud(p.amountCents as Money)
    case 'percent': return `${p.percent}%`
    case 'hours': return `${p.hours} h @ $${p.rateUsed}/h`
    case 'qty': return `${p.qty} × $${p.rateUsed}`
  }
}

const TIME_FORMAT = new Intl.DateTimeFormat('en-AU', { hour: 'numeric', minute: '2-digit' })

export function TodaysClaimsList({ claims }: Props) {
  if (claims.length === 0) return null
  return (
    <section className="space-y-2">
      <h3 className="text-xs uppercase tracking-wide text-gray-500">Today's claims</h3>
      <ul className="space-y-2">
        {claims.map((c) => (
          <li key={c.id} className="rounded-xl bg-white px-3 py-2 text-sm shadow">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate">{c.item.description ?? c.item.category}</span>
              <span className="shrink-0 font-semibold">{describeClaim(c.payload)}</span>
            </div>
            <div className="text-xs text-gray-500">{TIME_FORMAT.format(c.stampedAt)}</div>
          </li>
        ))}
      </ul>
    </section>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add src/app/log/components/TodaysClaimsList.tsx
git commit -m "feat(log): TodaysClaimsList — session-only inline append list

Reads from in-memory session state (not Supabase). Gives installers a visible
trail of what they've just logged without a history round-trip. Empties on
page refresh by design — DB is the source of truth for history."
```

---

### Task 15: /log/pick-job page

**Files:**
- Create: `src/app/log/pick-job/page.tsx`

- [ ] **Step 1: Implement**

```tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/lib/auth-context'
import type { Job } from '@/lib/types'

const STORAGE_KEY = 'hytek-budget:lastJobId'

export default function PickJobPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [jobs, setJobs] = useState<Job[]>([])
  const [query, setQuery] = useState('')

  useEffect(() => {
    if (!loading && !user) router.replace('/login')
  }, [loading, user, router])

  useEffect(() => {
    supabase
      .from('jobs')
      .select('*')
      .eq('install_status', 'active')
      .order('created_at', { ascending: false })
      .limit(50)
      .then(({ data }) => setJobs((data as Job[]) ?? []))
  }, [])

  function select(j: Job) {
    window.localStorage.setItem(STORAGE_KEY, j.id)
    router.replace('/log')
  }

  const filtered = query
    ? jobs.filter((j) =>
        j.name.toLowerCase().includes(query.toLowerCase()) ||
        j.job_number.toLowerCase().includes(query.toLowerCase()),
      )
    : jobs

  return (
    <main className="flex-1 p-4">
      <h1 className="mb-4 text-xl font-semibold text-hytek-black">Pick job</h1>
      <input
        type="text"
        placeholder="Search jobs…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="mb-4"
      />
      <ul className="space-y-2">
        {filtered.map((j) => (
          <li key={j.id}>
            <button
              type="button"
              onClick={() => select(j)}
              className="w-full rounded-xl bg-white p-3 text-left shadow"
            >
              <div className="font-semibold">{j.name}</div>
              <div className="text-xs text-gray-500">#{j.job_number}</div>
            </button>
          </li>
        ))}
        {filtered.length === 0 && (
          <li className="py-8 text-center text-sm text-gray-500">No jobs match.</li>
        )}
      </ul>
    </main>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add src/app/log/pick-job/page.tsx
git commit -m "feat(log): /log/pick-job — active-jobs picker with search

Only lists jobs with install_status = 'active' (don't surface completed jobs
in the mobile picker). Sets localStorage lastJobId on select and redirects
back to /log. Cold-path only — hot path uses sticky last job."
```

---

### Task 16: /log page — compose everything

**Files:**
- Create: `src/app/log/page.tsx`

- [ ] **Step 1: Implement**

```tsx
'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { useJobState } from '@/lib/use-job-state'
import { useRecentItems } from '@/lib/use-recent-items'
import { useOfflineQueue } from '@/lib/use-offline-queue'
import { supabase } from '@/lib/supabase'
import { buildClaimRow, type ClaimPayload } from '@/lib/claim-payload'
import { enqueueClaim } from '@/lib/queue'
import type { InstallBudgetItem } from '@/lib/types'
import { JobHeader } from './components/JobHeader'
import { ItemPicker } from './components/ItemPicker'
import { ClaimInput } from './components/ClaimInput'
import { SaveConfirmation } from './components/SaveConfirmation'
import { TodaysClaimsList, type SessionClaim } from './components/TodaysClaimsList'

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

async function readGpsOrNull(): Promise<{ lat: number; lng: number; accuracyMeters: number } | null> {
  if (typeof navigator === 'undefined' || !('geolocation' in navigator)) return null
  return new Promise((resolve) => {
    const controller = new AbortController()
    const timeout = setTimeout(() => { controller.abort(); resolve(null) }, 3000)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        clearTimeout(timeout)
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracyMeters: Math.round(pos.coords.accuracy),
        })
      },
      () => { clearTimeout(timeout); resolve(null) },
      { timeout: 3000, maximumAge: 30_000, enableHighAccuracy: false },
    )
  })
}

export default function LogPage() {
  const { user, profile, loading: authLoading } = useAuth()
  const { job, loading: jobLoading } = useJobState()
  const router = useRouter()

  const { items: recents, refresh: refreshRecents } = useRecentItems(user?.id ?? null, job?.id ?? null)
  const { counts, drainNow } = useOfflineQueue()

  const [allItems, setAllItems] = useState<InstallBudgetItem[]>([])
  const [selected, setSelected] = useState<InstallBudgetItem | null>(null)
  const [confirmation, setConfirmation] = useState<{ offline: boolean } | null>(null)
  const [sessionClaims, setSessionClaims] = useState<SessionClaim[]>([])

  // Guard auth + job selection
  useEffect(() => {
    if (!authLoading && !user) router.replace('/login')
  }, [authLoading, user, router])
  useEffect(() => {
    if (!jobLoading && !job) router.replace('/log/pick-job')
  }, [jobLoading, job, router])

  // Load budget items for the active job
  useEffect(() => {
    if (!job) { setAllItems([]); return }
    supabase
      .from('install_budget_items')
      .select('*')
      .eq('job_id', job.id)
      .order('category')
      .order('description')
      .then(({ data }) => setAllItems((data as InstallBudgetItem[]) ?? []))
  }, [job])

  const handleSave = useCallback(async (payload: ClaimPayload) => {
    if (!user || !job || !selected) return
    const gps = await readGpsOrNull()
    const row = buildClaimRow(payload, {
      userId: user.id,
      jobId: job.id,
      budgetItemId: selected.id,
      claimDate: todayIso(),
      budgetAmountDollars: selected.budget_amount,
      gps,
    })
    await enqueueClaim(row)
    // Confirmation fires OFF the IndexedDB write — per Panel #2 UX
    setSessionClaims((prev) => [
      { id: row.id, item: selected, payload, stampedAt: new Date() },
      ...prev,
    ].slice(0, 10))
    setConfirmation({ offline: typeof navigator !== 'undefined' ? !navigator.onLine : false })
    setSelected(null)
    // Kick drain in background — do NOT await
    drainNow().then(() => refreshRecents())
  }, [user, job, selected, drainNow, refreshRecents])

  if (authLoading || jobLoading || !user || !job) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-hytek-yellow border-t-transparent" />
      </div>
    )
  }

  return (
    <main className="flex flex-1 flex-col">
      <JobHeader
        job={job}
        onChange={() => router.push('/log/pick-job')}
        pendingCount={counts.pending + counts.inFlight + counts.failed}
        deadCount={counts.dead}
      />
      <SaveConfirmation
        visible={confirmation !== null}
        offline={confirmation?.offline ?? false}
        onDismiss={() => setConfirmation(null)}
      />
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {selected ? (
          <ClaimInput
            item={selected}
            onSave={handleSave}
            onCancel={() => setSelected(null)}
          />
        ) : (
          <ItemPicker
            recents={recents}
            allItems={allItems}
            onSelect={setSelected}
          />
        )}
        <TodaysClaimsList claims={sessionClaims} />
      </div>
    </main>
  )
}
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: clean. If complaints, fix them here before proceeding.

- [ ] **Step 3: Commit**

```bash
git add src/app/log/page.tsx
git commit -m "feat(log): /log page — compose Header + Picker + Input + Confirmation

Hot path: sticky-last-job header → recents pinned in ItemPicker → 1 tap item
→ ClaimInput with autoFocus field → tap Save → confirmation fires on IDB
write, drain kicks in background. If no job set, redirect to /log/pick-job."
```

---

### Task 17: Dashboard "Log a claim" link

**Files:**
- Modify: `src/app/dashboard/page.tsx`

- [ ] **Step 1: Add the button below the bootstrap section**

Modify `src/app/dashboard/page.tsx` — replace the `<section>` block with:

```tsx
      <section className="rounded-2xl bg-white p-6 shadow">
        <h2 className="mb-2 text-lg font-semibold">Quick-Log</h2>
        <p className="mb-4 text-sm text-gray-600">
          Log a progress claim against your current job.
        </p>
        <a
          href="/log"
          className="inline-block rounded-lg bg-hytek-yellow px-4 py-3 font-semibold text-hytek-black"
        >
          Log a claim
        </a>
      </section>
```

- [ ] **Step 2: Type-check + commit**

Run: `npx tsc --noEmit`
Expected: clean.

```bash
git add src/app/dashboard/page.tsx
git commit -m "feat(dashboard): add Log a claim button linking to /log

Replaces the Phase 0 bootstrap placeholder. /log is the hot-path entry point
for Phase 1; dashboard is the slow-path landing pad."
```

---

### Task 18: End-to-end manual verification

**Files:** none — this is a verification gate, not a code task.

- [ ] **Step 1: Run dev server**

```bash
npm run dev
```

Open `http://localhost:3000` in a real mobile device (or Chrome DevTools device emulation) — not just the desktop viewport.

- [ ] **Step 2: Happy path**

1. Sign in as `admin@hytekframing.com.au` / `Hytek2026`.
2. Dashboard → tap "Log a claim" → redirects to `/log/pick-job` (no sticky job yet).
3. Pick a test job (e.g. "Test 30 Unit Full-Coverage Complex") → lands on `/log`.
4. Tap an item in Recents (if none, tap any item in the list) → ClaimInput appears with the numeric keypad.
5. Enter a value, tap Save → confirmation banner slides down within <100ms, haptic fires (only on real device).
6. Session claims list appears below with the new entry.
7. Queue chip disappears (drain succeeded).

Expected: no console errors, no network errors beyond the single successful POST.

- [ ] **Step 3: Offline path**

1. Open Chrome DevTools → Network tab → Throttling → "Offline".
2. Log a claim the same way as Step 2.
3. Confirm the banner says "Logged — will sync when online".
4. Queue chip shows "1 pending" in header.
5. DevTools → Application → IndexedDB → should show one queue entry.
6. Switch throttle back to "Online" — queue chip should clear within ~60s (or instantly on the `online` event fire).

Expected: row appears in Supabase `install_claims` after drain, chip goes to 0.

- [ ] **Step 4: Duplicate-PK idempotency spot check**

1. Log a claim offline.
2. In DevTools, find the queued record; note its `payload.id` (UUID).
3. Go back online. Before drain fires, force a second drain by clicking the "Change job" chip to trigger a visibilitychange cycle (or reopen the tab).
4. Two drain attempts should race; the second gets `23505` and the record vanishes from the queue the same way.
5. Check Supabase — exactly one `install_claims` row with that UUID.

If this cannot be reproduced reliably, manually inspect `classifyResponse` output by logging `error` objects inside `drainQueue` during a temporary instrumentation commit.

- [ ] **Step 5: Check constraint bite**

1. Open DevTools console. Run:
   ```js
   await window.indexedDB.databases() // should list 'keyval-store'
   ```
2. Directly call `supabase.from('install_claims').insert({ id: crypto.randomUUID(), job_id: 'some-real-id', budget_item_id: 'some-real-id', claim_date: '2026-04-20', claim_kind: 'dollar', claim_amount: 100, percent_complete: 50 })`.
   — should error with "new row violates check constraint claim_kind_shape" because both amount and percent are set.
3. Confirms the schema CHECK is load-bearing.

- [ ] **Step 6: Write findings note**

Create `docs/superpowers/notes/2026-04-20-phase1-e2e-findings.md` with:
1. What worked first time
2. What had to be debugged
3. Rough cold-launch → saved tap count measured on-device
4. Any surprises worth saving to memory

- [ ] **Step 7: Commit findings + declare Phase 1 ready to pilot**

```bash
git add docs/superpowers/notes/2026-04-20-phase1-e2e-findings.md
git commit -m "docs(notes): Phase 1 E2E verification findings — ready for 3–5 day dogfood"
```

- [ ] **Step 8: Push**

```bash
git push origin main
```

If Vercel auto-deploys on push, confirm `budget.hytekframing.com.au` gets the update. If the first deploy fails with a build error, read the error, fix, recommit — no hotfix commits on top of broken state.

---

## Deferred, tracked

These are explicitly **not** in Phase 1. Do not "just add them" without a new spec + plan.

- `/log` Variation stream → **Phase 1.5**
- `/log` Rework stream + photo capture → **Phase 1.6**
- `/settings/queue` dead-letter UI → **Phase 2**
- Claim edit / delete → **Forever-deferred** (append-only invariant)
- Rate-card wiring for hours/qty modes → **Phase 1.x** (currently gated behind fall-back-to-dollar in ClaimInput)

## Self-review checklist (completed before handoff)

- [x] Spec §2 scope covered — Tasks 10, 11, 15, 16 cover `/log` + pick-job; Tasks 2–9 cover the libraries the spec requires.
- [x] Spec §5 data model — Task 4 `buildClaimRow` maps every column the migration added.
- [x] Spec §6 queue architecture — Tasks 5, 6, 7 cover storage primitives, drain engine, and trigger wiring respectively.
- [x] Spec §8 money — Task 2 covers it, and `ClaimInput` + `TodaysClaimsList` both import from `lib/money.ts`.
- [x] Spec §9 component contracts — Task 4 is the TS embodiment.
- [x] Spec §10 failure modes — each one is covered by either a library test (queue, classifyResponse) or a verification step in Task 18.
- [x] Spec §11 open items — Task 1 (DB probe) addresses unit_type + rate-card seeding upfront.
- [x] Spec §13 commitments — not code; Scott's responsibility, captured in spec, not re-documented here.
- [x] No placeholders, no "TBD", every step has exact content, types and function names consistent across tasks.
