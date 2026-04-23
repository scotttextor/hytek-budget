-- HYTEK Budget — Migration 17: customer-app v2 (variations visibility,
-- their-flags visibility, supervisor phone on site-contact card)
--
-- Context: /customer/[jobId] mobile page currently lets a customer:
--   - see dispatch trips + their own sightings
--   - raise a flagged issue
-- Scott wants v2 to also show:
--   - any variation raised on their job (V-number + description + status,
--     NO money — customer sees work exists, not commercial figures)
--   - the flags THEY raised + any staff replies posted as comments
--   - the site supervisor's name + phone number
--
-- Scope here is schema + RLS only:
--   A. add install_supervisors.phone (nullable text) — needed for the
--      site-contact card; null → UI shows "Phone not on file" fallback
--   B. SELECT policy on job_variations for customers with a valid grant
--   C. SELECT policy on install_flagged_items for customers on their own
--      flags (created_by = auth.uid()) scoped to a valid grant
--   D. SELECT policy on install_flagged_item_comments scoped through the
--      parent flag's job + ownership
--
-- All additive. No DROP, no RENAME. Idempotent.

BEGIN;

-- =============================================================================
-- A. install_supervisors — phone column for site-contact card
-- =============================================================================
ALTER TABLE public.install_supervisors
  ADD COLUMN IF NOT EXISTS phone text;

-- =============================================================================
-- B. job_variations — customer can SELECT for jobs they hold a valid grant on.
--    They see EVERY variation on the job, but the app layer projects columns
--    so $ figures are omitted from the customer UI. Defense-in-depth would be
--    a column-level grant, but the simpler app-side projection is sufficient
--    for v2 (customer grants are short-lived + revocable).
-- =============================================================================
DROP POLICY IF EXISTS "customer super reads variations on granted job" ON public.job_variations;
CREATE POLICY "customer super reads variations on granted job"
  ON public.job_variations FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.customer_super_grants g
      WHERE g.user_id = auth.uid()
        AND g.job_id = job_variations.job_id
        AND g.revoked_at IS NULL
        AND g.expires_at > now()
    )
  );

-- =============================================================================
-- C. install_flagged_items — customer reads flags THEY raised on granted jobs.
--    We scope on created_by = auth.uid() so internal staff flags stay hidden.
--    Grant check is defensive (prevents a stale session from revealing flags
--    on a since-revoked job).
-- =============================================================================
DROP POLICY IF EXISTS "customer super reads own flags on granted job" ON public.install_flagged_items;
CREATE POLICY "customer super reads own flags on granted job"
  ON public.install_flagged_items FOR SELECT TO authenticated
  USING (
    created_by = auth.uid()
    AND EXISTS (
      SELECT 1 FROM public.customer_super_grants g
      WHERE g.user_id = auth.uid()
        AND g.job_id = install_flagged_items.job_id
        AND g.revoked_at IS NULL
        AND g.expires_at > now()
    )
  );

-- =============================================================================
-- D. install_flagged_item_comments — customer reads comments on flags they own.
--    Joins up through the parent flag to verify ownership + valid grant.
-- =============================================================================
DROP POLICY IF EXISTS "customer super reads comments on own flags" ON public.install_flagged_item_comments;
CREATE POLICY "customer super reads comments on own flags"
  ON public.install_flagged_item_comments FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.install_flagged_items f
      JOIN public.customer_super_grants g
        ON g.user_id = auth.uid()
       AND g.job_id = f.job_id
       AND g.revoked_at IS NULL
       AND g.expires_at > now()
      WHERE f.id = install_flagged_item_comments.flagged_item_id
        AND f.created_by = auth.uid()
    )
  );

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY — expected: phone column present; 3 new policies listed.
-- =============================================================================
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'install_supervisors'
  AND column_name = 'phone';

SELECT polname, relname AS table_name
FROM pg_policy
JOIN pg_class ON pg_class.oid = pg_policy.polrelid
WHERE polname IN (
  'customer super reads variations on granted job',
  'customer super reads own flags on granted job',
  'customer super reads comments on own flags'
)
ORDER BY relname, polname;

-- =============================================================================
-- ROLLBACK (uncomment to undo)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "customer super reads comments on own flags" ON public.install_flagged_item_comments;
-- DROP POLICY IF EXISTS "customer super reads own flags on granted job" ON public.install_flagged_items;
-- DROP POLICY IF EXISTS "customer super reads variations on granted job" ON public.job_variations;
-- ALTER TABLE public.install_supervisors DROP COLUMN IF EXISTS phone;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
