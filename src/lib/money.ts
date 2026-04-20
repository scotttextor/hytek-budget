// AUD money arithmetic — stored as integer cents to avoid IEEE 754 errors.
// Panel #2 Mathematician §8: single source of truth for currency parsing,
// formatting, and addition across the app.

export type Money = number & { readonly __brand: 'AUD_cents' }

const DECIMAL_PATTERN = /^-?\d+(\.\d{1,2})?$/
const AUD_FORMATTER = new Intl.NumberFormat('en-AU', {
  style: 'currency',
  currency: 'AUD',
})

export function parseAudCentsFromString(input: string): Money {
  const trimmed = input.trim()
  if (!trimmed) throw new Error('Invalid amount')
  const sanitized = trimmed.replace(/[,$\s]/g, '')
  if (!DECIMAL_PATTERN.test(sanitized)) throw new Error('Invalid amount')
  const dollars = Number.parseFloat(sanitized)
  if (!Number.isFinite(dollars)) throw new Error('Invalid amount')
  const cents = Math.round(dollars * 100)
  if (!Number.isSafeInteger(cents)) throw new Error('Invalid amount')
  return cents as Money
}

export function parseAudCentsFromNumeric(input: number | null): Money | null {
  if (input === null || input === undefined) return null
  if (!Number.isFinite(input)) return null
  // Half-away-from-zero rounding (documented policy).
  const sign = input < 0 ? -1 : 1
  const cents = sign * Math.round(Math.abs(input) * 100)
  return cents as Money
}

export function formatAud(cents: Money | number): string {
  const dollars = Number(cents) / 100
  return AUD_FORMATTER.format(dollars)
}

export function addMoney(a: Money, b: Money): Money {
  return ((a as number) + (b as number)) as Money
}

export function multiplyMoney(a: Money, scalar: number): Money {
  return Math.round((a as number) * scalar) as Money
}
