'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { useJobState } from '@/lib/use-job-state'
import { useRecentItems } from '@/lib/use-recent-items'
import { useOfflineQueue } from '@/lib/use-offline-queue'
import { supabase } from '@/lib/supabase'
import { buildClaimRow, type ClaimPayload } from '@/lib/claim-payload'
import { buildVariationRow, type VariationPayload } from '@/lib/variation-payload'
import { buildReworkRow, type ReworkPayload } from '@/lib/rework-payload'
import { enqueueClaim, enqueueMutation } from '@/lib/queue'
import { resizeImageToBlob, buildPhotoStoragePath } from '@/lib/photo'
import type { InstallBudgetItem } from '@/lib/types'
import { JobHeader } from './components/JobHeader'
import { ItemPicker } from './components/ItemPicker'
import { ClaimInput } from './components/ClaimInput'
import { SaveConfirmation } from './components/SaveConfirmation'
import { TodaysClaimsList, type SessionClaim } from './components/TodaysClaimsList'
import { StreamSelector, type LogStream } from './components/StreamSelector'
import { VariationInput } from './components/VariationInput'
import { ReworkInput } from './components/ReworkInput'

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

  const [stream, setStream] = useState<LogStream>('progress')
  const [allItems, setAllItems] = useState<InstallBudgetItem[]>([])
  const [selected, setSelected] = useState<InstallBudgetItem | null>(null)
  const [confirmation, setConfirmation] = useState<{ offline: boolean } | null>(null)
  const [sessionClaims, setSessionClaims] = useState<SessionClaim[]>([])

  useEffect(() => {
    if (!authLoading && !user) router.replace('/login')
  }, [authLoading, user, router])
  useEffect(() => {
    if (!jobLoading && !job) router.replace('/log/pick-job')
  }, [jobLoading, job, router])

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

  // Clear form state when stream changes so no stale selection leaks
  useEffect(() => {
    setSelected(null)
  }, [stream])

  const fireConfirmationAndDrain = useCallback(() => {
    setConfirmation({ offline: typeof navigator !== 'undefined' ? !navigator.onLine : false })
    drainNow().then(() => refreshRecents())
  }, [drainNow, refreshRecents])

  const handleSaveProgress = useCallback(async (payload: ClaimPayload) => {
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
    setSessionClaims((prev) => [
      { id: row.id, item: selected, payload, stampedAt: new Date() },
      ...prev,
    ].slice(0, 10))
    setSelected(null)
    fireConfirmationAndDrain()
  }, [user, job, selected, fireConfirmationAndDrain])

  const handleSaveVariation = useCallback(async (payload: VariationPayload) => {
    if (!user || !job) return
    const gps = await readGpsOrNull()
    const row = buildVariationRow(payload, {
      userId: user.id,
      jobId: job.id,
      claimDate: todayIso(),
      gps,
    })
    await enqueueMutation({
      id: row.id,
      kind: 'variation',
      table: 'job_variations',
      // VariationRow.status is VariationState; queue union requires literal 'raised'.
      // buildVariationRow always sets status:'raised' — cast is safe.
      payload: row as typeof row & { status: 'raised' },
    })
    fireConfirmationAndDrain()
    setStream('progress') // hop back so the next action starts from Progress
  }, [user, job, fireConfirmationAndDrain])

  const handleSaveRework = useCallback(async (payload: ReworkPayload, photo: File) => {
    if (!user || !job) return
    const gps = await readGpsOrNull()
    const resized = await resizeImageToBlob(photo)
    const row = buildReworkRow(payload, {
      userId: user.id,
      jobId: job.id,
      claimDate: todayIso(),
      gps,
    })
    const storagePath = buildPhotoStoragePath(user.id, row.id, todayIso())
    await enqueueMutation({
      id: row.id,
      kind: 'rework_with_photo',
      table: 'job_rework',
      // ReworkRow.status is ReworkStatus; queue union requires literal 'identified'.
      // buildReworkRow always sets status:'identified' — cast is safe.
      payload: row as typeof row & { status: 'identified' },
      photo: { blob: resized, storagePath, fileName: photo.name },
    })
    fireConfirmationAndDrain()
    setStream('progress')
  }, [user, job, fireConfirmationAndDrain])

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
        <StreamSelector active={stream} onChange={setStream} />

        {stream === 'progress' && (
          <>
            {selected ? (
              <ClaimInput
                item={selected}
                onSave={handleSaveProgress}
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
          </>
        )}

        {stream === 'variation' && (
          <VariationInput
            onSave={handleSaveVariation}
            onCancel={() => setStream('progress')}
          />
        )}

        {stream === 'rework' && (
          <ReworkInput
            onSave={handleSaveRework}
            onCancel={() => setStream('progress')}
          />
        )}
      </div>
    </main>
  )
}
