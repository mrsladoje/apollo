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
    <div className={cn('flex items-baseline justify-between', className)}>
      <p
        className={cn(
          'text-xs font-semibold tracking-wide',
          isDarkTwin ? 'text-red-400/70' : 'text-muted-foreground',
        )}
      >
        {label}
      </p>
      <span className='text-[10px] font-mono text-muted-foreground/50'>
        t={t}
      </span>
    </div>
  )
}
