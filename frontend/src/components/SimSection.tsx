import { cn } from '@/lib/utils'
import { useSim } from '@/hooks/useSim'
import { UniversePanelGrid } from '@/components/UniversePanel'
import { UNIVERSES } from '@/types'

interface SimSectionProps {
  className?: string
}

export function SimSection({ className }: SimSectionProps) {
  const { state } = useSim()

  const universes = UNIVERSES.map(({ id, label }) => {
    const u = state[id]
    return {
      universeId: id,
      label,
      t: u.t,
      states: u.states,
      forecasts: u.forecasts,
      failures: u.failures,
      obituaries: u.obituaries,
      history: u.history,
    }
  })

  return (
    <section className={cn(className)}>
      <SimHeader />
      <UniversePanelGrid universes={universes} className='mt-4' />
    </section>
  )
}

function SimHeader({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-baseline gap-3', className)}>
      <p className='text-xs font-semibold uppercase tracking-widest text-muted-foreground'>
        Live Simulation
      </p>
      <LiveIndicator />
    </div>
  )
}

function LiveIndicator({ className }: { className?: string }) {
  return (
    <span className={cn('flex items-center gap-1', className)}>
      <span className='h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400' />
      <span className='text-[10px] text-muted-foreground/60'>live</span>
    </span>
  )
}
