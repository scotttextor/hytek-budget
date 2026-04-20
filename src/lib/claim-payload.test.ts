import { describe, it, expect } from 'vitest'
import { buildClaimRow, type ClaimPayload } from './claim-payload'

const base = {
  userId: 'user-uuid',
  jobId: 'job-uuid',
  budgetItemId: 'item-uuid',
  claimDate: '2026-04-20',
}

describe('buildClaimRow', () => {
  it('builds dollar claim', () => {
    const p: ClaimPayload = { kind: 'dollar', amountCents: 10050, notes: 'ok' }
    const row = buildClaimRow(p, base)
    expect(row.claim_kind).toBe('dollar')
    expect(row.claim_amount).toBe(100.5)
    expect(row.percent_complete).toBeNull()
    expect(row.hours).toBeNull()
    expect(row.qty).toBeNull()
    expect(row.notes).toBe('ok')
    expect(typeof row.id).toBe('string')
    expect(row.id.length).toBeGreaterThan(30) // uuid
    expect(row.captured_at).toBeTruthy()
  })

  it('builds percent claim — app computes claim_amount from budget', () => {
    const p: ClaimPayload = { kind: 'percent', percent: 25 }
    const row = buildClaimRow(p, { ...base, budgetAmountDollars: 4000 })
    expect(row.claim_kind).toBe('percent')
    expect(row.percent_complete).toBe(25)
    expect(row.claim_amount).toBe(1000) // 25% × $4000
    expect(row.hours).toBeNull()
    expect(row.qty).toBeNull()
  })

  it('builds percent claim with null budget — claim_amount 0', () => {
    const p: ClaimPayload = { kind: 'percent', percent: 25 }
    const row = buildClaimRow(p, { ...base, budgetAmountDollars: null })
    expect(row.claim_amount).toBe(0)
    expect(row.percent_complete).toBe(25)
  })

  it('builds hours claim — claim_amount = hours × rate', () => {
    const p: ClaimPayload = {
      kind: 'hours',
      hours: 8,
      companyServiceId: 'svc-uuid',
      rateUsed: 75,
    }
    const row = buildClaimRow(p, base)
    expect(row.claim_kind).toBe('hours')
    expect(row.hours).toBe(8)
    expect(row.rate_used).toBe(75)
    expect(row.claim_amount).toBe(600)
    expect(row.percent_complete).toBeNull()
    expect(row.qty).toBeNull()
    expect(row.company_service_id).toBe('svc-uuid')
  })

  it('builds qty claim — claim_amount = qty × rate', () => {
    const p: ClaimPayload = {
      kind: 'qty',
      qty: 12,
      companyServiceId: 'svc-uuid',
      rateUsed: 50,
    }
    const row = buildClaimRow(p, base)
    expect(row.claim_kind).toBe('qty')
    expect(row.qty).toBe(12)
    expect(row.claim_amount).toBe(600)
    expect(row.hours).toBeNull()
    expect(row.percent_complete).toBeNull()
  })

  it('stamps over_budget when flagged by caller', () => {
    const p: ClaimPayload = { kind: 'dollar', amountCents: 500000 }
    const row = buildClaimRow(p, { ...base, overBudget: true })
    expect(row.over_budget).toBe(true)
  })

  it('produces distinct UUIDs', () => {
    const p: ClaimPayload = { kind: 'dollar', amountCents: 100 }
    const r1 = buildClaimRow(p, base)
    const r2 = buildClaimRow(p, base)
    expect(r1.id).not.toBe(r2.id)
  })
})
