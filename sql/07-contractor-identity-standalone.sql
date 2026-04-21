-- HYTEK Budget — Migration 07: contractor identity standalone (no profile required)
--
-- Fixes T3 bug: profiles.id has FK to auth.users(id); PIN-only contractors
-- have no auth.users row, so creating a profiles row was impossible.
--
-- Fix: treat install_contractors.id as the canonical contractor identity.
-- Make profile_id nullable (some HYTEK staff contractors may also have a
-- profile — future case). Re-point child-table FKs at install_contractors.

BEGIN;

-- 1. install_contractors: profile_id nullable (keep column for future use)
ALTER TABLE public.install_contractors
  ALTER COLUMN profile_id DROP NOT NULL;

-- Drop the one-profile-one-contractor unique constraint since most contractors
-- will have NULL profile_id now
ALTER TABLE public.install_contractors
  DROP CONSTRAINT IF EXISTS one_profile_one_contractor;

-- Partial unique: if profile_id IS NOT NULL, it's still unique across contractors
CREATE UNIQUE INDEX IF NOT EXISTS uq_install_contractors_profile_id_when_set
  ON public.install_contractors (profile_id)
  WHERE profile_id IS NOT NULL;

-- 2. install_contractor_assignments.contractor_id: repoint FK from profiles → install_contractors
ALTER TABLE public.install_contractor_assignments
  DROP CONSTRAINT IF EXISTS install_contractor_assignments_contractor_id_fkey;
ALTER TABLE public.install_contractor_assignments
  ADD CONSTRAINT install_contractor_assignments_contractor_id_fkey
    FOREIGN KEY (contractor_id) REFERENCES public.install_contractors(id) ON DELETE RESTRICT;

-- 3. install_progress_reports.contractor_id: repoint FK from profiles → install_contractors
ALTER TABLE public.install_progress_reports
  DROP CONSTRAINT IF EXISTS install_progress_reports_contractor_id_fkey;
ALTER TABLE public.install_progress_reports
  ADD CONSTRAINT install_progress_reports_contractor_id_fkey
    FOREIGN KEY (contractor_id) REFERENCES public.install_contractors(id) ON DELETE RESTRICT;

-- 4. install_photos.created_by: make nullable so contractor photos (no profile)
-- can be uploaded with created_by = NULL and attributed via report_id linkage instead
ALTER TABLE public.install_photos
  ALTER COLUMN created_by DROP NOT NULL;

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =========================================================
-- VERIFY
-- =========================================================

-- A. install_contractors.profile_id now nullable
SELECT column_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'install_contractors'
  AND column_name = 'profile_id';
-- expect: is_nullable = 'YES'

-- B. install_contractor_assignments.contractor_id FK target
SELECT pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.install_contractor_assignments'::regclass
  AND conname = 'install_contractor_assignments_contractor_id_fkey';
-- expect: references install_contractors(id)

-- C. install_progress_reports.contractor_id FK target
SELECT pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.install_progress_reports'::regclass
  AND conname = 'install_progress_reports_contractor_id_fkey';
-- expect: references install_contractors(id)

-- D. install_photos.created_by now nullable
SELECT column_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'install_photos'
  AND column_name = 'created_by';
-- expect: is_nullable = 'YES'

-- =========================================================
-- ROLLBACK (uncomment if needed)
-- =========================================================
-- BEGIN;
-- ALTER TABLE public.install_contractor_assignments
--   DROP CONSTRAINT IF EXISTS install_contractor_assignments_contractor_id_fkey;
-- ALTER TABLE public.install_contractor_assignments
--   ADD CONSTRAINT install_contractor_assignments_contractor_id_fkey
--     FOREIGN KEY (contractor_id) REFERENCES public.profiles(id) ON DELETE RESTRICT;
-- ALTER TABLE public.install_progress_reports
--   DROP CONSTRAINT IF EXISTS install_progress_reports_contractor_id_fkey;
-- ALTER TABLE public.install_progress_reports
--   ADD CONSTRAINT install_progress_reports_contractor_id_fkey
--     FOREIGN KEY (contractor_id) REFERENCES public.profiles(id) ON DELETE RESTRICT;
-- ALTER TABLE public.install_contractors
--   ALTER COLUMN profile_id SET NOT NULL;
-- DROP INDEX IF EXISTS uq_install_contractors_profile_id_when_set;
-- ALTER TABLE public.install_contractors
--   ADD CONSTRAINT one_profile_one_contractor UNIQUE (profile_id);
-- ALTER TABLE public.install_photos
--   ALTER COLUMN created_by SET NOT NULL;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
