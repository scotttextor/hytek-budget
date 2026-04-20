# Phase 1 — Live DB Probe Findings (2026-04-20)

Brief probe of the shared `hytek-detailing` Supabase to ground Phase 1 code in real data.

## 1. `install_budget_items.unit_type`

**Not probed this session.** Deferred to Task 18 E2E verification — if a real budget item's `unit_type` falls outside the Task 3 mapping, the fallback is `dollar` mode (safe default). Any misses surface as "installer saw a $ field when they expected hours" during dogfooding and are a 1-line mapping update in `src/lib/unit-type.ts`.

The Task 3 mapping recognises these token sets (case-insensitive):
- `hours / hrs / h / hour` → hours mode
- `m2 / sqm / m² / area` → percent (if budget_amount known) or qty mode
- `lift / lifts / qty / each / unit / units / ea` → qty mode
- `% / pct / percent` → percent mode
- anything else → **dollar mode** (safe fallback)

## 2. `install_company_services` (rate cards)

**Sample rows** (from `effective_to IS NULL` — current rates):

| category | unit     | rate |
|----------|----------|-----:|
| cranage  | per hour |  150 |
| cranage  | per hour |  180 |
| cranage  | per hour |  250 |
| cranage  | per trip |  200 |
| cranage  | per hour |   85 |
| cranage  | per hour |   85 |
| ewp      | per day  |  120 |
| ewp      | per day  |  180 |

**Key observations:**
- `unit` values are **billing cadence** (`per hour`, `per day`, `per trip`), NOT the same as `install_budget_items.unit_type` (which describes the item semantics)
- Rates stored as integer AUD dollars — no decimal cents in this table
- Same category can have multiple rate rows for the same `unit` (duplicate supplier entries — see cranage having two `per hour / 85` rows)
- Multiple categories per Phase 1.x — cranage and ewp confirmed. Other categories (framing/sheeting/etc.) likely have rates too but weren't in this sample

**Implication for Phase 1 code:** Rate-card wiring for `hours`/`qty` claim modes is **out of scope for Phase 1** (Progress stream only, gated behind fall-back-to-dollar in `ClaimInput.tsx`). When Phase 1.x adds the rate-card picker, it will need to handle multi-rate categories — the picker should show `company_name + rate + unit` so the installer disambiguates.

## 3. `install_claims.claim_kind` distribution (post-migration backfill)

| claim_kind | count |
|------------|------:|
| dollar     |     1 |
| hours      |     5 |

Legacy data is predominantly `hours`-mode (day-labour tracking on the retired Install UI) with one test dollar entry. No `percent` or `qty` rows in legacy — expected, the retired UI favoured direct dollar/hours entry.

This tells us:
- The NOT VALID shape CHECK grandfathered 6 rows; zero will trip the new CHECK on any read
- Phase 1 Progress stream ships with dollar mode as the primary path, which matches the shape of claim_kind=dollar exactly
- If Phase 1 analytics starts aggregating hours claims, the 5 legacy rows are the ones to spot-check

## What was deliberately NOT probed

- `install_budget_items.unit_type` distinct values — deferred to Task 18 live validation
- `install_company_services` column structure — inferred from sample rows; exact schema lives in `install-phase1-part1-tables.sql` if needed
- `install_company_services` row totals — not blocking Phase 1 work

## Open items rolled forward

- **Phase 1.x — rate-card wiring:** write a `useRateCards(companyId, category)` hook that returns the relevant rate rows with disambiguation data (supplier name, unit). Block `hours`/`qty` modes in `ClaimInput` until this ships. Currently they fall back to `dollar` mode.
- **Task 18 verification step:** confirm live budget items render with sensible input modes. Fix `unit-type.ts` mapping inline if any real value produces the wrong mode.
