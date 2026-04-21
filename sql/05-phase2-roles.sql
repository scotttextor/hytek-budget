-- HYTEK Budget — Phase 2 schema: contractor + customer-super role foundations
-- Design source: hytek-install/docs/superpowers/specs/2026-04-21-contractor-customer-roles-design.md
-- Panel synthesis: Panel #3, 2026-04-21 (UX / Architect / Mathematician / Strategist)
--
-- Apply AFTER sql/01, 02, 03, 04. Safe to re-run (IF NOT EXISTS + DROP/re-add on constraints).
--
-- What this does (additive only — zero destructive ops):
--   1. Extends profiles.role CHECK to include 'contractor'
--   2. Adds jobs.closed_at (set-once timestamptz) + trigger
--   3. Creates install_contractor_assignments (per-item contractor scope)
--   4. Creates customer_super_grants (ephemeral per-job access, not in profiles)
--   5. Creates install_progress_reports (contractor-submitted progress against assigned items)
--   6. Creates claim_report_links (N:M junction: claims ↔ progress reports)
--   7. Adds install_photos.report_id FK column (nullable, additive)
--   8. Creates delivery_sightings (append-only customer-super sighting log)
--   9. Creates admin_alerts (rate-limit breach + misuse signals)
--
-- DB PROBE RESULTS (2026-04-21):
--   - jobs.updated_at: DOES NOT EXIST (42703) → backfill uses created_at
--   - profiles.role existing values: admin, supervisor, detailer
--     All are in the new CHECK set — migration is safe to apply
--   - jobs with install_status='complete': 0 rows → backfill is a no-op

BEGIN;

-- =============================================================================
-- 1. Extend profiles.role CHECK to include 'contractor'
-- =============================================================================
-- Design doc §3.1: contractors are recurring external parties, stored in profiles
-- (not ephemeral like customer supers).
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles ADD CONSTRAINT profiles_role_check
  CHECK (role IN ('admin', 'supervisor', 'detailer', 'driver', 'installer', 'contractor'));

-- =============================================================================
-- 2. jobs.closed_at — set-once timestamp
-- =============================================================================
-- Design doc §3.4: expires_at = jobs.closed_at + 30 days. closed_at is set ONCE
-- when install_status transitions to 'complete'. Reopening a job MUST NOT null it —
-- the first-close grant period is the canonical expiry.
--
-- NOTE: jobs.updated_at does NOT exist (probed 2026-04-21 — 42703 error).
-- Backfill uses created_at as best-effort stamp for any pre-existing complete rows.
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS closed_at timestamptz;

-- Backfill: any currently-complete jobs get closed_at from created_at (best-effort)
-- (Probe shows 0 complete rows as of 2026-04-21 — this is a no-op but safe to keep)
UPDATE public.jobs
   SET closed_at = created_at
 WHERE install_status = 'complete' AND closed_at IS NULL;

-- Trigger function: set closed_at on transition to 'complete'; never null it
CREATE OR REPLACE FUNCTION public.trg_set_job_closed_at() RETURNS trigger AS $$
BEGIN
  -- On transition to complete: set closed_at if not already set
  IF NEW.install_status = 'complete' AND NEW.closed_at IS NULL THEN
    NEW.closed_at := now();
  END IF;
  -- Set-once invariant: never allow clearing closed_at once set
  IF OLD.closed_at IS NOT NULL AND NEW.closed_at IS NULL THEN
    NEW.closed_at := OLD.closed_at;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_jobs_closed_at ON public.jobs;
CREATE TRIGGER trg_jobs_closed_at
  BEFORE UPDATE ON public.jobs
  FOR EACH ROW EXECUTE FUNCTION public.trg_set_job_closed_at();

-- =============================================================================
-- 3. install_contractor_assignments — per-item contractor scope
-- =============================================================================
-- Design doc §3.3: granularity is per-item (precise RLS joins), with UI bulk helpers.
-- UNIQUE on (contractor_id, budget_item_id) — one active assignment per contractor per item.
-- Soft-delete via revoked_at (never hard-delete — audit trail required).
CREATE TABLE IF NOT EXISTS public.install_contractor_assignments (
  id              uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
  contractor_id   uuid         NOT NULL REFERENCES public.profiles(id)             ON DELETE RESTRICT,
  job_id          uuid         NOT NULL REFERENCES public.jobs(id)                 ON DELETE RESTRICT,
  budget_item_id  uuid         NOT NULL REFERENCES public.install_budget_items(id) ON DELETE RESTRICT,
  assigned_by     uuid         REFERENCES public.profiles(id)                      ON DELETE SET NULL,
  assigned_at     timestamptz  NOT NULL DEFAULT now(),
  revoked_at      timestamptz,
  revoked_by      uuid         REFERENCES public.profiles(id)                      ON DELETE SET NULL,
  notes           text,
  CONSTRAINT contractor_item_unique UNIQUE (contractor_id, budget_item_id),
  CONSTRAINT revoke_after_assign    CHECK  (revoked_at IS NULL OR revoked_at > assigned_at)
);

-- Partial index: active assignments per contractor (hot path for RLS checks)
CREATE INDEX IF NOT EXISTS idx_contractor_assignments_contractor
  ON public.install_contractor_assignments (contractor_id, revoked_at)
  WHERE revoked_at IS NULL;

-- Partial index: active assignments per job (hot path for IM dashboard)
CREATE INDEX IF NOT EXISTS idx_contractor_assignments_job
  ON public.install_contractor_assignments (job_id, revoked_at)
  WHERE revoked_at IS NULL;

ALTER TABLE public.install_contractor_assignments ENABLE ROW LEVEL SECURITY;

-- Staff (admin/supervisor) can read and write all assignments
DROP POLICY IF EXISTS "staff manages assignments" ON public.install_contractor_assignments;
CREATE POLICY "staff manages assignments"
  ON public.install_contractor_assignments FOR ALL TO authenticated
  USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor'))
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor'))
  );

-- Contractors can read their own non-revoked assignments (so they know their scope)
DROP POLICY IF EXISTS "contractor reads own assignments" ON public.install_contractor_assignments;
CREATE POLICY "contractor reads own assignments"
  ON public.install_contractor_assignments FOR SELECT TO authenticated
  USING (
    contractor_id = auth.uid()
    AND revoked_at IS NULL
  );

-- =============================================================================
-- 4. customer_super_grants — ephemeral per-job external access
-- =============================================================================
-- Design doc §3.1: customer supers are NOT in profiles (avoids identity table bloat
-- from thousands of single-use records). One row per (job, customer email).
-- expires_at = jobs.closed_at + 30 days, set at the close-event time.
-- Design doc §3.4: link is valid for the full pre-close lifetime + 30 days post-close.
CREATE TABLE IF NOT EXISTS public.customer_super_grants (
  id              uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
  -- mirrors auth.users.id; no cross-schema FK (Supabase auth schema boundary)
  user_id         uuid         NOT NULL,
  job_id          uuid         NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
  email           text         NOT NULL,
  issued_by       uuid         REFERENCES public.profiles(id) ON DELETE SET NULL,
  issued_at       timestamptz  NOT NULL DEFAULT now(),
  expires_at      timestamptz  NOT NULL,
  last_seen_at    timestamptz,
  revoked_at      timestamptz,
  revoked_by      uuid         REFERENCES public.profiles(id) ON DELETE SET NULL,
  CONSTRAINT grant_expires_after_issue CHECK (expires_at > issued_at),
  CONSTRAINT one_grant_per_job_email   UNIQUE (job_id, email)
);

-- Partial index: active grants per user (hot path for auth middleware + RLS)
CREATE INDEX IF NOT EXISTS idx_customer_super_grants_user
  ON public.customer_super_grants (user_id)
  WHERE revoked_at IS NULL;

-- Partial index: active grants per job (hot path for IM dashboard visibility check)
CREATE INDEX IF NOT EXISTS idx_customer_super_grants_job
  ON public.customer_super_grants (job_id)
  WHERE revoked_at IS NULL;

ALTER TABLE public.customer_super_grants ENABLE ROW LEVEL SECURITY;

-- Staff (admin/supervisor) manage all grants
DROP POLICY IF EXISTS "staff manages grants" ON public.customer_super_grants;
CREATE POLICY "staff manages grants"
  ON public.customer_super_grants FOR ALL TO authenticated
  USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor'))
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor'))
  );

-- Customer super reads their own non-revoked, non-expired grant
DROP POLICY IF EXISTS "customer super reads own grant" ON public.customer_super_grants;
CREATE POLICY "customer super reads own grant"
  ON public.customer_super_grants FOR SELECT TO authenticated
  USING (
    user_id = auth.uid()
    AND revoked_at IS NULL
    AND expires_at > now()
  );

-- =============================================================================
-- 5. install_progress_reports — contractor progress submissions
-- =============================================================================
-- Design doc §3.6(e): contractors submit progress against assigned items.
-- RLS: staff reads all; contractor reads/writes only their own where assignment exists.
-- Mathematician §8: two contractors on the same item see ONLY their own reports.
-- Status machine: submitted → reviewed | dismissed (HYTEK staff reviews).
CREATE TABLE IF NOT EXISTS public.install_progress_reports (
  id                  uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id              uuid          NOT NULL REFERENCES public.jobs(id)                 ON DELETE RESTRICT,
  budget_item_id      uuid          NOT NULL REFERENCES public.install_budget_items(id) ON DELETE RESTRICT,
  unit_no             text,
  contractor_id       uuid          NOT NULL REFERENCES public.profiles(id)            ON DELETE RESTRICT,
  notes               text,
  percent_complete    numeric(5,2),
  status              text          NOT NULL DEFAULT 'submitted'
                                      CHECK (status IN ('submitted','reviewed','dismissed')),
  reviewed_by         uuid          REFERENCES public.profiles(id) ON DELETE SET NULL,
  reviewed_at         timestamptz,
  captured_at         timestamptz   NOT NULL DEFAULT now(),
  captured_lat        numeric(9,6),
  captured_lng        numeric(9,6),
  captured_accuracy_m integer,
  created_at          timestamptz   NOT NULL DEFAULT now()
);

-- Index: job + status + time (hot path for IM dashboard review queue)
CREATE INDEX IF NOT EXISTS idx_progress_reports_job
  ON public.install_progress_reports (job_id, status, captured_at DESC);

-- Index: contractor + time (hot path for contractor's own history)
CREATE INDEX IF NOT EXISTS idx_progress_reports_contractor
  ON public.install_progress_reports (contractor_id, captured_at DESC);

ALTER TABLE public.install_progress_reports ENABLE ROW LEVEL SECURITY;

-- Staff reads all progress reports
DROP POLICY IF EXISTS "staff reads progress reports" ON public.install_progress_reports;
CREATE POLICY "staff reads progress reports"
  ON public.install_progress_reports FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE id = auth.uid()
        AND role IN ('admin','supervisor','installer','detailer','driver')
    )
  );

-- Staff (admin/supervisor only) can update/delete (e.g. review a report)
DROP POLICY IF EXISTS "staff writes progress reports" ON public.install_progress_reports;
CREATE POLICY "staff writes progress reports"
  ON public.install_progress_reports FOR ALL TO authenticated
  USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor'))
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor'))
  );

-- Contractor reads ONLY their own reports (cross-contractor isolation per Mathematician §8)
DROP POLICY IF EXISTS "contractor reads own reports" ON public.install_progress_reports;
CREATE POLICY "contractor reads own reports"
  ON public.install_progress_reports FOR SELECT TO authenticated
  USING (
    contractor_id = auth.uid()
    AND EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'contractor')
  );

-- Contractor inserts against assigned items only (not against unassigned or revoked)
DROP POLICY IF EXISTS "contractor writes own reports" ON public.install_progress_reports;
CREATE POLICY "contractor writes own reports"
  ON public.install_progress_reports FOR INSERT TO authenticated
  WITH CHECK (
    contractor_id = auth.uid()
    AND EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'contractor')
    AND EXISTS (
      SELECT 1 FROM public.install_contractor_assignments a
      WHERE a.contractor_id = auth.uid()
        AND a.job_id         = install_progress_reports.job_id
        AND a.budget_item_id = install_progress_reports.budget_item_id
        AND a.revoked_at     IS NULL
    )
  );

-- =============================================================================
-- 6. claim_report_links — N:M junction (claims ↔ progress reports)
-- =============================================================================
-- Design doc §3.6(f) + Mathematician §3:
-- One claim can batch multiple reports; one report can feed multiple claims
-- (e.g. same progress report referenced across two billing weeks).
-- HYTEK staff links these manually when logging a claim against contractor reports.
CREATE TABLE IF NOT EXISTS public.claim_report_links (
  claim_id    uuid  NOT NULL REFERENCES public.install_claims(id)            ON DELETE CASCADE,
  report_id   uuid  NOT NULL REFERENCES public.install_progress_reports(id)  ON DELETE RESTRICT,
  linked_by   uuid  REFERENCES public.profiles(id)                           ON DELETE SET NULL,
  linked_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (claim_id, report_id)
);

-- Index: report → claims lookup (reverse direction, not covered by PK)
CREATE INDEX IF NOT EXISTS idx_claim_report_links_report
  ON public.claim_report_links (report_id);

ALTER TABLE public.claim_report_links ENABLE ROW LEVEL SECURITY;

-- Staff (admin/supervisor) manages all links
DROP POLICY IF EXISTS "staff manages claim report links" ON public.claim_report_links;
CREATE POLICY "staff manages claim report links"
  ON public.claim_report_links FOR ALL TO authenticated
  USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor'))
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin','supervisor'))
  );

-- =============================================================================
-- 7. install_photos.report_id — additive FK column
-- =============================================================================
-- Design doc §3.6(g): photos taken during a progress report get this FK.
-- Existing photos remain with report_id = NULL (no data touched).
ALTER TABLE public.install_photos
  ADD COLUMN IF NOT EXISTS report_id uuid
    REFERENCES public.install_progress_reports(id) ON DELETE SET NULL;

-- Sparse index: only indexes photos with a report link (majority will be NULL)
CREATE INDEX IF NOT EXISTS idx_install_photos_report
  ON public.install_photos (report_id)
  WHERE report_id IS NOT NULL;

-- =============================================================================
-- 8. delivery_sightings — append-only customer-super sighting log
-- =============================================================================
-- Design doc §3.6(h) + §3.5:
-- Audit rows log grant_id + ip_address + user_agent (not a profile identity — customer
-- may forward the link). Legal audit: "sighted by customer-super link for Job N from
-- IP x.y.z.w" — the truthful claim, not a named individual.
--
-- TODO: delivery_id has NO FK constraint intentionally. The dispatch delivery table name
-- is not confirmed. Once confirmed (check hytek-detailing/app scripts for delivery table),
-- add: ALTER TABLE public.delivery_sightings
--        ADD CONSTRAINT delivery_sightings_delivery_id_fkey
--        FOREIGN KEY (delivery_id) REFERENCES public.<dispatch_delivery_table>(id);
CREATE TABLE IF NOT EXISTS public.delivery_sightings (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  -- FK to dispatch's delivery table — intentionally unconstrained (table name TBD)
  -- See TODO above before adding FK at T10.
  delivery_id     uuid        NOT NULL,
  grant_id        uuid        NOT NULL REFERENCES public.customer_super_grants(id) ON DELETE CASCADE,
  action          text        NOT NULL CHECK (action IN ('sighted', 'retracted')),
  reason          text,
  ip_address      inet,
  user_agent      text,
  occurred_at     timestamptz NOT NULL DEFAULT now()
);

-- Index: delivery_id + time (query all sightings for a delivery)
CREATE INDEX IF NOT EXISTS idx_delivery_sightings_delivery
  ON public.delivery_sightings (delivery_id, occurred_at DESC);

-- Index: grant_id + time (query sightings by a specific customer super)
CREATE INDEX IF NOT EXISTS idx_delivery_sightings_grant
  ON public.delivery_sightings (grant_id, occurred_at DESC);

ALTER TABLE public.delivery_sightings ENABLE ROW LEVEL SECURITY;

-- Staff reads all sightings (install manager, driver, etc. can see confirmations)
DROP POLICY IF EXISTS "staff reads sightings" ON public.delivery_sightings;
CREATE POLICY "staff reads sightings"
  ON public.delivery_sightings FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles
      WHERE id = auth.uid()
        AND role IN ('admin','supervisor','installer','detailer','driver')
    )
  );

-- Customer super inserts sightings against their own valid, non-revoked, non-expired grant
DROP POLICY IF EXISTS "customer super inserts own sightings" ON public.delivery_sightings;
CREATE POLICY "customer super inserts own sightings"
  ON public.delivery_sightings FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.customer_super_grants g
      WHERE g.id         = delivery_sightings.grant_id
        AND g.user_id    = auth.uid()
        AND g.revoked_at IS NULL
        AND g.expires_at > now()
    )
  );

-- Customer super reads their own sightings (confirmed deliveries on their grant)
DROP POLICY IF EXISTS "customer super reads own sightings" ON public.delivery_sightings;
CREATE POLICY "customer super reads own sightings"
  ON public.delivery_sightings FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.customer_super_grants g
      WHERE g.id         = delivery_sightings.grant_id
        AND g.user_id    = auth.uid()
        AND g.revoked_at IS NULL
    )
  );

-- =============================================================================
-- 9. admin_alerts — rate-limit breach + grant misuse signals
-- =============================================================================
-- Design doc §3.11 + Mathematician §8:
-- App middleware writes rows here when rate limit sustained (20 req/hour per magic link,
-- 100+ for 3+ hours). No push notification — next-login visibility for admin.
-- Also used for suspected grant misuse (forward + concurrent sessions from distant IPs).
CREATE TABLE IF NOT EXISTS public.admin_alerts (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_type       text        NOT NULL
                                 CHECK (alert_type IN ('rate_limit_sustained','grant_misuse_suspected','other')),
  severity         text        NOT NULL DEFAULT 'info'
                                 CHECK (severity IN ('info','warning','critical')),
  subject_type     text,        -- e.g. 'customer_super_grant' | 'contractor' | 'job'
  subject_id       uuid,
  details          jsonb,
  created_at       timestamptz NOT NULL DEFAULT now(),
  acknowledged_at  timestamptz,
  acknowledged_by  uuid        REFERENCES public.profiles(id) ON DELETE SET NULL
);

-- Sparse index: unacknowledged alerts by recency (admin dashboard inbox)
CREATE INDEX IF NOT EXISTS idx_admin_alerts_unack
  ON public.admin_alerts (created_at DESC)
  WHERE acknowledged_at IS NULL;

ALTER TABLE public.admin_alerts ENABLE ROW LEVEL SECURITY;

-- Admins only (not supervisors — security sensitivity of rate-limit data)
DROP POLICY IF EXISTS "admin manages alerts" ON public.admin_alerts;
CREATE POLICY "admin manages alerts"
  ON public.admin_alerts FOR ALL TO authenticated
  USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  )
  WITH CHECK (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';

COMMIT;

-- =============================================================================
-- VERIFY — run each query separately after applying the migration
-- =============================================================================

-- A. profiles.role CHECK now includes 'contractor'
SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.profiles'::regclass
  AND conname = 'profiles_role_check';
-- Expect: role IN ('admin', 'supervisor', 'detailer', 'driver', 'installer', 'contractor')

-- B. jobs.closed_at column exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'jobs' AND column_name = 'closed_at';
-- Expect: 1 row, timestamptz, YES (nullable)

-- C. trg_jobs_closed_at trigger is registered
SELECT tgname, tgenabled, tgtype
FROM pg_trigger
WHERE tgrelid = 'public.jobs'::regclass AND tgname = 'trg_jobs_closed_at';
-- Expect: 1 row

-- D. New tables exist (expect 6 rows)
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'install_contractor_assignments',
    'customer_super_grants',
    'install_progress_reports',
    'claim_report_links',
    'delivery_sightings',
    'admin_alerts'
  )
ORDER BY table_name;

-- E. install_photos.report_id column added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'install_photos' AND column_name = 'report_id';
-- Expect: 1 row, uuid, YES (nullable)

-- F. RLS is enabled on all new tables (expect 6 rows, all relrowsecurity = true)
SELECT relname, relrowsecurity
FROM pg_class
WHERE relnamespace = 'public'::regnamespace
  AND relname IN (
    'install_contractor_assignments',
    'customer_super_grants',
    'install_progress_reports',
    'claim_report_links',
    'delivery_sightings',
    'admin_alerts'
  )
ORDER BY relname;

-- G. RLS policies count per table (sanity check)
SELECT polrelid::regclass AS table_name, count(*) AS policy_count
FROM pg_policy
WHERE polrelid::regclass::text IN (
  'install_contractor_assignments',
  'customer_super_grants',
  'install_progress_reports',
  'claim_report_links',
  'delivery_sightings',
  'admin_alerts'
)
GROUP BY polrelid
ORDER BY table_name;
-- Expect:
--   install_contractor_assignments  → 2
--   customer_super_grants           → 2
--   install_progress_reports        → 4
--   claim_report_links              → 1
--   delivery_sightings              → 3
--   admin_alerts                    → 1

-- H. Verify backfill (expect 0 rows if no complete jobs existed at apply time)
SELECT count(*) AS complete_jobs_without_closed_at
FROM public.jobs
WHERE install_status = 'complete' AND closed_at IS NULL;
-- Expect: 0

-- I. All indexes created (expect 9 rows)
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'idx_contractor_assignments_contractor',
    'idx_contractor_assignments_job',
    'idx_customer_super_grants_user',
    'idx_customer_super_grants_job',
    'idx_progress_reports_job',
    'idx_progress_reports_contractor',
    'idx_claim_report_links_report',
    'idx_install_photos_report',
    'idx_delivery_sightings_delivery',
    'idx_delivery_sightings_grant',
    'idx_admin_alerts_unack'
  )
ORDER BY indexname;
-- Expect: 11 rows


-- =============================================================================
-- ROLLBACK (uncomment to undo — apply as a separate transaction)
-- =============================================================================
-- BEGIN;
-- -- 9. admin_alerts
-- DROP TABLE IF EXISTS public.admin_alerts CASCADE;
-- -- 8. delivery_sightings
-- DROP TABLE IF EXISTS public.delivery_sightings CASCADE;
-- -- 7. install_photos.report_id
-- DROP INDEX IF EXISTS public.idx_install_photos_report;
-- ALTER TABLE public.install_photos DROP COLUMN IF EXISTS report_id;
-- -- 6. claim_report_links
-- DROP TABLE IF EXISTS public.claim_report_links CASCADE;
-- -- 5. install_progress_reports
-- DROP TABLE IF EXISTS public.install_progress_reports CASCADE;
-- -- 4. customer_super_grants
-- DROP TABLE IF EXISTS public.customer_super_grants CASCADE;
-- -- 3. install_contractor_assignments
-- DROP TABLE IF EXISTS public.install_contractor_assignments CASCADE;
-- -- 2. jobs.closed_at + trigger
-- DROP TRIGGER IF EXISTS trg_jobs_closed_at ON public.jobs;
-- DROP FUNCTION IF EXISTS public.trg_set_job_closed_at();
-- ALTER TABLE public.jobs DROP COLUMN IF EXISTS closed_at;
-- -- 1. profiles.role CHECK — restore to pre-migration state
-- ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
-- ALTER TABLE public.profiles ADD CONSTRAINT profiles_role_check
--   CHECK (role IN ('admin', 'supervisor', 'detailer', 'driver', 'installer'));
-- NOTIFY pgrst, 'reload schema';
-- COMMIT;
