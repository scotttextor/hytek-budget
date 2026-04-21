-- HYTEK Budget — Migration 09: Xero bill push readiness
--
-- Feature D: when install manager taps "Push to Xero" on a claim (or batch),
-- hytek-invoicing creates a DRAFT ACCPAY Bill in Xero. This migration adds
-- the columns the push flow needs.
--
-- Design locked by Scott 2026-04-21 after expert panel synthesis:
--   - Explicit manager push (no auto-fire on claim insert)
--   - One Xero draft per claim (accounts merges in Xero if needed)
--   - Claims lock against edits once pushed (correcting claims for fixes)
--   - Supplier → Xero contact mapped once per install_companies row
--   - GST treatment chosen EXPLICITLY at claim entry (no "what did they mean?")
--
-- Apply AFTER sql/01–08. Idempotent — safe to re-run.

BEGIN;

-- =============================================================================
-- 1. install_claims: Xero bill tracking + explicit GST treatment
-- =============================================================================

ALTER TABLE public.install_claims
  ADD COLUMN IF NOT EXISTS xero_bill_id    text,
  ADD COLUMN IF NOT EXISTS xero_pushed_at  timestamptz,
  ADD COLUMN IF NOT EXISTS xero_push_error text;

-- GST treatment — chosen at entry so the Xero push is deterministic.
-- 'inclusive' = amount includes GST (typical paper invoice)
-- 'exclusive' = amount is pre-GST (typical hourly rate sheet)
-- 'none'      = supplier not GST-registered (sole trader under threshold)
ALTER TABLE public.install_claims
  ADD COLUMN IF NOT EXISTS gst_treatment text NOT NULL DEFAULT 'inclusive';

-- Defer the CHECK until after default-backfill of pre-existing rows
ALTER TABLE public.install_claims
  DROP CONSTRAINT IF EXISTS install_claims_gst_treatment_check;
ALTER TABLE public.install_claims
  ADD CONSTRAINT install_claims_gst_treatment_check
  CHECK (gst_treatment IN ('inclusive', 'exclusive', 'none'));

-- Partial index: "pending to Xero" query hot path
CREATE INDEX IF NOT EXISTS idx_install_claims_pending_xero
  ON public.install_claims (company_id, claim_date)
  WHERE xero_bill_id IS NULL;

-- =============================================================================
-- 2. install_companies: one-time Xero contact mapping
-- =============================================================================

ALTER TABLE public.install_companies
  ADD COLUMN IF NOT EXISTS xero_contact_id   text,
  ADD COLUMN IF NOT EXISTS xero_contact_name text;

-- Index: quick "find unmapped suppliers" query for admin UI
CREATE INDEX IF NOT EXISTS idx_install_companies_unmapped
  ON public.install_companies (active, name)
  WHERE xero_contact_id IS NULL AND active = true;

-- =============================================================================
-- 3. Immutability trigger — claim content locks when it's been pushed to Xero
-- =============================================================================
-- Scott's rule: once a claim creates a Xero DRAFT bill, its financial content
-- (amount, date, GST, supplier, etc.) cannot change silently — the two systems
-- would drift. If a correction is needed, void the Xero draft and log a
-- NEW correcting claim. Xero push audit + local record stay in sync.
--
-- Fields intentionally still writable after push (safe edits):
--   - xero_bill_id, xero_pushed_at, xero_push_error  (the Xero sync fields)
--   - over_budget                                    (derived flag, recomputed)
--   - captured_at / captured_lat / captured_lng / captured_accuracy_m (audit)
--   - created_by (backfill corrections), payment_status (tracking state)

CREATE OR REPLACE FUNCTION public.trg_block_edit_after_xero_push() RETURNS trigger AS $$
BEGIN
  IF OLD.xero_pushed_at IS NOT NULL THEN
    IF NEW.claim_amount        IS DISTINCT FROM OLD.claim_amount
    OR NEW.claim_date          IS DISTINCT FROM OLD.claim_date
    OR NEW.claim_kind          IS DISTINCT FROM OLD.claim_kind
    OR NEW.hours               IS DISTINCT FROM OLD.hours
    OR NEW.qty                 IS DISTINCT FROM OLD.qty
    OR NEW.rate_used           IS DISTINCT FROM OLD.rate_used
    OR NEW.notes               IS DISTINCT FROM OLD.notes
    OR NEW.company_id          IS DISTINCT FROM OLD.company_id
    OR NEW.company_service_id  IS DISTINCT FROM OLD.company_service_id
    OR NEW.unit_no             IS DISTINCT FROM OLD.unit_no
    OR NEW.gst_treatment       IS DISTINCT FROM OLD.gst_treatment
    OR NEW.po_reference        IS DISTINCT FROM OLD.po_reference
    OR NEW.supplier_invoice_no IS DISTINCT FROM OLD.supplier_invoice_no
    OR NEW.budget_item_id      IS DISTINCT FROM OLD.budget_item_id
    OR NEW.job_id              IS DISTINCT FROM OLD.job_id
    OR NEW.sub_item_id         IS DISTINCT FROM OLD.sub_item_id
    OR NEW.percent_complete    IS DISTINCT FROM OLD.percent_complete
    THEN
      RAISE EXCEPTION
        'install_claims row % is locked because it was pushed to Xero at %. Void the Xero bill and log a correcting claim instead.',
        OLD.id, OLD.xero_pushed_at;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_install_claims_edit_lock ON public.install_claims;
CREATE TRIGGER trg_install_claims_edit_lock
  BEFORE UPDATE ON public.install_claims
  FOR EACH ROW EXECUTE FUNCTION public.trg_block_edit_after_xero_push();

NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY
-- =============================================================================

-- A. install_claims new columns present
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'install_claims'
  AND column_name IN ('xero_bill_id', 'xero_pushed_at', 'xero_push_error', 'gst_treatment')
ORDER BY column_name;
-- Expect 4 rows.

-- B. gst_treatment CHECK registered
SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.install_claims'::regclass
  AND conname = 'install_claims_gst_treatment_check';
-- Expect CHECK (gst_treatment = ANY (ARRAY['inclusive','exclusive','none']))

-- C. install_companies Xero columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'install_companies'
  AND column_name IN ('xero_contact_id', 'xero_contact_name')
ORDER BY column_name;
-- Expect 2 rows.

-- D. Indexes created
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'idx_install_claims_pending_xero',
    'idx_install_companies_unmapped'
  )
ORDER BY indexname;
-- Expect 2 rows.

-- E. Immutability trigger registered
SELECT tgname, tgenabled
FROM pg_trigger
WHERE tgrelid = 'public.install_claims'::regclass
  AND tgname = 'trg_install_claims_edit_lock';
-- Expect 1 row, enabled='O'

-- F. Smoke test for the lock (uncomment + substitute a real pushed claim id):
-- BEGIN;
--   -- Grab a pushed claim
--   SELECT id, xero_pushed_at FROM public.install_claims
--     WHERE xero_pushed_at IS NOT NULL LIMIT 1;
--   -- Attempt an edit — should RAISE EXCEPTION
--   UPDATE public.install_claims
--     SET claim_amount = claim_amount + 1
--     WHERE id = '<pushed-claim-uuid>';
-- ROLLBACK;

-- =============================================================================
-- ROLLBACK (uncomment if needed)
-- =============================================================================
-- BEGIN;
-- DROP TRIGGER IF EXISTS trg_install_claims_edit_lock ON public.install_claims;
-- DROP FUNCTION IF EXISTS public.trg_block_edit_after_xero_push();
-- DROP INDEX IF EXISTS public.idx_install_claims_pending_xero;
-- DROP INDEX IF EXISTS public.idx_install_companies_unmapped;
-- ALTER TABLE public.install_companies
--   DROP COLUMN IF EXISTS xero_contact_name,
--   DROP COLUMN IF EXISTS xero_contact_id;
-- ALTER TABLE public.install_claims
--   DROP CONSTRAINT IF EXISTS install_claims_gst_treatment_check,
--   DROP COLUMN IF EXISTS gst_treatment,
--   DROP COLUMN IF EXISTS xero_push_error,
--   DROP COLUMN IF EXISTS xero_pushed_at,
--   DROP COLUMN IF EXISTS xero_bill_id;
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
