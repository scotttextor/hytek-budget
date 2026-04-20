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

export interface InstallClaim {
  id: string
  budget_item_id: string
  amount: number | null
  percent_complete: number | null
  hours: number | null
  qty: number | null
  notes: string | null
  captured_at: string // client-stamped (when installer pressed save)
  created_at: string  // server-stamped (when Supabase received)
  created_by: string | null
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
