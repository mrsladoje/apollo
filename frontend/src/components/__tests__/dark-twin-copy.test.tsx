import { describe, it, expect } from 'vitest'
import { UNIVERSES } from '@/types'

// FR-W.2 — Dark Twin label present in all three UI surfaces.
describe('Dark Twin labelling (ADR-013, FR-W.2)', () => {
  it('exposes Universe A as the Dark Twin', () => {
    const dark = UNIVERSES.find((u) => u.id === 'dark-twin')
    expect(dark?.label).toBe('Universe A — Dark Twin')
  })

  it('exposes Universe C as Apollo (AI)', () => {
    const apollo = UNIVERSES.find((u) => u.id === 'apollo')
    expect(apollo?.label).toBe('Universe C — Apollo (AI)')
  })

  it('does not refer to NONE policy in user-facing labels', () => {
    UNIVERSES.forEach((u) => {
      expect(u.label).not.toMatch(/NONE/i)
    })
  })
})
