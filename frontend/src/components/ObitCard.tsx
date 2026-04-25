import { cn } from '@/lib/utils'
import type { ObitEvent } from '@/types'

interface ObitCardProps {
  obit: ObitEvent
  className?: string
}

export function ObitCard({ obit, className }: ObitCardProps) {
  return (
    <div
      className={cn('border-l-2 border-red-500/40 pl-3 space-y-1', className)}
    >
      <p className='text-[10px] font-mono uppercase tracking-wider text-red-400'>
        {obit.component} — failed
      </p>
      <p className='text-[11px] text-muted-foreground leading-relaxed'>
        {obit.narrative}
      </p>
    </div>
  )
}

interface ObitListProps {
  obits: ObitEvent[]
  className?: string
}

export function ObitList({ obits, className }: ObitListProps) {
  if (obits.length === 0) return null
  return (
    <div className={cn('space-y-3', className)}>
      {obits.map((o, i) => (
        <ObitCard key={`${o.component}-${o.run_id}-${i}`} obit={o} />
      ))}
    </div>
  )
}
