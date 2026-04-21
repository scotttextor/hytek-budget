import { describe, it, expect } from 'vitest'
import { buildVariationRow, type VariationPayload, generateVariationNumber } from './variation-payload'

const base = {
  userId: 'user-uuid',
  jobId: 'job-uuid',
  claimDate: '2026-04-20', // yyyy-mm-dd; used for the variation_number prefix
}

describe('generateVariationNumber', () => {
  it('produces the V-YYYYMMDD-xxxx shape from uuid + date', () => {
    const num = generateVariationNumber('a3f28b45-1111-4000-a000-000000000000', '2026-04-20')
    expect(num).toBe('V-20260420-a3f2')
  })
  it('is deterministic for the same uuid + date', () => {
    const a = generateVariationNumber('a3f28b45-1111-4000-a000-000000000000', '2026-04-20')
    const b = generateVariationNumber('a3f28b45-1111-4000-a000-000000000000', '2026-04-20')
    expect(a).toBe(b)
  })
})

describe('buildVariationRow', () => {
  it('builds a minimum-viable row with required fields', () => {
    const p: VariationPayload = {
      description: 'Extra wall on unit 4',
      poReference: 'PO-12345',
      estimatedCostCents: 125000,
    }
    const row = buildVariationRow(p, base)
    expect(row.description).toBe('Extra wall on unit 4')
    expect(row.po_reference).toBe('PO-12345')
    expect(row.estimated_cost).toBe(1250)
    expect(row.actual_cost).toBe(0)
    expect(row.status).toBe('raised')
    expect(row.created_by_department).toBe('install')
    expect(row.variation_number).toMatch(/^V-20260420-[0-9a-f]{4}$/)
    expect(row.id.length).toBeGreaterThan(30) // uuid
    expect(row.captured_at).toBeTruthy()
    expect(row.reason).toBeNull()
  })

  it('captures optional reason', () => {
    const row = buildVariationRow(
      {
        description: 'Extra wall',
        poReference: 'PO-9',
        estimatedCostCents: 10000,
        reason: 'Client requested after framing started',
      },
      base,
    )
    expect(row.reason).toBe('Client requested after framing started')
  })

  it('stamps GPS when provided', () => {
    const row = buildVariationRow(
      { description: 'x', poReference: 'p', estimatedCostCents: 1 },
      { ...base, gps: { lat: -27.45, lng: 153.02, accuracyMeters: 5 } },
    )
    expect(row.captured_lat).toBe(-27.45)
    expect(row.captured_lng).toBe(153.02)
    expect(row.captured_accuracy_m).toBe(5)
  })

  it('produces distinct UUIDs (and numbers) across calls', () => {
    const a = buildVariationRow({ description: 'x', poReference: 'p', estimatedCostCents: 1 }, base)
    const b = buildVariationRow({ description: 'x', poReference: 'p', estimatedCostCents: 1 }, base)
    expect(a.id).not.toBe(b.id)
    expect(a.variation_number).not.toBe(b.variation_number)
  })
})
