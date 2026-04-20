import { describe, it, expect, beforeEach } from 'vitest'
import {
  enqueueClaim,
  loadAllQueued,
  removeQueued,
  updateQueued,
  classifyResponse,
  computeNextRetry,
  type QueuedClaim,
} from './queue'
import type { ClaimRow } from './claim-payload'
import { clear } from 'idb-keyval'

const baseRow: ClaimRow = {
  id: '00000000-0000-4000-a000-000000000001',
  job_id: 'j', budget_item_id: 'b', sub_item_id: null, claim_date: '2026-04-20',
  claim_kind: 'dollar', claim_amount: 100,
  percent_complete: null, hours: null, qty: null, rate_used: null,
  notes: null, over_budget: false,
  captured_at: new Date().toISOString(),
  captured_lat: null, captured_lng: null, captured_accuracy_m: null,
  created_by: 'u',
  company_id: null, company_service_id: null, unit_no: null, supervisor_id: null,
}

beforeEach(async () => {
  await clear()
})

describe('enqueue + loadAll', () => {
  it('stores and retrieves a claim', async () => {
    await enqueueClaim(baseRow)
    const all = await loadAllQueued()
    expect(all).toHaveLength(1)
    expect(all[0].payload.id).toBe(baseRow.id)
    expect(all[0].status.state).toBe('pending')
  })

  it('preserves insert order', async () => {
    const a = { ...baseRow, id: 'a' }
    const b = { ...baseRow, id: 'b' }
    await enqueueClaim(a)
    await enqueueClaim(b)
    const all = await loadAllQueued()
    expect(all.map((r) => r.payload.id)).toEqual(['a', 'b'])
  })
})

describe('removeQueued', () => {
  it('removes by id', async () => {
    await enqueueClaim(baseRow)
    await removeQueued(baseRow.id)
    expect(await loadAllQueued()).toHaveLength(0)
  })
})

describe('updateQueued', () => {
  it('updates status', async () => {
    await enqueueClaim(baseRow)
    await updateQueued(baseRow.id, {
      state: 'failed',
      attempts: 1,
      lastError: 'boom',
      nextRetryAt: Date.now() + 60_000,
    })
    const all = await loadAllQueued()
    expect(all[0].status.state).toBe('failed')
  })
})

describe('classifyResponse', () => {
  it('classifies 2xx as success', () => {
    expect(classifyResponse(null, null).kind).toBe('success')
  })
  it('classifies 23505 as success (idempotent retry)', () => {
    const err = { code: '23505', message: 'duplicate key' }
    expect(classifyResponse(err, null).kind).toBe('success')
  })
  it('classifies 23503 as dead-fk', () => {
    const err = { code: '23503', message: 'fk violation on budget_item_id' }
    const c = classifyResponse(err, null)
    expect(c.kind).toBe('dead')
    expect(c.reason).toMatch(/fk/i)
  })
  it('classifies 4xx as dead-other', () => {
    expect(classifyResponse({ code: '23502', message: 'not null' }, null).kind).toBe('dead')
  })
  it('classifies network error as retry', () => {
    expect(classifyResponse({ message: 'Failed to fetch' }, null).kind).toBe('retry')
  })
})

describe('computeNextRetry', () => {
  it('exp backoff', () => {
    const now = 1_000_000
    const d1 = computeNextRetry(1, now) - now
    const d2 = computeNextRetry(2, now) - now
    expect(d1).toBeGreaterThanOrEqual(60_000 * 0.8)
    expect(d1).toBeLessThanOrEqual(60_000 * 1.2)
    expect(d2).toBeGreaterThanOrEqual(120_000 * 0.8)
    expect(d2).toBeLessThanOrEqual(120_000 * 1.2)
  })
  it('caps at 1h', () => {
    const delay = computeNextRetry(20, 0)
    expect(delay).toBeLessThanOrEqual(3_600_000 * 1.2)
  })
})
