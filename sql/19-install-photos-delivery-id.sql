-- HYTEK Budget — Migration 19: install_photos.delivery_id for customer-
-- supplied delivery sighting photos.
--
-- Context: the customer mobile page (/customer/[jobId]) lets a customer
-- confirm "I sighted this delivery" for each dispatch_trip. v2 extends
-- that to optionally attach a photo — "I saw the truck; here's proof".
--
-- Design: one unified photo table (install_photos) keeps the Photos tab
-- coherent — every photo on a job reaches it through the same feed. This
-- migration adds a nullable FK so a customer's sighting photo links to
-- the dispatch_trips row they confirmed against. Existing photo linkage
-- columns (claim_id, flagged_item_id, budget_item_id, report_id, variation
-- _id via variation_photos, rework_id via rework_photos) are unaffected.
--
-- All additive. No DROP, no RENAME. Idempotent.

BEGIN;

ALTER TABLE public.install_photos
  ADD COLUMN IF NOT EXISTS delivery_id uuid
    REFERENCES public.dispatch_trips(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_install_photos_delivery
  ON public.install_photos (delivery_id)
  WHERE delivery_id IS NOT NULL;

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY — expect the new column to appear.
-- =============================================================================
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'install_photos'
  AND column_name = 'delivery_id';

-- =============================================================================
-- ROLLBACK (uncomment to undo)
-- =============================================================================
-- BEGIN;
-- DROP INDEX IF EXISTS public.idx_install_photos_delivery;
-- ALTER TABLE public.install_photos DROP COLUMN IF EXISTS delivery_id;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
