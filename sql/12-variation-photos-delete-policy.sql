-- HYTEK Budget — Migration 12: DELETE policy on variation_photos
--
-- Wave 2 of variation-view unification (hytek-install commits 34da53e + 0505fc6)
-- ships a ✕ Remove button and ⟳ Replace affordance on variation_photos pills.
-- The agent that built it correctly flagged that the table's existing RLS only
-- has SELECT + INSERT policies (from add-variations-rework.sql) — no DELETE.
-- Without this migration, admin + supervisor deletes silently succeed with
-- 0 rows affected because RLS blocks the DELETE. The UI optimistically removes
-- the pill, but the row survives — a classic "works in dev, broken in prod"
-- ghost.
--
-- Fix: authenticated users can DELETE variation_photos. Gated by app layer
-- (admin + supervisor only have this UI affordance, contractors never touch it).
-- If tighter RBAC is needed later, add a role check via profiles join — for
-- now the simple `to authenticated` mirrors the existing SELECT + INSERT
-- policies for consistency.

BEGIN;

DROP POLICY IF EXISTS "Auth delete var photos" ON public.variation_photos;
CREATE POLICY "Auth delete var photos"
  ON public.variation_photos
  FOR DELETE
  TO authenticated
  USING (true);

-- Also cover UPDATE for symmetry — if a future Replace flow swaps a row in-
-- place instead of delete+insert, it'll need this.
DROP POLICY IF EXISTS "Auth update var photos" ON public.variation_photos;
CREATE POLICY "Auth update var photos"
  ON public.variation_photos
  FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY
-- =============================================================================
-- Run after apply — expect 4 rows (select + insert + delete + update):
SELECT policyname, cmd, roles, qual
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'variation_photos'
ORDER BY cmd;

-- =============================================================================
-- ROLLBACK (uncomment to undo)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "Auth delete var photos" ON public.variation_photos;
-- DROP POLICY IF EXISTS "Auth update var photos" ON public.variation_photos;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
