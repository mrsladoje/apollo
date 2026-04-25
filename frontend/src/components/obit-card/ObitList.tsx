import { cn } from '@/lib/utils'
import type { ObitEvent } from '@/types'
import { ObitCard } from './ObitCard'

interface ObitListProps {
  obits: ObitEvent[]
  className?: string
}

export function ObitList({ obits, className }: ObitListProps) {
  if (obits.length === 0) return null
  return (
    <div className={cn('space-y-3', className)}>
      {obits.map((o, i) => (
        <ObitCard key={`${o.component}-${o.run_id}-${i}`} obit={o} />
      ))}
    </div>
  )
}
