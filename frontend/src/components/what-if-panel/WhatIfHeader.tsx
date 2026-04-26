import { cn } from '@/lib/utils'

interface WhatIfHeaderProps {
  className?: string
}

export function WhatIfHeader({ className }: WhatIfHeaderProps) {
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
          What-If
        </span>
        <span className='font-mono text-[10px] text-muted-foreground/65'>
          / counterfactual
        </span>
      </div>
    </div>
  )
}
