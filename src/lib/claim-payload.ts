// Discriminated claim payload types + builder. Panel #2 Mathematician §4 —
// invalid states unrepresentable at the call site. DB CHECK is the backstop.
import type { ClaimKind } from './types'

export type DollarClaim = {
  kind: 'dollar'
  amountCents: number // > 0
  notes?: string
}
export type PercentClaim = {
  kind: 'percent'
  percent: number // 0 < x <= 100
  notes?: string
}
export type HoursClaim = {
  kind: 'hours'
  hours: number // > 0
  companyServiceId: string
  rateUsed: number
  notes?: string
}
export type QtyClaim = {
  kind: 'qty'
  qty: number // > 0
  companyServiceId: string
  rateUsed: number
  notes?: string
}

export type ClaimPayload = DollarClaim | PercentClaim | HoursClaim | QtyClaim

export interface ClaimContext {
  userId: string
  jobId: string
  budgetItemId: string
  subItemId?: string | null
  claimDate: string // YYYY-MM-DD
  budgetAmountDollars?: number | null
  overBudget?: boolean
  unitNo?: string | null
  supervisorId?: string | null
  companyId?: string | null
  gps?: {
    lat: number
    lng: number
    accuracyMeters: number
  } | null
}

export interface ClaimRow {
  id: string
  job_id: string
  budget_item_id: string
  sub_item_id: string | null
  claim_date: string
  claim_kind: ClaimKind
  claim_amount: number // dollars (DB stores numeric)
  percent_complete: number | null
  hours: number | null
  qty: number | null
  rate_used: number | null
  notes: string | null
  over_budget: boolean
  captured_at: string // ISO timestamptz
  captured_lat: number | null
  captured_lng: number | null
  captured_accuracy_m: number | null
  created_by: string
  company_id: string | null
  company_service_id: string | null
  unit_no: string | null
  supervisor_id: string | null
}

function newUuidV4(): string {
  // Prefer platform UUID generator (Node 18+, modern browsers).
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID()
  }
  // RFC 4122 v4 fallback — used only in ancient environments.
  const b = globalThis.crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const hex = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function buildClaimRow(payload: ClaimPayload, ctx: ClaimContext): ClaimRow {
  const base = {
    id: newUuidV4(),
    job_id: ctx.jobId,
    budget_item_id: ctx.budgetItemId,
    sub_item_id: ctx.subItemId ?? null,
    claim_date: ctx.claimDate,
    notes: payload.notes ?? null,
    over_budget: ctx.overBudget ?? false,
    captured_at: new Date().toISOString(),
    captured_lat: ctx.gps?.lat ?? null,
    captured_lng: ctx.gps?.lng ?? null,
    captured_accuracy_m: ctx.gps?.accuracyMeters ?? null,
    created_by: ctx.userId,
    company_id: ctx.companyId ?? null,
    company_service_id: null as string | null,
    unit_no: ctx.unitNo ?? null,
    supervisor_id: ctx.supervisorId ?? null,
  }

  switch (payload.kind) {
    case 'dollar':
      return {
        ...base,
        claim_kind: 'dollar',
        claim_amount: payload.amountCents / 100,
        percent_complete: null,
        hours: null,
        qty: null,
        rate_used: null,
      }
    case 'percent': {
      const budget = ctx.budgetAmountDollars ?? null
      const amount = budget != null ? Math.round(budget * payload.percent) / 100 : 0
      return {
        ...base,
        claim_kind: 'percent',
        claim_amount: amount,
        percent_complete: payload.percent,
        hours: null,
        qty: null,
        rate_used: null,
      }
    }
    case 'hours':
      return {
        ...base,
        claim_kind: 'hours',
        claim_amount: Math.round(payload.hours * payload.rateUsed * 100) / 100,
        percent_complete: null,
        hours: payload.hours,
        qty: null,
        rate_used: payload.rateUsed,
        company_service_id: payload.companyServiceId,
      }
    case 'qty':
      return {
        ...base,
        claim_kind: 'qty',
        claim_amount: Math.round(payload.qty * payload.rateUsed * 100) / 100,
        percent_complete: null,
        hours: null,
        qty: payload.qty,
        rate_used: payload.rateUsed,
        company_service_id: payload.companyServiceId,
      }
  }
}
