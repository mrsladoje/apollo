import { cn } from '@/lib/utils'
import { LiveIndicator } from './LiveIndicator'

interface SimHeaderProps {
  className?: string
}

export function SimHeader({ className }: SimHeaderProps) {
  return (
    <div className={cn('flex items-baseline gap-3', className)}>
      <p className='text-xs font-semibold uppercase tracking-widest text-muted-foreground'>
        Live Simulation
      </p>
      <LiveIndicator />
    </div>
  )
}
