// Shared types mirroring the hytek-detailing Supabase project.
// Duplicated (not imported) per Panel #1 Architect recommendation:
// cost of duplication is low for solo-dev; cost of drift is caught by type-check at build.

export type UserRole = 'admin' | 'supervisor' | 'detailer' | 'driver' | 'installer'

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

export interface InstallBudgetItem {
  id: string
  job_id: string
  category: string
  description: string | null
  budget_amount: number | null
  unit_type: string | null
  completed: boolean
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

export interface JobVariation {
  id: string
  job_id: string
  title: string
  description: string | null
  estimated_cost: number | null
  actual_cost: number | null
  status: VariationState
  po_reference: string | null
  status_changed_at: string | null
  status_changed_by: string | null
  created_at: string
}

export interface JobRework {
  id: string
  job_id: string
  title: string
  description: string | null
  root_cause: string | null
  estimated_cost: number | null
  actual_cost: number | null
  status: 'open' | 'in_progress' | 'complete'
  created_at: string
}
