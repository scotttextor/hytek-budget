import { describe, it, expect } from 'vitest'
import { buildReworkRow, generateReworkNumber, type ReworkPayload } from './rework-payload'

const base = {
  userId: 'user-uuid',
  jobId: 'job-uuid',
  claimDate: '2026-04-20',
}

describe('generateReworkNumber', () => {
  it('produces R-YYYYMMDD-xxxx from uuid + date', () => {
    expect(generateReworkNumber('a3f28b45-1111-4000-a000-000000000000', '2026-04-20')).toBe('R-20260420-a3f2')
  })
  it('is deterministic', () => {
    const a = generateReworkNumber('a3f28b45-1111-4000-a000-000000000000', '2026-04-20')
    const b = generateReworkNumber('a3f28b45-1111-4000-a000-000000000000', '2026-04-20')
    expect(a).toBe(b)
  })
})

describe('buildReworkRow', () => {
  it('builds a minimum-viable row', () => {
    const p: ReworkPayload = {
      description: 'Fix misaligned stud',
      explanation: 'Stud rotated 180° during framing',
      responsibleDepartment: 'install',
    }
    const row = buildReworkRow(p, base)
    expect(row.description).toBe('Fix misaligned stud')
    expect(row.explanation).toBe('Stud rotated 180° during framing')
    expect(row.responsible_department).toBe('install')
    expect(row.status).toBe('identified')
    expect(row.estimated_cost).toBe(0)
    expect(row.actual_cost).toBe(0)
    expect(row.responsible_person).toBeNull()
    expect(row.rework_number).toMatch(/^R-20260420-[0-9a-f]{4}$/)
    expect(row.id.length).toBeGreaterThan(30)
    expect(row.captured_at).toBeTruthy()
  })

  it('captures estimatedCostCents → dollars', () => {
    const row = buildReworkRow(
      {
        description: 'x',
        explanation: 'y',
        responsibleDepartment: 'detailing',
        estimatedCostCents: 45050,
      },
      base,
    )
    expect(row.estimated_cost).toBe(450.5)
  })

  it('captures responsiblePerson', () => {
    const row = buildReworkRow(
      {
        description: 'x',
        explanation: 'y',
        responsibleDepartment: 'other',
        responsiblePerson: 'Dave the subbie',
      },
      base,
    )
    expect(row.responsible_person).toBe('Dave the subbie')
  })

  it('stamps GPS when provided', () => {
    const row = buildReworkRow(
      { description: 'x', explanation: 'y', responsibleDepartment: 'install' },
      { ...base, gps: { lat: -27.45, lng: 153.02, accuracyMeters: 5 } },
    )
    expect(row.captured_lat).toBe(-27.45)
    expect(row.captured_accuracy_m).toBe(5)
  })

  it('produces distinct UUIDs + numbers across calls', () => {
    const a = buildReworkRow({ description: 'x', explanation: 'y', responsibleDepartment: 'install' }, base)
    const b = buildReworkRow({ description: 'x', explanation: 'y', responsibleDepartment: 'install' }, base)
    expect(a.id).not.toBe(b.id)
    expect(a.rework_number).not.toBe(b.rework_number)
  })

  it('sets affects_* booleans based on responsible_department', () => {
    const row = buildReworkRow(
      { description: 'x', explanation: 'y', responsibleDepartment: 'detailing' },
      base,
    )
    expect(row.affects_detailing).toBe(true)
    expect(row.affects_install).toBe(false)
  })
})
