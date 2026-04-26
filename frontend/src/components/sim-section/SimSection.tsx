import { useState } from 'react'
import { cn } from '@/lib/utils'
import { useSim } from '@/hooks/useSim'
import { UniversePanelGrid } from '@/components/universe-panel'
import { UNIVERSES } from '@/types'
import { SimHeader } from './SimHeader'

interface SimSectionProps {
  className?: string
}

export function SimSection({ className }: SimSectionProps) {
  // Default 0.2× = 5x slower than the backend's natural sim cadence.
  const [speed, setSpeed] = useState(0.2)
  const [restartKey, setRestartKey] = useState(0)

  const { state } = useSim({ speed, restartKey })

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

  const applyPreset = (s: number) => {
    setSpeed(s)
    setRestartKey((k) => k + 1)
  }

  return (
    <section className={cn(className)}>
      <SimHeader
        speed={speed}
        onSpeedChange={setSpeed}
        onPreset={applyPreset}
        onRestart={() => setRestartKey((k) => k + 1)}
      />
      <UniversePanelGrid universes={universes} className='mt-4' />
    </section>
  )
}
