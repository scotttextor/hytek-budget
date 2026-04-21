import { describe, it, expect } from 'vitest'
import { buildPhotoStoragePath, buildReworkPhotoRow } from './photo'

describe('buildPhotoStoragePath', () => {
  it('produces userId/YYYYMM/reworkId.jpg', () => {
    const p = buildPhotoStoragePath('user-123', 'rw-uuid-abc', '2026-04-20')
    expect(p).toBe('user-123/202604/rw-uuid-abc.jpg')
  })

  it('pads single-digit months', () => {
    expect(buildPhotoStoragePath('u', 'r', '2026-01-05')).toBe('u/202601/r.jpg')
  })

  it('accepts an ISO timestamp as well as a date-only string', () => {
    expect(buildPhotoStoragePath('u', 'r', '2026-04-20T07:35:53.351Z')).toBe('u/202604/r.jpg')
  })
})

describe('buildReworkPhotoRow', () => {
  it('returns the rework_photos insert shape', () => {
    const row = buildReworkPhotoRow('rw-uuid', 'user-123/202604/rw-uuid.jpg', 'site.jpg')
    expect(row.rework_id).toBe('rw-uuid')
    expect(row.storage_path).toBe('user-123/202604/rw-uuid.jpg')
    expect(row.file_name).toBe('site.jpg')
  })
})
