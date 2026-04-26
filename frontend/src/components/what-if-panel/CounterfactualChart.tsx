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

const COLOR_BRANCH = '#0096D6' // HP Blue branch marker
const COLOR_ORIGINAL = '#DC2626' // alert red — what would have happened
const COLOR_ALT = '#16A34A' // success green — counterfactual outcome

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
    <div className={cn('space-y-3', className)}>
      <div className='h-32'>
        <ResponsiveContainer width='100%' height='100%'>
          <LineChart
            data={data}
            margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
          >
            <XAxis
              dataKey='t'
              tick={{
                fontSize: 9,
                fill: '#64748B',
                fontFamily: '"IBM Plex Mono", monospace',
              }}
              axisLine={false}
              tickLine={false}
            />
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
              formatter={(v) => [`${((v as number) * 100).toFixed(0)}%`]}
            />
            <ReferenceLine
              x={branchT}
              stroke={COLOR_BRANCH}
              strokeDasharray='3 3'
              strokeOpacity={0.55}
              label={{
                value: 'branch',
                fill: COLOR_BRANCH,
                fontSize: 9,
                fontFamily: '"IBM Plex Mono", monospace',
                position: 'insideTopRight',
              }}
            />
            <Line
              type='monotone'
              dataKey='original'
              stroke={COLOR_ORIGINAL}
              strokeWidth={1.6}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type='monotone'
              dataKey='alt'
              stroke={COLOR_ALT}
              strokeWidth={1.6}
              strokeDasharray='4 2'
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className='flex items-center gap-4 font-mono text-[9px] uppercase tracking-[0.16em] text-muted-foreground/75'>
        <span className='flex items-center gap-1.5'>
          <span
            className='h-[1.5px] w-3 rounded-full'
            style={{ background: COLOR_ORIGINAL }}
          />
          original
        </span>
        <span className='flex items-center gap-1.5'>
          <span
            className='h-[1.5px] w-3 rounded-full'
            style={{
              background: `repeating-linear-gradient(90deg, ${COLOR_ALT} 0 4px, transparent 4px 6px)`,
            }}
          />
          counterfactual
        </span>
      </div>

      <UptimeDelta delta={result.uptime_delta_h} />
    </div>
  )
}
