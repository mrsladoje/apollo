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

  it('applies the refusal gray palette', () => {
    render(<SeverityBadge severity='REFUSAL' />)
    const badge = screen.getByText('REFUSAL')
    expect(badge.className).toMatch(/zinc/)
  })
})
