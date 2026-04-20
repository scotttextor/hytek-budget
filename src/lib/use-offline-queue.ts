'use client'

import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'
import { loadAllQueued, type QueuedClaim } from './queue'
import { drainQueue } from './queue-drain'

export interface QueueCounts {
  pending: number
  inFlight: number
  failed: number
  dead: number
  total: number
}

function countStatus(records: QueuedClaim[]): QueueCounts {
  const counts = { pending: 0, inFlight: 0, failed: 0, dead: 0, total: records.length }
  for (const r of records) {
    switch (r.status.state) {
      case 'pending': counts.pending++; break
      case 'in_flight': counts.inFlight++; break
      case 'failed': counts.failed++; break
      case 'dead': counts.dead++; break
    }
  }
  return counts
}

export function useOfflineQueue() {
  const [counts, setCounts] = useState<QueueCounts>({ pending: 0, inFlight: 0, failed: 0, dead: 0, total: 0 })

  const refresh = useCallback(async () => {
    const all = await loadAllQueued()
    setCounts(countStatus(all))
  }, [])

  const drainNow = useCallback(async () => {
    await drainQueue(supabase)
    await refresh()
  }, [refresh])

  useEffect(() => {
    refresh()
    const onVisible = () => { if (document.visibilityState === 'visible') drainNow() }
    const onOnline = () => drainNow()
    const onAuth = supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_IN') drainNow()
    })
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('online', onOnline)
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') drainNow()
    }, 60_000)

    return () => {
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('online', onOnline)
      onAuth.data.subscription.unsubscribe()
      clearInterval(interval)
    }
  }, [drainNow, refresh])

  return { counts, drainNow, refresh }
}
