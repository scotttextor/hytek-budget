// drain() — iterates queued records, dispatches to Supabase, updates status.
// Architect §2: guarded by in-memory flag + in_flight lease for cross-tab.

import type { SupabaseClient } from '@supabase/supabase-js'
import {
  loadAllQueued, removeQueued, updateQueued,
  classifyResponse, computeNextRetry, MAX_ATTEMPTS,
  type QueuedMutation,
} from './queue'

// Keep back-compat alias used by existing callers that import QueuedClaim
export type { QueuedMutation as QueuedClaim }

const LEASE_MS = 30_000
let draining = false

interface DrainOptions {
  online?: boolean // override for tests / non-browser
}

function isReady(r: QueuedMutation, now: number): boolean {
  const s = r.status
  if (s.state === 'pending') return true
  if (s.state === 'failed') return s.nextRetryAt <= now
  if (s.state === 'in_flight') return s.leaseUntil < now // prior drain crashed
  return false // dead
}

// Dispatches a single queued record to Supabase.
// rework_with_photo runs a 3-step flow (storage → rework row → photos row),
// all other kinds do a straight insert into record.table.
// Each step is idempotent: Storage 409 (already exists) and Postgres 23505
// (duplicate PK) are treated as success so retries don't abort the sequence.
async function executeMutation(
  supabase: SupabaseClient,
  record: QueuedMutation,
): Promise<{ error: { code?: string; message?: string } | null }> {
  try {
    if (record.kind === 'rework_with_photo') {
      // Step 1: upload blob to Storage. Deterministic path — retries hit the
      // same object. Supabase returns 409 on conflict, which we treat as
      // success (idempotent replay).
      const up = await supabase.storage
        .from('install-photos')
        .upload(record.photo.storagePath, record.photo.blob, {
          contentType: 'image/jpeg',
          upsert: false,
        })
      if (up.error) {
        const msg = (up.error as any).message ?? ''
        // 'already exists' / 'duplicate' => treat as success (already uploaded on prior attempt)
        if (!/exists|duplicate/i.test(msg)) {
          return { error: { message: `storage: ${msg}` } }
        }
      }

      // Step 2: insert the rework row
      const ins = await supabase.from('job_rework').insert(record.payload)
      if (ins.error) {
        // Unique PK violation (23505) = rework already inserted on prior attempt — treat as success
        if ((ins.error as any).code !== '23505') return { error: ins.error as any }
      }

      // Step 3: insert rework_photos row linking the two
      const photoRow = {
        rework_id: record.payload.id,
        storage_path: record.photo.storagePath,
        file_name: record.photo.fileName,
      }
      const photoIns = await supabase.from('rework_photos').insert(photoRow)
      if (photoIns.error) {
        // 23505 = already inserted on prior attempt
        if ((photoIns.error as any).code !== '23505') return { error: photoIns.error as any }
      }
      return { error: null }
    }

    // All other kinds: straight insert into record.table
    const res = await supabase.from(record.table).insert(record.payload)
    return { error: (res.error as any) ?? null }
  } catch (e: any) {
    return { error: { message: e?.message ?? String(e) } }
  }
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
      await updateQueued(record.id, {
        state: 'in_flight',
        leaseUntil: Date.now() + LEASE_MS,
        attempts: priorAttempts(record),
      })

      const { error } = await executeMutation(supabase, record)

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
          lastError: `max_attempts (last: ${error?.message ?? 'unknown'})`,
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

function priorAttempts(r: QueuedMutation): number {
  if (r.status.state === 'failed' || r.status.state === 'dead' || r.status.state === 'in_flight') return r.status.attempts
  return 0
}
