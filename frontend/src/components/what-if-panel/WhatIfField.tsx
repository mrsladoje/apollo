import { cn } from '@/lib/utils'

interface WhatIfFieldProps {
  label: string
  children: React.ReactNode
  className?: string
}

export function WhatIfField({ label, children, className }: WhatIfFieldProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <p className='font-mono text-[9px] uppercase tracking-[0.28em] text-muted-foreground/75'>
        {label}
      </p>
      {children}
    </div>
  )
}
