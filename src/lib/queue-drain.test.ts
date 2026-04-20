import { describe, it, expect, beforeEach, vi } from 'vitest'
import { enqueueClaim, enqueueMutation, loadAllQueued, updateQueued } from './queue'
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

function mockClient(responder: (op: { table?: string; storage?: string; row?: any; blob?: Blob }) => { error: { code?: string; message?: string } | null }) {
  return {
    from(table: string) {
      return {
        async insert(payload: any) {
          return { error: responder({ table, row: payload }).error, data: null }
        },
      }
    },
    storage: {
      from(bucket: string) {
        return {
          async upload(_path: string, blob: Blob) {
            return { error: responder({ storage: bucket, blob }).error, data: null }
          },
        }
      },
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

  it('preserves attempts count through in_flight recovery', async () => {
    // Simulate a record whose prior drain attempt crashed mid-flight:
    // set it directly to in_flight with 3 prior attempts and an expired lease
    await enqueueClaim(baseRow)
    await updateQueued(baseRow.id, {
      state: 'in_flight',
      leaseUntil: Date.now() - 1000, // expired 1s ago
      attempts: 3,
    })
    const sb = mockClient(() => ({ error: { message: 'Failed to fetch' } }))
    await drainQueue(sb, { online: true })
    const all = await loadAllQueued()
    expect(all).toHaveLength(1)
    expect(all[0].status.state).toBe('failed')
    if (all[0].status.state === 'failed') {
      expect(all[0].status.attempts).toBe(4) // 3 prior + 1 new attempt
    }
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

  it('drains a variation row to job_variations', async () => {
    await enqueueMutation({
      id: 'v-1',
      kind: 'variation',
      table: 'job_variations',
      payload: {
        id: 'v-1',
        job_id: 'j',
        variation_number: 'V-20260420-0001',
        description: 'Extra wall',
        status: 'raised',
      },
    })
    const tables: string[] = []
    const sb = mockClient((op) => {
      if (op.table) tables.push(op.table)
      return { error: null }
    })
    await drainQueue(sb, { online: true })
    expect(tables).toEqual(['job_variations'])
    expect(await loadAllQueued()).toHaveLength(0)
  })

  it('drains a rework_with_photo — storage upload, then rework insert, then rework_photos insert', async () => {
    const blob = new Blob(['fake-jpeg'], { type: 'image/jpeg' })
    await enqueueMutation({
      id: 'r-1',
      kind: 'rework_with_photo',
      table: 'job_rework',
      payload: {
        id: 'r-1',
        job_id: 'j',
        rework_number: 'R-20260420-0001',
        description: 'Fix corner',
        explanation: 'Stud misaligned',
        responsible_department: 'install',
        status: 'identified',
      },
      photo: { blob, storagePath: 'u/202604/r-1.jpg', fileName: 'site.jpg' },
    })

    const order: string[] = []
    const sb = mockClient((op) => {
      if (op.storage) order.push(`storage:${op.storage}`)
      if (op.table) order.push(`insert:${op.table}`)
      return { error: null }
    })
    await drainQueue(sb, { online: true })
    expect(order).toEqual(['storage:install-photos', 'insert:job_rework', 'insert:rework_photos'])
    expect(await loadAllQueued()).toHaveLength(0)
  })
})
