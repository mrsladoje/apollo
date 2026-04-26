import { cn } from '@/lib/utils'

interface UniverseHeaderProps {
  label: string
  t: number
  isDarkTwin?: boolean
  className?: string
}

export function UniverseHeader({
  label,
  t,
  isDarkTwin,
  className,
}: UniverseHeaderProps) {
  return (
    <div className={cn('flex items-baseline justify-between gap-2', className)}>
      <p
        className={cn(
          'truncate text-[12px] font-semibold tracking-tight',
          isDarkTwin ? 'text-[#B91C1C]' : 'text-foreground',
        )}
      >
        {label}
      </p>
      <span className='font-mono text-[10px] tabular-nums text-muted-foreground/60'>
        t={t}
      </span>
    </div>
  )
}
