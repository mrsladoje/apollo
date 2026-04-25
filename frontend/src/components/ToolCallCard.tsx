import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ToolCall } from '@/types'

interface ToolCallCardProps {
  toolCall: ToolCall
  className?: string
}

export function ToolCallCard({ toolCall, className }: ToolCallCardProps) {
  const [open, setOpen] = useState(false)
  const pending = toolCall.result === null

  return (
    <div className={cn('border-l-2 border-border pl-3', className)}>
      <button
        type='button'
        className='flex w-full items-center gap-2 text-left'
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          <ChevronDown className='h-3 w-3 text-muted-foreground' />
        ) : (
          <ChevronRight className='h-3 w-3 text-muted-foreground' />
        )}
        <span className='font-mono text-[11px] text-muted-foreground'>
          {toolCall.tool}
        </span>
        {pending && (
          <span className='ml-auto h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400' />
        )}
      </button>

      {open && (
        <div className='mt-2 space-y-2'>
          <ToolCallSection label='args' value={toolCall.args} />
          {toolCall.result !== null && (
            <ToolCallSection label='result' value={toolCall.result} />
          )}
        </div>
      )}
    </div>
  )
}

interface ToolCallSectionProps {
  label: string
  value: unknown
  className?: string
}

function ToolCallSection({ label, value, className }: ToolCallSectionProps) {
  return (
    <div className={cn('space-y-0.5', className)}>
      <p className='text-[10px] uppercase tracking-wider text-muted-foreground'>
        {label}
      </p>
      <pre className='overflow-x-auto rounded bg-muted/40 p-2 text-[10px] text-foreground/70'>
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  )
}

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
