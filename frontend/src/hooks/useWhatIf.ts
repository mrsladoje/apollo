import { useState } from 'react'
import type { CounterfactualResult } from '@/types'

interface WhatIfRequest {
  run_id: string
  branch_t: number
  alt_action: string
}

export function useWhatIf() {
  const [result, setResult] = useState<CounterfactualResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function run(req: WhatIfRequest) {
    setLoading(true)
    setResult(null)
    try {
      const res = await fetch('/api/whatif', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      })
      const data: CounterfactualResult = await res.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }

  return { result, loading, run }
}
