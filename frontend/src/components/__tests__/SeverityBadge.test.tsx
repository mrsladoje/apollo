import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SeverityBadge } from '@/components/severity-badge'

describe('<SeverityBadge>', () => {
  it.each(['INFO', 'WARNING', 'CRITICAL', 'REFUSAL'] as const)(
    'renders %s badge',
    (sev) => {
      render(<SeverityBadge severity={sev} />)
      expect(screen.getByText(sev)).toBeInTheDocument()
    },
  )

  it('applies the muted refusal palette', () => {
    render(<SeverityBadge severity='REFUSAL' />)
    const badge = screen.getByText('REFUSAL')
    // Refusal uses a neutral slate palette distinct from the chromatic
    // INFO (HP Blue) / WARNING (amber) / CRITICAL (red) chips.
    expect(badge.className).toMatch(/100,116,139|#475569/i)
  })
})
