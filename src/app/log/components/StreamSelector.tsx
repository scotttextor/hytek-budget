'use client'

export type LogStream = 'progress' | 'variation' | 'rework'

interface Props {
  active: LogStream
  onChange: (next: LogStream) => void
}

const LABELS: Record<LogStream, string> = {
  progress: 'Progress',
  variation: 'Variation',
  rework: 'Rework',
}

export function StreamSelector({ active, onChange }: Props) {
  return (
    <div
      role="tablist"
      aria-label="Log stream"
      className="flex gap-1 rounded-full bg-gray-100 p-1"
    >
      {(Object.keys(LABELS) as LogStream[]).map((s) => {
        const isActive = s === active
        return (
          <button
            key={s}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(s)}
            className={`flex-1 rounded-full px-3 py-2 text-sm font-medium transition-colors ${
              isActive ? 'bg-hytek-yellow text-hytek-black shadow' : 'text-gray-600'
            }`}
          >
            {LABELS[s]}
          </button>
        )
      })}
    </div>
  )
}
