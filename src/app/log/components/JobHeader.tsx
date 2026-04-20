'use client'

import type { Job } from '@/lib/types'

interface Props {
  job: Job
  onChange: () => void
  pendingCount: number
  deadCount: number
}

export function JobHeader({ job, onChange, pendingCount, deadCount }: Props) {
  return (
    <header className="flex items-center justify-between gap-2 border-b border-gray-200 bg-white px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="truncate text-base font-semibold text-hytek-black">{job.name}</div>
        <div className="truncate text-xs text-gray-500">#{job.job_number}</div>
      </div>
      {pendingCount > 0 && (
        <div
          aria-label={`${pendingCount} pending logs`}
          className={`relative rounded-full px-2 py-1 text-xs font-semibold ${
            deadCount > 0 ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-700'
          }`}
        >
          {pendingCount} pending
          {deadCount > 0 && (
            <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-red-600" />
          )}
        </div>
      )}
      <button
        type="button"
        onClick={onChange}
        className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs"
      >
        Change job
      </button>
    </header>
  )
}
