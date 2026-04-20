# Phase 1 — E2E Verification Findings (2026-04-20)

Verification of `phase1-quick-log` branch against local dev server + live Supabase + Claude-in-Chrome browser automation. Last commit verified: `14ff387`.

## Happy path — PASS

Full flow Dashboard → pick-job → /log → pick item → enter amount → Save:

- Dashboard "Log a claim" button → `/log`
- `/log` with no sticky job → redirect to `/log/pick-job` ✓
- Pick `Test 30 Unit Full-Coverage Complex` → localStorage write + `router.replace('/log')` ✓
- `/log` with sticky job → loads 20 budget items, renders JobHeader + ItemPicker ✓
- Click `Form 12 Budget` → ClaimInput mounts in dollar mode (unit = "per inspection" falls back to dollar — correct) ✓
- Enter `250`, notes `E2E test from Claude — Phase 1 verification`, Save ✓
- Save handler: `buildClaimRow` → `enqueueClaim` to IndexedDB → setConfirmation fires → drainNow in background ✓
- Supabase row lands within ~1s:
  - `id`: b145de86-81c5-4968-ba8c-ea727ad57600 (client UUID)
  - `claim_kind`: dollar
  - `claim_amount`: 250
  - `captured_at`: 2026-04-20T07:35:53.351+00:00 (client stamp)
  - `created_at`: 2026-04-20T07:35:54.329+00:00 (server, ~1s later)
  - `over_budget`: false (correct — $250 well under $10,500 budget)
  - `captured_lat/lng/accuracy_m`: null (browser blocked geolocation — fire-and-forget handled cleanly)
- IndexedDB queue drained clean — only `queue:index` master key remains; no `queue:{id}` records ✓
- Today's claims list appended with `Form 12 Budget — $250.00 — 5:35 pm` ✓
- Recently logged populated with the item (useRecentItems refreshed after drain) ✓

## Bug caught + root-caused during E2E

**Symptom:** `/log` showed "No items match" despite 20 items existing for the test job.

**Root cause:** Phase 0 scaffolding mirrored `install_budget_items` incorrectly in `src/lib/types.ts` — invented a `description` column (real field is `name`), missed 11 other real columns. Task 16 `/log/page.tsx` then ordered by `.order('description')` which caused Supabase to return an error silently; `data` was null, fallback was empty array.

**Fix:** Commit `14ff387` — expanded `InstallBudgetItem` to include every real column, switched order to `sort_order, name`, replaced `description` refs with `name` across ClaimInput, ItemPicker, TodaysClaimsList. Also made `ClaimInput` fall back from `unit_type` to `unit` when the former is null (real data has `unit` populated, `unit_type` often null).

**Why it matters for the session:** This is the *second* types-vs-real-schema drift found in this session (the first was `claim_amount` vs my invented `amount` during the schema migration). Both root-caused and fixed without patching. The pattern is clear: **Phase 0's `types.ts` was written from memory, not the live schema.** Leaving a memo below for the next session.

## Not tested in this E2E pass

- **Offline path** (DevTools offline → save → online → drain verification). Architectural coverage in `queue-drain.test.ts` covers the branches — real-device offline testing is dogfood-week territory, not CI.
- **Mobile device form factor** (haptic, actual 16px-no-zoom on iOS, thumb reach). Bench testing on a browser only gets you so far.
- **Two installers logging against the same item concurrently** — architecturally handled (append-only + unique PK) but not exercised.
- **FK-violation dead-letter path** — covered by `classifyResponse` unit test, not exercised against live Supabase.
- **Schema CHECK bite** — the `claim_kind_shape` CHECK constraint grandfathered legacy rows NOT VALID and enforces on new inserts. Confirmed in live DB via `pg_constraint` query on 2026-04-20 at schema-apply time; not re-tested here.

## Ready to ship

- 5 build routes compile (`/`, `/_not-found`, `/dashboard`, `/log`, `/log/pick-job`, `/login`)
- 49 unit tests pass
- `npx tsc --noEmit` clean
- Happy path works against live Supabase
- Schema drift bug caught and fixed
- Ready for 3–5 day dogfooding on a real mobile device per Strategist commitment

## Memo for next session

When scaffolding a new app that reads a shared DB: **do NOT mirror types from memory or another app's TS file.** Hit the live DB (Supabase `/rest/v1/<table>?select=*&limit=1` with the anon key from `.env.local`) and build the type from the actual response. Cost of 2 minutes of curl, saves hours of silent-failure debugging downstream. Save this lesson to memory after the session closes.
