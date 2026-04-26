import { Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatHeaderProps {
  className?: string
  onClear?: () => void
  canClear?: boolean
}

export function ChatHeader({ className, onClear, canClear }: ChatHeaderProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between pb-3 border-b border-border',
        className,
      )}
    >
      <p className='text-xs font-semibold uppercase tracking-widest text-muted-foreground'>
        Apollo
      </p>
      <button
        type='button'
        onClick={onClear}
        disabled={!canClear}
        aria-label='Clear chat'
        title='Clear chat'
        className={cn(
          'inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors',
          'hover:bg-accent hover:text-foreground',
          'disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-muted-foreground',
        )}
      >
        <Trash2 className='h-3.5 w-3.5' strokeWidth={2} />
      </button>
    </div>
  )
}
