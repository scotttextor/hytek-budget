-- HYTEK Budget — Migration 16: add job_type to public.jobs
--
-- Root cause discovered while debugging switch-job search: the dropdown's
-- cross-DB search in hytek-install does
--   .select('id, name, client, install_status, job_type, quote_number')
-- which PostgREST rejects with
--   "column jobs.job_type does not exist"
-- so the whole query errors and the UI renders "No jobs matching …".
--
-- Wider fallout from the missing column:
--   - src/lib/types.ts declares job_type as a non-null 'single_building'|'multi_unit'
--   - src/app/dashboard/_client.tsx inserts { job_type: jobType } on every
--     New Job click — inserts were failing with the same PostgREST error.
--   - src/app/jobs/[id]/page.tsx:172  isStandalone = job.job_type === 'single_building'
--     always resolves to false (undefined === string), so standalone jobs
--     render the Units tab even though the spec says they should not.
--   - use-recent-jobs.ts + command-palette carry the same .select / display bug.
--
-- The migration that would have added this column was never written — the
-- TypeScript type, UI, and inserts were authored optimistically. This makes
-- the schema catch up with the code that already expects it.
--
-- All additive. No DROP, no RENAME. Idempotent. CHECK constraint enforces
-- the same two-value domain the TS union declares. DEFAULT 'multi_unit'
-- backfills every existing row with the most common value, matching the
-- New Job modal's default.

BEGIN;

ALTER TABLE public.jobs
  ADD COLUMN IF NOT EXISTS job_type text NOT NULL DEFAULT 'multi_unit';

-- Add the CHECK constraint separately so the migration is re-runnable against
-- an already-partly-applied DB (ADD COLUMN IF NOT EXISTS + ADD CONSTRAINT IF
-- NOT EXISTS). Named so rollback is unambiguous.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'jobs_job_type_check'
  ) THEN
    ALTER TABLE public.jobs
      ADD CONSTRAINT jobs_job_type_check
      CHECK (job_type IN ('single_building', 'multi_unit'));
  END IF;
END $$;

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY — expect job_type to appear with NOT NULL + default 'multi_unit'
--          and the CHECK constraint to be listed.
-- =============================================================================
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'jobs'
  AND column_name = 'job_type';

SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conname = 'jobs_job_type_check';

-- Spot-check: every existing row should be 'multi_unit' after backfill.
SELECT job_type, count(*) FROM public.jobs GROUP BY job_type ORDER BY job_type;

-- =============================================================================
-- ROLLBACK (uncomment to undo — only safe if no app code depends on the column)
-- =============================================================================
-- BEGIN;
-- ALTER TABLE public.jobs DROP CONSTRAINT IF EXISTS jobs_job_type_check;
-- ALTER TABLE public.jobs DROP COLUMN IF EXISTS job_type;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
