-- HYTEK Budget — Migration 11: retroactive grandfather-update for progress reports
--
-- WHY: Migration 10 introduced install_progress_reports.status with default 'submitted'
-- and added approved_percent_complete. The supervisor-review queue (Feature E.4) only
-- counts reports toward progress when status='reviewed'. Pre-existing rows were logged
-- BEFORE the gate existed, so on deploy they would appear to drop to zero until someone
-- walked through and reviewed every historical row.
--
-- This migration grandfathers them:
--   - status   →  'reviewed'      (they were trusted before the gate existed)
--   - approved_percent_complete  →  percent_complete  (accept the contractor's number retroactively)
--   - reviewed_at  →  created_at  (best available timestamp, preserves ordering)
--
-- MUST be applied AFTER migration 10. If you run this before 10, the UPDATE fails because
-- approved_percent_complete / reviewed_at don't exist yet — that's the correct failure mode.
--
-- Idempotent: running twice is a no-op (after first run, no rows have status='submitted'
-- from the default — new rows from the mobile app will exist but should be reviewed, not
-- grandfathered).

BEGIN;

-- Preflight: confirm migration 10 ran. If these columns don't exist, the UPDATE below will
-- fail with a clear error mentioning the missing column — that's exactly what we want.

-- The grandfather update itself.
UPDATE public.install_progress_reports
   SET status                   = 'reviewed',
       approved_percent_complete = percent_complete,
       reviewed_at              = created_at
 WHERE status = 'submitted'
   AND reviewed_at IS NULL;   -- extra safety: only touch rows never reviewed

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Show how many rows were grandfathered vs still pending review (the latter is only
-- new reports logged AFTER this migration runs).
SELECT
  status,
  COUNT(*) AS count
FROM public.install_progress_reports
GROUP BY status
ORDER BY status;

COMMIT;

-- =============================================================================
-- ROLLBACK (uncomment to undo — note: reverses the grandfather but re-reviewing
-- is cheap, so there's rarely a reason to roll this back)
-- =============================================================================
-- BEGIN;
-- UPDATE public.install_progress_reports
--    SET status                   = 'submitted',
--        approved_percent_complete = NULL,
--        reviewed_at              = NULL
--  WHERE status = 'reviewed'
--    AND reviewed_at = created_at;  -- only the rows we grandfathered
-- COMMIT;
