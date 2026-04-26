import { cn } from '@/lib/utils'
import { PaceControl } from './PaceControl'

interface SimHeaderProps {
  className?: string
  speed: number
  onSpeedChange: (s: number) => void
  onPreset: (s: number) => void
  onRestart: () => void
}

export function SimHeader({
  className,
  speed,
  onSpeedChange,
  onPreset,
  onRestart,
}: SimHeaderProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 pb-3',
        className,
      )}
    >
      <div className='flex items-baseline gap-3'>
        <span
          className='font-sans text-[10px] font-semibold uppercase tracking-[0.28em]'
          style={{ color: '#1A1F2C' }}
        >
          Live Simulation
        </span>
        <span className='font-mono text-[10px] text-muted-foreground/65'>
          / 3 universes
        </span>
      </div>
      <PaceControl
        speed={speed}
        onSpeedChange={onSpeedChange}
        onPreset={onPreset}
        onRestart={onRestart}
      />
    </div>
  )
}
