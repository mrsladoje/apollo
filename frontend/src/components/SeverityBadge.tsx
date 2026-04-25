import { cn } from '@/lib/utils'
import type { Severity } from '@/types'

const SEVERITY_CLASSES: Record<Severity, string> = {
  INFO: 'bg-blue-500/10 text-blue-400 border border-blue-500/20',
  WARNING: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
  CRITICAL: 'bg-red-500/10 text-red-400 border border-red-500/20',
  REFUSAL: 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20',
}

interface SeverityBadgeProps {
  severity: Severity
  className?: string
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-mono font-semibold tracking-wider uppercase',
        SEVERITY_CLASSES[severity],
        className,
      )}
    >
      {severity}
    </span>
  )
}
