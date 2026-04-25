import { cn } from '@/lib/utils'

interface LiveIndicatorProps {
  className?: string
}

export function LiveIndicator({ className }: LiveIndicatorProps) {
  return (
    <span className={cn('flex items-center gap-1', className)}>
      <span className='h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400' />
      <span className='text-[10px] text-muted-foreground/60'>live</span>
    </span>
  )
}
