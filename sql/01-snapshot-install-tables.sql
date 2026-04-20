-- =============================================================================
-- HYTEK Budget — Safety snapshot of Install-related tables (2026-04-20)
--
-- Creates timestamped snapshot copies of every table the retired Install app
-- used to write to. Snapshots live in the same DB; belt-and-braces on top of
-- Supabase PITR. If the Budget-app migration corrupts anything, restore from
-- these tables by swapping back (or selectively INSERT ... SELECT).
--
-- Apply: paste whole file into Supabase SQL Editor against hytek-detailing
--        project. Safe to re-run — uses IF NOT EXISTS pattern.
-- Rollback: DROP each snapshot table individually when we're confident (e.g.
--        after 30 days of Budget running without incident).
-- =============================================================================

BEGIN;

-- Snapshot install_budget_items
CREATE TABLE IF NOT EXISTS public.install_budget_items_snapshot_20260420
  AS SELECT * FROM public.install_budget_items WHERE false;
INSERT INTO public.install_budget_items_snapshot_20260420
  SELECT * FROM public.install_budget_items
  ON CONFLICT DO NOTHING;

-- Snapshot install_claims
CREATE TABLE IF NOT EXISTS public.install_claims_snapshot_20260420
  AS SELECT * FROM public.install_claims WHERE false;
INSERT INTO public.install_claims_snapshot_20260420
  SELECT * FROM public.install_claims
  ON CONFLICT DO NOTHING;

-- Snapshot job_variations
CREATE TABLE IF NOT EXISTS public.job_variations_snapshot_20260420
  AS SELECT * FROM public.job_variations WHERE false;
INSERT INTO public.job_variations_snapshot_20260420
  SELECT * FROM public.job_variations
  ON CONFLICT DO NOTHING;

-- Snapshot job_rework
CREATE TABLE IF NOT EXISTS public.job_rework_snapshot_20260420
  AS SELECT * FROM public.job_rework WHERE false;
INSERT INTO public.job_rework_snapshot_20260420
  SELECT * FROM public.job_rework
  ON CONFLICT DO NOTHING;

-- Snapshot install_photos (if exists)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables
             WHERE table_schema='public' AND table_name='install_photos') THEN
    EXECUTE 'CREATE TABLE IF NOT EXISTS public.install_photos_snapshot_20260420
             AS SELECT * FROM public.install_photos WHERE false';
    EXECUTE 'INSERT INTO public.install_photos_snapshot_20260420
             SELECT * FROM public.install_photos ON CONFLICT DO NOTHING';
  END IF;
END $$;

-- Snapshot variation_costs, rework_costs, variation_photos, rework_photos (detailing's shared)
DO $$
DECLARE tbl text;
BEGIN
  FOR tbl IN SELECT unnest(ARRAY[
    'variation_costs', 'rework_costs',
    'variation_photos', 'rework_photos'
  ]) LOOP
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema='public' AND table_name=tbl) THEN
      EXECUTE format('CREATE TABLE IF NOT EXISTS public.%I_snapshot_20260420
                      AS SELECT * FROM public.%I WHERE false', tbl, tbl);
      EXECUTE format('INSERT INTO public.%I_snapshot_20260420
                      SELECT * FROM public.%I ON CONFLICT DO NOTHING', tbl, tbl);
    END IF;
  END LOOP;
END $$;

COMMIT;

-- Verify: row counts should match current tables
SELECT 'install_budget_items' AS tbl, COUNT(*) AS live,
       (SELECT COUNT(*) FROM install_budget_items_snapshot_20260420) AS snapshot
  FROM install_budget_items
UNION ALL
SELECT 'install_claims', COUNT(*),
       (SELECT COUNT(*) FROM install_claims_snapshot_20260420)
  FROM install_claims
UNION ALL
SELECT 'job_variations', COUNT(*),
       (SELECT COUNT(*) FROM job_variations_snapshot_20260420)
  FROM job_variations
UNION ALL
SELECT 'job_rework', COUNT(*),
       (SELECT COUNT(*) FROM job_rework_snapshot_20260420)
  FROM job_rework;
