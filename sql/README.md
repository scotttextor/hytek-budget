# HYTEK Budget — SQL migration

## Apply in Supabase SQL Editor (hytek-detailing project)

1. Open Supabase → SQL Editor → New query
2. Paste `01-snapshot-install-tables.sql` → Run → check the verify query at bottom shows matching row counts (live = snapshot)
3. Paste `02-budget-migration-v1.sql` → Run → check for "COMMIT" and no errors
4. Run post-apply verification queries at bottom of `02-budget-migration-v1.sql`
5. Paste `03-phase1-claim-kind.sql` → Run → check for "COMMIT" and run the 3 verify queries at the bottom
6. Paste `04-phase1.5-variations-rework.sql` → Run → check for "COMMIT" and run the verify queries at the bottom
7. Paste `05-phase2-roles.sql` → Run → check for "COMMIT" and run all 9 verify queries at the bottom
8. From a terminal:
   ```bash
   cd ../hytek-detailing/app
   node scripts/check-job-lifecycle.js
   ```
   Must show `✓ No drift detected across all 3 per-department statuses`

## Migration log

| File | Applied | What it did |
|---|---|---|
| `01-snapshot-install-tables.sql` | 2026-04-20 | Snapshot of install_*, job_variations, job_rework at `_snapshot_20260420` |
| `02-budget-migration-v1.sql` | 2026-04-20 | Variation state machine expansion, PO columns, transition log, rate history |
| `03-phase1-claim-kind.sql` | 2026-04-20 | Discriminated `claim_kind` + `over_budget` flag + GPS columns on `install_claims` |
| `04-phase1.5-variations-rework.sql` | pending | captured_at + GPS on job_variations + job_rework, partial CHECK approved⇒po_reference, install-photos storage bucket |
| `05-phase2-roles.sql` | pending | contractor role in profiles CHECK; jobs.closed_at set-once trigger; 6 new tables (install_contractor_assignments, customer_super_grants, install_progress_reports, claim_report_links, delivery_sightings, admin_alerts); install_photos.report_id FK; full RLS. Design: hytek-install/docs/superpowers/specs/2026-04-21-contractor-customer-roles-design.md |

## If anything looks wrong

- Don't panic, don't `--fix`.
- Uncomment the rollback block at the bottom of `02-budget-migration-v1.sql` and run it.
- The snapshots from step 2 are untouched — if tables got corrupted, we restore from them.

## Rollback hierarchy (least → most drastic)

1. **Run the commented rollback block** — undoes schema additions
2. **Restore from snapshots** — `TRUNCATE install_claims; INSERT INTO install_claims SELECT * FROM install_claims_snapshot_20260420;` etc.
3. **Supabase PITR** — point-in-time recovery to before the migration (paid plan only; Supabase dashboard)
4. **Git** — `git checkout pre-install-retirement-2026-04-20` on both `hytek-detailing` and `hytek-detailing/app` submodule
