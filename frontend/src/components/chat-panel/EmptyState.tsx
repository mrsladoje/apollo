import { cn } from '@/lib/utils'
import { SuggestedQuestions } from './SuggestedQuestions'

interface EmptyStateProps {
  className?: string
}

export function EmptyState({ className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-start gap-4 py-8', className)}>
      <p className='text-sm text-muted-foreground'>
        Ask me anything about the HP Metal Jet S100 telemetry.
      </p>
      <SuggestedQuestions />
    </div>
  )
}
