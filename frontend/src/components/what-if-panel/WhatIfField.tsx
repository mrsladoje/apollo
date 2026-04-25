import { cn } from '@/lib/utils'

interface WhatIfFieldProps {
  label: string
  children: React.ReactNode
  className?: string
}

export function WhatIfField({ label, children, className }: WhatIfFieldProps) {
  return (
    <div className={cn('space-y-1', className)}>
      <p className='text-[10px] uppercase tracking-wider text-muted-foreground'>
        {label}
      </p>
      {children}
    </div>
  )
}
