import { cn } from '@/lib/utils'
import type { ObitEvent } from '@/types'

interface ObitCardProps {
  obit: ObitEvent
  className?: string
}

export function ObitCard({ obit, className }: ObitCardProps) {
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
      <p className='text-[12px] leading-relaxed text-foreground/75'>
        {obit.narrative}
      </p>
    </div>
  )
}
