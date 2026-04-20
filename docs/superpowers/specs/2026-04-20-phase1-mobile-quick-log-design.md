# Phase 1 — Mobile Unified Quick-Log (Progress stream)

**Status:** Design approved in principle (Panel #2, 2026-04-20). Awaiting Scott review of this spec.
**Scope decision:** Progress claims only. Variations ship as Phase 1.5, Rework as Phase 1.6.
**Author:** Claude (synthesised from Panel #2 — UX / Architect / Mathematician / Strategist).

---

## 1. Why this exists

The retired Install UI lived at `hytek-detailing/app/install/*` and handled all three streams (progress / variation / rework) in a desktop-first form-heavy flow. Adoption was low. Installers are on phones in noisy sites, one-handed, often on spotty 4G or offline. Phase 1 replaces the Progress claim path with a mobile-first ≤3-tap flow. Variation and Rework hold on paper + SMS for 2–3 weeks until 1.5 / 1.6 ship.

**Success metric:** Daily active installers logging ≥1 claim, 7-day trailing average, target ≥4 of 5 by end of week 2. Observable in `install_claims.created_at` grouped by `created_by`. No new instrumentation.

**The one thing that most likely kills Phase 1:** installers log 2–3 claims day 1, get no visible outcome, silently stop by day 4. Mitigation is a behavioural commitment from Scott, not a feature: weekly Friday WhatsApp to the team — *"your logs drove $X of invoicing this week."*

## 2. Scope

### In scope
- `/log` route, Progress stream only
- Job picker with sticky-last-job + "Change" chip
- Budget line item picker: recently-used (this job, this week) + search + category chip filters
- Smart single input field whose label + keyboard depend on `install_budget_items.unit_type`
- Save flow fires "Logged!" confirmation off the local IndexedDB write (not the Supabase POST)
- Offline queue via `idb-keyval`: `pending → in_flight → failed/dead`
- Drain triggers: `visibilitychange → visible`, `window.online`, auth `SIGNED_IN`, manual retry, 60s interval while visible
- Pending-count chip in header (hidden when count = 0), red dot if any `dead` records exist
- "Today's claims" list below the form (append inline on each save)
- GPS fire-and-forget with 3s timeout
- Full use of the new `claim_kind` discriminator + `captured_at` client-clock + `over_budget` flag

### Not in scope (Phase 1)
- Variation stream (→ Phase 1.5)
- Rework stream + photo capture (→ Phase 1.6)
- `/settings/queue` dead-letter reassignment UI (→ Phase 2)
- Editing or deleting past claims (forever blocked — append-only invariant)
- Multi-photo, voice notes, past-claim browsing across days

## 3. Hot-path user flow (tap count = 3)

1. **Cold launch** (phone wake → tap app icon) → authed, lands on `/log` with sticky last job already selected.
2. **Tap 1** — tap the budget item in the Recently-Used list (1 tap on 80% case; 2 taps if using search).
3. **Tap 2** — tap the numeric keypad to enter the value. Keypad is pre-focused on item select; label reads e.g. `"Hours worked"` / `"m² complete"` / `"Lifts today"` / `"$ claimed"` based on `unit_type`.
4. **Tap 3** — tap "Save". Confirmation fires (green slide-down + haptic + inline row) within 50ms. Supabase POST happens in background.

**Cold-launch budget:** ≤3 taps on the 80% path. 4 taps on cold-launch first-use (job picker shown once; "Change job" only reopens it later). 2 taps if installer is logging a second claim against the same item back-to-back.

## 4. Screen inventory

### `/log` (primary)
- **Header**: job name + "Change job" chip + pending-count chip (if queue > 0)
- **Recently-used items** (this job, this week, most-recent-first, max 5)
- **Search + category chips** (scrollable below recents)
- **Input panel** (appears after item selected): single smart field + Save button
- **"Today's claims"** list (appended inline on each save — read-only, collapses after 5 minutes or 5 items to save real estate)

### `/log/pick-job` (sheet, opens from "Change job")
- Recent jobs (last 5) + search box
- Selecting a job sets `localStorage.lastJobId` and closes the sheet

### Existing `/dashboard` (unchanged Phase 1)
- Gets a "Log a claim" button linking to `/log`

## 5. Data model (already migrated)

Schema landed in commit `b5628f5` via `sql/03-phase1-claim-kind.sql`. New columns on `install_claims`:

| Column | Type | Purpose |
|---|---|---|
| `claim_kind` | text NOT NULL | discriminator: `'dollar'` / `'percent'` / `'hours'` / `'qty'` |
| `over_budget` | boolean NOT NULL DEFAULT false | app sets true when cumulative $-claims for item exceed `budget_amount` |
| `captured_at` | timestamptz NOT NULL | client-clock stamp at Save press — distinct from server `created_at` |
| `captured_lat` / `captured_lng` / `captured_accuracy_m` | nullable | fire-and-forget GPS at save |

Existing columns relied on: `id`, `job_id`, `budget_item_id`, `claim_date`, `claim_amount` (NOT NULL, canonical payable $), `percent_complete`, `hours`, `qty`, `rate_used`, `notes`, `created_by`, `created_at`, `company_id`, `company_service_id`, `unit_no`, `supervisor_id`, `sub_item_id`.

`claim_kind` semantics (the contract that downstream readers rely on):

| Kind | What installer enters | What app stores |
|---|---|---|
| `dollar` | $ amount | `claim_amount = X`, metadata fields null |
| `percent` | % of this milestone | `percent_complete = X`, `claim_amount = budget_amount × X / 100` if budget_amount known else 0 |
| `hours` | hours worked today | `hours = X`, `claim_amount = X × rate_used` (rate from selected `company_service_id`) |
| `qty` | units produced today | `qty = X`, `claim_amount = X × rate_used` (rate from selected `company_service_id`) |

Shape CHECK (`claim_kind_shape`, NOT VALID) enforces these on every new insert.

## 6. Offline queue architecture

### Queued record (stored in `idb-keyval`)

```ts
type QueueStatus =
  | { state: 'pending' }
  | { state: 'in_flight'; leaseUntil: number /* epoch ms */ }
  | { state: 'failed'; attempts: number; lastError: string; nextRetryAt: number }
  | { state: 'dead'; attempts: number; lastError: string; deadAt: number };

interface QueuedClaim {
  id: string;                 // UUIDv4 — same value written to install_claims.id
  kind: 'claim';              // reserved: future 'variation' / 'rework'
  payload: InstallClaimInsert;
  firstQueuedAt: number;
  updatedAt: number;
  status: QueueStatus;
  clientContext: { appVersion: string; deviceId: string; userId: string };
}
```

Keys: `queue:{id}` for each record, `queue:index` holds `string[]` of all ids. Keeping a separate index avoids enumerating the whole IndexedDB store on every drain.

### Idempotency — PK is the guarantee
Client-generated UUID on `install_claims.id` **is** the idempotency key. On drain-retry, a duplicate insert gets Postgres error 23505 (unique violation) — drainer treats that as success and removes from queue. No `client_request_id` column needed; adding one would create a drift risk with the 4 sibling apps that read this table.

### Drain algorithm

```
drain():
  if draining: return
  if !navigator.onLine: return
  draining = true
  try:
    for record in load_all():
      if not ready(record): continue       // pending, OR failed-past-nextRetryAt, OR in_flight-past-lease
      cas(record, { state: 'in_flight', leaseUntil: now + 30s })
      try:
        response = await supabase.from('install_claims').insert(record.payload)
        if response.status == 2xx or response.code == '23505':
          remove(record)
        elif response.code == '23503':     // FK violation (e.g., budget item was deleted by Hub re-import)
          deadletter(record, 'fk_missing:...')
        elif response.status 4xx:
          deadletter(record, response.message)
        else:                              // 5xx, network, abort
          record.status = { state: 'failed', attempts: attempts+1,
                            lastError, nextRetryAt: now + min(60s * 2^attempts, 1h) * jitter±20% }
          if attempts >= 8: deadletter(record, 'max_attempts')
          save(record)
      catch e:
        (same as 5xx branch)
  finally:
    draining = false
```

### Drain triggers
- `document.addEventListener('visibilitychange')` when document becomes visible
- `window.addEventListener('online')`
- Auth state → `SIGNED_IN`
- Manual "Retry now" action (deferred to Phase 2 UI, but the function is wired)
- `setInterval(drain, 60_000)` while tab visible — belt-and-braces for Android quirks

### FK violations
Dead letter with full payload preserved. Do NOT silent-drop (loses installer work) and do NOT stall queue (one zombie shouldn't block 20 good rows). `over_budget` items raise `install_flagged_items` on successful insert — that existing table is how supervisors already see exceptions.

### Storage quota
Phase 1 has no photos. QuotaExceeded is not expected. If thrown, catch on `.set` and block new saves with modal "Phone storage full — sync pending items before logging more."

## 7. Component tree

`/log` is fully a Client Component — `useAuth`, IndexedDB, `navigator.onLine`, geolocation all need the browser. There is **no useful Server Action** here: every mutation routes through the offline queue, and a Server Action would either bypass the queue (defeating the design) or be a pointless thin proxy to Supabase.

Server Components earn their keep in Phase 1 for: layout chrome, the auth-gated wrapper. The `'use client'` boundary sits at `app/log/page.tsx` and any component that uses `useAuth`, `idb-keyval`, or the queue.

```
app/
  layout.tsx                    Server
  providers.tsx                 Client (auth context provider)
  log/
    page.tsx                    Client
    components/
      JobHeader.tsx              Client
      RecentItems.tsx            Client
      ItemPicker.tsx             Client
      ClaimInput.tsx             Client
      TodaysClaimsList.tsx       Client
      PendingChip.tsx            Client
  log/pick-job/
    page.tsx                    Client (or /log modal — decide at impl time)
lib/
  queue.ts                      client-only — drain, enqueue, dead-letter
  money.ts                      Money branded type + parse/format helpers (per Math §8)
  variations.ts                 reserved for Phase 1.5
```

## 8. Money & number handling

Per Mathematician §8:

- **Store new money columns in integer cents** — deferred until Phase 2 (no new money columns in Phase 1; `claim_amount` stays `numeric` as existing).
- **`Money` branded type at the boundary**: Supabase reads → `Money` conversion via `parseAudCentsFromNumeric`. All arithmetic on claim_amount goes through `lib/money.ts` helpers. Never `+` or `*` directly on a raw number representing dollars.
- **Parse rule**: `"$1,000.00"` → strip `[^0-9.\-]`, parse to float, `Math.round(× 100)` = cents. Reject NaN, >`MAX_SAFE_INTEGER`, or >2 decimals with inline error "Invalid amount."
- **Display**: `Intl.NumberFormat('en-AU', { style: 'currency', currency: 'AUD' })` from cents.

Over-budget check at save time: `new_total_dollars_claimed(item) + this_dollars > budget_amount` → set `over_budget = true`, insert `install_flagged_items` row (existing flow), never block save.

## 9. Component contracts

### `claimInput: DollarClaim | PercentClaim | HoursClaim | QtyClaim`

```ts
type DollarClaim  = { kind: 'dollar';  budgetItemId: string; amountCents: number /* > 0 */; notes?: string }
type PercentClaim = { kind: 'percent'; budgetItemId: string; percent: number /* 0 < x ≤ 100 */; notes?: string }
type HoursClaim   = { kind: 'hours';   budgetItemId: string; hours: number /* > 0 */; companyServiceId: string; notes?: string }
type QtyClaim     = { kind: 'qty';     budgetItemId: string; qty: number /* > 0 */; companyServiceId: string; notes?: string }

type ClaimPayload = DollarClaim | PercentClaim | HoursClaim | QtyClaim
```

The `saveClaim(payload: ClaimPayload)` function is the single entry point. By type, you cannot construct an invalid claim — the runtime CHECK in the DB is the backstop, not the primary enforcement.

### `smart-input` label/keyboard mapping

```ts
unitTypeToInputMode(ut: string | null): {
  mode: ClaimKind;
  label: string;
  inputMode: 'numeric' | 'decimal';
  step: number;
}
```

Mapping:
- `'hours'` / `'hrs'` / `'h'` → `hours` mode, "Hours worked today", decimal, 0.25 step
- `'m2'` / `'sqm'` / `'area'` → `percent` mode if budget_amount known, else `qty` mode, "m² complete", decimal, 0.5 step
- `'lift'` / `'lifts'` / `'qty'` / `'each'` → `qty` mode, "Units today", numeric, 1 step
- `'%'` / `'pct'` / `'percent'` → `percent` mode, "% complete", numeric, 1 step (capped 0–100)
- default / `null` → `dollar` mode, "$ claimed", decimal, 0.01 step

Exact `unit_type` string conventions need one pass through live data at impl time (query `install_budget_items` for `DISTINCT unit_type`) to confirm the mapping is exhaustive. Unknown unit_type falls back to `dollar` mode.

## 10. Failure modes and mitigations

| Failure | Likelihood | Mitigation |
|---|---|---|
| Installer presses Save, phone dies before IndexedDB flush | Low | Await `idb.set(...)` before showing "Logged!" confirmation. <100ms window accepted. |
| Two installers log against same item offline, come online within 30s | Expected | Both become separate `install_claims` rows. Correct — each is a distinct event. Read-side aggregation (Postgres function `current_percent(item_id)` = `LEAST(100, SUM(percent_complete))`) handles ordering-independent sum. |
| Hub re-imports job mid-drain, wipes budget items | Low | FK violation → dead letter with payload preserved. `/settings/queue` reassign UI in Phase 2. Push Hub-app owner for soft-delete pattern. |
| Phone clock is days off | Low | `captured_at` stored as-is (don't normalise). `created_at` is canonical for ordering/analytics; `captured_at` is display-only. Detect `|captured_at - created_at| > 24h` server-side, flag row for supervisor. |
| `getCurrentPosition` hangs on some Android browsers | Low | 3s AbortController timeout, fire-and-forget. Save does not wait. |
| Double-fire of `visibilitychange` drains record twice | Absorbed | `draining` flag + `in_flight` lease handles single-tab. Unique PK collision (23505 → success) absorbs cross-tab. |

## 11. Open items for impl time (defer decisions to implementation, track here)

- **Exact `unit_type` distinct values** — query live DB before writing `unitTypeToInputMode()`. One-shot job at start of implementation.
- **Rate card lookup for hours/qty claims** — which `company_service_id` does the app auto-select vs require installer to pick? Depends on how `install_company_services` is currently seeded. Probe at impl time.
- **"Today's claims" list source** — in-memory from session saves, or also query Supabase for today's committed rows? Session-only is simpler; Supabase read adds consistency at cost of extra round trip. Lean session-only; reload = fresh list.
- **Pilot installer identity** — Scott picks when ready to ship (Strategist Q2). Does not affect code.

## 12. Ship sequence

1. Implementation plan written via `superpowers:writing-plans` skill (next step after this spec is approved).
2. Build `/log` route and all components per plan.
3. Local dev verify (end-to-end: airplane-mode test — save while offline, come online, confirm drain).
4. Deploy to Vercel preview, Scott dogfoods 3–5 days on a test job.
5. Hand to one trusted lead installer for week 2. Watch DAU metric.
6. Full rollout week 3 if DAU ≥ 4/5 of installers; rollback to paper if not, time-boxed 2 weeks.

## 13. Non-code commitments from Scott (Strategist)

1. 3–5 days solo dogfooding before any installer sees it
2. One pilot installer for week 2 before full rollout week 3
3. **Weekly Friday WhatsApp: "your logs drove $X of invoicing this week"** — the single biggest adoption lever, zero code
4. Rollback = paper + SMS, time-boxed 2 weeks; do NOT restore the retired Install UI
