import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { cn } from '@/lib/utils'
import type { ToolCall } from '@/types'
import { ToolCallSection } from './ToolCallSection'

interface ToolCallCardProps {
  toolCall: ToolCall
  className?: string
}

export function ToolCallCard({ toolCall, className }: ToolCallCardProps) {
  const [open, setOpen] = useState(false)
  const pending = toolCall.result === null
  const plot = getPlotResult(toolCall)

  return (
    <div className={cn('relative pl-3', className)}>
      <span
        aria-hidden
        className='pointer-events-none absolute left-0 top-1 bottom-1 w-[2px] rounded-full'
        style={{ background: 'rgba(0,150,214,0.5)' }}
      />
      <button
        type='button'
        className='flex w-full items-center gap-2 text-left transition-colors hover:text-foreground'
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          <ChevronDown className='h-3 w-3 text-muted-foreground' />
        ) : (
          <ChevronRight className='h-3 w-3 text-muted-foreground' />
        )}
        <span className='font-mono text-[11px] tracking-wide text-muted-foreground'>
          {toolCall.tool}
        </span>
        {pending && (
          <span
            className='ml-auto h-1.5 w-1.5 animate-hp-pulse rounded-full'
            style={{ background: '#F59E0B' }}
          />
        )}
      </button>

      {open && (
        <div className='mt-2 space-y-2'>
          <ToolCallSection label='args' value={toolCall.args} />
          {plot ? (
            <PlotComponentHistory result={plot} />
          ) : toolCall.result !== null ? (
            <ToolCallSection label='result' value={toolCall.result} />
          ) : null}
        </div>
      )}
    </div>
  )
}

type PlotPoint = { t: number; health: number }
type PlotResult = {
  run_id: string
  component: string
  points: PlotPoint[]
}

function getPlotResult(toolCall: ToolCall): PlotResult | null {
  if (toolCall.tool !== 'plot_component_history' || !toolCall.result) {
    return null
  }
  const result = toolCall.result
  const points = Array.isArray(result.points) ? result.points : []
  if (
    typeof result.run_id !== 'string' ||
    typeof result.component !== 'string' ||
    points.length === 0
  ) {
    return null
  }
  const parsed = points
    .map((p) => {
      if (
        typeof p === 'object' &&
        p !== null &&
        typeof (p as { t?: unknown }).t === 'number' &&
        typeof (p as { health?: unknown }).health === 'number'
      ) {
        return {
          t: (p as { t: number }).t,
          health: (p as { health: number }).health,
        }
      }
      return null
    })
    .filter((p): p is PlotPoint => p !== null)

  return parsed.length
    ? { run_id: result.run_id, component: result.component, points: parsed }
    : null
}

function PlotComponentHistory({ result }: { result: PlotResult }) {
  const data = result.points.map((p) => ({
    t: p.t,
    label: new Date(p.t * 1000).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    }),
    health: Number(p.health.toFixed(3)),
  }))
  const first = data[0]?.health ?? 0
  const last = data[data.length - 1]?.health ?? 0

  return (
    <div
      className='space-y-2 rounded-xl border p-3'
      style={{
        borderColor: 'rgba(0,150,214,0.18)',
        background: 'rgba(0,150,214,0.045)',
      }}
    >
      <div className='flex items-center justify-between gap-3'>
        <div>
          <p className='font-mono text-[10px] uppercase tracking-wider text-muted-foreground'>
            {result.component} history
          </p>
          <p className='truncate font-mono text-[10px] text-muted-foreground/80'>
            {result.run_id}
          </p>
        </div>
        <p className='font-mono text-[10px] text-muted-foreground'>
          {first.toFixed(3)} {'->'} {last.toFixed(3)}
        </p>
      </div>

      <div className='h-28'>
        <ResponsiveContainer width='100%' height='100%'>
          <LineChart data={data} margin={{ top: 6, right: 8, left: -28, bottom: 0 }}>
            <XAxis
              dataKey='label'
              tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }}
              tickLine={false}
              axisLine={false}
              minTickGap={18}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }}
              tickLine={false}
              axisLine={false}
              width={28}
            />
            <Tooltip
              formatter={(value) => [value, 'health']}
              labelClassName='font-mono text-[10px]'
              contentStyle={{
                borderRadius: 12,
                border: '1px solid rgba(0,150,214,0.18)',
                background: 'hsl(var(--background))',
                fontSize: 11,
              }}
            />
            <Line
              type='monotone'
              dataKey='health'
              stroke='#0096D6'
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
