import { cn } from '@/lib/utils'
import type { ComponentStatus } from '@/types'
import { HealthBar } from './HealthBar'

interface HealthBarItem {
  component: string
  health: number
  status: ComponentStatus
}

interface HealthBarListProps {
  components: HealthBarItem[]
  className?: string
}

interface Subsystem {
  id: string
  label: string
  accent: string
  members: string[]
}

const SUBSYSTEMS: Subsystem[] = [
  {
    id: 'recoating',
    label: 'Recoating',
    accent: 'bg-[#0096D6]',
    members: ['blade', 'motor'],
  },
  {
    id: 'printhead',
    label: 'Printhead',
    accent: 'bg-[#7C3AED]',
    members: ['nozzle', 'resistor'],
  },
  {
    id: 'thermal',
    label: 'Thermal',
    accent: 'bg-[#F59E0B]',
    members: ['heater', 'insulation'],
  },
]

export function HealthBarList({ components, className }: HealthBarListProps) {
  const byId = new Map(components.map((c) => [c.component, c]))
  const grouped = SUBSYSTEMS.map((s) => ({
    ...s,
    items: s.members
      .map((m) => byId.get(m))
      .filter((c): c is HealthBarItem => c !== undefined),
  })).filter((g) => g.items.length > 0)

  const claimed = new Set(SUBSYSTEMS.flatMap((s) => s.members))
  const ungrouped = components.filter((c) => !claimed.has(c.component))

  return (
    <div className={cn('space-y-3', className)}>
      {grouped.map((g) => (
        <div
          key={g.id}
          className='rounded-md border border-[rgb(225,230,236)] bg-white/40 px-2.5 py-2'
        >
          <div className='mb-1.5 flex items-center gap-1.5'>
            <span className={cn('h-1.5 w-1.5 rounded-full', g.accent)} />
            <span className='font-mono text-[9px] font-semibold uppercase tracking-wider text-muted-foreground'>
              {g.label}
            </span>
          </div>
          <div className='space-y-2'>
            {g.items.map((c) => (
              <HealthBar
                key={c.component}
                component={c.component}
                health={c.health}
                status={c.status}
              />
            ))}
          </div>
        </div>
      ))}
      {ungrouped.length > 0 && (
        <div className='space-y-2'>
          {ungrouped.map((c) => (
            <HealthBar
              key={c.component}
              component={c.component}
              health={c.health}
              status={c.status}
            />
          ))}
        </div>
      )}
    </div>
  )
}
