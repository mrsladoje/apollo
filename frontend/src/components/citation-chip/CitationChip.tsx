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
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[10px] tracking-wide text-muted-foreground transition-colors duration-200',
        'hover:border-[rgba(0,150,214,0.4)] hover:bg-[rgba(0,150,214,0.05)] hover:text-[#0073A8]',
        className,
      )}
      style={{
        borderColor: 'rgb(225 230 236)',
        background: '#FFFFFF',
      }}
      title={`run: ${citation.run_id} · ${citation.timestamp}`}
    >
      <span
        className='h-1.5 w-1.5 rounded-full'
        style={{
          background: '#0096D6',
          boxShadow: '0 0 4px rgba(0,150,214,0.55)',
        }}
      />
      {label}
    </button>
  )
}
