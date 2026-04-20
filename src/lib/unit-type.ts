// Map install_budget_items.unit_type → the input field shape installer sees.
// Panel #2 UX decision: one smart field, not a $/%/hrs/qty toggle — the data
// model already knows which mode applies.

import type { ClaimKind } from './types'

export interface InputMode {
  mode: ClaimKind
  label: string
  inputMode: 'numeric' | 'decimal'
  step: number
  min?: number
  max?: number
}

interface Context {
  budgetAmountCents?: number | null
}

const normalize = (ut: string): string => ut.trim().toLowerCase()

const HOURS_TOKENS = new Set(['hours', 'hrs', 'h', 'hour'])
const AREA_TOKENS = new Set(['m2', 'sqm', 'm²', 'area'])
const QTY_TOKENS = new Set(['lift', 'lifts', 'qty', 'each', 'unit', 'units', 'ea'])
const PERCENT_TOKENS = new Set(['%', 'pct', 'percent'])

export function unitTypeToInputMode(
  unitType: string | null,
  ctx: Context = {}
): InputMode {
  if (!unitType) return dollarMode()
  const t = normalize(unitType)

  if (HOURS_TOKENS.has(t)) {
    return { mode: 'hours', label: 'Hours worked today', inputMode: 'decimal', step: 0.25, min: 0 }
  }
  if (AREA_TOKENS.has(t)) {
    if (ctx.budgetAmountCents != null && ctx.budgetAmountCents > 0) {
      return { mode: 'percent', label: '% complete', inputMode: 'numeric', step: 1, min: 0, max: 100 }
    }
    return { mode: 'qty', label: 'm² today', inputMode: 'decimal', step: 0.5, min: 0 }
  }
  if (QTY_TOKENS.has(t)) {
    return { mode: 'qty', label: 'Units today', inputMode: 'numeric', step: 1, min: 0 }
  }
  if (PERCENT_TOKENS.has(t)) {
    return { mode: 'percent', label: '% complete', inputMode: 'numeric', step: 1, min: 0, max: 100 }
  }
  return dollarMode()
}

function dollarMode(): InputMode {
  return { mode: 'dollar', label: '$ claimed', inputMode: 'decimal', step: 0.01, min: 0 }
}
