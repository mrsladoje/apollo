import { cn } from '@/lib/utils'

const PACE_PRESETS = [0.2, 0.5, 1, 2]

interface PaceControlProps {
  className?: string
  speed: number
  onSpeedChange: (s: number) => void
  onPreset: (s: number) => void
  onRestart: () => void
}

export function PaceControl({
  className,
  speed,
  onSpeedChange,
  onPreset,
  onRestart,
}: PaceControlProps) {
  return (
    <div
      className={cn('flex items-center gap-2.5', className)}
      style={{ fontFamily: '"Inter", system-ui, sans-serif' }}
    >
      <span
        className='font-mono text-[9px] uppercase tracking-[0.28em] text-muted-foreground/70'
      >
        Pace
      </span>

      <input
        type='range'
        min={0.1}
        max={2}
        step={0.05}
        value={speed}
        onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
        aria-label='Sim playback pace'
        style={{ width: 88, accentColor: '#0096D6', cursor: 'pointer' }}
      />

      <span
        style={{
          fontSize: 10,
          fontWeight: 600,
          fontFamily: '"IBM Plex Mono", monospace',
          color: '#0096D6',
          minWidth: 38,
          textAlign: 'right',
          letterSpacing: '0.02em',
        }}
      >
        {speed.toFixed(2)}×
      </span>

      <span
        aria-hidden
        style={{ width: 1, height: 12, background: 'rgba(15,23,42,0.12)' }}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
        {PACE_PRESETS.map((p) => {
          const active = Math.abs(speed - p) < 1e-3
          return (
            <button
              key={p}
              onClick={() => onPreset(p)}
              style={{
                padding: '3px 7px',
                fontSize: 9,
                fontWeight: 600,
                letterSpacing: '0.06em',
                fontFamily: '"IBM Plex Mono", monospace',
                color: active ? '#FFFFFF' : 'rgba(26,31,44,0.65)',
                background: active ? '#0096D6' : 'transparent',
                border: active
                  ? '1px solid #0096D6'
                  : '1px solid rgba(15,23,42,0.12)',
                borderRadius: 999,
                cursor: 'pointer',
                lineHeight: 1,
              }}
            >
              {p}×
            </button>
          )
        })}
      </div>

      <button
        onClick={onRestart}
        aria-label='Restart sim playback'
        title='Restart playback'
        style={{
          width: 22,
          height: 22,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 999,
          border: '1px solid rgba(15,23,42,0.14)',
          background: '#FFFFFF',
          color: '#0096D6',
          cursor: 'pointer',
          fontSize: 11,
          lineHeight: 1,
        }}
      >
        ↻
      </button>
    </div>
  )
}
