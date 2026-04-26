import { cn } from '@/lib/utils'
import type { SimScenario } from '@/hooks/useSim'

interface ScenarioSelectProps {
  className?: string
  scenario: SimScenario
  onScenarioChange: (s: SimScenario) => void
}

const SCENARIOS: { value: SimScenario; label: string }[] = [
  { value: 'barcelona-humid', label: 'Barcelona · humid' },
  { value: 'phoenix-dry', label: 'Phoenix · dry' },
  { value: 'stressed', label: 'Stressed · adversarial' },
]

export function ScenarioSelect({
  className,
  scenario,
  onScenarioChange,
}: ScenarioSelectProps) {
  return (
    <div
      className={cn('flex items-center gap-2', className)}
      style={{ fontFamily: '"Inter", system-ui, sans-serif' }}
    >
      <span className='font-mono text-[9px] uppercase tracking-[0.28em] text-muted-foreground/70'>
        Scenario
      </span>
      <select
        value={scenario}
        onChange={(e) => onScenarioChange(e.target.value as SimScenario)}
        aria-label='Simulation scenario'
        style={{
          padding: '3px 22px 3px 8px',
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: '0.04em',
          fontFamily: '"IBM Plex Mono", monospace',
          color: '#1A1F2C',
          background:
            'url("data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'10\' height=\'6\' viewBox=\'0 0 10 6\'><path d=\'M1 1l4 4 4-4\' fill=\'none\' stroke=\'%230096D6\' stroke-width=\'1.4\' stroke-linecap=\'round\'/></svg>") no-repeat right 6px center #FFFFFF',
          border: '1px solid rgba(15,23,42,0.16)',
          borderRadius: 999,
          cursor: 'pointer',
          lineHeight: 1.2,
          appearance: 'none',
          WebkitAppearance: 'none',
          MozAppearance: 'none',
        }}
      >
        {SCENARIOS.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </select>
    </div>
  )
}
