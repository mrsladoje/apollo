import { cn } from '@/lib/utils'
import type { Citation } from '@/types'
import { CitationChip } from './CitationChip'

interface CitationListProps {
  citations: Citation[]
  onCitationClick?: (citation: Citation) => void
  className?: string
}

export function CitationList({
  citations,
  onCitationClick,
  className,
}: CitationListProps) {
  if (citations.length === 0) return null
  return (
    <div className={cn('flex flex-wrap gap-1', className)}>
      {citations.map((c, i) => (
        <CitationChip
          key={`${c.run_id}-${c.component}-${c.timestamp}-${i}`}
          citation={c}
          onClick={onCitationClick}
        />
      ))}
    </div>
  )
}
