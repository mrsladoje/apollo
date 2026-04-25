import { cn } from '@/lib/utils'

interface UptimeDeltaProps {
  delta: number
  className?: string
}

export function UptimeDelta({ delta, className }: UptimeDeltaProps) {
  const positive = delta >= 0
  return (
    <div className={cn('flex items-baseline gap-1', className)}>
      <span
        className={cn(
          'text-3xl font-bold tabular-nums',
          positive ? 'text-emerald-400' : 'text-red-400',
        )}
      >
        {positive ? '+' : ''}
        {delta.toFixed(1)} h
      </span>
      <span className='text-[10px] text-muted-foreground'>
        uptime gained (modeled)
      </span>
    </div>
  )
}
