import { cn } from '@/lib/utils'

interface WhatIfHeaderProps {
  className?: string
  open?: boolean
  onToggle?: () => void
}

export function WhatIfHeader({ className, open, onToggle }: WhatIfHeaderProps) {
  const interactive = typeof onToggle === 'function'
  return (
    <button
      type='button'
      onClick={onToggle}
      disabled={!interactive}
      aria-expanded={open}
      className={cn(
        'flex w-full items-center justify-between gap-3 text-left',
        interactive
          ? cn(
              'rounded-lg border px-4 py-2.5 transition-colors',
              'border-foreground/15 bg-background/40',
              'hover:border-foreground/30 hover:bg-background/70',
              open && 'border-foreground/25 bg-background/60',
            )
          : 'cursor-default pb-3',
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
      {interactive && (
        <span
          aria-hidden
          className='font-mono text-[11px] text-muted-foreground/80 transition-transform duration-200'
          style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
        >
          ▾
        </span>
      )}
    </button>
  )
}
