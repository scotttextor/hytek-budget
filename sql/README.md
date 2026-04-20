# HYTEK Budget — SQL migration

## Apply in Supabase SQL Editor (hytek-detailing project)

1. Open Supabase → SQL Editor → New query
2. Paste `01-snapshot-install-tables.sql` → Run → check the verify query at bottom shows matching row counts (live = snapshot)
3. Paste `02-budget-migration-v1.sql` → Run → check for "COMMIT" and no errors
4. Run post-apply verification queries at bottom of `02-budget-migration-v1.sql`
5. From a terminal:
   ```bash
   cd ../hytek-detailing/app
   node scripts/check-job-lifecycle.js
   ```
   Must show `✓ No drift detected across all 3 per-department statuses`

## If anything looks wrong

- Don't panic, don't `--fix`.
- Uncomment the rollback block at the bottom of `02-budget-migration-v1.sql` and run it.
- The snapshots from step 2 are untouched — if tables got corrupted, we restore from them.

## Rollback hierarchy (least → most drastic)

1. **Run the commented rollback block** — undoes schema additions
2. **Restore from snapshots** — `TRUNCATE install_claims; INSERT INTO install_claims SELECT * FROM install_claims_snapshot_20260420;` etc.
3. **Supabase PITR** — point-in-time recovery to before the migration (paid plan only; Supabase dashboard)
4. **Git** — `git checkout pre-install-retirement-2026-04-20` on both `hytek-detailing` and `hytek-detailing/app` submodule
