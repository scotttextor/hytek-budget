-- =============================================================================
-- HYTEK Budget — Migration v1 (Flavour A: Budget is sole writer)
--
-- Old Install UI retired; Budget app takes over. This migration:
--   1. Expands job_variations.status CHECK to the full state machine
--   2. Adds PO reference + change-tracking columns to job_variations
--   3. Adds append-only state transition log (variation_state_transitions)
--   4. Adds effective-date columns to install_company_services for rate history
--
-- Design decisions (from Panel #1 Mathematician review, adapted for Flavour A):
--   - Reuse existing job_variations.status column (no dual status/state)
--   - Extend existing install_company_services for rate cards (no new table,
--     mathematician flagged substantial overlap)
--   - Backfill existing status values to new vocabulary deterministically
--   - Append-only transition log; no UPDATE/DELETE policy
--
-- Apply: RUN 01-snapshot-install-tables.sql FIRST. Then paste this file into
--        Supabase SQL Editor against hytek-detailing project.
-- Audit: AFTER applying, run from hytek-detailing/app/:
--        node scripts/check-job-lifecycle.js
--        Expect: "No drift detected across all 3 per-department statuses"
-- Rollback: Block at the bottom of the file, commented out.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Expand job_variations.status CHECK to full state machine
-- -----------------------------------------------------------------------------
-- Existing values: pending | approved | in_progress | complete | rejected
-- Target values:   raised | priced | submitted | approved | invoiced
--                  | rejected | cancelled | superseded

-- Drop old constraint first
ALTER TABLE public.job_variations
  DROP CONSTRAINT IF EXISTS job_variations_status_check;

-- Backfill existing rows to new vocabulary (deterministic mapping)
UPDATE public.job_variations SET status = 'raised'    WHERE status = 'pending';
UPDATE public.job_variations SET status = 'approved'  WHERE status = 'in_progress';
UPDATE public.job_variations SET status = 'invoiced'  WHERE status = 'complete';
-- 'approved' and 'rejected' map through unchanged

-- Add new CHECK constraint
ALTER TABLE public.job_variations
  ADD CONSTRAINT job_variations_status_check
    CHECK (status IN (
      'raised', 'priced', 'submitted', 'approved',
      'invoiced', 'rejected', 'cancelled', 'superseded'
    ));

-- -----------------------------------------------------------------------------
-- 2. Add PO + change-tracking columns to job_variations
-- -----------------------------------------------------------------------------
ALTER TABLE public.job_variations
  ADD COLUMN IF NOT EXISTS po_reference       text,
  ADD COLUMN IF NOT EXISTS status_changed_at  timestamptz DEFAULT now(),
  ADD COLUMN IF NOT EXISTS status_changed_by  uuid REFERENCES public.profiles(id) ON DELETE SET NULL;

-- Backfill status_changed_at from created_at for existing rows
UPDATE public.job_variations
   SET status_changed_at = COALESCE(status_changed_at, created_at)
 WHERE status_changed_at IS NULL;

-- -----------------------------------------------------------------------------
-- 3. Append-only state transition log
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.variation_state_transitions (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  variation_id  uuid NOT NULL REFERENCES public.job_variations(id) ON DELETE CASCADE,
  from_status   text,    -- NULL on first insertion (creation event)
  to_status     text NOT NULL,
  changed_by    uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  changed_at    timestamptz NOT NULL DEFAULT now(),
  reason        text,
  CHECK (from_status IS NULL OR from_status <> to_status),
  CHECK (to_status IN (
    'raised', 'priced', 'submitted', 'approved',
    'invoiced', 'rejected', 'cancelled', 'superseded'
  ))
);

CREATE INDEX IF NOT EXISTS idx_variation_state_transitions_variation
  ON public.variation_state_transitions (variation_id, changed_at DESC);

ALTER TABLE public.variation_state_transitions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "auth read variation_state_transitions" ON public.variation_state_transitions;
CREATE POLICY "auth read variation_state_transitions"
  ON public.variation_state_transitions FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS "auth insert variation_state_transitions" ON public.variation_state_transitions;
CREATE POLICY "auth insert variation_state_transitions"
  ON public.variation_state_transitions FOR INSERT TO authenticated
  WITH CHECK (true);
-- No UPDATE or DELETE policy — append-only audit log.

-- Seed one "creation" transition row for every existing variation that doesn't
-- already have one (so the log is never empty for live variations)
INSERT INTO public.variation_state_transitions (variation_id, from_status, to_status, changed_at)
SELECT v.id, NULL, v.status, COALESCE(v.status_changed_at, v.created_at)
  FROM public.job_variations v
 WHERE NOT EXISTS (
   SELECT 1 FROM public.variation_state_transitions t WHERE t.variation_id = v.id
 );

-- -----------------------------------------------------------------------------
-- 4. Effective-date columns on install_company_services (rate card history)
-- -----------------------------------------------------------------------------
-- Panel #1 Mathematician found install_company_services already models
-- (company, category, rate, unit). Extending instead of duplicating.
ALTER TABLE public.install_company_services
  ADD COLUMN IF NOT EXISTS effective_from  date DEFAULT CURRENT_DATE,
  ADD COLUMN IF NOT EXISTS effective_to    date,
  ADD COLUMN IF NOT EXISTS created_by      uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS notes           text;

-- Invariant: effective_to >= effective_from when both non-null
ALTER TABLE public.install_company_services
  DROP CONSTRAINT IF EXISTS install_company_services_date_order;
ALTER TABLE public.install_company_services
  ADD CONSTRAINT install_company_services_date_order
    CHECK (effective_to IS NULL OR effective_to >= effective_from);

-- Index for "current rate" queries
CREATE INDEX IF NOT EXISTS idx_install_company_services_current
  ON public.install_company_services (company_id, category, effective_from DESC)
  WHERE effective_to IS NULL;

-- -----------------------------------------------------------------------------
-- 5. Tell PostgREST about the schema change (HYTEK house pattern)
-- -----------------------------------------------------------------------------
NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- Post-apply verification
-- =============================================================================
-- Run these queries after the migration commits:
--
-- 1. All existing variations now have valid new-vocabulary status:
--    SELECT status, COUNT(*) FROM job_variations GROUP BY status ORDER BY 2 DESC;
--
-- 2. Every variation has at least one transition log entry:
--    SELECT COUNT(*) AS orphans FROM job_variations v
--      WHERE NOT EXISTS (SELECT 1 FROM variation_state_transitions t
--                         WHERE t.variation_id = v.id);
--    -- expect 0
--
-- 3. Lifecycle audit is still clean:
--    cd ../hytek-detailing/app && node scripts/check-job-lifecycle.js
--    -- expect "No drift detected"
-- =============================================================================


-- =============================================================================
-- Rollback (uncomment + run in Supabase SQL Editor if lifecycle audit drifts)
-- =============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS public.variation_state_transitions;
-- ALTER TABLE public.job_variations
--   DROP CONSTRAINT IF EXISTS job_variations_status_check,
--   DROP COLUMN IF EXISTS po_reference,
--   DROP COLUMN IF EXISTS status_changed_at,
--   DROP COLUMN IF EXISTS status_changed_by;
-- -- Restore original status CHECK
-- UPDATE public.job_variations SET status = 'pending'     WHERE status = 'raised';
-- UPDATE public.job_variations SET status = 'in_progress' WHERE status = 'approved'; -- note lossy
-- UPDATE public.job_variations SET status = 'complete'    WHERE status = 'invoiced';
-- ALTER TABLE public.job_variations
--   ADD CONSTRAINT job_variations_status_check
--     CHECK (status IN ('pending','approved','in_progress','complete','rejected'));
-- ALTER TABLE public.install_company_services
--   DROP CONSTRAINT IF EXISTS install_company_services_date_order,
--   DROP COLUMN IF EXISTS effective_from,
--   DROP COLUMN IF EXISTS effective_to,
--   DROP COLUMN IF EXISTS created_by,
--   DROP COLUMN IF EXISTS notes;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
-- =============================================================================
