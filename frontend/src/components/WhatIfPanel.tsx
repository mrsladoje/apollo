import { useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { cn } from '@/lib/utils'
import { useWhatIf } from '@/hooks/useWhatIf'
import type { CounterfactualResult } from '@/types'

const ALT_ACTIONS = [
  'swap_blade',
  'clean_nozzle',
  'replace_insulation',
  'reduce_temperature',
  'increase_maintenance',
]

interface WhatIfFormProps {
  onSubmit: (runId: string, branchT: number, altAction: string) => void
  loading?: boolean
  className?: string
}

function WhatIfForm({ onSubmit, loading, className }: WhatIfFormProps) {
  const [runId, setRunId] = useState('barcelona-humid-none-seed0042')
  const [branchT, setBranchT] = useState(30)
  const [altAction, setAltAction] = useState(ALT_ACTIONS[0])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit(runId, branchT, altAction)
  }

  return (
    <form onSubmit={handleSubmit} className={cn('space-y-3', className)}>
      <WhatIfField label='Run ID'>
        <select
          value={runId}
          onChange={(e) => setRunId(e.target.value)}
          className='w-full bg-transparent font-mono text-[11px] text-muted-foreground outline-none'
        >
          {[
            'barcelona-humid-none-seed0042',
            'phoenix-dry-none-seed0042',
            'stressed-none-seed0042',
          ].map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </WhatIfField>

      <WhatIfField label={`Branch at t=${branchT}`}>
        <input
          type='range'
          min={0}
          max={120}
          step={5}
          value={branchT}
          onChange={(e) => setBranchT(Number(e.target.value))}
          className='w-full accent-primary'
        />
      </WhatIfField>

      <WhatIfField label='Action'>
        <select
          value={altAction}
          onChange={(e) => setAltAction(e.target.value)}
          className='w-full bg-transparent font-mono text-[11px] text-muted-foreground outline-none'
        >
          {ALT_ACTIONS.map((a) => (
            <option key={a} value={a}>
              {a.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </WhatIfField>

      <button
        type='submit'
        disabled={loading}
        className='text-[11px] text-primary underline-offset-2 hover:underline disabled:opacity-40'
      >
        {loading ? 'Running…' : 'Run counterfactual'}
      </button>
    </form>
  )
}

interface WhatIfFieldProps {
  label: string
  children: React.ReactNode
  className?: string
}

function WhatIfField({ label, children, className }: WhatIfFieldProps) {
  return (
    <div className={cn('space-y-1', className)}>
      <p className='text-[10px] uppercase tracking-wider text-muted-foreground'>
        {label}
      </p>
      {children}
    </div>
  )
}

interface CounterfactualChartProps {
  result: CounterfactualResult
  branchT: number
  className?: string
}

function CounterfactualChart({
  result,
  branchT,
  className,
}: CounterfactualChartProps) {
  const data = result.original_health.map((o, i) => ({
    t: o.t,
    original: o.health,
    alt: result.alt_health[i]?.health ?? null,
  }))

  return (
    <div className={cn('space-y-2', className)}>
      <div className='h-32'>
        <ResponsiveContainer width='100%' height='100%'>
          <LineChart
            data={data}
            margin={{ top: 4, right: 0, left: -28, bottom: 0 }}
          >
            <XAxis
              dataKey='t'
              tick={{ fontSize: 9, fill: '#666' }}
              axisLine={false}
              tickLine={false}
            />
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
              formatter={(v) => [`${((v as number) * 100).toFixed(0)}%`]}
            />
            <ReferenceLine
              x={branchT}
              stroke='#6366f1'
              strokeDasharray='3 3'
              strokeOpacity={0.5}
            />
            <Line
              type='monotone'
              dataKey='original'
              stroke='#ef4444'
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type='monotone'
              dataKey='alt'
              stroke='#22c55e'
              strokeWidth={1.5}
              strokeDasharray='4 2'
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <UptimeDelta delta={result.uptime_delta_h} />
    </div>
  )
}

interface UptimeDeltaProps {
  delta: number
  className?: string
}

function UptimeDelta({ delta, className }: UptimeDeltaProps) {
  const positive = delta >= 0
  return (
    <div className={cn('flex items-baseline gap-1', className)}>
      <span
        className={cn(
          'text-3xl font-bold tabular-nums',
          positive ? 'text-emerald-400' : 'text-red-400',
        )}
      >
        {positive ? '+' : ''}
        {delta.toFixed(1)} h
      </span>
      <span className='text-[10px] text-muted-foreground'>
        uptime gained (modeled)
      </span>
    </div>
  )
}

interface WhatIfPanelProps {
  className?: string
}

export function WhatIfPanel({ className }: WhatIfPanelProps) {
  const { result, loading, run } = useWhatIf()
  const [lastBranchT, setLastBranchT] = useState(30)

  function handleSubmit(runId: string, branchT: number, altAction: string) {
    setLastBranchT(branchT)
    run({ run_id: runId, branch_t: branchT, alt_action: altAction })
  }

  return (
    <div className={cn('space-y-5', className)}>
      <WhatIfHeader />
      <WhatIfForm onSubmit={handleSubmit} loading={loading} />
      {result && <CounterfactualChart result={result} branchT={lastBranchT} />}
    </div>
  )
}

function WhatIfHeader({ className }: { className?: string }) {
  return (
    <p
      className={cn(
        'text-xs font-semibold uppercase tracking-widest text-muted-foreground',
        className,
      )}
    >
      What-If
    </p>
  )
}
