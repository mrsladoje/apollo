import { cn } from '@/lib/utils'

interface ToolCallSectionProps {
  label: string
  value: unknown
  className?: string
}

export function ToolCallSection({
  label,
  value,
  className,
}: ToolCallSectionProps) {
  return (
    <div className={cn('space-y-0.5', className)}>
      <p className='text-[10px] uppercase tracking-wider text-muted-foreground'>
        {label}
      </p>
      <pre className='overflow-x-auto rounded bg-muted/40 p-2 text-[10px] text-foreground/70'>
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  )
}
