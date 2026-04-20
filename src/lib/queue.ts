// Offline claim queue stored in idb-keyval. Panel #2 Architect §1-§3:
// append-only, UUID is idempotency key, 4-state status.

import { get, set, del } from 'idb-keyval'
import type { ClaimRow } from './claim-payload'

export type QueueStatus =
  | { state: 'pending' }
  | { state: 'in_flight'; leaseUntil: number; attempts: number }
  | { state: 'failed'; attempts: number; lastError: string; nextRetryAt: number }
  | { state: 'dead'; attempts: number; lastError: string; deadAt: number }

export interface QueuedClaim {
  id: string
  kind: 'claim'
  payload: ClaimRow
  firstQueuedAt: number
  updatedAt: number
  status: QueueStatus
}

const KEY_PREFIX = 'queue:'
const INDEX_KEY = 'queue:index'

async function loadIndex(): Promise<string[]> {
  return (await get<string[]>(INDEX_KEY)) ?? []
}

async function saveIndex(ids: string[]): Promise<void> {
  await set(INDEX_KEY, ids)
}

export async function enqueueClaim(row: ClaimRow): Promise<void> {
  const now = Date.now()
  const record: QueuedClaim = {
    id: row.id,
    kind: 'claim',
    payload: row,
    firstQueuedAt: now,
    updatedAt: now,
    status: { state: 'pending' },
  }
  await set(`${KEY_PREFIX}${row.id}`, record)
  const ids = await loadIndex()
  if (!ids.includes(row.id)) {
    ids.push(row.id)
    await saveIndex(ids)
  }
}

export async function loadAllQueued(): Promise<QueuedClaim[]> {
  const ids = await loadIndex()
  const records = await Promise.all(ids.map((id) => get<QueuedClaim>(`${KEY_PREFIX}${id}`)))
  return records.filter((r): r is QueuedClaim => r !== undefined)
}

export async function removeQueued(id: string): Promise<void> {
  await del(`${KEY_PREFIX}${id}`)
  const ids = (await loadIndex()).filter((x) => x !== id)
  await saveIndex(ids)
}

export async function updateQueued(id: string, status: QueueStatus): Promise<void> {
  const key = `${KEY_PREFIX}${id}`
  const existing = await get<QueuedClaim>(key)
  if (!existing) return
  const next: QueuedClaim = { ...existing, status, updatedAt: Date.now() }
  await set(key, next)
}

// Classify a Supabase response / error into queue action.
// PostgREST error codes documented at https://postgrest.org/en/v12/errors.html
interface PgError {
  code?: string
  message?: string
}

export type Classification =
  | { kind: 'success' }
  | { kind: 'retry' }
  | { kind: 'dead'; reason: string }

export function classifyResponse(error: PgError | null, _data: unknown): Classification {
  if (!error) return { kind: 'success' }
  const code = error.code ?? ''
  const msg = error.message ?? ''
  if (code === '23505') return { kind: 'success' } // dup PK = idempotent retry
  if (code === '23503') return { kind: 'dead', reason: `fk_missing: ${msg}` }
  if (code.startsWith('22') || code.startsWith('23')) return { kind: 'dead', reason: msg || code }
  // Network / transport — Supabase-js surfaces as { message: 'Failed to fetch' }
  if (/fetch|network|timeout|abort/i.test(msg)) return { kind: 'retry' }
  // Unknown — default to retry; drain will eventually dead-letter after MAX_ATTEMPTS
  return { kind: 'retry' }
}

export const MAX_ATTEMPTS = 8

export function computeNextRetry(attempts: number, now: number = Date.now()): number {
  const base = 60_000 * 2 ** Math.max(0, attempts - 1)
  const capped = Math.min(base, 60 * 60_000)
  const jitter = 1 + (Math.random() * 0.4 - 0.2) // ±20%
  return now + Math.round(capped * jitter)
}
