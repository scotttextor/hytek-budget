'use client'

import { useState } from 'react'
import { parseAudCentsFromString } from '@/lib/money'
import type { VariationPayload } from '@/lib/variation-payload'

interface Props {
  onSave: (payload: VariationPayload) => void | Promise<void>
  onCancel: () => void
}

export function VariationInput({ onSave, onCancel }: Props) {
  const [description, setDescription] = useState('')
  const [poReference, setPoReference] = useState('')
  const [estimatedCost, setEstimatedCost] = useState('')
  const [reason, setReason] = useState('')
  const [showReason, setShowReason] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSave() {
    setError(null)
    try {
      const desc = description.trim()
      if (!desc) throw new Error('Title is required')
      const po = poReference.trim()
      if (!po) throw new Error('PO reference is required — no PO, no save')
      const cents = parseAudCentsFromString(estimatedCost)
      if (cents <= 0) throw new Error('Estimated cost must be positive')
      setSubmitting(true)
      await onSave({
        description: desc,
        poReference: po,
        estimatedCostCents: cents,
        reason: reason.trim() || undefined,
      })
    } catch (e: any) {
      setError(e.message ?? 'Invalid input')
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-4 rounded-2xl bg-white p-4 shadow-lg">
      <div className="text-xs uppercase text-gray-500">New variation</div>

      <label className="block">
        <span className="mb-1 block text-sm font-medium">PO reference</span>
        <input
          type="text"
          autoFocus
          value={poReference}
          onChange={(e) => setPoReference(e.target.value)}
          placeholder="PO-12345"
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-sm font-medium">Title</span>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="e.g. Extra wall on unit 4"
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-sm font-medium">Estimated cost</span>
        <input
          type="text"
          inputMode="decimal"
          value={estimatedCost}
          onChange={(e) => setEstimatedCost(e.target.value)}
          placeholder="0.00"
        />
      </label>

      {!showReason ? (
        <button
          type="button"
          onClick={() => setShowReason(true)}
          className="text-sm text-gray-500 underline"
        >
          Add detail
        </button>
      ) : (
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Detail (optional)</span>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
      )}

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
          disabled={submitting || !poReference.trim() || !description.trim() || !estimatedCost.trim()}
          className="flex-1 rounded-lg bg-hytek-yellow py-3 font-semibold text-hytek-black disabled:opacity-50"
        >
          {submitting ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  )
}
