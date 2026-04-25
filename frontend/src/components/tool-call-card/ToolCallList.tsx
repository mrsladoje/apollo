import { cn } from '@/lib/utils'
import type { ToolCall } from '@/types'
import { ToolCallCard } from './ToolCallCard'

interface ToolCallListProps {
  toolCalls: ToolCall[]
  className?: string
}

export function ToolCallList({ toolCalls, className }: ToolCallListProps) {
  if (toolCalls.length === 0) return null
  return (
    <div className={cn('space-y-2', className)}>
      {toolCalls.map((tc) => (
        <ToolCallCard key={tc.call_id} toolCall={tc} />
      ))}
    </div>
  )
}
