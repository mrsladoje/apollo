import { useState } from 'react'
import { cn } from '@/lib/utils'
import { useSim, type SimScenario } from '@/hooks/useSim'
import { UniversePanelGrid } from '@/components/universe-panel'
import { UNIVERSES } from '@/types'
import { SimHeader } from './SimHeader'

interface SimSectionProps {
  className?: string
}

export function SimSection({ className }: SimSectionProps) {
  // Default 0.2× = 5x slower than the backend's natural sim cadence.
  const [speed, setSpeed] = useState(0.2)
  const [scenario, setScenario] = useState<SimScenario>('barcelona-humid')
  const [restartKey, setRestartKey] = useState(0)

  const { state } = useSim({ speed, restartKey, scenario })

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

  const applyScenario = (s: SimScenario) => {
    setScenario(s)
    setRestartKey((k) => k + 1)
  }

  return (
    <section className={cn(className)}>
      <SimHeader
        speed={speed}
        scenario={scenario}
        onSpeedChange={setSpeed}
        onPreset={applyPreset}
        onRestart={() => setRestartKey((k) => k + 1)}
        onScenarioChange={applyScenario}
      />
      <UniversePanelGrid universes={universes} className='mt-4' />
    </section>
  )
}
