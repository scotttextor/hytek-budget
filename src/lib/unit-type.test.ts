import { describe, it, expect } from 'vitest'
import { unitTypeToInputMode } from './unit-type'

describe('unitTypeToInputMode', () => {
  it('maps hours-like', () => {
    for (const ut of ['hours', 'hrs', 'h', 'HOURS']) {
      expect(unitTypeToInputMode(ut).mode).toBe('hours')
    }
  })
  it('maps area-like to percent when budget_amount known', () => {
    const m = unitTypeToInputMode('m2', { budgetAmountCents: 100000 })
    expect(m.mode).toBe('percent')
  })
  it('maps area-like to qty when no budget', () => {
    const m = unitTypeToInputMode('m2', { budgetAmountCents: null })
    expect(m.mode).toBe('qty')
  })
  it('maps lift-like to qty', () => {
    expect(unitTypeToInputMode('lifts').mode).toBe('qty')
    expect(unitTypeToInputMode('each').mode).toBe('qty')
  })
  it('maps percent-like to percent', () => {
    expect(unitTypeToInputMode('%').mode).toBe('percent')
    expect(unitTypeToInputMode('pct').mode).toBe('percent')
  })
  it('defaults to dollar for null', () => {
    expect(unitTypeToInputMode(null).mode).toBe('dollar')
  })
  it('defaults to dollar for unknown', () => {
    expect(unitTypeToInputMode('somethingweird').mode).toBe('dollar')
  })
  it('hours mode label + keyboard', () => {
    const m = unitTypeToInputMode('hours')
    expect(m.label).toMatch(/hours/i)
    expect(m.inputMode).toBe('decimal')
  })
  it('percent mode caps at 100', () => {
    const m = unitTypeToInputMode('%')
    expect(m.max).toBe(100)
    expect(m.min).toBe(0)
  })
})
