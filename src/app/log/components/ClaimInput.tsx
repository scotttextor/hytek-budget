'use client'

import { useState, useMemo } from 'react'
import type { InstallBudgetItem } from '@/lib/types'
import { unitTypeToInputMode } from '@/lib/unit-type'
import { parseAudCentsFromString } from '@/lib/money'
import type { ClaimPayload } from '@/lib/claim-payload'

interface Props {
  item: InstallBudgetItem
  onSave: (payload: ClaimPayload) => void | Promise<void>
  onCancel: () => void
  // For hours/qty: rate lookup deferred to Phase 1.x. For now, if unit_type
  // triggers hours/qty mode, we fall back to dollar mode until rate-card wiring
  // ships (Task 1 probe + follow-up task).
}

export function ClaimInput({ item, onSave, onCancel }: Props) {
  // Real schema: unit_type is often null; unit carries the billing cadence
  // ("per hour" / "per day" / "lump sum"). Prefer unit_type when set, fall
  // back to unit, then to null (→ dollar mode).
  const mode = useMemo(
    () => unitTypeToInputMode(item.unit_type ?? item.unit ?? null, {
      budgetAmountCents: item.budget_amount != null ? Math.round(item.budget_amount * 100) : null,
    }),
    [item],
  )
  // Gate hours/qty modes for Phase 1 (need rate-card wiring) — fall back to dollar
  const effectiveMode = (mode.mode === 'hours' || mode.mode === 'qty')
    ? { ...mode, mode: 'dollar' as const, label: '$ claimed', inputMode: 'decimal' as const, step: 0.01 }
    : mode

  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSave() {
    setError(null)
    try {
      let payload: ClaimPayload
      if (effectiveMode.mode === 'dollar') {
        const cents = parseAudCentsFromString(value)
        if (cents <= 0) throw new Error('Amount must be positive')
        payload = { kind: 'dollar', amountCents: cents, notes: notes || undefined }
      } else { // percent
        const pct = Number.parseFloat(value)
        if (!Number.isFinite(pct) || pct <= 0 || pct > 100) throw new Error('Enter 0–100')
        payload = { kind: 'percent', percent: pct, notes: notes || undefined }
      }
      setSubmitting(true)
      await onSave(payload)
    } catch (e: any) {
      setError(e.message ?? 'Invalid input')
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-4 rounded-2xl bg-white p-4 shadow-lg">
      <div>
        <div className="text-xs uppercase text-gray-500">{item.category}</div>
        <div className="text-lg font-semibold">{item.name ?? '(unnamed item)'}</div>
      </div>
      <label className="block">
        <span className="mb-1 block text-sm font-medium">{effectiveMode.label}</span>
        <input
          type="text"
          inputMode={effectiveMode.inputMode}
          autoFocus
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={effectiveMode.mode === 'percent' ? '0–100' : '0.00'}
        />
      </label>
      <label className="block">
        <span className="mb-1 block text-sm font-medium">Notes (optional)</span>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </label>
      {error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 rounded-lg border border-gray-300 bg-white py-3 font-semibold"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={submitting || !value.trim()}
          className="flex-1 rounded-lg bg-hytek-yellow py-3 font-semibold text-hytek-black disabled:opacity-50"
        >
          {submitting ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  )
}
