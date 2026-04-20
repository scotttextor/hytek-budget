'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/lib/auth-context'
import type { Job } from '@/lib/types'

const STORAGE_KEY = 'hytek-budget:lastJobId'

export default function PickJobPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [jobs, setJobs] = useState<Job[]>([])
  const [query, setQuery] = useState('')

  useEffect(() => {
    if (!loading && !user) router.replace('/login')
  }, [loading, user, router])

  useEffect(() => {
    supabase
      .from('jobs')
      .select('*')
      .eq('install_status', 'active')
      .order('created_at', { ascending: false })
      .limit(50)
      .then(({ data }) => setJobs((data as Job[]) ?? []))
  }, [])

  function select(j: Job) {
    window.localStorage.setItem(STORAGE_KEY, j.id)
    router.replace('/log')
  }

  const filtered = query
    ? jobs.filter((j) =>
        j.name.toLowerCase().includes(query.toLowerCase()) ||
        j.job_number.toLowerCase().includes(query.toLowerCase()),
      )
    : jobs

  return (
    <main className="flex-1 p-4">
      <h1 className="mb-4 text-xl font-semibold text-hytek-black">Pick job</h1>
      <input
        type="text"
        placeholder="Search jobs…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="mb-4"
      />
      <ul className="space-y-2">
        {filtered.map((j) => (
          <li key={j.id}>
            <button
              type="button"
              onClick={() => select(j)}
              className="w-full rounded-xl bg-white p-3 text-left shadow"
            >
              <div className="font-semibold">{j.name}</div>
              <div className="text-xs text-gray-500">#{j.job_number}</div>
            </button>
          </li>
        ))}
        {filtered.length === 0 && (
          <li className="py-8 text-center text-sm text-gray-500">No jobs match.</li>
        )}
      </ul>
    </main>
  )
}
