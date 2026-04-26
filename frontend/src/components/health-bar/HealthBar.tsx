import { cn } from '@/lib/utils'
import type { ComponentStatus } from '@/types'

// HP-aligned semantic statuses — clean saturated tones, HP Blue for nominal
const STATUS_BAR: Record<ComponentStatus, string> = {
  FUNCTIONAL: 'bg-[linear-gradient(90deg,#0096D6_0%,#33A8DD_100%)]',
  DEGRADED: 'bg-[linear-gradient(90deg,#F59E0B_0%,#FBBF24_100%)]',
  CRITICAL: 'bg-[linear-gradient(90deg,#DC2626_0%,#EF4444_100%)]',
  FAILED: 'bg-[linear-gradient(90deg,#475569_0%,#64748B_100%)]',
}

const STATUS_TEXT: Record<ComponentStatus, string> = {
  FUNCTIONAL: 'text-[#0073A8]',
  DEGRADED: 'text-[#B45309]',
  CRITICAL: 'text-[#B91C1C]',
  FAILED: 'text-[#475569]',
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
    <div className={cn('space-y-1.5', className)}>
      <div className='flex items-center justify-between'>
        <span className='font-mono text-[10px] tracking-wide text-muted-foreground'>
          {component}
        </span>
        <span
          className={cn(
            'font-mono text-[10px] font-semibold tabular-nums',
            STATUS_TEXT[status],
          )}
        >
          {pct}%
        </span>
      </div>
      <div className='relative h-1 w-full overflow-hidden rounded-full bg-[rgb(225,230,236)]'>
        <div
          className={cn(
            'h-full rounded-full transition-[width] duration-700 ease-out',
            STATUS_BAR[status],
          )}
          style={{ width: `${pct}%` }}
        />
        <div
          aria-hidden
          className='pointer-events-none absolute inset-0 rounded-full'
          style={{
            background:
              'linear-gradient(180deg, rgba(255,255,255,0.4) 0%, rgba(255,255,255,0) 50%)',
          }}
        />
      </div>
    </div>
  )
}
