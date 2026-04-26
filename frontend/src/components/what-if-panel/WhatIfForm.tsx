import { useState } from 'react'
import { cn } from '@/lib/utils'
import { WhatIfField } from './WhatIfField'

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

const FIELD_INPUT =
  'w-full bg-transparent font-mono text-[11px] text-foreground/85 outline-none transition-colors hover:text-foreground'

export function WhatIfForm({ onSubmit, loading, className }: WhatIfFormProps) {
  const [runId, setRunId] = useState('barcelona-humid-none-seed0042')
  const [branchT, setBranchT] = useState(30)
  const [altAction, setAltAction] = useState(ALT_ACTIONS[0])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit(runId, branchT, altAction)
  }

  return (
    <form onSubmit={handleSubmit} className={cn('space-y-3.5', className)}>
      <WhatIfField label='Run ID'>
        <select
          value={runId}
          onChange={(e) => setRunId(e.target.value)}
          className={FIELD_INPUT}
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
          className='hp-range w-full'
        />
        <style>{`
          .hp-range {
            -webkit-appearance: none;
            appearance: none;
            background: linear-gradient(
              90deg,
              rgba(0,150,214,0.5) 0%,
              rgba(0,115,168,0.5) 100%
            );
            height: 2px;
            border-radius: 1px;
            outline: none;
          }
          .hp-range::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #FFFFFF;
            border: 2px solid #0096D6;
            cursor: pointer;
            box-shadow: 0 2px 6px -1px rgba(0,150,214,0.4);
            transition: transform 200ms ease;
          }
          .hp-range::-webkit-slider-thumb:hover {
            transform: scale(1.15);
          }
          .hp-range::-moz-range-thumb {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #FFFFFF;
            border: 2px solid #0096D6;
            cursor: pointer;
            box-shadow: 0 2px 6px -1px rgba(0,150,214,0.4);
          }
        `}</style>
      </WhatIfField>

      <WhatIfField label='Action'>
        <select
          value={altAction}
          onChange={(e) => setAltAction(e.target.value)}
          className={FIELD_INPUT}
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
        className={cn(
          'group relative inline-flex items-center gap-2.5 rounded-full px-5 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition-all duration-200',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'hover:shadow-[0_8px_22px_-8px_rgba(0,150,214,0.55)]',
        )}
        style={{
          background: 'linear-gradient(180deg, #0096D6 0%, #0073A8 100%)',
          color: '#FFFFFF',
          border: '1px solid rgba(0,115,168,0.9)',
          boxShadow:
            '0 1px 0 rgba(255,255,255,0.2) inset,' +
            '0 6px 16px -8px rgba(0,150,214,0.45)',
        }}
      >
        <span
          className='h-1.5 w-1.5 rounded-full transition-transform duration-300 group-hover:scale-125'
          style={{
            background: '#FFFFFF',
            animation: loading
              ? 'hp-pulse 1.6s ease-in-out infinite'
              : 'none',
          }}
        />
        {loading ? 'Running' : 'Run counterfactual'}
      </button>
    </form>
  )
}
