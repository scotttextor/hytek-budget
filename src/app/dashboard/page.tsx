'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

export default function DashboardPage() {
  const { user, profile, loading, signOut } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) router.replace('/login')
  }, [user, loading, router])

  if (loading || !user) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-hytek-yellow border-t-transparent" />
      </div>
    )
  }

  return (
    <main className="flex-1 p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-hytek-black">HYTEK Budget</h1>
          <p className="text-sm text-gray-500">
            Signed in as {profile?.full_name ?? user.email} ({profile?.role ?? 'unknown role'})
          </p>
        </div>
        <button
          onClick={() => signOut()}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm"
        >
          Sign out
        </button>
      </header>

      <section className="rounded-2xl bg-white p-6 shadow">
        <h2 className="mb-2 text-lg font-semibold">Phase 0 — Bootstrap check</h2>
        <p className="text-sm text-gray-600">
          If you&apos;re reading this, auth and Supabase are wired up. Phase 1
          (mobile Quick-Log) is next.
        </p>
      </section>
    </main>
  )
}
