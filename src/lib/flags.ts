// Feature flags — Panel #1 Strategist recommendation.
// Read from NEXT_PUBLIC_* env vars so Vercel can toggle without a code deploy.
// Each flag gates one user-visible stream; if something misbehaves on Friday
// afternoon we flip it off in Vercel UI and it's gone in 60 seconds.

function flag(name: string, fallback = false): boolean {
  const raw = process.env[name]
  if (raw === undefined) return fallback
  return raw === 'true' || raw === '1'
}

export const FLAGS = {
  variations: flag('NEXT_PUBLIC_ENABLE_VARIATIONS', true),
  rework: flag('NEXT_PUBLIC_ENABLE_REWORK', true),
  photos: flag('NEXT_PUBLIC_ENABLE_PHOTOS', true),
  reports: flag('NEXT_PUBLIC_ENABLE_REPORTS', false),
} as const
