import { useState } from 'react'
import { cn } from '@/lib/utils'
import { useWhatIf } from '@/hooks/useWhatIf'
import { WhatIfHeader } from './WhatIfHeader'
import { WhatIfForm } from './WhatIfForm'
import { CounterfactualChart } from './CounterfactualChart'

interface WhatIfPanelProps {
  className?: string
}

export function WhatIfPanel({ className }: WhatIfPanelProps) {
  const { result, loading, run } = useWhatIf()
  const [lastBranchT, setLastBranchT] = useState(30)
  const [open, setOpen] = useState(false)

  function handleSubmit(runId: string, branchT: number, altAction: string) {
    setLastBranchT(branchT)
    run({ run_id: runId, branch_t: branchT, alt_action: altAction })
  }

  return (
    <div className={cn('space-y-5', className)}>
      <WhatIfHeader open={open} onToggle={() => setOpen((v) => !v)} />
      {open && (
        <div className='space-y-5'>
          <WhatIfForm onSubmit={handleSubmit} loading={loading} />
          {result && <CounterfactualChart result={result} branchT={lastBranchT} />}
        </div>
      )}
    </div>
  )
}
