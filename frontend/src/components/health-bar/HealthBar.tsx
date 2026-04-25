import { cn } from '@/lib/utils'
import type { ComponentStatus } from '@/types'

const STATUS_CLASSES: Record<ComponentStatus, string> = {
  FUNCTIONAL: 'bg-emerald-500',
  DEGRADED: 'bg-amber-400',
  CRITICAL: 'bg-red-500',
  FAILED: 'bg-zinc-700',
}

const STATUS_TEXT: Record<ComponentStatus, string> = {
  FUNCTIONAL: 'text-emerald-400',
  DEGRADED: 'text-amber-300',
  CRITICAL: 'text-red-400',
  FAILED: 'text-zinc-500',
}

interface HealthBarProps {
  component: string
  health: number
  status: ComponentStatus
  className?: string
}

export function HealthBar({
  component,
  health,
  status,
  className,
}: HealthBarProps) {
  const pct = Math.round(health * 100)

  return (
    <div className={cn('space-y-1', className)}>
      <div className='flex items-center justify-between'>
        <span className='text-[10px] font-mono text-muted-foreground'>
          {component}
        </span>
        <span className={cn('text-[10px] font-mono', STATUS_TEXT[status])}>
          {pct}%
        </span>
      </div>
      <div className='h-1 w-full rounded-full bg-muted/30'>
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            STATUS_CLASSES[status],
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
