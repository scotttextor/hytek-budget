-- HYTEK Budget — Phase 1 schema: discriminated claim_kind + scope-change flag
--                 + client-clock captured_at + GPS
-- Apply AFTER 01-snapshot-install-tables.sql and 02-budget-migration-v1.sql
--
-- SAFE TO RE-RUN — all statements use IF NOT EXISTS / DROP IF EXISTS.
--
-- What this does (additive only — no drops, no renames on shared columns):
--   1. Adds claim_kind discriminator text column to install_claims
--   2. Adds over_budget boolean (set by app when claim pushes item over its budget)
--   3. Adds captured_at timestamptz (client clock at save time — distinct from
--      created_at which is server stamp; Mathematician §7 requirement)
--   4. Adds GPS columns (nullable, fire-and-forget at save)
--   5. Backfills existing rows deterministically
--   6. Locks in NOT NULL on claim_kind + captured_at (safe after backfill)
--   7. Adds value CHECK: claim_kind ∈ {dollar, percent, hours, qty}
--   8. Adds shape CHECK (NOT VALID) enforcing new rows match the discriminator
--
-- The shape CHECK is NOT VALID so it grandfathers any legacy rows that may have
-- multiple metadata fields populated; going forward every new insert must match.
--
-- Design rationale (Panel #2 — Mathematician + Architect):
--   Real schema: claim_amount is ALWAYS the dollar value (NOT NULL, defaults to 0).
--   Metadata fields (percent_complete, hours+rate_used, qty+rate_used) are the
--   audit trail for HOW the dollars were computed. claim_kind tells readers which
--   input path was taken without parsing nulls across four columns.
--
--   Why captured_at is new and not claim_date:
--     claim_date is a date (day resolution) — insufficient for ordering rapid
--     offline-queue drains or detecting client-clock skew. captured_at is
--     timestamptz (ms precision). claim_date stays for display/reporting;
--     captured_at is the canonical client-stamp for app logic.

BEGIN;

-- -----------------------------------------------------------------------------
-- 1-4. Additive columns
-- -----------------------------------------------------------------------------
ALTER TABLE public.install_claims
  ADD COLUMN IF NOT EXISTS claim_kind           text,
  ADD COLUMN IF NOT EXISTS over_budget          boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS captured_at          timestamptz,
  ADD COLUMN IF NOT EXISTS captured_lat         numeric(9,6),
  ADD COLUMN IF NOT EXISTS captured_lng         numeric(9,6),
  ADD COLUMN IF NOT EXISTS captured_accuracy_m  integer;

-- -----------------------------------------------------------------------------
-- 5a. Backfill claim_kind — discriminate by which metadata field is populated.
--     Priority order: percent > hours > qty > dollar.
--     Rows with no metadata (legacy dollar-only claims) fall through to 'dollar'.
-- -----------------------------------------------------------------------------
UPDATE public.install_claims
   SET claim_kind = CASE
     WHEN percent_complete IS NOT NULL AND percent_complete > 0 THEN 'percent'
     WHEN hours IS NOT NULL AND hours > 0                        THEN 'hours'
     WHEN qty IS NOT NULL   AND qty > 0                          THEN 'qty'
     ELSE                                                             'dollar'
   END
 WHERE claim_kind IS NULL;

-- -----------------------------------------------------------------------------
-- 5b. Backfill captured_at from created_at for legacy rows.
--     (True client-stamp was never captured historically; falling back to server
--     time is the best we can do. New rows will have a true client stamp.)
-- -----------------------------------------------------------------------------
UPDATE public.install_claims
   SET captured_at = created_at
 WHERE captured_at IS NULL;

-- -----------------------------------------------------------------------------
-- 6. Lock in NOT NULL (safe — backfill just populated every row)
-- -----------------------------------------------------------------------------
ALTER TABLE public.install_claims
  ALTER COLUMN claim_kind   SET NOT NULL,
  ALTER COLUMN captured_at  SET NOT NULL;

-- -----------------------------------------------------------------------------
-- 7. Value CHECK — drop/recreate so the migration is idempotent
-- -----------------------------------------------------------------------------
ALTER TABLE public.install_claims
  DROP CONSTRAINT IF EXISTS claim_kind_values;
ALTER TABLE public.install_claims
  ADD CONSTRAINT claim_kind_values
    CHECK (claim_kind IN ('dollar','percent','hours','qty'));

-- -----------------------------------------------------------------------------
-- 8. Shape CHECK (NOT VALID grandfathers legacy rows, enforces new inserts)
--    'dollar' = pure $-amount claim, no metadata fields populated
--    'percent' = milestone % claim; app computes claim_amount from budget_amount
--    'hours'   = labour claim; app computes claim_amount = hours × rate_used
--    'qty'     = piecework claim; app computes claim_amount = qty × rate_used
-- -----------------------------------------------------------------------------
ALTER TABLE public.install_claims
  DROP CONSTRAINT IF EXISTS claim_kind_shape;
ALTER TABLE public.install_claims
  ADD CONSTRAINT claim_kind_shape CHECK (
    (claim_kind = 'dollar'  AND claim_amount > 0
                            AND percent_complete IS NULL
                            AND hours IS NULL
                            AND qty IS NULL) OR
    (claim_kind = 'percent' AND percent_complete IS NOT NULL
                            AND percent_complete > 0
                            AND percent_complete <= 100
                            AND hours IS NULL
                            AND qty IS NULL) OR
    (claim_kind = 'hours'   AND hours IS NOT NULL
                            AND hours > 0
                            AND percent_complete IS NULL
                            AND qty IS NULL) OR
    (claim_kind = 'qty'     AND qty IS NOT NULL
                            AND qty > 0
                            AND percent_complete IS NULL
                            AND hours IS NULL)
  ) NOT VALID;

-- Tell PostgREST about the schema change (HYTEK house pattern)
NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY — run each query separately and read the output
-- =============================================================================

-- A. New columns exist (expect 6 rows)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'install_claims'
  AND column_name IN (
    'claim_kind','over_budget','captured_at',
    'captured_lat','captured_lng','captured_accuracy_m'
  )
ORDER BY column_name;

-- B. Backfill sanity: no NULL claim_kinds, distribution visible
SELECT claim_kind, COUNT(*) AS row_count
FROM public.install_claims
GROUP BY claim_kind
ORDER BY row_count DESC;

-- C. captured_at is NOT NULL everywhere, matches created_at on legacy rows
SELECT
  COUNT(*) FILTER (WHERE captured_at IS NULL)                      AS null_captured,
  COUNT(*) FILTER (WHERE captured_at = created_at)                 AS backfilled_from_created,
  COUNT(*) FILTER (WHERE captured_at <> created_at)                AS distinct_timestamps
FROM public.install_claims;

-- D. Constraints are registered
SELECT conname, convalidated, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.install_claims'::regclass
  AND conname IN ('claim_kind_values','claim_kind_shape');
-- Expect:
--   claim_kind_values  convalidated = true
--   claim_kind_shape   convalidated = false  (NOT VALID — grandfathers legacy)

-- E. Shape enforcement smoke test — should RAISE 'new row violates check constraint'
-- Uncomment to prove it:
-- INSERT INTO public.install_claims
--   (id, job_id, budget_item_id, claim_date, claim_kind, claim_amount, percent_complete)
-- VALUES (
--   gen_random_uuid(),
--   (SELECT job_id FROM public.install_budget_items LIMIT 1),
--   (SELECT id FROM public.install_budget_items LIMIT 1),
--   CURRENT_DATE, 'dollar', 100, 50
-- );

-- =============================================================================
-- ROLLBACK (uncomment block to undo)
-- =============================================================================
-- BEGIN;
-- ALTER TABLE public.install_claims DROP CONSTRAINT IF EXISTS claim_kind_shape;
-- ALTER TABLE public.install_claims DROP CONSTRAINT IF EXISTS claim_kind_values;
-- ALTER TABLE public.install_claims
--   ALTER COLUMN claim_kind  DROP NOT NULL,
--   ALTER COLUMN captured_at DROP NOT NULL;
-- ALTER TABLE public.install_claims
--   DROP COLUMN IF EXISTS claim_kind,
--   DROP COLUMN IF EXISTS over_budget,
--   DROP COLUMN IF EXISTS captured_at,
--   DROP COLUMN IF EXISTS captured_lat,
--   DROP COLUMN IF EXISTS captured_lng,
--   DROP COLUMN IF EXISTS captured_accuracy_m;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
