import { cn } from '@/lib/utils'

interface LiveIndicatorProps {
  className?: string
}

export function LiveIndicator({ className }: LiveIndicatorProps) {
  return (
    <span className={cn('flex items-center gap-1.5', className)}>
      <span className='relative inline-flex h-1.5 w-1.5'>
        <span
          className='absolute inset-0 animate-hp-pulse rounded-full'
          style={{
            background:
              'radial-gradient(circle, #16A34A 0%, rgba(22,163,74,0.3) 60%, transparent 100%)',
          }}
        />
        <span
          className='relative h-1.5 w-1.5 rounded-full'
          style={{ background: '#16A34A' }}
        />
      </span>
      <span className='font-mono text-[9px] uppercase tracking-[0.28em] text-muted-foreground/70'>
        live
      </span>
    </span>
  )
}
