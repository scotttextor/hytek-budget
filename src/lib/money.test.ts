import { describe, it, expect } from 'vitest'
import {
  parseAudCentsFromString,
  parseAudCentsFromNumeric,
  formatAud,
  type Money,
} from './money'

describe('parseAudCentsFromString', () => {
  it('parses plain number', () => {
    expect(parseAudCentsFromString('100')).toBe(10000)
  })
  it('parses with dollar sign', () => {
    expect(parseAudCentsFromString('$100')).toBe(10000)
  })
  it('parses with commas', () => {
    expect(parseAudCentsFromString('$1,000.50')).toBe(100050)
  })
  it('parses negative', () => {
    expect(parseAudCentsFromString('-$50.25')).toBe(-5025)
  })
  it('rejects NaN', () => {
    expect(() => parseAudCentsFromString('abc')).toThrow(/Invalid amount/)
  })
  it('rejects >2 decimals', () => {
    expect(() => parseAudCentsFromString('1.234')).toThrow(/Invalid amount/)
  })
  it('rejects empty', () => {
    expect(() => parseAudCentsFromString('   ')).toThrow(/Invalid amount/)
  })
  it('rejects overflow', () => {
    expect(() => parseAudCentsFromString('1e20')).toThrow(/Invalid amount/)
  })
})

describe('parseAudCentsFromNumeric', () => {
  it('converts Supabase numeric to cents', () => {
    expect(parseAudCentsFromNumeric(1234.56)).toBe(123456)
  })
  it('handles zero', () => {
    expect(parseAudCentsFromNumeric(0)).toBe(0)
  })
  it('handles null as null', () => {
    expect(parseAudCentsFromNumeric(null)).toBeNull()
  })
  it('rounds half-away-from-zero on third decimal', () => {
    expect(parseAudCentsFromNumeric(0.125)).toBe(13)
    expect(parseAudCentsFromNumeric(-0.125)).toBe(-13)
  })
})

describe('formatAud', () => {
  it('formats cents to AUD string', () => {
    expect(formatAud(123456 as Money)).toBe('$1,234.56')
  })
  it('formats zero', () => {
    expect(formatAud(0 as Money)).toBe('$0.00')
  })
  it('formats negative', () => {
    expect(formatAud(-5025 as Money)).toBe('-$50.25')
  })
})
