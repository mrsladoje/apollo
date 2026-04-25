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

export function WhatIfForm({ onSubmit, loading, className }: WhatIfFormProps) {
  const [runId, setRunId] = useState('barcelona-01')
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
          {['barcelona-01', 'phoenix-02', 'dark-twin-00'].map((r) => (
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
