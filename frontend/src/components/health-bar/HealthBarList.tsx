import { cn } from '@/lib/utils'
import type { ComponentStatus } from '@/types'
import { HealthBar } from './HealthBar'

interface HealthBarListProps {
  components: Array<{
    component: string
    health: number
    status: ComponentStatus
  }>
  className?: string
}

export function HealthBarList({ components, className }: HealthBarListProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {components.map((c) => (
        <HealthBar
          key={c.component}
          component={c.component}
          health={c.health}
          status={c.status}
        />
      ))}
    </div>
  )
}
