import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { cn } from '@/lib/utils'
import { HealthBarList } from '@/components/HealthBar'
import { ObitList } from '@/components/ObitCard'
import type {
  ComponentId,
  ComponentState,
  ComponentStatus,
  FailureEvent,
  Forecast,
  ObitEvent,
} from '@/types'
import type { UniverseId } from '@/types'

interface UniversePanelProps {
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

  // Chart data: history + forecast band
  const chartData = history.map((h) => ({
    t: h.t,
    health: h.health,
    lower: undefined as number | undefined,
    upper: undefined as number | undefined,
  }))

  // Attach the most recent forecast band point to the last entry
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

interface UniverseHeaderProps {
  label: string
  t: number
  isDarkTwin?: boolean
  className?: string
}

function UniverseHeader({
  label,
  t,
  isDarkTwin,
  className,
}: UniverseHeaderProps) {
  return (
    <div className={cn('flex items-baseline justify-between', className)}>
      <p
        className={cn(
          'text-xs font-semibold tracking-wide',
          isDarkTwin ? 'text-red-400/70' : 'text-muted-foreground',
        )}
      >
        {label}
      </p>
      <span className='text-[10px] font-mono text-muted-foreground/50'>
        t={t}
      </span>
    </div>
  )
}

interface ChartEntry {
  t: number
  health: number
  lower?: number
  upper?: number
}

interface MasterChartProps {
  chartData: ChartEntry[]
  failures: FailureEvent[]
  className?: string
}

function MasterChart({ chartData, failures, className }: MasterChartProps) {
  return (
    <div className={cn('h-28', className)}>
      <ResponsiveContainer width='100%' height='100%'>
        <AreaChart
          data={chartData}
          margin={{ top: 4, right: 0, left: -28, bottom: 0 }}
        >
          <defs>
            <linearGradient id='healthGrad' x1='0' y1='0' x2='0' y2='1'>
              <stop offset='5%' stopColor='#3b82f6' stopOpacity={0.15} />
              <stop offset='95%' stopColor='#3b82f6' stopOpacity={0} />
            </linearGradient>
            <linearGradient id='bandGrad' x1='0' y1='0' x2='0' y2='1'>
              <stop offset='5%' stopColor='#6366f1' stopOpacity={0.08} />
              <stop offset='95%' stopColor='#6366f1' stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey='t' tick={false} axisLine={false} tickLine={false} />
          <YAxis
            domain={[0, 1]}
            tick={{ fontSize: 9, fill: '#666' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: 'hsl(var(--background))',
              border: '1px solid hsl(var(--border))',
              borderRadius: 4,
              fontSize: 10,
            }}
            labelFormatter={(v) => `t=${v}`}
            formatter={(v) => [`${((v as number) * 100).toFixed(0)}%`]}
          />
          <Area
            type='monotone'
            dataKey='upper'
            stroke='none'
            fill='url(#bandGrad)'
            fillOpacity={1}
            isAnimationActive={false}
          />
          <Area
            type='monotone'
            dataKey='health'
            stroke='#3b82f6'
            strokeWidth={1.5}
            fill='url(#healthGrad)'
            dot={false}
            isAnimationActive={false}
          />
          {failures.map((f, i) => (
            <ReferenceDot
              key={`${f.component}-${i}`}
              x={f.t_fail}
              y={0.05}
              r={3}
              fill='#ef4444'
              stroke='none'
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

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
