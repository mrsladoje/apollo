import { cn } from '@/lib/utils'
import { UniversePanel } from './UniversePanel'
import type { UniversePanelProps } from './UniversePanel'

interface UniversePanelGridProps {
  universes: UniversePanelProps[]
  className?: string
}

export function UniversePanelGrid({
  universes,
  className,
}: UniversePanelGridProps) {
  return (
    <div className={cn('grid grid-cols-3 gap-6', className)}>
      {universes.map((u) => (
        <UniversePanel key={u.universeId} {...u} />
      ))}
    </div>
  )
}
