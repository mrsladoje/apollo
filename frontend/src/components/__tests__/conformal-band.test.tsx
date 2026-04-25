// FR-W.6 — Conformal prediction band shape matches Plan A's Forecast contract.
import { describe, it, expect } from 'vitest'
import type { Forecast } from '@/types'

describe('conformal-band FR-W.6', () => {
  it('Forecast type carries point + lower + upper + ci_level', () => {
    const f: Forecast = {
      component_id: 'nozzle',
      horizon_min: 10,
      point: 0.78,
      lower: 0.7,
      upper: 0.85,
      ci_level: 0.95,
    }
    expect(f.lower).toBeLessThanOrEqual(f.point)
    expect(f.upper).toBeGreaterThanOrEqual(f.point)
    expect(f.ci_level).toBe(0.95)
  })
})
