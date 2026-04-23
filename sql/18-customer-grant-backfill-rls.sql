-- HYTEK Budget — Migration 18: customer-super grant user_id backfill RLS
--
-- Root cause for T9: when a customer first clicks their magic link,
-- /customer/[jobId]/page.tsx runs:
--
--   .from('customer_super_grants')
--   .update({ user_id: <auth.uid()>, last_seen_at: now() })
--   .eq('job_id', ...).eq('email', ...).is('revoked_at', null)
--
-- customer_super_grants has RLS enabled but only a "staff manages" policy
-- for UPDATE (admin + supervisor). An authenticated customer has no policy
-- that allows them to touch their own row, so PostgREST filters the UPDATE
-- down to 0 affected rows — silently, no error.
--
-- The grant row therefore stays with user_id = '00000000-...' (the placeholder
-- the admin panel inserts at issuance). The subsequent SELECT in step 3 of
-- page.tsx uses `.eq('user_id', auth.uid())` and finds no match — the page
-- falls into the `no-grant` state and renders "This access has expired or
-- been revoked."
--
-- Fix: add a narrow UPDATE policy that lets an authenticated user whose JWT
-- email matches the grant row update their own grant, provided:
--   - the row is not revoked
--   - the row has not expired
--   - the resulting user_id MATCHES auth.uid() (can't set to an arbitrary id)
--   - the resulting email still matches the JWT email (can't steal another row)
--
-- This also covers the ongoing `last_seen_at` touches once the backfill has
-- happened and user_id = auth.uid().

BEGIN;

DROP POLICY IF EXISTS "customer super updates own grant" ON public.customer_super_grants;
CREATE POLICY "customer super updates own grant"
  ON public.customer_super_grants FOR UPDATE TO authenticated
  USING (
    revoked_at IS NULL
    AND expires_at > now()
    AND email = (auth.jwt() ->> 'email')
    AND (
      user_id = auth.uid()
      OR user_id = '00000000-0000-0000-0000-000000000000'::uuid
    )
  )
  WITH CHECK (
    revoked_at IS NULL
    AND email = (auth.jwt() ->> 'email')
    AND user_id = auth.uid()
  );

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY — expected: the new policy listed against customer_super_grants
-- =============================================================================
SELECT polname, relname AS table_name, cmd
FROM pg_policy
JOIN pg_class ON pg_class.oid = pg_policy.polrelid
WHERE polname = 'customer super updates own grant';

-- =============================================================================
-- ROLLBACK (uncomment to undo)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "customer super updates own grant" ON public.customer_super_grants;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
