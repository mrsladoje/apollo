import { cn } from '@/lib/utils'
import { useSim } from '@/hooks/useSim'
import { UniversePanelGrid } from '@/components/universe-panel'
import { UNIVERSES } from '@/types'
import { SimHeader } from './SimHeader'

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
