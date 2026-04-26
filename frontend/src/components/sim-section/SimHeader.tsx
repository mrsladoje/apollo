import { cn } from '@/lib/utils'
import { LiveIndicator } from './LiveIndicator'

interface SimHeaderProps {
  className?: string
}

export function SimHeader({ className }: SimHeaderProps) {
  return (
    <div
      className={cn(
        'flex items-baseline justify-between gap-3 pb-3',
        className,
      )}
    >
      <div className='flex items-baseline gap-3'>
        <span
          className='font-sans text-[10px] font-semibold uppercase tracking-[0.28em]'
          style={{ color: '#1A1F2C' }}
        >
          Live Simulation
        </span>
        <span className='font-mono text-[10px] text-muted-foreground/65'>
          / 3 universes
        </span>
      </div>
      <LiveIndicator />
    </div>
  )
}
