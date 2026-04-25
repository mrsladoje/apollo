import { cn } from '@/lib/utils'

interface WhatIfHeaderProps {
  className?: string
}

export function WhatIfHeader({ className }: WhatIfHeaderProps) {
  return (
    <p
      className={cn(
        'text-xs font-semibold uppercase tracking-widest text-muted-foreground',
        className,
      )}
    >
      What-If
    </p>
  )
}
