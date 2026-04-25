import { cn } from '@/lib/utils'
import { HealthBarList } from '@/components/health-bar'
import { ObitList } from '@/components/obit-card'
import type {
  ComponentId,
  ComponentState,
  ComponentStatus,
  FailureEvent,
  Forecast,
  ObitEvent,
  UniverseId,
} from '@/types'
import { UniverseHeader } from './UniverseHeader'
import { MasterChart } from './MasterChart'

export interface UniversePanelProps {
  universeId: UniverseId
  label: string
  t: number
  states: Record<ComponentId, ComponentState>
  forecasts: Record<ComponentId, Forecast>
  failures: FailureEvent[]
  obituaries: ObitEvent[]
  history: Array<{ t: number; health: number }>
  scrollToTime?: (t: number) => void
  className?: string
}

export function UniversePanel({
  universeId,
  label,
  t,
  states,
  forecasts,
  failures,
  obituaries,
  history,
  className,
}: UniversePanelProps) {
  const components: Array<{
    component: string
    health: number
    status: ComponentStatus
  }> = Object.values(states).map((s) => ({
    component: s.component_id,
    health: s.health,
    status: s.status,
  }))

  const chartData = history.map((h) => ({
    t: h.t,
    health: h.health,
    lower: undefined as number | undefined,
    upper: undefined as number | undefined,
  }))

  const forecastBands = Object.values(forecasts)
  if (forecastBands.length > 0 && chartData.length > 0) {
    const avg =
      forecastBands.reduce((a, f) => a + f.point, 0) / forecastBands.length
    const avgLower =
      forecastBands.reduce((a, f) => a + f.lower, 0) / forecastBands.length
    const avgUpper =
      forecastBands.reduce((a, f) => a + f.upper, 0) / forecastBands.length
    chartData[chartData.length - 1] = {
      ...chartData[chartData.length - 1],
      health: avg,
      lower: avgLower,
      upper: avgUpper,
    }
  }

  const isDarkTwin = universeId === 'dark-twin'

  return (
    <div className={cn('flex flex-col gap-4 min-w-0', className)}>
      <UniverseHeader label={label} t={t} isDarkTwin={isDarkTwin} />
      <MasterChart chartData={chartData} failures={failures} />
      {components.length > 0 && <HealthBarList components={components} />}
      <ObitList obits={obituaries} />
    </div>
  )
}
