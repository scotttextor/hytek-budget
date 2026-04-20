'use client'

import type { InstallBudgetItem } from '@/lib/types'
import type { ClaimPayload } from '@/lib/claim-payload'
import { formatAud, type Money } from '@/lib/money'

export interface SessionClaim {
  id: string
  item: InstallBudgetItem
  payload: ClaimPayload
  stampedAt: Date
}

interface Props {
  claims: SessionClaim[]
}

function describeClaim(p: ClaimPayload): string {
  switch (p.kind) {
    case 'dollar': return formatAud(p.amountCents as Money)
    case 'percent': return `${p.percent}%`
    case 'hours': return `${p.hours} h @ $${p.rateUsed}/h`
    case 'qty': return `${p.qty} × $${p.rateUsed}`
  }
}

const TIME_FORMAT = new Intl.DateTimeFormat('en-AU', { hour: 'numeric', minute: '2-digit' })

export function TodaysClaimsList({ claims }: Props) {
  if (claims.length === 0) return null
  return (
    <section className="space-y-2">
      <h3 className="text-xs uppercase tracking-wide text-gray-500">Today's claims</h3>
      <ul className="space-y-2">
        {claims.map((c) => (
          <li key={c.id} className="rounded-xl bg-white px-3 py-2 text-sm shadow">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate">{c.item.name ?? c.item.category}</span>
              <span className="shrink-0 font-semibold">{describeClaim(c.payload)}</span>
            </div>
            <div className="text-xs text-gray-500">{TIME_FORMAT.format(c.stampedAt)}</div>
          </li>
        ))}
      </ul>
    </section>
  )
}
