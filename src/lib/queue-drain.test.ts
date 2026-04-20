import { describe, it, expect, beforeEach, vi } from 'vitest'
import { enqueueClaim, loadAllQueued } from './queue'
import { drainQueue } from './queue-drain'
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
  created_by: 'u', company_id: null, company_service_id: null, unit_no: null, supervisor_id: null,
}

beforeEach(async () => {
  await clear()
})

function mockClient(responder: (row: ClaimRow) => { error: { code?: string; message?: string } | null }) {
  return {
    from() { return this },
    async insert(rows: ClaimRow[]) {
      const row = Array.isArray(rows) ? rows[0] : rows
      return { error: responder(row).error, data: null }
    },
  } as any
}

describe('drainQueue', () => {
  it('removes successful inserts', async () => {
    await enqueueClaim(baseRow)
    const sb = mockClient(() => ({ error: null }))
    await drainQueue(sb, { online: true })
    expect(await loadAllQueued()).toHaveLength(0)
  })

  it('treats 23505 as success (idempotent retry)', async () => {
    await enqueueClaim(baseRow)
    const sb = mockClient(() => ({ error: { code: '23505', message: 'dup' } }))
    await drainQueue(sb, { online: true })
    expect(await loadAllQueued()).toHaveLength(0)
  })

  it('dead-letters on 23503 FK violation', async () => {
    await enqueueClaim(baseRow)
    const sb = mockClient(() => ({ error: { code: '23503', message: 'fk' } }))
    await drainQueue(sb, { online: true })
    const all = await loadAllQueued()
    expect(all).toHaveLength(1)
    expect(all[0].status.state).toBe('dead')
  })

  it('marks failed + schedules retry on network error', async () => {
    await enqueueClaim(baseRow)
    const sb = mockClient(() => ({ error: { message: 'Failed to fetch' } }))
    await drainQueue(sb, { online: true })
    const all = await loadAllQueued()
    expect(all).toHaveLength(1)
    expect(all[0].status.state).toBe('failed')
  })

  it('does nothing when offline', async () => {
    await enqueueClaim(baseRow)
    const sb = mockClient(() => ({ error: null }))
    const insertSpy = vi.spyOn(sb, 'from')
    await drainQueue(sb, { online: false })
    expect(insertSpy).not.toHaveBeenCalled()
    expect(await loadAllQueued()).toHaveLength(1)
  })

  it('is reentrant-safe (concurrent calls yield 1 insert)', async () => {
    await enqueueClaim(baseRow)
    let calls = 0
    const sb = mockClient(() => { calls++; return { error: null } })
    await Promise.all([
      drainQueue(sb, { online: true }),
      drainQueue(sb, { online: true }),
    ])
    expect(calls).toBe(1)
  })
})
