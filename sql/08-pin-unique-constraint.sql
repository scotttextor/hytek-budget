-- HYTEK Budget — Migration 08: unique constraint on install_contractors.pin
--
-- ROOT-CAUSE FIX for the dup-PIN-9999 incident (2026-04-21):
--   install_supervisors has UNIQUE (pin) since day 1 (install-phase1-data-foundation.sql).
--   install_contractors (added in migration 05) mirrored the supervisors pattern in every
--   way EXCEPT this — it only got a partial lookup index (not unique). The
--   generateUniquePin() helper in the contractor admin tab does a check-then-insert
--   (TOCTOU): two concurrent admin inserts can both pass the app-layer uniqueness check
--   and then both INSERT the same PIN. The DB has no defense.
--
-- WHAT THIS DOES:
--   1. Verifies no duplicate PINs exist before attempting the constraint
--      (the ALTER will fail atomically if any exist — rolling back the whole transaction)
--   2. Adds UNIQUE (pin) on install_contractors.pin, matching install_supervisors
--   3. Keeps the existing idx_install_contractors_pin partial index for active-row lookup
--      (the new unique constraint creates its own full index, but the partial index is still
--      marginally faster for the PIN-lookup hot path — low cost to keep)
--
-- WHY FULL UNIQUE (not partial WHERE active = true):
--   Matching install_supervisors pattern exactly. Reusing a deactivated supervisor's PIN
--   would require regenerating it anyway (security — old PIN shouldn't leak to new person).
--   4-digit PIN pool = 9000 values; HYTEK will not exhaust this in our lifetime of staff.
--
-- APP-LAYER CHANGES (separate commit):
--   - Contractor tab: replace fetch-then-check with insert-and-retry-on-23505
--   - Supervisor tab: catch 23505 on manual PIN entry and show "PIN already in use"
--
-- Apply AFTER sql/01–07. Idempotent — safe to re-run.

BEGIN;

-- 1. Pre-flight: assert no duplicate PINs currently exist.
-- If this SELECT returns any rows, the next ALTER will fail and the whole tx rolls back.
-- Run this standalone FIRST if you want to inspect dups before attempting the migration:
--   SELECT pin, count(*) AS dup_count
--   FROM public.install_contractors
--   GROUP BY pin HAVING count(*) > 1;

-- 2. Add the unique constraint (mirrors install_supervisors).
-- Name matches the convention PostgreSQL would auto-generate for consistency.
ALTER TABLE public.install_contractors
  DROP CONSTRAINT IF EXISTS install_contractors_pin_key;

ALTER TABLE public.install_contractors
  ADD CONSTRAINT install_contractors_pin_key UNIQUE (pin);

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY
-- =============================================================================

-- A. Constraint exists and covers pin
SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.install_contractors'::regclass
  AND conname = 'install_contractors_pin_key';
-- Expect: 1 row, definition = UNIQUE (pin)

-- B. Confirm no dup PINs (should be 0 rows if tx committed)
SELECT pin, count(*) AS dup_count
FROM public.install_contractors
GROUP BY pin HAVING count(*) > 1;
-- Expect: 0 rows

-- C. Confirm install_supervisors constraint still exists (sanity — no collateral damage)
SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.install_supervisors'::regclass
  AND contype = 'u';
-- Expect: at least 1 row with UNIQUE (pin)

-- =============================================================================
-- ROLLBACK (uncomment if needed)
-- =============================================================================
-- BEGIN;
-- ALTER TABLE public.install_contractors
--   DROP CONSTRAINT IF EXISTS install_contractors_pin_key;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
