import { cn } from '@/lib/utils'

interface UptimeDeltaProps {
  delta: number
  className?: string
}

export function UptimeDelta({ delta, className }: UptimeDeltaProps) {
  const positive = delta >= 0
  return (
    <div className={cn('flex items-baseline gap-2', className)}>
      <span
        className='font-display text-3xl font-semibold tabular-nums leading-none tracking-tight'
        style={{ color: positive ? '#16A34A' : '#B91C1C' }}
      >
        {positive ? '+' : ''}
        {delta.toFixed(1)} h
      </span>
      <span className='font-mono text-[9px] uppercase tracking-[0.16em] text-muted-foreground/65'>
        uptime gained · modeled
      </span>
    </div>
  )
}
