-- HYTEK Budget — Migration 15: enrich install_form12_inspections
--
-- Booking a Form 12 today only captures inspector name + datetime. Scott:
-- "you need to be able to pick a company to use and all the stuff associated
-- with a form 12". Adding the fields a real Form 12 booking needs:
--
-- - company_id  → which company is providing the inspector (engineer / certifier)
-- - service_id  → optional, the specific service the company offers
-- - estimated_cost → expected fee, used for budget tracking + variance
-- - inspector_phone → on-the-day site contact
-- - pre_inspection_notes → access info, scope notes, anything the inspector
--                          needs to know before showing up
--
-- All additive. No DROP, no RENAME. Idempotent.

BEGIN;

ALTER TABLE public.install_form12_inspections
  ADD COLUMN IF NOT EXISTS company_id            uuid REFERENCES public.install_companies(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS service_id            uuid REFERENCES public.install_company_services(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS estimated_cost        numeric(12,2),
  ADD COLUMN IF NOT EXISTS inspector_phone       text,
  ADD COLUMN IF NOT EXISTS pre_inspection_notes  text;

CREATE INDEX IF NOT EXISTS idx_form12_company
  ON public.install_form12_inspections (company_id)
  WHERE company_id IS NOT NULL;

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY — expect the 5 new columns to appear
-- =============================================================================
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'install_form12_inspections'
  AND column_name IN ('company_id','service_id','estimated_cost','inspector_phone','pre_inspection_notes')
ORDER BY column_name;

-- =============================================================================
-- ROLLBACK (uncomment to undo)
-- =============================================================================
-- BEGIN;
-- ALTER TABLE public.install_form12_inspections
--   DROP COLUMN IF EXISTS pre_inspection_notes,
--   DROP COLUMN IF EXISTS inspector_phone,
--   DROP COLUMN IF EXISTS estimated_cost,
--   DROP COLUMN IF EXISTS service_id,
--   DROP COLUMN IF EXISTS company_id;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
