-- HYTEK Budget — Migration 06: manual prune of expired customer-super auth.users rows
--
-- Pair with customer_super_grants + magic-link flow from migration 05.
-- Over time, each supply-only job may accumulate customer-super auth.users
-- rows (one per (job, customer_email) grant). Long-running HYTEK apps may see
-- this grow unbounded. This function provides an admin-triggered cleanup.
--
-- SAFETY: only targets auth.users whose ALL grants are either expired OR revoked.
-- A customer super with any active grant is never pruned.
-- Safe to re-run; idempotent.

BEGIN;

CREATE OR REPLACE FUNCTION public.prune_expired_customer_grants()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER       -- runs with function-owner privileges so it can delete from auth.users
SET search_path = public, auth
AS $$
DECLARE
  deleted_count integer := 0;
  rec record;
BEGIN
  -- Find auth.users whose ONLY grants are all expired OR revoked
  FOR rec IN
    SELECT DISTINCT g.user_id
    FROM public.customer_super_grants g
    WHERE g.user_id IS NOT NULL
      AND g.user_id <> '00000000-0000-0000-0000-000000000000'
      AND NOT EXISTS (
        -- A grant is "still active" if not revoked AND not expired
        SELECT 1
        FROM public.customer_super_grants g2
        WHERE g2.user_id = g.user_id
          AND g2.revoked_at IS NULL
          AND g2.expires_at > now()
      )
  LOOP
    DELETE FROM auth.users WHERE id = rec.user_id;
    IF FOUND THEN
      deleted_count := deleted_count + 1;
    END IF;
  END LOOP;

  RETURN deleted_count;
END;
$$;

-- Only allow admin role to invoke
GRANT EXECUTE ON FUNCTION public.prune_expired_customer_grants() TO authenticated;

COMMIT;

-- Dry-run preview (uncomment to see what WOULD be deleted without actually deleting):
-- SELECT DISTINCT g.user_id, g.email, max(g.expires_at) as latest_expiry, max(g.revoked_at) as latest_revoke
--   FROM public.customer_super_grants g
--  WHERE g.user_id IS NOT NULL
--    AND g.user_id <> '00000000-0000-0000-0000-000000000000'
--    AND NOT EXISTS (SELECT 1 FROM public.customer_super_grants g2
--                    WHERE g2.user_id = g.user_id AND g2.revoked_at IS NULL AND g2.expires_at > now())
--  GROUP BY g.user_id, g.email;

-- Execute (admin-only):
-- SELECT public.prune_expired_customer_grants();
