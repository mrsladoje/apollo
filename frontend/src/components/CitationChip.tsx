import { cn } from '@/lib/utils'
import type { Citation } from '@/types'

interface CitationChipProps {
  citation: Citation
  onClick?: (citation: Citation) => void
  className?: string
}

export function CitationChip({
  citation,
  onClick,
  className,
}: CitationChipProps) {
  const ts = new Date(citation.timestamp)
  const label = `${citation.component} · ${ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`

  return (
    <button
      type='button'
      onClick={() => onClick?.(citation)}
      className={cn(
        'inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground',
        className,
      )}
      title={`run: ${citation.run_id} · ${citation.timestamp}`}
    >
      <span className='h-1.5 w-1.5 rounded-full bg-current opacity-60' />
      {label}
    </button>
  )
}

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
