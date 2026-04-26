import { cn } from '@/lib/utils'
import type { Severity } from '@/types'

// Corporate-clean severity chips — HP Blue for INFO, semantic for the rest
const SEVERITY_CLASSES: Record<Severity, string> = {
  INFO: 'bg-[rgba(0,150,214,0.10)] text-[#0073A8] border-[rgba(0,150,214,0.32)]',
  WARNING:
    'bg-[rgba(245,158,11,0.10)] text-[#B45309] border-[rgba(245,158,11,0.32)]',
  CRITICAL:
    'bg-[rgba(220,38,38,0.10)] text-[#B91C1C] border-[rgba(220,38,38,0.32)]',
  REFUSAL:
    'bg-[rgba(100,116,139,0.10)] text-[#475569] border-[rgba(100,116,139,0.32)]',
}

interface SeverityBadgeProps {
  severity: Severity
  className?: string
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-[0.16em]',
        SEVERITY_CLASSES[severity],
        className,
      )}
    >
      {severity}
    </span>
  )
}
