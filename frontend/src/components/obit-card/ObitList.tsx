import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ObitEvent } from '@/types'
import { ObitCard } from './ObitCard'

interface ObitListProps {
  obits: ObitEvent[]
  className?: string
}

export function ObitList({ obits, className }: ObitListProps) {
  const [isOpen, setIsOpen] = useState(false)
  if (obits.length === 0) return null
  return (
    <div className={cn('space-y-2', className)}>
      <button
        type='button'
        onClick={() => setIsOpen((v) => !v)}
        aria-expanded={isOpen}
        className='flex w-full items-center justify-between rounded-md px-2 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-foreground/60 hover:text-foreground/80 hover:bg-foreground/5 transition-colors'
      >
        <span>
          Failure log ({obits.length})
        </span>
        <ChevronDown
          className={cn(
            'h-3.5 w-3.5 transition-transform duration-200',
            isOpen && 'rotate-180',
          )}
        />
      </button>
      {isOpen && (
        <div className='space-y-3'>
          {obits.map((o, i) => (
            <ObitCard key={`${o.component}-${o.run_id}-${i}`} obit={o} />
          ))}
        </div>
      )}
    </div>
  )
}
