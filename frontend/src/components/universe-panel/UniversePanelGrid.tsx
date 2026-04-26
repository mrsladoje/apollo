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
    <div
      className={cn(
        'grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-5',
        className,
      )}
    >
      {universes.map((u) => (
        <article
          key={u.universeId}
          className='hp-card p-5 transition-shadow duration-300 hover:shadow-[0_1px_0_rgba(255,255,255,1)_inset,0_2px_6px_rgba(15,23,42,0.06),0_18px_36px_-18px_rgba(15,23,42,0.16)]'
        >
          <UniversePanel {...u} />
        </article>
      ))}
    </div>
  )
}
