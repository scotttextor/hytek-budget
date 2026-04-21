@AGENTS.md

# HYTEK Budget App — MOTHBALLED 2026-04-22

> **🛑 MOTHBALLED 2026-04-22:** This app has been retired. All routes now 307
> redirect to `https://hytek-install.vercel.app/dashboard` via
> [`next.config.ts`](next.config.ts) `redirects()`. Any request hitting
> `budget.hytekframing.com.au` lands on the new app.
>
> **Why:** hytek-install has full parity and is the sole writer for all
> install tables (verified 2026-04-22 — hytek-install writes
> install_claims, install_budget_items, install_flagged_items,
> install_photos, job_rework + job_variations via the offline queue).
> Keeping two apps alive was pure maintenance tax.
>
> **What stayed:**
> - The Vercel deployment (serves the redirect + fallback page)
> - The GitHub repo + full git history
> - The Supabase tables (hytek-install still writes them)
> - The OneDrive git-bundle backup at `CLAUDE DATA FILE/github-mirror/hytek-budget.bundle`
> - Git tag `mothballed-2026-04-22` on the commit that flipped the redirect
>
> **What changed:**
> - Every HTTP path redirects to hytek-install (307 — intentionally non-permanent
>   so browsers don't aggressively cache if we ever un-mothball)
> - Root page shows a static "retired" notice as a safety fallback
>
> **To un-mothball:** delete the `redirects()` block in `next.config.ts` and
> redeploy. All routes instantly work again.
>
> **Do not start new feature work here.** Build in `hytek-install`.

Mobile-first budget tracking app for HYTEK Framing. Was built to replace the earlier Install UI that lived under `hytek-detailing/app/install/*`. Since superseded by `hytek-install` which expanded to cover the full install workflow (office desktop + mobile PIN supervisors).

## Role in the HYTEK suite (historical — pre-mothball)

- **WAS sole writer** for `install_budget_items`, `install_claims`, `job_variations`, `job_rework`, `install_photos`, `install_flagged_items` in the shared `hytek-detailing` Supabase project. hytek-install now covers all writes.
- Install app UI is retired (routes still on disk in git history at tag `pre-install-retirement-2026-04-20` on both `hytek-detailing` and `hytek-detailing/app`). Safety branches: `install-retired-backup` on both.
- Hub import (`hytek-hub/app/api/import-job/route.ts`) continues to seed `install_budget_items` on quote import. Budget reads what Hub seeded and is the only thing that mutates it thereafter.
- Dispatch, Detailing, Planner, Invoicing apps all unchanged — they read the same shared DB.

## Tech stack
- Next.js 16.2.3 (App Router — **post-training-cutoff; read `node_modules/next/dist/docs/` for API questions**)
- React 19.2.4
- Supabase JS `@supabase/supabase-js ^2.103.0`
- Tailwind v4 via `@tailwindcss/postcss`
- `idb-keyval` for offline claim queue
- TypeScript strict

## Folder structure
- `src/app/` — App Router pages
  - `login/page.tsx`
  - `dashboard/page.tsx` (placeholder — Phase 0 proof-of-life)
  - `log/page.tsx` (Phase 1 — mobile Quick-Log, 3 streams)
- `src/lib/` — Supabase client, auth context, types, flags
- `sql/` — migration + snapshot scripts (apply in Supabase SQL Editor)

## Shared Supabase
- URL: `https://gqtikzguvhukpujyxkez.supabase.co`
- Same anon + service-role keys as `hytek-detailing/app` (architect: per-app keys = scavenger hunt on rotation)
- Legacy JWT format (`eyJ...`), NOT new `sb_publishable_` format

## Key patterns (match siblings)
- DD/MM/YYYY date format (Australian) — use helper when added
- All `useState` before any conditional returns (React hooks rule — has bitten twice in sibling apps)
- RLS: `FOR ALL` policies need BOTH `USING` and `WITH CHECK` clauses for inserts
- Brand: yellow `#FFCB05`, black `#231F20`

## Mobile-first rules (Panel #1 UX lens)
- Hot-path screens (`/log`, job picker): **max 3 taps** from cold launch to save
- Min tap target 44×44 (Apple HIG)
- Inputs `font-size: 16px` minimum — anything smaller triggers iOS auto-zoom
- Offline queue is **append-only** — offline logs become new `install_claims` rows with client-generated UUIDs, never UPDATEs (prevents last-write-wins races)
- Confirmation UI (`Logged!`) fires off the local IndexedDB write, NOT the Supabase POST (spotty 4G = POST can take 10+ seconds)

## State machine (job_variations.status)
```
raised → priced → submitted → approved → invoiced
         ↘       ↘           ↘
          cancelled  cancelled  rejected
                     priced (revise)
         superseded (new variation replaces this)
```
- `approved` requires `po_reference` to be non-null (app-level enforcement; DB CHECK verifies value, not presence)
- `invoiced` implies a matching invoice row in the SEPARATE `hytek-invoicing` Supabase — cannot be a FK (cross-project), enforced at app level

## Audit discipline (non-negotiable)
After ANY change touching `jobs`, `tasks`, `install_budget_items`, or triggers:
```bash
cd ../hytek-detailing/app && node scripts/check-job-lifecycle.js
```
Must show `No drift detected`. NEVER run `--fix` without Scott's approval.

## Rules for future sessions
- Panel of specialists for non-trivial decisions — see `feedback_expert_agent_discipline.md` in user memory
- No patches — root cause only
- Verify before claiming done — run dev server + hit the page before declaring success
- Never DROP or RENAME columns on `jobs`, `install_*`, `job_variations`, `job_rework`, `install_photos` — other apps still read them
- Never bypass the SQL migration audit (`check-job-lifecycle.js`)

## Accounts
- Admin: `admin@hytekframing.com.au` / `Hytek2026`
- Test jobs: Test 30 Unit Full-Coverage Complex, Test 25 Unit Complex, Test Hospital, Test House
