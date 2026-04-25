import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CitationChip } from '@/components/citation-chip'
import type { Citation } from '@/types'

const cite: Citation = {
  run_id: 'barcelona-humid-ai-seed0042',
  component: 'nozzle',
  timestamp: '2026-04-25T10:00:00Z',
}

describe('<CitationChip>', () => {
  it('renders the component label', () => {
    render(<CitationChip citation={cite} />)
    expect(screen.getByRole('button')).toHaveTextContent(/nozzle/)
  })

  it('invokes onClick synchronously (FR-3.8 dispatch budget)', () => {
    const onClick = vi.fn()
    render(<CitationChip citation={cite} onClick={onClick} />)
    fireEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledWith(cite)
  })
})
