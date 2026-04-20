// Photo helpers for the rework-with-photo flow. Panel #2 Architect §5:
// client-resize to 1600px / JPEG 0.75 before queueing the Blob, use a
// deterministic path so retries hit the same object, keep rework_photos
// row construction thin.

export interface ResizeOptions {
  maxEdgePx?: number  // default 1600
  quality?: number    // default 0.75 (JPEG)
}

/**
 * Resize an image File/Blob to a JPEG Blob, longest edge <= maxEdgePx.
 * Browser-only (uses createImageBitmap + OffscreenCanvas). Callers must not
 * run this in Node. Preserves EXIF orientation via imageOrientation.
 */
export async function resizeImageToBlob(
  file: Blob,
  opts: ResizeOptions = {},
): Promise<Blob> {
  const maxEdge = opts.maxEdgePx ?? 1600
  const quality = opts.quality ?? 0.75

  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  const { width, height } = bitmap
  const scale = Math.min(1, maxEdge / Math.max(width, height))
  const targetW = Math.round(width * scale)
  const targetH = Math.round(height * scale)

  const canvas = new OffscreenCanvas(targetW, targetH)
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Failed to acquire 2D context for image resize')
  ctx.drawImage(bitmap, 0, 0, targetW, targetH)
  bitmap.close()

  return await canvas.convertToBlob({ type: 'image/jpeg', quality })
}

/**
 * Deterministic Storage path. Retries hit the same object — Storage returns
 * 409 on conflict which the drain logic treats as idempotent success
 * (equivalent to install_claims 23505 path).
 */
export function buildPhotoStoragePath(
  userId: string,
  reworkId: string,
  isoDateOrDate: string,
): string {
  const datePart = isoDateOrDate.slice(0, 10) // YYYY-MM-DD
  const [y, m] = datePart.split('-')
  return `${userId}/${y}${m}/${reworkId}.jpg`
}

/**
 * Row to insert into rework_photos after the Storage upload + job_rework
 * insert both succeed. The rework_photos table auto-generates its own id.
 * Panel #2 Phase 1.5: no description captured (optional field on the table).
 */
export function buildReworkPhotoRow(
  reworkId: string,
  storagePath: string,
  fileName: string,
): { rework_id: string; storage_path: string; file_name: string } {
  return {
    rework_id: reworkId,
    storage_path: storagePath,
    file_name: fileName,
  }
}
