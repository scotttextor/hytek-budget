'use client'

import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'
import type { Job } from './types'

const STORAGE_KEY = 'hytek-budget:lastJobId'

export function useJobState() {
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)

  const loadJob = useCallback(async (jobId: string) => {
    const { data } = await supabase.from('jobs').select('*').eq('id', jobId).maybeSingle()
    if (data) setJob(data as Job)
  }, [])

  useEffect(() => {
    const stored = typeof window !== 'undefined' ? window.localStorage.getItem(STORAGE_KEY) : null
    if (stored) {
      loadJob(stored).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [loadJob])

  const selectJob = useCallback((next: Job) => {
    setJob(next)
    window.localStorage.setItem(STORAGE_KEY, next.id)
  }, [])

  const clearJob = useCallback(() => {
    setJob(null)
    window.localStorage.removeItem(STORAGE_KEY)
  }, [])

  return { job, loading, selectJob, clearJob }
}
