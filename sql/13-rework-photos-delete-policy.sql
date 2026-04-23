-- HYTEK Budget — Migration 13: DELETE + UPDATE policies on rework_photos
--
-- Mirror of migration 12 for the rework side. When we apply the same "expand
-- to edit + delete attachments" treatment to the Rework tab, the ✕ Remove
-- button will silently fail without this — rework_photos was created with
-- SELECT + INSERT only (from add-variations-rework.sql), same as
-- variation_photos was.
--
-- No schema changes — just RLS.
--
-- job_rework itself already has "Auth manage rework" FOR ALL, so deleting
-- the parent rework row works and cascades to rework_photos (via the table's
-- ON DELETE CASCADE). But to delete an individual rework_photo without
-- deleting the parent, we need these two policies.

BEGIN;

DROP POLICY IF EXISTS "Auth delete rework photos" ON public.rework_photos;
CREATE POLICY "Auth delete rework photos"
  ON public.rework_photos
  FOR DELETE
  TO authenticated
  USING (true);

-- Symmetry with variation_photos migration — if a future Replace flow swaps
-- a row in-place instead of delete+insert, it'll need this.
DROP POLICY IF EXISTS "Auth update rework photos" ON public.rework_photos;
CREATE POLICY "Auth update rework photos"
  ON public.rework_photos
  FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY
-- =============================================================================
-- Expect 4 rows (select + insert + delete + update):
SELECT policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public' AND tablename = 'rework_photos'
ORDER BY cmd;

-- =============================================================================
-- ROLLBACK (uncomment to undo)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "Auth delete rework photos" ON public.rework_photos;
-- DROP POLICY IF EXISTS "Auth update rework photos" ON public.rework_photos;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
