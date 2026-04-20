// drain() — iterates queued records, dispatches to Supabase, updates status.
// Architect §2: guarded by in-memory flag + in_flight lease for cross-tab.

import type { SupabaseClient } from '@supabase/supabase-js'
import {
  loadAllQueued, removeQueued, updateQueued,
  classifyResponse, computeNextRetry, MAX_ATTEMPTS,
  type QueuedClaim,
} from './queue'

const LEASE_MS = 30_000
let draining = false

interface DrainOptions {
  online?: boolean // override for tests / non-browser
}

function isReady(r: QueuedClaim, now: number): boolean {
  const s = r.status
  if (s.state === 'pending') return true
  if (s.state === 'failed') return s.nextRetryAt <= now
  if (s.state === 'in_flight') return s.leaseUntil < now // prior drain crashed
  return false // dead
}

export async function drainQueue(
  supabase: SupabaseClient,
  opts: DrainOptions = {},
): Promise<void> {
  const online = opts.online ?? (typeof navigator !== 'undefined' ? navigator.onLine : true)
  if (!online) return
  if (draining) return
  draining = true
  try {
    const now = Date.now()
    const records = (await loadAllQueued()).filter((r) => isReady(r, now))

    for (const record of records) {
      await updateQueued(record.id, { state: 'in_flight', leaseUntil: Date.now() + LEASE_MS })

      let error: { code?: string; message?: string } | null = null
      try {
        const res = await supabase.from('install_claims').insert(record.payload)
        error = res.error as any
      } catch (e: any) {
        error = { message: e?.message ?? String(e) }
      }

      const cls = classifyResponse(error, null)
      if (cls.kind === 'success') {
        await removeQueued(record.id)
        continue
      }
      if (cls.kind === 'dead') {
        await updateQueued(record.id, {
          state: 'dead',
          attempts: priorAttempts(record) + 1,
          lastError: cls.reason,
          deadAt: Date.now(),
        })
        continue
      }
      // retry
      const attempts = priorAttempts(record) + 1
      if (attempts >= MAX_ATTEMPTS) {
        await updateQueued(record.id, {
          state: 'dead',
          attempts,
          lastError: error?.message ?? 'max_attempts',
          deadAt: Date.now(),
        })
      } else {
        await updateQueued(record.id, {
          state: 'failed',
          attempts,
          lastError: error?.message ?? 'unknown',
          nextRetryAt: computeNextRetry(attempts),
        })
      }
    }
  } finally {
    draining = false
  }
}

function priorAttempts(r: QueuedClaim): number {
  if (r.status.state === 'failed' || r.status.state === 'dead') return r.status.attempts
  return 0
}
