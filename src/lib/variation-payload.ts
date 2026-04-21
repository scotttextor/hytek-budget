// Minimum-viable variation payload for the mobile raise-variation flow.
// Panel #2 UX: required = description + po_reference + estimated_cost.
// Status always starts 'raised'; state machine advances happen in the install
// manager UI (Phase 3), not here.

import type { JobVariation, VariationState } from './types'

export interface VariationPayload {
  description: string              // UI "title"
  poReference: string              // required — Panel #2 "no PO, no save"
  estimatedCostCents: number       // > 0
  reason?: string                  // optional narrative (UI "description" collapsed disclosure)
}

export interface VariationContext {
  userId: string
  jobId: string
  claimDate: string                // yyyy-mm-dd; drives variation_number prefix
  gps?: { lat: number; lng: number; accuracyMeters: number } | null
}

export type VariationRow = Omit<JobVariation, 'created_at' | 'status_changed_at' | 'status_changed_by'> & {
  // created_at / status_changed_at stamped by Supabase; keep row untouched there
  status: VariationState
}

function newUuidV4(): string {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID()
  }
  const b = globalThis.crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const hex = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

/**
 * Derives a short human-readable variation number from a UUID + date.
 * Format: V-YYYYMMDD-xxxx where xxxx is the first 4 hex chars of the UUID.
 * Deterministic for the same (uuid, date) — important for idempotent re-save
 * semantics: if a queued variation is resent after retry, it keeps the same
 * visible number.
 */
export function generateVariationNumber(uuid: string, claimDate: string): string {
  const yyyymmdd = claimDate.slice(0, 10).replace(/-/g, '')
  const suffix = uuid.replace(/-/g, '').slice(0, 4).toLowerCase()
  return `V-${yyyymmdd}-${suffix}`
}

export function buildVariationRow(p: VariationPayload, ctx: VariationContext): VariationRow {
  const id = newUuidV4()
  return {
    id,
    job_id: ctx.jobId,
    variation_number: generateVariationNumber(id, ctx.claimDate),
    description: p.description,
    reason: p.reason ?? null,
    estimated_cost: p.estimatedCostCents / 100,
    actual_cost: 0,
    purchase_order: null,
    po_reference: p.poReference,
    requires_gm_approval: false,
    gm_approved: false,
    gm_approved_by: null,
    approved_by: null,
    approved_date: null,
    status: 'raised',
    affects_detailing: false,
    affects_dispatch: false,
    affects_install: true,
    affects_fabrication: false,
    daywork_notes: null,
    captured_at: new Date().toISOString(),
    captured_lat: ctx.gps?.lat ?? null,
    captured_lng: ctx.gps?.lng ?? null,
    captured_accuracy_m: ctx.gps?.accuracyMeters ?? null,
    created_by: ctx.userId,
    created_by_department: 'install',
  }
}
