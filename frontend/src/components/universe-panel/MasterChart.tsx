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

const COLOR_LINE = '#0096D6' // HP Blue
const COLOR_BAND = '#33A8DD' // HP Blue light
const COLOR_FAILURE = '#DC2626' // Standard alert red

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
          margin={{ top: 4, right: 0, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id='healthGrad' x1='0' y1='0' x2='0' y2='1'>
              <stop offset='5%' stopColor={COLOR_LINE} stopOpacity={0.22} />
              <stop offset='95%' stopColor={COLOR_LINE} stopOpacity={0} />
            </linearGradient>
            <linearGradient id='bandGrad' x1='0' y1='0' x2='0' y2='1'>
              <stop offset='5%' stopColor={COLOR_BAND} stopOpacity={0.14} />
              <stop offset='95%' stopColor={COLOR_BAND} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey='t' tick={false} axisLine={false} tickLine={false} />
          <YAxis
            domain={[0, 1]}
            tick={false}
            axisLine={false}
            tickLine={false}
            width={0}
          />
          <Tooltip
            contentStyle={{
              background: 'rgba(255,255,255,0.97)',
              border: '1px solid rgb(225 230 236)',
              borderRadius: 8,
              fontSize: 10,
              fontFamily: '"IBM Plex Mono", monospace',
              color: '#1A1F2C',
              boxShadow: '0 8px 24px -10px rgba(15,23,42,0.18)',
              backdropFilter: 'blur(8px)',
            }}
            cursor={{
              stroke: 'rgba(0,150,214,0.35)',
              strokeWidth: 1,
              strokeDasharray: '2 3',
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
            stroke={COLOR_LINE}
            strokeWidth={1.6}
            fill='url(#healthGrad)'
            dot={false}
            isAnimationActive={false}
          />
          {failures.map((f, i) => (
            <ReferenceDot
              key={`${f.component}-${i}`}
              x={f.t_fail}
              y={0.05}
              r={3.5}
              fill={COLOR_FAILURE}
              stroke='#FFFFFF'
              strokeWidth={1.4}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
