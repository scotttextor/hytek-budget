// Feature flags — Phase 0.
// Originally backed by NEXT_PUBLIC_ENABLE_* env vars per Panel #1 strategist's
// recommendation (Vercel-toggleable without code deploy). Simplified to plain
// constants for Phase 0 to eliminate a dependency on Vercel env var wiring
// that was blocking deploy. If a runtime toggle becomes necessary later, swap
// these back to process.env reads — code shape is unchanged.

export const FLAGS = {
  variations: true,
  rework: true,
  photos: true,
  reports: false,
} as const
