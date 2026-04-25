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
import type { CounterfactualResult } from '@/types'
import { UptimeDelta } from './UptimeDelta'

interface CounterfactualChartProps {
  result: CounterfactualResult
  branchT: number
  className?: string
}

export function CounterfactualChart({
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
