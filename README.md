# HYTEK Budget

Mobile-first budget tracking app for HYTEK Framing. Replaces the retired Install UI (`hytek-detailing/app/install/*`) — Budget is now the sole writer for `install_budget_items`, `install_claims`, `job_variations`, `job_rework` and related tables.

## Stack
- Next.js 16.2.3 (App Router)
- React 19.2.4
- Supabase JS `@supabase/supabase-js` (shared `hytek-detailing` project)
- Tailwind v4
- `idb-keyval` for offline claim queue (site crew, spotty 4G)
- TypeScript

## Development

```bash
npm install
npm run dev
```

App runs at `http://localhost:3000`.

## Deploy

Vercel project, custom domain `budget.hytekframing.com.au`.

## First time setup

1. `npm install`
2. Apply SQL migration: paste `sql/01-snapshot-install-tables.sql` into Supabase SQL Editor (safety snapshot)
3. Paste `sql/02-budget-migration-v1.sql` into Supabase SQL Editor (the migration)
4. Run `node ../hytek-detailing/app/scripts/check-job-lifecycle.js` — must show no drift
5. `npm run dev` → log in as `admin@hytekframing.com.au` / `Hytek2026`
