-- HYTEK Budget — Migration 10: variations workflow + contractor variation cost + review override
--
-- Scott's decisions (locked 2026-04-22):
--   - Submit: correspondence required, PO optional, track submitter+time
--   - Approve: acceptance + accepted_by + correspondence required, PO optional
--   - PO editable at any stage (not state-locked)
--   - Attachments: PDFs / images / .eml / .msg — download-only preview
--   - Contractor cost: editable at variation raise AND at assignment
--   - Junction table for contractor-variation assignments (parallel to budget-item version)
--   - Review queue mandatory — only reviewed reports count toward progress
--   - Review mode: supervisor can OVERRIDE the contractor's percent (Scott's choice)

BEGIN;

-- =============================================================================
-- 1. job_variations — new workflow fields
-- =============================================================================

ALTER TABLE public.job_variations
  ADD COLUMN IF NOT EXISTS submitted_at                  timestamptz,
  ADD COLUMN IF NOT EXISTS submitted_by                  uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS submission_correspondence_url text,
  ADD COLUMN IF NOT EXISTS submission_note               text,
  ADD COLUMN IF NOT EXISTS has_po                        boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS acceptance_received           boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS acceptance_by_name            text,
  ADD COLUMN IF NOT EXISTS acceptance_at                 timestamptz,
  ADD COLUMN IF NOT EXISTS acceptance_correspondence_url text,
  ADD COLUMN IF NOT EXISTS acceptance_note               text,
  ADD COLUMN IF NOT EXISTS contractor_cost               numeric NOT NULL DEFAULT 0;

-- Seed has_po = true for any existing variation with a non-empty po_reference
UPDATE public.job_variations
   SET has_po = true
 WHERE has_po = false
   AND po_reference IS NOT NULL
   AND length(trim(po_reference)) > 0;

-- =============================================================================
-- 2. Replace the old "Approved requires PO" CHECK with the new acceptance gate
-- =============================================================================
-- Drop old constraint from migration 04 if present
ALTER TABLE public.job_variations
  DROP CONSTRAINT IF EXISTS variations_approved_requires_po;

-- New rule: Approved requires acceptance_received + acceptance_by_name + acceptance_correspondence_url
ALTER TABLE public.job_variations
  DROP CONSTRAINT IF EXISTS variations_approved_requires_acceptance;
ALTER TABLE public.job_variations
  ADD CONSTRAINT variations_approved_requires_acceptance CHECK (
    status <> 'approved'
    OR (
      acceptance_received = true
      AND acceptance_by_name IS NOT NULL
      AND length(trim(acceptance_by_name)) > 0
      AND acceptance_correspondence_url IS NOT NULL
      AND length(trim(acceptance_correspondence_url)) > 0
    )
  ) NOT VALID;

-- =============================================================================
-- 3. install_contractor_variation_assignments — new junction table
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.install_contractor_variation_assignments (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contractor_id           uuid NOT NULL REFERENCES public.install_contractors(id) ON DELETE RESTRICT,
  variation_id            uuid NOT NULL REFERENCES public.job_variations(id)      ON DELETE RESTRICT,
  agreed_contractor_cost  numeric NOT NULL DEFAULT 0,
  agreed_by               uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  agreed_at               timestamptz NOT NULL DEFAULT now(),
  assigned_at             timestamptz NOT NULL DEFAULT now(),
  revoked_at              timestamptz,
  revoked_by              uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  notes                   text,
  CONSTRAINT contractor_variation_unique UNIQUE (contractor_id, variation_id),
  CONSTRAINT variation_revoke_after_assign CHECK (revoked_at IS NULL OR revoked_at > assigned_at)
);

CREATE INDEX IF NOT EXISTS idx_contractor_variation_assignments_contractor
  ON public.install_contractor_variation_assignments (contractor_id, revoked_at)
  WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_contractor_variation_assignments_variation
  ON public.install_contractor_variation_assignments (variation_id, revoked_at)
  WHERE revoked_at IS NULL;

ALTER TABLE public.install_contractor_variation_assignments ENABLE ROW LEVEL SECURITY;

-- Staff manages (admin + supervisor), anon reads their own (app-layer filtered) — parallel to budget-item version
DROP POLICY IF EXISTS "staff manages variation assignments" ON public.install_contractor_variation_assignments;
CREATE POLICY "staff manages variation assignments" ON public.install_contractor_variation_assignments
  FOR ALL TO authenticated
  USING (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor')))
  WITH CHECK (EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor')));

DROP POLICY IF EXISTS "anon reads variation assignments (app-filtered)" ON public.install_contractor_variation_assignments;
CREATE POLICY "anon reads variation assignments (app-filtered)" ON public.install_contractor_variation_assignments
  FOR SELECT TO anon
  USING (revoked_at IS NULL);

-- =============================================================================
-- 4. install_progress_reports — support variation-linked reports + override %
-- =============================================================================

-- Column to link progress reports to a variation (alternative to budget_item_id)
ALTER TABLE public.install_progress_reports
  ADD COLUMN IF NOT EXISTS variation_id uuid REFERENCES public.job_variations(id) ON DELETE RESTRICT;

-- Override percent — what the supervisor approved (may differ from contractor's stated percent_complete)
ALTER TABLE public.install_progress_reports
  ADD COLUMN IF NOT EXISTS approved_percent_complete numeric(5,2);

-- Dismiss reason (audit trail)
ALTER TABLE public.install_progress_reports
  ADD COLUMN IF NOT EXISTS review_note text;

-- Exactly one of (budget_item_id, variation_id) must be set — existing rows have budget_item_id set, so NOT VALID grandfathers
ALTER TABLE public.install_progress_reports
  DROP CONSTRAINT IF EXISTS progress_report_target_exclusive;
ALTER TABLE public.install_progress_reports
  ADD CONSTRAINT progress_report_target_exclusive CHECK (
    (budget_item_id IS NOT NULL AND variation_id IS NULL) OR
    (budget_item_id IS NULL AND variation_id IS NOT NULL)
  ) NOT VALID;

-- Index for variation-progress lookups (pairs with existing contractor index)
CREATE INDEX IF NOT EXISTS idx_progress_reports_variation
  ON public.install_progress_reports (variation_id, status, captured_at DESC)
  WHERE variation_id IS NOT NULL;

-- =============================================================================
-- 5. install_progress_reports — anon INSERT policy update to allow variation reports
-- =============================================================================
-- The existing anon-insert policy from migration 05/07 gates on install_contractor_assignments.
-- For variation reports, it should gate on install_contractor_variation_assignments instead.
-- Rewrite with a branch.

DROP POLICY IF EXISTS "anon writes reports (assignment-gated)" ON public.install_progress_reports;
CREATE POLICY "anon writes reports (assignment-gated)" ON public.install_progress_reports
  FOR INSERT TO anon
  WITH CHECK (
    -- budget-item report: gated on a non-revoked budget-item assignment
    (
      budget_item_id IS NOT NULL
      AND EXISTS (
        SELECT 1 FROM public.install_contractor_assignments a
        WHERE a.contractor_id = install_progress_reports.contractor_id
          AND a.job_id        = install_progress_reports.job_id
          AND a.budget_item_id = install_progress_reports.budget_item_id
          AND a.revoked_at IS NULL
      )
    )
    OR
    -- variation report: gated on a non-revoked variation assignment
    (
      variation_id IS NOT NULL
      AND EXISTS (
        SELECT 1 FROM public.install_contractor_variation_assignments v
        WHERE v.contractor_id = install_progress_reports.contractor_id
          AND v.variation_id  = install_progress_reports.variation_id
          AND v.revoked_at IS NULL
      )
    )
  );

-- =============================================================================
-- 6. Effective-progress helper function
-- =============================================================================
-- Returns the capped sum of approved percents for an item/variation.
-- The app-side current-progress UI reads through this so logic is in one place.
-- Uses approved_percent_complete (override) if set, else falls back to
-- percent_complete (contractor's stated number) — but only for 'reviewed' rows.

CREATE OR REPLACE FUNCTION public.fn_current_progress_for_item(p_budget_item_id uuid)
RETURNS numeric
LANGUAGE sql
STABLE
AS $$
  SELECT LEAST(100, COALESCE(SUM(
    COALESCE(approved_percent_complete, percent_complete, 0)
  ), 0))
  FROM public.install_progress_reports
  WHERE budget_item_id = p_budget_item_id
    AND status = 'reviewed'
$$;

CREATE OR REPLACE FUNCTION public.fn_current_progress_for_variation(p_variation_id uuid)
RETURNS numeric
LANGUAGE sql
STABLE
AS $$
  SELECT LEAST(100, COALESCE(SUM(
    COALESCE(approved_percent_complete, percent_complete, 0)
  ), 0))
  FROM public.install_progress_reports
  WHERE variation_id = p_variation_id
    AND status = 'reviewed'
$$;

-- =============================================================================
-- 7. Storage bucket for variation attachments (correspondence)
-- =============================================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'variation-attachments',
  'variation-attachments',
  false,
  26214400,  -- 25 MB (emails with attachments can be hefty)
  ARRAY[
    'application/pdf',
    'image/jpeg', 'image/png', 'image/heic', 'image/webp',
    'message/rfc822',                              -- .eml
    'application/vnd.ms-outlook'                   -- .msg
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Staff can read + insert, contractors/customers cannot touch
DROP POLICY IF EXISTS "staff read variation-attachments" ON storage.objects;
CREATE POLICY "staff read variation-attachments"
  ON storage.objects FOR SELECT TO authenticated
  USING (
    bucket_id = 'variation-attachments'
    AND EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor'))
  );

DROP POLICY IF EXISTS "staff insert variation-attachments" ON storage.objects;
CREATE POLICY "staff insert variation-attachments"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (
    bucket_id = 'variation-attachments'
    AND EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor'))
  );

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY (run each block separately)
-- =============================================================================

-- A. New job_variations columns (expect 11)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_variations'
  AND column_name IN (
    'submitted_at','submitted_by','submission_correspondence_url','submission_note',
    'has_po','acceptance_received','acceptance_by_name','acceptance_at',
    'acceptance_correspondence_url','acceptance_note','contractor_cost'
  )
ORDER BY column_name;

-- B. Approve-requires-acceptance CHECK in place, old PO CHECK gone
SELECT conname, convalidated, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.job_variations'::regclass
  AND conname IN ('variations_approved_requires_acceptance','variations_approved_requires_po');
-- expect: acceptance row present, po row absent

-- C. install_contractor_variation_assignments table + indexes
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'install_contractor_variation_assignments'
ORDER BY indexname;

-- D. install_progress_reports additions
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'install_progress_reports'
  AND column_name IN ('variation_id','approved_percent_complete','review_note');

-- E. Helper functions exist
SELECT proname, pronargs FROM pg_proc
WHERE proname IN ('fn_current_progress_for_item','fn_current_progress_for_variation')
ORDER BY proname;

-- F. Storage bucket exists
SELECT id, name, public, file_size_limit, allowed_mime_types FROM storage.buckets WHERE id = 'variation-attachments';

-- =============================================================================
-- ROLLBACK (uncomment to undo)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "staff read variation-attachments" ON storage.objects;
-- DROP POLICY IF EXISTS "staff insert variation-attachments" ON storage.objects;
-- DELETE FROM storage.buckets WHERE id = 'variation-attachments';
-- DROP FUNCTION IF EXISTS public.fn_current_progress_for_variation(uuid);
-- DROP FUNCTION IF EXISTS public.fn_current_progress_for_item(uuid);
-- ALTER TABLE public.install_progress_reports DROP CONSTRAINT IF EXISTS progress_report_target_exclusive;
-- ALTER TABLE public.install_progress_reports DROP COLUMN IF EXISTS variation_id;
-- ALTER TABLE public.install_progress_reports DROP COLUMN IF EXISTS approved_percent_complete;
-- ALTER TABLE public.install_progress_reports DROP COLUMN IF EXISTS review_note;
-- DROP POLICY IF EXISTS "staff manages variation assignments" ON public.install_contractor_variation_assignments;
-- DROP POLICY IF EXISTS "anon reads variation assignments (app-filtered)" ON public.install_contractor_variation_assignments;
-- DROP TABLE IF EXISTS public.install_contractor_variation_assignments;
-- ALTER TABLE public.job_variations DROP CONSTRAINT IF EXISTS variations_approved_requires_acceptance;
-- ALTER TABLE public.job_variations
--   DROP COLUMN IF EXISTS submitted_at, DROP COLUMN IF EXISTS submitted_by,
--   DROP COLUMN IF EXISTS submission_correspondence_url, DROP COLUMN IF EXISTS submission_note,
--   DROP COLUMN IF EXISTS has_po, DROP COLUMN IF EXISTS acceptance_received,
--   DROP COLUMN IF EXISTS acceptance_by_name, DROP COLUMN IF EXISTS acceptance_at,
--   DROP COLUMN IF EXISTS acceptance_correspondence_url, DROP COLUMN IF EXISTS acceptance_note,
--   DROP COLUMN IF EXISTS contractor_cost;
-- -- Optional: restore the old approved-requires-PO CHECK
-- ALTER TABLE public.job_variations
--   ADD CONSTRAINT variations_approved_requires_po CHECK (
--     status <> 'approved'
--     OR (po_reference IS NOT NULL AND length(trim(po_reference)) > 0)
--   ) NOT VALID;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
