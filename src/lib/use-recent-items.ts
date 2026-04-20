'use client'

import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'
import type { InstallBudgetItem } from './types'

export interface RecentItem {
  budgetItem: InstallBudgetItem
  lastLoggedAt: string // captured_at ISO
}

// Returns up to 5 budget items this user has logged against on this job within
// the last 7 days, most-recent first. Server-side aggregation keeps this cheap.
export function useRecentItems(userId: string | null, jobId: string | null) {
  const [items, setItems] = useState<RecentItem[]>([])
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    if (!userId || !jobId) { setItems([]); return }
    setLoading(true)
    try {
      const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60_000).toISOString()
      const { data: claims } = await supabase
        .from('install_claims')
        .select('budget_item_id, captured_at')
        .eq('created_by', userId)
        .eq('job_id', jobId)
        .gte('captured_at', sevenDaysAgo)
        .order('captured_at', { ascending: false })

      if (!claims || claims.length === 0) { setItems([]); return }

      // Dedupe by budget_item_id keeping first (= most recent)
      const seen = new Map<string, string>()
      for (const c of claims as { budget_item_id: string; captured_at: string }[]) {
        if (!seen.has(c.budget_item_id)) seen.set(c.budget_item_id, c.captured_at)
        if (seen.size >= 5) break
      }

      const ids = Array.from(seen.keys())
      const { data: budgetItems } = await supabase
        .from('install_budget_items')
        .select('*')
        .in('id', ids)

      const byId = new Map<string, InstallBudgetItem>()
      for (const b of (budgetItems ?? []) as InstallBudgetItem[]) byId.set(b.id, b)

      const ordered: RecentItem[] = ids
        .map((id) => {
          const bi = byId.get(id)
          if (!bi) return null
          return { budgetItem: bi, lastLoggedAt: seen.get(id)! }
        })
        .filter((x): x is RecentItem => x !== null)

      setItems(ordered)
    } finally {
      setLoading(false)
    }
  }, [userId, jobId])

  useEffect(() => { refresh() }, [refresh])

  return { items, loading, refresh }
}
