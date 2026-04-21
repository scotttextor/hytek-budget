// Shared types mirroring the hytek-detailing Supabase project.
// Duplicated (not imported) per Panel #1 Architect recommendation:
// cost of duplication is low for solo-dev; cost of drift is caught by type-check at build.

export type UserRole = 'admin' | 'supervisor' | 'detailer' | 'driver' | 'installer' | 'contractor'

export interface Profile {
  id: string
  email: string
  full_name: string | null
  role: UserRole
  created_at: string
}

export interface Job {
  id: string
  job_number: string
  name: string
  client: string | null
  job_type: 'single_building' | 'multi_unit'
  status: string | null
  install_status: 'setup' | 'active' | 'complete' | null
  detailing_status: 'setup' | 'active' | 'complete' | null
  dispatch_status: 'setup' | 'active' | 'complete' | null
  created_at: string
}

// Real columns (verified 2026-04-20 against live Supabase):
// id, job_id, name, category, budget_amount, budget_hours, budget_qty,
// rate_per_unit, unit, unit_type (often null), notes, sort_order,
// created_at, completed, completed_at, group_id, scope, unit_no, parent_item_id.
// UI display uses `name`. `unit` is billing cadence ("per hour"/"lump sum");
// `unit_type` is the semantic kind when populated, else null.
export interface InstallBudgetItem {
  id: string
  job_id: string
  name: string | null
  category: string
  budget_amount: number | null
  budget_hours: number | null
  budget_qty: number | null
  rate_per_unit: number | null
  unit: string | null
  unit_type: string | null
  notes: string | null
  sort_order: number | null
  completed: boolean
  completed_at: string | null
  group_id: string | null
  scope: string | null
  unit_no: string | null
  parent_item_id: string | null
  created_at: string
}

// `install_claims` real columns (verified against scripts/install-schema.sql +
// install-phase1-data-foundation.sql + install-templates.sql in hytek-detailing).
// claim_amount is the canonical payable $ (NOT NULL, DB default 0).
// Metadata fields (percent_complete / hours+rate_used / qty+rate_used) are the
// audit trail for HOW claim_amount was computed; claim_kind discriminates.
export type ClaimKind = 'dollar' | 'percent' | 'hours' | 'qty'

export interface InstallClaim {
  id: string
  job_id: string
  budget_item_id: string
  sub_item_id: string | null
  claim_date: string // date (day resolution) — display/reporting
  claim_kind: ClaimKind
  claim_amount: number // NOT NULL — canonical payable $
  percent_complete: number | null
  hours: number | null
  qty: number | null
  rate_used: number | null
  notes: string | null
  over_budget: boolean
  captured_at: string  // client-stamped timestamptz (when installer pressed save)
  captured_lat: number | null
  captured_lng: number | null
  captured_accuracy_m: number | null
  created_by: string | null
  created_at: string   // server-stamped (when Supabase received)
  // Contractor/rate-card linkage (from install-phase1-part2-alters.sql)
  company_id: string | null
  company_service_id: string | null
  unit_no: string | null
  supervisor_id: string | null
}

// Variation state machine — Budget app is sole writer
export type VariationState =
  | 'raised'
  | 'priced'
  | 'submitted'
  | 'approved'
  | 'invoiced'
  | 'rejected'
  | 'cancelled'
  | 'superseded'

// Real columns (verified 2026-04-20 against add-variations-rework.sql + 02-budget-migration-v1.sql).
// `description` is the required headline text (the UI's "title"). `reason` is optional narrative.
// `purchase_order` is a legacy free-text field from original creation; `po_reference` added by
// Phase 0 migration and is the canonical PO field for the new Budget app — prefer po_reference.
// `variation_number` is app-generated (`V-YYYYMMDD-xxxx`) — no DB default.
export interface JobVariation {
  id: string
  job_id: string
  variation_number: string
  description: string               // title (NOT NULL)
  reason: string | null
  estimated_cost: number            // NOT NULL DEFAULT 0
  actual_cost: number               // NOT NULL DEFAULT 0
  purchase_order: string | null     // legacy
  po_reference: string | null       // canonical for Budget app
  requires_gm_approval: boolean
  gm_approved: boolean
  gm_approved_by: string | null
  approved_by: string | null
  approved_date: string | null
  status: VariationState
  affects_detailing: boolean
  affects_dispatch: boolean
  affects_install: boolean
  affects_fabrication: boolean
  daywork_notes: string | null
  status_changed_at: string | null
  status_changed_by: string | null
  // Phase 1.5 additions (in migration sql/04)
  captured_at: string | null
  captured_lat: number | null
  captured_lng: number | null
  captured_accuracy_m: number | null
  created_by: string | null
  created_by_department: string | null
  created_at: string
}

// Real columns (verified 2026-04-20 against add-variations-rework.sql).
// UI "title" → `description`, UI "details" → `explanation`. `responsible_department`
// is a CHECK-constrained enum and is the core categorisation — we use it as the
// installer's "who" picker on the Rework form. `status` starts 'identified' (not 'open').
export type ReworkStatus = 'identified' | 'in_progress' | 'complete'
export type ResponsibleDepartment = 'detailing' | 'dispatch' | 'install' | 'fabrication' | 'other'

export interface JobRework {
  id: string
  job_id: string
  rework_number: string
  description: string               // title (NOT NULL)
  explanation: string               // required details (NOT NULL)
  responsible_department: ResponsibleDepartment
  responsible_person: string | null
  estimated_cost: number            // NOT NULL DEFAULT 0
  actual_cost: number               // NOT NULL DEFAULT 0
  status: ReworkStatus
  affects_detailing: boolean
  affects_dispatch: boolean
  affects_install: boolean
  affects_fabrication: boolean
  // Phase 1.5 additions (in migration sql/04)
  captured_at: string | null
  captured_lat: number | null
  captured_lng: number | null
  captured_accuracy_m: number | null
  created_by: string | null
  created_at: string
}
