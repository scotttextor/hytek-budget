'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

export default function RootPage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (loading) return
    if (user) {
      router.replace('/dashboard')
    } else {
      router.replace('/login')
    }
  }, [user, loading, router])

  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-hytek-yellow border-t-transparent" />
    </div>
  )
}
