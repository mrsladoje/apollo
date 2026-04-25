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
import type { FailureEvent } from '@/types'

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

export function MasterChart({
  chartData,
  failures,
  className,
}: MasterChartProps) {
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
