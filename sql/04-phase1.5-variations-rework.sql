-- HYTEK Budget — Phase 1.5 schema: Variation + Rework capture fields
-- + partial CHECK enforcing PO-required-on-approved + install-photos storage bucket
--
-- Apply AFTER sql/01, 02, 03. Safe to re-run (IF NOT EXISTS + DROP/re-add on constraints).
--
-- What this does (additive only):
--   1. Adds captured_at timestamptz NOT NULL + GPS cols to job_variations
--   2. Adds captured_at timestamptz NOT NULL + GPS cols to job_rework
--   3. Adds partial CHECK on job_variations: status='approved' => po_reference non-empty
--      (NOT VALID — grandfathers any legacy approved rows with missing po_reference)
--   4. Creates install-photos Storage bucket (private) with auth RLS

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. job_variations — capture fields
-- -----------------------------------------------------------------------------
ALTER TABLE public.job_variations
  ADD COLUMN IF NOT EXISTS captured_at          timestamptz,
  ADD COLUMN IF NOT EXISTS captured_lat         numeric(9,6),
  ADD COLUMN IF NOT EXISTS captured_lng         numeric(9,6),
  ADD COLUMN IF NOT EXISTS captured_accuracy_m  integer;

-- Backfill legacy rows (currently zero — tables empty) from created_at
UPDATE public.job_variations
   SET captured_at = created_at
 WHERE captured_at IS NULL;

ALTER TABLE public.job_variations
  ALTER COLUMN captured_at SET DEFAULT now(),
  ALTER COLUMN captured_at SET NOT NULL;

-- -----------------------------------------------------------------------------
-- 2. job_rework — capture fields
-- -----------------------------------------------------------------------------
ALTER TABLE public.job_rework
  ADD COLUMN IF NOT EXISTS captured_at          timestamptz,
  ADD COLUMN IF NOT EXISTS captured_lat         numeric(9,6),
  ADD COLUMN IF NOT EXISTS captured_lng         numeric(9,6),
  ADD COLUMN IF NOT EXISTS captured_accuracy_m  integer;

UPDATE public.job_rework
   SET captured_at = created_at
 WHERE captured_at IS NULL;

ALTER TABLE public.job_rework
  ALTER COLUMN captured_at SET DEFAULT now(),
  ALTER COLUMN captured_at SET NOT NULL;

-- -----------------------------------------------------------------------------
-- 3. Partial CHECK: approved variations must have a real po_reference
-- -----------------------------------------------------------------------------
-- Mathematician §4: "approved requires po_reference" — app-level enforcement
-- was flagged as insufficient. This is the belt-and-braces.
ALTER TABLE public.job_variations
  DROP CONSTRAINT IF EXISTS variations_approved_requires_po;
ALTER TABLE public.job_variations
  ADD CONSTRAINT variations_approved_requires_po CHECK (
    status <> 'approved'
    OR (po_reference IS NOT NULL AND length(trim(po_reference)) > 0)
  ) NOT VALID;

-- -----------------------------------------------------------------------------
-- 4. Storage bucket for rework/variation photos
-- -----------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES ('install-photos', 'install-photos', false, 10485760)  -- 10 MB cap
ON CONFLICT (id) DO NOTHING;

-- Authenticated users can read + insert; no update/delete (append-only discipline)
DROP POLICY IF EXISTS "auth read install-photos" ON storage.objects;
CREATE POLICY "auth read install-photos"
  ON storage.objects FOR SELECT TO authenticated
  USING (bucket_id = 'install-photos');

DROP POLICY IF EXISTS "auth insert install-photos" ON storage.objects;
CREATE POLICY "auth insert install-photos"
  ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'install-photos');

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY — run each separately
-- =============================================================================

-- A. New columns exist on variations (expect 4)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_variations'
  AND column_name IN ('captured_at','captured_lat','captured_lng','captured_accuracy_m')
ORDER BY column_name;

-- B. New columns exist on rework (expect 4)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_rework'
  AND column_name IN ('captured_at','captured_lat','captured_lng','captured_accuracy_m')
ORDER BY column_name;

-- C. Partial CHECK is registered (convalidated = false, NOT VALID)
SELECT conname, convalidated, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.job_variations'::regclass
  AND conname = 'variations_approved_requires_po';

-- D. Storage bucket present
SELECT id, name, public, file_size_limit FROM storage.buckets WHERE id = 'install-photos';

-- E. Storage policies present (expect 2 rows — read + insert)
SELECT polname, cmd::text
FROM pg_policy
WHERE polrelid = 'storage.objects'::regclass
  AND polname IN ('auth read install-photos', 'auth insert install-photos');

-- F. Probe CHECK enforcement — should RAISE 'new row violates check constraint'
-- Uncomment to prove:
-- INSERT INTO public.job_variations (id, job_id, variation_number, description, status)
-- VALUES (gen_random_uuid(), (SELECT id FROM public.jobs LIMIT 1), 'TEST-CHECK', 'approved without PO test', 'approved');

-- =============================================================================
-- ROLLBACK (uncomment to undo)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "auth read install-photos" ON storage.objects;
-- DROP POLICY IF EXISTS "auth insert install-photos" ON storage.objects;
-- DELETE FROM storage.buckets WHERE id = 'install-photos';
-- ALTER TABLE public.job_variations DROP CONSTRAINT IF EXISTS variations_approved_requires_po;
-- ALTER TABLE public.job_variations
--   ALTER COLUMN captured_at DROP NOT NULL,
--   ALTER COLUMN captured_at DROP DEFAULT,
--   DROP COLUMN IF EXISTS captured_at,
--   DROP COLUMN IF EXISTS captured_lat,
--   DROP COLUMN IF EXISTS captured_lng,
--   DROP COLUMN IF EXISTS captured_accuracy_m;
-- ALTER TABLE public.job_rework
--   ALTER COLUMN captured_at DROP NOT NULL,
--   ALTER COLUMN captured_at DROP DEFAULT,
--   DROP COLUMN IF EXISTS captured_at,
--   DROP COLUMN IF EXISTS captured_lat,
--   DROP COLUMN IF EXISTS captured_lng,
--   DROP COLUMN IF EXISTS captured_accuracy_m;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
