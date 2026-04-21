// Minimum-viable rework payload for the mobile log-rework flow.
// Panel #2 UX: required = description + explanation + responsible_department.
// Photo goes in rework_photos (separate table) via Storage upload — handled by
// T5/T6 helpers, NOT this module. Status always starts 'identified'.

import type { JobRework, ReworkStatus, ResponsibleDepartment } from './types'

export interface ReworkPayload {
  description: string                  // UI "title"
  explanation: string                  // required details narrative
  responsibleDepartment: ResponsibleDepartment
  responsiblePerson?: string           // optional — name of subbie/person
  estimatedCostCents?: number          // optional — default 0 on save
}

export interface ReworkContext {
  userId: string
  jobId: string
  claimDate: string                    // yyyy-mm-dd
  gps?: { lat: number; lng: number; accuracyMeters: number } | null
}

export type ReworkRow = Omit<JobRework, 'created_at'>

function newUuidV4(): string {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID()
  }
  const b = globalThis.crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const hex = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function generateReworkNumber(uuid: string, claimDate: string): string {
  const yyyymmdd = claimDate.slice(0, 10).replace(/-/g, '')
  const suffix = uuid.replace(/-/g, '').slice(0, 4).toLowerCase()
  return `R-${yyyymmdd}-${suffix}`
}

/**
 * Set affects_* booleans from responsible_department.
 * 'other' falls through — no department flagged. Supervisor can edit later.
 */
function affectsFor(dept: ResponsibleDepartment) {
  return {
    affects_detailing: dept === 'detailing',
    affects_dispatch: dept === 'dispatch',
    affects_install: dept === 'install',
    affects_fabrication: dept === 'fabrication',
  }
}

export function buildReworkRow(p: ReworkPayload, ctx: ReworkContext): ReworkRow {
  const id = newUuidV4()
  const estimated = p.estimatedCostCents != null ? p.estimatedCostCents / 100 : 0
  const status: ReworkStatus = 'identified'
  return {
    id,
    job_id: ctx.jobId,
    rework_number: generateReworkNumber(id, ctx.claimDate),
    description: p.description,
    explanation: p.explanation,
    responsible_department: p.responsibleDepartment,
    responsible_person: p.responsiblePerson ?? null,
    estimated_cost: estimated,
    actual_cost: 0,
    status,
    ...affectsFor(p.responsibleDepartment),
    captured_at: new Date().toISOString(),
    captured_lat: ctx.gps?.lat ?? null,
    captured_lng: ctx.gps?.lng ?? null,
    captured_accuracy_m: ctx.gps?.accuracyMeters ?? null,
    created_by: ctx.userId,
  }
}
