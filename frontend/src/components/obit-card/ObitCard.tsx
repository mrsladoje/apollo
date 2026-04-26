import { cn } from '@/lib/utils'
import type { ObitEvent } from '@/types'

interface ObitCardProps {
  obit: ObitEvent
  className?: string
}

const ISO_DATETIME_RE = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?/g
const CAUSE_SENTENCE_RE = /\s*The dominant cause was ([^.]+)\.\s*/

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

function formatIso(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const month = MONTHS[d.getMonth()]
  const day = d.getDate()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${month} ${day}, ${hh}:${mm}`
}

function parseObitNarrative(narrative: string): {
  cause: string | null
  body: string
} {
  const match = narrative.match(CAUSE_SENTENCE_RE)
  const cause = match ? match[1].trim() : null
  const stripped = match ? narrative.replace(CAUSE_SENTENCE_RE, ' ') : narrative
  const body = stripped.replace(ISO_DATETIME_RE, (m) => formatIso(m)).trim()
  return { cause, body }
}

export function ObitCard({ obit, className }: ObitCardProps) {
  const { cause, body } = parseObitNarrative(obit.narrative)
  return (
    <div className={cn('relative space-y-1 rounded-md py-1 pl-3 pr-2', className)}>
      <span
        aria-hidden
        className='pointer-events-none absolute left-0 top-1 bottom-1 w-[2px] rounded-full'
        style={{ background: '#DC2626' }}
      />
      <p
        className='font-mono text-[10px] uppercase tracking-[0.16em]'
        style={{ color: '#B91C1C' }}
      >
        {obit.component} — failed
      </p>
      {cause && (
        <p className='text-[11px] font-medium leading-snug text-foreground/85'>
          {cause}
        </p>
      )}
      <p className='text-[12px] leading-relaxed text-foreground/65'>
        {body}
      </p>
    </div>
  )
}
