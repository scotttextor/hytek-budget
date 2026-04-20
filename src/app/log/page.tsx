'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { useJobState } from '@/lib/use-job-state'
import { useRecentItems } from '@/lib/use-recent-items'
import { useOfflineQueue } from '@/lib/use-offline-queue'
import { supabase } from '@/lib/supabase'
import { buildClaimRow, type ClaimPayload } from '@/lib/claim-payload'
import { enqueueClaim } from '@/lib/queue'
import type { InstallBudgetItem } from '@/lib/types'
import { JobHeader } from './components/JobHeader'
import { ItemPicker } from './components/ItemPicker'
import { ClaimInput } from './components/ClaimInput'
import { SaveConfirmation } from './components/SaveConfirmation'
import { TodaysClaimsList, type SessionClaim } from './components/TodaysClaimsList'

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

async function readGpsOrNull(): Promise<{ lat: number; lng: number; accuracyMeters: number } | null> {
  if (typeof navigator === 'undefined' || !('geolocation' in navigator)) return null
  return new Promise((resolve) => {
    const timeout = setTimeout(() => { resolve(null) }, 3000)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        clearTimeout(timeout)
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracyMeters: Math.round(pos.coords.accuracy),
        })
      },
      () => { clearTimeout(timeout); resolve(null) },
      { timeout: 3000, maximumAge: 30_000, enableHighAccuracy: false },
    )
  })
}

export default function LogPage() {
  const { user, loading: authLoading } = useAuth()
  const { job, loading: jobLoading } = useJobState()
  const router = useRouter()

  const { items: recents, refresh: refreshRecents } = useRecentItems(user?.id ?? null, job?.id ?? null)
  const { counts, drainNow } = useOfflineQueue()

  const [allItems, setAllItems] = useState<InstallBudgetItem[]>([])
  const [selected, setSelected] = useState<InstallBudgetItem | null>(null)
  const [confirmation, setConfirmation] = useState<{ offline: boolean } | null>(null)
  const [sessionClaims, setSessionClaims] = useState<SessionClaim[]>([])

  // Guard auth + job selection
  useEffect(() => {
    if (!authLoading && !user) router.replace('/login')
  }, [authLoading, user, router])
  useEffect(() => {
    if (!jobLoading && !job) router.replace('/log/pick-job')
  }, [jobLoading, job, router])

  // Load budget items for the active job
  useEffect(() => {
    if (!job) { setAllItems([]); return }
    supabase
      .from('install_budget_items')
      .select('*')
      .eq('job_id', job.id)
      .order('sort_order')
      .order('name')
      .then(({ data }) => setAllItems((data as InstallBudgetItem[]) ?? []))
  }, [job])

  const handleSave = useCallback(async (payload: ClaimPayload) => {
    if (!user || !job || !selected) return
    const gps = await readGpsOrNull()
    const row = buildClaimRow(payload, {
      userId: user.id,
      jobId: job.id,
      budgetItemId: selected.id,
      claimDate: todayIso(),
      budgetAmountDollars: selected.budget_amount,
      gps,
    })
    await enqueueClaim(row)
    // Confirmation fires OFF the IndexedDB write — per Panel #2 UX
    setSessionClaims((prev) => [
      { id: row.id, item: selected, payload, stampedAt: new Date() },
      ...prev,
    ].slice(0, 10))
    setConfirmation({ offline: typeof navigator !== 'undefined' ? !navigator.onLine : false })
    setSelected(null)
    // Kick drain in background — do NOT await
    drainNow().then(() => refreshRecents())
  }, [user, job, selected, drainNow, refreshRecents])

  if (authLoading || jobLoading || !user || !job) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-hytek-yellow border-t-transparent" />
      </div>
    )
  }

  return (
    <main className="flex flex-1 flex-col">
      <JobHeader
        job={job}
        onChange={() => router.push('/log/pick-job')}
        pendingCount={counts.pending + counts.inFlight + counts.failed}
        deadCount={counts.dead}
      />
      <SaveConfirmation
        visible={confirmation !== null}
        offline={confirmation?.offline ?? false}
        onDismiss={() => setConfirmation(null)}
      />
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {selected ? (
          <ClaimInput
            item={selected}
            onSave={handleSave}
            onCancel={() => setSelected(null)}
          />
        ) : (
          <ItemPicker
            recents={recents}
            allItems={allItems}
            onSelect={setSelected}
          />
        )}
        <TodaysClaimsList claims={sessionClaims} />
      </div>
    </main>
  )
}
