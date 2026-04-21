'use client'

import { useRef, useState } from 'react'
import { parseAudCentsFromString } from '@/lib/money'
import type { ReworkPayload } from '@/lib/rework-payload'
import type { ResponsibleDepartment } from '@/lib/types'

interface Props {
  onSave: (payload: ReworkPayload, photo: File) => void | Promise<void>
  onCancel: () => void
}

const DEPT_OPTIONS: Array<{ value: ResponsibleDepartment; label: string }> = [
  { value: 'install', label: 'Install' },
  { value: 'detailing', label: 'Detailing' },
  { value: 'dispatch', label: 'Dispatch' },
  { value: 'fabrication', label: 'Fabrication' },
  { value: 'other', label: 'Other' },
]

export function ReworkInput({ onSave, onCancel }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [photo, setPhoto] = useState<File | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [description, setDescription] = useState('')
  const [explanation, setExplanation] = useState('')
  const [responsibleDepartment, setResponsibleDepartment] = useState<ResponsibleDepartment>('install')
  const [estimatedCost, setEstimatedCost] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function onFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setPhoto(file)
    if (photoPreview) URL.revokeObjectURL(photoPreview)
    setPhotoPreview(URL.createObjectURL(file))
  }

  async function handleSave() {
    setError(null)
    try {
      if (!photo) throw new Error('Photo required — tap the camera to capture')
      const desc = description.trim()
      if (!desc) throw new Error('Short title is required')
      const exp = explanation.trim()
      if (!exp) throw new Error('Explanation is required')
      let estCents: number | undefined
      if (estimatedCost.trim()) {
        estCents = parseAudCentsFromString(estimatedCost)
        if (estCents < 0) throw new Error('Cost must be positive or blank')
      }
      setSubmitting(true)
      await onSave(
        {
          description: desc,
          explanation: exp,
          responsibleDepartment,
          estimatedCostCents: estCents,
        },
        photo,
      )
    } catch (e: any) {
      setError(e.message ?? 'Invalid input')
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-4 rounded-2xl bg-white p-4 shadow-lg">
      <div className="text-xs uppercase text-gray-500">New rework</div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={onFilePicked}
        className="hidden"
      />

      {photoPreview ? (
        <div className="relative overflow-hidden rounded-xl bg-gray-100">
          <img src={photoPreview} alt="Rework photo" className="h-48 w-full object-cover" />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="absolute right-2 top-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium shadow"
          >
            Retake
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex h-48 w-full items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 text-sm font-medium text-gray-600"
        >
          📷  Tap to take photo
        </button>
      )}

      <label className="block">
        <span className="mb-1 block text-sm font-medium">Short title</span>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="e.g. Fix misaligned stud"
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-sm font-medium">What happened</span>
        <input
          type="text"
          value={explanation}
          onChange={(e) => setExplanation(e.target.value)}
          placeholder="e.g. Stud rotated 180° during framing"
        />
      </label>

      <label className="block">
        <span className="mb-1 block text-sm font-medium">Responsible department</span>
        <select
          value={responsibleDepartment}
          onChange={(e) => setResponsibleDepartment(e.target.value as ResponsibleDepartment)}
        >
          {DEPT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="mb-1 block text-sm font-medium">Estimated cost (optional)</span>
        <input
          type="text"
          inputMode="decimal"
          value={estimatedCost}
          onChange={(e) => setEstimatedCost(e.target.value)}
          placeholder="0.00"
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
          disabled={submitting || !photo || !description.trim() || !explanation.trim()}
          className="flex-1 rounded-lg bg-hytek-yellow py-3 font-semibold text-hytek-black disabled:opacity-50"
        >
          {submitting ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  )
}
